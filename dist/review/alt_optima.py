"""Item 3: bound the 2023 at-cap count across alternate optima, holding the objective at its optimum.

Year 2023, point values (same LP as the stored model: demand, lambda, beds, kappa at point).
Step 1: solve the LP, objective V*.  Step 2: MILP over the same feasible set plus
    c.x + PI*unmet <= V* (1 + tol)
with a binary z_j per facility (and z_p per non-floored pair), linked so that z = 1 iff the
unit is at cap, i.e. served/kappa > 0.95 (strict, 1e-7 margin):
    z=1  ->  served >= (0.95 + 1e-7) kappa      z=0  ->  served <= 0.95 kappa
Then minimise and maximise sum z. Counts are re-derived from the solution with a 1e-6 band
(the minimiser sits exactly on 0.95 for many units, so a bare '> 0.95' on floats is noise). tol = 1e-9 and 1e-6 (relative). Time limit 600 s per solve;
the solver's dual bound is reported next to the incumbent so that a limit hit is visible.
Facilities and pairs are done separately (the pair count is not bounded by the facility one).
"""
import sys, json, time
import numpy as np
from scipy import sparse
from scipy.optimize import linprog, milp, LinearConstraint, Bounds
sys.path.insert(0, 'dist/review')
import _boot_src as S

Y = S.Year('2023'); one = np.ones(len(Y.key))
r = S.gap_parts(Y, one, one, one)
kj, kp = r['kj'], r['kp']; nx, nu = Y.nx, Y.nu
w = one; wJ = w[Y.sel]
cnt = np.bincount(Y.pairv_J, weights=wJ, minlength=Y.npair); sm = np.bincount(Y.pairv_J, weights=wJ*Y.dias_J, minlength=Y.npair)
pc = np.bincount(Y.pkv_J, weights=wJ, minlength=Y.NP); ps = np.bincount(Y.pkv_J, weights=wJ*Y.dias_J, minlength=Y.NP)
pm = np.divide(ps, pc, out=np.zeros(Y.NP), where=pc > 0); lam = (sm + S.K*pm[Y.pair_pk])/(cnt + S.K)
Cb = sparse.coo_matrix((lam[Y.colpair], (Y.rC, Y.cC)), shape=(len(Y.J), nx+nu)).tocsr()
A_ub = sparse.vstack([Cb, Y.Sc, Y.Pb]).tocsr(); b_ub = np.concatenate([Y.B, kj, kp])
dem = r['dem']
lp = linprog(Y.obj, A_ub=A_ub, b_ub=b_ub, A_eq=Y.A, b_eq=dem, bounds=(0, None), method='highs')
V = lp.fun
fac0 = np.asarray(Y.Sc[:, :nx] @ lp.x[:nx]).ravel(); sv0 = np.bincount(Y.colpair, weights=lp.x[:nx], minlength=Y.npair)
nf = kp > 0.5001
L = [__doc__, f'LP optimum V* = {V:.9f}; |J| {len(Y.J)}, non-floored pairs {int(nf.sum())}',
     f'point solve: at-cap facilities {int((fac0/kj > .95).sum())}, at-cap pairs {int((nf & (sv0/kp > .95)).sum())}',
     f'facilities with kappa_j > 0 that are "interior" (neither 0 nor kappa): see counts below', '']
res = {'V': V, 'point_fac': int((fac0/kj > .95).sum()), 'point_pair': int((nf & (sv0/kp > .95)).sum())}

def run(level, tol, sense):
    nz = len(Y.J) if level == 'facility' else int(nf.sum())
    S_ = Y.Sc[:, :nx] if level == 'facility' else Y.Pb[:, :nx]
    cap = kj if level == 'facility' else kp[nf]
    if level == 'pair': S_ = S_[np.where(nf)[0], :]
    n = nx + nu + nz
    ext = lambda M: sparse.hstack([M, sparse.csr_matrix((M.shape[0], nz))]).tocsr()
    cons = [LinearConstraint(ext(A_ub), -np.inf, b_ub),
            LinearConstraint(ext(Y.A), dem, dem),
            LinearConstraint(sparse.csr_matrix(np.concatenate([Y.obj, np.zeros(nz)])), -np.inf, V*(1+tol))]
    Sx = sparse.hstack([S_, sparse.csr_matrix((S_.shape[0], nu))]).tocsr()
    Z = sparse.identity(nz, format='csr')
    cons.append(LinearConstraint(sparse.hstack([Sx, -sparse.diags((0.95+1e-7)*cap)*Z]).tocsr(), 0, np.inf))
    cons.append(LinearConstraint(sparse.hstack([Sx, -sparse.diags(0.05*cap)*Z]).tocsr(), -np.inf, 0.95*cap))
    integ = np.concatenate([np.zeros(nx+nu), np.ones(nz)])
    cvec = np.concatenate([np.zeros(nx+nu), np.full(nz, 1.0 if sense == 'min' else -1.0)])
    t0 = time.time()
    m = milp(cvec, constraints=cons, integrality=integ, bounds=Bounds(np.zeros(n), np.concatenate([np.full(nx+nu, np.inf), np.ones(nz)])),
             options=dict(time_limit=600, mip_rel_gap=0))
    if m.x is None:
        return dict(status=int(m.status), msg=m.message)
    x = m.x[:nx]; s = np.asarray(S_ @ x).ravel() if level == 'pair' else np.asarray(Y.Sc[:, :nx] @ x).ravel()
    ratio = np.divide(s, cap, out=np.zeros_like(s), where=cap > 0)
    cnt_true = int((ratio > 0.95 + 1e-6).sum()); cnt_lo = int((ratio > 0.95 - 1e-6).sum())
    obj = float(np.dot(Y.obj, m.x[:nx+nu]))
    return dict(status=int(m.status), msg=m.message, count=cnt_true, count_lo=cnt_lo, z_sum=int(round(m.x[nx+nu:].sum())),
                dual_bound=(None if m.mip_dual_bound is None else (m.mip_dual_bound if sense == 'min' else -m.mip_dual_bound)),
                obj_rel_excess=obj/V-1, secs=time.time()-t0)

for level in ('facility', 'pair'):
    for tol in (1e-9, 1e-6):
        for sense in ('min', 'max'):
            o = run(level, tol, sense); res[f'{level}|{tol}|{sense}'] = o
            L.append(f'{level:9s} tol {tol:.0e} {sense}: ' + (f"count {o['count']} (>=0.95-1e-6: {o['count_lo']}) (z_sum {o['z_sum']}) dual bound {o['dual_bound']} "
                     f"status {o['status']} obj excess {o['obj_rel_excess']:.2e} {o['secs']:.0f}s" if 'count' in o else str(o)))
            print(L[-1], flush=True)
txt = '\n'.join(L); open('dist/review/alt_optima.txt', 'w').write(txt + '\n'); json.dump(res, open('dist/review/alt_optima.json', 'w'), indent=1)

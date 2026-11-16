"""T1 (dist/sprint/PREREG_round3.md): disjointness across the optimal face. Usage: python dist/review/face_v2.py YEAR

LP = the paper's elective LP at point values with the ALL-RECORD stay-length shrinkage target (same as scripts/model_run.py, the stored model).
Face F = {(x,u) feasible, objective <= V*(1+TOL)}, TOL = 1e-6. Thresholds: A = served/kappa > 0.95 (+1e-6 band), B = served/kappa >= 0.999999.
Bed-bound = bed-day use / budget > 0.95. Aggregates only.
"""
import sys, os, json, time
import numpy as np
from scipy import sparse
from scipy.optimize import linprog, milp, LinearConstraint, Bounds
sys.path.insert(0, 'dist/review')
os.environ['BOOT_LAM'] = 'all'
import _boot_src as S
YEAR = sys.argv[1]; TOL = 1e-9; TL = 200; A_THR, B_THR, MARG = 0.95, 0.999999, 1e-4
Y = S.Year(YEAR); one = np.ones(len(Y.key)); nx, nu = Y.nx, Y.nu; J = list(Y.J); nj = len(J)
kj, kp, _, _ = S.kappas(Y, one); dem = np.bincount(Y.cellv, weights=one, minlength=nu)/12.0
# all-record lambda (as model_run.py)
pc = np.bincount(Y.pkv, minlength=Y.NP); ps = np.bincount(Y.pkv, weights=Y.dias, minlength=Y.NP); pm = ps/np.maximum(pc, 1)
cnt = np.bincount(Y.pairv_J, minlength=Y.npair); sm = np.bincount(Y.pairv_J, weights=Y.dias_J, minlength=Y.npair)
lam = (sm + S.K*pm[Y.pair_pk])/(cnt + S.K)
Cb = sparse.coo_matrix((lam[Y.colpair], (Y.rC, Y.cC)), shape=(nj, nx+nu)).tocsr()
Sc = Y.Sc; Pb = Y.Pb; B = Y.B
A_ub = sparse.vstack([Cb, Sc, Pb]).tocsr(); b_ub = np.concatenate([B, kj, kp])
res0 = linprog(Y.obj, A_ub=A_ub, b_ub=b_ub, A_eq=Y.A, b_eq=dem, bounds=(0, None), method='highs'); V = res0.fun
objrow = sparse.csr_matrix(np.concatenate([Y.obj[:nx], Y.obj[nx:]]))
A_face = sparse.vstack([A_ub, objrow]).tocsr(); b_face = np.concatenate([b_ub, [V*(1+TOL)]])
def fac_of(v): return np.asarray(Sc @ v).ravel()
def use_of(v): return np.asarray(Cb @ v).ravel()
x0 = res0.x; r0 = fac_of(x0)/kj; bb0 = use_of(x0)/B > 0.95
out = {'year': YEAR, 'n_fac': nj, 'V': V, 'reported_vertex': {'cap_A': int((r0 > A_THR).sum()), 'cap_B': int((r0 >= B_THR).sum()), 'bed_bound': int(bb0.sum()),
       'both_A': int(((r0 > A_THR) & bb0).sum()), 'both_B': int(((r0 >= B_THR) & bb0).sum())}}
print(YEAR, out['reported_vertex'], flush=True)


def viol(v):
    r = A_face @ v - b_face; return float(max(r.max(), 0.0)/max(np.abs(b_face).max(), 1.0))
out['reported_vertex']['row_violation'] = viol(res0.x)
THRS = (0.90, 0.95, 0.99)
def counts(v):
    fr = fac_of(v)/kj; ur = use_of(v)/B; c = {f'cap_{int(t*100)}': int((fr > t + 1e-6).sum()) for t in THRS}
    bed = ur > 0.95 + 1e-6; c['bed'] = int(bed.sum()); c['both_95'] = int(((fr > 0.95 + 1e-6) & bed).sum()); c['both_99'] = int(((fr > 0.99 + 1e-6) & bed).sum())
    c['unused_at_cap95'] = float(((B - use_of(v))[fr > 0.95 + 1e-6]).sum()); c['row_violation'] = viol(v); return c
out['reported_vertex'].update(counts(x0))
def solve(kind, thr=0.95):
    nz = nj; n = nx+nu+3*nz; ib, ic, iz = nx+nu, nx+nu+nz, nx+nu+2*nz
    ext = lambda M: sparse.hstack([M, sparse.csr_matrix((M.shape[0], 3*nz))]).tocsr()
    cons = [LinearConstraint(ext(A_face), -np.inf, b_face), LinearConstraint(ext(Y.A), dem, dem)]
    Zb = sparse.hstack([sparse.csr_matrix((nz, nx+nu)), sparse.identity(nz), sparse.csr_matrix((nz, 2*nz))]).tocsr()
    Zc = sparse.hstack([sparse.csr_matrix((nz, nx+nu+nz)), sparse.identity(nz), sparse.csr_matrix((nz, nz))]).tocsr()
    Zd = sparse.hstack([sparse.csr_matrix((nz, nx+nu+2*nz)), sparse.identity(nz)]).tocsr()
    F = ext(Sc.tocsr()); U = ext(Cb)
    capup = lambda: cons.append(LinearConstraint(F - sparse.diags((thr+MARG)*kj)@Zc, 0, np.inf)); capdn = lambda: cons.append(LinearConstraint(F - sparse.diags((1-thr)*kj)@Zc, -np.inf, thr*kj))
    bedup = lambda: cons.append(LinearConstraint(U - sparse.diags((0.95+MARG)*B)@Zb, 0, np.inf)); beddn = lambda: cons.append(LinearConstraint(U - sparse.diags(0.05*B)@Zb, -np.inf, 0.95*B))
    c = np.zeros(n)
    if kind in ('bed_min', 'bed_max'): bedup(); beddn(); c[ib:ic] = 1 if kind == 'bed_min' else -1
    elif kind in ('cap_min', 'cap_max'): capup(); capdn(); c[ic:iz] = 1 if kind == 'cap_min' else -1
    elif kind == 'both_max': capup(); bedup(); cons.append(LinearConstraint(Zd - Zb, -np.inf, 0)); cons.append(LinearConstraint(Zd - Zc, -np.inf, 0)); c[iz:] = -1
    elif kind in ('unused_max', 'unused_min'):
        capup(); capdn()
        if kind == 'unused_max': cons.append(LinearConstraint(Zd + U, -np.inf, B)); cons.append(LinearConstraint(Zd - sparse.diags(B)@Zc, -np.inf, 0)); c[iz:] = -1
        else: cons.append(LinearConstraint(Zd + U - sparse.diags(B)@Zc, 0, np.inf)); c[iz:] = 1
    integ = np.concatenate([np.zeros(nx+nu), np.ones(2*nz), (np.zeros(nz) if kind.startswith('unused') else np.ones(nz))])
    ub = np.concatenate([np.full(nx+nu, np.inf), np.ones(2*nz), (B if kind.startswith('unused') else np.ones(nz))])
    t0 = time.time(); m_ = milp(c, constraints=cons, integrality=integ, bounds=Bounds(np.zeros(n), ub), options=dict(time_limit=TL, mip_rel_gap=0))
    if m_.x is None: return dict(status=int(m_.status), msg=str(m_.message))
    r = counts(m_.x[:nx+nu]); r.update(status=int(m_.status), secs=time.time()-t0, obj=float(m_.fun), dual=(None if m_.mip_dual_bound is None else float(m_.mip_dual_bound))); return r
out['milp'] = {}
jobs = [('bed_min', 0.95), ('bed_max', 0.95)] + [(k, t) for t in THRS for k in ('cap_min', 'cap_max')] + [('both_max', 0.95), ('both_max', 0.99), ('unused_max', 0.95), ('unused_min', 0.95)]
for kind, thr in jobs:
    key = f'{kind}@{thr}'; out['milp'][key] = solve(kind, thr); print(key, json.dumps({a: (round(b, 4) if isinstance(b, float) else b) for a, b in out['milp'][key].items()}), flush=True)
    json.dump(out, open(f'dist/review/face2_{YEAR}.json', 'w'), indent=1, default=float)
print('DONE', YEAR)

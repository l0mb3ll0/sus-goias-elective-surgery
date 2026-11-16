"""T1 (dist/sprint/PREREG_round3.md): disjointness across the optimal face. Usage: python dist/review/face_analysis.py YEAR

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
YEAR = sys.argv[1]; TOL = 1e-6; TL = 300; A_THR, B_THR, MARG = 0.95, 0.999999, 1e-7
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

# ---- per-facility interval of served/kappa over F (exact: F is convex) ----
lo = np.zeros(nj); hi = np.zeros(nj); t0 = time.time()
for j in range(nj):
    c = np.zeros(nx+nu); c[:nx] = np.asarray(Sc[j, :nx].todense()).ravel()/kj[j]
    for sgn, store in ((1, lo), (-1, hi)):
        r = linprog(sgn*c, A_ub=A_face, b_ub=b_face, A_eq=Y.A, b_eq=dem, bounds=(0, None), method='highs')
        store[j] = sgn*r.fun if r.status == 0 else np.nan
print(f'intervals done {time.time()-t0:.0f}s', flush=True)
def classify(thr, strict):
    if strict: always, never = lo > thr + 1e-6, hi <= thr + 1e-6
    else:      always, never = lo >= thr - 1e-9, hi < thr - 1e-9
    return int(always.sum()), int((~always & ~never).sum()), int(never.sum()), always, never
cA = classify(A_THR, True); cB = classify(B_THR, False)
out['classification'] = {'A_gt_0.95': dict(always=cA[0], sometimes=cA[1], never=cA[2]), 'B_ge_0.999999': dict(always=cB[0], sometimes=cB[1], never=cB[2])}
out['ratio_interval_summary'] = {'max_width': float(np.nanmax(hi-lo)), 'median_width': float(np.nanmedian(hi-lo)), 'n_width_gt_0.05': int((hi-lo > 0.05).sum())}
# bed-bound intervals (use/B) for facilities that can be bed-bound at all
ulo = np.zeros(nj); uhi = np.zeros(nj)
for j in range(nj):
    c = np.zeros(nx+nu); c[:] = np.asarray(Cb[j].todense()).ravel()/B[j]
    for sgn, store in ((1, ulo), (-1, uhi)):
        r = linprog(sgn*c, A_ub=A_face, b_ub=b_face, A_eq=Y.A, b_eq=dem, bounds=(0, None), method='highs'); store[j] = sgn*r.fun if r.status == 0 else np.nan
bed_always = ulo > 0.95 + 1e-6; bed_never = uhi <= 0.95 + 1e-6
out['bed_classification'] = dict(always=int(bed_always.sum()), sometimes=int((~bed_always & ~bed_never).sum()), never=int(bed_never.sum()))
# facilities that can be both (necessary condition): not never-bed-bound and not never-cap-bound
out['can_be_both_necessary_A'] = int((~bed_never & ~cA[4]).sum()); out['can_be_both_necessary_B'] = int((~bed_never & ~cB[4]).sum())
print(json.dumps({k: out[k] for k in ('classification', 'bed_classification', 'can_be_both_necessary_A', 'can_be_both_necessary_B')}), flush=True)

# ---- MILPs ----
def solve(kind):
    nz = nj; n = nx+nu+3*nz; ib, ic, iz = nx+nu, nx+nu+nz, nx+nu+2*nz       # zb, zc, zboth blocks
    ext = lambda M: sparse.hstack([M, sparse.csr_matrix((M.shape[0], 3*nz))]).tocsr()
    cons = [LinearConstraint(ext(A_face), -np.inf, b_face), LinearConstraint(ext(Y.A), dem, dem)]
    Zb = sparse.hstack([sparse.csr_matrix((nz, nx+nu)), sparse.identity(nz), sparse.csr_matrix((nz, 2*nz))]).tocsr()
    Zc = sparse.hstack([sparse.csr_matrix((nz, nx+nu+nz)), sparse.identity(nz), sparse.csr_matrix((nz, nz))]).tocsr()
    Zd = sparse.hstack([sparse.csr_matrix((nz, nx+nu+2*nz)), sparse.identity(nz)]).tocsr()
    F = ext(Sc[:, :].tocsr() if Sc.shape[1] == nx+nu else Sc); U = ext(Cb)
    thr = B_THR if kind.endswith('_B') else A_THR; m = MARG if not kind.endswith('_B') else 0.0
    # z=1 implies; and (for min problems) z=0 implies not
    capup = lambda: cons.append(LinearConstraint(F - sparse.diags((thr+m)*kj)@Zc, 0, np.inf))
    capdn = lambda: cons.append(LinearConstraint(F - sparse.diags((1-thr)*kj)@Zc, -np.inf, thr*kj))
    bedup = lambda: cons.append(LinearConstraint(U - sparse.diags((0.95+MARG)*B)@Zb, 0, np.inf))
    beddn = lambda: cons.append(LinearConstraint(U - sparse.diags(0.05*B)@Zb, -np.inf, 0.95*B))
    c = np.zeros(n)
    if kind in ('bed_min', 'bed_max'):
        bedup(); beddn(); c[ib:ic] = 1 if kind == 'bed_min' else -1
    elif kind in ('cap_min', 'cap_max'):
        capup(); capdn(); c[ic:iz] = 1 if kind == 'cap_min' else -1
    elif kind in ('both_max_A', 'both_max_B'):
        capup(); bedup()
        cons.append(LinearConstraint(Zd - Zb, -np.inf, 0)); cons.append(LinearConstraint(Zd - Zc, -np.inf, 0)); c[iz:] = -1
    elif kind in ('unused_max', 'unused_min'):
        # w_j = unused bed-days counted when cap-bound(A): reuse zboth block as w (continuous)
        capup(); capdn()
        if kind == 'unused_max':
            cons.append(LinearConstraint(Zd + U, -np.inf, B)); cons.append(LinearConstraint(Zd - sparse.diags(B)@Zc, -np.inf, 0)); c[iz:] = -1
        else:
            cons.append(LinearConstraint(Zd + U - sparse.diags(B)@Zc, B - B, np.inf)); c[iz:] = 1
            # w >= (B - use) - B(1 - zc)  <=>  w + use - B zc >= 0
    integ = np.concatenate([np.zeros(nx+nu), np.ones(2*nz), (np.zeros(nz) if kind.startswith('unused') else np.ones(nz))])
    ub = np.concatenate([np.full(nx+nu, np.inf), np.ones(2*nz), (B if kind.startswith('unused') else np.ones(nz))])
    t0 = time.time()
    m_ = milp(c, constraints=cons, integrality=integ, bounds=Bounds(np.zeros(n), ub), options=dict(time_limit=TL, mip_rel_gap=0))
    if m_.x is None: return dict(status=int(m_.status), msg=m_.message)
    v = m_.x[:nx+nu]; fr = fac_of(v)/kj; ur = use_of(v)/B
    r = dict(status=int(m_.status), secs=time.time()-t0, dual=(None if m_.mip_dual_bound is None else float(m_.mip_dual_bound)), obj=float(m_.fun),
             cap_A=int((fr > A_THR+1e-6).sum()), cap_B=int((fr >= B_THR-1e-9).sum()), bed=int((ur > 0.95+1e-6).sum()),
             both_A=int(((fr > A_THR+1e-6) & (ur > 0.95+1e-6)).sum()), both_B=int(((fr >= B_THR-1e-9) & (ur > 0.95+1e-6)).sum()),
             unused_at_capA=float(((B - use_of(v))[fr > A_THR+1e-6]).sum()))
    return r
out['milp'] = {}
for kind in ('bed_min', 'bed_max', 'both_max_A', 'both_max_B', 'cap_min', 'cap_max', 'unused_max', 'unused_min'):
    out['milp'][kind] = solve(kind); print(kind, json.dumps(out['milp'][kind]), flush=True)
    json.dump(out, open(f'dist/review/face_{YEAR}.json', 'w'), indent=1, default=float)
# vertex unused at cap-bound for the reported solution
out['reported_vertex']['unused_at_capA'] = float(((B - use_of(x0))[r0 > A_THR]).sum())
json.dump(out, open(f'dist/review/face_{YEAR}.json', 'w'), indent=1, default=float)
print('DONE', YEAR)

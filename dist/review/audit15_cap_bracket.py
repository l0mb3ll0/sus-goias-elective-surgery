"""Reviewer-driven checks (a) cap bracket and (c) bed utilisation across the optimal face. PREREG_round4.md item 15."""
import sys, json, numpy as np
sys.path.insert(0, 'dist/review')
import audit_year as AY
from scipy import sparse
from scipy.optimize import linprog
rng = np.random.default_rng(20261107); out = {}
def pfloor(mu, n=2000):
    X = rng.poisson(mu[None, :, None], size=(n, len(mu), 12)).astype(float); cs = np.cumsum(np.pad(X, ((0, 0), (0, 0), (1, 0))), axis=2)
    return ((cs[:, :, 3:] - cs[:, :, :-3])/3).max(axis=2).mean(axis=0)/np.maximum(mu, 1e-9)
for y in ('2019', '2023', '2025'):
    Y = AY.AYear(y); kj, kp, jm, pmm = Y.kappas(); base = Y.solve()
    mu = jm.mean(axis=1); pmu = np.maximum(pmm.mean(axis=1), 0.5)
    res = {}
    for name, (a, b) in {'headline': (kj, kp), 'kappa_mean': (np.maximum(mu, 1e-6), pmu), 'kappa_noise_deflated': (np.maximum(mu, kj - mu*(pfloor(mu)-1)), np.maximum(pmu, kp - pmm.mean(axis=1)*(pfloor(np.maximum(pmm.mean(axis=1), 1e-3))-1)))}.items():
        try:
            r = Y.solve(kj=a, kp=b); res[name] = dict(gap=r['gap_J'], unmet=r['unmet'], bed_util=float(r['use'].sum()/r['B'].sum()), bed_bound=int((r['use']/r['B'] > 0.95).sum()), cap_over_demand=float(a.sum()/r['dem'].sum()))
        except AssertionError as e: res[name] = dict(error='infeasible')
        print(y, name, res[name], flush=True)
    # bed-day use over the optimal face
    nx, nu = Y.nx, Y.nu; V = base['V']; Cb = base['Cb']
    A_ub = sparse.vstack([Cb, Y.Sc, Y.Pb, sparse.csr_matrix(Y.obj)]).tocsr(); b_ub = np.concatenate([Y.B, base['kj'], base['kp'], [V*(1+1e-6)]])
    cvec = np.zeros(nx+nu); cvec[:nx] = np.asarray(Cb[:, :nx].sum(axis=0)).ravel()
    fr = [linprog(s*cvec, A_ub=A_ub, b_ub=b_ub, A_eq=Y.A, b_eq=base['dem'], bounds=(0, None), method='highs').fun*s for s in (1, -1)]
    res['bed_util_face'] = dict(min=fr[0]/Y.B.sum(), max=fr[1]/Y.B.sum(), reported=float(base['use'].sum()/Y.B.sum())); print(y, 'face util', res['bed_util_face'], flush=True)
    out[y] = res
json.dump(out, open('dist/review/audit15_cap_bracket.json', 'w'), indent=1)

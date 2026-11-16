"""Final-batch item 3: facilities that are at cap (> 0.95) in EVERY optimum of equal cost in 2023 (min over the face of served/kappa > 0.95 + 1e-6; tolerance 1e-9),
their observed exceedance 2023->2024, and a fixed-set stationary null (Poisson and resampling; no re-solve, so selection is not simulated)."""
import sys, os, json, numpy as np
sys.path.insert(0, 'dist/review'); os.environ['BOOT_LAM'] = 'all'
import _boot_src as S
from scipy import sparse
from scipy.optimize import linprog
import audit_year as AY
Y = AY.AYear('2023'); r0 = Y.solve(); kj = r0['kj']; nx, nu = Y.nx, Y.nu
A_face = sparse.vstack([sparse.vstack([r0['Cb'], Y.Sc, Y.Pb]), sparse.csr_matrix(Y.obj)]).tocsr(); b_face = np.concatenate([Y.B, r0['kj'], r0['kp'], [r0['V']*(1+1e-9)]])
mins = np.zeros(Y.nj)
for j in range(Y.nj):
    c = np.zeros(nx+nu); c[:nx] = np.asarray(Y.Sc[j, :nx].todense()).ravel()/kj[j]
    r = linprog(c, A_ub=A_face, b_ub=b_face, A_eq=Y.A, b_eq=r0['dem'], bounds=(0, None), method='highs'); mins[j] = r.fun if r.status == 0 else np.nan
always = mins > 0.95 + 1e-6; print('always at cap (>0.95) 2023:', int(always.sum()), 'of', Y.nj, flush=True)
Y1 = AY.AYear('2024'); k1 = dict(zip(Y1.J, Y1.kappas()[0])); kn = np.array([k1.get(j, 0.0) for j in Y.J]); obs = float((kn > kj)[always].mean()); n_obs = int(always.sum())
_, _, jm, _ = Y.kappas(); mu = jm.mean(axis=1); rng = np.random.default_rng(20261109)
def r3(M):
    cs = np.cumsum(np.pad(M, ((0, 0), (1, 0))), axis=1); return ((cs[:, 3:] - cs[:, :-3])/3).max(axis=1)
res = {}
for mode in ('poisson', 'resample'):
    rates = []
    for _ in range(1000):
        if mode == 'poisson': X = rng.poisson(mu[:, None], size=(Y.nj, 24)).astype(float)
        else: idx = rng.integers(0, 12, size=(Y.nj, 24)); X = jm[np.arange(Y.nj)[:, None], idx]
        a, b = r3(X[:, :12]), r3(X[:, 12:]); rates.append(float((b > a)[always].mean()))
    rates = np.array(rates); res[mode] = dict(null_mean=float(rates.mean()), lo=float(np.percentile(rates, 2.5)), hi=float(np.percentile(rates, 97.5)), p_ge=float((rates >= obs).mean()))
out = dict(n_always=n_obs, n_fac=int(Y.nj), observed_rate=obs, null=res); print(json.dumps(out), flush=True); json.dump(out, open('dist/review/always_set.json', 'w'), indent=1)

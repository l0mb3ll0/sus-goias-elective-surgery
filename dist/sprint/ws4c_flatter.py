"""Tests T1, T2 of WS4c_flatter_prereg.md. Aggregates only."""
import sys, json, numpy as np
OUT = {}
sys.path.insert(0, 'dist/review')
import _boot_src as S
rng = np.random.default_rng(20261105)
data = {}
for y in ('2019', '2023', '2025'):
    Y = S.Year(y); one = np.ones(len(Y.key)); kj, kp, jm, pmm = S.kappas(Y, one)
    D = np.bincount(Y.cellv, minlength=Y.nu).sum() / 12.0
    mu = jm.mean(axis=1)
    data[y] = dict(J=list(Y.J), kappa=kj, mu=mu, D=D)
    print(y, 'slack', round(kj.sum() / D, 3), ' coverage C', round(mu.sum() / D, 3), ' sum w r', round(kj.sum() / mu.sum(), 3))

def balanced(a, b):
    ia = {j: n for n, j in enumerate(data[a]['J'])}; ib = {j: n for n, j in enumerate(data[b]['J'])}
    common = sorted(set(ia) & set(ib)); return [ia[j] for j in common], [ib[j] for j in common]

def poisson_floor(mu, n=2000):
    X = rng.poisson(mu[None, :, None], size=(n, len(mu), 12)).astype(float)
    cs = np.cumsum(np.pad(X, ((0, 0), (0, 0), (1, 0))), axis=2); R = ((cs[:, :, 3:] - cs[:, :, :-3]) / 3).max(axis=2)
    return R.mean(axis=0) / mu

for a, b in (('2019', '2023'), ('2023', '2025'), ('2019', '2025')):
    ia, ib = balanced(a, b); A, B = data[a], data[b]
    mua, mub, ka, kb = A['mu'][ia], B['mu'][ib], A['kappa'][ia], B['kappa'][ib]
    ok = (mua > 0) & (mub > 0); mua, mub, ka, kb = mua[ok], mub[ok], ka[ok], kb[ok]
    ra, rb = ka / mua, kb / mub; wa, wb = mua / mua.sum(), mub / mub.sum()
    d_total = (wb * rb).sum() - (wa * ra).sum()
    within = ((wa + wb) / 2 * (rb - ra)).sum(); between = ((ra + rb) / 2 * (wb - wa)).sum()
    OUT[f'{a}->{b}'] = None
    print(f'\n{a}->{b}: balanced facilities {ok.sum()} | sum w r {np.dot(wa,ra):.3f} -> {np.dot(wb,rb):.3f} (change {d_total:+.3f}): within {within:+.3f} ({100*within/d_total:.0f}%), between {between:+.3f} ({100*between/d_total:.0f}%)')
    print(f'   coverage C on all J: {A["mu"].sum()/A["D"]:.3f} -> {B["mu"].sum()/B["D"]:.3f}; slack {A["kappa"].sum()/A["D"]:.3f} -> {B["kappa"].sum()/B["D"]:.3f}')
    fa, fb = poisson_floor(mua), poisson_floor(mub); na, nb = ra / fa, rb / fb
    stat = lambda idx: (np.dot(wb[idx] / wb[idx].sum(), nb[idx]) - np.dot(wa[idx] / wa[idx].sum(), na[idx]))
    pt = stat(np.arange(len(na)))
    bs = np.array([stat(rng.integers(0, len(na), len(na))) for _ in range(2000)]); lo, hi = np.percentile(bs, [2.5, 97.5])
    OUT[f'{a}->{b}'] = dict(n_balanced=int(ok.sum()), sum_wr_a=float(np.dot(wa,ra)), sum_wr_b=float(np.dot(wb,rb)), within=float(within), between=float(between), within_share=float(within/d_total),
        net_change=float(pt), net_lo=float(lo), net_hi=float(hi), slack_a=float(A['kappa'].sum()/A['D']), slack_b=float(B['kappa'].sum()/B['D']), coverage_a=float(A['mu'].sum()/A['D']), coverage_b=float(B['mu'].sum()/B['D']))
    print(f'   Poisson floor weighted mean r_P {np.dot(wa,fa):.3f} -> {np.dot(wb,fb):.3f}; weighted raw r {np.dot(wa,ra):.3f} -> {np.dot(wb,rb):.3f}; '
          f'net ratio {np.dot(wa,na):.3f} -> {np.dot(wb,nb):.3f}, change {pt:+.3f} [95% facility bootstrap {lo:+.3f}, {hi:+.3f}]')

json.dump(OUT, open('dist/sprint/WS4c_flatter.json', 'w'), indent=1)

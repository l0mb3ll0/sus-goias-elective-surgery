"""Final-batch item 5: bootstrap sensitivity. Variants (100 draws, all three years paired, same seed scheme):
  bothfixed  kappa AND demand at point values; stay lengths and observed baseline resampled (Dirichlet/exponential weights, CV 1)
  cv05       full resampling with weight dispersion halved: w = 1 + 0.5 (e - 1), e ~ Exp(1) (CV 0.5)
  multinomial full resampling with count weights: Multinomial(n, 1/n) slots (count-matched, integer weights, n draws)
Rules (PREREG_final.md): the upward shift of the full bootstrap is reported as dispersion-dependent if cv05 shift is below 70 per cent of the CV-1 shift."""
import sys, os, json, numpy as np
os.environ['BOOT_LAM'] = 'all'
sys.path.insert(0, 'dist/review')
import _boot_src as S
YEARS = ['2019', '2023', '2025']
Y = {y: S.Year(y) for y in YEARS}; allkeys = sorted({k for y in YEARS for k in Y[y].key}); kidx = {k: n for n, k in enumerate(allkeys)}
for y in YEARS: Y[y].kv = np.array([kidx[k] for k in Y[y].key])
NK = len(allkeys); one = {y: np.ones(len(Y[y].key)) for y in YEARS}
point = {y: S.gap_parts(Y[y], one[y], one[y], one[y])['gap'] for y in YEARS}; out = {'point': point}
VARIANT = sys.argv[1]
for variant in (VARIANT,):
    rng = np.random.default_rng(20261108 + len(variant)); rows = []
    for b in range(100):
        e = rng.exponential(size=NK)
        w = (1 + 0.5*(e - 1)) if variant == 'cv05' else (rng.multinomial(NK, np.full(NK, 1.0/NK)).astype(float) if variant == 'multinomial' else e)
        w = w*NK/w.sum(); row = []
        for y in YEARS:
            wy = w[Y[y].kv]
            r = S.gap_parts(Y[y], one[y], one[y], wy) if variant == 'bothfixed' else S.gap_parts(Y[y], wy, wy, wy)
            row.append(r['gap'] if r['ok'] else np.nan)
        rows.append(row)
        if (b+1) % 20 == 0: print(variant, b+1, flush=True)
    D = np.array(rows); D = D[~np.isnan(D).any(axis=1)]
    out[variant] = {y: dict(mean=float(D[:, k].mean()), sd=float(D[:, k].std(ddof=1)), lo=float(np.quantile(D[:, k], .025)), hi=float(np.quantile(D[:, k], .975)), shift_pp=100*float(D[:, k].mean() - point[y]),
                            covers_point=bool(np.quantile(D[:, k], .025) <= point[y] <= np.quantile(D[:, k], .975))) for k, y in enumerate(YEARS)}
    print(variant, json.dumps(out[variant]), flush=True); json.dump(out, open('dist/review/boot_sens_'+VARIANT+'.json', 'w'), indent=1)

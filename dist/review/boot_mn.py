"""T3 (dist/sprint/PREREG_round3.md): m-out-of-n multiplier bootstrap for the paired gap. m = floor(f*n), f in {0.5, 0.7}; 340 draws; all three years share the draw.
Slots = facility x month-of-year (n = 1836). Counts ~ Multinomial(m, 1/n), scaled by n/m (zero weights occur, unlike the Dirichlet scheme). Uses scripts/bootstrap_paired.Year (all-record shrinkage).
"""
import sys, json, numpy as np
sys.argv = ['bootstrap_paired', 'combine']
sys.path.insert(0, '.')
import scripts.bootstrap_paired as B
YEARS = B.YEARS; Y = {y: B.Year(y) for y in YEARS}
allkeys = sorted({k for y in YEARS for k in Y[y].key}); kidx = {k: n for n, k in enumerate(allkeys)}
for y in YEARS: Y[y].kv = np.array([kidx[k] for k in Y[y].key])
NK = len(allkeys); point = {}
for y in YEARS: point[y] = Y[y].gap(np.ones(len(Y[y].key)))
res = {'n_slots': NK, 'point': point}
for f in (0.5, 0.7):
    m = int(f*NK); rng = np.random.default_rng(20261106 + int(f*10)); rows = []
    for b in range(340):
        w = rng.multinomial(m, np.full(NK, 1.0/NK)).astype(float)*(NK/m)
        rows.append([Y[y].gap(w[Y[y].kv]) for y in YEARS])
        if (b+1) % 40 == 0: print(f, b+1, flush=True)
    D = np.array(rows); D = D[~np.isnan(D).any(axis=1)]
    out = {}
    for k, y in enumerate(YEARS):
        lo, hi = np.quantile(D[:, k], [0.025, 0.975])
        out[y] = dict(point=point[y], mean=float(D[:, k].mean()), sd=float(D[:, k].std(ddof=1)), lo=float(lo), hi=float(hi), covers_point=bool(lo <= point[y] <= hi), frac_below_point=float((D[:, k] < point[y]).mean()))
    res[f'm_{f}'] = out; res[f'm_{f}_draws'] = int(len(D))
    print(f'f={f} m={m}', json.dumps(out), flush=True)
    json.dump(res, open('dist/review/boot_mn.json', 'w'), indent=1)
lines = ['m-out-of-n multiplier bootstrap (T3). point = stored-model gap; interval = percentile 2.5/97.5; 340 draws']
for f in (0.5, 0.7):
    for y in YEARS:
        r = res[f'm_{f}'][y]; lines.append(f'f={f} {y}: point {100*r["point"]:.1f}  mean {100*r["mean"]:.1f}  sd {100*r["sd"]:.2f}  [{100*r["lo"]:.1f}, {100*r["hi"]:.1f}]  covers point: {r["covers_point"]}  frac below point {r["frac_below_point"]:.3f}')
open('dist/review/boot_mn.txt', 'w').write('\n'.join(lines) + '\n'); print('\n'.join(lines))

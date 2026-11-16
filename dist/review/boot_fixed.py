"""Paired bootstrap with kappa fixed at point values, then with demand fixed.

Uses the paper's own weight draws: seed 20260807 + 1000*chunk, chunks of 40, 150 and 150
(340 draws, the scheme that produced none/_boot_paired/draws_*.npy). Each draw solves three
variants per year on the same weight vector:

  full   demand, kappa, lambda and observed baseline all reweighted (the paper's bootstrap)
  kfix   kappa (facility and pair caps) at point values; everything else reweighted
  dfix   demand at point values; everything else reweighted

'Everything else' is lambda (stay length) and the observed-travel baseline, which the brief
does not mention, so they keep resampling in both variants.

    /usr/bin/time -v python dist/review/boot_fixed.py run --chunk N   (logs exit status, peak RSS)
    python dist/review/boot_fixed.py combine
"""
import json, os, sys, time, glob
import numpy as np
sys.path.insert(0, 'dist/review')
import _boot_src as S

YEARS = ['2019', '2023', '2025']
SEED, CHUNKS = 20260807, {0: 40, 1: 150, 2: 150}
TAG = os.environ.get('BOOT_FIXED_TAG', '')            # '' = original run (J-only shrinkage); '_all' = all-record shrinkage rerun
OUT = os.environ.get('BOOT_FIXED_OUT', 'dist/review/_cache')
VARS = ('full', 'kfix', 'dfix')
FIELDS = ('opt', 'obs', 'gap', 'unmet')


def build():
    Y = {y: S.Year(y) for y in YEARS}
    allkeys = sorted({k for y in YEARS for k in Y[y].key})
    kidx = {k: n for n, k in enumerate(allkeys)}
    for y in YEARS:
        Y[y].kv = np.array([kidx[k] for k in Y[y].key])
    return Y, len(allkeys)


def solve_all(Y, w):
    row = {}
    for y in YEARS:
        wy, one = w[Y[y].kv], np.ones(len(Y[y].key))
        for v, args in (('full', (wy, wy, wy)), ('kfix', (wy, one, wy)), ('dfix', (one, wy, wy))):
            r = S.gap_parts(Y[y], *args)
            row[(v, y)] = [r[f] if r['ok'] else np.nan for f in FIELDS]
    return row


if sys.argv[1] == 'run':
    # Each draw is saved to its own file as soon as it finishes, so a kill loses at most the
    # draw in progress. A restart regenerates the chunk's weight sequence from the same seed
    # (the RNG must advance through every draw to stay aligned) and solves only missing draws.
    ch = int(sys.argv[sys.argv.index('--chunk') + 1])
    if os.path.exists(f'{OUT}/fixed_{ch}.npy'):
        print('chunk already complete:', f'{OUT}/fixed_{ch}.npy'); sys.exit(0)
    Y, NK = build()
    rng = np.random.default_rng(SEED + 1000*ch)
    t0, done = time.time(), 0
    for b in range(CHUNKS[ch]):
        wk = rng.exponential(size=NK); wk *= NK/wk.sum()
        dst = f'{OUT}/fixed_{ch}_d{b:03d}.npy'
        if os.path.exists(dst):
            continue
        row = solve_all(Y, wk)
        A = np.array([[row[(v, y)] for y in YEARS] for v in VARS])
        np.save(dst + '.part.npy', A); os.replace(dst + '.part.npy', dst)
        done += 1
        if done % 10 == 0:
            print(f'  chunk {ch}: draw {b+1}/{CHUNKS[ch]} ({done} solved this run)  {time.time()-t0:.0f}s', flush=True)
    print(f'chunk {ch}: all {CHUNKS[ch]} draws on disk ({done} solved this run)')

else:
    def load_chunk(c):
        whole = f'{OUT}/fixed_{c}.npy'                       # written by an end-of-chunk run
        if os.path.exists(whole):
            return np.load(whole)
        parts = [f'{OUT}/fixed_{c}_d{b:03d}.npy' for b in range(CHUNKS[c])]
        missing = [p for p in parts if not os.path.exists(p)]
        assert not missing, f'chunk {c}: {len(missing)} draws missing, rerun it'
        return np.stack([np.load(p) for p in parts])
    A = np.concatenate([load_chunk(c) for c in sorted(CHUNKS)])
    P = np.concatenate([np.load(f) for f in sorted(glob.glob(os.environ.get('BOOT_FIXED_REF', 'paper/_boot_paired') + '/draws_*.npy'))])
    Y, NK = build()
    point = {}
    for y in YEARS:
        one = np.ones(len(Y[y].key)); r = S.gap_parts(Y[y], one, one, one)
        point[y] = {f: r[f] for f in FIELDS}
    gi = FIELDS.index('gap')
    diff = np.nanmax(np.abs(A[:, 0, :, gi] - P))
    lines = [f'Paired bootstrap, kappa fixed and demand fixed. {len(A)} draws (paper weights, '
             f'seeds 20260807 + 1000*chunk). Source md5 of scripts/bootstrap_paired.py {S.SRC_MD5}.',
             f'Reproduction check: max |full-variant gap - cached paper draw| = {diff:.2e} over '
             f'{np.isfinite(A[:, 0, :, gi]).sum()} draw-years.', '',
             'opt = optimal travel over served cases (the bootstrap\'s definition); '
             'gap = (obs - opt)/obs; unmet = share of demand left unserved.', '']
    res = {'draws': int(len(A)), 'reproduction_max_abs_diff': float(diff), 'point': point, 'variants': {}}
    hdr = f"{'year':6s}{'variant':9s}{'mean opt':>10s}{'sd':>8s}{'mean obs':>10s}{'mean gap':>10s}{'sd':>8s}{'2.5%':>8s}{'97.5%':>8s}{'shift':>8s}{'unmet':>8s}{'n':>5s}"
    lines += [hdr]
    for k, y in enumerate(YEARS):
        p = point[y]
        lines.append(f"{y:6s}{'point':9s}{p['opt']:>10.4f}{'':>8s}{p['obs']:>10.4f}{p['gap']*100:>9.2f}%{'':>8s}{'':>8s}{'':>8s}{'':>8s}{p['unmet']*100:>7.2f}%{1:>5d}")
        for i, v in enumerate(VARS):
            M = A[:, i, k]; ok = np.isfinite(M).all(axis=1); M = M[ok]
            o, ob, g, u = (M[:, j] for j in range(4))
            lo, hi = np.quantile(g, [0.025, 0.975])
            res['variants'].setdefault(v, {})[y] = dict(
                mean_opt=float(o.mean()), sd_opt=float(o.std(ddof=1)), mean_obs=float(ob.mean()),
                mean_gap=float(g.mean()), sd_gap=float(g.std(ddof=1)), pct_lo=float(lo), pct_hi=float(hi),
                shift_vs_point=float(g.mean()-p['gap']), mean_unmet=float(u.mean()), n=int(ok.sum()))
            r = res['variants'][v][y]
            lines.append(f"{'':6s}{v:9s}{r['mean_opt']:>10.4f}{r['sd_opt']:>8.4f}{r['mean_obs']:>10.4f}"
                         f"{r['mean_gap']*100:>9.2f}%{r['sd_gap']*100:>7.2f}{lo*100:>8.2f}{hi*100:>8.2f}"
                         f"{r['shift_vs_point']*100:>+7.2f}p{r['mean_unmet']*100:>7.2f}%{r['n']:>5d}")
        lines.append('')
    lines.append('shift = mean bootstrap gap minus point gap, in percentage points.')
    txt = '\n'.join(lines)
    print(txt)
    open(f'dist/review/boot_fixed{TAG}.txt', 'w').write(txt + '\n')
    json.dump(res, open(f'dist/review/boot_fixed{TAG}.json', 'w'), indent=1)
    print(f'\n-> dist/review/boot_fixed{TAG}.txt/json')

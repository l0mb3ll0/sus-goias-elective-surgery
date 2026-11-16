"""Is the undisclosed low-base exclusion doing any work?

Sections 3.2 and 3.4 report facility-level results on subsets of the 61-facility
reliable set, 49 and 54 respectively. Both drops come from an unstated second
rule: exclude facilities averaging under five elective cases per month in the
relevant base window, because a growth ratio on a denominator of one or two
cases is noise. This recomputes both findings on the full 61 so the rule can be
disclosed alongside evidence about whether it matters.

Reliable subset (Section 2.3): >=95 per cent of months reported within a span of
>=60 months, and >=500 elective cases over the panel.

    python -m scripts.subset_sensitivity [--write]
"""
import io, json, sys
import numpy as np, pandas as pd

NJ = 'paper/numbers.json'
LOWBASE = 5.0
W = {'a_2021H2': ('2021-08', '2022-02'),   # 3.2 first-step base
     'b_2022Q2': ('2022-03', '2022-07'),   # 3.2 first-step target / second-step base
     'c_2022H2': ('2022-08', '2023-01'),   # 3.2 second-step target
     'pre_34':   ('2022-01', '2022-07'),   # 3.4 denominator
     'post_34':  ('2022-08', '2023-06')}   # 3.4 numerator

pan = pd.read_parquet('data/interim/hospital_panel.parquet')
pan['any'] = (pan['elec'] + pan['urg']) > 0
span = pan[pan['any']].groupby('CNES')['COMPETENCIA'].agg(['min', 'max', 'count'])
span['n'] = (pd.PeriodIndex(span['max'], freq='M').asi8
             - pd.PeriodIndex(span['min'], freq='M').asi8 + 1)
vol = pan.groupby('CNES')['elec'].sum()
rel = sorted(c for c in span[(span['count']/span['n'] >= .95) & (span['n'] >= 60)].index
             if vol.get(c, 0) >= 500)
sub = pan[pan.CNES.isin(rel)]
m = {k: sub[sub.COMPETENCIA.between(*v)].groupby('CNES')['elec'].mean().reindex(rel).fillna(0)
     for k, v in W.items()}
print(f'reliable subset: {len(rel)} facilities')

# ---------------- (a) Section 3.2, wave separation ----------------
def waves(keep):
    a, b, c = m['a_2021H2'][keep], m['b_2022Q2'][keep], m['c_2022H2'][keep]
    s1 = (b/a.replace(0, np.nan))
    s2 = (c/b.replace(0, np.nan))
    ok = s1.notna() & s2.notna()
    mv1, mv2 = s1 > 1.3, s2 > 1.3
    return {'n': len(keep), 'n_defined': int(ok.sum()),
            'first_only': int((mv1 & ~mv2 & ok).sum()), 'second_only': int((~mv1 & mv2 & ok).sum()),
            'both': int((mv1 & mv2 & ok).sum()), 'neither': int((~mv1 & ~mv2 & ok).sum()),
            'undefined': int((~ok).sum()),
            'pearson': float(s1[ok].corr(s2[ok])),
            'log': float(np.log(s1[ok].replace(0, np.nan)).corr(np.log(s2[ok].replace(0, np.nan)))),
            'spearman': float(s1[ok].corr(s2[ok], method='spearman'))}

keep32 = [c for c in rel if m['a_2021H2'][c] >= LOWBASE]
w_all, w_sub = waves(rel), waves(keep32)
print(f"\n(a) Section 3.2 wave separation, threshold {LOWBASE:g} cases/mo on {W['a_2021H2'][0]}..{W['a_2021H2'][1]}")
print(f"{'':22s}{'all 61':>12s}{'reported 49':>14s}")
for k in ['n', 'n_defined', 'first_only', 'second_only', 'both', 'neither', 'undefined']:
    print(f'  {k:20s}{w_all[k]:>12d}{w_sub[k]:>14d}')
for k in ['pearson', 'log', 'spearman']:
    print(f'  {k:20s}{w_all[k]:>12.3f}{w_sub[k]:>14.3f}')

# ---------------- (b) Section 3.4, dispersion ----------------
def disp(keep):
    g = (m['post_34'][keep] / m['pre_34'][keep].replace(0, np.nan)).dropna()
    bins = [0, 0.5, 1, 1.5, 2, 3, np.inf]
    h = pd.cut(g, bins, right=False).value_counts().sort_index()
    return {'n': int(len(g)), 'median': float(g.median()), 'mean': float(g.mean()),
            'max': float(g.max()), 'not_growing': int((g <= 1).sum()),
            'above_2x': int((g > 2).sum()), 'above_3x': int((g > 3).sum()),
            'share_below_1': float((g < 1).mean()),
            'bins': {str(i): int(v) for i, v in h.items()}}

keep34 = [c for c in rel if m['pre_34'][c] >= LOWBASE]
d_all, d_sub = disp(rel), disp(keep34)
print(f"\n(b) Section 3.4 dispersion, threshold {LOWBASE:g} cases/mo on {W['pre_34'][0]}..{W['pre_34'][1]}")
print(f"{'':22s}{'all 61':>12s}{'reported 54':>14s}")
for k in ['n', 'median', 'mean', 'max', 'not_growing', 'above_2x', 'above_3x', 'share_below_1']:
    va, vs = d_all[k], d_sub[k]
    fmt = (lambda v: f'{v:>12.3f}') if isinstance(va, float) else (lambda v: f'{v:>12d}')
    print(f'  {k:20s}{fmt(va)}{fmt(vs).strip():>14s}')
print('  histogram bins (growth ratio):')
for b in d_all['bins']:
    print(f"    {b:16s}{d_all['bins'][b]:>10d}{d_sub['bins'].get(b, 0):>14d}")

# ---------------- (d) split-half, independent denominators ----------------
# Section 3.7's fourth limitation notes the two growth ratios share the window
# 2022-03..2022-07, biasing their correlation downward, and says a split-half
# re-estimate "would be required, and we have not performed it". Splitting the
# shared window removes the shared denominator entirely.
SPLIT = {'b1': ('2022-03', '2022-05'), 'b2': ('2022-06', '2022-07')}
for k, v in SPLIT.items():
    m[k] = sub[sub.COMPETENCIA.between(*v)].groupby('CNES')['elec'].mean().reindex(rel).fillna(0)


def waves_split(keep):
    a, b1, b2, c = m['a_2021H2'][keep], m['b1'][keep], m['b2'][keep], m['c_2022H2'][keep]
    s1 = b1/a.replace(0, np.nan)          # first step, denominator = 2021H2
    s2 = c/b2.replace(0, np.nan)          # second step, denominator = 2022-06..07
    ok = s1.notna() & s2.notna()
    mv1, mv2 = s1 > 1.3, s2 > 1.3
    return {'n': len(keep), 'n_defined': int(ok.sum()),
            'first_only': int((mv1 & ~mv2 & ok).sum()), 'second_only': int((~mv1 & mv2 & ok).sum()),
            'both': int((mv1 & mv2 & ok).sum()), 'neither': int((~mv1 & ~mv2 & ok).sum()),
            'pearson': float(s1[ok].corr(s2[ok])),
            'log': float(np.log(s1[ok].replace(0, np.nan)).corr(np.log(s2[ok].replace(0, np.nan)))),
            'spearman': float(s1[ok].corr(s2[ok], method='spearman'))}


print(f"\n(d) split-half: first step uses {SPLIT['b1'][0]}..{SPLIT['b1'][1]} as numerator, "
      f"second step uses {SPLIT['b2'][0]}..{SPLIT['b2'][1]} as denominator")
sp = {'all 61': waves_split(rel), 'reported 49': waves_split(keep32), 'the 54': waves_split(keep34)}
print(f"{'':22s}" + ''.join(f'{k:>14s}' for k in sp))
for f in ['n_defined', 'first_only', 'second_only', 'both', 'neither']:
    print(f'  {f:20s}' + ''.join(f'{sp[k][f]:>14d}' for k in sp))
for f in ['pearson', 'log', 'spearman']:
    print(f'  {f:20s}' + ''.join(f'{sp[k][f]:>14.3f}' for k in sp))
out_split = sp

# ---------------- (c) volume shares ----------------
tot = float(pan['elec'].sum())
shares = {'rel_61': float(vol.reindex(rel).sum()/tot),
          'sub_54': float(vol.reindex(keep34).sum()/tot),
          'sub_49': float(vol.reindex(keep32).sum()/tot)}
print('\n(c) share of all elective surgical volume')
for k, v in shares.items():
    print(f'  {k:8s}{v*100:>8.1f}%')

stored = json.load(io.open(NJ, encoding='utf-8'))
g_stored = stored['growth']
print(f"\nregression check against numbers.json growth (the 54-subset):")
for k, sk in [('n', 'n'), ('median', 'median'), ('mean', 'mean'), ('max', 'max'),
              ('share_below_1', 'share_below_1')]:
    ok = abs(d_sub[k] - g_stored[sk]) < (1e-3 if isinstance(d_sub[k], float) else 0.5)
    print(f'  {k:16s} recomputed {d_sub[k]:<10.3f} stored {g_stored[sk]:<10.3f} {"OK" if ok else "MISMATCH"}')

out = {'low_base_threshold': LOWBASE, 'reliable_n': len(rel),
       'windows': {k: list(v) for k, v in W.items()},
       'waves_all61': w_all, 'waves_reported49': w_sub,
       'dispersion_all61': d_all, 'dispersion_reported54': d_sub,
       'volume_shares': shares, 'split_half': out_split}
# `growth` was an orphan: nothing recomputed it. disp() already does, on the
# same 54-facility subset the paper reports, so this script owns it.
growth_out = {k: d_sub[k] for k in
              ('n', 'median', 'mean', 'max', 'not_growing', 'above_2x', 'above_3x',
               'share_below_1')}
growth_out['subset'] = 'reliable 61 with >=5 elective cases/mo in 2022-01..2022-07'
if '--write' in sys.argv:
    stored['subset_sensitivity'] = out
    stored['growth'] = {**stored.get('growth', {}), **growth_out}
    json.dump(stored, io.open(NJ, 'w', encoding='utf-8'), indent=1)
    print('\nwritten', NJ)

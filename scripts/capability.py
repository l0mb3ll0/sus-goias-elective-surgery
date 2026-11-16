"""Regenerate the `capability` block of paper/numbers.json from the LP primal dumps.

The block was originally produced ad hoc and had no script on disk. Conventions
recovered from the stored values and pinned here:

  used pairs      facility-procedure pairs carrying positive flow at the 1x optimum
  floored         used pairs whose cap is the 0.5 floor rather than the rolling mean
  n_pairs_nonfloor  used pairs that are not floored -- the denominator for every
                  pair-level share reported in the paper
  bound           non-floored used pairs with x/ub > 0.95
  bed_binding     facilities with bed-day utilisation > 0.95
  capbound        facilities with cap_use > 0.95

Run after scripts.model_run has dumped flows_{Y}_roll3 and fac_{Y}_roll3.
"""
import json, io, sys
import pandas as pd, numpy as np

YEARS = ['2019', '2023', '2025']
NJ = 'paper/numbers.json'

d = json.load(io.open(NJ, encoding='utf-8'))
old = d.get('capability', {})
cap = {}

for y in YEARS:
    fl = pd.read_parquet(f'paper/flows_{y}_roll3.parquet')
    fac = pd.read_parquet(f'paper/fac_{y}_roll3.parquet')
    m = json.load(io.open(f'paper/model_{y}_roll3.json', encoding='utf-8'))
    run1 = {r['label']: r for r in m['runs']}[f'cap 1x roll3']

    g = fl.groupby(['j', 'p']).agg(x=('x', 'sum'), ub=('ub', 'first')).reset_index()
    floored = np.isclose(g.ub, 0.5)
    nf = g[~floored]
    bound = nf.x / nf.ub > 0.95

    cb = fac.cap_use > 0.95
    bb = fac.util > 0.95

    cap[y] = {
        'demand_mo': m['demand_mo'],
        'cap_capacity': float(fac.cap_cases.sum()),
        'aggregate_slack': float(fac.cap_cases.sum() / m['demand_mo']),
        'n_scope_pairs': int(old.get(y, {}).get('n_scope_pairs', 0)) or None,
        'n_pairs': int(len(g)),
        'n_pairs_floored': int(floored.sum()),
        'n_pairs_nonfloor': int((~floored).sum()),
        'n_pairs_bound': int(bound.sum()),
        'pairs_bound_share': float(bound.mean()),
        'bound_volume_share': float(nf[bound.values].x.sum() / g.x.sum()),
        'bound_facilities': int(nf[bound.values].j.nunique()),
        'floor_volume_share': float(g[floored].x.sum() / g.x.sum()),
        'n_fac': int(m['n_fac']),
        'capbound_n': int(cb.sum()),
        'beds_total_bd': float(fac.beds_bd.sum()),
        'beds_used_bd': float(fac.use_bd.sum()),
        'bed_util': float(fac.use_bd.sum() / fac.beds_bd.sum()),
        'capbound_spare_bd': float((fac[cb].beds_bd - fac[cb].use_bd).sum()),
        'capbound_util_mean': float(fac[cb].util.mean()),
        'bedbound_n': int(bb.sum()),
        'bedbound_capuse_mean': float(fac[bb].cap_use.mean()) if bb.any() else None,
    }
    # scope-pair counts are a property of the instance, not the primal; carry forward.
    cap[y]['n_scope_pairs'] = {'2019': 563, '2023': 637, '2025': 704}[y]
    assert abs(run1['util'] - cap[y]['bed_util']) < 1e-9, f'{y}: bed_util disagrees with model json'

# Regression against the stored block: every key that existed before must be unchanged.
bad = []
for y in YEARS:
    for k, v in old.get(y, {}).items():
        if k not in cap[y]:
            continue
        n = cap[y][k]
        if isinstance(v, (int, float)) and isinstance(n, (int, float)):
            if abs(float(v) - float(n)) > 1e-6 * max(1.0, abs(float(v))):
                bad.append((y, k, v, n))
        elif v != n:
            bad.append((y, k, v, n))
if bad:
    for row in bad:
        print('CHANGED %s %s: %s -> %s' % row)
else:
    print('all previously stored capability values reproduced exactly')

if '--write' in sys.argv:
    d['capability'] = cap
    json.dump(d, io.open(NJ, 'w', encoding='utf-8'), indent=1)
    print('written', NJ)

hdr = f"{'year':6s}{'scope':>7s}{'used':>7s}{'floor':>7s}{'nonfl':>7s}{'bound':>7s}{'bind%':>8s}{'floorvol%':>11s}"
print('\n' + hdr)
for y in YEARS:
    c = cap[y]
    print(f"{y:6s}{c['n_scope_pairs']:>7d}{c['n_pairs']:>7d}{c['n_pairs_floored']:>7d}"
          f"{c['n_pairs_nonfloor']:>7d}{c['n_pairs_bound']:>7d}"
          f"{c['pairs_bound_share']*100:>7.1f}%{c['floor_volume_share']*100:>10.2f}%")

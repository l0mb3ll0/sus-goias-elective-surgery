"""Pair-cap sensitivity: how much of the capability restriction is composition?

Compares three regimes at the 1x rolling-3 cap:
  unconstrained   no capability constraint at all
  facility only   equation (4)'s facility total, pair row dropped (--nopair)
  full            both rows, as specified

The step from unconstrained to facility-only prices total throughput scarcity.
The step from facility-only to full prices portfolio rigidity: the facility
could do this many cases, but not this mix of them.

Requires model_{Y}_roll3.json and model_{Y}_roll3_nopair.json.

    python -m scripts.pair_sensitivity [--write]
"""
import json, io, sys
import pandas as pd

YEARS = ['2019', '2023', '2025']
NJ = 'paper/numbers.json'

d = json.load(io.open(NJ, encoding='utf-8'))
out = {}

for y in YEARS:
    full = json.load(io.open(f'paper/model_{y}_roll3.json', encoding='utf-8'))
    npr = json.load(io.open(f'paper/model_{y}_roll3_nopair.json', encoding='utf-8'))
    g = lambda m, l: {r['label']: r for r in m['runs']}[l]
    unc, fac, fl = g(full, 'unconstrained'), g(npr, 'cap 1x roll3'), g(full, 'cap 1x roll3')
    fac_step = unc['gap'] - fac['gap']
    pair_step = fac['gap'] - fl['gap']

    pt = pd.read_parquet(f'paper/duals_{y}_roll3.parquet')
    fc = pd.read_parquet(f'paper/fac_{y}_roll3.parquet')
    capb = set(fc[fc.cap_use > 0.95].j)
    pos = pt[pt.dual > 1e-9]

    out[y] = {
        'gap_unconstrained': unc['gap'],
        'gap_facility_only': fac['gap'],
        'gap_full': fl['gap'],
        'travel_facility_only': fac['travel'],
        'facility_step_pp': fac_step * 100,
        'pair_step_pp': pair_step * 100,
        'pair_share_of_restriction': pair_step / (fac_step + pair_step),
        'bed_binding_facility_only': fac['binding'],
        'util_facility_only': fac['util'],
        'n_pairs_positive_dual': int(len(pos)),
        'n_positive_dual_nonfloored': int((pos.kappa > 0.5001).sum()),
        'n_positive_dual_at_capped_facility': int(pos.j.isin(capb).sum()),
        'share_positive_dual_at_capped_facility': float(pos.j.isin(capb).mean()),
    }

d['pair_sensitivity'] = out
if '--write' in sys.argv:
    json.dump(d, io.open(NJ, 'w', encoding='utf-8'), indent=1)
    print('written', NJ)

print(f"{'yr':6s}{'unconstr':>10s}{'fac-only':>10s}{'full':>8s}{'fac step':>10s}{'pair step':>11s}{'pair share':>12s}")
for y in YEARS:
    o = out[y]
    print(f"{y:6s}{o['gap_unconstrained']*100:>9.1f}%{o['gap_facility_only']*100:>9.1f}%"
          f"{o['gap_full']*100:>7.1f}%{o['facility_step_pp']:>9.1f}p{o['pair_step_pp']:>10.1f}p"
          f"{o['pair_share_of_restriction']*100:>11.1f}%")
print()
for y in YEARS:
    o = out[y]
    print(f"  {y}: positive-dual pairs {o['n_pairs_positive_dual']} "
          f"({o['n_positive_dual_nonfloored']} non-floored) | "
          f"{o['share_positive_dual_at_capped_facility']*100:.0f}% sit at a facility whose total cap also binds")

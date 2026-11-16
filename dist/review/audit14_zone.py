"""Zone sensitivity (PREREG_round4.md item 14)."""
import sys, json, numpy as np
sys.path.insert(0, 'dist/review')
import audit_year as AY
out = {}
for y in ('2019', '2023', '2025'):
    for z in ('muni', 'region', 'macro'):
        Y = AY.AYear(y, zone=z); r = Y.solve(); d = dict(gap=r['gap_J'], obs=r['obs_J'], opt=r['opt'], n_cells=int(Y.nu), unmet=r['unmet']); out[f'{y}|{z}'] = d
        print(f"{y} {z:7s} gap {100*d['gap']:5.2f} obs {d['obs']:.4f} opt {d['opt']:.4f} demand cells {d['n_cells']}", flush=True)
json.dump(out, open('dist/review/audit14_zone.json', 'w'), indent=1)

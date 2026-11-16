"""Audit item 9: recode cost to region-boundary crossings c' = max(c-1,0) and rerun (PREREG_round4.md)."""
import sys, json, numpy as np
sys.path.insert(0, 'dist/review')
import audit_year as AY
out = {}
for y in ('2019', '2023', '2025'):
    for cost in ('ord', 'cross'):
        Y = AY.AYear(y, cost=cost); r = Y.solve(); fa = r['fac']/np.maximum(r['kj'], 1e-12) > 0.95; bb = r['use']/r['B'] > 0.95
        d = dict(gap=r['gap_J'], obs=r['obs_J'], opt=r['opt'], at_cap=int(fa.sum()), bed_bound=int(bb.sum()), overlap=int((fa & bb).sum()), bed_util=float(r['use'].sum()/r['B'].sum()), unmet=r['unmet'])
        out[f'{y}|{cost}'] = d; print(f"{y} {cost:5s} gap {100*d['gap']:5.2f} obs {d['obs']:.4f} opt {d['opt']:.4f} atcap {d['at_cap']:3d} bedbound {d['bed_bound']:2d} overlap {d['overlap']} util {d['bed_util']:.3f}", flush=True)
    out[f'{y}|delta_gap_pp'] = 100*(out[f'{y}|cross']['gap'] - out[f'{y}|ord']['gap'])
json.dump(out, open('dist/review/audit9_cost.json', 'w'), indent=1)

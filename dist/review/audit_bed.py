"""Final-batch item 1: no bed row and local (unshrunk) lambda. Gap = (obs - opt)/obs, obs over model facilities."""
import sys, json, numpy as np
sys.path.insert(0, 'dist/review')
import audit_year as AY
out = {}
for y in ('2019', '2023', '2025'):
    Y = AY.AYear(y); res = {}
    for name, kw in {'base': {}, 'no_bed_row': dict(B=np.full(Y.nj, 1e12)), 'local_lambda': dict(Kshrink=0.0), 'local_lambda_no_bed_row': dict(Kshrink=0.0, B=np.full(Y.nj, 1e12))}.items():
        r = Y.solve(**kw); fa = r['fac']/np.maximum(r['kj'], 1e-12) > 0.95; Bv = Y.B
        res[name] = dict(gap=r['gap_J'], unmet=r['unmet'], bed_util=float(r['use'].sum()/Y.B.sum()), bed_bound=int((r['use']/Bv > 0.95).sum()), over_budget=int((r['use'] > Bv*(1+1e-9)).sum()), at_cap=int(fa.sum()))
        print(y, name, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in res[name].items()}, flush=True)
    res['delta_pp_no_bed_row'] = 100*(res['no_bed_row']['gap'] - res['base']['gap']); res['delta_pp_local_lambda_no_bed_row'] = 100*(res['local_lambda_no_bed_row']['gap'] - res['local_lambda']['gap'])
    out[y] = res
json.dump(out, open('dist/review/audit_bed.json', 'w'), indent=1)

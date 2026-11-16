"""Final pass items 1-2: gap excluding RIDE-DF Entorno municipalities of Goias (LC 94/1998 as amended by LC 163/2018; 29 Goias municipalities), and gap with cost and zones on the 18 SES-GO health regions (5 macro-regions)."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, 'dist/review')
import audit_year as AY
ride = set(pd.read_csv('data/ref/ride_df_goias.csv', dtype=str).cod6); out = {}
cfg = {'paper': {}, 'excl_entorno': dict(exclude=ride), 'health_cost_muni_zone': dict(geo='health'), 'health_zone': dict(geo='health', zone='region'), 'health_macro_zone': dict(geo='health', zone='macro')}
for y in ('2019', '2023', '2025'):
    for name, kw in cfg.items():
        Y = AY.AYear(y, **kw); r = Y.solve(); out[f'{y}|{name}'] = dict(gap=r['gap_J'], obs=r['obs_J'], opt=r['opt'], unmet=r['unmet'], n_cells=int(Y.nu), n_fac=int(Y.nj))
        print(y, name, {k: round(v, 4) if isinstance(v, float) else v for k, v in out[f'{y}|{name}'].items()}, flush=True)
json.dump(out, open('dist/review/audit_final12.json', 'w'), indent=1)

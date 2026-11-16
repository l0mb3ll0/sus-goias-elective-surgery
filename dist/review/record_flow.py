"""RECORD-style flow of records into the analysis sample, by year (aggregates only)."""
import sys, glob, json, numpy as np, pandas as pd
sys.path.insert(0, 'dist/review')
import audit_year as AY
out = {}
for y in ('2019', '2023', '2025'):
    a = pd.concat([pd.read_parquet(f, columns=['CNES', 'PROC_REA', 'CAR_INT', 'MUNIC_RES']) for f in sorted(glob.glob(f'data/interim/sih/RDGO{y[2:]}*.parquet'))])
    n_all = len(a); sg = a[a.PROC_REA.str[:2] == '04']; el = sg[sg.CAR_INT == '01']; ins = el[el.MUNIC_RES.astype(str).str[:6].isin(AY.GO)]
    Y = AY.AYear(y); inJ = int(Y.inJ.sum()); used = int(len(Y.sel))
    out[y] = dict(all_aih=n_all, surgical_group04=len(sg), elective=len(el), elective_in_state=len(ins), excluded_other_state_or_invalid=len(el)-len(ins), at_model_facilities=inJ, in_estimated_pairs=used, facilities_in_J=int(Y.nj))
    print(y, out[y], flush=True)
json.dump(out, open('dist/review/record_flow.json', 'w'), indent=1)

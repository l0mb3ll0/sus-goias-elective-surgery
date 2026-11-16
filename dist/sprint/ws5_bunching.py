"""WS5 bunching test per dist/sprint/WS5_prereg.md. Aggregates only."""
import glob, numpy as np, pandas as pd
ref = pd.read_csv('data/ref/ibge_municipios_go.csv', dtype=str); GO = set(ref.cod6)
rng = np.random.default_rng(20261105)
rows = []
for yy in ('19','20','21','22','23','24','25'):
    a = pd.concat([pd.read_parquet(f, columns=['CNES','PROC_REA','CAR_INT','COMPETENCIA','MUNIC_RES']) for f in sorted(glob.glob(f'data/interim/sih/RDGO{yy}*.parquet'))])
    a = a[(a.PROC_REA.str[:2] == '04') & a.MUNIC_RES.astype(str).str[:6].isin(GO)]
    for name, m in (('elective', a.CAR_INT == '01'), ('urgent', a.CAR_INT != '01')):
        t = a[m].groupby(['CNES', 'COMPETENCIA']).size().unstack(fill_value=0)
        t = t.reindex(columns=sorted(a.COMPETENCIA.unique()), fill_value=0)
        t = t[(t.shape[1] == 12) & (t.mean(axis=1) >= 5)] if t.shape[1] == 12 else t.iloc[0:0]
        X = t.to_numpy(); mu = X.mean(axis=1)
        T = (X == X.max(axis=1, keepdims=True)).sum(axis=1)
        sims = rng.poisson(mu[None, :, None], size=(1000, len(mu), 12))
        Ts = (sims == sims.max(axis=2, keepdims=True)).sum(axis=2)          # 1000 x n
        nm = Ts.mean(axis=1)
        rows.append(dict(year='20'+yy, stream=name, n=len(mu), obs_T=T.mean(), null_T=nm.mean(), null_lo=np.percentile(nm, 2.5), null_hi=np.percentile(nm, 97.5),
                         obs_share_T2=(T >= 2).mean(), null_share_T2=(Ts >= 2).mean()))
d = pd.DataFrame(rows); d['excess'] = d.obs_T - d.null_T; d['above'] = d.obs_T > d.null_hi
print(d.round(3).to_string(index=False))
e, u = d[d.stream == 'elective'].set_index('year'), d[d.stream == 'urgent'].set_index('year')
ok = [y for y in e.index if e.above[y] and e.excess[y] > u.excess[y]]
print('\nyears where elective above null 97.5 AND excess > urgent excess:', ok, f'({len(ok)} of {len(e)}; rule needs >=5 of 7 and (a) in >=5)')
print('years elective above null:', int(e.above.sum()), ' urgent above null:', int(u.above.sum()))
print('VERDICT:', 'SUPPORTS truncation (rule met)' if len(ok) >= 5 and e.above.sum() >= 5 else 'NO SUPPORT (rule not met)')
d.to_csv('dist/sprint/WS5_bunching.csv', index=False)

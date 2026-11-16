import pandas as pd, numpy as np, glob, json

YEAR = '2019'
ref = pd.read_csv('data/ref/ibge_municipios_go.csv', dtype=str)
reg_im = dict(zip(ref.cod6, ref.reg_imediata))
reg_it = dict(zip(ref.cod6, ref.reg_intermediaria))
go = set(ref.cod6)

d = pd.concat([pd.read_parquet(f, columns=['CNES','PROC_REA','CAR_INT','MUNIC_RES','MUNIC_MOV','DIAS_PERM','COMPETENCIA'])
               for f in sorted(glob.glob(f'data/interim/sih/RDGO{YEAR[2:]}*.parquet'))])
d = d[(d.PROC_REA.str[:2]=='04') & (d.CAR_INT=='01')].copy()
d['i'] = d.MUNIC_RES.astype(str).str[:6]
d['p'] = d.PROC_REA.str[:4]
n0 = len(d)
d = d[d.i.isin(go)]
print(f'elective {n0}, in-state {len(d)}, dropped {n0-len(d)} ({1-len(d)/n0:.3%})')

# facility municipality = modal MUNIC_MOV
fm = d.groupby('CNES').MUNIC_MOV.agg(lambda s: s.mode().iat[0]).astype(str).str[:6]
print('facilities', len(fm), '| in GO ref', fm.isin(go).sum())

# demand
dem = d.groupby(['i','p']).size().rename('d').reset_index()
print('demand cells', len(dem), '| total', dem.d.sum())

# scope set and lambda
cell = d.groupby(['CNES','p']).DIAS_PERM.agg(['size','mean'])
pmean = d.groupby('p').DIAS_PERM.mean()
K = 30.0
lam = cell.reset_index()
lam['lam'] = (lam['size']*lam['mean'] + K*lam.p.map(pmean)) / (lam['size'] + K)
print('scope pairs (j,p)', len(lam), '| lam range', round(lam.lam.min(),2), round(lam.lam.max(),2))
print('zero-LOS cells', int((lam['mean']==0).sum()))

# capacity: surgical beds net of all non-elective-surgical bed-days
inpat = {'01','02','03','04','05','06','08','09','11','12','13','14','15','16','67','90','91','10','68','83'}
lt = pd.read_parquet('data/interim/cnes_lt_raw.parquet').copy()
lt['sus'] = pd.to_numeric(lt.QT_SUS, errors='coerce').fillna(0)
lt['co'] = lt.CODLEITO.astype(str).str.zfill(2)
lt['cm'] = lt.comp.astype(str).str[:4]
beds = lt[lt.co.isin(inpat) & (lt.cm==YEAR)].groupby(['CNES','comp']).sus.sum().groupby('CNES').mean()

allrec = pd.concat([pd.read_parquet(f, columns=['CNES','PROC_REA','CAR_INT','DIAS_PERM'])
                    for f in sorted(glob.glob(f'data/interim/sih/RDGO{YEAR[2:]}*.parquet'))])
el = (allrec.PROC_REA.str[:2]=='04') & (allrec.CAR_INT=='01')
other = allrec[~el].groupby('CNES').DIAS_PERM.sum() / 12.0
gross = beds * 30.0
B = (gross - other.reindex(gross.index).fillna(0)).clip(lower=0)
print('facilities with beds', len(B), '| B<=0 after netting', int((B<=0).sum()))
print('gross bed-days/mo', int(gross.sum()), '| net', int(B.sum()))

need = (d.groupby('CNES').DIAS_PERM.sum()/12.0)
chk = pd.DataFrame({'need':need, 'B':B}).dropna()
print('observed elective bed-days/mo', int(chk.need.sum()), '| available', int(chk.B.sum()),
      '| facilities where need>B', int((chk.need>chk.B).sum()))

out = {'year':YEAR,'n_i':dem.i.nunique(),'n_j':len(B),'n_p':dem.p.nunique(),
       'scope_pairs':len(lam),'demand_total':int(dem.d.sum()),
       'B_total':float(B.sum()),'need_total':float(chk.need.sum())}
print(json.dumps(out, indent=1))
dem.to_parquet('data/interim/model_demand.parquet')
lam[['CNES','p','lam']].to_parquet('data/interim/model_lambda.parquet')
B.rename('B').to_frame().to_parquet('data/interim/model_capacity.parquet')
fm.rename('muni').to_frame().to_parquet('data/interim/model_facmuni.parquet')
print('written')
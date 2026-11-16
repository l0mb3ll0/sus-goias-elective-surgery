import pandas as pd, numpy as np, glob, json
from scipy.optimize import linprog
from scipy import sparse

YEAR='2019'
ref=pd.read_csv('data/ref/ibge_municipios_go.csv',dtype=str)
ri=dict(zip(ref.cod6,ref.reg_imediata)); rt=dict(zip(ref.cod6,ref.reg_intermediaria))

dem=pd.read_parquet('data/interim/model_demand.parquet')
lam=pd.read_parquet('data/interim/model_lambda.parquet')
fm=pd.read_parquet('data/interim/model_facmuni.parquet')

# monthly demand
dem=dem.assign(d=dem.d/12.0)

# capacity: surgical beds net of urgent surgical bed-days
inpat={'01','02','03','04','05','06','08','09','11','12','13','14','15','16','67','90','91','10','68','83'}
lt=pd.read_parquet('data/interim/cnes_lt_raw.parquet').copy()
lt['sus']=pd.to_numeric(lt.QT_SUS,errors='coerce').fillna(0)
lt['co']=lt.CODLEITO.astype(str).str.zfill(2); lt['yr']=lt.comp.astype(str).str[:4]
beds=lt[lt.co.isin(inpat)&(lt.yr==YEAR)].groupby(['CNES','comp']).sus.sum().groupby('CNES').mean()
a=pd.concat([pd.read_parquet(f,columns=['CNES','PROC_REA','CAR_INT','DIAS_PERM']) for f in sorted(glob.glob(f'data/interim/sih/RDGO{YEAR[2:]}*.parquet'))])
sg=a.PROC_REA.str[:2]=='04'
urg=a[sg&(a.CAR_INT!='01')].groupby('CNES').DIAS_PERM.sum()/12.0
B=(beds*30.0).sub(urg,fill_value=0).clip(lower=0)

J=sorted(set(lam.CNES)&set(B[B>0].index))
lam=lam[lam.CNES.isin(J)]
B=B.loc[J]
jidx={c:k for k,c in enumerate(J)}
print('facilities',len(J),'| scope pairs',len(lam))

def cost(i,j):
    mj=fm.muni.get(j)
    if mj==i: return 0.0
    if ri.get(i) and ri.get(i)==ri.get(mj): return 1.0
    if rt.get(i) and rt.get(i)==rt.get(mj): return 2.0
    return 3.0

scope={}
for _,r in lam.iterrows(): scope.setdefault(r.p,[]).append((r.CNES,r.lam))

cells=dem[dem.d>0].reset_index(drop=True)
cols=[]; c=[]; rowsA=[]; colsA=[]; valsA=[]; rowsC=[]; colsC=[]; valsC=[]
for n,r in cells.iterrows():
    for (j,lj) in scope.get(r.p,[]):
        k=len(cols); cols.append((r.i,j,r.p))
        c.append(cost(r.i,j))
        rowsA.append(n); colsA.append(k); valsA.append(1.0)
        rowsC.append(jidx[j]); colsC.append(k); valsC.append(lj)
nx=len(cols); nu=len(cells)
PI=float(np.percentile([x for x in c],95))+3.0
print('x vars',nx,'| demand cells',nu,'| pi',PI)

A=sparse.coo_matrix((valsA+[1.0]*nu,(rowsA+list(range(nu)),colsA+list(range(nx,nx+nu)))),shape=(nu,nx+nu))
C=sparse.coo_matrix((valsC,(rowsC,colsC)),shape=(len(J),nx+nu))
obj=np.array(c+[PI]*nu)
res=linprog(obj,A_ub=C,b_ub=B.values,A_eq=A,b_eq=cells.d.values,bounds=(0,None),method='highs')
print(res.status,res.message)

x=res.x[:nx]; u=res.x[nx:]
served=x.sum(); unmet=u.sum()
opt_travel=float(np.dot(c,x))
print(f'demand/mo {cells.d.sum():.0f} | served {served:.0f} | unmet {unmet:.1f}')
print(f'optimal mean travel cost {opt_travel/served:.4f}')

# observed
d0=pd.concat([pd.read_parquet(f,columns=['CNES','PROC_REA','CAR_INT','MUNIC_RES']) for f in sorted(glob.glob(f'data/interim/sih/RDGO{YEAR[2:]}*.parquet'))])
d0=d0[(d0.PROC_REA.str[:2]=='04')&(d0.CAR_INT=='01')].copy()
d0['i']=d0.MUNIC_RES.astype(str).str[:6]
d0=d0[d0.i.isin(set(ref.cod6))&d0.CNES.isin(J)]
obs=np.mean([cost(r.i,r.CNES) for r in d0.itertuples()])
print(f'observed mean travel cost {obs:.4f} (n={len(d0)})')
print(f'gap {(obs-opt_travel/served)/obs:.1%}')

use=pd.Series(0.0,index=J)
for k,(i,j,p) in enumerate(cols): use[j]+=x[k]*dict(scope[p])[j]
sl=pd.DataFrame({'used':use,'B':B}); sl['u']=sl.used/sl.B
print('facilities at >95pct bed-day capacity:',int((sl.u>0.95).sum()),'of',len(J))
print('mean utilisation',round(sl.used.sum()/sl.B.sum(),3))
json.dump({'year':YEAR,'demand_mo':float(cells.d.sum()),'served':float(served),'unmet':float(unmet),
           'travel_opt':opt_travel/served,'travel_obs':float(obs),
           'binding_facilities':int((sl.u>0.95).sum()),'mean_util':float(sl.used.sum()/sl.B.sum())},
          open('paper/model_2019.json','w'),indent=1)
print('written paper/model_2019.json')
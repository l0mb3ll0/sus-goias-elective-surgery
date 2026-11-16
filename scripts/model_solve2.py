import pandas as pd, numpy as np, glob, json
from scipy.optimize import linprog
from scipy import sparse

YEAR='2019'
ref=pd.read_csv('data/ref/ibge_municipios_go.csv',dtype=str)
ri=dict(zip(ref.cod6,ref.reg_imediata)); rt=dict(zip(ref.cod6,ref.reg_intermediaria))
GO=set(ref.cod6)

dem=pd.read_parquet('data/interim/model_demand.parquet')
lam=pd.read_parquet('data/interim/model_lambda.parquet')
fm=pd.read_parquet('data/interim/model_facmuni.parquet')
dem=dem.assign(d=dem.d/12.0)

inpat={'01','02','03','04','05','06','08','09','11','12','13','14','15','16','67','90','91','10','68','83'}
lt=pd.read_parquet('data/interim/cnes_lt_raw.parquet').copy()
lt['sus']=pd.to_numeric(lt.QT_SUS,errors='coerce').fillna(0)
lt['co']=lt.CODLEITO.astype(str).str.zfill(2); lt['yr']=lt.comp.astype(str).str[:4]
beds=lt[lt.co.isin(inpat)&(lt.yr==YEAR)].groupby(['CNES','comp']).sus.sum().groupby('CNES').mean()

a=pd.concat([pd.read_parquet(f,columns=['CNES','PROC_REA','CAR_INT','DIAS_PERM','COMPETENCIA','MUNIC_RES'])
             for f in sorted(glob.glob(f'data/interim/sih/RDGO{YEAR[2:]}*.parquet'))])
sg=a.PROC_REA.str[:2]=='04'
urg=a[sg&(a.CAR_INT!='01')].groupby('CNES').DIAS_PERM.sum()/12.0
B=(beds*30.0).sub(urg,fill_value=0).clip(lower=0)

el=a[sg&(a.CAR_INT=='01')].copy(); el['p']=el.PROC_REA.str[:4]; el['i']=el.MUNIC_RES.astype(str).str[:6]
# observed monthly peak by (facility, procedure) and by facility
peak_jp=el.groupby(['CNES','p','COMPETENCIA']).size().groupby(['CNES','p']).max()
peak_j=el.groupby(['CNES','COMPETENCIA']).size().groupby('CNES').max()

J=sorted(set(lam.CNES)&set(B[B>0].index)); lam=lam[lam.CNES.isin(J)]; B=B.loc[J]
jidx={c:k for k,c in enumerate(J)}

def cost(i,j):
    mj=fm.muni.get(j)
    if mj==i: return 0.0
    if ri.get(i) and ri.get(i)==ri.get(mj): return 1.0
    if rt.get(i) and rt.get(i)==rt.get(mj): return 2.0
    return 3.0

scope={}
for _,r in lam.iterrows(): scope.setdefault(r.p,[]).append((r.CNES,r.lam))
cells=dem[dem.d>0].reset_index(drop=True)

cols=[]; c=[]; rA=[]; cA=[]; vA=[]; rC=[]; cC=[]; vC=[]
for n,r in cells.iterrows():
    for (j,lj) in scope.get(r.p,[]):
        k=len(cols); cols.append((r.i,j,r.p)); c.append(cost(r.i,j))
        rA.append(n); cA.append(k); vA.append(1.0)
        rC.append(jidx[j]); cC.append(k); vC.append(lj)
nx=len(cols); nu=len(cells)
PI=6.0
obj=np.array(c+[PI]*nu)
A=sparse.coo_matrix((vA+[1.0]*nu,(rA+list(range(nu)),cA+list(range(nx,nx+nu)))),shape=(nu,nx+nu))
Cb=sparse.coo_matrix((vC,(rC,cC)),shape=(len(J),nx+nu))

# observed baseline
o=el[el.i.isin(GO)&el.CNES.isin(J)]
obs_travel=float(np.mean([cost(r.i,r.CNES) for r in o.itertuples()]))
obs_jp=o.groupby(['CNES','p']).size()/12.0

def solve(mult, label):
    ub=[]
    for (i,j,p) in cols:
        ub.append(np.inf if mult is None else max(mult*peak_jp.get((j,p),0.0), 0.5))
    ub=ub+[np.inf]*nu
    # facility-level session cap
    if mult is None:
        rows=[Cb]; b=[B.values]
    else:
        rS=[]; cS=[]; vS=[]
        for k,(i,j,p) in enumerate(cols): rS.append(jidx[j]); cS.append(k); vS.append(1.0)
        S=sparse.coo_matrix((vS,(rS,cS)),shape=(len(J),nx+nu))
        rows=[Cb,S]; b=[B.values, np.array([mult*peak_j.get(j,0.0) for j in J])]
    res=linprog(obj,A_ub=sparse.vstack(rows),b_ub=np.concatenate(b),A_eq=A,b_eq=cells.d.values,
                bounds=list(zip([0]*(nx+nu),ub)),method='highs')
    if res.status!=0: print(label,'FAILED',res.message); return None
    x=res.x[:nx]; u=res.x[nx:]; s=x.sum()
    t=float(np.dot(c,x))/s if s>0 else np.nan
    print(f'{label:22s} served {s:7.1f} unmet {u.sum():6.1f} travel {t:.4f} gap {(obs_travel-t)/obs_travel:+.1%}')
    return {'label':label,'served':float(s),'unmet':float(u.sum()),'travel':t,
            'gap':float((obs_travel-t)/obs_travel)}

print(f'observed mean travel {obs_travel:.4f} (n={len(o)}), demand/mo {cells.d.sum():.0f}')
out={'year':YEAR,'travel_obs':obs_travel,'demand_mo':float(cells.d.sum()),'runs':[]}
for m,lab in [(None,'unconstrained'),(3.0,'cap 3x peak'),(2.0,'cap 2x peak'),(1.5,'cap 1.5x peak'),(1.0,'cap 1x peak')]:
    r=solve(m,lab)
    if r: out['runs'].append(r)
json.dump(out,open('paper/model_2019_robust.json','w'),indent=1)
print('written')
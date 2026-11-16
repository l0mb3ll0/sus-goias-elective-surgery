import pandas as pd, numpy as np, glob, json, sys
from scipy.optimize import linprog
from scipy import sparse

ROLL=3
PI=float(sys.argv[sys.argv.index('--pi')+1]) if '--pi' in sys.argv else 6.0

ref=pd.read_csv('data/ref/ibge_municipios_go.csv',dtype=str)
ri=dict(zip(ref.cod6,ref.reg_imediata)); rt=dict(zip(ref.cod6,ref.reg_intermediaria))
GO=set(ref.cod6)
inpat={'01','02','03','04','05','06','08','09','11','12','13','14','15','16','67','90','91','10','68','83'}
lt=pd.read_parquet('data/interim/cnes_lt_raw.parquet').copy()
lt['sus']=pd.to_numeric(lt.QT_SUS,errors='coerce').fillna(0)
lt['co']=lt.CODLEITO.astype(str).str.zfill(2); lt['yr']=lt.comp.astype(str).str[:4]

def load(year):
    yy=year[2:]
    a=pd.concat([pd.read_parquet(f,columns=['CNES','PROC_REA','CAR_INT','DIAS_PERM','COMPETENCIA','MUNIC_RES','MUNIC_MOV'])
                 for f in sorted(glob.glob(f'data/interim/sih/RDGO{yy}*.parquet'))])
    sg=a.PROC_REA.str[:2]=='04'
    el=a[sg&(a.CAR_INT=='01')].copy()
    el['p']=el.PROC_REA.str[:4]; el['i']=el.MUNIC_RES.astype(str).str[:6]
    el=el[el.i.isin(GO)]
    beds=lt[lt.co.isin(inpat)&(lt.yr==year)].groupby(['CNES','comp']).sus.sum().groupby('CNES').mean()
    urg=a[sg&(a.CAR_INT!='01')].groupby('CNES').DIAS_PERM.sum()/12.0
    return el,(beds*30.0).sub(urg,fill_value=0).clip(lower=0)

def scope_of(el):
    cell=el.groupby(['CNES','p']).DIAS_PERM.agg(['size','mean'])
    pm=el.groupby('p').DIAS_PERM.mean(); K=30.0
    L=cell.reset_index(); L['lam']=(L['size']*L['mean']+K*L.p.map(pm))/(L['size']+K)
    return L[['CNES','p','lam']]

def rollmax(g,keys,roll=3):
    t=g.groupby(keys+['COMPETENCIA']).size().unstack('COMPETENCIA',fill_value=0)
    t=t.reindex(columns=sorted(g.COMPETENCIA.unique()),fill_value=0)
    if roll is None: return t.max(axis=1)
    return t.T.rolling(roll,min_periods=roll).mean().max()

def run(el_dem, B, lam, peaks_from, label, mult=1.0):
    """el_dem supplies demand+geography; lam supplies options; peaks_from supplies capability caps."""
    fm=el_dem.groupby('CNES').MUNIC_MOV.agg(lambda s:s.mode().iat[0]).astype(str).str[:6]
    fm2=peaks_from.groupby('CNES').MUNIC_MOV.agg(lambda s:s.mode().iat[0]).astype(str).str[:6]
    fm=fm2.combine_first(fm)
    dem=(el_dem.groupby(['i','p']).size()/12.0).rename('d').reset_index()
    pjp=rollmax(peaks_from,['CNES','p'],ROLL)
    pj=rollmax(peaks_from,['CNES'],ROLL)
    J=sorted(set(lam.CNES)&set(B[B>0].index)); L=lam[lam.CNES.isin(J)]; Bv=B.loc[J]
    jidx={c:k for k,c in enumerate(J)}
    def cost(i,j):
        mj=fm.get(j)
        if mj==i: return 0.0
        if ri.get(i) and ri.get(i)==ri.get(mj): return 1.0
        if rt.get(i) and rt.get(i)==rt.get(mj): return 2.0
        return 3.0
    scope={}
    for _,r in L.iterrows(): scope.setdefault(r.p,[]).append((r.CNES,r.lam))
    cells=dem[dem.d>0].reset_index(drop=True)
    noopt=float(cells[~cells.p.isin(scope)].d.sum())
    cols=[];c=[];rA=[];cA=[];vA=[];rC=[];cC=[];vC=[];rS=[];cS=[];vS=[]
    rP=[];cP=[];vP=[];pidx={}
    for n,r in cells.iterrows():
        for (j,lj) in scope.get(r.p,[]):
            k=len(cols); cols.append((r.i,j,r.p)); c.append(cost(r.i,j))
            rA.append(n); cA.append(k); vA.append(1.0)
            rC.append(jidx[j]); cC.append(k); vC.append(lj)
            rS.append(jidx[j]); cS.append(k); vS.append(1.0)
            # equation (4) caps the pair total over origins, not each origin's arc
            q=pidx.setdefault((j,r.p),len(pidx)); rP.append(q); cP.append(k); vP.append(1.0)
    nx=len(cols); nu=len(cells); npair=len(pidx)
    obj=np.array(c+[PI]*nu)
    A=sparse.coo_matrix((vA+[1.0]*nu,(rA+list(range(nu)),cA+list(range(nx,nx+nu)))),shape=(nu,nx+nu))
    Cb=sparse.coo_matrix((vC,(rC,cC)),shape=(len(J),nx+nu))
    Sc=sparse.coo_matrix((vS,(rS,cS)),shape=(len(J),nx+nu))
    Pb=sparse.coo_matrix((vP,(rP,cP)),shape=(npair,nx+nu))
    pair_keys=sorted(pidx,key=pidx.get)
    ub=[np.inf]*(nx+nu)
    # Only the pair cap is floored. model_run.py does not floor the facility
    # total and equation (4) does not either; flooring it here was the source of
    # the 0.594 against 0.595 discrepancy between Table 3 and Table 2.
    bub=np.concatenate([Bv.values,np.array([mult*pj.get(j,0.0) for j in J]),
                        np.array([max(mult*pjp.get(k,0.0),0.5) for k in pair_keys])])
    res=linprog(obj,A_ub=sparse.vstack([Cb,Sc,Pb]),b_ub=bub,A_eq=A,b_eq=cells.d.values,
                bounds=list(zip([0]*(nx+nu),ub)),method='highs')
    if res.status!=0:
        print(f'{label:38s} FAILED {res.message[:45]}'); return {'label':label,'status':'failed'}
    x=res.x[:nx]; u=res.x[nx:]; s=x.sum(); un=float(u.sum()); tot=float(cells.d.sum())
    t=float(np.dot(c,x))/s
    tadj=(float(np.dot(c,x))+PI*un)/tot
    print(f'{label:38s} opt {t:.4f}  adj {tadj:.4f}  served {s:7.1f}  unmet {un:6.1f} ({un/tot:5.1%})  scope {len(L):4d}')
    return {'label':label,'travel_opt':t,'travel_adj':tadj,'served':float(s),'unmet':un,
            'unmet_share':un/tot,'demand_total':tot,'unmet_no_option':noopt,'scope_pairs':int(len(L))}

el19,B19=load('2019'); el23,B23=load('2023')
s19=scope_of(el19); s23=scope_of(el23)

def obs_travel(el):
    fm=el.groupby('CNES').MUNIC_MOV.agg(lambda s:s.mode().iat[0]).astype(str).str[:6]
    def cost(i,j):
        mj=fm.get(j)
        if mj==i: return 0.0
        if ri.get(i) and ri.get(i)==ri.get(mj): return 1.0
        if rt.get(i) and rt.get(i)==rt.get(mj): return 2.0
        return 3.0
    return float(np.mean([cost(r.i,r.CNES) for r in el.itertuples()]))

o19=obs_travel(el19); o23=obs_travel(el23)
print(f'cap rule: roll={ROLL} | pi={PI}')
print(f'observed 2019 {o19:.4f} | observed 2023 {o23:.4f}\n')

out={'cap_roll':ROLL,'pi':PI,'obs_2019':o19,'obs_2023':o23,'runs':[]}
out['runs'].append(run(el19,B19,s19,el19,'A. 2019 demand, 2019 options'))
out['runs'].append(run(el23,B19,s19,el19,'B. 2023 demand, 2019 options+caps'))
out['runs'].append(run(el23,B23,s19,el23,'C. 2023 demand, 2019 options, 23 cap'))
out['runs'].append(run(el23,B23,s23,el23,'D. 2023 demand, 2023 options'))
suffix=('' if ROLL is None else f'_roll{ROLL}') + ('' if PI==6.0 else f'_pi{PI:g}')
json.dump(out,open(f'paper/model_decomp{suffix}.json','w'),indent=1)
print(f'\nwritten paper/model_decomp{suffix}.json')
import pandas as pd, numpy as np, glob, json, sys

ARCBOUND = '--arcbound' in sys.argv
from scipy.optimize import linprog
from scipy import sparse

ref = pd.read_csv('data/ref/ibge_municipios_go.csv', dtype=str)
ri = dict(zip(ref.cod6, ref.reg_imediata)); rt = dict(zip(ref.cod6, ref.reg_intermediaria))
GO = set(ref.cod6)
inpat = {'01','02','03','04','05','06','08','09','11','12','13','14','15','16','67','90','91','10','68','83'}
lt = pd.read_parquet('data/interim/cnes_lt_raw.parquet').copy()
lt['sus'] = pd.to_numeric(lt.QT_SUS, errors='coerce').fillna(0)
lt['co'] = lt.CODLEITO.astype(str).str.zfill(2); lt['yr'] = lt.comp.astype(str).str[:4]

def load(year):
    yy = year[2:]
    a = pd.concat([pd.read_parquet(f, columns=['CNES','PROC_REA','CAR_INT','DIAS_PERM','COMPETENCIA','MUNIC_RES','MUNIC_MOV'])
                   for f in sorted(glob.glob(f'data/interim/sih/RDGO{yy}*.parquet'))])
    sg = a.PROC_REA.str[:2] == '04'
    el = a[sg & (a.CAR_INT == '01')].copy()
    el['p'] = el.PROC_REA.str[:4]; el['i'] = el.MUNIC_RES.astype(str).str[:6]
    el = el[el.i.isin(GO)]
    beds = lt[lt.co.isin(inpat) & (lt.yr == year)].groupby(['CNES','comp']).sus.sum().groupby('CNES').mean()
    urg = a[sg & (a.CAR_INT != '01')].groupby('CNES').DIAS_PERM.sum() / 12.0
    B = (beds*30.0).sub(urg, fill_value=0).clip(lower=0)
    return el, B

def scope_of(el):
    cell = el.groupby(['CNES','p']).DIAS_PERM.agg(['size','mean'])
    pm = el.groupby('p').DIAS_PERM.mean(); K = 30.0
    L = cell.reset_index()
    L['lam'] = (L['size']*L['mean'] + K*L.p.map(pm)) / (L['size'] + K)
    return L[['CNES','p','lam']]

def solve(el, B, lam, label, mult=1.0):
    fm = el.groupby('CNES').MUNIC_MOV.agg(lambda s: s.mode().iat[0]).astype(str).str[:6]
    dem = (el.groupby(['i','p']).size() / 12.0).rename('d').reset_index()
    peak_jp = el.groupby(['CNES','p','COMPETENCIA']).size().groupby(['CNES','p']).max()
    peak_j = el.groupby(['CNES','COMPETENCIA']).size().groupby('CNES').max()
    J = sorted(set(lam.CNES) & set(B[B > 0].index)); L = lam[lam.CNES.isin(J)]; Bv = B.loc[J]
    jidx = {c: k for k, c in enumerate(J)}
    def cost(i, j):
        mj = fm.get(j)
        if mj == i: return 0.0
        if ri.get(i) and ri.get(i) == ri.get(mj): return 1.0
        if rt.get(i) and rt.get(i) == rt.get(mj): return 2.0
        return 3.0
    scope = {}
    for _, r in L.iterrows(): scope.setdefault(r.p, []).append((r.CNES, r.lam))
    cells = dem[dem.d > 0].reset_index(drop=True)
    cols=[]; c=[]; rA=[]; cA=[]; vA=[]; rC=[]; cC=[]; vC=[]; rS=[]; cS=[]; vS=[]
    rP=[]; cP=[]; vP=[]; pidx={}
    for n, r in cells.iterrows():
        for (j, lj) in scope.get(r.p, []):
            k = len(cols); cols.append((r.i, j, r.p)); c.append(cost(r.i, j))
            rA.append(n); cA.append(k); vA.append(1.0)
            rC.append(jidx[j]); cC.append(k); vC.append(lj)
            rS.append(jidx[j]); cS.append(k); vS.append(1.0)
            # equation (4) caps the pair total over origins, not each origin's arc
            q = pidx.setdefault((j, r.p), len(pidx))
            rP.append(q); cP.append(k); vP.append(1.0)
    nx = len(cols); nu = len(cells); npair = len(pidx)
    obj = np.array(c + [6.0]*nu)
    A = sparse.coo_matrix((vA+[1.0]*nu, (rA+list(range(nu)), cA+list(range(nx, nx+nu)))), shape=(nu, nx+nu))
    Cb = sparse.coo_matrix((vC, (rC, cC)), shape=(len(J), nx+nu))
    Sc = sparse.coo_matrix((vS, (rS, cS)), shape=(len(J), nx+nu))
    Pb = sparse.coo_matrix((vP, (rP, cP)), shape=(npair, nx+nu))
    pair_keys = sorted(pidx, key=pidx.get)
    if ARCBOUND:
        Aub = sparse.vstack([Cb, Sc])
        bub = np.concatenate([Bv.values, np.array([mult*peak_j.get(j, 0.0) for j in J])])
        ub = [max(mult*peak_jp.get((j, p), 0.0), 0.5) for (i, j, p) in cols] + [np.inf]*nu
    else:
        Aub = sparse.vstack([Cb, Sc, Pb])
        bub = np.concatenate([Bv.values, np.array([mult*peak_j.get(j, 0.0) for j in J]),
                              np.array([max(mult*peak_jp.get(k, 0.0), 0.5) for k in pair_keys])])
        ub = [np.inf]*(nx+nu)
    res = linprog(obj, A_ub=Aub, b_ub=bub, A_eq=A, b_eq=cells.d.values,
                  bounds=list(zip([0]*(nx+nu), ub)), method='highs')
    o = el[el.CNES.isin(J)]
    obs = float(np.mean([cost(r.i, r.CNES) for r in o.itertuples()]))
    if res.status != 0:
        print(f'{label:34s} INFEASIBLE ({res.message[:40]})'); return {'label': label, 'status': 'infeasible', 'travel_obs': obs}
    x = res.x[:nx]; u = res.x[nx:]; s = x.sum(); t = float(np.dot(c, x))/s
    print(f'{label:34s} scope {len(L):4d} served {s:7.1f} unmet {u.sum():6.1f} obs {obs:.4f} opt {t:.4f} gap {(obs-t)/obs:+.1%}')
    return {'label': label, 'scope_pairs': int(len(L)), 'served': float(s), 'unmet': float(u.sum()),
            'travel_obs': obs, 'travel_opt': t, 'gap': float((obs-t)/obs)}

el19, B19 = load('2019'); el23, B23 = load('2023')
s19 = scope_of(el19); s23 = scope_of(el23)
common = set(map(tuple, s19[['CNES','p']].values)) & set(map(tuple, s23[['CNES','p']].values))
print(f'scope 2019 {len(s19)} | 2023 {len(s23)} | common {len(common)}')
s23c = s23[[tuple(r) in common for r in s23[['CNES','p']].values]]
s19c = s19[[tuple(r) in common for r in s19[['CNES','p']].values]]

out = {'runs': []}
out['runs'].append(solve(el19, B19, s19, '2019 demand, 2019 scope'))
out['runs'].append(solve(el23, B23, s23, '2023 demand, 2023 scope'))
out['runs'].append(solve(el23, B23, s23c, '2023 demand, common scope'))
out['runs'].append(solve(el19, B19, s19c, '2019 demand, common scope'))
json.dump(out, open('paper/model_fixedscope.json', 'w'), indent=1)
print('written')
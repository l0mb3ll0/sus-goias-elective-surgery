"""Efficiency-equity frontier.

The objective minimises mean travel. A secretariat cares about the worst-served
municipality. Adding a per-municipality cap tau on mean cost and sweeping it
traces what aggregate travel must rise to bring the worst municipality under a
given threshold.

Constraint added, for each municipality i with positive demand:

    sum_{j,p} c_ij x_ijp  <=  tau * sum_p d_ip

which caps i's own mean cost at tau when all of i's demand is served. Demand is
served in full at the 1x cap in every year, so the two coincide here.

Still one LP per tau value.

    python -m scripts.equity_frontier 2025 [--write]
"""
import json, io, sys
import numpy as np, pandas as pd, glob
from scipy.optimize import linprog
from scipy import sparse

YEAR = sys.argv[1] if len(sys.argv) > 1 else '2025'
ROLL, PI, K = 3, 6.0, 30.0
TAUS = [None, 3.0, 2.75, 2.5, 2.25, 2.0, 1.9, 1.8, 1.7, 1.65, 1.6, 1.55, 1.5, 1.25, 1.0]
# Unmet demand is forced to zero. Otherwise a tighter tau is satisfied by
# dropping the expensive cells, and mean cost over served falls as tau falls:
# the served-only artifact of Section 4.2, not an equity-efficiency frontier.
YY = YEAR[2:]

ref = pd.read_csv('data/ref/ibge_municipios_go.csv', dtype=str)
ri = dict(zip(ref.cod6, ref.reg_imediata)); rt = dict(zip(ref.cod6, ref.reg_intermediaria))
nm = dict(zip(ref.cod6, ref.nome)); GO = set(ref.cod6)

a = pd.concat([pd.read_parquet(f, columns=['CNES','PROC_REA','CAR_INT','DIAS_PERM','COMPETENCIA','MUNIC_RES','MUNIC_MOV'])
               for f in sorted(glob.glob(f'data/interim/sih/RDGO{YY}*.parquet'))])
sg = a.PROC_REA.str[:2] == '04'
el = a[sg & (a.CAR_INT == '01')].copy()
el['p'] = el.PROC_REA.str[:4]; el['i'] = el.MUNIC_RES.astype(str).str[:6]
el = el[el.i.isin(GO)]

fm = el.groupby('CNES').MUNIC_MOV.agg(lambda s: s.mode().iat[0]).astype(str).str[:6]
dem = (el.groupby(['i','p']).size() / 12.0).rename('d').reset_index()
cellt = el.groupby(['CNES','p']).DIAS_PERM.agg(['size','mean'])
pmean = el.groupby('p').DIAS_PERM.mean()
lam = cellt.reset_index()
lam['lam'] = (lam['size']*lam['mean'] + K*lam.p.map(pmean)) / (lam['size'] + K)

inpat = {'01','02','03','04','05','06','08','09','11','12','13','14','15','16','67','90','91','10','68','83'}
lt = pd.read_parquet('data/interim/cnes_lt_raw.parquet').copy()
lt['sus'] = pd.to_numeric(lt.QT_SUS, errors='coerce').fillna(0)
lt['co'] = lt.CODLEITO.astype(str).str.zfill(2); lt['yr'] = lt.comp.astype(str).str[:4]
beds = lt[lt.co.isin(inpat) & (lt.yr == YEAR)].groupby(['CNES','comp']).sus.sum().groupby('CNES').mean()
urg = a[sg & (a.CAR_INT != '01')].groupby('CNES').DIAS_PERM.sum() / 12.0
B = (beds*30.0).sub(urg, fill_value=0).clip(lower=0)

def rollmax(g, keys, roll=ROLL):
    t = g.groupby(keys + ['COMPETENCIA']).size().unstack('COMPETENCIA', fill_value=0)
    t = t.reindex(columns=sorted(g.COMPETENCIA.unique()), fill_value=0)
    return t.T.rolling(roll, min_periods=roll).mean().max()

peak_jp = rollmax(el, ['CNES','p']); peak_j = rollmax(el, ['CNES'])
J = sorted(set(lam.CNES) & set(B[B > 0].index)); lam = lam[lam.CNES.isin(J)]; B = B.loc[J]
jidx = {c: k for k, c in enumerate(J)}

def cost(i, j):
    mj = fm.get(j)
    if mj == i: return 0.0
    if ri.get(i) and ri.get(i) == ri.get(mj): return 1.0
    if rt.get(i) and rt.get(i) == rt.get(mj): return 2.0
    return 3.0

scope = {}
for _, r in lam.iterrows(): scope.setdefault(r.p, []).append((r.CNES, r.lam))
cells = dem[dem.d > 0].reset_index(drop=True)
munis = sorted(cells.i.unique()); uidx = {m: k for k, m in enumerate(munis)}
dem_i = cells.groupby('i').d.sum()

cols=[]; c=[]; rA=[]; cA=[]; rC=[]; cC=[]; vC=[]; rS=[]; cS=[]; rP=[]; cP=[]; rM=[]; cM=[]; vM=[]
pidx={}
for n, r in cells.iterrows():
    for (j, lj) in scope.get(r.p, []):
        k = len(cols); cols.append((r.i, j, r.p)); cij = cost(r.i, j); c.append(cij)
        rA.append(n); cA.append(k)
        rC.append(jidx[j]); cC.append(k); vC.append(lj)
        rS.append(jidx[j]); cS.append(k)
        q = pidx.setdefault((j, r.p), len(pidx)); rP.append(q); cP.append(k)
        rM.append(uidx[r.i]); cM.append(k); vM.append(cij)
nx = len(cols); nu = len(cells); npair = len(pidx); nmun = len(munis)
c = np.array(c); obj = np.concatenate([c, np.full(nu, PI)])
pair_keys = sorted(pidx, key=pidx.get)

A = sparse.coo_matrix((np.ones(nx+nu), (np.concatenate([rA, np.arange(nu)]),
                                        np.concatenate([cA, np.arange(nx, nx+nu)]))), shape=(nu, nx+nu))
Cb = sparse.coo_matrix((vC, (rC, cC)), shape=(len(J), nx+nu))
Sc = sparse.coo_matrix((np.ones(nx), (rS, cS)), shape=(len(J), nx+nu))
Pb = sparse.coo_matrix((np.ones(nx), (rP, cP)), shape=(npair, nx+nu))
Mb = sparse.coo_matrix((vM, (rM, cM)), shape=(nmun, nx+nu))
kap = np.array([max(peak_jp.get(k, 0.0), 0.5) for k in pair_keys])
kj = np.array([peak_j.get(j, 0.0) for j in J])
dvec = np.array([dem_i[m] for m in munis])

out = {'year': YEAR, 'runs': []}
base_mean = 0.0
for tau in TAUS:
    if tau is None:
        Aub = sparse.vstack([Cb, Sc, Pb]); bub = np.concatenate([B.values, kj, kap])
    else:
        Aub = sparse.vstack([Cb, Sc, Pb, Mb])
        bub = np.concatenate([B.values, kj, kap, tau*dvec])
    lo = np.zeros(nx+nu); hi = np.concatenate([np.full(nx, np.inf), np.zeros(nu)])
    res = linprog(obj, A_ub=Aub, b_ub=bub, A_eq=A, b_eq=cells.d.values,
                  bounds=list(zip(lo, hi)), method='highs')
    if res.status != 0:
        print(f'tau {str(tau):>5s}  INFEASIBLE at full service')
        out['runs'].append({'tau': tau, 'feasible': False}); continue
    x = res.x[:nx]
    mean_cost = float(np.dot(c, x)/x.sum())
    mi = np.zeros(nmun); np.add.at(mi, [uidx[i] for (i, j, p) in cols], c*x)
    worst_i = mi/dvec
    k = int(np.argmax(worst_i))
    rise = (mean_cost/base_mean - 1)*100 if base_mean else 0.0
    print(f'tau {str(tau):>5s}  mean {mean_cost:.4f} ({rise:+5.1f}%)  worst {worst_i.max():.3f} '
          f'({nm.get(munis[k])})  munis over tau-1: {(worst_i > 1.0001).sum():3d}')
    out['runs'].append({'tau': tau, 'feasible': True, 'mean_cost': mean_cost,
                        'mean_cost_rise_pct': rise,
                        'worst_muni_cost': float(worst_i.max()), 'worst_muni': nm.get(munis[k]),
                        'n_muni_over_1': int((worst_i > 1.0001).sum())})
    if tau is None: base_mean = mean_cost

json.dump(out, io.open(f'paper/equity_{YEAR}.json', 'w', encoding='utf-8'), indent=1)
print(f'written paper/equity_{YEAR}.json')

if '--write' in sys.argv:
    NJ = 'paper/numbers.json'
    d = json.load(io.open(NJ, encoding='utf-8'))
    d.setdefault('equity_frontier', {})[YEAR] = out['runs']
    json.dump(d, io.open(NJ, 'w', encoding='utf-8'), indent=1)
    print('written', NJ)

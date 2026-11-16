"""Metric travel-cost robustness check.

Same LP as scripts/model_run.py at the 1x rolling-3 cap, with cost(i,j)
replaced by great-circle km between municipal seats. Reports both metrics
side by side. The comparable quantity is the percentage reduction, not the
level: the two costs are in different units.

    python -m scripts.model_metric 2019
"""
import pandas as pd, numpy as np, glob, json, sys
from scipy.optimize import linprog
from scipy import sparse

ROLL = 3
PI_ORD = 6.0          # penalty in region-crossings
ARCBOUND = '--arcbound' in sys.argv
YEAR = sys.argv[1] if len(sys.argv) > 1 else '2019'
YY = YEAR[2:]

ref = pd.read_csv('data/ref/ibge_municipios_go_xy.csv', dtype=str)
ri = dict(zip(ref.cod6, ref.reg_imediata)); rt = dict(zip(ref.cod6, ref.reg_intermediaria))
lat = {c: float(v) for c, v in zip(ref.cod6, ref.latitude)}
lon = {c: float(v) for c, v in zip(ref.cod6, ref.longitude)}
GO = set(ref.cod6)

a = pd.concat([pd.read_parquet(f, columns=['CNES','PROC_REA','CAR_INT','DIAS_PERM','COMPETENCIA','MUNIC_RES','MUNIC_MOV'])
               for f in sorted(glob.glob(f'data/interim/sih/RDGO{YY}*.parquet'))])
sg = a.PROC_REA.str[:2] == '04'
el = a[sg & (a.CAR_INT == '01')].copy()
el['p'] = el.PROC_REA.str[:4]; el['i'] = el.MUNIC_RES.astype(str).str[:6]
el = el[el.i.isin(GO)]

fm = el.groupby('CNES').MUNIC_MOV.agg(lambda s: s.mode().iat[0]).astype(str).str[:6]
dem = (el.groupby(['i','p']).size() / 12.0).rename('d').reset_index()

cell = el.groupby(['CNES','p']).DIAS_PERM.agg(['size','mean'])
pmean = el.groupby('p').DIAS_PERM.mean(); K = 30.0
lam = cell.reset_index()
lam['lam'] = (lam['size']*lam['mean'] + K*lam.p.map(pmean)) / (lam['size'] + K)

inpat = {'01','02','03','04','05','06','08','09','11','12','13','14','15','16','67','90','91','10','68','83'}
lt = pd.read_parquet('data/interim/cnes_lt_raw.parquet').copy()
lt['sus'] = pd.to_numeric(lt.QT_SUS, errors='coerce').fillna(0)
lt['co'] = lt.CODLEITO.astype(str).str.zfill(2); lt['yr'] = lt.comp.astype(str).str[:4]
beds = lt[lt.co.isin(inpat) & (lt.yr == YEAR)].groupby(['CNES','comp']).sus.sum().groupby('CNES').mean()
urg = a[sg & (a.CAR_INT != '01')].groupby('CNES').DIAS_PERM.sum() / 12.0
B = (beds*30.0).sub(urg, fill_value=0).clip(lower=0)

def rollmax(g, keys, roll=3):
    t = g.groupby(keys + ['COMPETENCIA']).size().unstack('COMPETENCIA', fill_value=0)
    t = t.reindex(columns=sorted(g.COMPETENCIA.unique()), fill_value=0)
    if roll is None: return t.max(axis=1)
    return t.T.rolling(roll, min_periods=roll).mean().max()

peak_jp = rollmax(el, ['CNES','p'], ROLL)
peak_j = rollmax(el, ['CNES'], ROLL)

J = sorted(set(lam.CNES) & set(B[B > 0].index)); lam = lam[lam.CNES.isin(J)]; B = B.loc[J]
jidx = {c: k for k, c in enumerate(J)}

def cost_ord(i, j):
    mj = fm.get(j)
    if mj == i: return 0.0
    if ri.get(i) and ri.get(i) == ri.get(mj): return 1.0
    if rt.get(i) and rt.get(i) == rt.get(mj): return 2.0
    return 3.0

R = 6371.0
def cost_km(i, j):
    mj = fm.get(j)
    if mj is None or i not in lat or mj not in lat: return np.nan
    p1, p2 = np.radians(lat[i]), np.radians(lat[mj])
    dp = p2 - p1; dl = np.radians(lon[mj] - lon[i])
    h = np.sin(dp/2)**2 + np.cos(p1)*np.cos(p2)*np.sin(dl/2)**2
    return float(2*R*np.arcsin(np.sqrt(h)))

scope = {}
for _, r in lam.iterrows(): scope.setdefault(r.p, []).append((r.CNES, r.lam))
cells = dem[dem.d > 0].reset_index(drop=True)
tot = float(cells.d.sum())

cols=[]; rA=[]; cA=[]; vA=[]; rC=[]; cC=[]; vC=[]; rS=[]; cS=[]; vS=[]
rP=[]; cP=[]; vP=[]; pidx={}
for n, r in cells.iterrows():
    for (j, lj) in scope.get(r.p, []):
        k = len(cols); cols.append((r.i, j, r.p))
        rA.append(n); cA.append(k); vA.append(1.0)
        rC.append(jidx[j]); cC.append(k); vC.append(lj)
        rS.append(jidx[j]); cS.append(k); vS.append(1.0)
        # equation (4) caps the pair total over origins, not each origin's arc
        q = pidx.setdefault((j, r.p), len(pidx))
        rP.append(q); cP.append(k); vP.append(1.0)
nx = len(cols); nu = len(cells); npair = len(pidx)

c_ord = np.array([cost_ord(i, j) for (i, j, p) in cols])
c_km  = np.array([cost_km(i, j) for (i, j, p) in cols])
nbad = int(np.isnan(c_km).sum())
if nbad:
    print(f'WARNING {nbad} of {nx} columns have no coordinate; filled at max')
    c_km = np.where(np.isnan(c_km), np.nanmax(c_km), c_km)

A = sparse.coo_matrix((vA+[1.0]*nu, (rA+list(range(nu)), cA+list(range(nx, nx+nu)))), shape=(nu, nx+nu))
Cb = sparse.coo_matrix((vC, (rC, cC)), shape=(len(J), nx+nu))
Sc = sparse.coo_matrix((vS, (rS, cS)), shape=(len(J), nx+nu))
Pb = sparse.coo_matrix((vP, (rP, cP)), shape=(npair, nx+nu))
pair_keys = sorted(pidx, key=pidx.get)
if ARCBOUND:
    Aub = sparse.vstack([Cb, Sc])
    bub = np.concatenate([B.values, np.array([peak_j.get(j, 0.0) for j in J])])
    ub = [max(peak_jp.get((j, p), 0.0), 0.5) for (i, j, p) in cols] + [np.inf]*nu
else:
    Aub = sparse.vstack([Cb, Sc, Pb])
    bub = np.concatenate([B.values, np.array([peak_j.get(j, 0.0) for j in J]),
                          np.array([max(peak_jp.get(k, 0.0), 0.5) for k in pair_keys])])
    ub = [np.inf]*(nx+nu)

o = el[el.CNES.isin(J)]
obs_ord = float(np.mean([cost_ord(r.i, r.CNES) for r in o.itertuples()]))
km_obs = [cost_km(r.i, r.CNES) for r in o.itertuples()]
km_obs = [v for v in km_obs if not np.isnan(v)]
obs_km = float(np.mean(km_obs))

print(f'{YEAR}: {len(o)} cases | facilities {len(J)} | cap roll{ROLL}')
print(f'observed  ordinal {obs_ord:.4f} crossings | metric {obs_km:.1f} km')

out = {'year': YEAR, 'cap_roll': ROLL, 'obs_ordinal': obs_ord, 'obs_km': obs_km, 'runs': []}
# scale the unmet penalty so it sits at the same rank position under both metrics
PI_KM = PI_ORD / 3.0 * float(np.nanmax(c_km))
for c, pi, lab, unit in [(c_ord, PI_ORD, 'ordinal', 'crossings'), (c_km, PI_KM, 'metric', 'km')]:
    obj = np.concatenate([c, np.full(nu, pi)])
    res = linprog(obj, A_ub=Aub, b_ub=bub, A_eq=A, b_eq=cells.d.values,
                  bounds=list(zip([0]*(nx+nu), ub)), method='highs')
    if res.status != 0:
        print(f'{lab:8s} FAILED {res.message[:50]}'); continue
    x = res.x[:nx]; u = res.x[nx:]; s = x.sum(); un = float(u.sum())
    t = float(np.dot(c, x))/s
    obs = obs_ord if lab == 'ordinal' else obs_km
    # cross-evaluate: what does this solution cost under the OTHER metric?
    other = c_km if lab == 'ordinal' else c_ord
    t_other = float(np.dot(other, x))/s
    print(f'{lab:8s} opt {t:8.4f} {unit:9s} gap {(obs-t)/obs:+.1%} | unmet {un/tot:.1%} | same solution scores {t_other:.4f} on the other metric')
    out['runs'].append({'metric': lab, 'opt': t, 'obs': obs, 'gap': float((obs-t)/obs),
                        'unmet_share': un/tot, 'cross_eval': t_other})

json.dump(out, open(f'paper/model_metric_{YEAR}.json', 'w'), indent=1)
print(f'written paper/model_metric_{YEAR}.json')
"""Capability placement ranking for SES-GO, plus the worst-served origin table.

For each candidate facility-procedure pair the model can price, reports what one
increment of demonstrated capability there would be worth in avoided travel, the
municipalities whose patients would be routed to it, and the bed-days it consumes
at that facility's current occupancy.

Two properties keep this defensible where an endogenous-opening MIP is not. It
never claims a pair should be opened, only what one would be worth, so the
missing pair-opening cost never enters. And the dual is only a first-order
estimate, so the top candidates are verified by exact re-solve.

Two cautions from the pair-cap sensitivity are enforced rather than noted:
  - Floored pairs are excluded. Their cap is a construct, so a high dual there
    prices the floor, not the facility.
  - Pairs at a facility whose total cap also binds are flagged. Relaxing one
    pair there moves volume within the facility instead of adding to it, so the
    dual overstates what the pair alone would buy. The exact re-solve settles it.

    python -m scripts.ses_go_package 2025 [--verify 50]
"""
import json, io, sys
import numpy as np, pandas as pd, glob
from scipy.optimize import linprog
from scipy import sparse

YEAR = sys.argv[1] if len(sys.argv) > 1 else '2025'
NVERIFY = int(sys.argv[sys.argv.index('--verify') + 1]) if '--verify' in sys.argv else 50
INC = 5.0
ROLL, PI, K = 3, 6.0, 30.0
YY = YEAR[2:]

ref = pd.read_csv('data/ref/ibge_municipios_go.csv', dtype=str)
ri = dict(zip(ref.cod6, ref.reg_imediata)); rt = dict(zip(ref.cod6, ref.reg_intermediaria))
nm = dict(zip(ref.cod6, ref.nome)); GO = set(ref.cod6)
sig = pd.read_csv('data/ref/sigtap_procedimentos.csv', dtype=str)
pname = (sig.assign(p=sig.CO_PROCEDIMENTO.str[:4]).groupby('p').subgrupo.first().to_dict()
         if 'subgrupo' in sig.columns else {})

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

cols=[]; c=[]; rA=[]; cA=[]; rC=[]; cC=[]; vC=[]; rS=[]; cS=[]; rP=[]; cP=[]
pidx={}
for n, r in cells.iterrows():
    for (j, lj) in scope.get(r.p, []):
        k = len(cols); cols.append((r.i, j, r.p)); c.append(cost(r.i, j))
        rA.append(n); cA.append(k)
        rC.append(jidx[j]); cC.append(k); vC.append(lj)
        rS.append(jidx[j]); cS.append(k)
        q = pidx.setdefault((j, r.p), len(pidx)); rP.append(q); cP.append(k)
nx = len(cols); nu = len(cells); npair = len(pidx)
c = np.array(c); obj = np.concatenate([c, np.full(nu, PI)])
pair_keys = sorted(pidx, key=pidx.get)
A = sparse.coo_matrix((np.ones(nx+nu), (np.concatenate([rA, np.arange(nu)]),
                                        np.concatenate([cA, np.arange(nx, nx+nu)]))), shape=(nu, nx+nu))
Cb = sparse.coo_matrix((vC, (rC, cC)), shape=(len(J), nx+nu))
Sc = sparse.coo_matrix((np.ones(nx), (rS, cS)), shape=(len(J), nx+nu))
Pb = sparse.coo_matrix((np.ones(nx), (rP, cP)), shape=(npair, nx+nu))
kap0 = np.array([max(peak_jp.get(k, 0.0), 0.5) for k in pair_keys])
kj = np.array([peak_j.get(j, 0.0) for j in J])
lam_map = {(r.CNES, r.p): r.lam for r in lam.itertuples()}

def solve(kap, kjv):
    Aub = sparse.vstack([Cb, Sc, Pb]); bub = np.concatenate([B.values, kjv, kap])
    res = linprog(obj, A_ub=Aub, b_ub=bub, A_eq=A, b_eq=cells.d.values, bounds=(0, None), method='highs')
    return res

base = solve(kap0, kj)
tot = float(cells.d.sum())
base_cost = float(np.dot(c, base.x[:nx]))
mg = base.ineqlin.marginals[len(J)*2:]

t = pd.DataFrame(pair_keys, columns=['j','p'])
t['kappa'] = kap0
t['dual'] = -mg
t['floored'] = np.isclose(kap0, 0.5)
fac_use = np.zeros(len(J))
xb = base.x[:nx]
for k, (i, j, p) in enumerate(cols): fac_use[jidx[j]] += xb[k]
t['fac_cap'] = [kj[jidx[j]] for j in t.j]
t['fac_served'] = [fac_use[jidx[j]] for j in t.j]
t['fac_cap_binds'] = t.fac_served > 0.95*t.fac_cap
t['value_per_month'] = t.dual * INC
t['muni'] = t.j.map(fm).map(nm)
t['subgrupo'] = t.p.map(pname)
t['bed_days_per_inc'] = [INC*lam_map.get((j, p), np.nan) for j, p in zip(t.j, t.p)]

cand = t[(~t.floored) & (t.dual > 1e-9)].sort_values('value_per_month', ascending=False).reset_index(drop=True)
print(f'{YEAR}: {len(t)} pairs | {int(t.floored.sum())} floored, excluded '
      f'| {len(cand)} priced candidates | {int(cand.fac_cap_binds.sum())} at a facility whose total cap also binds')

n = min(NVERIFY, len(cand))
print(f'verifying top {n} by exact re-solve (+{INC:.0f} cases/mo each, one at a time)...')
exact = []
for r in cand.head(n).itertuples():
    kap = kap0.copy(); kap[pidx[(r.j, r.p)]] += INC
    kjv = kj.copy(); kjv[jidx[r.j]] += INC     # capability added, not reshuffled
    res = solve(kap, kjv)
    exact.append(base_cost - float(np.dot(c, res.x[:nx])) if res.status == 0 else np.nan)
cand.loc[:n-1, 'exact_saving'] = exact
cand['dual_error'] = cand.value_per_month - cand.exact_saving

v = cand.head(n)
print(f'  dual predicted mean {v.value_per_month.mean():.3f}, exact mean {v.exact_saving.mean():.3f} '
      f'crossings/mo | correlation {v.value_per_month.corr(v.exact_saving):.3f}')
print(f'  dual overstates at {int((v.dual_error > 0.01).sum())} of {n}; '
      f'of those, {int(((v.dual_error > 0.01) & v.fac_cap_binds).sum())} are at a facility whose total cap binds')

out = cand.head(n)[['j','p','subgrupo','muni','kappa','fac_cap_binds','value_per_month',
                    'exact_saving','bed_days_per_inc']]
out.to_csv(f'paper/ses_go_placement_{YEAR}.csv', index=False)
print(f'\ntop 15 by verified saving, region-crossings avoided per month per {INC:.0f} cases:')
print(out.sort_values('exact_saving', ascending=False).head(15)
      .to_string(index=False, float_format=lambda x: f'{x:.2f}'))

rank = pd.read_csv(f'paper/flows_rank_{YEAR}_roll3.csv', dtype={'i': str})
worst = rank.nlargest(15, 'excess').copy()
fl = pd.read_parquet(f'paper/flows_{YEAR}_roll3.parquet')
dest = []
for r in worst.itertuples():
    g = fl[fl.i == r.i].groupby('muni_mov').x.sum().sort_values(ascending=False).head(3)
    dest.append('; '.join(f'{nm.get(m, m)} ({v:.0f})' for m, v in g.items()))
worst['optimal_destinations'] = dest
worst[['i','nome','obs_n','obs_c','opt_c','served','excess','optimal_destinations']].to_csv(
    f'paper/ses_go_worst_served_{YEAR}.csv', index=False)
print(f'\nwritten paper/ses_go_placement_{YEAR}.csv and paper/ses_go_worst_served_{YEAR}.csv')

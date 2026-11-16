"""Urgent-surgery capability instrument: kappa_urgent in place of kappa.

WHY. The paper's capability cap is built from realised elective volume, so
"capability binds" risks being definitional: output defined as capability, then
found to constrain output. Urgent surgical activity is exogenous to the elective
allocation process -- not scheduled, not queue-managed, not the target of the
2022 reform, PNRF or PMAE -- while running through the same theatres, teams and
billing pipeline. A facility performing urgent surgery in subgroup p
demonstrably holds the capability for p, on evidence that never touches elective
billing.

CONSTRUCTION HELD FIXED. kappa_urgent uses the identical rule as kappa: largest
three-month rolling mean of monthly volume, 0.5 floor, floored pairs excluded
from every pair-level count. The only change is the record set feeding it
(CAR_INT != '01' rather than == '01'). Deviations, all forced and logged:

  1. lambda_jp stays estimated on ELECTIVE admissions, per instruction. Urgent
     length of stay differs and re-estimating on urgent records would change the
     bed-day constraint as well as the cap, confounding the comparison. For a
     pair with no elective history the existing shrinkage formula
     (n*mean + K*pmean)/(n + K) with n = 0 returns the procedure-level elective
     mean exactly, so no new rule is needed.
  2. J expands. Facilities with urgent volume and positive net beds but no
     elective volume enter the program. That is the point of the instrument, not
     a side effect: those facilities are invisible under the elective cap.
  3. B_j is unchanged and still nets urgent bed-day consumption, so a facility
     admitted on urgent capability is still charged for the urgent work it does.

    python -m scripts.model_urgent 2019 --cap urgent|max|elective
"""
import argparse, glob, json
import numpy as np, pandas as pd
from scipy.optimize import linprog
from scipy import sparse

ROLL, PI, K = 3, 6.0, 30.0
INPAT = {'01','02','03','04','05','06','08','09','11','12','13','14','15','16',
         '67','90','91','10','68','83'}

ap = argparse.ArgumentParser()
ap.add_argument('year'); ap.add_argument('--cap', default='urgent',
                                         choices=['urgent', 'max', 'elective'])
ap.add_argument('--drop-urgent-only', action='store_true',
                help='exclude facilities with no elective volume, to isolate their share')
ap.add_argument('--intersect', action='store_true',
                help='restrict scope to pairs licensed by BOTH caps, so the two '
                     'constructions cover identical facility-procedure sets')
ap.add_argument('--urgent-instate', action='store_true',
                help='build kappa_urgent on in-state residents only, matching the '
                     'residency restriction the elective cap already carries')
ap.add_argument('--fix-obs', action='store_true',
                help='hold the observed baseline on the elective J, for comparability')
A = ap.parse_args()
YEAR, YY = A.year, A.year[2:]

ref = pd.read_csv('data/ref/ibge_municipios_go.csv', dtype=str)
ri = dict(zip(ref.cod6, ref.reg_imediata)); rt = dict(zip(ref.cod6, ref.reg_intermediaria))
GO = set(ref.cod6)

a = pd.concat([pd.read_parquet(f, columns=['CNES','PROC_REA','CAR_INT','DIAS_PERM',
                                           'COMPETENCIA','MUNIC_RES','MUNIC_MOV'])
               for f in sorted(glob.glob(f'data/interim/sih/RDGO{YY}*.parquet'))])
sg = a.PROC_REA.str[:2] == '04'
el = a[sg & (a.CAR_INT == '01')].copy()
ur = a[sg & (a.CAR_INT != '01')].copy()
for d in (el, ur):
    d['p'] = d.PROC_REA.str[:4]; d['i'] = d.MUNIC_RES.astype(str).str[:6]
el = el[el.i.isin(GO)]; ur_in = ur[ur.i.isin(GO)]

# facility municipality: from elective where known, else from urgent
fm = pd.concat([el, ur_in]).groupby('CNES').MUNIC_MOV.agg(
    lambda s: s.mode().iat[0]).astype(str).str[:6]
dem = (el.groupby(['i','p']).size()/12.0).rename('d').reset_index()   # demand: elective only

# lambda on ELECTIVE only; n=0 falls back to the procedure mean by construction
cell = el.groupby(['CNES','p']).DIAS_PERM.agg(['size','mean'])
pmean = el.groupby('p').DIAS_PERM.mean()
lam = cell.reset_index()
lam['lam'] = (lam['size']*lam['mean'] + K*lam.p.map(pmean))/(lam['size'] + K)
lam_map = {(r.CNES, r.p): r.lam for r in lam.itertuples()}

lt = pd.read_parquet('data/interim/cnes_lt_raw.parquet').copy()
lt['sus'] = pd.to_numeric(lt.QT_SUS, errors='coerce').fillna(0)
lt['co'] = lt.CODLEITO.astype(str).str.zfill(2); lt['yr'] = lt.comp.astype(str).str[:4]
beds = lt[lt.co.isin(INPAT) & (lt.yr == YEAR)].groupby(['CNES','comp']).sus.sum().groupby('CNES').mean()
urgbd = ur.groupby('CNES').DIAS_PERM.sum()/12.0
B = (beds*30.0).sub(urgbd, fill_value=0).clip(lower=0)

def rollmax(g, keys, roll=ROLL):
    t = g.groupby(keys + ['COMPETENCIA']).size().unstack('COMPETENCIA', fill_value=0)
    t = t.reindex(columns=sorted(g.COMPETENCIA.unique()), fill_value=0)
    return t.T.rolling(roll, min_periods=roll).mean().max()

# ASYMMETRY, logged. el is filtered to in-state residents at line 62, so the
# elective cap counts only in-state volume. The urgent cap defaults to all urgent
# records, which is the larger set. --urgent-instate makes the two symmetric.
uc = ur_in if A.urgent_instate else ur
pe_jp, pe_j = rollmax(el, ['CNES','p']), rollmax(el, ['CNES'])
pu_jp, pu_j = rollmax(uc, ['CNES','p']), rollmax(uc, ['CNES'])

if A.cap == 'elective':
    kap_jp, kap_j, src = pe_jp, pe_j, el
elif A.cap == 'urgent':
    kap_jp, kap_j, src = pu_jp, pu_j, uc
else:
    kap_jp = pe_jp.reindex(pe_jp.index.union(pu_jp.index), fill_value=0).combine(
        pu_jp.reindex(pe_jp.index.union(pu_jp.index), fill_value=0), max)
    kap_j = pe_j.reindex(pe_j.index.union(pu_j.index), fill_value=0).combine(
        pu_j.reindex(pe_j.index.union(pu_j.index), fill_value=0), max)
    src = pd.concat([el, uc])

scope_pairs = sorted({(j, p) for (j, p) in kap_jp.index if kap_jp[(j, p)] > 0})
elective_fac = set(el.CNES.unique())
if A.intersect:
    # Pairs both caps license. On this restriction the elective and urgent runs
    # cover identical (j,p) sets, so any difference in what binds cannot be a
    # difference in scope. Applied before the B>0 filter so both runs see it.
    both = ({k for k in pe_jp.index if pe_jp[k] > 0}
            & {k for k in pu_jp.index if pu_jp[k] > 0})
    scope_pairs = [k for k in scope_pairs if k in both]
if A.drop_urgent_only:
    scope_pairs = [(j, p) for (j, p) in scope_pairs if j in elective_fac]
Jall = sorted({j for j, _ in scope_pairs} & set(B[B > 0].index))
scope_pairs = [(j, p) for (j, p) in scope_pairs if j in Jall]
B_all = B                     # B is narrowed to Jall on the next line
B = B.loc[Jall]; jidx = {c: k for k, c in enumerate(Jall)}
scope = {}
for j, p in scope_pairs:
    scope.setdefault(p, []).append(j)
print(f'{YEAR} cap={A.cap}: |J| {len(Jall)} | scope pairs {len(scope_pairs)} '
      f'| demand/mo {dem.d.sum():.0f}')

def cost(i, j):
    mj = fm.get(j)
    if mj == i: return 0.0
    if ri.get(i) and ri.get(i) == ri.get(mj): return 1.0
    if rt.get(i) and rt.get(i) == rt.get(mj): return 2.0
    return 3.0

cells = dem[dem.d > 0].reset_index(drop=True)
cols=[]; c=[]; rA=[]; cA=[]; rC=[]; cC=[]; vC=[]; rS=[]; cS=[]; rP=[]; cP=[]; pidx={}
for n, r in cells.iterrows():
    for j in scope.get(r.p, []):
        k = len(cols); cols.append((r.i, j, r.p)); c.append(cost(r.i, j))
        rA.append(n); cA.append(k)
        rC.append(jidx[j]); cC.append(k)
        vC.append(lam_map.get((j, r.p), float(pmean[r.p])))
        rS.append(jidx[j]); cS.append(k)
        q = pidx.setdefault((j, r.p), len(pidx)); rP.append(q); cP.append(k)
nx, nu, npair = len(cols), len(cells), len(pidx)
pair_keys = sorted(pidx, key=pidx.get)
obj = np.concatenate([np.array(c), np.full(nu, PI)])
Aeq = sparse.coo_matrix((np.ones(nx+nu), (np.concatenate([rA, np.arange(nu)]),
        np.concatenate([np.arange(nx), nx+np.arange(nu)]))), shape=(nu, nx+nu))
Cb = sparse.coo_matrix((vC, (rC, cC)), shape=(len(Jall), nx+nu))
Sc = sparse.coo_matrix((np.ones(nx), (rS, cS)), shape=(len(Jall), nx+nu))
Pb = sparse.coo_matrix((np.ones(nx), (rP, cP)), shape=(npair, nx+nu))
kv = np.array([max(float(kap_jp.get(k, 0.0)), 0.5) for k in pair_keys])
jv = np.array([float(kap_j.get(j, 0.0)) for j in Jall])
res = linprog(obj, A_ub=sparse.vstack([Cb, Sc, Pb]),
              b_ub=np.concatenate([B.values, jv, kv]),
              A_eq=Aeq, b_eq=cells.d.values, bounds=(0, None), method='highs')
assert res.status == 0, res.message
x = res.x[:nx]
# The observed baseline is computed over facilities in J. J changes with the cap,
# so gaps across caps are not comparable unless the baseline is held fixed.
# --fix-obs pins it to the elective J, which is what the fixtures use.
obs_J = (sorted({j for j, q in pe_jp.index if pe_jp[(j, q)] > 0}
                & set(B_all[B_all > 0].index))
         if A.fix_obs else Jall)   # the elective-cap J, so gaps compare on one baseline
if A.fix_obs: print(f'  [fix-obs] baseline held on the elective J, {len(obs_J)} facilities')
o = el[el.CNES.isin(obs_J)]
obs = float(np.mean([cost(r.i, r.CNES) for r in o.itertuples()]))
travel = float(np.dot(c, x)/x.sum())
# Share of SERVED volume the optimum routes to facilities with no elective
# history. Reported on served volume, not on demand: unmet is large under the
# urgent cap, so a share of demand would not be interpretable.
_uo = np.array([1.0 if j not in elective_fac else 0.0 for (_i, j, _p) in cols])
uo_share = float(np.dot(_uo, x)/x.sum())
uo_vol = float(np.dot(_uo, x))
print(f'  urgent-only facilities: {len(set(Jall) - elective_fac):3d} in J | '
      f'{uo_vol:7.0f} cases/mo routed = {100*uo_share:.1f}% of served volume')
use = np.zeros(len(Jall))
for k, (i, j, p) in enumerate(cols): use[jidx[j]] += x[k]*vC[k]
util = use.sum()/B.values.sum()
served = np.zeros(npair)
for k, (i, j, p) in enumerate(cols): served[pidx[(j, p)]] += x[k]
fac_served = np.zeros(len(Jall))
for k, (i, j, p) in enumerate(cols): fac_served[jidx[j]] += x[k]
cap_use = np.divide(fac_served, jv, out=np.zeros(len(Jall)), where=jv > 0)
bedu = use/np.maximum(B.values, 1e-9)
bb, cb = bedu > 0.95, cap_use > 0.95
nf = kv > 0.5001
out = {'year': YEAR, 'cap': A.cap, 'n_fac': len(Jall), 'scope_pairs': len(scope_pairs),
       'travel_obs': obs, 'travel': travel, 'gap': (obs-travel)/obs, 'unmet': float(res.x[nx:].sum()),
       'bed_util': float(util), 'cap_capacity': float(jv.sum()), 'demand_mo': float(cells.d.sum()),
       'slack': float(jv.sum()/cells.d.sum()),
       'uo_share': uo_share, 'uo_vol': uo_vol, 'bedbound_n': int(bb.sum()), 'capbound_n': int(cb.sum()),
       'both_n': int((bb & cb).sum()),
       'bedbound_capuse_mean': float(cap_use[bb].mean()) if bb.any() else None,
       'capbound_spare_bd': float((B.values[cb]-use[cb]).sum()),
       'beds_used_bd': float(use.sum()),
       'n_pairs_nonfloor': int(nf.sum()),
       'n_pairs_bound': int(((served[nf]/kv[nf]) > 0.95).sum()),
       'both_cnes': [Jall[k] for k in np.where(bb & cb)[0]]}
print(f'  gap {out["gap"]*100:+.1f}%  travel {travel:.4f} vs obs {obs:.4f}  '
      f'bed util {util:.3f}  slack {out["slack"]:.3f}')
print(f'  bed-bound {out["bedbound_n"]}  capability-bound {out["capbound_n"]}  '
      f'BOTH {out["both_n"]} {out["both_cnes"] if out["both_n"] else ""}')
suffix = (A.cap + ('_isect' if A.intersect else '') + ('_instate' if A.urgent_instate else '')
          + ('_dropUO' if A.drop_urgent_only else '') + ('_fixobs' if A.fix_obs else ''))
json.dump(out, open(f'paper/model_urgent_{YEAR}_{suffix}.json','w'), indent=1)

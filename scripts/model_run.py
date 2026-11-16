import pandas as pd, numpy as np, glob, json, sys
from scipy.optimize import linprog
from scipy import sparse

ROLL = None if (len(sys.argv) > 2 and sys.argv[2].lower() in ('none', 'peak')) else 3
PI = 6.0
ARCBOUND = '--arcbound' in sys.argv
# Sensitivity: drop the pair row of equation (4) and keep only the facility
# total. Separates "this facility cannot do more of anything" from "this
# facility cannot do more of *this*".
NOPAIR = '--nopair' in sys.argv

YEAR = sys.argv[1] if len(sys.argv) > 1 else '2019'
YY = YEAR[2:]
ref = pd.read_csv('data/ref/ibge_municipios_go.csv', dtype=str)
ri = dict(zip(ref.cod6, ref.reg_imediata)); rt = dict(zip(ref.cod6, ref.reg_intermediaria))
GO = set(ref.cod6)

a = pd.concat([pd.read_parquet(f, columns=['CNES','PROC_REA','CAR_INT','DIAS_PERM','COMPETENCIA','MUNIC_RES','MUNIC_MOV'])
               for f in sorted(glob.glob(f'data/interim/sih/RDGO{YY}*.parquet'))])
sg = a.PROC_REA.str[:2] == '04'
el = a[sg & (a.CAR_INT == '01')].copy()
el['p'] = el.PROC_REA.str[:4]; el['i'] = el.MUNIC_RES.astype(str).str[:6]
n0 = len(el); el = el[el.i.isin(GO)]
print(f'{YEAR}: elective {n0}, in-state {len(el)}')

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
CAPLAB = 'peak' if ROLL is None else f'roll{ROLL}'

J = sorted(set(lam.CNES) & set(B[B > 0].index)); lam = lam[lam.CNES.isin(J)]; B = B.loc[J]
jidx = {c: k for k, c in enumerate(J)}
print(f'facilities {len(J)} | scope pairs {len(lam)} | demand/mo {dem.d.sum():.0f} | cap {CAPLAB} | pi {PI}')

def cost(i, j):
    mj = fm.get(j)
    if mj == i: return 0.0
    if ri.get(i) and ri.get(i) == ri.get(mj): return 1.0
    if rt.get(i) and rt.get(i) == rt.get(mj): return 2.0
    return 3.0

scope = {}
for _, r in lam.iterrows(): scope.setdefault(r.p, []).append((r.CNES, r.lam))
cells = dem[dem.d > 0].reset_index(drop=True)

cols=[]; c=[]; rA=[]; cA=[]; vA=[]; rC=[]; cC=[]; vC=[]; rS=[]; cS=[]; vS=[]
rP=[]; cP=[]; vP=[]; pidx={}
for n, r in cells.iterrows():
    for (j, lj) in scope.get(r.p, []):
        k = len(cols); cols.append((r.i, j, r.p)); c.append(cost(r.i, j))
        rA.append(n); cA.append(k); vA.append(1.0)
        rC.append(jidx[j]); cC.append(k); vC.append(lj)
        rS.append(jidx[j]); cS.append(k); vS.append(1.0)
        # Equation (4) caps the pair's total over origins, not each origin's arc.
        q = pidx.setdefault((j, r.p), len(pidx))
        rP.append(q); cP.append(k); vP.append(1.0)
nx = len(cols); nu = len(cells); npair = len(pidx)
obj = np.array(c + [PI]*nu)
A = sparse.coo_matrix((vA+[1.0]*nu, (rA+list(range(nu)), cA+list(range(nx, nx+nu)))), shape=(nu, nx+nu))
Cb = sparse.coo_matrix((vC, (rC, cC)), shape=(len(J), nx+nu))
Sc = sparse.coo_matrix((vS, (rS, cS)), shape=(len(J), nx+nu))
Pb = sparse.coo_matrix((vP, (rP, cP)), shape=(npair, nx+nu))
pair_keys = sorted(pidx, key=pidx.get)

o = el[el.CNES.isin(J)]
oc = np.array([cost(r.i, r.CNES) for r in o.itertuples()])
obs = float(oc.mean())
obs_i = o.assign(c=oc).groupby('i').c.agg(obs_n='size', obs_c='mean').reset_index()
tot = float(cells.d.sum())
print(f'observed mean travel {obs:.4f} (n={len(o)})')

suffix = ('' if ROLL is None else f'_{CAPLAB}') + ('_nopair' if NOPAIR else '') + ('_arcbound' if ARCBOUND else '')
out = {'year': YEAR, 'cap_roll': ROLL, 'pi': PI, 'travel_obs': obs, 'demand_mo': tot,
       'n_fac': len(J), 'n_muni': int(cells.i.nunique()), 'runs': []}
for mult, lab in [(None,'unconstrained'), (2.0,f'cap 2x {CAPLAB}'), (1.5,f'cap 1.5x {CAPLAB}'), (1.0,f'cap 1x {CAPLAB}')]:
    if mult is None:
        Aub = Cb; bub = B.values
        ub = [np.inf]*(nx+nu)
    else:
        kap = np.array([max(mult*peak_jp.get(k, 0.0), 0.5) for k in pair_keys])
        if ARCBOUND:
            # Superseded specification: the pair cap applied to each origin's arc
            # separately rather than to the pair total. Retained to quantify the
            # difference; not the program of equation (4).
            Aub = sparse.vstack([Cb, Sc])
            bub = np.concatenate([B.values, np.array([mult*peak_j.get(j, 0.0) for j in J])])
            ub = [max(mult*peak_jp.get((j, p), 0.0), 0.5) for (i, j, p) in cols] + [np.inf]*nu
        elif NOPAIR:
            Aub = sparse.vstack([Cb, Sc])
            bub = np.concatenate([B.values, np.array([mult*peak_j.get(j, 0.0) for j in J])])
            ub = [np.inf]*(nx+nu)
        else:
            Aub = sparse.vstack([Cb, Sc, Pb])
            bub = np.concatenate([B.values, np.array([mult*peak_j.get(j, 0.0) for j in J]), kap])
            ub = [np.inf]*(nx+nu)
    res = linprog(obj, A_ub=Aub, b_ub=bub, A_eq=A, b_eq=cells.d.values,
                  bounds=list(zip([0]*(nx+nu), ub)), method='highs')
    if res.status != 0:
        print(f'{lab:18s} FAILED: {res.message}'); continue
    x = res.x[:nx]; u = res.x[nx:]; s = x.sum(); un = float(u.sum())
    t = float(np.dot(c, x))/s
    tadj = (float(np.dot(c, x)) + PI*un)/tot
    use = np.zeros(len(J))
    for k, (i, j, p) in enumerate(cols): use[jidx[j]] += x[k]*dict(scope[p])[j]
    util = use.sum()/B.values.sum()
    bind = int((use/np.maximum(B.values, 1e-9) > 0.95).sum())
    print(f'{lab:18s} served {s:7.1f} unmet {un:6.1f} ({un/tot:4.1%}) travel {t:.4f} adj {tadj:.4f} gap_adj {(obs-tadj)/obs:+.1%} util {util:.3f} binding {bind}')
    out['runs'].append({'label': lab, 'served': float(s), 'unmet': un, 'unmet_share': un/tot,
                        'travel': t, 'travel_adj': tadj, 'gap': float((obs-t)/obs),
                        'gap_adj': float((obs-tadj)/obs), 'util': float(util), 'binding': bind})
    if mult == 1.0:
        kmap = dict(zip(pair_keys, kap))
        fl = pd.DataFrame(cols, columns=['i', 'j', 'p'])
        fl['c'] = c
        fl['x'] = x
        # ub is the pair's cap, the right-hand side of equation (4), not an arc bound.
        fl['ub'] = [kmap[(j, p)] for (i, j, p) in cols]
        fl = fl[fl.x > 1e-9].copy()
        fl['muni_mov'] = fl.j.map(fm)
        # Shadow price of one more unit of demonstrated capability at pair (j,p),
        # in region-crossings per case per month. Negative marginals are savings.
        if not ARCBOUND and not NOPAIR:
            mg = res.ineqlin.marginals[len(J)*2:]
            pt = pd.DataFrame(pair_keys, columns=['j', 'p'])
            pt['kappa'] = kap
            pt['served'] = pt.apply(lambda r: fl[(fl.j == r.j) & (fl.p == r.p)].x.sum(), axis=1)
            pt['dual'] = -mg
            pt['binding'] = pt.served >= 0.95*pt.kappa
            pt['muni_mov'] = pt.j.map(fm)
            pt.to_parquet(f'paper/duals_{YEAR}{suffix}.parquet', index=False)
            nb = int(pt.binding.sum())
            print(f'pair duals: {nb} binding of {len(pt)} | max {pt.dual.max():.3f} '
                  f'| total value of +1 unit at every binding pair {pt[pt.binding].dual.sum():.1f}')
        um = pd.DataFrame({'i': cells.i.values, 'p': cells.p.values, 'd': cells.d.values, 'u': u})
        fl.to_parquet(f'paper/flows_{YEAR}{suffix}.parquet', index=False)
        um.to_parquet(f'paper/unmet_{YEAR}{suffix}.parquet', index=False)
        obs_i.to_parquet(f'paper/obs_i_{YEAR}{suffix}.parquet', index=False)
        sj = fl.groupby('j').x.sum()
        fac = pd.DataFrame({'j': J, 'beds_bd': B.values, 'use_bd': use,
                            'util': use / np.maximum(B.values, 1e-9),
                            'cap_cases': [peak_j.get(j, 0.0) for j in J]})
        fac['served_cases'] = fac.j.map(sj).fillna(0.0)
        fac['cap_use'] = fac.served_cases / fac.cap_cases.replace(0, np.nan)
        fac['bed_binding'] = fac.util > 0.95
        fac.to_parquet(f'paper/fac_{YEAR}{suffix}.parquet', index=False)
        b = fac[fac.bed_binding]
        print(f'bed-binding facilities {len(b)} | their mean cap_use {b.cap_use.mean():.3f}')
        print(f'cap-binding (cap_use>0.95): {(fac.cap_use > 0.95).sum()} | their mean bed util {fac[fac.cap_use > 0.95].util.mean():.3f}')
        print(f'flows dumped: {len(fl)} arcs, served {fl.x.sum():.1f}, unmet {um.u.sum():.1f}')

json.dump(out, open(f'paper/model_{YEAR}{suffix}.json', 'w'), indent=1)
print(f'written paper/model_{YEAR}{suffix}.json')
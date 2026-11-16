"""Endogenous opening under a budget of k new facility-procedure pairs.

No pair-opening cost is needed. Fix a budget k, let the program choose which
pairs to open, and sweep k. The frontier of access gain against k is the object;
no price ever enters.

    min  sum c_ij x_ijp + pi sum u_ip
    s.t. demand, bed-days and the facility total exactly as in equation (4)
         sum_i x_ijp <= kappa_jp                      for (j,p) in scope
         sum_i x_ijp <= y_jp * kappahat_jp            for (j,p) a candidate
         sum y_jp <= k,   y binary

Three modelling choices, all stated rather than tuned:

  kappahat_jp   the capability a newly opened pair receives. Median kappa_jp for
                procedure p among facilities in the same bed-size tercile, swept
                at 0.5x, 1x and 2x as a robustness ladder.
  lambda_jp     a new pair has no facility-specific length of stay. It gets the
                procedure-level mean.
  candidate arcs  a candidate pair is linked only to municipalities within cost
                1, that is the facility's own municipality or its immediate
                region. Opening capability to serve patients two regions away is
                not the policy this represents.

The facility total row is NOT relaxed when a pair opens. A facility that is
already at its total cap can re-mix its caseload but cannot do more of it. This
is the conservative reading and it matters: Section 4.2 shows most binding pairs
sit at such facilities.

    python -m scripts.ksweep 2025 --mult 1.0 --klist 1,2,3,5,8,12,16,20,30,40,50
"""
import json, io, sys, glob, time
import numpy as np, pandas as pd
from scipy.optimize import linprog, milp, LinearConstraint, Bounds
from scipy import sparse

YEAR = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else '2025'
MULT = float(sys.argv[sys.argv.index('--mult') + 1]) if '--mult' in sys.argv else 1.0
KLIST = [int(v) for v in (sys.argv[sys.argv.index('--klist') + 1].split(',')
         if '--klist' in sys.argv else '1,2,3,5,8,12,16,20,30,40,50'.split(','))]
TLIM = float(sys.argv[sys.argv.index('--tlim') + 1]) if '--tlim' in sys.argv else 60.0
NSCREEN = int(sys.argv[sys.argv.index('--screen') + 1]) if '--screen' in sys.argv else 400
ROLL, PI, K = 3, 6.0, 30.0
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
dem = (el.groupby(['i','p']).size()/12.0).rename('d').reset_index()
cellt = el.groupby(['CNES','p']).DIAS_PERM.agg(['size','mean'])
pmean = el.groupby('p').DIAS_PERM.mean()
lam = cellt.reset_index(); lam['lam'] = (lam['size']*lam['mean'] + K*lam.p.map(pmean))/(lam['size']+K)

inpat = {'01','02','03','04','05','06','08','09','11','12','13','14','15','16','67','90','91','10','68','83'}
lt = pd.read_parquet('data/interim/cnes_lt_raw.parquet').copy()
lt['sus'] = pd.to_numeric(lt.QT_SUS, errors='coerce').fillna(0)
lt['co'] = lt.CODLEITO.astype(str).str.zfill(2); lt['yr'] = lt.comp.astype(str).str[:4]
beds = lt[lt.co.isin(inpat) & (lt.yr == YEAR)].groupby(['CNES','comp']).sus.sum().groupby('CNES').mean()
urg = a[sg & (a.CAR_INT != '01')].groupby('CNES').DIAS_PERM.sum()/12.0
B = (beds*30.0).sub(urg, fill_value=0).clip(lower=0)

def rollmax(g, keys, roll=ROLL):
    t = g.groupby(keys+['COMPETENCIA']).size().unstack('COMPETENCIA', fill_value=0)
    t = t.reindex(columns=sorted(g.COMPETENCIA.unique()), fill_value=0)
    return t.T.rolling(roll, min_periods=roll).mean().max()

peak_jp = rollmax(el, ['CNES','p']); peak_j = rollmax(el, ['CNES'])
J = sorted(set(lam.CNES) & set(B[B > 0].index)); lam = lam[lam.CNES.isin(J)]; B = B.loc[J]
jidx = {c: k for k, c in enumerate(J)}
P = sorted(el.p.unique())

def cost(i, j):
    mj = fm.get(j)
    if mj == i: return 0.0
    if ri.get(i) and ri.get(i) == ri.get(mj): return 1.0
    if rt.get(i) and rt.get(i) == rt.get(mj): return 2.0
    return 3.0

# kappa-hat: median kappa_jp for p among facilities in the same bed-size tercile
bs = B.rank(pct=True)
terc = {j: (0 if bs[j] <= 1/3 else 1 if bs[j] <= 2/3 else 2) for j in J}
kobs = {(j, p): peak_jp.get((j, p), 0.0) for j in J for p in P if (j, p) in peak_jp.index}
khat = {}
for p in P:
    for t in (0, 1, 2):
        v = [kobs[(j, p)] for j in J if terc[j] == t and (j, p) in kobs and kobs[(j, p)] > 0]
        khat[(p, t)] = float(np.median(v)) if v else 0.0

scope_set = set(map(tuple, el[el.CNES.isin(J)][['CNES','p']].drop_duplicates().values))
scope = {}
for _, r in lam.iterrows(): scope.setdefault(r.p, []).append((r.CNES, r.lam))
cells = dem[dem.d > 0].reset_index(drop=True)

cand = [(j, p) for j in J for p in P if (j, p) not in scope_set and khat[(p, terc[j])] > 0]
print(f'{YEAR}: |J| {len(J)} |P| {len(P)} | scope {len(scope_set)} | candidates {len(cand)} '
      f'| kappahat multiplier {MULT}', flush=True)

# ---- base columns (existing pairs) ----
cols=[]; c=[]; rA=[]; cA=[]; rC=[]; cC=[]; vC=[]; rS=[]; cS=[]; rP=[]; cP=[]; pidx={}
for n, r in cells.iterrows():
    for (j, lj) in scope.get(r.p, []):
        k = len(cols); cols.append((r.i, j, r.p)); c.append(cost(r.i, j))
        rA.append(n); cA.append(k); rC.append(jidx[j]); cC.append(k); vC.append(lj)
        rS.append(jidx[j]); cS.append(k)
        q = pidx.setdefault((j, r.p), len(pidx)); rP.append(q); cP.append(k)
nx0 = len(cols); nu = len(cells); npair = len(pidx)
pair_keys = sorted(pidx, key=pidx.get)
kap = np.array([max(peak_jp.get(k, 0.0), 0.5) for k in pair_keys])
kj = np.array([peak_j.get(j, 0.0) for j in J])
cellk = {(r.i, r.p): n for n, r in cells.iterrows()}

# ---- candidate columns, linked only within cost 1 ----
ccols=[]; cc=[]; crA=[]; crC=[]; cvC=[]; crS=[]; crY=[]
cidx = {}
for (j, p) in cand:
    y = cidx.setdefault((j, p), len(cidx))
    for i in cells[cells.p == p].i.values:
        cij = cost(i, j)
        if cij > 1.0: continue
        k = len(ccols); ccols.append((i, j, p)); cc.append(cij)
        crA.append(cellk[(i, p)]); crC.append(jidx[j]); cvC.append(float(pmean[p]))
        crS.append(jidx[j]); crY.append(y)
ncx = len(ccols); ny = len(cidx)
cand_keys = sorted(cidx, key=cidx.get)
khat_v = np.array([MULT*khat[(p, terc[j])] for (j, p) in cand_keys])
print(f'  candidate columns {ncx} over {ny} candidate pairs '
      f'(kappahat median {np.median(khat_v):.2f}, max {khat_v.max():.2f})', flush=True)

N = nx0 + ncx + nu + ny
obj = np.concatenate([np.array(c), np.array(cc), np.full(nu, PI), np.zeros(ny)])

def blocks():
    Aeq = sparse.coo_matrix(
        (np.ones(nx0+ncx+nu),
         (np.concatenate([rA, crA, np.arange(nu)]),
          np.concatenate([np.arange(nx0), nx0+np.arange(ncx), nx0+ncx+np.arange(nu)]))),
        shape=(nu, N)).tocsr()
    Cb = sparse.coo_matrix((np.concatenate([vC, cvC]),
        (np.concatenate([rC, crC]), np.concatenate([np.arange(nx0), nx0+np.arange(ncx)]))),
        shape=(len(J), N)).tocsr()
    Sc = sparse.coo_matrix((np.ones(nx0+ncx),
        (np.concatenate([rS, crS]), np.concatenate([np.arange(nx0), nx0+np.arange(ncx)]))),
        shape=(len(J), N)).tocsr()
    Pb = sparse.coo_matrix((np.ones(nx0), (rP, cP)), shape=(npair, N)).tocsr()
    # sum_i x - khat*y <= 0
    Yb = sparse.coo_matrix(
        (np.concatenate([np.ones(ncx), -khat_v]),
         (np.concatenate([crY, np.arange(ny)]),
          np.concatenate([nx0+np.arange(ncx), nx0+ncx+nu+np.arange(ny)]))),
        shape=(ny, N)).tocsr()
    Kb = sparse.coo_matrix((np.ones(ny), (np.zeros(ny), nx0+ncx+nu+np.arange(ny))), shape=(1, N)).tocsr()
    return Aeq, Cb, Sc, Pb, Yb, Kb

Aeq, Cb, Sc, Pb, Yb, Kb = blocks()
d_eq = cells.d.values

# ---- screen candidates on the LP relaxation at a generous budget ----
t0 = time.time()
Aub = sparse.vstack([Cb, Sc, Pb, Yb])
bub = np.concatenate([B.values, kj, kap, np.zeros(ny)])
ub = np.concatenate([np.full(nx0+ncx+nu, np.inf), np.ones(ny)])
relax = linprog(obj, A_ub=sparse.vstack([Aub, Kb]),
                b_ub=np.concatenate([bub, [float(max(KLIST))]]),
                A_eq=Aeq, b_eq=d_eq, bounds=list(zip(np.zeros(N), ub)), method='highs')
yrel = relax.x[nx0+ncx+nu:]
keep = np.argsort(-yrel)[:NSCREEN]
keep = np.array(sorted(set(keep.tolist()) | set(np.where(yrel > 1e-6)[0].tolist())))
print(f'  LP relaxation {time.time()-t0:.0f}s, cost {np.dot(obj[:nx0+ncx], relax.x[:nx0+ncx]):.1f}, '
      f'{int((yrel > 1e-6).sum())} candidates with y>0; screening to {len(keep)}', flush=True)

# rebuild with only the screened candidates
keepset = set(keep.tolist())
mask_c = np.array([crY[k] in keepset for k in range(ncx)])
remap = {old: n for n, old in enumerate(keep)}
ccols = [ccols[k] for k in range(ncx) if mask_c[k]]
cc = list(np.array(cc)[mask_c]); crA = list(np.array(crA)[mask_c])
crC = list(np.array(crC)[mask_c]); cvC = list(np.array(cvC)[mask_c])
crS = list(np.array(crS)[mask_c]); crY = [remap[crY[k]] for k in range(ncx) if mask_c[k]]
ncx = len(ccols); ny = len(keep)
cand_keys = [cand_keys[k] for k in keep]; khat_v = khat_v[keep]
N = nx0 + ncx + nu + ny
obj = np.concatenate([np.array(c), np.array(cc), np.full(nu, PI), np.zeros(ny)])
Aeq, Cb, Sc, Pb, Yb, Kb = blocks()
Aub = sparse.vstack([Cb, Sc, Pb, Yb])
bub = np.concatenate([B.values, kj, kap, np.zeros(ny)])

base = linprog(np.concatenate([np.array(c), np.zeros(ncx), np.full(nu, PI), np.zeros(ny)]),
               A_ub=sparse.vstack([Aub, Kb]), b_ub=np.concatenate([bub, [0.0]]),
               A_eq=Aeq, b_eq=d_eq, bounds=list(zip(np.zeros(N), np.concatenate(
                   [np.full(nx0+ncx+nu, np.inf), np.ones(ny)]))), method='highs')
base_mean = float(np.dot(obj[:nx0+ncx], base.x[:nx0+ncx])/base.x[:nx0+ncx].sum())
print(f'  k=0 mean cost {base_mean:.4f}', flush=True)

integrality = np.concatenate([np.zeros(nx0+ncx+nu), np.ones(ny)])
lb = np.zeros(N); ub = np.concatenate([np.full(nx0+ncx+nu, np.inf), np.ones(ny)])
runs = []
for kk in KLIST:
    t0 = time.time()
    cons = [LinearConstraint(Aeq, d_eq, d_eq),
            LinearConstraint(sparse.vstack([Aub, Kb]),
                             -np.inf, np.concatenate([bub, [float(kk)]]))]
    r = milp(c=obj, constraints=cons, integrality=integrality, bounds=Bounds(lb, ub),
             options={'time_limit': TLIM, 'mip_rel_gap': 1e-4})
    el_t = time.time()-t0
    if r.x is None:
        print(f'  k={kk:3d}  no incumbent in {el_t:.0f}s', flush=True)
        runs.append({'k': kk, 'status': 'no incumbent', 'seconds': el_t}); continue
    xs = r.x[:nx0+ncx]
    mean = float(np.dot(obj[:nx0+ncx], xs)/xs.sum())
    yv = r.x[nx0+ncx+nu:]
    chosen = [cand_keys[q] for q in np.where(yv > 0.5)[0]]
    gapmip = float(getattr(r, 'mip_gap', np.nan))
    # A larger budget can only weaken the constraint, so an incumbent worse than
    # k=0 is a feasible point the solver happened to stop on, not a bound worth
    # reporting. Record the failure instead of the number.
    if mean > base_mean + 1e-9:
        print(f'  k={kk:3d}  no usable incumbent (mean {mean:.4f} > k=0 {base_mean:.4f}, '
              f'mipgap {gapmip:.2e}) in {el_t:.0f}s', flush=True)
        runs.append({'k': kk, 'status': 'no usable incumbent', 'mip_gap': gapmip,
                     'seconds': el_t, 'incumbent_mean': mean})
        continue
    runs.append({'k': kk, 'mean_cost': mean, 'improvement_pct': (base_mean-mean)/base_mean*100,
                 'n_opened': int(len(chosen)), 'mip_gap': gapmip, 'seconds': el_t,
                 'chosen': [{'j': j, 'p': p, 'muni': nm.get(fm.get(j))} for (j, p) in chosen]})
    print(f'  k={kk:3d}  mean {mean:.4f}  gain {(base_mean-mean)/base_mean*100:5.2f}%  '
          f'opened {len(chosen):3d}  mipgap {gapmip:.2e}  {el_t:5.0f}s', flush=True)

out = {'year': YEAR, 'mult': MULT, 'base_mean': base_mean, 'n_candidates_screened': int(ny),
       'n_candidates_total': int(len(cand)), 'time_limit': TLIM, 'runs': runs}
fn = f'paper/ksweep_{YEAR}_m{MULT:g}.json'
json.dump(out, io.open(fn, 'w', encoding='utf-8'), indent=1)
print('written', fn)

"""Bootstrap intervals on the allocative gap.

Resamples facility-months with replacement, re-estimates the bed-day consumption
parameter lambda_jp and the capability caps kappa_jp and kappa_j on the resampled
panel, re-solves at the 1x rolling-3 cap, and records the gap.

Demand, the observed baseline and the caps all move with the resample, so the
interval reflects sampling variability in the panel as a whole rather than in the
caps alone. Bed endowments B_j come from CNES and are held fixed.

The column structure of the program is built once per year; each draw updates
only the data that changes (lambda on Cb, demand on b_eq, caps on b_ub). A draw
is therefore one solve rather than one rebuild.

    python -m scripts.bootstrap_gap 2023 --draws 200 [--write]
"""
import json, io, sys, time
import numpy as np, pandas as pd, glob
from scipy.optimize import linprog
from scipy import sparse

YEAR = sys.argv[1] if len(sys.argv) > 1 else '2023'
DRAWS = int(sys.argv[sys.argv.index('--draws') + 1]) if '--draws' in sys.argv else 200
SEED = 20260807
CLASSICAL = '--classical' in sys.argv
ROLL, PI, K = 3, 6.0, 30.0
YY = YEAR[2:]

rng = np.random.default_rng(SEED)
ref = pd.read_csv('data/ref/ibge_municipios_go.csv', dtype=str)
ri = dict(zip(ref.cod6, ref.reg_imediata)); rt = dict(zip(ref.cod6, ref.reg_intermediaria))
GO = set(ref.cod6)

a = pd.concat([pd.read_parquet(f, columns=['CNES','PROC_REA','CAR_INT','DIAS_PERM','COMPETENCIA','MUNIC_RES','MUNIC_MOV'])
               for f in sorted(glob.glob(f'data/interim/sih/RDGO{YY}*.parquet'))])
sg = a.PROC_REA.str[:2] == '04'
el = a[sg & (a.CAR_INT == '01')].copy()
el['p'] = el.PROC_REA.str[:4]; el['i'] = el.MUNIC_RES.astype(str).str[:6]
el = el[el.i.isin(GO)].reset_index(drop=True)

fm = el.groupby('CNES').MUNIC_MOV.agg(lambda s: s.mode().iat[0]).astype(str).str[:6]
inpat = {'01','02','03','04','05','06','08','09','11','12','13','14','15','16','67','90','91','10','68','83'}
lt = pd.read_parquet('data/interim/cnes_lt_raw.parquet').copy()
lt['sus'] = pd.to_numeric(lt.QT_SUS, errors='coerce').fillna(0)
lt['co'] = lt.CODLEITO.astype(str).str.zfill(2); lt['yr'] = lt.comp.astype(str).str[:4]
beds = lt[lt.co.isin(inpat) & (lt.yr == YEAR)].groupby(['CNES','comp']).sus.sum().groupby('CNES').mean()
urg = a[sg & (a.CAR_INT != '01')].groupby('CNES').DIAS_PERM.sum() / 12.0
Ball = (beds*30.0).sub(urg, fill_value=0).clip(lower=0)

# Demand is every in-state elective admission, including those treated at
# facilities outside J. Only lambda, kappa and the observed baseline are
# restricted to J. Restricting demand as well understates it and inflates the gap.
J = sorted(set(el.CNES) & set(Ball[Ball > 0].index))
B = Ball.loc[J].values
jidx = {c: k for k, c in enumerate(J)}
inJ = el.CNES.isin(J).to_numpy()

facs = sorted(el.CNES.unique())
fidx = {c: k for k, c in enumerate(facs)}
months = sorted(el.COMPETENCIA.unique())
midx = {m: k for k, m in enumerate(months)}
el['fk'] = el.CNES.map(fidx).astype(int)
el['mk'] = el.COMPETENCIA.map(midx).astype(int)
el['fmk'] = el.fk * len(months) + el.mk          # facility-month key, all facilities
NFM = len(facs) * len(months)
el['jk'] = el.CNES.map(lambda x: jidx.get(x, -1)).astype(int)

def cost(i, j):
    mj = fm.get(j)
    if mj == i: return 0.0
    if ri.get(i) and ri.get(i) == ri.get(mj): return 1.0
    if rt.get(i) and rt.get(i) == rt.get(mj): return 2.0
    return 3.0

# ---- fixed structure, built on the full sample ----
cells = el.groupby(['i','p']).size().reset_index()[['i','p']].reset_index(drop=True)
cellk = {(r.i, r.p): n for n, r in cells.iterrows()}
scope_pairs = el[inJ][['CNES','p']].drop_duplicates()
scope = {}
for r in scope_pairs.itertuples(): scope.setdefault(r.p, []).append(r.CNES)

cols_i=[]; cols_j=[]; cols_p=[]; c=[]; rA=[]; cA=[]; rC=[]; cC=[]; rS=[]; cS=[]; rP=[]; cP=[]
pidx = {}
for n, r in cells.iterrows():
    for j in scope.get(r.p, []):
        k = len(cols_i)
        cols_i.append(r.i); cols_j.append(j); cols_p.append(r.p); c.append(cost(r.i, j))
        rA.append(n); cA.append(k)
        rC.append(jidx[j]); cC.append(k)
        rS.append(jidx[j]); cS.append(k)
        q = pidx.setdefault((j, r.p), len(pidx)); rP.append(q); cP.append(k)
nx = len(cols_i); nu = len(cells); npair = len(pidx)
c = np.array(c); obj = np.concatenate([c, np.full(nu, PI)])
pair_keys = sorted(pidx, key=pidx.get)
colpair = np.array([pidx[(j, p)] for j, p in zip(cols_j, cols_p)])
colfac = np.array([jidx[j] for j in cols_j])

A = sparse.coo_matrix((np.concatenate([np.ones(nx), np.ones(nu)]),
                       (np.concatenate([rA, np.arange(nu)]), np.concatenate([cA, np.arange(nx, nx+nu)]))),
                      shape=(nu, nx+nu)).tocsr()
Sc = sparse.coo_matrix((np.ones(nx), (rS, cS)), shape=(len(J), nx+nu)).tocsr()
Pb = sparse.coo_matrix((np.ones(nx), (rP, cP)), shape=(npair, nx+nu)).tocsr()
Cb_pat = sparse.coo_matrix((np.ones(nx), (rC, cC)), shape=(len(J), nx+nu)).tocsr()

el['cellk'] = [cellk[(i, p)] for i, p in zip(el.i, el.p)]
el['pairk'] = [pidx.get((j, p), -1) for j, p in zip(el.CNES, el.p)]
el['obs_c'] = [cost(i, j) for i, j in zip(el.i, el.CNES)]
pcode = {p: k for k, p in enumerate(sorted(el.p.unique()))}
el['pk'] = el.p.map(pcode).astype(int)
NP = len(pcode)

dias = el.DIAS_PERM.to_numpy(float)
fmk = el.fmk.to_numpy(); cellv = el.cellk.to_numpy()
pkv = el.pk.to_numpy(); mkv = el.mk.to_numpy()
obsc = el.obs_c.to_numpy(float)
# J-restricted views for lambda, kappa and the observed baseline
sel = np.where(inJ & (el.pairk.to_numpy() >= 0))[0]
pairv_J = el.pairk.to_numpy()[sel]; dias_J = dias[sel]; pkv_J = pkv[sel]
jkv_J = el.jk.to_numpy()[sel]; mkv_J = mkv[sel]; obsc_J = obsc[sel]
pair_pk = np.array([pcode[p] for j, p in pair_keys])


def solve(w):
    """w: weight per record (bootstrap multiplicity of its facility-month)."""
    dem = np.bincount(cellv, weights=w, minlength=nu) / 12.0
    wJ = w[sel]
    cnt = np.bincount(pairv_J, weights=wJ, minlength=npair)
    sm  = np.bincount(pairv_J, weights=wJ*dias_J, minlength=npair)
    pcnt = np.bincount(pkv_J, weights=wJ, minlength=NP)
    psum = np.bincount(pkv_J, weights=wJ*dias_J, minlength=NP)
    pmean = np.divide(psum, pcnt, out=np.zeros(NP), where=pcnt > 0)
    lam_pair = (sm + K*pmean[pair_pk]) / (cnt + K)

    jm = np.bincount(jkv_J*len(months) + mkv_J, weights=wJ,
                     minlength=len(J)*len(months)).reshape(len(J), len(months))
    pm = np.zeros((npair, len(months)))
    np.add.at(pm, (pairv_J, mkv_J), wJ)
    def roll3max(M):
        if M.shape[1] < ROLL: return M.max(axis=1)
        cs = np.cumsum(np.pad(M, ((0,0),(1,0))), axis=1)
        return ((cs[:, ROLL:] - cs[:, :-ROLL]) / ROLL).max(axis=1)
    kap_j = roll3max(jm)
    kap_p = np.maximum(roll3max(pm), 0.5)

    Cb = sparse.coo_matrix((lam_pair[colpair], (rC, cC)), shape=(len(J), nx+nu)).tocsr()

    Aub = sparse.vstack([Cb, Sc, Pb]).tocsr()
    bub = np.concatenate([B, kap_j, kap_p])
    res = linprog(obj, A_ub=Aub, b_ub=bub, A_eq=A, b_eq=dem,
                  bounds=(0, None), method='highs')
    if res.status != 0: return None
    x = res.x[:nx]
    obs = float(np.dot(wJ, obsc_J) / wJ.sum())
    opt = float(np.dot(c, x) / x.sum())
    return obs, opt, (obs - opt)/obs, float(res.x[nx:].sum())


w0 = np.ones(len(el))
base = solve(w0)
print(f'{YEAR}: {len(el)} records | {len(J)} facilities | {nu} cells | {nx} variables | {npair} pairs')
print(f'point estimate: obs {base[0]:.4f} opt {base[1]:.4f} gap {base[2]*100:+.1f}% unmet {base[3]:.1f}')

gaps=[]; opts=[]; t0=time.time()
for b in range(DRAWS):
    if CLASSICAL:
        draw = rng.integers(0, NFM, size=NFM)
        wfm = np.bincount(draw, minlength=NFM).astype(float)
    else:
        # Multiplier (Bayesian) bootstrap. kappa is a maximum over rolling
        # windows, so any resample that zeroes facility-months deflates it
        # systematically and biases the gap upward. Dirichlet weights keep every
        # facility-month present with weight > 0 and perturb only its magnitude.
        wfm = rng.exponential(size=NFM); wfm *= NFM/wfm.sum()
    w = wfm[fmk]
    if w.sum() == 0: continue
    r = solve(w)
    if r is None: continue
    gaps.append(r[2]); opts.append(r[1])
    if (b+1) % 25 == 0:
        print(f'  {b+1}/{DRAWS}  {time.time()-t0:.0f}s  gap mean {np.mean(gaps)*100:.2f}%  sd {np.std(gaps)*100:.2f}')

g = np.array(gaps)
res = {'year': YEAR, 'draws': int(len(g)), 'seed': SEED,
       'scheme': 'classical facility-month' if CLASSICAL else 'multiplier (Dirichlet) on facility-months',
       'gap_point': base[2], 'obs_point': base[0], 'opt_point': base[1],
       'gap_mean': float(g.mean()), 'gap_sd': float(g.std(ddof=1)),
       'gap_p025': float(np.quantile(g, 0.025)), 'gap_p975': float(np.quantile(g, 0.975)),
       'opt_mean': float(np.mean(opts))}
print(f"\n{YEAR}: gap {base[2]*100:.1f}%  bootstrap mean {g.mean()*100:.1f}%  sd {g.std(ddof=1)*100:.2f}"
      f"  95% CI [{np.quantile(g,0.025)*100:.1f}, {np.quantile(g,0.975)*100:.1f}]  ({len(g)} draws)")

if '--write' in sys.argv:
    NJ = 'paper/numbers.json'
    d = json.load(io.open(NJ, encoding='utf-8'))
    d.setdefault('bootstrap', {})[YEAR] = res
    json.dump(d, io.open(NJ, 'w', encoding='utf-8'), indent=1)
    print('written', NJ)

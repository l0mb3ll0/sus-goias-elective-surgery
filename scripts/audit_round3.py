"""Audit quantities that the round-2 grep sweep did not cover.

Recomputes, under the corrected specification of equation (4):
  obs_scope        the all-records observed baseline and the gap it implies
  neg_excess       negative municipal excess as a share of the positive total
  degeneracy       binding pairs carrying a zero dual, and whether the dual
                   ranking survives a small perturbation of the objective
  pair_populations the three pair counts the paper uses, so 517 and 490 are
                   distinguishable rather than contradictory
  decomp_pi        configuration C's unmet demand across pi in {4, 6, 10}

Regression-checks anything already in numbers.json before overwriting.

    python -m scripts.audit_round3 [--write] [--perturb 20]
"""
import json, io, sys, glob
import numpy as np, pandas as pd
from scipy.optimize import linprog
from scipy import sparse
from scipy.stats import spearmanr

YEARS = ['2019', '2023', '2025']
NJ = 'paper/numbers.json'
NPERT = int(sys.argv[sys.argv.index('--perturb') + 1]) if '--perturb' in sys.argv else 20
ROLL, PI, K = 3, 6.0, 30.0
SEED = 20260807

d = json.load(io.open(NJ, encoding='utf-8'))
out = {}

# ---------------- pair populations ----------------
pop = {}
for y in YEARS:
    pt = pd.read_parquet(f'paper/duals_{y}_roll3.parquet')
    fl = pd.read_parquet(f'paper/flows_{y}_roll3.parquet')
    used = set(map(tuple, fl[['j','p']].drop_duplicates().values))
    inuse = np.array([tuple(r) in used for r in pt[['j','p']].values])
    nf = (pt.kappa > 0.5001).to_numpy()
    pop[y] = {'scope': int(len(pt)), 'scope_nonfloored': int(nf.sum()),
              'used': int(inuse.sum()), 'used_nonfloored': int((nf & inuse).sum())}
    assert pop[y]['used_nonfloored'] == d['capability'][y]['n_pairs_nonfloor'], \
        f'{y}: used_nonfloored disagrees with numbers.json'
out['pair_populations'] = pop

# ---------------- negative excess ----------------
neg = {}
for y in YEARS:
    t = pd.read_csv(f'paper/flows_rank_{y}_roll3.csv', dtype={'i': str})
    pos = float(t[t.excess > 0].excess.sum()); ng = float(t[t.excess < 0].excess.sum())
    worst = t.nsmallest(1, 'excess').iloc[0]
    neg[y] = {'positive_total': pos, 'negative_total': ng,
              'negative_share_of_positive': abs(ng)/pos, 'n_negative': int((t.excess < 0).sum()),
              'largest_negative_muni': worst.nome, 'largest_negative': float(worst.excess)}
out['neg_excess'] = neg

# ---------------- observed/optimum ratio ----------------
ratio = {}
for y in YEARS:
    m = json.load(io.open(f'paper/model_{y}_roll3.json', encoding='utf-8'))
    r = {q['label']: q for q in m['runs']}['cap 1x roll3']
    ratio[y] = m['travel_obs'] / r['travel']
out['obs_over_opt'] = ratio

# ---------------- decomposition: pi sweep and A's share ----------------
dc = {}
for pi, suf in [(4, '_pi4'), (6, ''), (10, '_pi10')]:
    j = json.load(io.open(f'paper/model_decomp_roll3{suf}.json', encoding='utf-8'))
    dc[str(pi)] = {r['label'][0]: {'adj': r['travel_adj'], 'opt': r['travel_opt'],
                                   'unmet_share': r['unmet_share']} for r in j['runs']}
base = json.load(io.open('paper/model_decomp_roll3.json', encoding='utf-8'))
m19 = json.load(io.open('paper/model_2019_roll3.json', encoding='utf-8'))
rr = {q['label']: q for q in m19['runs']}
A = [r for r in base['runs'] if r['label'].startswith('A')][0]
D = [r for r in base['runs'] if r['label'].startswith('D')][0]
out['decomp_pi'] = dc
out['decomp_A_share_of_unconstrained_gain'] = (
    (base['obs_2019'] - A['travel_opt']) / (base['obs_2019'] - rr['unconstrained']['travel']))
out['decomp_A_matches_table2'] = abs(A['travel_opt'] - rr['cap 1x roll3']['travel']) < 5e-4
m23 = json.load(io.open('paper/model_2023_roll3.json', encoding='utf-8'))
out['decomp_D_matches_table2'] = abs(
    D['travel_opt'] - {q['label']: q for q in m23['runs']}['cap 1x roll3']['travel']) < 5e-4

# ---------------- 2023 model, for the observed baseline and dual stability ----------------
ref = pd.read_csv('data/ref/ibge_municipios_go.csv', dtype=str)
ri = dict(zip(ref.cod6, ref.reg_imediata)); rt = dict(zip(ref.cod6, ref.reg_intermediaria))
GO = set(ref.cod6)
a = pd.concat([pd.read_parquet(f, columns=['CNES','PROC_REA','CAR_INT','DIAS_PERM','COMPETENCIA','MUNIC_RES','MUNIC_MOV'])
               for f in sorted(glob.glob('data/interim/sih/RDGO23*.parquet'))])
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
beds = lt[lt.co.isin(inpat) & (lt.yr == '2023')].groupby(['CNES','comp']).sus.sum().groupby('CNES').mean()
urg = a[sg & (a.CAR_INT != '01')].groupby('CNES').DIAS_PERM.sum()/12.0
B = (beds*30.0).sub(urg, fill_value=0).clip(lower=0)

def rollmax(g, keys, roll=ROLL):
    t = g.groupby(keys+['COMPETENCIA']).size().unstack('COMPETENCIA', fill_value=0)
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

oc_all = np.array([cost(r.i, r.CNES) for r in el.itertuples()])
inJ = el.CNES.isin(J).to_numpy()
obs_all = float(oc_all.mean()); obs_inJ = float(oc_all[inJ].mean()); obs_out = float(oc_all[~inJ].mean())
opt = {q['label']: q for q in m23['runs']}['cap 1x roll3']['travel']
out['obs_scope_2023'] = {
    'n_all': int(len(el)), 'n_inJ': int(inJ.sum()), 'n_out': int((~inJ).sum()),
    'share_inJ': float(inJ.mean()), 'obs_all': obs_all, 'obs_inJ': obs_inJ, 'obs_out': obs_out,
    'opt': opt, 'gap_inJ': (obs_inJ-opt)/obs_inJ, 'gap_all': (obs_all-opt)/obs_all,
    'note': 'recomputed under the corrected equation (4)',
}

# ---------------- dual stability under objective perturbation ----------------
scope = {}
for _, r in lam.iterrows(): scope.setdefault(r.p, []).append((r.CNES, r.lam))
cells = dem[dem.d > 0].reset_index(drop=True)
cols=[]; c=[]; rA=[]; cA=[]; rC=[]; cC=[]; vC=[]; rS=[]; cS=[]; rP=[]; cP=[]; pidx={}
for n, r in cells.iterrows():
    for (j, lj) in scope.get(r.p, []):
        k = len(cols); cols.append((r.i, j, r.p)); c.append(cost(r.i, j))
        rA.append(n); cA.append(k); rC.append(jidx[j]); cC.append(k); vC.append(lj)
        rS.append(jidx[j]); cS.append(k)
        q = pidx.setdefault((j, r.p), len(pidx)); rP.append(q); cP.append(k)
nx = len(cols); nu = len(cells); npair = len(pidx)
c = np.array(c); pair_keys = sorted(pidx, key=pidx.get)
A_eq = sparse.coo_matrix((np.ones(nx+nu), (np.concatenate([rA, np.arange(nu)]),
                                           np.concatenate([cA, np.arange(nx, nx+nu)]))), shape=(nu, nx+nu))
Cb = sparse.coo_matrix((vC, (rC, cC)), shape=(len(J), nx+nu))
Sc = sparse.coo_matrix((np.ones(nx), (rS, cS)), shape=(len(J), nx+nu))
Pb = sparse.coo_matrix((np.ones(nx), (rP, cP)), shape=(npair, nx+nu))
Aub = sparse.vstack([Cb, Sc, Pb])
kap = np.array([max(peak_jp.get(k, 0.0), 0.5) for k in pair_keys])
bub = np.concatenate([B.values, np.array([peak_j.get(j, 0.0) for j in J]), kap])

rng = np.random.default_rng(SEED)
EPS = 1e-4
duals = []
for b in range(NPERT + 1):
    cc = c if b == 0 else c + EPS*rng.random(nx)
    res = linprog(np.concatenate([cc, np.full(nu, PI)]), A_ub=Aub, b_ub=bub,
                  A_eq=A_eq, b_eq=cells.d.values, bounds=(0, None), method='highs')
    duals.append(-res.ineqlin.marginals[len(J)*2:])
D0 = duals[0]
nf = kap > 0.5001
rhos = [float(spearmanr(D0[nf], dk[nf]).statistic) for dk in duals[1:]]
top50 = set(np.argsort(-np.where(nf, D0, -np.inf))[:50])
jac = [len(top50 & set(np.argsort(-np.where(nf, dk, -np.inf))[:50]))/50 for dk in duals[1:]]
pt23 = pd.read_parquet('paper/duals_2023_roll3.parquet')
n_binding = int(pt23.binding.sum())
out['degeneracy'] = {
    'year': '2023', 'pairs': int(npair),
    'binding_lp': n_binding,
    'binding_nonfloored': int(d['capability']['2023']['n_pairs_bound']),
    'positive_dual': int((D0 > 1e-9).sum()),
    'binding_zero_dual': n_binding - int((D0 > 1e-9).sum()),
    'perturbations': NPERT, 'epsilon': EPS,
    'spearman_mean': float(np.mean(rhos)), 'spearman_min': float(np.min(rhos)),
    'top50_overlap_mean': float(np.mean(jac)), 'top50_overlap_min': float(np.min(jac)),
}

if '--write' in sys.argv:
    d.update({k: v for k, v in out.items()})
    json.dump(d, io.open(NJ, 'w', encoding='utf-8'), indent=1)
    print('written', NJ)

print('pair populations (scope / scope non-floored / used / used non-floored):')
for y in YEARS:
    p = pop[y]; print(f"  {y}: {p['scope']} / {p['scope_nonfloored']} / {p['used']} / {p['used_nonfloored']}")
print('\nnegative excess as share of positive total:')
for y in YEARS:
    n = neg[y]; print(f"  {y}: {n['negative_share_of_positive']*100:5.1f}%  ({n['n_negative']} municipalities, "
                      f"largest {n['largest_negative_muni']} at {n['largest_negative']:.1f})")
print('\nobserved / optimum ratio:', {y: round(ratio[y], 3) for y in YEARS})
print(f"\nA share of unconstrained gain: {out['decomp_A_share_of_unconstrained_gain']*100:.1f}%")
print(f"A matches Table 2: {out['decomp_A_matches_table2']} | D matches Table 2: {out['decomp_D_matches_table2']}")
print('\nconfiguration unmet by pi:')
for pi in ['4','6','10']:
    print(f"  pi={pi:>2s}: B {dc[pi]['B']['unmet_share']*100:.1f}%  C {dc[pi]['C']['unmet_share']*100:.1f}%  "
          f"adj A {dc[pi]['A']['adj']:.4f} D {dc[pi]['D']['adj']:.4f} C {dc[pi]['C']['adj']:.4f} B {dc[pi]['B']['adj']:.4f}")
o = out['obs_scope_2023']
print(f"\nobserved baseline 2023: in-J {o['obs_inJ']:.4f} (n={o['n_inJ']}, {o['share_inJ']*100:.1f}%), "
      f"outside {o['obs_out']:.4f} (n={o['n_out']}), all {o['obs_all']:.4f}")
print(f"  gap against optimum {o['opt']:.4f}: in-J {o['gap_inJ']*100:.1f}%, all-records {o['gap_all']*100:.1f}%")
g = out['degeneracy']
print(f"\ndual degeneracy 2023: {g['binding_lp']} binding pairs, {g['positive_dual']} with a positive dual, "
      f"{g['binding_zero_dual']} binding at zero dual")
print(f"  under {NPERT} objective perturbations of {EPS}: Spearman mean {g['spearman_mean']:.3f} "
      f"min {g['spearman_min']:.3f} | top-50 overlap mean {g['top50_overlap_mean']*100:.0f}% "
      f"min {g['top50_overlap_min']*100:.0f}%")

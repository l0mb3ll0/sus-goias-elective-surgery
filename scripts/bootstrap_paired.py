"""Paired bootstrap on the gap, and BCa intervals.

Section 4.8 supported the stability claim by noting that three marginal
intervals overlap. Overlapping marginals are weak evidence about a difference.
Here one Dirichlet weight vector is drawn per replicate and applied to all three
years, so the between-year differences can be read off directly.

The weight index is (facility, month-of-year), which is the sampling unit of
scripts.bootstrap_gap and is common to the three panels: a facility's January
slot carries the same weight in 2019, 2023 and 2025. Facility-months absent in a
given year simply do not appear in that year's records.

Also reports BCa percentile intervals. The point estimate sits low in its own
percentile interval because the LP optimum is convex in demand; bias correction
removes the objection rather than explaining it. Acceleration comes from a
jackknife over facilities, which is the coarser cluster and keeps the jackknife
to a few hundred solves.

Stages, so each fits in one call:
    python -m scripts.bootstrap_paired draws     --chunk 0 --draws 50
    python -m scripts.bootstrap_paired jackknife --chunk 0 --size 40
    python -m scripts.bootstrap_paired combine   [--write]
"""
import json, io, sys, os, glob, time
import numpy as np, pandas as pd
from scipy.optimize import linprog
from scipy import sparse
from scipy.stats import norm

STAGE = sys.argv[1] if len(sys.argv) > 1 else 'combine'
CHUNK = int(sys.argv[sys.argv.index('--chunk') + 1]) if '--chunk' in sys.argv else 0
NDRAW = int(sys.argv[sys.argv.index('--draws') + 1]) if '--draws' in sys.argv else 50
JSIZE = int(sys.argv[sys.argv.index('--size') + 1]) if '--size' in sys.argv else 40
YEARS = ['2019', '2023', '2025']
ROLL, PI, K = 3, 6.0, 30.0
SEED = 20260807
CACHE = os.environ.get('BOOT_CACHE', 'paper/_boot_paired')
# Stay-length shrinkage target. 'all' (default) = procedure mean over ALL elective in-state records, as in
# scripts/model_run.py; 'jonly' = the earlier behaviour (records at model facilities only), kept to reproduce
# the 2026-08 draws. The two differ by <0.01 pp on the point gap (dist/sprint/WS2_audit.md).
LAM_TARGET = os.environ.get('BOOT_LAM', 'all')
# NOTE: nothing is created at import. The cache directory is made by the stage that writes to it.

# State and data root. Default is Goias under data/. BOOT_UF / BOOT_ROOT point the same builder at another state's files
# (used by scripts/state_pilot.py): <ROOT>/ref.csv, <ROOT>/interim/cnes_lt_raw.parquet, <ROOT>/interim/sih/RD<UF>yymm.parquet.
UF = os.environ.get('BOOT_UF', 'GO'); ROOT = os.environ.get('BOOT_ROOT')
REF = f'{ROOT}/ref.csv' if ROOT else 'data/ref/ibge_municipios_go.csv'
LTP = f'{ROOT}/interim/cnes_lt_raw.parquet' if ROOT else 'data/interim/cnes_lt_raw.parquet'
SIHG = f'{ROOT}/interim/sih/RD{UF}' if ROOT else 'data/interim/sih/RDGO'
ref = pd.read_csv(REF, dtype=str)
ri = dict(zip(ref.cod6, ref.reg_imediata)); rt = dict(zip(ref.cod6, ref.reg_intermediaria))
GO = set(ref.cod6)
inpat = {'01','02','03','04','05','06','08','09','11','12','13','14','15','16','67','90','91','10','68','83'}
lt = pd.read_parquet(LTP).copy()
lt['sus'] = pd.to_numeric(lt.QT_SUS, errors='coerce').fillna(0)
lt['co'] = lt.CODLEITO.astype(str).str.zfill(2); lt['yr'] = lt.comp.astype(str).str[:4]


class Year:
    def __init__(self, year):
        yy = year[2:]
        a = pd.concat([pd.read_parquet(f, columns=['CNES','PROC_REA','CAR_INT','DIAS_PERM','COMPETENCIA','MUNIC_RES','MUNIC_MOV'])
                       for f in sorted(glob.glob(f'{SIHG}{yy}*.parquet'))])
        sg = a.PROC_REA.str[:2] == '04'
        el = a[sg & (a.CAR_INT == '01')].copy()
        el['p'] = el.PROC_REA.str[:4]; el['i'] = el.MUNIC_RES.astype(str).str[:6]
        el = el[el.i.isin(GO)].reset_index(drop=True)
        self.fm = el.groupby('CNES').MUNIC_MOV.agg(lambda s: s.mode().iat[0]).astype(str).str[:6]
        beds = lt[lt.co.isin(inpat) & (lt.yr == year)].groupby(['CNES','comp']).sus.sum().groupby('CNES').mean()
        urg = a[sg & (a.CAR_INT != '01')].groupby('CNES').DIAS_PERM.sum()/12.0
        Ball = (beds*30.0).sub(urg, fill_value=0).clip(lower=0)
        J = sorted(set(el.CNES) & set(Ball[Ball > 0].index))
        self.J = J; self.B = Ball.loc[J].values
        jidx = {c: k for k, c in enumerate(J)}
        inJ = el.CNES.isin(J).to_numpy()

        def cost(i, j):
            mj = self.fm.get(j)
            if mj == i: return 0.0
            if ri.get(i) and ri.get(i) == ri.get(mj): return 1.0
            if rt.get(i) and rt.get(i) == rt.get(mj): return 2.0
            return 3.0

        cells = el.groupby(['i','p']).size().reset_index()[['i','p']].reset_index(drop=True)
        cellk = {(r.i, r.p): n for n, r in cells.iterrows()}
        scope = {}
        for r in el[inJ][['CNES','p']].drop_duplicates().itertuples():
            scope.setdefault(r.p, []).append(r.CNES)
        cols_j=[]; cols_p=[]; c=[]; rA=[]; cA=[]; rC=[]; cC=[]; rS=[]; cS=[]; rP=[]; cP=[]; pidx={}
        for n, r in cells.iterrows():
            for j in scope.get(r.p, []):
                k = len(cols_j); cols_j.append(j); cols_p.append(r.p); c.append(cost(r.i, j))
                rA.append(n); cA.append(k); rC.append(jidx[j]); cC.append(k)
                rS.append(jidx[j]); cS.append(k)
                q = pidx.setdefault((j, r.p), len(pidx)); rP.append(q); cP.append(k)
        self.nx = nx = len(cols_j); self.nu = nu = len(cells); self.npair = npair = len(pidx)
        self.c = np.array(c); self.obj = np.concatenate([self.c, np.full(nu, PI)])
        self.pair_keys = sorted(pidx, key=pidx.get)
        self.colpair = np.array([pidx[(j, p)] for j, p in zip(cols_j, cols_p)])
        self.rC, self.cC = rC, cC
        self.A = sparse.coo_matrix((np.ones(nx+nu), (np.concatenate([rA, np.arange(nu)]),
                                   np.concatenate([cA, np.arange(nx, nx+nu)]))), shape=(nu, nx+nu)).tocsr()
        self.Sc = sparse.coo_matrix((np.ones(nx), (rS, cS)), shape=(len(J), nx+nu)).tocsr()
        self.Pb = sparse.coo_matrix((np.ones(nx), (rP, cP)), shape=(npair, nx+nu)).tocsr()

        months = sorted(el.COMPETENCIA.unique())
        self.moy = {m: k for k, m in enumerate(months)}       # 12 slots
        el['moy'] = el.COMPETENCIA.map(self.moy).astype(int)
        el['cellk'] = [cellk[(i, p)] for i, p in zip(el.i, el.p)]
        el['pairk'] = [pidx.get((j, p), -1) for j, p in zip(el.CNES, el.p)]
        el['obs_c'] = [cost(i, j) for i, j in zip(el.i, el.CNES)]
        pcode = {p: k for k, p in enumerate(sorted(el.p.unique()))}
        self.NP = len(pcode)
        self.pair_pk = np.array([pcode[p] for j, p in self.pair_keys])
        self.cellv = el.cellk.to_numpy(); self.dias = el.DIAS_PERM.to_numpy(float)
        self.pkv = el.p.map(pcode).to_numpy()
        self.key = list(zip(el.CNES, el.moy))                 # common index
        sel = np.where(inJ & (el.pairk.to_numpy() >= 0))[0]
        self.sel = sel
        self.pairv_J = el.pairk.to_numpy()[sel]; self.dias_J = self.dias[sel]
        self.pkv_J = self.pkv[sel]; self.obsc_J = el.obs_c.to_numpy(float)[sel]
        self.jkv_J = el.CNES.map(jidx).to_numpy()[sel].astype(int)
        self.moy_J = el.moy.to_numpy()[sel]
        self.nmonth = len(months); self.el_fac = el.CNES.to_numpy()
        self.cells_d = cells

    def gap(self, w):
        nu, nx, npair, J = self.nu, self.nx, self.npair, self.J
        dem = np.bincount(self.cellv, weights=w, minlength=nu)/12.0
        wJ = w[self.sel]
        cnt = np.bincount(self.pairv_J, weights=wJ, minlength=npair)
        sm = np.bincount(self.pairv_J, weights=wJ*self.dias_J, minlength=npair)
        if LAM_TARGET == 'all':
            pc = np.bincount(self.pkv, weights=w, minlength=self.NP)
            ps = np.bincount(self.pkv, weights=w*self.dias, minlength=self.NP)
        else:
            pc = np.bincount(self.pkv_J, weights=wJ, minlength=self.NP)
            ps = np.bincount(self.pkv_J, weights=wJ*self.dias_J, minlength=self.NP)
        pm = np.divide(ps, pc, out=np.zeros(self.NP), where=pc > 0)
        lam = (sm + K*pm[self.pair_pk])/(cnt + K)
        jm = np.bincount(self.jkv_J*self.nmonth + self.moy_J, weights=wJ,
                         minlength=len(J)*self.nmonth).reshape(len(J), self.nmonth)
        pmm = np.zeros((npair, self.nmonth)); np.add.at(pmm, (self.pairv_J, self.moy_J), wJ)
        def r3(M):
            cs = np.cumsum(np.pad(M, ((0,0),(1,0))), axis=1)
            return ((cs[:, ROLL:] - cs[:, :-ROLL])/ROLL).max(axis=1)
        Cb = sparse.coo_matrix((lam[self.colpair], (self.rC, self.cC)),
                               shape=(len(J), nx+self.nu)).tocsr()
        bub = np.concatenate([self.B, r3(jm), np.maximum(r3(pmm), 0.5)])
        res = linprog(self.obj, A_ub=sparse.vstack([Cb, self.Sc, self.Pb]).tocsr(),
                      b_ub=bub, A_eq=self.A, b_eq=dem, bounds=(0, None), method='highs')
        if res.status != 0: return np.nan
        x = res.x[:nx]
        obs = float(np.dot(wJ, self.obsc_J)/wJ.sum())
        return (obs - float(np.dot(self.c, x)/x.sum()))/obs


if __name__ == '__main__':
    Y = {y: Year(y) for y in YEARS}
    allkeys = sorted({k for y in YEARS for k in Y[y].key})
    kidx = {k: n for n, k in enumerate(allkeys)}
    for y in YEARS:
        Y[y].kv = np.array([kidx[k] for k in Y[y].key])
    NK = len(allkeys)
    facs = sorted({k[0] for k in allkeys})
    print(f'common index: {NK} facility-month slots over {len(facs)} facilities', flush=True)

    if STAGE == 'draws':
        rng = np.random.default_rng(SEED + 1000*CHUNK)
        rows = []; t0 = time.time()
        for b in range(NDRAW):
            wk = rng.exponential(size=NK); wk *= NK/wk.sum()
            rows.append([Y[y].gap(wk[Y[y].kv]) for y in YEARS])
            if (b+1) % 10 == 0: print(f'  {b+1}/{NDRAW} {time.time()-t0:.0f}s', flush=True)
        os.makedirs(CACHE, exist_ok=True)
        np.save(f'{CACHE}/draws_{CHUNK}.npy', np.array(rows))
        print(f'saved {CACHE}/draws_{CHUNK}.npy  {np.array(rows).shape}')

    elif STAGE == 'jackknife':
        lo, hi = CHUNK*JSIZE, min((CHUNK+1)*JSIZE, len(facs))
        if lo >= len(facs):
            print('chunk beyond range'); sys.exit(0)
        rows = []; t0 = time.time()
        for n in range(lo, hi):
            f = facs[n]
            wk = np.ones(NK)
            drop = [kidx[k] for k in allkeys if k[0] == f]
            wk[drop] = 1e-9
            wk *= NK/wk.sum()
            rows.append([Y[y].gap(wk[Y[y].kv]) for y in YEARS])
            print(f'  {n-lo+1}/{hi-lo} {f} {time.time()-t0:.0f}s', flush=True)
        os.makedirs(CACHE, exist_ok=True)
        np.save(f'{CACHE}/jack_{CHUNK}.npy', np.array(rows))
        print(f'saved {CACHE}/jack_{CHUNK}.npy  {np.array(rows).shape}')

    else:
        D = np.vstack([np.load(f) for f in sorted(glob.glob(f'{CACHE}/draws_*.npy'))])
        D = D[~np.isnan(D).any(axis=1)]
        jf = sorted(glob.glob(f'{CACHE}/jack_*.npy'))
        Jk = np.vstack([np.load(f) for f in jf]) if jf else None
        point = np.array([json.load(io.open(f'paper/model_{y}_roll3.json', encoding='utf-8'))
                          and {q['label']: q for q in json.load(io.open(f'paper/model_{y}_roll3.json',
                              encoding='utf-8'))['runs']}['cap 1x roll3']['gap'] for y in YEARS])

        def bca(col, theta):
            b = D[:, col]
            z0 = norm.ppf(max(min((b < theta).mean(), 1-1e-6), 1e-6))
            if Jk is None or np.isnan(Jk[:, col]).all():
                a = 0.0
            else:
                jj = Jk[:, col][~np.isnan(Jk[:, col])]
                dev = jj.mean() - jj
                a = (dev**3).sum()/(6*((dev**2).sum())**1.5) if (dev**2).sum() > 0 else 0.0
            out = []; qs = []
            for al in (0.025, 0.975):
                z = norm.ppf(al)
                q = norm.cdf(z0 + (z0+z)/(1 - a*(z0+z)))
                qs.append(float(q))
                out.append(float(np.quantile(b, q)))
            # BCa assumes the bias is a smooth monotone distortion. Here it is a
            # systematic Jensen shift, z0 runs to -2, and the corrected endpoints
            # fall off the end of the empirical distribution: with this many draws
            # the interval is not estimable rather than merely wide.
            usable = qs[0]*len(b) >= 1.0 and (1-qs[1])*len(b) >= 1.0
            return out, float(z0), float(a), qs, bool(usable)

        res = {'draws': int(len(D)), 'jackknife_facilities': int(0 if Jk is None else len(Jk)),
               'scheme': 'paired multiplier on (facility, month-of-year), shared across years',
               'years': {}, 'differences': {}}
        print(f'\n{len(D)} paired draws' + (f', {len(Jk)} jackknife facilities' if Jk is not None else ''))
        print(f"{'year':6s}{'point':>8s}{'mean':>8s}{'sd':>7s}{'pct 2.5':>9s}{'pct 97.5':>10s}"
              f"{'BCa lo':>9s}{'BCa hi':>9s}{'z0':>7s}{'a':>8s}")
        for k, y in enumerate(YEARS):
            (lo, hi), z0, acc, qs, usable = bca(k, point[k])
            res['years'][y] = {'point': float(point[k]), 'mean': float(D[:, k].mean()),
                               'sd': float(D[:, k].std(ddof=1)),
                               'pct_lo': float(np.quantile(D[:, k], 0.025)),
                               'pct_hi': float(np.quantile(D[:, k], 0.975)),
                               'bca_lo': lo, 'bca_hi': hi, 'z0': z0, 'a': acc,
                               'bca_target_quantiles': qs, 'bca_usable': usable,
                               'frac_below_point': float((D[:, k] < point[k]).mean())}
            r = res['years'][y]
            print(f"{y:6s}{r['point']*100:>7.1f}%{r['mean']*100:>7.1f}%{r['sd']*100:>7.2f}"
                  f"{r['pct_lo']*100:>9.1f}{r['pct_hi']*100:>10.1f}{lo*100:>9.1f}{hi*100:>9.1f}"
                  f"{z0:>7.2f}{acc:>8.3f}  BCa {'usable' if usable else 'DEGENERATE'} "
                  f"(targets {qs[0]:.1e}, {qs[1]:.3f})")
        print()
        for lab, i, j in [('2023 - 2019', 1, 0), ('2025 - 2023', 2, 1), ('2025 - 2019', 2, 0)]:
            d = D[:, i] - D[:, j]
            pt = point[i] - point[j]
            lo, hi = np.quantile(d, [0.025, 0.975])
            res['differences'][lab] = {'point': float(pt), 'mean': float(d.mean()),
                                       'sd': float(d.std(ddof=1)), 'lo': float(lo), 'hi': float(hi),
                                       'p_two_sided': float(2*min((d < 0).mean(), (d > 0).mean()))}
            r = res['differences'][lab]
            print(f"  {lab}: point {pt*100:+.1f}p  bootstrap mean {d.mean()*100:+.1f}p  "
                  f"sd {d.std(ddof=1)*100:.2f}  95% [{lo*100:+.1f}, {hi*100:+.1f}]  p={r['p_two_sided']:.3f}")
        if '--write' in sys.argv:
            NJ = 'paper/numbers.json'
            dd = json.load(io.open(NJ, encoding='utf-8'))
            dd['bootstrap_paired'] = res
            json.dump(dd, io.open(NJ, 'w', encoding='utf-8'), indent=1)
            print('\nwritten', NJ)

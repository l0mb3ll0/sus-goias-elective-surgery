"""AYear: a copy of scripts/bootstrap_paired.Year (same LP, same constants) with audit options. Defaults reproduce Year exactly (checked in audit2.py).
Options: time 'comp' | 'saida' (month of DT_SAIDA); window 'cal' (calendar year) | 'jul' (July of t-1 to June of t); bed 'paper' (20-code surgical bed set, net of urgent group-04 bed-days)
| 'all' (all CODLEITO beds, net of the bed-days of ALL AIH other than elective surgical ones); days 30 | 'actual' (calendar days/12); cost 'ord' | 'cross' (max(c-1,0)); rolling = ROLL.
"""
import glob, calendar
import numpy as np, pandas as pd
from scipy import sparse
from scipy.optimize import linprog
ROLL, PI, K = 3, 6.0, 30.0
inpat = {'01','02','03','04','05','06','08','09','11','12','13','14','15','16','67','90','91','10','68','83'}
ref = pd.read_csv('data/ref/ibge_municipios_go.csv', dtype=str)
ri = dict(zip(ref.cod6, ref.reg_imediata)); rt = dict(zip(ref.cod6, ref.reg_intermediaria)); GO = set(ref.cod6)
lt = pd.read_parquet('data/interim/cnes_lt_raw.parquet').copy()
lt['sus'] = pd.to_numeric(lt.QT_SUS, errors='coerce').fillna(0); lt['co'] = lt.CODLEITO.astype(str).str.zfill(2); lt['yr'] = lt.comp.astype(str).str[:4]
lt['ym'] = lt.comp.astype(str).str[:4] + '-' + lt.comp.astype(str).str[4:6]

def r3(M):
    cs = np.cumsum(np.pad(M, ((0, 0), (1, 0))), axis=1)
    return ((cs[:, ROLL:] - cs[:, :-ROLL]) / ROLL).max(axis=1)

class AYear:
    def __init__(self, year, time='comp', window='cal', bed='paper', days=30, cost='ord', roll=True, zone='muni', geo='ibge', exclude=None):
        y = int(year); yy = year[2:]
        if geo == 'health':
            _h = pd.read_csv('data/ref/regioes_saude_go.csv', dtype=str); ri = dict(zip(_h.cod6, _h.regiao_saude)); rt = dict(zip(_h.cod6, _h.macrorregiao_saude))
        else:
            ri = globals()['ri']; rt = globals()['rt']
        files = sorted(glob.glob(f'data/interim/sih/RDGO{yy}*.parquet'))
        if window == 'jul': files = sorted(glob.glob(f'data/interim/sih/RDGO{y-1-2000:02d}*.parquet')) + files
        if time == 'saida' and window == 'cal': files = files + sorted(glob.glob(f'data/interim/sih/RDGO{y+1-2000:02d}*.parquet'))   # AIH discharged in Dec t are processed in Jan t+1 (absent for 2025: 2026 files do not exist)
        if time == 'saida' and window == 'jul': files = files + sorted(glob.glob(f'data/interim/sih/RDGO{y+1-2000:02d}*.parquet'))[:1]
        a = pd.concat([pd.read_parquet(f, columns=['CNES','PROC_REA','CAR_INT','DIAS_PERM','COMPETENCIA','MUNIC_RES','MUNIC_MOV','DT_SAIDA']) for f in files])
        if time == 'saida': a['COMPETENCIA'] = a.DT_SAIDA.astype(str).str[:4] + '-' + a.DT_SAIDA.astype(str).str[4:6]
        months = [f'{y}-{m:02d}' for m in range(1, 13)] if window == 'cal' else [f'{y-1}-{m:02d}' for m in range(7, 13)] + [f'{y}-{m:02d}' for m in range(1, 7)]
        self.n_outside = int((~a.COMPETENCIA.isin(months)).sum()); a = a[a.COMPETENCIA.isin(months)]
        sg = a.PROC_REA.str[:2] == '04'
        el = a[sg & (a.CAR_INT == '01')].copy(); el['p'] = el.PROC_REA.str[:4]; el['i'] = el.MUNIC_RES.astype(str).str[:6]
        self.el_all_n = len(el); el = el[el.i.isin(GO)]
        if exclude: el = el[~el.i.isin(exclude)]
        el = el.reset_index(drop=True)
        rtreg = {ri[c]: rt[c] for c in ri}
        if zone == 'region': el['i'] = el.i.map(ri)
        elif zone == 'macro': el['i'] = el.i.map(rt)
        self.fm = el.groupby('CNES').MUNIC_MOV.agg(lambda s: s.mode().iat[0]).astype(str).str[:6]
        dpm = (calendar.isleap(y) + 365) / 12.0 if days == 'actual' else 30.0
        ltw = lt[lt.ym.isin(months)] if window == 'jul' else lt[lt.yr == year]
        if bed == 'paper':
            beds = ltw[ltw.co.isin(inpat)].groupby(['CNES','comp']).sus.sum().groupby('CNES').mean()
            net = a[sg & (a.CAR_INT != '01')].groupby('CNES').DIAS_PERM.sum() / 12.0
        else:
            beds = ltw.groupby(['CNES','comp']).sus.sum().groupby('CNES').mean()
            net = a[~(sg & (a.CAR_INT == '01'))].groupby('CNES').DIAS_PERM.sum() / 12.0
        Ball = (beds*dpm).sub(net, fill_value=0).clip(lower=0)
        self.Ball_gross = beds*dpm; self.net = net
        J = sorted(set(el.CNES) & set(Ball[Ball > 0].index)); self.J = J; self.B = Ball.loc[J].values
        jidx = {c: k for k, c in enumerate(J)}; inJ = el.CNES.isin(J).to_numpy()
        def cst(i, j):
            mj = self.fm.get(j)
            if zone == 'region': return 0.0 if ri.get(mj) == i else 1.0 if rt.get(mj) == rtreg.get(i) else 2.0
            if zone == 'macro': return 0.0 if rt.get(mj) == i else 1.0
            c = 0.0 if mj == i else 1.0 if (ri.get(i) and ri.get(i) == ri.get(mj)) else 2.0 if (rt.get(i) and rt.get(i) == rt.get(mj)) else 3.0
            return max(c - 1.0, 0.0) if cost == 'cross' else c
        cells = el.groupby(['i','p']).size().reset_index()[['i','p']].reset_index(drop=True); cellk = {(r.i, r.p): n for n, r in cells.iterrows()}
        scope = {}
        for r in el[inJ][['CNES','p']].drop_duplicates().itertuples(): scope.setdefault(r.p, []).append(r.CNES)
        cols_j=[]; cols_p=[]; c=[]; rA=[]; cA=[]; rC=[]; cC=[]; rS=[]; cS=[]; rP=[]; cP=[]; pidx={}
        for n, r in cells.iterrows():
            for j in scope.get(r.p, []):
                k = len(cols_j); cols_j.append(j); cols_p.append(r.p); c.append(cst(r.i, j)); rA.append(n); cA.append(k); rC.append(jidx[j]); cC.append(k); rS.append(jidx[j]); cS.append(k)
                q = pidx.setdefault((j, r.p), len(pidx)); rP.append(q); cP.append(k)
        self.col_cell = np.array(rA); self.cell_i = cells.i.to_numpy(); self.cell_p = cells.p.to_numpy()
        self.nx = nx = len(cols_j); self.nu = nu = len(cells); self.npair = npair = len(pidx); self.nj = len(J)
        self.c = np.array(c); self.obj = np.concatenate([self.c, np.full(nu, PI)]); self.pair_keys = sorted(pidx, key=pidx.get)
        self.colpair = np.array([pidx[(j, p)] for j, p in zip(cols_j, cols_p)]); self.rC, self.cC = rC, cC
        self.A = sparse.coo_matrix((np.ones(nx+nu), (np.concatenate([rA, np.arange(nu)]), np.concatenate([cA, np.arange(nx, nx+nu)]))), shape=(nu, nx+nu)).tocsr()
        self.Sc = sparse.coo_matrix((np.ones(nx), (rS, cS)), shape=(len(J), nx+nu)).tocsr(); self.Pb = sparse.coo_matrix((np.ones(nx), (rP, cP)), shape=(npair, nx+nu)).tocsr()
        el['moy'] = el.COMPETENCIA.map({m: k for k, m in enumerate(months)}).astype(int)
        el['pairk'] = [pidx.get((j, p), -1) for j, p in zip(el.CNES, el.p)]
        el['obs_c'] = [cst(i, j) for i, j in zip(el.i, el.CNES)]
        pcode = {p: k for k, p in enumerate(sorted(el.p.unique()))}; self.NP = len(pcode); self.pair_pk = np.array([pcode[p] for j, p in self.pair_keys])
        self.cellv = el.cellk.to_numpy() if 'cellk' in el else np.array([cellk[(i, p)] for i, p in zip(el.i, el.p)])
        self.dias = el.DIAS_PERM.to_numpy(float); self.pkv = el.p.map(pcode).to_numpy()
        sel = np.where(inJ & (el.pairk.to_numpy() >= 0))[0]; self.sel = sel
        self.pairv_J = el.pairk.to_numpy()[sel]; self.dias_J = self.dias[sel]; self.pkv_J = self.pkv[sel]; self.obsc_J = el.obs_c.to_numpy(float)[sel]
        self.obsc_all = el.obs_c.to_numpy(float); self.jkv_J = el.CNES.map(jidx).to_numpy()[sel].astype(int); self.moy_J = el.moy.to_numpy()[sel]; self.nmonth = 12
        self.cnes_all = el.CNES.to_numpy(); self.inJ = inJ; self.rec_i = el.i.to_numpy()
    def kappas(self):
        jm = np.bincount(self.jkv_J*12 + self.moy_J, minlength=self.nj*12).reshape(self.nj, 12).astype(float)
        pmm = np.zeros((self.npair, 12)); np.add.at(pmm, (self.pairv_J, self.moy_J), 1.0)
        return r3(jm), np.maximum(r3(pmm), 0.5), jm, pmm
    def solve(self, kj=None, kp=None, B=None, c_noise=None, Kshrink=None):
        nx, nu = self.nx, self.nu
        k1, k2, jm, pmm = self.kappas(); kj = k1 if kj is None else kj; kp = k2 if kp is None else kp; B = self.B if B is None else B
        dem = np.bincount(self.cellv, minlength=nu) / 12.0
        pc = np.bincount(self.pkv, minlength=self.NP); ps = np.bincount(self.pkv, weights=self.dias, minlength=self.NP); pm = np.divide(ps, pc, out=np.zeros(self.NP), where=pc > 0)
        cnt = np.bincount(self.pairv_J, minlength=self.npair); sm = np.bincount(self.pairv_J, weights=self.dias_J, minlength=self.npair)
        Ks = K if Kshrink is None else Kshrink
        lam = (sm + Ks*pm[self.pair_pk])/np.maximum(cnt + Ks, 1e-9)
        Cb = sparse.coo_matrix((lam[self.colpair], (self.rC, self.cC)), shape=(self.nj, nx+nu)).tocsr()
        obj = self.obj if c_noise is None else np.concatenate([self.c + c_noise, np.full(nu, PI)])
        res = linprog(obj, A_ub=sparse.vstack([Cb, self.Sc, self.Pb]).tocsr(), b_ub=np.concatenate([B, kj, kp]), A_eq=self.A, b_eq=dem, bounds=(0, None), method='highs')
        assert res.status == 0, res.status
        x = res.x[:nx]; served = x.sum(); fac = np.asarray(self.Sc[:, :nx] @ x).ravel(); use = np.asarray(Cb[:, :nx] @ x).ravel()
        obs_J = float(self.obsc_J.mean()); obs_all = float(self.obsc_all.mean()); opt = float(self.c @ x / served)
        return dict(x=x, fac=fac, use=use, kj=kj, kp=kp, B=B, dem=dem, opt=opt, obs_J=obs_J, obs_all=obs_all, gap_J=(obs_J-opt)/obs_J, gap_all=(obs_all-opt)/obs_all,
                    unmet=float(res.x[nx:].sum()/dem.sum()), lam=lam, Cb=Cb, V=res.fun)

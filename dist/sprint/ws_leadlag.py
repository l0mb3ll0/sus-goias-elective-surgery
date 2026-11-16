"""T4 (EXPLORATORY): do surgeon rises come before or after elective volume rises? See dist/sprint/PREREG_round3.md. Aggregates only; no identifiers printed."""
import sys, glob, json, numpy as np, pandas as pd
sys.path.insert(0, 'dist/review')
SURG = {'225225','225270','225250','225265','225203','225285','225260','225275','225235','225310','225220','225210','225230','225290','225255','225280','225240','225215','225295'}
ref = pd.read_csv('data/ref/ibge_municipios_go.csv', dtype=str); GO = set(ref.cod6)
pf = pd.read_parquet('data/interim/cnes/cnes_pf_GO_raw.parquet', columns=['CNES', 'CBO', 'cm', 'CPF_PROF'])
for c in pf.columns: pf[c] = pf[c].astype(str).str.strip()
pf = pf[pf.CBO.isin(SURG)]
s = pf.groupby(['CNES', 'cm']).CPF_PROF.nunique().unstack(fill_value=0)              # facility x month counts only
a = pd.concat([pd.read_parquet(f, columns=['CNES', 'PROC_REA', 'CAR_INT', 'COMPETENCIA', 'MUNIC_RES']) for f in sorted(glob.glob('data/interim/sih/RDGO2[45]*.parquet'))])
a = a[(a.PROC_REA.str[:2] == '04') & (a.CAR_INT == '01') & a.MUNIC_RES.astype(str).str[:6].isin(GO)]
a['cm'] = a.COMPETENCIA.astype(str).str.strip()
v = a.groupby(['CNES', 'cm']).size().unstack(fill_value=0)
months = sorted(set(s.columns) & set(v.columns)); assert len(months) == 24, months
fac = [f for f in v.index if v.loc[f, months].mean() >= 5]
V = v.reindex(fac)[months].to_numpy(float); Sm = s.reindex(fac).fillna(0)[months].to_numpy(float)
print(f'facilities {len(fac)}, months {len(months)} ({months[0]}..{months[-1]}); mean surgeons/facility-month {Sm.mean():.2f}; mean elective/facility-month {V.mean():.1f}')
roll = lambda M: np.stack([M[:, i:i+3].mean(axis=1) for i in range(M.shape[1]-2)], axis=1)
Rv, Rs = roll(V), roll(Sm)                       # 22 smoothed months
dV, dS = np.diff(Rv, axis=1), np.diff(Rs, axis=1)  # 21 changes
H = 6; T = dV.shape[1]; usable = T - 2*H
if usable < 8: H = 4; usable = T - 2*H
print(f'smoothed changes {T}, lags +/-{H}, usable months per facility {usable}')
rows = []
for f in range(len(fac)):
    for t in range(H, T-H):
        rows.append([f, t, dV[f, t]] + [dS[f, t-h] for h in range(-H, H+1)])     # column for h: surgeon change h months BEFORE volume change
D = np.array(rows); f_id, t_id, y, X = D[:, 0].astype(int), D[:, 1].astype(int), D[:, 2], D[:, 3:]
# facility and month fixed effects by dummies (month dummies absorb common trend; facility dummies absorb level drift)
Fd = (f_id[:, None] == np.arange(len(fac))[None, :]).astype(float); Td = (t_id[:, None] == np.arange(H, T-H)[None, 1:]).astype(float)
Z = np.hstack([X, Fd, Td]); beta, *_ = np.linalg.lstsq(Z, y, rcond=None); e = y - Z @ beta
bread = np.linalg.pinv(Z.T @ Z); meat = np.zeros((Z.shape[1], Z.shape[1]))
for f in range(len(fac)):
    m = f_id == f; g = Z[m].T @ e[m]; meat += np.outer(g, g)
G = len(fac); cov = (G/(G-1)) * bread @ meat @ bread
hs = list(range(-H, H+1)); k = len(hs)
def comb(idx):
    w = np.zeros(Z.shape[1]); w[idx] = 1; return float(w @ beta), float(np.sqrt(w @ cov @ w))
lead_idx = [i for i, h in enumerate(hs) if 1 <= h <= H]; lag_idx = [i for i, h in enumerate(hs) if -H <= h <= -1]
bl, sl = comb(lead_idx); ba, sa = comb(lag_idx)
w = np.zeros(Z.shape[1]); w[lead_idx] = 1; w[lag_idx] = -1; bd, sd = float(w @ beta), float(np.sqrt(w @ cov @ w))
print('\ncoefficients b_h (h>0: surgeon change h months BEFORE the volume change; h<0: AFTER), cluster-robust SE by facility')
for i, h in enumerate(hs): print(f'  h={h:+d}  b={beta[i]:+.3f}  se={np.sqrt(cov[i,i]):.3f}')
print(f'\nsum b_h, h=1..{H} (surgeons lead):  {bl:+.3f}  95% [{bl-1.96*sl:+.3f}, {bl+1.96*sl:+.3f}]')
print(f'sum b_h, h=-{H}..-1 (volume leads): {ba:+.3f}  95% [{ba-1.96*sa:+.3f}, {ba+1.96*sa:+.3f}]')
print(f'difference (lead minus lag):        {bd:+.3f}  95% [{bd-1.96*sd:+.3f}, {bd+1.96*sd:+.3f}]  (b_0 = {beta[hs.index(0)]:+.3f})')
verdict = ('surgeon rises come BEFORE volume rises' if bl-1.96*sl > 0 and bd > 0 else
           'surgeon rises come AFTER volume rises' if ba-1.96*sa > 0 and bd < 0 else 'no temporal ordering detected')
print('VERDICT (exploratory, correlational, low power):', verdict)
json.dump(dict(n_fac=len(fac), H=H, usable_months=usable, lead_sum=bl, lead_se=sl, lag_sum=ba, lag_se=sa, diff=bd, diff_se=sd, b0=float(beta[hs.index(0)]), verdict=verdict,
               b={str(h): float(beta[i]) for i, h in enumerate(hs)}), open('dist/sprint/WS_leadlag.json', 'w'), indent=1)

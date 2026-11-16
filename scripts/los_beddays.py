"""The 2024 facility-LOS residual, expressed in bed-days.

THE ASSUMPTION, stated before any number. This converts a regression residual
into bed-days as if the residual were addressable -- as if a facility running
above its fitted LOS could be moved to that fitted value, and the freed bed-days
would then be available for other surgery. That may well be false. The residual
is unexplained, not diagnosed: it may be case complexity the six predictors do
not capture, referral role, or coding practice, none of which a manager can act
on. Read these as the SIZE OF THE UNEXPLAINED VARIATION in bed-day units, not as
a savings estimate.

Two counterfactuals:
  fitted  facility runs at its own model-predicted LOS
  CRER    facility runs at CRER's observed LOS (the largest negative residual,
          1.42 days on 473 cases) -- a best-observed-practice benchmark, not a
          model quantity

Cholecystectomy only. The denominator is the TOTAL surgical bed-day endowment,
which serves all surgery, so these shares are small by construction and the
comparison is deliberately conservative.

    python -m scripts.los_beddays
"""
import glob
import numpy as np
import pandas as pd
import statsmodels.api as sm

CHOL = ['0407030026', '0407030034']
PH_DOC = '000000000000000'
MINC, CRER = 30, '2673932'

rd = pd.concat([pd.read_parquet(f, columns=['N_AIH', 'CNES', 'PROC_REA', 'DIAS_PERM'])
                for f in sorted(glob.glob('data/interim/sih/RDGO24*.parquet'))])
for c in ('N_AIH', 'CNES', 'PROC_REA'):
    rd[c] = rd[c].astype(str).str.strip()
rd = rd[rd.PROC_REA.isin(CHOL)].copy()
rd['DIAS_PERM'] = pd.to_numeric(rd.DIAS_PERM, errors='coerce')
rd['lap'] = (rd.PROC_REA == '0407030034').astype(int)

sp = pd.read_parquet('data/interim/sih_sp/sp_GO_2024.parquet',
                     columns=['SP_NAIH', 'SP_PF_DOC', 'SP_PF_CBO', 'SP_CNES'])
for c in sp.columns:
    sp[c] = sp[c].astype(str).str.strip()
att = set(sp[(sp.SP_PF_CBO == '225225') & (sp.SP_PF_DOC != PH_DOC)].SP_NAIH)
rd = rd[rd.N_AIH.isin(att)]                       # the 52-facility basis

f = rd.groupby('CNES').agg(cases=('DIAS_PERM', 'size'), los=('DIAS_PERM', 'mean'),
                           lap_share=('lap', 'mean'))
f = f[f.cases >= MINC].copy()
spj = sp[(sp.SP_PF_DOC != PH_DOC) & sp.SP_NAIH.isin(set(rd.N_AIH))]
f['prof_case'] = spj.groupby(['SP_CNES', 'SP_NAIH']).SP_PF_DOC.nunique() \
                    .groupby(level=0).mean().reindex(f.index)
m = pd.read_csv('data/ref/hospital_master_2425.csv', dtype={'CNES': str}) \
      .set_index('CNES')
f['beds_surg'] = m.beds_surg_sus.reindex(f.index)
f['has_lap'] = (m.laparoscope.reindex(f.index).fillna(0) > 0).astype(int)
f['tp_gestao'] = m.tp_gestao.reindex(f.index)
f['volume'] = f.cases
f = f.dropna(subset=['prof_case', 'beds_surg', 'tp_gestao'])

X = f[['lap_share', 'volume', 'beds_surg', 'prof_case', 'has_lap']].astype(float)
X = X.join(pd.get_dummies(f.tp_gestao, prefix='g', drop_first=True).astype(float))
r = sm.OLS(f.los.values, sm.add_constant(X)).fit()
f['fitted'] = r.fittedvalues
f['resid'] = f.los - f.fitted
print(f'n={len(f)}  R2={r.rsquared:.3f}  (unchanged model, no predictors added)')

crer_los = float(f.los[CRER])
print(f'CRER ({CRER}) observed LOS {crer_los:.2f} on {int(f.cases[CRER])} cases')

pos = f[f.resid > 0].copy()
pos['bd_fitted'] = pos.cases * pos.resid
above = f[f.los > crer_los].copy()
above['bd_crer'] = above.cases * (above.los - crer_los)

print(f'\nfacilities with a positive residual: {len(pos)} of {len(f)}')
print(f'  cholecystectomy cases at those facilities: {int(pos.cases.sum()):,}')
print(f'  bed-days above fitted LOS: {pos.bd_fitted.sum():,.0f}')
print(f'\nfacilities above CRER observed LOS: {len(above)} of {len(f)}')
print(f'  bed-days above CRER LOS: {above.bd_crer.sum():,.0f}')

# ---- denominator ----------------------------------------------------------
bd_52 = f.beds_surg.sum() * 365.0
bd_all = m.beds_surg_sus.fillna(0).sum() * 365.0
obs_bd = (rd.DIAS_PERM.sum())
print(f'\ndenominators (annual surgical bed-days, beds x 365):')
print(f'  the {len(f)} modelled facilities: {bd_52:,.0f}')
print(f'  all 163 master facilities:        {bd_all:,.0f}')
print(f'  observed cholecystectomy bed-days (attributed AIHs): {obs_bd:,.0f} '
      f'({100*obs_bd/bd_all:.2f}% of the statewide endowment)')

print(f'\n=== residual in bed-days, as a share ===')
print(f'  {"counterfactual":22s}{"bed-days":>11s}{"% of 52-fac":>13s}'
      f'{"% of statewide":>16s}{"% of chol bd":>14s}')
for lab, v in [('at fitted LOS', pos.bd_fitted.sum()),
               ('at CRER observed LOS', above.bd_crer.sum())]:
    print(f'  {lab:22s}{v:>11,.0f}{100*v/bd_52:>12.2f}%'
          f'{100*v/bd_all:>15.2f}%{100*v/obs_bd:>13.1f}%')

print(f'\n  top contributors, fitted counterfactual:')
for cnes, row in pos.sort_values('bd_fitted', ascending=False).head(8).iterrows():
    print(f'    {cnes}  n={int(row.cases):>4}  LOS {row.los:5.2f} vs fitted '
          f'{row.fitted:5.2f}  resid {row.resid:+5.2f}  bed-days {row.bd_fitted:>7,.0f}')

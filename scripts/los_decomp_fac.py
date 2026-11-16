"""What explains facility mean LOS for cholecystectomy? 2024, facilities >=30 cases.

n = 52. That is small, so this reports univariate fits, a sequential build, and
the full model side by side rather than one specification: with six predictors on
52 points, any single R-squared is optimistic and the gap between R-squared and
adjusted R-squared is part of the answer.

PREDICTORS
  lap_share   share of the facility's cholecystectomies coded laparoscopic (SIH)
  volume      annual cholecystectomy AIHs (SIH)
  beds_surg   mean monthly surgical SUS beds, 2024-25 (CNES LT monthly)
  prof_case   mean distinct identified professionals per AIH (SIH SP)
  tp_gestao   management authority, dummies (CNES ST monthly)
  has_lap     registered laparoscopic equipment. CAVEAT: from the 202606
              snapshot, whose time-variance is what the room panel would test
              and could not be fetched. Included because it was asked for; it is
              the one predictor whose window does not match the outcome.

    python -m scripts.los_decomp_fac
"""
import argparse, glob
import numpy as np
import pandas as pd
import statsmodels.api as sm

CHOL = {'0407030026': 'open', '0407030034': 'laparoscopic'}
PH_DOC = '000000000000000'
MINC = 30

ap = argparse.ArgumentParser()
ap.add_argument('--attributed', action='store_true',
                help='restrict to AIHs with an identified 225225 surgeon, the '
                     'basis on which the earlier 52-facility figure was computed')
ARGS = ap.parse_args()

rd = pd.concat([pd.read_parquet(f, columns=['N_AIH', 'CNES', 'PROC_REA',
                                            'DIAS_PERM', 'MORTE'])
                for f in sorted(glob.glob('data/interim/sih/RDGO24*.parquet'))])
for c in ('N_AIH', 'CNES', 'PROC_REA'):
    rd[c] = rd[c].astype(str).str.strip()
rd = rd[rd.PROC_REA.isin(CHOL)].copy()
rd['lap'] = (rd.PROC_REA == '0407030034').astype(int)
rd['DIAS_PERM'] = pd.to_numeric(rd.DIAS_PERM, errors='coerce')

if ARGS.attributed:
    # The 52-facility figure came from the surgeon-attributed subset: AIHs with
    # an identified 225225 professional, 9,525 of 10,191. On the full RD set the
    # threshold admits 59 facilities. Neither is wrong; they answer different
    # questions, so the basis is named rather than left implicit.
    _sp = pd.read_parquet('data/interim/sih_sp/sp_GO_2024.parquet',
                          columns=['SP_NAIH', 'SP_PF_DOC', 'SP_PF_CBO'])
    for _c in _sp.columns:
        _sp[_c] = _sp[_c].astype(str).str.strip()
    keep = set(_sp[(_sp.SP_PF_CBO == '225225') &
                   (_sp.SP_PF_DOC != PH_DOC)].SP_NAIH)
    rd = rd[rd.N_AIH.isin(keep)]
    print(f'BASIS: surgeon-attributed AIHs only ({len(rd):,} cases)')
else:
    print(f'BASIS: all RD cholecystectomy AIHs ({len(rd):,} cases)')

f = rd.groupby('CNES').agg(cases=('DIAS_PERM', 'size'),
                           los=('DIAS_PERM', 'mean'),
                           lap_share=('lap', 'mean'))
f = f[f.cases >= MINC].copy()
print(f'facilities with >={MINC} cholecystectomies in 2024: {len(f)}')
print(f'  mean LOS spread {f.los.min():.2f} to {f.los.max():.2f}, '
      f'sd {f.los.std():.2f}, variance {f.los.var():.3f}')

sp = pd.read_parquet('data/interim/sih_sp/sp_GO_2024.parquet',
                     columns=['SP_NAIH', 'SP_PF_DOC', 'SP_CNES'])
for c in sp.columns:
    sp[c] = sp[c].astype(str).str.strip()
sp = sp[(sp.SP_PF_DOC != PH_DOC) & sp.SP_NAIH.isin(set(rd.N_AIH))]
team = sp.groupby(['SP_CNES', 'SP_NAIH']).SP_PF_DOC.nunique().groupby(level=0).mean()
f['prof_case'] = team.reindex(f.index)

m = pd.read_csv('data/ref/hospital_master_2425.csv', dtype={'CNES': str}) \
      .set_index('CNES')
miss = [c for c in f.index if c not in m.index]
print(f'  facilities absent from the master record: {len(miss)} {miss}')
f['beds_surg'] = m.beds_surg_sus.reindex(f.index)
f['has_lap'] = (m.laparoscope.reindex(f.index).fillna(0) > 0).astype(int)
f['tp_gestao'] = m.tp_gestao.reindex(f.index)
f['volume'] = f.cases

for c in ['prof_case', 'beds_surg', 'tp_gestao']:
    n = int(f[c].isna().sum())
    if n:
        print(f'  {c}: {n} missing, rows dropped from the model')
f = f.dropna(subset=['prof_case', 'beds_surg', 'tp_gestao'])
print(f'  modelled n = {len(f)}')
print(f'  tp_gestao: {f.tp_gestao.value_counts().to_dict()}')

y = f.los.values
tot_var = y.var(ddof=1)


def fit(cols, label, dummies=False):
    X = f[cols].copy() if cols else pd.DataFrame(index=f.index)
    if dummies:
        X = X.join(pd.get_dummies(f.tp_gestao, prefix='g', drop_first=True)
                   .astype(float))
    if not len(X.columns):
        return None
    X = sm.add_constant(X.astype(float))
    r = sm.OLS(y, X).fit()
    print(f'  {label:38s} R2={r.rsquared:5.3f}  adjR2={r.rsquared_adj:6.3f}  '
          f'resid sd={np.sqrt(r.mse_resid):.3f}  k={int(r.df_model)}')
    return r


print('\n=== univariate: each predictor alone ===')
uni = {}
for c in ['lap_share', 'volume', 'beds_surg', 'prof_case', 'has_lap']:
    uni[c] = fit([c], c)
uni['tp_gestao'] = fit([], 'tp_gestao (dummies)', dummies=True)

print('\n  Spearman with facility mean LOS:')
for c in ['lap_share', 'volume', 'beds_surg', 'prof_case', 'has_lap']:
    print(f'    {c:12s} {f[[c]].join(f.los).corr(method="spearman").iloc[0,1]:+.3f}')

print('\n=== full model ===')
full = fit(['lap_share', 'volume', 'beds_surg', 'prof_case', 'has_lap'],
           'all five + tp_gestao dummies', dummies=True)
print('\n  coefficients (t, p):')
for name, b, t, p in zip(full.params.index, full.params, full.tvalues,
                         full.pvalues):
    print(f'    {name:12s} {b:+9.4f}  t={t:+6.2f}  p={p:.3f}')

print('\n=== how much of the spread each accounts for ===')
print(f'  total between-facility variance in mean LOS: {tot_var:.3f} '
      f'(sd {np.sqrt(tot_var):.3f} days)')
print(f'  {"predictor":14s}{"alone R2":>10s}{"var explained":>15s}'
      f'{"drop from full":>16s}')
base = full.rsquared
for c, r in uni.items():
    if c == 'tp_gestao':
        rest = fit(['lap_share', 'volume', 'beds_surg', 'prof_case', 'has_lap'],
                   '_', dummies=False)
    else:
        cols = [x for x in ['lap_share', 'volume', 'beds_surg', 'prof_case',
                            'has_lap'] if x != c]
        rest = fit(cols, '_', dummies=True)
    print(f'  {c:14s}{r.rsquared:>10.3f}{r.rsquared*tot_var:>15.3f}'
          f'{base - rest.rsquared:>16.3f}')

print(f'\n=== residual ===')
print(f'  full model R2 = {full.rsquared:.3f}, adjusted = {full.rsquared_adj:.3f}')
print(f'  UNEXPLAINED = {1-full.rsquared:.1%} of variance '
      f'({(1-full.rsquared)*tot_var:.3f} of {tot_var:.3f})')
print(f'  residual sd = {np.sqrt(full.mse_resid):.3f} days against a raw sd of '
      f'{np.sqrt(tot_var):.3f}')
res = pd.Series(full.resid, index=f.index).sort_values()
print(f'  residual range {res.min():+.2f} to {res.max():+.2f} days')
print(f'\n  largest residuals (facility LOS unexplained by any predictor):')
sh = pd.concat([res.head(4), res.tail(4)])
for cnes, r in sh.items():
    print(f'    {cnes}  actual {f.los[cnes]:5.2f}  fitted '
          f'{f.los[cnes]-r:5.2f}  resid {r:+5.2f}  n={int(f.cases[cnes])}')

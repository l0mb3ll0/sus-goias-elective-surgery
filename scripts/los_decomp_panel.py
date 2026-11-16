"""Facility LOS decomposition fitted independently on 2024 and 2025, then the
residuals correlated across facilities appearing in both.

Both years use YEAR-SPECIFIC predictors so the two fits are genuinely independent:
beds from the monthly LT file for that year, management from monthly ST, and
laparoscopic equipment from the monthly EQ file rather than the 202606 snapshot.
That also removes the window mismatch the snapshot forced on the 2024 run; the
2024 numbers therefore differ slightly from the snapshot-based version, and both
are printed so the difference is visible rather than silent.

EQ code fields are zero-padded before comparison: TIPEQUIP switched from '3' to
'03' at 2025-09, and an unpadded match loses every laparoscope after that.

Model is unchanged and no predictors are added.

    python -m scripts.los_decomp_panel
"""
import glob
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import spearmanr, pearsonr

CHOL = ['0407030026', '0407030034']
PH_DOC = '000000000000000'
MINC = 30
SURG_BEDS = {'01','02','03','04','05','06','08','09','11','12','13','14','15',
             '16','67','90','91','10','68','83'}
PRED = ['lap_share', 'volume', 'beds_surg', 'prof_case', 'has_lap']

lt = pd.read_parquet('data/interim/cnes_lt_raw.parquet')
lt['co'] = lt.CODLEITO.astype(str).str.strip().str.zfill(2)
lt['sus'] = pd.to_numeric(lt.QT_SUS, errors='coerce').fillna(0)
lt['yr'] = lt.comp.astype(str).str[:4]
st = pd.read_parquet('data/interim/cnes_st_raw.parquet')
st['yr'] = st.comp.astype(str).str[:4]
eq = pd.read_parquet('data/interim/cnes/cnes_eq_GO_raw.parquet')
for c in ('TIPEQUIP', 'CODEQUIP'):
    eq[c] = eq[c].astype(str).str.strip().str.zfill(2)
eq['yr'] = eq.cm.astype(str).str[:4]


def build(year):
    rd = pd.concat([pd.read_parquet(f, columns=['N_AIH', 'CNES', 'PROC_REA',
                                                'DIAS_PERM'])
                    for f in sorted(glob.glob(
                        f'data/interim/sih/RDGO{year[2:]}*.parquet'))])
    for c in ('N_AIH', 'CNES', 'PROC_REA'):
        rd[c] = rd[c].astype(str).str.strip()
    rd = rd[rd.PROC_REA.isin(CHOL)].copy()
    rd['DIAS_PERM'] = pd.to_numeric(rd.DIAS_PERM, errors='coerce')
    rd['lap'] = (rd.PROC_REA == '0407030034').astype(int)

    sp = pd.read_parquet(f'data/interim/sih_sp/sp_GO_{year}.parquet',
                         columns=['SP_NAIH', 'SP_PF_DOC', 'SP_PF_CBO', 'SP_CNES'])
    for c in sp.columns:
        sp[c] = sp[c].astype(str).str.strip()
    att = set(sp[(sp.SP_PF_CBO == '225225') & (sp.SP_PF_DOC != PH_DOC)].SP_NAIH)
    n_before = len(rd)
    rd = rd[rd.N_AIH.isin(att)]
    print(f'{year}: {n_before:,} cholecystectomy AIHs, {len(rd):,} with an '
          f'identified 225225 surgeon ({100*len(rd)/n_before:.1f}%)')

    f = rd.groupby('CNES').agg(cases=('DIAS_PERM', 'size'),
                               los=('DIAS_PERM', 'mean'), lap_share=('lap', 'mean'))
    f = f[f.cases >= MINC].copy()
    spj = sp[(sp.SP_PF_DOC != PH_DOC) & sp.SP_NAIH.isin(set(rd.N_AIH))]
    f['prof_case'] = spj.groupby(['SP_CNES', 'SP_NAIH']).SP_PF_DOC.nunique() \
                        .groupby(level=0).mean().reindex(f.index)
    b = lt[(lt.yr == year) & lt.co.isin(SURG_BEDS)]
    f['beds_surg'] = b.groupby(['CNES', 'comp']).sus.sum().groupby('CNES').mean() \
                      .reindex(f.index)
    sy = st[st.yr == year]
    f['tp_gestao'] = sy.groupby('CNES').TPGESTAO.agg(
        lambda s: s.mode().iat[0] if len(s.mode()) else np.nan).reindex(f.index)
    l = eq[(eq.yr == year) & (eq.TIPEQUIP == '03') & (eq.CODEQUIP == '35')]
    lq = l.groupby('CNES').QT_EXIST.apply(
        lambda s: pd.to_numeric(s, errors='coerce').fillna(0).max())
    f['has_lap'] = (lq.reindex(f.index).fillna(0) > 0).astype(int)
    f['volume'] = f.cases
    drop = f[f[['prof_case', 'beds_surg', 'tp_gestao']].isna().any(axis=1)]
    if len(drop):
        print(f'  dropped for missing predictors: {len(drop)} {list(drop.index)}')
    return f.dropna(subset=['prof_case', 'beds_surg', 'tp_gestao'])


def fit(f, year):
    X = f[PRED].astype(float)
    X = X.join(pd.get_dummies(f.tp_gestao, prefix='g', drop_first=True).astype(float))
    r = sm.OLS(f.los.values, sm.add_constant(X)).fit()
    f = f.copy()
    f['fitted'] = r.fittedvalues
    f['resid'] = f.los - f.fitted
    print(f'\n{year}: n={len(f)}  R2={r.rsquared:.3f}  adjR2={r.rsquared_adj:.3f}  '
          f'resid sd={np.sqrt(r.mse_resid):.3f}')
    print(f'  LOS spread {f.los.min():.2f}-{f.los.max():.2f}, '
          f'variance {f.los.var():.3f}, unexplained {1-r.rsquared:.1%}')
    print(f'  {"term":12s}{"coef":>10s}{"t":>8s}{"p":>8s}')
    for n_, b_, t_, p_ in zip(r.params.index, r.params, r.tvalues, r.pvalues):
        print(f'  {n_:12s}{b_:>10.4f}{t_:>8.2f}{p_:>8.3f}')
    print('  univariate R2: ' + '  '.join(
        f'{c}={sm.OLS(f.los.values, sm.add_constant(f[[c]].astype(float))).fit().rsquared:.3f}'
        for c in PRED))
    return f, r


a, ra = fit(build('2024'), '2024')
b, rb = fit(build('2025'), '2025')

both = a.index.intersection(b.index)
print(f'\n=== residual stability ===')
print(f'  facilities modelled: 2024 {len(a)}, 2025 {len(b)}, in BOTH {len(both)}')
print(f'  only 2024: {sorted(set(a.index) - set(b.index))}')
print(f'  only 2025: {sorted(set(b.index) - set(a.index))}')
x, y = a.resid.reindex(both), b.resid.reindex(both)
rs, ps = spearmanr(x, y)
rp, pp = pearsonr(x, y)
print(f'\n  Spearman(resid 2024, resid 2025) = {rs:+.3f}  p={ps:.4f}  n={len(both)}')
print(f'  Pearson                          = {rp:+.3f}  p={pp:.4f}')
print(f'  sign agreement: {100*np.mean(np.sign(x) == np.sign(y)):.1f}% of facilities')
lo = a.los.reindex(both); lo2 = b.los.reindex(both)
print(f'  for reference, Spearman(mean LOS 2024, mean LOS 2025) = '
      f'{spearmanr(lo, lo2).statistic:+.3f}')
print(f'\n  largest 2024 residuals and their 2025 value:')
for cnes in a.resid.reindex(both).abs().sort_values(ascending=False).head(8).index:
    print(f'    {cnes}  2024 resid {a.resid[cnes]:+5.2f} (n={int(a.cases[cnes]):>4})'
          f'   2025 resid {b.resid[cnes]:+5.2f} (n={int(b.cases[cnes]):>4})')

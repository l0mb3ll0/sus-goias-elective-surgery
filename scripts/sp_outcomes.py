"""Surgeon annual volume against outcomes, 2024 cholecystectomy panel.

Joins SP (which professional operated) to RD (DIAS_PERM, MORTE) on the AIH number.
SP_NAIH <-> N_AIH, both 13-digit; the match rate is reported, never assumed.

ATTRIBUTION RULE, fixed before looking at outcomes. An AIH can carry more than
one 225225 professional. The operating surgeon is taken to be the one with the
most act rows on that AIH; ties and multi-surgeon frequencies are reported. AIHs
with no identified 225225 professional are counted and excluded, not imputed.

DECILES are of the surgeon's ANNUAL cholecystectomy case count, assigned at the
surgeon level then attached to the AIH, so a decile is a group of surgeons rather
than a group of cases.

    python -m scripts.sp_outcomes
"""
import glob
import numpy as np
import pandas as pd

CHOL = {'0407030026': 'open', '0407030034': 'laparoscopic'}
PH_DOC, PH_CBO = '000000000000000', '000000'
SURGEON = '225225'

sp = pd.read_parquet('data/interim/sih_sp/sp_GO_2024.parquet')
for c in ('SP_NAIH', 'SP_PF_DOC', 'SP_PF_CBO', 'SP_CNES', 'SP_PROCREA', 'cm'):
    sp[c] = sp[c].astype(str).str.strip()

rd = pd.concat([pd.read_parquet(f, columns=['N_AIH', 'CNES', 'PROC_REA', 'CAR_INT',
                                            'DIAS_PERM', 'MORTE', 'IDADE', 'SEXO'])
                for f in sorted(glob.glob('data/interim/sih/RDGO24*.parquet'))])
for c in ('N_AIH', 'CNES', 'PROC_REA'):
    rd[c] = rd[c].astype(str).str.strip()
rd = rd[rd.PROC_REA.isin(CHOL)].copy()
rd['approach'] = rd.PROC_REA.map(CHOL)
rd['DIAS_PERM'] = pd.to_numeric(rd.DIAS_PERM, errors='coerce')
rd['MORTE'] = pd.to_numeric(rd.MORTE, errors='coerce')
print(f'RD cholecystectomy AIHs 2024: {len(rd):,} '
      f'({rd.approach.value_counts().to_dict()})')

# ---- attribution -----------------------------------------------------------
s = sp[(sp.SP_PF_CBO == SURGEON) & (sp.SP_PF_DOC != PH_DOC)]
s = s[s.SP_NAIH.isin(set(rd.N_AIH))]
per = s.groupby(['SP_NAIH', 'SP_PF_DOC']).size().rename('acts').reset_index()
nsurg = per.groupby('SP_NAIH').SP_PF_DOC.nunique()
print(f'\nattribution:')
print(f'  AIHs with >=1 identified 225225: {len(nsurg):,} of {len(rd):,} '
      f'({100*len(nsurg)/len(rd):.1f}%)')
print(f'  225225 per AIH: {nsurg.value_counts().sort_index().head(6).to_dict()}')
per = per.sort_values(['SP_NAIH', 'acts'], ascending=[True, False])
ties = per.groupby('SP_NAIH').acts.apply(lambda a: len(a) > 1 and a.iat[0] == a.iat[1])
print(f'  AIHs where the top-two act counts tie: {int(ties.sum()):,} '
      f'({100*ties.mean():.1f}% of multi-surgeon AIHs resolved arbitrarily)')
main = per.drop_duplicates('SP_NAIH').set_index('SP_NAIH').SP_PF_DOC

d = rd.set_index('N_AIH')
d['surgeon'] = main
unmatched = int(d.surgeon.isna().sum())
print(f'  AIHs with no identified 225225, excluded: {unmatched:,} '
      f'({100*unmatched/len(d):.1f}%)')
d = d[d.surgeon.notna()].copy()

# ---- surgeon annual volume and deciles --------------------------------------
vol = d.groupby('surgeon').size().rename('annual')
print(f'\nsurgeons attributed: {len(vol):,}; annual volume median '
      f'{vol.median():.0f}, p90 {vol.quantile(.9):.0f}, max {int(vol.max())}')
dec = pd.qcut(vol.rank(method='first'), 10, labels=range(1, 11))
d['decile'] = d.surgeon.map(dec).astype(int)
d['annual'] = d.surgeon.map(vol)

def tab(df, label):
    g = df.groupby('decile').agg(
        surgeons=('surgeon', 'nunique'), cases=('DIAS_PERM', 'size'),
        vol_med=('annual', 'median'),
        los_mean=('DIAS_PERM', 'mean'), los_med=('DIAS_PERM', 'median'),
        morte_n=('MORTE', 'sum'), morte_pct=('MORTE', lambda x: 100 * x.mean()))
    print(f'\n{label}')
    print(f'  {"dec":>4}{"surg":>6}{"cases":>7}{"vol_med":>9}{"LOS mean":>10}'
          f'{"LOS med":>9}{"deaths":>8}{"death %":>9}')
    for r in g.itertuples():
        print(f'  {r.Index:>4}{r.surgeons:>6}{r.cases:>7}{r.vol_med:>9.0f}'
              f'{r.los_mean:>10.2f}{r.los_med:>9.1f}{int(r.morte_n):>8}'
              f'{r.morte_pct:>9.2f}')
    return g

tab(d, 'ALL cholecystectomy, by surgeon annual-volume decile')
for k in ('laparoscopic', 'open'):
    tab(d[d.approach == k], f'{k.upper()}')

# ---- the confound ----------------------------------------------------------
print('\n=== CONFOUND: is this surgeon or hospital? ===')
nf = d.groupby('decile').CNES.nunique()
print(f'  facilities represented per decile: {nf.to_dict()}')
hi = d[d.decile >= 9]; lo = d[d.decile <= 2]
print(f'  top-2 deciles span {hi.CNES.nunique()} facilities, '
      f'bottom-2 span {lo.CNES.nunique()}; overlap '
      f'{len(set(hi.CNES) & set(lo.CNES))} facilities')
lap = d.groupby('decile').approach.apply(lambda s: 100 * (s == 'laparoscopic').mean())
print(f'  laparoscopic share by decile: '
      f'{ {k: round(v, 1) for k, v in lap.items()} }')
fac_los = d.groupby('CNES').DIAS_PERM.mean()
fac_n = d.groupby('CNES').size()
big = fac_n[fac_n >= 30].index
print(f'  between-facility spread in mean LOS (facilities with >=30 cases, '
      f'n={len(big)}): {fac_los[big].min():.2f} to {fac_los[big].max():.2f}')
# within-facility: does volume still track LOS once the facility is held fixed?
d['fac_mean'] = d.CNES.map(fac_los)
d['los_dev'] = d.DIAS_PERM - d.fac_mean
w = d[d.CNES.isin(big)].groupby('decile').los_dev.agg(['mean', 'size'])
print(f'\n  LOS deviation from own-facility mean, by decile '
      f'(facilities with >=30 cases):')
for r in w.itertuples():
    print(f'    decile {r.Index:>2}: {r.mean:+.2f} days  (n={int(r.size)})')
share = d.groupby('CNES').decile.nunique()
print(f'\n  facilities whose cases all fall in ONE decile: '
      f'{int((share == 1).sum())} of {d.CNES.nunique()}')
print(f'  Spearman(surgeon annual volume, own-facility mean LOS) over surgeons: '
      f'{vol.to_frame().join(d.groupby("surgeon").fac_mean.first()).corr(method="spearman").iloc[0,1]:.3f}')

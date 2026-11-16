"""THROWAWAY diagnostic. Facility-level elective surgical bed-day utilisation, 2024-25.

Not part of the paper pipeline; writes nothing to numbers.json.

DEFINITIONS, stated before computing.

  Unit        the facility (CNES). Not the municipality: the CNES bed file has no
              municipality column, so a municipality version needs the
              establishment crosswalk extracted alongside this.
  Window      2024-01 .. 2025-12 on COMPETENCIA, the processing month, which is
              the key the bed panel is also on. See the edge-month note printed
              at the end.
  Capacity    QT_SUS summed over CODLEITO in the repo's 20-code surgical
              inpatient set, per facility-month, times 30 to give bed-days.
              A facility qualifies if it has >0 surgical SUS beds in at least
              one month of the window.
  Numerator   DIAS_PERM summed over elective surgical admissions at that
              facility-month: PROC_REA in SIGTAP group 04 and CAR_INT = 01.
  Utilisation pooled elective bed-days / pooled surgical bed-days over the
              window. Gross of urgent use, matching Section 3.5's "elective
              occupancy of surgical beds"; the urgent-netted variant is printed
              separately for contrast.
"""
import glob
import numpy as np, pandas as pd

INPAT = {'01','02','03','04','05','06','08','09','11','12','13','14','15','16',
         '67','90','91','10','68','83'}
LO, HI = '2024-01', '2025-12'

lt = pd.read_parquet('data/interim/cnes_lt_raw.parquet')
lt['sus'] = pd.to_numeric(lt.QT_SUS, errors='coerce').fillna(0)
lt['co'] = lt.CODLEITO.astype(str).str.zfill(2)
lt['cm'] = lt.comp.astype(str).str[:4] + '-' + lt.comp.astype(str).str[4:6]
beds = (lt[lt.co.isin(INPAT) & lt.cm.between(LO, HI)]
        .groupby(['CNES','cm']).sus.sum().rename('beds').reset_index())
beds = beds[beds.beds > 0]

cols = ['CNES','PROC_REA','CAR_INT','DIAS_PERM','COMPETENCIA','MUNIC_MOV']
a = pd.concat([pd.read_parquet(f, columns=cols)
               for f in sorted(glob.glob('data/interim/sih/RDGO2[45]*.parquet'))],
              ignore_index=True)
a = a[a.COMPETENCIA.between(LO, HI) & (a.PROC_REA.str[:2] == '04')]
el = a[a.CAR_INT == '01']
ur = a[a.CAR_INT != '01']

def days(df):
    return (df.groupby(['CNES','COMPETENCIA']).DIAS_PERM.sum()
            .rename('d').reset_index().rename(columns={'COMPETENCIA':'cm'}))

fm = (beds.merge(days(el).rename(columns={'d':'edays'}), on=['CNES','cm'], how='left')
          .merge(days(ur).rename(columns={'d':'udays'}), on=['CNES','cm'], how='left')
          .fillna({'edays':0,'udays':0}))
fm['bd'] = fm.beds * 30.0

f = fm.groupby('CNES').agg(bd=('bd','sum'), edays=('edays','sum'),
                           udays=('udays','sum'), months=('cm','size')).reset_index()
f['util'] = f.edays / f.bd
f['util_net'] = f.edays / (f.bd - f.udays).clip(lower=1)
ecases = el.groupby('CNES').size().rename('ecases')
f = f.merge(ecases, on='CNES', how='left').fillna({'ecases':0})

n = len(f)
print(f'facilities with >0 surgical SUS beds in 2024-25 : {n}')
print(f'pooled elective surgical bed-day utilisation     : {f.edays.sum()/f.bd.sum():.3f}')
print(f'  same, net of urgent surgical bed-days          : {f.edays.sum()/(f.bd.sum()-f.udays.sum()):.3f}')
print()
print('distribution of facility-level utilisation')
q = f.util.quantile([0,.1,.25,.5,.75,.9,.95,1])
for k, v in q.items():
    print(f'  p{int(k*100):<3d} {v:7.3f}')
print(f'  mean {f.util.mean():.3f}   sd {f.util.std():.3f}')
print()
band = [(0,0.01),(0.01,0.05),(0.05,0.10),(0.10,0.20),(0.20,0.50),(0.50,1.0),(1.0,np.inf)]
print('facilities by utilisation band')
for lo, hi in band:
    m = (f.util >= lo) & (f.util < hi)
    print(f'  {lo:>5.2f} to {hi if hi!=np.inf else 999:>6.2f} : {m.sum():4d}  ({m.sum()/n:5.1%})')
print()
u20 = f.util < 0.20
print(f'under 20 per cent utilisation                    : {u20.sum()} of {n} ({u20.sum()/n:.1%})')
print(f'  their share of all surgical bed-days           : {f[u20].bd.sum()/f.bd.sum():.1%}')
print(f'  their share of all elective bed-days           : {f[u20].edays.sum()/f.edays.sum():.1%}')
print()
for lab, m in [('zero elective cases', f.ecases == 0),
               ('under 50 elective cases over 24 months', f.ecases < 50),
               ('utilisation under 1 per cent', f.util < 0.01),
               ('utilisation under 5 per cent', f.util < 0.05)]:
    print(f'  capacity but {lab:<40s}: {m.sum():4d}  '
          f'({f[m].bd.sum()/f.bd.sum():5.1%} of surgical bed-days)')
print()
print('top 10 facilities by surgical bed-days, with utilisation')
top = f.nlargest(10, 'bd')
print(f"  {'CNES':9s}{'bed-days':>10s}{'elec bd':>9s}{'util':>7s}{'cases':>7s}")
for r in top.itertuples():
    print(f'  {r.CNES:9s}{r.bd:10.0f}{r.edays:9.0f}{r.util:7.3f}{int(r.ecases):7d}')
print()
print('WINDOW BASIS: COMPETENCIA (processing month), matching the bed panel key.')
print('Edge-month artifact: NOT excluded, and on this key it is small but real.')
print('  Section 2.3 measures a mean elective submission lag of 0.65 months, so')
print('  2024-01 carries some late-2023 admissions and some late-2025 admissions')
print('  land after 2025-12. On DT_INTER the same window would be right-censored')
print('  at the panel edge instead. Neither is excluded here; the effect is a')
print('  fraction of one month at each end of a 24-month window.')

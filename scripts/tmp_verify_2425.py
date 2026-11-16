"""THROWAWAY verification. Reproduces the 2024-25 facility utilisation figures
and qualifies the zero-elective set. Writes nothing; modifies nothing.

DEFINITIONS -- identical to scripts/tmp_util_2425.py, restated so they are on
the record rather than inherited silently:

  bed set    the repo's 20-code surgical inpatient set on CODLEITO:
             01 02 03 04 05 06 08 09 10 11 12 13 14 15 16 67 68 83 90 91
             (CIRURGIA GERAL is 03; the set also carries obstetric-surgical 10,
             paediatric-surgical 68 and surgical ICU 83)
  capacity   QT_SUS summed over those codes per facility-month, x30 = bed-days
  qualifies  >0 surgical SUS beds in at least one month of the window
  elective   PROC_REA group 04 AND CAR_INT == '01'
  urgent     PROC_REA group 04 AND CAR_INT != '01'  (in this extract that is '02')
  window     2024-01 .. 2025-12 inclusive, on COMPETENCIA (processing month)
  util       pooled elective DIAS_PERM / pooled surgical bed-days, gross of urgent
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
win = lt[lt.cm.between(LO, HI)]
beds = win[win.co.isin(INPAT)].groupby(['CNES','cm']).sus.sum().rename('beds').reset_index()
beds = beds[beds.beds > 0]
allb = win.groupby('CNES').sus.sum().rename('all_sus_bedmonths').reset_index()

cols = ['CNES','PROC_REA','CAR_INT','DIAS_PERM','COMPETENCIA','DT_INTER']
a = pd.concat([pd.read_parquet(f, columns=cols)
               for f in sorted(glob.glob('data/interim/sih/RDGO2[45]*.parquet'))],
              ignore_index=True)
a = a[a.COMPETENCIA.between(LO, HI) & (a.PROC_REA.str[:2] == '04')]
el, ur = a[a.CAR_INT == '01'], a[a.CAR_INT != '01']
print('CAR_INT values present in group 04, this window:',
      sorted(a.CAR_INT.dropna().unique().tolist()))

def agg(df, nm):
    g = df.groupby(['CNES','COMPETENCIA']).agg(d=('DIAS_PERM','sum'), n=('DIAS_PERM','size'))
    return g.rename(columns={'d': nm+'days', 'n': nm+'cases'}).reset_index() \
            .rename(columns={'COMPETENCIA': 'cm'})

fm = (beds.merge(agg(el,'e'), on=['CNES','cm'], how='left')
          .merge(agg(ur,'u'), on=['CNES','cm'], how='left')
          .fillna({'edays':0,'ecases':0,'udays':0,'ucases':0}))
fm['bd'] = fm.beds * 30.0
f = fm.groupby('CNES').agg(bd=('bd','sum'), edays=('edays','sum'), ecases=('ecases','sum'),
                           udays=('udays','sum'), ucases=('ucases','sum'),
                           surg_bedmonths=('beds','sum')).reset_index()
f['util'] = f.edays / f.bd

# ---------------- TASK 1 ----------------
n = len(f); zero = f.ecases == 0; u20 = f.util < 0.20
print('\n== TASK 1: reproduce ==')
exp = {'facilities': 275, 'zero-elective': 112, 'under 20% util': 246}
got = {'facilities': n, 'zero-elective': int(zero.sum()), 'under 20% util': int(u20.sum())}
for k in exp:
    print(f'  {k:16s} expected {exp[k]:5d}   got {got[k]:5d}   {"MATCH" if exp[k]==got[k] else "*** DIFFERS"}')
sb, se = f[u20].bd.sum()/f.bd.sum()*100, f[u20].edays.sum()/f.edays.sum()*100
for k, e, g in (('u20 share bed-days', 80.3, sb), ('u20 share elec bed-days', 36.3, se)):
    print(f'  {k:24s} expected {e:5.1f}%  got {g:5.1f}%  {"MATCH" if abs(e-g)<0.05 else "*** DIFFERS"}')

# ---------------- TASK 2 ----------------
est = pd.read_parquet('data/ref/cnes/tbEstabelecimento_202606.parquet')
lab = pd.read_csv('data/ref/cnes/tbTipoUnidade_202606.csv', dtype=str)
tmap = dict(zip(lab.CO_TIPO_UNIDADE.str.zfill(2), lab.DS_TIPO_UNIDADE))
est['tp'] = est.TP_UNIDADE.astype(str).str.zfill(2)
est['ds'] = est.tp.map(tmap)
HOSP = {'05','07','15','36','62','67','am'}   # placeholder, resolved below
# hospital-type = any DS containing HOSPITAL, plus PRONTO SOCORRO GERAL
est['is_hosp'] = est.ds.fillna('').str.contains('HOSPITAL') | \
                 est.ds.fillna('').str.contains('PRONTO SOCORRO GERAL')
j = f.merge(est[['CO_CNES','NO_FANTASIA','NO_RAZAO_SOCIAL','tp','ds','is_hosp']],
            left_on='CNES', right_on='CO_CNES', how='left').merge(allb, on='CNES', how='left')
j['surg_beds_avg'] = j.surg_bedmonths / 24.0
j['all_beds_avg'] = j.all_sus_bedmonths / 24.0
print(f'\n  establishment join: {j.ds.notna().sum()} of {len(j)} matched; '
      f'{j.ds.isna().sum()} unmatched')
print('  type field used: TP_UNIDADE, labelled from tbTipoUnidade202606.csv (39 rows)')

z = j[zero.values].copy().sort_values('surg_beds_avg', ascending=False)
print(f'\n== TASK 2: the {len(z)} zero-elective facilities ==')
print(f"  {'CNES':8s} {'type':>4s} {'surgbeds':>9s} {'allbeds':>8s}  name / establishment type")
for r in z.itertuples():
    print(f'  {r.CNES:8s} {str(r.tp):>4s} {r.surg_beds_avg:9.1f} {r.all_beds_avg:8.1f}  '
          f'{str(r.NO_FANTASIA)[:34]:34s} | {str(r.ds)[:34]}')

def summarise(sub, label):
    nh = sub.is_hosp.fillna(False)
    lt5 = sub.surg_beds_avg < 5
    defen = nh & ~lt5
    print(f'\n  {label} (n={len(sub)})')
    print(f'    hospital-type                        : {int(nh.sum()):4d}')
    print(f'    non-hospital (clinic/post/other)     : {int((~nh).sum()):4d}')
    print(f'    fewer than 5 surgical beds (avg)     : {int(lt5.sum()):4d}')
    print(f'    hospital-type AND 5+ surgical beds   : {int(defen.sum()):4d}   <- defensible')
    print(f'    defensible share of subset bed-days  : {sub[defen].bd.sum()/sub.bd.sum():6.1%}')
    print('    non-hospital types present:')
    for d, c in sub[~nh].ds.value_counts().head(6).items():
        print(f'      {c:3d}  {d}')
    return defen

dz = summarise(z, 'the 112 zero-elective')
d2 = summarise(j[u20.values].copy(), 'the 246 under-20%')

# ---------------- TASK 3 ----------------
print(f'\n== TASK 3: urgent activity among the {len(z)} zero-elective ==')
has_u = z.ucases > 0
print(f'  performed urgent group-04 admissions      : {int(has_u.sum())} of {len(z)} ({has_u.mean():.1%})')
print(f'  did nothing at all in group 04            : {int((~has_u).sum())}')
if has_u.any():
    v = z[has_u].ucases
    print(f'  among those with any: median {v.median():.0f}, mean {v.mean():.0f}, '
          f'min {v.min():.0f}, max {v.max():.0f}, total {v.sum():.0f} over 24 months')
    hu = has_u & z.is_hosp.fillna(False) & (z.surg_beds_avg >= 5)
    print(f'  of the defensible subset, urgent-active   : {int(hu.sum())} of {int(dz.sum())}')

# ---------------- TASK 4 ----------------
print('\n== TASK 4: window basis and submission lag ==')
print('  window basis: COMPETENCIA (processing month), matching the bed panel key.')
comp = pd.PeriodIndex(el.COMPETENCIA, freq='M')
adm = pd.PeriodIndex(pd.to_datetime(el.DT_INTER, format='%Y%m%d', errors='coerce'), freq='M')
lag = pd.Series((comp.asi8 - adm.asi8).astype(float)).dropna()
print(f'  elective submission lag, this window: mean {lag.mean():.3f} months, '
      f'median {lag.median():.0f}, n={len(lag)}')
print(f'    share lag 0: {(lag==0).mean():.1%}   lag>=1: {(lag>=1).mean():.1%}   '
      f'lag>=2: {(lag>=2).mean():.1%}')
alt = el.assign(adm=pd.to_datetime(el.DT_INTER, format='%Y%m%d', errors='coerce'))
alt = alt[(alt.adm >= '2024-01-01') & (alt.adm <= '2025-12-31')]
print(f'  cases in window on COMPETENCIA: {len(el)}   on DT_INTER: {len(alt)}   '
      f'difference: {len(alt)-len(el):+d} ({(len(alt)-len(el))/len(el):+.2%})')

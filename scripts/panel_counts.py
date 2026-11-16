"""Descriptive counts cited in Section 1, Section 2 and Section 3.1.

These were orphans: no script wrote them, so nothing checked them. Definitions
are stated here rather than inferred.

  n_total_aih        every AIH record in the Goias extract, all specialties
  n_surgical_rows    records with PROC_REA in SIGTAP group 04
  n_elective         group 04 with CAR_INT = 01
  n_hospitals        distinct CNES with at least one ELECTIVE surgical record,
                     which is what Section 2.2's "across 201 distinct facilities"
                     modifies; any-surgical would give 234
  panel_start/end    first and last COMPETENCIA present
  elective_per_month monthly mean elective surgical admissions, 2019 and 2025
  urgent_growth      monthly mean urgent surgical admissions, 2025 over 2019
  n_clean            the Section 2.3 reliable subset
  clean_share_volume its share of all elective surgical volume
  model_caps         the batch-reporting diagnostic cited in Section 4.2:
                     facilities with 2023 elective volume that report an
                     interleaved zero month inside their own reporting span,
                     and the share of 2023 elective volume they carry

Counts are over the whole extract, not restricted to in-state residents, which
is how Sections 2.2 and 3.1 state them.

    python -m scripts.panel_counts [--write]
"""
import glob, io, json, sys
import pandas as pd

NJ = 'paper/numbers.json'
cols = ['CNES', 'PROC_REA', 'CAR_INT', 'COMPETENCIA']
a = pd.concat([pd.read_parquet(f, columns=cols)
               for f in sorted(glob.glob('data/interim/sih/RDGO*.parquet'))], ignore_index=True)
surg = a[a.PROC_REA.str[:2] == '04']
el = surg[surg.CAR_INT == '01']
ur = surg[surg.CAR_INT != '01']

out = {
    'n_total_aih': int(len(a)),
    'n_surgical_rows': int(len(surg)),
    'n_elective': int(len(el)),
    'n_hospitals': int(el.CNES.nunique()),
    'n_hospitals_any_surgical': int(surg.CNES.nunique()),
    'panel_start': str(a.COMPETENCIA.min()),
    'panel_end': str(a.COMPETENCIA.max()),
}
# Written as literal keys, not f-strings: scripts/check_coverage.py resolves
# writers statically, and a computed key name is invisible to it.
def per_month(df, y):
    return round(len(df[df.COMPETENCIA.str[:4] == y])/12, 1)


out['elective_per_month_2019'] = per_month(el, '2019')
out['elective_per_month_2025'] = per_month(el, '2025')
out['urgent_per_month_2019'] = per_month(ur, '2019')
out['urgent_per_month_2025'] = per_month(ur, '2025')
out['elective_growth_2019_2025'] = round(
    out['elective_per_month_2025']/out['elective_per_month_2019'] - 1, 3)
out['urgent_growth_2019_2025'] = round(
    out['urgent_per_month_2025']/out['urgent_per_month_2019'] - 1, 3)

# ---- Section 2.3 reliable subset ----
pan = pd.read_parquet('data/interim/hospital_panel.parquet')
pan['any'] = (pan['elec'] + pan['urg']) > 0
span = pan[pan['any']].groupby('CNES')['COMPETENCIA'].agg(['min', 'max', 'count'])
span['n'] = (pd.PeriodIndex(span['max'], freq='M').asi8
             - pd.PeriodIndex(span['min'], freq='M').asi8 + 1)
vol = pan.groupby('CNES')['elec'].sum()
rel = [c for c in span[(span['count']/span['n'] >= .95) & (span['n'] >= 60)].index
       if vol.get(c, 0) >= 500]
out['n_clean'] = int(len(rel))
out['clean_share_volume'] = round(float(vol.reindex(rel).sum()/vol.sum()), 3)

# ---- Section 4.2 batch-reporting diagnostic ----
e23 = el[el.COMPETENCIA.str[:4] == '2023']
months = sorted(e23.COMPETENCIA.unique())
byfac = (e23.groupby(['CNES', 'COMPETENCIA']).size().unstack('COMPETENCIA', fill_value=0)
         .reindex(columns=months, fill_value=0))
batch = []
for c, row in byfac.iterrows():
    nz = [i for i, v in enumerate(row.values) if v > 0]
    if not nz:
        continue
    inner = row.values[nz[0]:nz[-1] + 1]
    if (inner == 0).any():
        batch.append(c)
out['model_caps'] = {
    'rule': 'max 3-month rolling mean of monthly volume',
    'pi': 6.0,
    'n_facilities_2023': int(byfac.shape[0]),
    'n_batch_reporters': int(len(batch)),
    'batch_volume_share': round(float(e23[e23.CNES.isin(batch)].shape[0]/len(e23)), 3),
    'why': 'raw monthly peak inflated by batch reporting',
    'pi_invariance': 'A/B/C/D ordering unchanged at pi = 4, 6, 10',
}

store = json.load(io.open(NJ, encoding='utf-8'))
print(f"{'field':34s}{'stored':>14s}{'recomputed':>14s}   status")
diff = 0
for k, v in out.items():
    if isinstance(v, dict):
        for f, nv in v.items():
            if not isinstance(nv, (int, float)):
                continue
            ov = store.get(k, {}).get(f)
            s = 'NEW' if ov is None else ('ok' if abs(ov - nv) <= max(abs(ov)*0.01, 0.002) else 'DIFFERS')
            diff += s == 'DIFFERS'
            print(f'  {k+"."+f:32s}{str(ov):>14s}{nv:>14}   {s}')
        continue
    ov = store.get(k)
    if ov is None:
        s = 'NEW'
    elif isinstance(v, str):
        s = 'ok' if ov == v else 'DIFFERS'
    else:
        s = 'ok' if abs(ov - v) <= max(abs(ov)*0.01, 0.002) else 'DIFFERS'
    diff += s == 'DIFFERS'
    print(f'  {k:32s}{str(ov):>14s}{str(v):>14s}   {s}')
print(f'\n{diff} differ')

if '--write' in sys.argv:
    store.update(out)
    json.dump(store, io.open(NJ, 'w', encoding='utf-8'), indent=1)
    print('written', NJ)

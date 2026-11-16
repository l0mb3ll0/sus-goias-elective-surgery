"""Re-derive the tubal-ligation sentence in section 3.2 (347 of 414 at 16 of 35).

Read-only: does not write numbers.json. Run from the repo root; set SIH_DIR if
the parquet files live elsewhere.
Prior window is 2019-2022, matching the paper's text ("between 2019 and 2022").
"""
import glob, os
import pandas as pd

fr = [pd.read_parquet(f, columns=['CNES', 'PROC_REA', 'CAR_INT', 'COMPETENCIA'])
      for f in sorted(glob.glob(os.environ.get('SIH_DIR', 'data/interim/sih') + '/RDGO*.parquet'))]
a = pd.concat(fr, ignore_index=True)
a['CNES'] = a.CNES.astype(str).str.strip()
a['yr'] = a.COMPETENCIA.astype(str).str[:4]
a['el'] = (a.PROC_REA.astype(str).str[:2] == '04') & \
          (a.CAR_INT.astype(str).str.strip() == '01')
a['p'] = a.PROC_REA.astype(str).str[:4]
e = a[a.el]
S = {y: set(map(tuple, e[e.yr == y][['CNES', 'p']].drop_duplicates().values))
     for y in ('2019', '2023')}
NEW = S['2023'] - S['2019']
fac09 = {k[0] for k in NEW if k[1] == '0409'}
TL = e[e.PROC_REA.astype(str).isin(['0409060186', '0409060313'])]
tl23 = TL[(TL.yr == '2023') & TL.CNES.isin(fac09)]
prior = set(TL[TL.yr.isin(('2019', '2020', '2021', '2022'))].CNES)
ov = fac09 & prior
v = int(TL[(TL.yr == '2023') & TL.CNES.isin(ov)].shape[0])
print(f'facilities (new 0409 pairs): {len(fac09)}')
print(f'tubal ligations 2023 at those facilities: {len(tl23)}')
print(f'facilities with prior 2019-2022 tubal ligation: {len(ov)}')
print(f'2023 cases at those: {v}')
ok = (len(fac09), len(tl23), len(ov), v) == (35, 414, 16, 347)
print('REPRODUCES 347 of 414 at 16 of 35:', ok)

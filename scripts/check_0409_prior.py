"""Does the tubal-ligation claim survive the monthly panel?

Section 3.3 says a substantial part of the entrant expansion is elective
sterilisation "becoming available at facilities that did not previously offer
it". Checked here against monthly activity 2019-2022.
"""
import glob, io, sys
import pandas as pd

fr = [pd.read_parquet(f, columns=['CNES', 'PROC_REA', 'CAR_INT', 'COMPETENCIA'])
      for f in sorted(glob.glob('data/interim/sih/RDGO*.parquet'))]
a = pd.concat(fr, ignore_index=True)
a['CNES'] = a.CNES.astype(str).str.strip()
a['yr'] = a.COMPETENCIA.astype(str).str[:4]
a['comp'] = a.COMPETENCIA.astype(str).str.strip()
a['el'] = (a.PROC_REA.astype(str).str[:2] == '04') & \
          (a.CAR_INT.astype(str).str.strip() == '01')
a['p'] = a.PROC_REA.astype(str).str[:4]
e = a[a.el]
S = {y: set(map(tuple, e[e.yr == y][['CNES', 'p']].drop_duplicates().values))
     for y in ('2019', '2023')}
NEW = S['2023'] - S['2019']

for grp in ('0409', '0407', '0408'):
    g = {k for k in NEW if k[1] == grp}
    nc = e[(e.yr == '2023')].merge(pd.DataFrame(list(g), columns=['CNES', 'p']),
                                   on=['CNES', 'p'])
    pri = set(map(tuple, e[e.yr.isin(('2020', '2021', '2022'))]
                  [['CNES', 'p']].drop_duplicates().values))
    with_prior = {k for k in g if k in pri}
    nc['k'] = list(zip(nc.CNES, nc.p))
    vp = int(nc.k.isin(with_prior).sum())
    print(f'{grp}: {len(g)} new pairs, {len(nc):,} cases')
    print(f'   pairs active in 2020-2022: {len(with_prior)} ({100*len(with_prior)/len(g):.1f}%)')
    print(f'   cases at those pairs     : {vp:,} ({100*vp/len(nc):.1f}%)')

# tubal ligation specifically
# 0409060089 is not a SIGTAP code and returns zero rows. The sterilisation
# codes are 0409060186 (laqueadura tubaria) and 0409060313 (same admission as
# a normal delivery), confirmed against data/ref/sigtap_procedimentos.csv.
TL = e[e.PROC_REA.astype(str).isin(['0409060186', '0409060313'])]
print(f"\ntubal ligation 0409060089: {len(TL):,} elective cases 2019-2025")
print('   by year:', TL.groupby('yr').size().to_dict())
g09 = {k for k in NEW if k[1] == '0409'}
fac09 = {k[0] for k in g09}
tl23 = TL[(TL.yr == '2023') & TL.CNES.isin(fac09)]
print(f'   at the {len(fac09)} new-0409 facilities in 2023: {len(tl23):,} cases')
pri_tl = set(TL[TL.yr.isin(('2019', '2020', '2021', '2022'))].CNES)
overlap = fac09 & pri_tl
print(f'   of those facilities, performed tubal ligation in 2020-2022: '
      f'{len(overlap)} of {len(fac09)}')
if overlap:
    v = int(TL[(TL.yr == '2023') & TL.CNES.isin(overlap)].shape[0])
    print(f'   2023 tubal-ligation cases at facilities that DID previously '
          f'offer it: {v:,} of {len(tl23):,} ({100*v/max(1,len(tl23)):.1f}%)')


if '--write' in sys.argv:
    import collections, json
    NJ = 'paper/numbers.json'
    store = json.load(io.open(NJ, encoding='utf-8'),
                      object_pairs_hook=collections.OrderedDict)
    n09 = nc[nc.p == '0409'] if 'nc' in dir() else None
    sub = {}
    for grp in ('0407', '0409', '0408'):
        g = {k for k in NEW if k[1] == grp}
        cc = e[e.yr == '2023'].merge(pd.DataFrame(list(g), columns=['CNES', 'p']),
                                     on=['CNES', 'p'])
        pri = set(map(tuple, e[e.yr.isin(('2020', '2021', '2022'))]
                      [['CNES', 'p']].drop_duplicates().values))
        wp = {k for k in g if k in pri}
        cc['k'] = list(zip(cc.CNES, cc.p))
        sub[f'{grp}_pair_share'] = round(len(wp)/len(g), 3)
        sub[f'{grp}_case_share'] = round(int(cc.k.isin(wp).sum())/len(cc), 3)
    store['subgroup_prior_activity'] = {k: sub[k] for k in sorted(sub)}
    nc9 = e[e.yr == '2023'].merge(
        pd.DataFrame([k for k in NEW if k[1] == '0409'], columns=['CNES', 'p']),
        on=['CNES', 'p'])
    vc = nc9.PROC_REA.astype(str).value_counts()
    fac9 = {k[0] for k in NEW if k[1] == '0409'}
    TLc = e[e.PROC_REA.astype(str).isin(['0409060186', '0409060313'])]
    priT = set(TLc[TLc.yr.isin(('2019', '2020', '2021', '2022'))].CNES)
    store['subgroup_0409_composition'] = {
        'new_0409_cases': int(len(nc9)),
        'hysterectomy': int(vc.get('0409060135', 0)),
        'postectomy': int(vc.get('0409050083', 0)),
        'vasectomy': int(vc.get('0409040240', 0)),
        'tubal_ligation': int(vc.get('0409060186', 0)),
        'sterilisation_combined': int(vc.get('0409060186', 0) + vc.get('0409040240', 0)),
        'tubal_2023_at_facilities_with_prior':
            int(len(TLc[(TLc.yr == '2023') & TLc.CNES.isin(fac9 & priT)])),
        'facilities_with_prior_tubal': int(len(fac9 & priT)),
        'new_0409_facilities': int(len(fac9)),
    }
    io.open(NJ, 'w', encoding='utf-8').write(json.dumps(store, indent=1) + '\n')
    print('wrote subgroup_prior_activity, subgroup_0409_composition')

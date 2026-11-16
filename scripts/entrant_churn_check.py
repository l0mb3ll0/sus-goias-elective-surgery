"""Reproduce Section 3.3's pair churn, then re-examine it on the monthly panel.

REPRODUCTION FIRST. Nothing is reinterpreted until the paper's counts are matched.

DEFINITIONAL CHOICES
  pair       (CNES, 4-digit SIGTAP subgroup)
  elective   PROC_REA group 04 and CAR_INT == '01'
  presence   >=1 elective case in the calendar year (a pair is a STATE)
  scope      the paper states these counts are "over every facility with
             elective volume", NOT bed-restricted. The bed-restricted version
             is the model option set, 563/637. The brief asked for the
             bed-restricted basis; both are computed and labelled, and the
             unrestricted one is the paper's.
  residency  run both ways, since the paper does not say.

    python -m scripts.entrant_churn_check
"""
import glob, io
import numpy as np
import pandas as pd

SURG_BEDS = {'01','02','03','04','05','06','08','09','11','12','13','14','15',
             '16','67','90','91','10','68','83'}
TARGET = {'new': 284, 'lost': 192, 'p2019': 574, 'p2023': 666,
          'cases': 21845, 'share': 0.275, 'absent_cases': 18370,
          'inc_cases': 3475, 'extensive': 0.841}


def load():
    fr = []
    for f in sorted(glob.glob('data/interim/sih/RDGO*.parquet')):
        d = pd.read_parquet(f, columns=['CNES', 'PROC_REA', 'CAR_INT',
                                        'COMPETENCIA', 'MUNIC_RES', 'DIAS_PERM'])
        fr.append(d)
    a = pd.concat(fr, ignore_index=True)
    a['sg'] = a.PROC_REA.astype(str).str[:2]
    a['el'] = (a.sg == '04') & (a.CAR_INT.astype(str).str.strip() == '01')
    a['p'] = a.PROC_REA.astype(str).str[:4]
    a['i'] = a.MUNIC_RES.astype(str).str[:6]
    a['comp'] = a.COMPETENCIA.astype(str).str.strip()
    a['yr'] = a.comp.str[:4]
    a['CNES'] = a.CNES.astype(str).str.strip()
    return a


a = load()
ref = pd.read_csv('data/ref/ibge_municipios_go.csv', dtype=str)
GO = set(ref.cod6)
print(f'loaded {len(a):,} admissions; elective surgical {int(a.el.sum()):,}')

lt = pd.read_parquet('data/interim/cnes_lt_raw.parquet')
lt['co'] = lt.CODLEITO.astype(str).str.strip().str.zfill(2)
lt['sus'] = pd.to_numeric(lt.QT_SUS, errors='coerce').fillna(0)
lt['yr'] = lt.comp.astype(str).str[:4]


def bedok(year, el):
    beds = lt[(lt.yr == year) & lt.co.isin(SURG_BEDS)] \
        .groupby(['CNES', 'comp']).sus.sum().groupby('CNES').mean()
    urg = a[(a.sg == '04') & (~a.el) & (a.yr == year)] \
        .groupby('CNES').DIAS_PERM.sum() / 12.0
    B = (beds * 30.0).sub(urg, fill_value=0).clip(lower=0)
    return set(B[B > 0].index)


print('\n=== REPRODUCTION: calendar-year pair presence ===')
best = None
for instate in (False, True):
    e = a[a.el & (a.i.isin(GO) if instate else True)]
    for bedres in (False, True):
        s = {}
        for y in ('2019', '2023'):
            sub = e[e.yr == y]
            if bedres:
                sub = sub[sub.CNES.isin(bedok(y, e))]
            s[y] = set(map(tuple, sub[['CNES', 'p']].drop_duplicates().values))
        new, lost = s['2023'] - s['2019'], s['2019'] - s['2023']
        lab = f'{"in-state" if instate else "all resid"}, ' \
              f'{"bed-restricted" if bedres else "all facilities"}'
        hit = (len(new) == TARGET['new'] and len(lost) == TARGET['lost'])
        print(f'  {lab:34s} 2019 {len(s["2019"]):>4}  2023 {len(s["2023"]):>4}  '
              f'new {len(new):>4}  lost {len(lost):>4}  churn {len(new)+len(lost):>4}'
              f'{"   <== MATCHES PAPER" if hit else ""}')
        if hit:
            best = (instate, s, new, lost)

if best is None:
    print('\nSTOP: the paper counts do not reproduce under any of the four '
          'combinations. Reporting the discrepancy rather than tuning to fit.')
    raise SystemExit(1)

instate, S, NEW, LOST = best
e = a[a.el & (a.i.isin(GO) if instate else True)]
print(f'\n  reproduced with residency={"in-state" if instate else "all"}, '
      f'all facilities')

nc = e[(e.yr == '2023')].merge(pd.DataFrame(list(NEW), columns=['CNES', 'p']),
                               on=['CNES', 'p'])
tot23 = int((e.yr == '2023').sum())
print(f'  new-pair cases 2023 : {len(nc):,}  (paper {TARGET["cases"]:,})')
print(f'  share of 2023 volume: {len(nc)/tot23:.3f}  (paper {TARGET["share"]})')

fac19 = set(e[e.yr == '2019'].CNES)
nc_abs = nc[~nc.CNES.isin(fac19)]
print(f'  cases at facilities absent from 2019 elective: {len(nc_abs):,} '
      f'(paper {TARGET["absent_cases"]:,})')
print(f'  cases at incumbents adding a subgroup       : {len(nc)-len(nc_abs):,} '
      f'(paper {TARGET["inc_cases"]:,})')
print(f'  extensive share: {len(nc_abs)/len(nc):.3f}  (paper {TARGET["extensive"]})')

# ---------------------------------------------------------------- monthly ---
print('\n=== MONTHLY PANEL: were the 284 "new" pairs really new? ===')
act = e.groupby(['CNES', 'p', 'yr']).size()
newdf = pd.DataFrame(list(NEW), columns=['CNES', 'p'])
for y in ('2019', '2020', '2021', '2022'):
    hit = [tuple(r) in act.index.droplevel(2)[act.index.get_level_values(2) == y]
           for r in newdf.values] if False else None
prior = {}
for y in ('2019', '2020', '2021', '2022'):
    keys = set(map(tuple, e[e.yr == y][['CNES', 'p']].drop_duplicates().values))
    prior[y] = {k for k in NEW if k in keys}
    print(f'  active in {y}: {len(prior[y]):>4} of {len(NEW)} '
          f'({100*len(prior[y])/len(NEW):.1f}%)')
anyprior = set().union(*prior.values())
print(f'  active in ANY of 2019-2022 (i.e. dark-and-returned): {len(anyprior)} '
      f'of {len(NEW)} ({100*len(anyprior)/len(NEW):.1f}%)')
print(f'  genuinely absent 2019-2022                        : '
      f'{len(NEW)-len(anyprior)} ({100*(len(NEW)-len(anyprior))/len(NEW):.1f}%)')

pre = e[e.yr.isin(('2019', '2020', '2021', '2022'))]
pre_k = pre.set_index(['CNES', 'p'])
mo = pre.groupby(['CNES', 'p']).comp.nunique()
vo = pre.groupby(['CNES', 'p']).size()
sel = [k for k in anyprior]
if sel:
    idx = pd.MultiIndex.from_tuples(sel, names=['CNES', 'p'])
    m_, v_ = mo.reindex(idx).fillna(0), vo.reindex(idx).fillna(0)
    print(f'  for those with prior activity: months of activity before 2023 '
          f'median {m_.median():.0f}, p90 {m_.quantile(.9):.0f}, max {int(m_.max())}')
    print(f'                                 prior volume median {v_.median():.0f}, '
          f'p90 {v_.quantile(.9):.0f}, max {int(v_.max())}, total {int(v_.sum()):,}')

# volume split
nc['k'] = list(zip(nc.CNES, nc.p))
v_dark = int(nc.k.isin(anyprior).sum())
v_true = len(nc) - v_dark
print(f'\n  of the {len(nc):,} cases carried by the "new" pairs:')
print(f'    at pairs with NO prior activity 2019-2022: {v_true:,} '
      f'({100*v_true/len(nc):.1f}%)  = {v_true/tot23:.3f} of 2023 volume')
print(f'    at pairs that went dark and returned     : {v_dark:,} '
      f'({100*v_dark/len(nc):.1f}%)  = {v_dark/tot23:.3f} of 2023 volume')

# ---- reverse: the 192 lost pairs -------------------------------------------
print('\n=== the 192 "lost" pairs: dark or gone? ===')
for y in ('2024', '2025'):
    keys = set(map(tuple, e[e.yr == y][['CNES', 'p']].drop_duplicates().values))
    k = {x for x in LOST if x in keys}
    print(f'  active in {y}: {len(k):>4} of {len(LOST)} ({100*len(k)/len(LOST):.1f}%)')
k2 = set(map(tuple, e[e.yr.isin(('2024', '2025'))][['CNES', 'p']]
             .drop_duplicates().values))
back = {x for x in LOST if x in k2}
print(f'  active in 2024 OR 2025 (returned): {len(back)} of {len(LOST)} '
      f'({100*len(back)/len(LOST):.1f}%)')

# ---- facility-level claim ----------------------------------------------------
print('\n=== facility claim: absent from 2019 in every month? ===')
absent_fac = set(nc_abs.CNES)
print(f'  facilities carrying the extensive-margin cases: {len(absent_fac)}')
el19 = e[e.yr == '2019']
in19 = {f for f in absent_fac if f in set(el19.CNES)}
print(f'  of those, with ANY elective month in 2019: {len(in19)} '
      f'(by construction 0 -- the classifier uses the same data)')
anysih = a[a.yr == '2019']
in_sih = {f for f in absent_fac if f in set(anysih.CNES)}
print(f'  present in 2019 SIH at all (any admission, elective or not): '
      f'{len(in_sih)} of {len(absent_fac)} ({100*len(in_sih)/len(absent_fac):.1f}%)')
cases_in_sih = int(nc_abs[nc_abs.CNES.isin(in_sih)].shape[0])
print(f'  extensive-margin cases at facilities that WERE in 2019 SIH: '
      f'{cases_in_sih:,} of {len(nc_abs):,} ({100*cases_in_sih/len(nc_abs):.1f}%)')
print(f'  extensive share recomputed excluding those: '
      f'{(len(nc_abs)-cases_in_sih)/len(nc):.3f} against the paper 0.841')

if '--write' in __import__('sys').argv:
    import json, collections
    NJ = 'paper/numbers.json'
    store = json.load(io.open(NJ, encoding='utf-8'),
                      object_pairs_hook=collections.OrderedDict)
    store['pair_intermittency'] = {
        'new_pairs_active_2020_2022': len(anyprior),
        'new_pairs_total': len(NEW),
        'new_pairs_prior_share': round(len(anyprior)/len(NEW), 3),
        'new_pair_cases_with_prior': v_dark,
        'new_pair_cases_no_prior': v_true,
        'cases_with_prior_share': round(v_dark/len(nc), 3),
        'share_2023_reactivation': round(v_dark/tot23, 3),
        'share_2023_genuinely_new': round(v_true/tot23, 3),
        'prior_months_median': int(m_.median()),
        'prior_cases_median': int(v_.median()),
        'prior_cases_total': int(v_.sum()),
        'lost_pairs_total': len(LOST),
        'lost_pairs_back_2024_2025': len(back),
        'lost_pairs_back_share': round(len(back)/len(LOST), 3),
    }
    # The panel-level intermittency counts are NOT written here. This script
    # never computes them, and reading them out of the store to write them back
    # would make the regression check compare the store against itself. They
    # live in pair_panel_intermittency, written by scripts/pair_entry_describe.py.
    store['extensive_margin_definitions'] = {
        'facilities_carrying_extensive_cases': len(absent_fac),
        'facilities_in_2019_sih_nonelective': len(in_sih),
        'cases_at_those_facilities': cases_in_sih,
        'extensive_share_elective_basis': round(len(nc_abs)/len(nc), 3),
        'extensive_share_sih_basis': round((len(nc_abs)-cases_in_sih)/len(nc), 3),
    }
    io.open(NJ, 'w', encoding='utf-8').write(json.dumps(store, indent=1) + '\n')
    print('wrote pair_intermittency, extensive_margin_definitions')

pd.DataFrame(sorted(NEW), columns=['CNES', 'p']).assign(
    prior_active=lambda d: [tuple(r) in anyprior for r in d.values]
).to_csv('data/ref/entrant_churn_2023.csv', index=False)
print('\n-> data/ref/entrant_churn_2023.csv')

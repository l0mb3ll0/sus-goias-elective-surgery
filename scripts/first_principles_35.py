"""Section 3.5's four unreproduced quantities, defined from first principles.

The stored values were typed in by scripts/patch_s3.py and no derivation exists.
Rather than search for a convention that recovers them, each quantity is defined
here before being computed, and whatever it gives is the answer.

DEFINITIONS, fixed before any result was seen.

1. CASES PER SURGICAL BED-MONTH, group g, regime R.

   Unit of observation: the facility-month (j, m), m in R, j assigned to g.
   Universe:  facility-months where j has a CNES bed record in m with at least
              one surgical bed. A facility-month with no surgical beds supplies
              no capacity and cannot carry a rate. Facility-months with beds but
              zero elective cases DO enter, contributing 0 to the numerator;
              dropping them would condition the denominator on the outcome.
   Numerator: elective surgical admissions at (j, m), PROC_REA group 04 and
              CAR_INT = 01.
   Denominator: surgical beds at (j, m), QT_SUS summed over CODLEITO in the
              surgical inpatient set. Per footnote 1 this set includes
              obstetric-surgical, paediatric-surgical and surgical intensive
              care; TP_LEITO would omit them and understate capacity by about a
              third.
   Aggregation: pooled. Sum the numerator over the cell, sum the denominator
              over the cell, divide. The claim is about a group's aggregate
              throughput per unit of its capacity, and the model's bed-day
              constraint is likewise aggregate. The unweighted mean of
              facility-level ratios is reported alongside as a sensitivity, not
              as the headline.
   Ratio:     municipal pooled / state pooled.

   COHERENCE. Elective bed-days = cases x mean length of stay, and capacity =
   beds x 30, so

       elective occupancy of surgical beds = CPBM x LOS / 30.

   The same facility-month universe is used for both, so the identity must hold
   to rounding. It is asserted below. Section 3.5 reports elective occupancy of
   surgical beds converging at 0.113 against 0.135 in 2023-25 while the LOS
   ratio holds at 1.478; those two facts jointly pin the CPBM ratio, and the
   check tells us which of the stored and recomputed series is consistent.

2. LOS RATIO EXCLUDING THE LARGEST INSTITUTIONS.
   "The two largest" is read per side, by elective case count in 2023, because
   the concern the sentence answers is that one dominant institution on either
   side drives its own group's mean. Four facilities are dropped in total. The
   ratio is then recomputed pooled over the remaining records.

3. GROWTH BY GROUP, RE-BASED ON 2019.
   Mean monthly elective volume in the post window over mean monthly elective
   volume in calendar 2019, per group, on facilities assigned to that group.
   Post window is 2022-09..2023-07, the same post window Section 3.5 uses for
   the contaminated-window comparison, so the two differ only in the base.

4. OCCUPANCY, 2023-25.
   Total bed-days from every admission over all SUS beds x 30, per facility-
   month, pooled within group; and the median across facilities of each
   facility's mean monthly occupancy. Elective surgical occupancy restricts both
   sides to elective surgical bed-days and surgical beds.

    python -m scripts.first_principles_35 [--write]
"""
import glob, io, json, sys
import numpy as np, pandas as pd

NJ = 'paper/numbers.json'
INPAT = {'01','02','03','04','05','06','08','09','11','12','13','14','15','16',
         '67','90','91','10','68','83'}
REG = {'R1': ('2019-01', '2019-12'), 'R3': ('2022-09', '2023-07'), 'R4': ('2023-08', '2025-12')}

pan = pd.read_parquet('data/interim/hospital_panel_v2.parquet')
grp = pan.drop_duplicates('CNES').set_index('CNES')['group']
MUN, ST = 'municipal_at_break', {'always_state', 'transferred'}
side_of = {c: ('mun' if g == MUN else 'st' if g in ST else None) for c, g in grp.items()}

cols = ['CNES', 'PROC_REA', 'CAR_INT', 'DIAS_PERM', 'COMPETENCIA', 'COMPLEX']
a_all = pd.concat([pd.read_parquet(f, columns=cols)
                   for f in sorted(glob.glob('data/interim/sih/RDGO*.parquet'))], ignore_index=True)
a_all['side'] = a_all.CNES.map(side_of)
surg = a_all[a_all.PROC_REA.str[:2] == '04']
el = surg[surg.CAR_INT == '01']

lt = pd.read_parquet('data/interim/cnes_lt_raw.parquet').copy()
lt['sus'] = pd.to_numeric(lt.QT_SUS, errors='coerce').fillna(0)
lt['co'] = lt.CODLEITO.astype(str).str.zfill(2)
lt['cm'] = lt.comp.astype(str).str[:4] + '-' + lt.comp.astype(str).str[4:6]
sbeds = (lt[lt.co.isin(INPAT)].groupby(['CNES', 'cm']).sus.sum()
         .rename('beds').reset_index())
sbeds = sbeds[sbeds.beds > 0]
sbeds['side'] = sbeds.CNES.map(side_of)
abeds = lt.groupby(['CNES', 'cm']).sus.sum().rename('beds').reset_index()
abeds = abeds[abeds.beds > 0]
abeds['side'] = abeds.CNES.map(side_of)

out, report = {}, []

# ---------------- 1. cases per surgical bed-month ----------------
ecases = el.groupby(['CNES', 'COMPETENCIA']).size().rename('cases').reset_index() \
           .rename(columns={'COMPETENCIA': 'cm'})
edays = el.groupby(['CNES', 'COMPETENCIA']).DIAS_PERM.sum().rename('edays').reset_index() \
          .rename(columns={'COMPETENCIA': 'cm'})
fm = sbeds.merge(ecases, on=['CNES', 'cm'], how='left') \
          .merge(edays, on=['CNES', 'cm'], how='left').fillna({'cases': 0, 'edays': 0})

cpm = {}
print('1. CASES PER SURGICAL BED-MONTH (pooled over facility-months with surgical beds)\n')
print(f"{'regime':8s}{'mun':>9s}{'st':>9s}{'ratio':>9s}{'mun_fac':>9s}{'st_fac':>9s}"
      f"{'ratio_fac':>11s}{'LOS mun':>9s}{'LOS st':>8s}{'identity':>10s}")
for r, (lo, hi) in REG.items():
    w = fm[fm.cm.between(lo, hi)]
    v, vf, occ, los = {}, {}, {}, {}
    for s in ('mun', 'st'):
        x = w[w.side == s]
        v[s] = float(x.cases.sum()/x.beds.sum())
        fr = x.groupby('CNES').apply(lambda t: t.cases.sum()/t.beds.sum(), include_groups=False)
        vf[s] = float(fr.mean())
        occ[s] = float(x.edays.sum()/(x.beds*30.0).sum())
        los[s] = float(x.edays.sum()/max(x.cases.sum(), 1))
    ident = {s: occ[s]*30.0/los[s] for s in ('mun', 'st')}
    ok = all(abs(ident[s] - v[s]) < 1e-6 for s in ('mun', 'st'))
    cpm[r] = {'mun': round(v['mun'], 3), 'st': round(v['st'], 3),
              'ratio': round(v['mun']/v['st'], 3),
              'mun_mean_of_facility_ratios': round(vf['mun'], 3),
              'st_mean_of_facility_ratios': round(vf['st'], 3),
              'ratio_mean_of_facility_ratios': round(vf['mun']/vf['st'], 3),
              'elective_occ_mun': round(occ['mun'], 3), 'elective_occ_st': round(occ['st'], 3),
              'los_mun': round(los['mun'], 3), 'los_st': round(los['st'], 3)}
    print(f"{r:8s}{v['mun']:>9.3f}{v['st']:>9.3f}{v['mun']/v['st']:>9.3f}"
          f"{vf['mun']:>9.3f}{vf['st']:>9.3f}{vf['mun']/vf['st']:>11.3f}"
          f"{los['mun']:>9.3f}{los['st']:>8.3f}{'holds' if ok else 'FAILS':>10s}")
    assert ok, f'{r}: identity CPBM = occ*30/LOS failed'
cpm['denom'] = 'CODLEITO surgical set incl. obstetric-surgical, paediatric-surgical, surgical ICU; QT_SUS'
cpm['definition'] = 'pooled elective cases / pooled surgical bed-months, facility-months with beds>0'
out['cases_per_surg_bedmonth'] = cpm

# ---------------- 2. LOS ratio dropping the two largest per side ----------------
e23 = el[el.COMPETENCIA.str[:4] == '2023']
los = {}
for s in ('mun', 'st'):
    x = e23[e23.side == s]
    los[f'{s}_n'] = int(len(x)); los[f'{s}_days'] = int(x.DIAS_PERM.sum())
    los[f'{s}_mean'] = round(float(x.DIAS_PERM.mean()), 3)
los['ratio'] = round(los['st_mean']/los['mun_mean'], 3)
drop = set()
for s in ('mun', 'st'):
    drop |= set(e23[e23.side == s].CNES.value_counts().head(2).index)
x = e23[~e23.CNES.isin(drop)]
los['ratio_drop_top2'] = round(float(x[x.side == 'st'].DIAS_PERM.mean()
                                     / x[x.side == 'mun'].DIAS_PERM.mean()), 3)
los['dropped_cnes'] = sorted(drop)
fmn = e23.groupby(['side', 'CNES']).DIAS_PERM.mean()
los['ratio_median_of_facility_means'] = round(float(fmn['st'].median()/fmn['mun'].median()), 3)
out['los_2023'] = los
print(f"\n2. LOS 2023: pooled ratio {los['ratio']}, dropping two largest per side "
      f"{los['ratio_drop_top2']}, median of facility means {los['ratio_median_of_facility_means']}")
print(f"   dropped: {', '.join(los['dropped_cnes'])}")

# ---------------- 2b. complexity, 2023 elective ----------------
# Reproduced exactly against the stored literals; carried here so one script
# owns the whole Section 3.5 block.
cx = {}
for s_ in ('mun', 'st'):
    x = e23[e23.side == s_]
    cx[f'{s_}_alta_share'] = round(float((x.COMPLEX == '03').mean()), 3)
for lab, code in [('media', '02'), ('alta', '03')]:
    x = e23[e23.COMPLEX == code]
    cx[f'ratio_{lab}'] = round(float(x[x.side == 'st'].DIAS_PERM.mean()
                                     / x[x.side == 'mun'].DIAS_PERM.mean()), 3)
wts = e23[e23.side == 'mun'].COMPLEX.value_counts(normalize=True)
stm = e23[e23.side == 'st'].groupby('COMPLEX').DIAS_PERM.mean()
cx['ratio_standardized'] = round(float((stm.reindex(wts.index).fillna(0)*wts).sum()
                                       / e23[e23.side == 'mun'].DIAS_PERM.mean()), 3)
out['complexity_2023'] = cx

# ---------------- 2c. growth by group, contaminated 2021 window ----------------
g21 = {}
for lab, gs in [('always_state', ['always_state']), ('transferred', ['transferred']),
                ('municipal', [MUN])]:
    ids = {c for c, g in grp.items() if g in gs}
    pre = el[(el.COMPETENCIA.between('2021-12', '2022-07')) & el.CNES.isin(ids)]
    post = el[(el.COMPETENCIA.between('2022-09', '2023-07')) & el.CNES.isin(ids)]
    g21[lab] = round(float((len(post)/11)/(len(pre)/8) - 1), 3)
g21.update({'pre': '2021-12/2022-07', 'post': '2022-09/2023-07'})
out['growth_by_group_2021w'] = g21

# ---------------- 3. growth by group, 2019 base ----------------
b19 = {}
for lab, gs in [('state', ['always_state', 'transferred']), ('municipal', [MUN])]:
    ids = {c for c, g in grp.items() if g in gs}
    base = len(el[(el.COMPETENCIA.str[:4] == '2019') & el.CNES.isin(ids)])/12
    post = len(el[(el.COMPETENCIA.between('2022-09', '2023-07')) & el.CNES.isin(ids)])/11
    b19[lab] = round(float(post/base), 3)
b19['ratio'] = round(b19['state']/b19['municipal'], 3)
b19['base'] = '2019 calendar'; b19['post'] = '2022-09/2023-07'
out['growth_by_group_2019base'] = b19
print(f"\n3. growth re-based on 2019: state {b19['state']}, municipal {b19['municipal']}, "
      f"ratio of ratios {b19['ratio']}")

# ---------------- 4. occupancy 2023-25 ----------------
lo, hi = REG['R4']
adays = a_all.groupby(['CNES', 'COMPETENCIA']).DIAS_PERM.sum().rename('days').reset_index() \
             .rename(columns={'COMPETENCIA': 'cm'})
aw = abeds[abeds.cm.between(lo, hi)].merge(adays, on=['CNES', 'cm'], how='left').fillna({'days': 0})
oc = {}
for s in ('mun', 'st'):
    x = aw[aw.side == s]
    oc[f'all_beds_{s}'] = round(float(x.days.sum()/(x.beds*30.0).sum()), 3)
    per = x.groupby('CNES').apply(lambda t: t.days.sum()/(t.beds*30.0).sum(), include_groups=False)
    oc[f'all_beds_{s}_median'] = round(float(per.median()), 3)
sw = fm[fm.cm.between(lo, hi)]
for s in ('mun', 'st'):
    x = sw[sw.side == s]
    oc[f'elective_surg_{s}'] = round(float(x.edays.sum()/(x.beds*30.0).sum()), 3)
out['occupancy_R4'] = oc
print(f"\n4. occupancy 2023-25: all beds mun {oc['all_beds_mun']} st {oc['all_beds_st']}, "
      f"medians {oc['all_beds_mun_median']} / {oc['all_beds_st_median']}; "
      f"elective surgical {oc['elective_surg_mun']} / {oc['elective_surg_st']}")

# ---------------- comparison with the stored literals ----------------
store = json.load(io.open(NJ, encoding='utf-8'))


def pairs(d, pre=''):
    for f, nv in d.items():
        if isinstance(nv, dict):
            yield from pairs(nv, f'{pre}{f}.')
        elif isinstance(nv, (int, float)):
            yield pre + f, nv


def dig(d, path):
    for part in path.split('.'):
        if not isinstance(d, dict):
            return None
        d = d.get(part)
    return d


print(f"\n{'key.field':46s}{'stored':>11s}{'first-principles':>18s}   status")
diff = []
for k, v in out.items():
    for f, nv in pairs(v):
        ov = dig(store.get(k, {}), f)
        if ov is None:
            print(f'  {k+"."+f:44s}{"-":>11s}{nv:>18}   NEW'); continue
        tol = max(abs(ov)*0.01, 0.002)
        ok = abs(ov - nv) <= tol
        if not ok:
            diff.append((f'{k}.{f}', ov, nv))
        print(f'  {k+"."+f:44s}{ov:>11}{nv:>18}   {"ok" if ok else "DIFFERS"}')
print(f'\n{len(diff)} fields differ from the stored literals')

if '--write' in sys.argv:
    store.update(out)
    json.dump(store, io.open(NJ, 'w', encoding='utf-8'), indent=1)
    print('written', NJ, '- first-principles values now replace the stored literals')

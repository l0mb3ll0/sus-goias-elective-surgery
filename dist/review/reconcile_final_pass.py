"""Final-pass reconciliation: re-derive the counts the paper quotes from the source RD files.

Read-only. Does not write numbers.json. Usage (from the repo root):
    python dist/review/reconcile_final_pass.py [DATA_INTERIM_DIR]
DATA_INTERIM_DIR defaults to data/interim (needs sih/RDGO*.parquet and hospital_panel_v2.parquet).

Definitions follow scripts/entrant_churn_check.py: pair = (CNES, 4-digit PROC_REA);
elective = PROC_REA group 04 and CAR_INT == '01'; ALL residents (the combination that
reproduces 284/192); presence = >=1 case in the calendar year.
Group rule (scripts/panel_v2.py, hospital_panel_v2.parquet 'group'): TP_GESTAO class of the
facility as of 2022-08: municipal_at_break / always_state / transferred, plus 'excluded' and
'unknown'. A facility absent from that panel is 'not_in_panel'. No rule is invented here.
"""
import glob, sys
import pandas as pd

D = sys.argv[1] if len(sys.argv) > 1 else 'data/interim'
fr = [pd.read_parquet(f, columns=['CNES','PROC_REA','CAR_INT','COMPETENCIA','MUNIC_RES'])
      for f in sorted(glob.glob(f'{D}/sih/RDGO*.parquet'))]
a = pd.concat(fr, ignore_index=True)
a['CNES'] = a.CNES.astype(str).str.strip()
a['p'] = a.PROC_REA.astype(str).str[:4]
a['el'] = (a.PROC_REA.astype(str).str[:2] == '04') & (a.CAR_INT.astype(str).str.strip() == '01')
a['yr'] = a.COMPETENCIA.astype(str).str.strip().str[:4]
a['comp'] = a.COMPETENCIA.astype(str).str.strip()
go = set(pd.read_csv('data/ref/ibge_municipios_go.csv', dtype=str).cod6)
e = a[a.el]   # all residents: the basis that reproduces 574/666/284/192 and 21,845 (entrant_churn_check.py)
keys = lambda y: set(map(tuple, e[e.yr == y][['CNES','p']].drop_duplicates().values))
S19, S23 = keys('2019'), keys('2023')
NEW, LOST = S23 - S19, S19 - S23
e23 = e[e.yr == '2023']; tot23 = len(e23)
nc = e23.merge(pd.DataFrame(sorted(NEW), columns=['CNES','p']), on=['CNES','p'])
print(f'pairs 2019 {len(S19)}, 2023 {len(S23)}; new {len(NEW)}, lost {len(LOST)}; '
      f'new-pair cases {len(nc):,}; share of 2023 volume {len(nc)/tot23:.4f}')

pan = pd.read_parquet(f'{D}/hospital_panel_v2.parquet', columns=['CNES','group']).drop_duplicates('CNES')
pan['CNES'] = pan.CNES.astype(str).str.strip()
gmap = dict(zip(pan.CNES, pan.group))
nc['g'] = nc.CNES.map(gmap).fillna('not_in_panel')
pr = pd.DataFrame(sorted(NEW), columns=['CNES','p']); pr['g'] = pr.CNES.map(gmap).fillna('not_in_panel')
cases = nc.groupby('g').size()
print('\n== 1. New pairs by group (rule: hospital_panel_v2 group) ==')
tab = pd.DataFrame({'pairs': pr.groupby('g').size(), 'cases': cases}).fillna(0).astype(int)
print(tab.to_string()); print('TOTAL pairs', tab.pairs.sum(), 'cases', tab.cases.sum())
main3 = ['municipal_at_break','always_state','transferred']
print('three named groups: pairs', tab.loc[[g for g in main3 if g in tab.index],'pairs'].sum(),
      'cases', tab.loc[[g for g in main3 if g in tab.index],'cases'].sum())
res = tab.drop([g for g in main3 if g in tab.index])
print('RESIDUAL (not in the three groups): pairs', res.pairs.sum(), 'cases', res.cases.sum())
print('\nresidual pair list (CNES, subgroup, cases 2023, group):')
cc = nc.groupby(['CNES','p']).size().rename('cases')
for _, r in pr[~pr.g.isin(main3)].iterrows():
    print(' ', r.CNES, r.p, int(cc.get((r.CNES, r.p), 0)), r.g)

print('\n== 2. Section 3.2 subgroup counts and intervening activity (2020-2022) ==')
pre = e[e.yr.isin(['2019','2020','2021','2022'])]
interv = set(map(tuple, e[e.yr.isin(['2020','2021','2022'])][['CNES','p']].drop_duplicates().values))
anyprior = set(map(tuple, pre[['CNES','p']].drop_duplicates().values)) & NEW
print('NOTE: paper text says "active in some month of 2020 to 2022"; the stored numbers use 2019-2022 on NEW pairs (absent in calendar 2019, so identical by construction).')
print(f'  with intervening activity (2020-22): {len(NEW & interv)} of {len(NEW)}; any 2019-22: {len(anyprior)}')
nc['k'] = list(zip(nc.CNES, nc.p)); dark = nc.k.isin(NEW & interv)
print(f'  cases with intervening activity: {int(dark.sum()):,} of {len(nc):,} ({dark.mean():.4f}); '
      f'points of 2023 volume {dark.sum()/tot23*100:.1f} vs no activity {(~dark).sum()/tot23*100:.1f}')
pm = pre[pre.set_index(['CNES','p']).index.isin(list(NEW & interv))]
mo = pm.groupby(['CNES','p']).comp.nunique(); vo = pm.groupby(['CNES','p']).size()
mm = mo.reindex(pd.MultiIndex.from_tuples(sorted(NEW & interv))).fillna(0)
print(f'  median active months before 2023 (2019-22 window): {mm.median():.0f}; median cases {vo.median():.0f}; total prior cases {int(vo.sum()):,}')
mo2 = e[e.yr.isin(['2020','2021','2022'])].groupby(['CNES','p']).comp.nunique().reindex(pd.MultiIndex.from_tuples(sorted(NEW & interv)))
print(f'  median active months, 2020-22 only: {mo2.median():.0f}')
for sg in ['0407','0409','0408']:
    ps = {k for k in NEW if k[1]==sg}; sub = nc[nc.p==sg]
    print(f'  {sg}: pairs {len(ps)}, cases {len(sub):,}; pair share with intervening {len(ps&interv)/len(ps)*100:.1f}%, case share {sub.k.isin(ps&interv).mean()*100:.1f}%')
LB = {k for k in LOST}
back = set(map(tuple, e[e.yr.isin(['2024','2025'])][['CNES','p']].drop_duplicates().values))
print(f'\n== 3. lost pairs active again 2024/25: {len(LB & back)} of {len(LB)}')

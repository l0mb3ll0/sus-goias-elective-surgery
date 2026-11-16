"""Re-derive four numbers that earlier had no generating script, from the RD and CNES files, using the definitions stated in the text.
Writes dist/review/untraced_numbers.json; scripts/store_untraced_numbers.py merges it into paper/numbers.json.
Run from the repository root with data/interim present:  python dist/review/untraced_numbers.py

 (1) Section 4 opening. Elective surgical admissions (PROC_REA group 04, CAR_INT 01), all 84 months, all residents (n = 430,802).
     'Outside the municipality of residence' = MUNIC_RES[:6] != MUNIC_MOV[:6]. Provider groups as in scripts/panel_v2.py:
     TP_GESTAO of the facility in the last CNES month before 2022-09; state-administered = always-state + transferred,
     municipal-administered = municipal at the break.
 (2) Appendix A.3. Mean elective cases per facility-month, over state-administered facility-months with positive elective volume,
     in the final regime (2025-04 to 2025-12; the regime boundary of Section 3.1).
 (3) Section 3.1. Elective admissions per month and elective/urgent ratio (CAR_INT 01 / 02, group 04) over 2022-08 to 2023-07.
 (4) Section 3.3. Pair-entry month under three definitions (D1 first positive month; D2 first of three consecutive positive months;
     D3 first month whose trailing 3-month mean is >= 0.5), pairs = CNES x 4-digit subgroup, in-state residents, observable (not
     left-censored) entries as in scripts/pair_entry_describe.py. Displacement = |entry month under one definition - under another|, in months.
"""
import glob, json, itertools
import numpy as np, pandas as pd

OUT = 'dist/review/untraced_numbers.json'
sih = sorted(glob.glob('data/interim/sih/RDGO*.parquet'))
cols = ['CNES', 'PROC_REA', 'CAR_INT', 'COMPETENCIA', 'MUNIC_RES', 'MUNIC_MOV']
a = pd.concat([pd.read_parquet(f, columns=cols) for f in sih], ignore_index=True)
a = a[a.PROC_REA.astype(str).str[:2] == '04']
a['CAR_INT'] = a.CAR_INT.astype(str).str.strip(); a['comp'] = a.COMPETENCIA.astype(str).str.strip()
el = a[a.CAR_INT == '01'].copy(); ur = a[a.CAR_INT == '02']

# provider groups, as scripts/panel_v2.py
BREAK = '202209'
pan = pd.read_parquet('data/interim/hospital_panel.parquet')
st = pd.read_parquet('data/interim/cnes_st_raw.parquet')
st['CNES'] = st.CNES.astype(str).str.zfill(7); st['comp'] = st.comp.astype(str)
s = st[st.CNES.isin(set(pan.CNES))].sort_values('comp')
first, at_break = {}, {}
for c, g in s.groupby('CNES'):
    v, m = g.TPGESTAO.tolist(), g.comp.tolist(); first[c] = v[0]
    prior = [v[i] for i in range(len(v)) if m[i] < BREAK]; at_break[c] = prior[-1] if prior else None
def grp(c):
    if at_break.get(c) is None: return 'unknown'
    if at_break[c] != 'E': return 'municipal'
    return 'transferred' if first[c] == 'M' else 'always_state'
G = {c: grp(c) for c in pan.CNES.unique()}; G['5419662'] = 'excluded'
el['g'] = el.CNES.map(G)
el['out'] = el.MUNIC_RES.astype(str).str[:6] != el.MUNIC_MOV.astype(str).str[:6]
state = el.g.isin(['always_state', 'transferred'])
r = {}
r['cross_municipal'] = {'n_elective': int(len(el)), 'share_all': float(el.out.mean()),
                        'share_state_administered': float(el[state].out.mean()),
                        'share_municipal_administered': float(el[el.g == 'municipal'].out.mean()),
                        'n_state': int(state.sum()), 'n_municipal': int((el.g == 'municipal').sum()), 'window': '2019-01..2025-12'}
fm = el[state & el.comp.between('2025-04', '2025-12')].groupby(['CNES', 'comp']).size()
r['state_plateau'] = {'mean_cases_per_facility_month': float(fm.mean()), 'n_facility_months': int(len(fm)),
                      'n_facilities': int(fm.index.get_level_values(0).nunique()), 'window': '2025-04..2025-12'}
e = el.groupby('comp').size(); u = ur.groupby('comp').size()
lo, hi = '2022-08', '2023-07'
r['ratio_window'] = {'elective_per_month': float(e[lo:hi].mean()), 'ratio': float(e[lo:hi].sum() / u[lo:hi].sum()),
                     'highest_2019_monthly_ratio': float((e / u)['2019-01':'2019-12'].max()),
                     'lowest_monthly_ratio_from_2022_08': float((e / u)['2022-08':].min()), 'window': f'{lo}..{hi}'}

# (4) pair entry
MONTHS = [f'{y}-{m:02d}' for y in range(2019, 2026) for m in range(1, 13)]
ref = pd.read_csv('data/ref/ibge_municipios_go.csv', dtype=str); GO = set(ref.cod6)
b = el[el.MUNIC_RES.astype(str).str[:6].isin(GO)].copy(); b['p'] = b.PROC_REA.astype(str).str[:4]
V = b.groupby(['CNES', 'p', 'comp']).size().unstack('comp', fill_value=0).reindex(columns=MONTHS, fill_value=0)
A = V.values > 0
def entries(rule, floor=None):
    if rule == 'D1': act = A
    elif rule == 'D2':
        act = np.zeros_like(A)
        for k in range(A.shape[1] - 2): act[:, k] = A[:, k] & A[:, k+1] & A[:, k+2]
    else:
        act = pd.DataFrame(V.values).T.rolling(3, min_periods=3).mean().T.values >= floor
    first = {}
    for i in range(A.shape[0]):
        on = np.flatnonzero(act[i])
        if len(on) and not A[i, 0]: first[i] = int(on[0])   # observable (not left-censored) first entry
    return first
E_ = {'D1': entries('D1'), 'D2': entries('D2'), 'D3_05': entries('D3', 0.5)}
pairs = {}
for x, y in itertools.combinations(E_, 2):
    com = set(E_[x]) & set(E_[y]); d = np.array([E_[x][k] - E_[y][k] for k in com])
    pairs[f'{x}_vs_{y}'] = {'n_pairs': int(len(com)), 'mean_abs_months': float(np.abs(d).mean()), 'mean_signed_months': float(d.mean()),
                            'median_signed_months': float(np.median(d)), 'share_identical': float((d == 0).mean())}
r['entry_displacement'] = {'pairs': pairs, 'max_mean_abs_months': max(v['mean_abs_months'] for v in pairs.values())}
json.dump(r, open(OUT, 'w'), indent=1); print(json.dumps(r, indent=1))

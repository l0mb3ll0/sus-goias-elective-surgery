"""Recompute the elective submission-lag row of the falsification table.

The table row (Table 1, "Mean submission lag, elective") had no generating
script on disk; its values live only in numbers.json. Section 3.6 asserts the
elective lag "does rise across the break", which the table's -2.6 per cent
contradicts. This recomputes the lag on the windows the table uses so the
disagreement can be settled from data rather than from prose.

Windows are inferred from the stored denominators: pre-window means carry
sevenths and post-window means carry elevenths, matching Section 3.4's
"August 2022 to June 2023 divided by January to July 2022".

lag = processing month (COMPETENCIA) minus admission month (DT_INTER).

    python -m scripts.lag_check
"""
import glob, io, json
import numpy as np, pandas as pd

PRE = ('2022-01', '2022-07')     # 7 months
POST = ('2022-08', '2023-06')    # 11 months
NJ = 'paper/numbers.json'

frames = []
for f in sorted(glob.glob('data/interim/sih/RDGO*.parquet')):
    frames.append(pd.read_parquet(f, columns=['COMPETENCIA', 'DT_INTER', 'CAR_INT', 'PROC_REA']))
a = pd.concat(frames, ignore_index=True)
a = a[a.PROC_REA.str[:2] == '04']

comp = pd.PeriodIndex(a.COMPETENCIA, freq='M')
adm = pd.PeriodIndex(pd.to_datetime(a.DT_INTER, format='%Y%m%d', errors='coerce'), freq='M')
a['lag'] = (comp.asi8 - adm.asi8).astype(float)
a = a[a.lag.notna()]
el = a[a.CAR_INT == '01']
ur = a[a.CAR_INT != '01']


def win(df, lo, hi):
    return df[(df.COMPETENCIA >= lo) & (df.COMPETENCIA <= hi)]


rows = []
for name, df in [('elective', el), ('urgent', ur)]:
    p = win(df, *PRE).lag
    q = win(df, *POST).lag
    rows.append({'series': name, 'pre_mean': p.mean(), 'post_mean': q.mean(),
                 'chg_pct': (q.mean()/p.mean() - 1)*100, 'n_pre': len(p), 'n_post': len(q)})
res = pd.DataFrame(rows)
print(f'windows: pre {PRE[0]}..{PRE[1]} (7 months), post {POST[0]}..{POST[1]} (11 months)')
print(res.to_string(index=False, float_format=lambda v: f'{v:.3f}'))

stored = [r for r in json.load(io.open(NJ, encoding='utf-8'))['table2']
          if 'lag' in r['quantity'].lower()][0]
mine = res[res.series == 'elective'].iloc[0]
print(f"\nnumbers.json: pre {stored['pre']}, post {stored['post']}, chg {stored['chg']}%")
print(f"recomputed:   pre {mine.pre_mean:.3f}, post {mine.post_mean:.3f}, chg {mine.chg_pct:.3f}%")
ok = (abs(stored['pre'] - mine.pre_mean) < 5e-3 and abs(stored['post'] - mine.post_mean) < 5e-3)
print('table row reproduces:', ok)

# Section 2.3's separate claim: calendar 2021 against calendar 2022.
for y in ('2021', '2022'):
    m = el[el.COMPETENCIA.str[:4] == y].lag.mean()
    u = ur[ur.COMPETENCIA.str[:4] == y].lag.mean()
    print(f'  calendar {y}: elective {m:.3f}, urgent {u:.3f}')
print(f'  whole panel elective mean lag {el.lag.mean():.3f}, median {el.lag.median():.0f}')

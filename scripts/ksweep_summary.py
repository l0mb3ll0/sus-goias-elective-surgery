"""Summarise the k-sweep and test the guardrail.

The guardrail: if the chosen sets differ across the kappa-hat ladder, the data
does not identify where to open and that is the finding. Reports Jaccard overlap
of the chosen sets between 0.5x, 1x and 2x at each k, and how concentrated the
choices are by municipality and procedure.

    python -m scripts.ksweep_summary [--write]
"""
import json, io, sys, glob
import numpy as np, pandas as pd

MULTS = ['0.5', '1', '2']
NJ = 'paper/numbers.json'
S = {m: json.load(io.open(f'paper/ksweep_2025_m{m}.json', encoding='utf-8')) for m in MULTS}
base = S['1']['base_mean']

rows = []
for m in MULTS:
    for r in S[m]['runs']:
        if 'mean_cost' not in r: continue
        rows.append({'mult': float(m), 'k': r['k'], 'mean': r['mean_cost'],
                     'gain': r['improvement_pct'], 'gap': r['mip_gap'], 'sec': r['seconds'],
                     'n': r['n_opened']})
df = pd.DataFrame(rows)

print(f'base (k=0) mean cost {base:.4f}\n')
print('access gain, per cent of aggregate travel, by budget and kappa-hat level')
piv = df.pivot(index='k', columns='mult', values='gain')
print(piv.to_string(float_format=lambda v: f'{v:.2f}'))
print('\nmax MIP gap by level:', {m: f"{df[df.mult==float(m)].gap.max():.1e}" for m in MULTS})
print('total solve time by level (s):', {m: f"{df[df.mult==float(m)].sec.sum():.0f}" for m in MULTS})

sets = {}
for m in MULTS:
    for r in S[m]['runs']:
        if 'chosen' not in r: continue
        sets[(m, r['k'])] = {(c['j'], c['p']) for c in r['chosen']}

print('\nJaccard overlap of chosen sets across the kappa-hat ladder')
print(f"{'k':>4s}{'0.5 vs 1':>10s}{'1 vs 2':>10s}{'0.5 vs 2':>10s}{'all three':>11s}")
ov = []
for k in sorted({k for (_, k) in sets}):
    a, b, c = sets.get(('0.5', k)), sets.get(('1', k)), sets.get(('2', k))
    if not (a and b and c): continue
    j = lambda x, y: len(x & y)/len(x | y)
    triple = len(a & b & c)/len(a | b | c)
    ov.append({'k': k, 'j_05_1': j(a, b), 'j_1_2': j(b, c), 'j_05_2': j(a, c), 'j_all': triple})
    print(f'{k:>4d}{j(a,b):>10.2f}{j(b,c):>10.2f}{j(a,c):>10.2f}{triple:>11.2f}')
ovd = pd.DataFrame(ov)

k20 = sets.get(('1', 20), set())
print(f'\nat k=20, 1x: {len(k20)} pairs opened')
ch = [c for r in S['1']['runs'] if r.get('k') == 20 for c in r['chosen']]
if ch:
    cd = pd.DataFrame(ch)
    print('  municipalities receiving them:')
    print('   ', ', '.join(f'{m} ({n})' for m, n in cd.muni.value_counts().head(10).items()))
    print('  procedure subgroups:')
    print('   ', ', '.join(f'{p} ({n})' for p, n in cd.p.value_counts().items()))

core = set.intersection(*[sets[(m, 20)] for m in MULTS]) if all(('%s' % m, 20) in sets for m in MULTS) else set()
print(f'\npairs chosen at k=20 under all three kappa-hat levels: {len(core)} of 20')

out = {'base_mean': base,
       'frontier': {m: [{'k': int(r['k']), 'mean': r['mean_cost'], 'gain_pct': r['improvement_pct'],
                         'mip_gap': r['mip_gap'], 'seconds': r['seconds']}
                        for r in S[m]['runs'] if 'mean_cost' in r] for m in MULTS},
       'overlap': ovd.to_dict('records'),
       'core_at_k20': sorted(f'{j}:{p}' for (j, p) in core),
       'max_mip_gap': {m: float(df[df.mult == float(m)].gap.max()) for m in MULTS},
       'total_seconds': {m: float(df[df.mult == float(m)].sec.sum()) for m in MULTS}}
if '--write' in sys.argv:
    d = json.load(io.open(NJ, encoding='utf-8'))
    d['ksweep'] = out
    json.dump(d, io.open(NJ, 'w', encoding='utf-8'), indent=1)
    print('\nwritten', NJ)

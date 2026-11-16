"""Is the 400-candidate screen binding at these budgets?

ksweep.py restricts the integer program to the 400 candidates with the largest
values in the LP relaxation, so its reported optimum is the optimum of a
restricted problem and therefore a lower bound on the true frontier. The bound is
only interesting if the screen actually binds. Counts the distinct candidates
ever selected, across every budget and every kappa-hat level.

    python -m scripts.ksweep_screen_check [--write]
"""
import json, io, sys

MULTS = ['0.5', '1', '2']
NJ = 'paper/numbers.json'
NSCREEN = 400

sel = {}
per = {}
for m in MULTS:
    S = json.load(io.open(f'paper/ksweep_2025_m{m}.json', encoding='utf-8'))
    s = set()
    for r in S['runs']:
        for c in r.get('chosen', []):
            s.add((c['j'], c['p']))
    per[m] = s
    sel |= {k: True for k in s}

kmax = max(r['k'] for r in json.load(io.open('paper/ksweep_2025_m1.json', encoding='utf-8'))['runs'])
union = set(sel)
out = {'n_screened': NSCREEN, 'n_candidates_total': 1471, 'max_k': int(kmax),
       'n_distinct_selected_all_levels': int(len(union)),
       'n_distinct_selected_by_level': {m: int(len(per[m])) for m in MULTS},
       'screen_headroom': int(NSCREEN - len(union)),
       'screen_binds': bool(len(union) >= NSCREEN)}

print(f'screen size {NSCREEN} of 1,471 candidates; largest budget {kmax}')
for m in MULTS:
    print(f'  kappahat {m}x: {len(per[m]):3d} distinct pairs ever selected')
print(f'  union across all levels and budgets: {len(union)} distinct pairs')
print(f'  headroom: {NSCREEN - len(union)} screened candidates never chosen')
print(f'  screen binds: {out["screen_binds"]}')

if '--write' in sys.argv:
    d = json.load(io.open(NJ, encoding='utf-8'))
    d.setdefault('ksweep', {})['screen_check'] = out
    json.dump(d, io.open(NJ, 'w', encoding='utf-8'), indent=1)
    print('written', NJ)

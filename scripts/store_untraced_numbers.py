"""Merge dist/review/untraced_numbers.json (made by dist/review/untraced_numbers.py from the RD/CNES files) into paper/numbers.json as four NEW keys.
Refuses to overwrite a key that already exists with a different value.

    python -m scripts.store_untraced_numbers [--write]
"""
import io, json, sys
NJ = 'paper/numbers.json'
d = json.load(io.open(NJ, encoding='utf-8'))
r = json.load(open('dist/review/untraced_numbers.json'))
d['cross_municipal_share'] = r['cross_municipal']          # Section 4 opening: 42.7 / 70.3 / 30.4
d['state_plateau_2025'] = r['state_plateau']                # Appendix A.3: 151
d['ratio_window_2022_08'] = r['ratio_window']               # Section 3.1: 5,986 and 0.648
d['entry_displacement'] = r['entry_displacement']           # Section 3.3: twelve months
old = json.load(io.open(NJ, encoding='utf-8'))
for k in ('cross_municipal_share', 'state_plateau_2025', 'ratio_window_2022_08', 'entry_displacement'):
    assert k not in old or old[k] == d[k], f'{k} exists with a different value'
changed = [k for k in old if old[k] != d[k]]
assert not changed, changed
if '--write' in sys.argv:
    io.open(NJ, 'w', encoding='utf-8').write(json.dumps(d, indent=1) + '\n')
    print('wrote 4 keys')
else:
    print('dry run; 4 keys would be added')

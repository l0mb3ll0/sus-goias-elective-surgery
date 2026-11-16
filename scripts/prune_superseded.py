"""Delete numbers.json keys that hold pre-correction duplicates.

Four keys predate the equation (4) fix and hold values that a later key or a
generated paper/*.json now supersedes. Two keys holding the same quantity, one
stale, is a hazard: a future reader or script has no way to tell which is live.

Refuses to delete a key whose stored values appear anywhere in the paper.

  model_2019    superseded by paper/model_2019_roll3.json  (cap1x 0.5581 -> 0.5947)
  model_2023    superseded by paper/model_2023_roll3.json  (cap1x 0.5631 -> 0.5873)
  model_decomp  superseded by paper/model_decomp_roll3.json (A 0.5576 -> 0.5947)
  model_metric  superseded by paper/model_metric_*.json     (2019 gap_km 0.465 -> 0.366)

model_caps is NOT deleted. It is not a model result; Section 4.2 cites its
batch-reporting diagnostic, and scripts/panel_counts.py now regenerates it.

    python -m scripts.prune_superseded [--write]
"""
import glob, io, json, re, sys

NJ = 'paper/numbers.json'
DROP = ['model_2019', 'model_2023', 'model_decomp', 'model_metric']

store = json.load(io.open(NJ, encoding='utf-8'))
tex = ''.join(io.open(f, encoding='utf-8').read() for f in glob.glob('paper/*.tex'))
tex = re.sub(r'\s+', ' ', tex).replace('{,}', '')


def flat(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from flat(v)
    elif isinstance(o, list):
        for v in o:
            yield from flat(v)
    elif isinstance(o, float):
        yield o


# Values live in the generated per-run JSONs. A stale key is only load-bearing
# if it holds a number the paper uses that NO generated file also holds; where
# both agree (the observed baseline and the unconstrained optimum are unchanged
# by the equation (4) fix) deleting the stale copy loses nothing.
live = set()
for f in glob.glob('paper/model_*.json') + glob.glob('paper/ksweep_*.json') + \
         glob.glob('paper/equity_*.json'):
    live |= set(flat(json.load(io.open(f, encoding='utf-8'))))


def near(v, pool):
    return any(abs(v - w) <= max(abs(v), 1.0)*1e-3 for w in pool)


blocked = {}
for k in DROP:
    if k not in store:
        continue
    hits = []
    for v in set(flat(store[k])):
        if v == 0 or abs(v) < 0.01 or near(v, live):
            continue
        for sc in (1.0, 100.0):
            t = f'{v*sc:.3f}'.rstrip('0').rstrip('.')
            if len(t.replace('.', '')) >= 3 and re.search(rf'(?<![\d.]){re.escape(t)}(?![\d])', tex):
                hits.append(t)
    if hits:
        blocked[k] = sorted(set(hits))

print(f'{len(DROP)} keys marked superseded')
for k in DROP:
    print(f'  {k:16s} present: {k in store}   read by the paper: '
          f'{blocked.get(k, "no")}')
if blocked:
    print('\nrefusing to delete: the paper still reads these values')
    sys.exit(1)

if '--write' in sys.argv:
    for k in DROP:
        store.pop(k, None)
    json.dump(store, io.open(NJ, 'w', encoding='utf-8'), indent=1)
    print(f'\ndeleted {len(DROP)} keys; {len(store)} remain')
else:
    print(f'\nsafe to delete; {len(store) - len([k for k in DROP if k in store])} would remain')

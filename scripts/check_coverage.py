"""Fail if any numbers.json key has no computing writer.

An audit found fourteen keys written into the store as literals by one-off patch
scripts. A regression check against such a key compares the store to itself and
passes unconditionally, which is worse than no check because it is invisible.
This turns that audit into an invariant.

Classification:
  GENERATED  a non-patch script assigns the key into the store
  HARDCODED  only a patch_*.py assigns it, i.e. the value was typed in
  ORPHAN     no script assigns it

Exit status is non-zero if any key is HARDCODED or ORPHAN and is not listed in
ALLOWED_UNCOVERED. Run in CI or as a pre-commit step.

Two regression tests guard the bugs that made the first version of this checker
unreliable, both found the hard way:

  R1  a pandas column assignment such as `a['growth'] = ...` was counted as a
      store write, so an orphan key reported as generated. The writer pattern
      must require the assignment target to be the store object.
  R2  nested dicts were skipped by the value comparator, so an entire block of
      nine fields silently reported as passing. The comparator must descend.

    python -m scripts.check_coverage [--test]
"""
import glob, io, json, re, sys

NJ = 'paper/numbers.json'

# Keys deliberately left uncovered. Each must name a reason. These appear in no
# table, no abstract sentence and no Section 1 sentence.
ALLOWED_UNCOVERED = {
    'breaks_full_pen1':  'PELT changepoint output, Section 3.1; needs a ruptures re-run',
    'breaks_full_pen2':  'PELT changepoint output, Section 3.1; needs a ruptures re-run',
    'breaks_clean_pen1': 'PELT changepoint output, Section 3.1; needs a ruptures re-run',
    'breaks_clean_pen05':'PELT changepoint output, Section 3.1; needs a ruptures re-run',
    'regime_means':      'regime segment means, Section 3.1; depends on the break dates',
    'entrant_share_of_step': 'Section 3.3 entrant share at the break',
    'entrants_2023':     'Section 3.3 new-pair counts',
    'los_decomposition': 'Section 3.5 same-day and overnight margins',
    'groups_v2':         'mirrors scripts/panel_v2.py console output',
    'table2':            'falsification table; scripts/lag_check.py regenerates the lag row only',
}

# Accumulator names that are merged into the store. `a`, `t`, `fl` and friends
# are deliberately absent: R1's bug was a pandas column assignment counting as a
# store write. A script must also reference numbers.json to qualify at all.
STORE_NAMES = r'(?:store|stored|out|res|d|dd|n|nums|numbers)'
ASSIGN = (r"""{store}\[\s*['"]{k}['"]\s*\]\s*="""
          r"""|{store}\.setdefault\(\s*['"]{k}['"]"""
          r"""|['"]{k}['"]\s*:""")


def classify(store, scripts):
    hard_re = re.compile(r'scripts/patch_\w+\.py$')
    gen, hard, orphan = {}, {}, []
    for k in store:
        pat = ASSIGN.format(store=STORE_NAMES, k=re.escape(k))
        w = [p for p, s in scripts.items()
             if 'numbers.json' in s and re.search(pat, s)]
        g = [p for p in w if not hard_re.search(p)]
        h = [p for p in w if hard_re.search(p)]
        if g:
            gen[k] = sorted(x.split('/')[-1] for x in g)
        elif h:
            hard[k] = sorted(x.split('/')[-1] for x in h)
        else:
            orphan.append(k)
    return gen, hard, orphan


def walk(o, pre=''):
    """Yield every leaf number with its dotted path. Must descend into dicts."""
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk(v, f'{pre}{k}.')
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, f'{pre}{i}.')
    elif isinstance(o, (int, float)) and not isinstance(o, bool):
        yield pre.rstrip('.'), float(o)


def selftest():
    ok = True
    # R1: a pandas column assignment must NOT count as a store write.
    fake = {'scripts/x.py': "NJ='paper/numbers.json'\na['growth'] = (a.k25-a.k).clip(0)\n"}
    gen, hard, orphan = classify({'growth': 1}, fake)
    r1 = 'growth' in orphan
    print(f'  R1 pandas column assignment not counted as a writer: {"PASS" if r1 else "FAIL"}')
    ok &= r1
    # R1b: a genuine store write must count.
    fake2 = {'scripts/y.py': "NJ='paper/numbers.json'\nstore['growth'] = compute()\n"}
    gen2, _, _ = classify({'growth': 1}, fake2)
    r1b = 'growth' in gen2
    print(f'  R1b genuine store write counted as a writer:          {"PASS" if r1b else "FAIL"}')
    ok &= r1b
    # R2: the comparator must descend into nested dicts.
    nested = {'cases_per_surg_bedmonth': {'R1': {'mun': 1.378, 'st': 1.041}}}
    paths = dict(walk(nested))
    r2 = paths.get('cases_per_surg_bedmonth.R1.mun') == 1.378 and len(paths) == 2
    print(f'  R2 nested dicts descended, not skipped:               {"PASS" if r2 else "FAIL"}')
    ok &= r2
    # R2b: a flat comparator would have found nothing here.
    r2b = len(dict(walk({'a': {'b': 1.0}}))) == 1
    print(f'  R2b single nested leaf reachable:                     {"PASS" if r2b else "FAIL"}')
    ok &= r2b
    return ok


if '--test' in sys.argv:
    print('regression tests for the two checker bugs:')
    sys.exit(0 if selftest() else 1)

store = json.load(io.open(NJ, encoding='utf-8'))
scripts = {p: io.open(p, encoding='utf-8').read() for p in sorted(glob.glob('scripts/*.py'))
           if not p.endswith('check_coverage.py')}
gen, hard, orphan = classify(store, scripts)

print('regression tests for the two checker bugs:')
if not selftest():
    print('\nFAIL: the checker itself is broken')
    sys.exit(2)

print(f'\nnumbers.json: {len(store)} keys, {len(dict(walk(store)))} leaf numbers\n')
print(f'GENERATED ({len(gen)}):')
for k, v in sorted(gen.items()):
    print(f'  {k:32s} <- {", ".join(v)}')
bad = []
if hard:
    print(f'\nHARDCODED ({len(hard)}):')
    for k, v in sorted(hard.items()):
        note = ALLOWED_UNCOVERED.get(k)
        print(f'  {k:32s} <- {", ".join(v)}' + (f'   [allowed: {note}]' if note else '   *** FAIL'))
        if not note:
            bad.append(k)
if orphan:
    print(f'\nORPHAN ({len(orphan)}):')
    for k in sorted(orphan):
        note = ALLOWED_UNCOVERED.get(k)
        print(f'  {k:32s}' + (f'   [allowed: {note}]' if note else '   *** FAIL'))
        if not note:
            bad.append(k)

cov = len(gen)/len(store)*100
print(f'\n{len(gen)} generated, {len(hard)} hardcoded, {len(orphan)} orphan '
      f'({cov:.0f} per cent regenerating)')
stale = [k for k in ALLOWED_UNCOVERED if k in gen]
if stale:
    print(f'\nallowlist is stale, these are now generated: {", ".join(sorted(stale))}')
if bad:
    print(f'\nFAIL: {len(bad)} key(s) with no computing writer and no allowlist entry: '
          f'{", ".join(sorted(bad))}')
    sys.exit(1)
print('\nPASS: every key either regenerates or is explicitly allowed')

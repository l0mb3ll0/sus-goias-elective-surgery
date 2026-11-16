"""Step 1: describe facility-procedure pair entry and exit, 2019-01..2025-12.

Exploratory. Describes events only; designs and estimates nothing.

DEFINITIONAL CHOICES, all stated because each could reasonably go the other way.

  Pair          (CNES, 4-digit SIGTAP subgroup), matching the paper's level.
  Elective      PROC_REA group 04 and CAR_INT == '01', matching the panel.
  Residency     IN-STATE residents only (MUNIC_RES in Goias), matching the
                capability-cap construction in scripts/model_run.py. Reported
                both ways below, since this is arbitrary at the pair level.
  Active month  positive elective volume under the entry rule in force.

  ENTRY RULES, run three ways:
    D1  first month with positive volume
    D2  first month of three consecutive positive months
    D3  first month whose trailing 3-month rolling MEAN is at or above a floor;
        the floor is arbitrary so both 0.5 and 1.0 are reported.

  LEFT CENSORING. A pair already active in 2019-01 has no observable entry: its
  true entry may predate the panel. Those are counted separately and NEVER
  treated as entering in month 1, which would manufacture a spike of 'entries'
  at the panel edge -- the same left-censoring artifact that killed the SR probe.

  EXIT          three consecutive zero months after being active.
  RE-ENTRY      a later entry (same rule) after an exit.

    python -m scripts.pair_entry_describe
"""
import glob, io, sys
import numpy as np
import pandas as pd

# COMPETENCIA is stored as 'YYYY-MM' in the interim parquet, verified rather
# than assumed: a 'YYYYMM' calendar reindexes to an all-zero grid silently.
MONTHS = [f'{y}-{m:02d}' for y in range(2019, 2026) for m in range(1, 13)]
GAP = 3


def load(instate=True):
    ref = pd.read_csv('data/ref/ibge_municipios_go.csv', dtype=str)
    GO = set(ref.cod6)
    fr = []
    for f in sorted(glob.glob('data/interim/sih/RDGO*.parquet')):
        d = pd.read_parquet(f, columns=['CNES', 'PROC_REA', 'CAR_INT',
                                        'COMPETENCIA', 'MUNIC_RES'])
        d = d[(d.PROC_REA.astype(str).str[:2] == '04') &
              (d.CAR_INT.astype(str).str.strip() == '01')]
        fr.append(d)
    a = pd.concat(fr, ignore_index=True)
    a['p'] = a.PROC_REA.astype(str).str[:4]
    a['i'] = a.MUNIC_RES.astype(str).str[:6]
    a['comp'] = a.COMPETENCIA.astype(str).str.strip()
    bad = set(a.comp.unique()) - set(MONTHS)
    assert not bad, f'COMPETENCIA values outside the 84-month calendar: {sorted(bad)[:5]}'
    if instate:
        a = a[a.i.isin(GO)]
    return a


def grid(a):
    """pair x month volume matrix over the full 84-month calendar."""
    t = a.groupby(['CNES', 'p', 'comp']).size().unstack('comp', fill_value=0)
    return t.reindex(columns=MONTHS, fill_value=0)


def entries(V, rule, floor=None):
    """Return dict pair -> list of entry month indices, plus censored flag."""
    A = (V.values > 0)
    if rule == 'D1':
        act = A
    elif rule == 'D2':
        act = np.zeros_like(A)
        for k in range(A.shape[1] - 2):
            act[:, k] = A[:, k] & A[:, k+1] & A[:, k+2]
    else:                                   # D3: trailing 3-month rolling mean
        R = pd.DataFrame(V.values).T.rolling(3, min_periods=3).mean().T.values
        act = R >= floor
    # Left censoring is judged on RAW activity in 2019-01, uniformly across
    # rules. Judging it on the rule's own activity flag lets D3 report zero
    # censored pairs, because its trailing 3-month window cannot be satisfied at
    # month 0 -- an artifact of the window, not evidence the pair is new.
    out, censored = {}, []
    for r in range(A.shape[0]):
        on = np.flatnonzero(act[r])
        if not len(on):
            continue
        if A[r, 0]:
            censored.append(r)
        # entry = an active month with GAP inactive months before it
        ev = []
        for k in on:
            if k == 0:
                ev.append(0); continue
            lo = max(0, k - GAP)
            if not act[r, lo:k].any():
                ev.append(k)
        out[r] = ev
    return out, censored


def describe(a, tag):
    V = grid(a)
    pairs = V.index
    print(f'\n{"="*74}\n{tag}: {len(pairs):,} facility-procedure pairs ever active, '
          f'{int((V.values > 0).sum()):,} active pair-months')
    res = {}
    for name, rule, floor in [('D1 first positive', 'D1', None),
                              ('D2 3 consecutive', 'D2', None),
                              ('D3 roll3 mean>=0.5', 'D3', 0.5),
                              ('D3 roll3 mean>=1.0', 'D3', 1.0)]:
        ev, cens = entries(V, rule, floor)
        first = {r: v[0] for r, v in ev.items() if v}
        obs = {r: k for r, k in first.items() if r not in set(cens)}
        nre = sum(1 for r, v in ev.items() if len(v) > 1)
        res[name] = (first, set(cens), obs, ev)
        print(f'\n  {name}')
        print(f'    pairs ever active under rule : {len(ev):,}')
        print(f'    left-censored (active 2019-01): {len(cens):,} '
              f'({100*len(cens)/max(1,len(ev)):.1f}%)')
        print(f'    with an OBSERVABLE entry      : {len(obs):,}')
        print(f'    pairs with >1 entry (re-entry): {nre:,}')
        if obs:
            yr = pd.Series([MONTHS[k][:4] for k in obs.values()]).value_counts().sort_index()
            print(f'    observable entries by year    : {yr.to_dict()}')
    return V, res


a_in = load(instate=True)
V, res = describe(a_in, 'IN-STATE residents (panel construction)')

print(f'\n{"="*74}\n=== how much do entry dates move between definitions? ===')
base = res['D2 3 consecutive'][2]
for name in ['D1 first positive', 'D3 roll3 mean>=0.5', 'D3 roll3 mean>=1.0']:
    other = res[name][2]
    common = set(base) & set(other)
    d = pd.Series({r: other[r] - base[r] for r in common})
    print(f'\n  {name} vs D2, on {len(common):,} pairs observable under both')
    print(f'    identical entry month : {int((d == 0).sum()):,} ({100*(d==0).mean():.1f}%)')
    print(f'    within +/-1 month     : {int((d.abs() <= 1).sum()):,} '
          f'({100*(d.abs()<=1).mean():.1f}%)')
    print(f'    within +/-3 months    : {int((d.abs() <= 3).sum()):,} '
          f'({100*(d.abs()<=3).mean():.1f}%)')
    if len(d):
        print(f'    median shift {d.median():+.0f}, mean {d.mean():+.2f}, '
              f'IQR {d.quantile(.25):+.0f} to {d.quantile(.75):+.0f}, '
              f'max |shift| {int(d.abs().max())}')
    print(f'    pairs observable under D2 but NOT this rule: '
          f'{len(set(base) - set(other)):,}; the reverse: {len(set(other) - set(base)):,}')

# ---- entrant type: new facility vs incumbent adding a subgroup --------------
print(f'\n{"="*74}\n=== entrant type, D2 (facility new to elective vs incumbent) ===')
first_fac = a_in.groupby('CNES').comp.min()
idx = list(V.index)
for name in ['D1 first positive', 'D2 3 consecutive', 'D3 roll3 mean>=0.5']:
    obs = res[name][2]
    new_fac = inc = 0
    for r, k in obs.items():
        cnes = idx[r][0]
        if MONTHS.index(first_fac[cnes]) >= k:
            new_fac += 1
        else:
            inc += 1
    tot = new_fac + inc
    print(f'  {name:22s} facility new to elective {new_fac:>5,} '
          f'({100*new_fac/max(1,tot):.1f}%)   incumbent adds subgroup {inc:>5,} '
          f'({100*inc/max(1,tot):.1f}%)')

# ---- exits ------------------------------------------------------------------
print(f'\n{"="*74}\n=== exits, D2 activity with {GAP} consecutive zero months ===')
A = (V.values > 0)
nexit = nboth = 0
for r in range(A.shape[0]):
    on = np.flatnonzero(A[r])
    if not len(on):
        continue
    last = on[-1]
    ex = 0
    for k in on:
        if k + GAP <= A.shape[1] - 1 and not A[r, k+1:k+1+GAP].any() and k != last:
            ex += 1
    if A.shape[1] - 1 - last >= GAP:
        ex += 1
    if ex:
        nexit += 1
    if ex and len(res['D2 3 consecutive'][3].get(r, [])) > 1:
        nboth += 1
print(f'  pairs with >=1 exit  : {nexit:,} of {len(V):,}')
print(f'  pairs with exit AND re-entry: {nboth:,}')

# ---- residency sensitivity ---------------------------------------------------
a_all = load(instate=False)
V2, res2 = describe(a_all, 'ALL residents (residency filter removed)')
o1, o2 = res['D2 3 consecutive'][2], res2['D2 3 consecutive'][2]
i1, i2 = list(V.index), list(V2.index)
m1 = {i1[r]: k for r, k in o1.items()}
m2 = {i2[r]: k for r, k in o2.items()}
common = set(m1) & set(m2)
d = pd.Series({k: m2[k] - m1[k] for k in common})
print(f'\n  residency sensitivity, D2: {len(common):,} pairs observable both ways; '
      f'identical entry month {int((d==0).sum()):,} ({100*(d==0).mean():.1f}%)')

if '--write' in sys.argv:
    import collections, json
    NJ = 'paper/numbers.json'
    store = json.load(io.open(NJ, encoding='utf-8'),
                      object_pairs_hook=collections.OrderedDict)
    agree = []
    for nm in ['D1 first positive', 'D3 roll3 mean>=0.5', 'D3 roll3 mean>=1.0']:
        oth = res[nm][2]
        com = set(base) & set(oth)
        agree.append(np.mean([oth[r] == base[r] for r in com]))
    store['pair_panel_intermittency'] = {
        'panel_pairs': int(len(V)),
        'panel_pairs_with_exit': int(nexit),
        'panel_pairs_exit_and_reenter': int(nboth),
        'entry_date_agreement_min': round(float(min(agree)), 3),
        'entry_date_agreement_max': round(float(max(agree)), 3),
    }
    io.open(NJ, 'w', encoding='utf-8').write(json.dumps(store, indent=1) + '\n')
    print('wrote pair_panel_intermittency')

out = pd.DataFrame([{'CNES': i1[r][0], 'p': i1[r][1],
                     'entry_D1': MONTHS[res['D1 first positive'][2][r]]
                     if r in res['D1 first positive'][2] else None,
                     'entry_D2': MONTHS[k],
                     'entry_D3_05': MONTHS[res['D3 roll3 mean>=0.5'][2][r]]
                     if r in res['D3 roll3 mean>=0.5'][2] else None}
                    for r, k in res['D2 3 consecutive'][2].items()])
out.to_csv('data/ref/pair_entry_events.csv', index=False)
print(f'\n-> data/ref/pair_entry_events.csv  ({len(out):,} observable D2 entries)')

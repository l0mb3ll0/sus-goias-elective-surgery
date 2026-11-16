"""Regression fixtures for the Goias paper. Run before and after every workstream.

These are the numbers the paper's claims rest on. If any moves, that is a bug
until proven otherwise, and the run should stop rather than continue onto new
analysis built on a shifted base.

Each fixture names the store it is read from, so this asserts the analysis
outputs against the paper's claims -- not a copy of the brief against another
copy of the brief. Reads only committed JSON: no data, no network, seconds.

    python -m tests.test_fixtures          # or: python tests/test_fixtures.py
"""
import io, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda n: os.path.join(ROOT, 'paper', n)
load = lambda n: json.load(io.open(P(n), encoding='utf-8'))
YEARS = ['2019', '2023', '2025']

results = []


def check(name, got, want, tol=0.0, source=''):
    if isinstance(want, float) or isinstance(got, float):
        ok = abs(float(got) - float(want)) <= tol
    else:
        ok = got == want
    results.append((ok, name, got, want, source))
    return ok


def run():
    nums = load('numbers.json')
    cap = nums['capability']
    roll = {y: load(f'model_{y}_roll3.json') for y in YEARS}
    peak = {y: load(f'model_{y}.json') for y in YEARS}
    r1x = {y: {r['label']: r for r in roll[y]['runs']}['cap 1x roll3'] for y in YEARS}

    # --- record counts -------------------------------------------------
    check('total AIH records', nums['n_total_aih'], 2_719_254, source='numbers.json')
    check('elective surgical admissions', nums['n_elective'], 430_802, source='numbers.json')
    check('distinct CNES facilities', nums['n_hospitals'], 201, source='numbers.json')

    # --- program dimensions --------------------------------------------
    for y, want in zip(YEARS, [131, 131, 145]):
        check(f'|J| {y}', cap[y]['n_fac'], want, source=f'capability.{y}.n_fac')
    for y, want in zip(YEARS, [563, 637, 704]):
        check(f'scope pairs {y}', cap[y]['n_scope_pairs'], want,
              source=f'capability.{y}.n_scope_pairs')
    for y in YEARS:
        check(f'|I| {y}', roll[y]['n_muni'], 246, source=f'model_{y}_roll3.n_muni')

    # --- allocative gap and travel at the 1x cap ------------------------
    for y, want in zip(YEARS, [28.8, 30.6, 29.1]):
        check(f'gap {y} (%)', round(r1x[y]['gap']*100, 1), want, 0.05,
              f'model_{y}_roll3 cap 1x gap')
    for y, want in zip(YEARS, [0.595, 0.587, 0.642]):
        check(f'optimal travel {y}', round(r1x[y]['travel'], 3), want, 5e-4,
              f'model_{y}_roll3 cap 1x travel')
    for y, want in zip(YEARS, [0.835, 0.846, 0.906]):
        check(f'observed travel {y}', round(roll[y]['travel_obs'], 3), want, 5e-4,
              f'model_{y}_roll3.travel_obs')

    # --- utilisation and capability ratio -------------------------------
    for y, want in zip(YEARS, [0.132, 0.178, 0.215]):
        check(f'bed utilisation {y}', round(cap[y]['bed_util'], 3), want, 5e-4,
              f'capability.{y}.bed_util')
    for y, want in zip(YEARS, [1.368, 1.321, 1.160]):
        check(f'capability/demand {y}', round(cap[y]['aggregate_slack'], 3), want, 5e-4,
              f'capability.{y}.aggregate_slack')

    # --- disjointness, the principal result ------------------------------
    for y, want in zip(YEARS, [1, 3, 6]):
        check(f'bed-bound facilities {y}', cap[y]['bedbound_n'], want,
              source=f'capability.{y}.bedbound_n')
    for y, want in zip(YEARS, [79, 77, 105]):
        check(f'capability-bound facilities {y}', cap[y]['capbound_n'], want,
              source=f'capability.{y}.capbound_n')
    for y, want in zip(YEARS, [0.41, 0.58, 0.63]):
        check(f'bed-bound mean cap use {y}', round(cap[y]['bedbound_capuse_mean'], 2), want,
              5e-3, f'capability.{y}.bedbound_capuse_mean')
    for y, want in zip(YEARS, [23_821, 26_269, 31_309]):
        check(f'spare bed-days at cap-bound {y}', round(cap[y]['capbound_spare_bd']), want, 1,
              f'capability.{y}.capbound_spare_bd')
    check('bed-days consumed by all 131, 2023', round(cap['2023']['beds_used_bd']), 10_902, 1,
          'capability.2023.beds_used_bd')

    # --- floored pairs, excluded from every pair-level count -------------
    for y, wf, wn in zip(YEARS, [116, 111, 100], [532, 601, 663]):
        check(f'floored pairs {y}', cap[y]['n_pairs_floored'], wf,
              source=f'capability.{y}.n_pairs_floored')
        check(f'pairs carrying flow {y}', cap[y]['n_pairs'], wn,
              source=f'capability.{y}.n_pairs')

    # --- single-month robustness row (Table 2) ---------------------------
    for y, want in zip(YEARS, [35.7, 39.9, 38.2]):
        r = {x['label']: x for x in peak[y]['runs']}['cap 1x peak']
        check(f'single-month cap gap {y} (%)', round(r['gap']*100, 1), want, 0.05,
              f'model_{y}.json cap 1x peak')

    # --- k-sweep central result ------------------------------------------
    ks = {r['k']: r for r in load('ksweep_2025_m1.json')['runs'] if 'improvement_pct' in r}
    check('k=20 gain at central kappa-hat (%)', round(ks[20]['improvement_pct'], 2), 9.48, 0.005,
          'ksweep_2025_m1.json k=20')
    check('k-sweep monotone in k', all(
        ks[a]['mean_cost'] >= ks[b]['mean_cost'] - 1e-9
        for a, b in zip(sorted(ks), sorted(ks)[1:])), True, source='ksweep_2025_m1.json')

    # --- dual degeneracy, guards any new ranking -------------------------
    deg = nums['degeneracy']
    check('2023 non-floored pairs at cap', cap['2023']['n_pairs_bound'], 249,
          source='capability.2023.n_pairs_bound')
    check('2023 pairs with positive dual', deg['positive_dual'], 143,
          source='degeneracy.positive_dual')


if __name__ == '__main__':
    run()
    bad = [r for r in results if not r[0]]
    w = max(len(r[1]) for r in results)
    for ok, name, got, want, src in results:
        if not ok or '-v' in sys.argv:
            print(f'  {"ok  " if ok else "FAIL"} {name:{w}s} got {got!r:>12} want {want!r:>12}'
                  + (f'   [{src}]' if not ok else ''))
    print(f'\n{len(results) - len(bad)}/{len(results)} fixtures hold')
    if bad:
        print(f'\nFAIL: {len(bad)} fixture(s) moved. Stop and investigate before '
              f'building on this base.')
        sys.exit(1)
    print('PASS: every fixture matches the paper')

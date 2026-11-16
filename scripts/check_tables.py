"""Fail if a number printed in a table does not match the store it came from.

scripts/check_coverage.py proves every stored number regenerates from a script.
This proves every printed number matches the store. Together they close the loop
from raw data to page.

The gap this fills is not hypothetical. A row of Table 1 disagreed with the
prose describing it for four rounds of correction, because nothing compared the
printed cell against paper/numbers.json.

Runs with no data, no network and no DATASUS: it reads only the .tex sources and
the committed JSON result files.

TOLERANCE RULE. Cells are compared at the precision they are printed to, not at
full float. A cell printed as "0.595" is checked against the stored value rounded
half-up to three decimals, "28.8" to one. Half-up rather than Python's round(),
which is banker's rounding and would disagree with a person typesetting a table
at a midpoint. The exact binary value is rounded, not its shortest repr, since
repr can manufacture a midpoint the double does not have. This is the only rule
that treats the
table as what it is, a rounded view of the store, without either failing on
correct rounding or passing on a wrong third decimal.

A cell that cannot be mapped to a store key is a FAIL, never a skip. A silent
skip is the same failure mode as a checker that compares a value to itself, which
is the bug that made this test necessary.

    python -m scripts.check_tables [--test]
"""
import io, json, os, re, shutil, sys, tempfile
from decimal import Decimal, ROUND_HALF_UP

PAPER = 'paper'


def load(name):
    return json.load(io.open(os.path.join(PAPER, name), encoding='utf-8'))


def tex(name):
    return io.open(os.path.join(PAPER, name), encoding='utf-8').read()


def rows_of(body):
    """Data rows of a tabular: strip rules, keep lines with an ampersand."""
    body = re.sub(r'\\(?:top|mid|bottom)rule|\\cmidrule\([^)]*\)\{[^}]*\}', '', body)
    out = []
    for raw in body.split(r'\\'):
        line = raw.strip()
        if not line or '&' not in line:
            continue
        if line.startswith('\\multicolumn') and 'emph' in line:   # section label row
            continue
        out.append([c.strip() for c in line.split('&')])
    return out


NUM = re.compile(r'^[+-]?\d+(?:[,{]?,?\}?\d{3})*(?:\.\d+)?\\?%?$')


def parse_cell(c):
    """Return (value, decimals) for a numeric cell, or None if not numeric."""
    t = c.replace('\\%', '').replace('{,}', '').replace(',', '').strip()
    t = re.sub(r'\\[a-zA-Z]+', '', t).strip()
    if t in ('', '---', '--', '-'):
        return None
    if not re.fullmatch(r'[+-]?\d+(?:\.\d+)?', t):
        return None
    dec = len(t.split('.')[1]) if '.' in t else 0
    return float(t), dec


def expect(table, row, col, printed, stored, checks, fails):
    """Compare a printed cell against a stored value at printed precision."""
    v, dec = printed
    if stored is None:
        fails.append((table, row, col, v, 'NO STORE KEY'))
        return
    q = Decimal(1).scaleb(-dec)
    # Decimal(float) is the exact binary value. Decimal(repr(float)) is the
    # shortest round-tripping string, which can manufacture a midpoint the
    # stored double does not have: repr(398.19499999...) is '398.195', and
    # rounding that half-up gives 398.20 for a value that is below the midpoint.
    rnd = lambda x: Decimal(float(x)).quantize(q, rounding=ROUND_HALF_UP)
    if rnd(stored) != rnd(v):
        fails.append((table, row, col, v, float(rnd(stored))))
    checks.append((table, row, col))


def check(paper_dir=PAPER):
    global PAPER
    PAPER = paper_dir
    checks, fails, unmapped = [], [], []

    s4 = tex('section_4_model.tex') + tex('appendix.tex')     # the k-sweep table moved to the appendix
    tabs = {}
    for blk in re.findall(r'\\begin\{table\}.*?\\end\{table\}', s4, re.S):
        lab = re.search(r'\\label\{(tab:[^}]+)\}', blk)
        body = re.search(r'\\begin\{tabular\}\{[^}]*\}(.*?)\\end\{tabular\}', blk, re.S)
        if lab and body:
            tabs[lab.group(1)] = body.group(1)

    # ---------- Table 1: falsification ----------
    t1 = rows_of(tex('tab2_falsification.tex'))
    store1 = load('numbers.json')['table2']
    data1 = [r for r in t1 if parse_cell(r[1]) or parse_cell(r[2])]
    if len(data1) != len(store1):
        fails.append(('Table 1', '-', 'row count', len(data1), len(store1)))
    for r, rec in zip(data1, store1):
        for col, key in ((1, 'pre'), (2, 'post'), (3, 'chg')):
            p = parse_cell(r[col]) if col < len(r) else None
            if p is None:
                continue
            expect('Table 1', rec['quantity'][:34], key, p, rec.get(key), checks, fails)

    # ---------- Table 2: capability cap ladder ----------
    YEARS = ['2019', '2023', '2025']
    roll = {y: load(f'model_{y}_roll3.json') for y in YEARS}
    peak = {y: load(f'model_{y}.json') for y in YEARS}
    run = lambda m, lab: {r['label']: r for r in m['runs']}[lab]
    LADDER = [('Observed allocation', None),
              ('Unconstrained optimum', 'unconstrained'),
              ('Cap at 2', 'cap 2x roll3'),
              ('Cap at 1.5', 'cap 1.5x roll3'),
              ('Cap at 1', 'cap 1x roll3')]
    body2 = rows_of(tabs['tab:modelrobust'])
    data2 = [r for r in body2 if parse_cell(r[1])]
    if len(data2) != 6:
        fails.append(('Table 2', '-', 'row count', len(data2), 6))
    for i, r in enumerate(data2):
        last = i == len(data2) - 1                     # single-month robustness row
        name, lab = ('Cap at 1x, single-month', 'cap 1x peak') if last else LADDER[i]
        for k, y in enumerate(YEARS):
            for off, field in ((0, 'travel'), (1, 'gap')):
                col = 1 + 2*k + off
                p = parse_cell(r[col]) if col < len(r) else None
                if p is None:
                    continue
                src = peak[y] if last else roll[y]
                if lab is None:
                    val = src['travel_obs']
                else:
                    val = run(src, lab)[field]
                    if field == 'gap':
                        val *= 100
                expect('Table 2', name, f'{y} {field}', p, val, checks, fails)

    # ---------- Table 3: decomposition ----------
    dec = load('model_decomp_roll3.json')['runs']
    body3 = rows_of(tabs['tab:decomp'])
    data3 = [r for r in body3 if len(r) >= 5 and parse_cell(r[2])]
    if len(data3) != len(dec):
        fails.append(('Table 3', '-', 'row count', len(data3), len(dec)))
    for r, rec in zip(data3, dec):
        for col, field, scale in ((2, 'scope_pairs', 1), (3, 'travel_opt', 1), (4, 'travel_adj', 1),
                                  (5, 'unmet_share', 100)):
            p = parse_cell(r[col])
            if p is None:
                continue
            expect('Table 3', rec['label'][0], field, p, rec[field]*scale, checks, fails)

    # ---------- Table 4: k-sweep ----------
    ks = {m: {x['k']: x for x in load(f'ksweep_2025_m{m}.json')['runs'] if 'improvement_pct' in x}
          for m in ('0.5', '1', '2')}
    for r in rows_of(tabs['tab:ksweep']):
        kp = parse_cell(r[0])
        if kp is None:
            continue
        k = int(kp[0])
        for col, m in ((1, '0.5'), (2, '1'), (3, '2')):
            p = parse_cell(r[col])
            if p is None:
                unmapped.append(('Table 4', f'k={k}', m))
                continue
            rec = ks[m].get(k)
            expect('Table 4', f'k={k}', f'{m}x', p,
                   rec['improvement_pct'] if rec else None, checks, fails)

    return checks, fails, unmapped


def selftest():
    """Mutate one cell in a temp copy and confirm the check fails on it."""
    with tempfile.TemporaryDirectory() as td:
        dst = os.path.join(td, 'paper')
        shutil.copytree(PAPER, dst)
        p = os.path.join(dst, 'section_4_model.tex')
        s = io.open(p, encoding='utf-8').read()
        old = 'Cap at 1$\\times$ historical peak & 0.595 & 28.8\\%'
        assert s.count(old) == 1, 'selftest anchor not found'
        io.open(p, 'w', encoding='utf-8').write(
            s.replace(old, 'Cap at 1$\\times$ historical peak & 0.777 & 28.8\\%'))
        _, fails, _ = check(dst)
        hit = any(f[3] == 0.777 for f in fails)
        print(f'  mutated Table 2 cell 0.595 -> 0.777 is caught: {"PASS" if hit else "FAIL"}')
        return hit


if __name__ == '__main__':
    if '--test' in sys.argv:
        print('regression test:')
        ok = selftest()
        PAPER = 'paper'
        sys.exit(0 if ok else 1)

    checks, fails, unmapped = check()
    per = {}
    for t, _, _ in checks:
        per[t] = per.get(t, 0) + 1
    print('cells checked against the committed stores:')
    for t in sorted(per):
        print(f'  {t:10s} {per[t]:3d} cells')
    print(f'  {"total":10s} {len(checks):3d} cells')

    print('\nregression test:')
    if not selftest():
        print('\nFAIL: the checker does not detect a mutated cell')
        sys.exit(2)

    if unmapped:
        print(f'\nUNMAPPED ({len(unmapped)}) — a cell with no store key is a failure:')
        for t, r, c in unmapped:
            print(f'  {t} row {r} col {c}')
    if fails:
        print(f'\nFAIL: {len(fails)} mismatched or unmappable cell(s)')
        for t, r, c, printed, stored in fails:
            print(f'  {t:9s} row {str(r):34s} {str(c):14s} printed {printed}  stored {stored}')
        sys.exit(1)
    if unmapped:
        sys.exit(1)
    print(f'\nPASS: all {len(checks)} printed cells match the store at printed precision')

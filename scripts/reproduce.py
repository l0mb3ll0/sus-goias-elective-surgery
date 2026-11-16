"""One command to rebuild the paper's stored numbers, figures and PDF from data/interim, and to check them against the committed values.

    python -m scripts.reproduce                 # default: everything except the bootstrap and the k-sweep (minutes)
    python -m scripts.reproduce --full          # also the paired bootstrap (340 draws + 80 jackknife) and the k-sweep (hours)
    python -m scripts.reproduce --list          # print the steps without running

Prerequisite: data/interim populated (see data/README.md). Raw download is a separate, network step.
Order follows each script's inputs. Each step logs to <log dir>/NN_name.log; a failed step stops the run unless --keep-going.
After the steps it compares every numeric leaf of paper/numbers.json and paper/model_*.json with the version at --ref (default HEAD) and prints the
differences above 1e-9. Run it in a clean checkout/worktree so the working tree is the thing being tested. It never touches the network and never prints identifiers.
"""
import argparse, glob, json, os, subprocess, sys, time

PY = sys.executable
M = lambda mod, *a: [PY, '-m', f'scripts.{mod}', *a]

BASE = [
    ('check_inputs',     M('check_build_inputs')),
    ('model_2019',       [PY, 'scripts/model_run.py', '2019']),
    ('model_2023',       [PY, 'scripts/model_run.py', '2023']),
    ('model_2025',       [PY, 'scripts/model_run.py', '2025']),
    ('model_2019_nopair', [PY, 'scripts/model_run.py', '2019', '3', '--nopair']),
    ('model_2023_nopair', [PY, 'scripts/model_run.py', '2023', '3', '--nopair']),
    ('model_2025_nopair', [PY, 'scripts/model_run.py', '2025', '3', '--nopair']),
    ('model_decomp',     M('model_decomp')),
    ('capability',       M('capability')),
    # paper/figures.py REPLACES the numbers.json keys it computes (growth, clean_share_volume, ...) with rounded values, so it must run
    # before the scripts that own those keys (subset_sensitivity merges into growth; panel_counts owns clean_share_volume).
    ('figures',          [PY, 'paper/figures.py']),
    ('panel_counts',     M('panel_counts', '--write')),
    ('first_principles', M('first_principles_35', '--write')),
    ('flows_panel',      M('flows_panel', '--write')),
    ('audit_round3',     M('audit_round3', '--write')),
    ('subset_sens',      M('subset_sensitivity', '--write')),
    ('pair_sens',        M('pair_sensitivity', '--write')),
    ('placement',        M('placement_test', '--write')),
    ('entrant_churn',    M('entrant_churn_check')),
    ('check_0409',       M('check_0409_prior')),
    ('equity',           M('equity_frontier', '2025', '--write')),
]
FULL = [
    ('bootstrap_d0', M('bootstrap_paired', 'draws', '--chunk', '0', '--draws', '40')),
    ('bootstrap_d1', M('bootstrap_paired', 'draws', '--chunk', '1', '--draws', '150')),
    ('bootstrap_d2', M('bootstrap_paired', 'draws', '--chunk', '2', '--draws', '150')),
    ('bootstrap_j0',  M('bootstrap_paired', 'jackknife', '--chunk', '0', '--size', '40')),
    ('bootstrap_j1',  M('bootstrap_paired', 'jackknife', '--chunk', '1', '--size', '40')),
    ('bootstrap_combine', M('bootstrap_paired', 'combine', '--write')),
    ('ksweep_summary', M('ksweep_summary', '--write')),   # needs the ksweep_2025_m*.json runs; scripts.ksweep is hours, see its docstring
]
TAIL = [
    ('check_coverage', M('check_coverage')),
    ('check_tables',   M('check_tables')),
    ('test_recompute', M('test_recompute')),
    ('pdflatex_1',     ['pdflatex', '-interaction=nonstopmode', '-output-directory=paper', 'paper/main.tex']),
    ('pdflatex_2',     ['pdflatex', '-interaction=nonstopmode', '-output-directory=paper', 'paper/main.tex']),
]


def leaves(o, pre=''):
    if isinstance(o, dict):
        for k, v in o.items(): yield from leaves(v, f'{pre}/{k}')
    elif isinstance(o, list):
        for i, v in enumerate(o): yield from leaves(v, f'{pre}[{i}]')
    elif isinstance(o, (int, float)) and not isinstance(o, bool):
        yield pre, float(o)


def compare(ref):
    bad, n = [], 0
    files = ['paper/numbers.json'] + sorted(glob.glob('paper/model_*.json'))
    for f in files:
        try:
            old = json.loads(subprocess.run(['git', 'show', f'{ref}:{f}'], capture_output=True, text=True, check=True).stdout)
        except subprocess.CalledProcessError:
            continue
        new = json.load(open(f))
        a, b = dict(leaves(old)), dict(leaves(new))
        for k in sorted(set(a) | set(b)):
            n += 1
            if k not in a or k not in b: bad.append((f, k, a.get(k), b.get(k)))
            elif abs(a[k] - b[k]) > 1e-9 * max(1.0, abs(a[k])): bad.append((f, k, a[k], b[k]))
    return n, bad


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--full', action='store_true'); ap.add_argument('--list', action='store_true')
    ap.add_argument('--keep-going', action='store_true'); ap.add_argument('--ref', default='HEAD')
    ap.add_argument('--logdir', default='repro_logs'); ap.add_argument('--only', nargs='*')
    A = ap.parse_args()
    os.environ['PYTHONPATH'] = os.getcwd()   # paper/figures.py imports sus.py from the repo root
    steps = BASE + (FULL if A.full else []) + TAIL
    if A.only: steps = [s for s in steps if s[0] in A.only]
    if A.list:
        for i, (n, c) in enumerate(steps, 1): print(f'{i:02d} {n:18s} {" ".join(c)}')
        sys.exit(0)
    os.makedirs(A.logdir, exist_ok=True)
    summary, failed = [], False
    for i, (name, cmd) in enumerate(steps, 1):
        t0 = time.time()
        with open(f'{A.logdir}/{i:02d}_{name}.log', 'w') as lg:
            rc = subprocess.run(cmd, stdout=lg, stderr=subprocess.STDOUT).returncode
        summary.append((i, name, rc, time.time() - t0)); print(f'{i:02d} {name:18s} exit {rc:3d} {time.time()-t0:7.1f}s', flush=True)
        if rc and not A.keep_going: failed = True; break
    n, bad = compare(A.ref)
    print(f'\ncompared {n} numeric leaves against {A.ref}: {len(bad)} differ by more than 1e-9 (relative)')
    for f, k, a, b in bad[:40]: print(f'  {f}{k}: {a} -> {b}')
    with open(f'{A.logdir}/SUMMARY.txt', 'w') as fh:
        fh.write('\n'.join(f'{i:02d} {n} exit {rc} {s:.1f}s' for i, n, rc, s in summary) + f'\ncompared {n} leaves, {len(bad)} differ\n')
        for f, k, a, b in bad: fh.write(f'  {f}{k}: {a} -> {b}\n')
    sys.exit(1 if failed or any(rc for _, _, rc, _ in summary) else 0)

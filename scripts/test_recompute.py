"""Reproducibility check: re-runs the same code on the same raw files and compares the output with the stored fixtures (the existing checks only compare stored JSON with the paper). It is not an independent test of correctness: a bug shared by the model code would pass.

    python -m scripts.test_recompute            # ~2 minutes; needs data/interim

Checks, per year 2019 / 2023 / 2025: (1) the LP gap rebuilt from raw SIH and CNES files equals the stored model gap to 1e-9;
(2) aggregate peak-volume cap over demand (the 1.368 / 1.321 / 1.160 series) equals the stored value to 1e-9;
(3) the number of facilities above 95 per cent of the bed-day budget at a fresh solve is within 1 of the stored count (the count is one vertex of an optimal face);
(4) net bed utilisation matches the stored value to 5e-3 (it differs by up to 0.003 because bed-day use is itself a property of the optimal vertex: a fresh solve lands on a different vertex of the same optimal face).
"""
import io, json, sys
import numpy as np
sys.argv = ['bootstrap_paired', 'combine']
import scripts.bootstrap_paired as B
from scipy import sparse
from scipy.optimize import linprog

stored = json.load(io.open('paper/numbers.json', encoding='utf-8'))['capability']
bad = []
for y in ('2019', '2023', '2025'):
    Y = B.Year(y); one = np.ones(len(Y.key))
    m = json.load(io.open(f'paper/model_{y}_roll3.json', encoding='utf-8')); gap_s = {q['label']: q for q in m['runs']}['cap 1x roll3']['gap']
    gap = Y.gap(one)
    # fresh solve for slack and bed use
    w = one; wJ = w[Y.sel]; pc = np.bincount(Y.pkv, weights=w, minlength=Y.NP); ps = np.bincount(Y.pkv, weights=w*Y.dias, minlength=Y.NP); pm = np.divide(ps, pc, out=np.zeros(Y.NP), where=pc > 0)
    cnt = np.bincount(Y.pairv_J, minlength=Y.npair); sm = np.bincount(Y.pairv_J, weights=Y.dias_J, minlength=Y.npair); lam = (sm + B.K*pm[Y.pair_pk])/(cnt + B.K)
    jm = np.bincount(Y.jkv_J*Y.nmonth + Y.moy_J, minlength=len(Y.J)*Y.nmonth).reshape(len(Y.J), Y.nmonth).astype(float); pmm = np.zeros((Y.npair, Y.nmonth)); np.add.at(pmm, (Y.pairv_J, Y.moy_J), 1.0)
    def r3(M):
        cs = np.cumsum(np.pad(M, ((0, 0), (1, 0))), axis=1); return ((cs[:, B.ROLL:] - cs[:, :-B.ROLL])/B.ROLL).max(axis=1)
    kj, kp = r3(jm), np.maximum(r3(pmm), 0.5); dem = np.bincount(Y.cellv, minlength=Y.nu)/12.0
    Cb = sparse.coo_matrix((lam[Y.colpair], (Y.rC, Y.cC)), shape=(len(Y.J), Y.nx+Y.nu)).tocsr()
    res = linprog(Y.obj, A_ub=sparse.vstack([Cb, Y.Sc, Y.Pb]).tocsr(), b_ub=np.concatenate([Y.B, kj, kp]), A_eq=Y.A, b_eq=dem, bounds=(0, None), method='highs')
    x = res.x[:Y.nx]; use = np.asarray(Cb[:, :Y.nx] @ x).ravel(); bb = int((use/Y.B > 0.95).sum())
    checks = [('gap', abs(gap - gap_s) < 1e-9, f'{gap:.12f} vs {gap_s:.12f}'),
              ('slack', abs(kj.sum()/dem.sum() - stored[y]['aggregate_slack']) < 1e-9, f'{kj.sum()/dem.sum():.12f} vs {stored[y]["aggregate_slack"]:.12f}'),
              ('bed_bound within 1', abs(bb - stored[y]['bedbound_n']) <= 1, f'{bb} vs {stored[y]["bedbound_n"]}'),
              ('bed_util', abs(use.sum()/Y.B.sum() - stored[y]['bed_util']) < 5e-3, f'{use.sum()/Y.B.sum():.4f} vs {stored[y]["bed_util"]:.4f}')]
    for name, ok, msg in checks:
        print(f'{y} {name:20s} {"PASS" if ok else "FAIL"}  {msg}')
        if not ok: bad.append((y, name))
print('\nPASS: recomputed headline results match the stored fixtures' if not bad else f'\nFAIL: {bad}')
sys.exit(1 if bad else 0)

"""Audit item 6: 20 re-solves with additive U(0,1e-4) noise on arc costs; stability of municipal excess and its top-15 ranking (PREREG_round4.md). Municipality names only (no personal data)."""
import sys, json, numpy as np, pandas as pd
from scipy.stats import spearmanr
sys.path.insert(0, 'dist/review')
import audit_year as AY
rng = np.random.default_rng(20261106); out = {}
ref = pd.read_csv('data/ref/ibge_municipios_go.csv', dtype=str); nm = dict(zip(ref.cod6, ref.nome))
for y in ('2019', '2023', '2025'):
    Y = AY.AYear(y); base = Y.solve()
    def excess(r):
        opt_i = pd.Series(Y.c * r['x']).groupby(Y.cell_i[Y.col_cell]).sum()                 # monthly optimal cost units per origin (true costs)
        obs_i = pd.Series(Y.obsc_all).groupby(Y.rec_i).sum() / 12.0
        e = (obs_i.reindex(opt_i.index) - opt_i); return e
    e0 = excess(base); top0 = list(e0.sort_values(ascending=False).head(15).index); tops, rho, gaps = [], [], []
    for k in range(20):
        r = Y.solve(c_noise=rng.uniform(0, 1e-4, Y.nx)); e = excess(r); tops.append(list(e.sort_values(ascending=False).head(15).index)); rho.append(spearmanr(e0, e.reindex(e0.index)).correlation); gaps.append(r['gap_J'])
    memb = pd.Series([m for t in tops for m in t]).value_counts(); stable = [m for m in top0 if memb.get(m, 0) >= 18]
    out[y] = dict(base_gap=base['gap_J'], gap_min=min(gaps), gap_max=max(gaps), spearman_mean=float(np.mean(rho)), spearman_min=float(np.min(rho)), top15_in_base=[nm[m] for m in top0],
                  top15_stable_ge18of20=[nm[m] for m in stable], n_stable=len(stable), share_top15_excess=float(e0.sort_values(ascending=False).head(15).sum()/e0.clip(lower=0).sum()))
    print(y, json.dumps({k: v for k, v in out[y].items() if k != 'top15_in_base'}), flush=True)
json.dump(out, open('dist/review/audit6_vertices.json', 'w'), indent=1)

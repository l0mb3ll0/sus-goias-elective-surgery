"""Regenerate the `flows_panel` and `model_peak` blocks of paper/numbers.json.

Reads the LP primal dumps written by scripts.model_run and the origin rankings
written by scripts.flows_rank. Nothing here is computed ad hoc.

    python -m scripts.flows_panel [--write]
"""
import json, io, sys
import pandas as pd, numpy as np
from scipy.stats import spearmanr

YEARS = ['2019', '2023', '2025']
NJ = 'paper/numbers.json'
RIO_VERDE = '521880'

d = json.load(io.open(NJ, encoding='utf-8'))
ranks = {y: pd.read_csv(f'paper/flows_rank_{y}_roll3.csv', dtype={'i': str}) for y in YEARS}
panel = {}

for y in YEARS:
    t = ranks[y]
    fl = pd.read_parquet(f'paper/flows_{y}_roll3.parquet')
    tot = float(t.excess.sum())
    panel[y] = {
        'arcs': int(len(fl)),
        'excess_total': tot,
        'top15_share': float(t.nlargest(15, 'excess').excess.sum() / tot),
        'own_muni_share': float(fl[fl.i == fl.muni_mov].x.sum() / fl.x.sum()),
        'n_muni': int((t.served > 0).sum()),
        'obs_mean_served_weighted': float((t.obs_c * t.served).sum() / t.served.sum()),
        'obs_mean_record_weighted': float((t.obs_c * t.obs_n).sum() / t.obs_n.sum()),
    }

for a, b in [('2019', '2023'), ('2023', '2025'), ('2019', '2025')]:
    m = ranks[a][['i', 'excess']].merge(ranks[b][['i', 'excess']], on='i', suffixes=('_a', '_b'))
    ta = set(ranks[a].nlargest(15, 'excess').i)
    tb = set(ranks[b].nlargest(15, 'excess').i)
    panel[f'{a}_{b}'] = {
        'spearman': float(spearmanr(m.excess_a, m.excess_b).statistic),
        'n': int(len(m)),
        'top15_overlap': int(len(ta & tb)),
    }

rv = {}
for y in YEARS:
    t = ranks[y].sort_values('excess', ascending=False).reset_index(drop=True)
    r = t[t.i == RIO_VERDE]
    fl = pd.read_parquet(f'paper/flows_{y}_roll3.parquet')
    fac = pd.read_parquet(f'paper/fac_{y}_roll3.parquet')
    jrv = fl[fl.muni_mov == RIO_VERDE].j.unique()
    res = fl[fl.i == RIO_VERDE]
    rv[y] = {
        'rank': int(r.index[0] + 1), 'of': int(len(t)),
        'excess': float(r.excess.iat[0]), 'obs_c': float(r.obs_c.iat[0]),
        'opt_c': float(r.opt_c.iat[0]), 'served_mo': float(r.served.iat[0]),
        'n_fac_local': int(len(jrv)),
        'cap_cases_local': float(fac[fac.j.isin(jrv)].cap_cases.sum()),
        'opt_share_kept_local': float(res[res.muni_mov == RIO_VERDE].x.sum() / res.x.sum()),
    }
panel['rio_verde'] = rv
d['flows_panel'] = panel

peak = {}
for y in YEARS:
    m = json.load(io.open(f'paper/model_{y}.json', encoding='utf-8'))
    r = {q['label']: q for q in m['runs']}[f'cap 1x peak']
    peak[y] = {'travel': r['travel'], 'gap': r['gap'], 'unmet_share': r['unmet_share'],
               'travel_obs': m['travel_obs'], 'n_fac': m['n_fac']}
peak['rule'] = 'single-month maximum in place of 3-month rolling mean'
d['model_peak'] = peak
d.pop('model_peak_2025', None)

# Share of the unconstrained gain that survives the 1x cap.
surv = {}
for y in YEARS:
    m = json.load(io.open(f'paper/model_{y}_roll3.json', encoding='utf-8'))
    rr = {q['label']: q for q in m['runs']}
    o = m['travel_obs']
    unc = o - rr['unconstrained']['travel']
    cap = o - rr['cap 1x roll3']['travel']
    surv[y] = {'unconstrained_gain': unc, 'capped_gain': cap, 'share_surviving': cap / unc}
d['cap_gain_survival'] = surv

if '--write' in sys.argv:
    json.dump(d, io.open(NJ, 'w', encoding='utf-8'), indent=1)
    print('written', NJ)

print(f"{'yr':6s}{'arcs':>6s}{'excess':>9s}{'top15':>8s}{'own':>8s}{'obs_sw':>8s}{'obs_rw':>8s}")
for y in YEARS:
    p = panel[y]
    print(f"{y:6s}{p['arcs']:>6d}{p['excess_total']:>9.1f}{p['top15_share']*100:>7.1f}%"
          f"{p['own_muni_share']*100:>7.1f}%{p['obs_mean_served_weighted']:>8.4f}"
          f"{p['obs_mean_record_weighted']:>8.4f}")
print()
for k in ['2019_2023', '2023_2025', '2019_2025']:
    print(f"  {k}: rho {panel[k]['spearman']:.3f}  top15 overlap {panel[k]['top15_overlap']}")
print()
for y in YEARS:
    r = rv[y]
    print(f"  Rio Verde {y}: rank {r['rank']}/{r['of']}  excess {r['excess']:+.1f}  "
          f"obs {r['obs_c']:.2f} opt {r['opt_c']:.2f}  cap {r['cap_cases_local']:.0f}  "
          f"kept local {r['opt_share_kept_local']*100:.0f}%")
print()
for y in YEARS:
    s = surv[y]
    print(f"  {y}: unconstrained gain {s['unconstrained_gain']:.4f}  capped {s['capped_gain']:.4f}  "
          f"surviving {s['share_surviving']*100:.1f}%")
print()
for y in YEARS:
    print(f"  peak {y}: {peak[y]['travel']:.4f}  gap {peak[y]['gap']*100:.1f}%")

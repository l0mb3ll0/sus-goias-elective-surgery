"""Write the review-pass results that the paper now cites into paper/numbers.json, so every printed number traces to the store.

Inputs (all under dist/review or paper/, produced by the scripts named in dist/sprint/WS4_results.md):
  dist/review/alt_optima.json       MILP bounds on the 2023 at-cap count across optima of equal cost (dist/review/alt_optima.py)
  dist/review/null_cap.json         stationary-Poisson null for the cap test (dist/review/null_cap.py)
  paper/model_urgent_<y>_elective.json, paper/model_urgent_<y>_urgent_instate_fixobs.json   bed-bound / cap-bound / overlap counts

    python -m scripts.store_review_results [--write]
"""
import io, json, sys
from scipy.stats import hypergeom

NJ = 'paper/numbers.json'
d = json.load(io.open(NJ, encoding='utf-8'))
ao = json.load(open('dist/review/alt_optima.json'))
f6min, f6max = ao['facility|1e-06|min'], ao['facility|1e-06|max']
f9max = ao['facility|1e-09|max']; p6min, p6max = ao['pair|1e-06|min'], ao['pair|1e-06|max']
d['alt_optima_2023'] = {
    'n_fac': 131, 'n_pairs_nonfloored': 517,
    'fac_point_solve': ao['point_fac'], 'fac_stored': 77,
    'fac_min': f6min['z_sum'], 'fac_min_proved': f6min['status'] == 0,
    'fac_max': f6max['z_sum'], 'fac_max_proved': f6max['status'] == 0,
    'fac_max_dual_bound_tol1e9': f9max['dual_bound'],
    'pair_point_solve': ao['point_pair'],
    'pair_min': p6min['z_sum'], 'pair_min_proved': p6min['status'] == 0,
    'pair_max_incumbent': p6max['z_sum'], 'pair_max_dual_bound': p6max['dual_bound'], 'pair_max_proved': p6max['status'] == 0,
    'threshold': 0.95, 'objective_tolerance': 1e-6,
}
nc = json.load(open('dist/review/null_cap.json'))
out = {}
for tr in ('2023->2024', '2024->2025'):
    r = nc[tr]['res']
    pick = lambda k: {kk: r[k][kk] for kk in ('null_exceed_mean', 'null_exceed_lo', 'null_exceed_hi', 'p', 'null_size_median')} | {'obs_exceed': r[k]['obs']['exceed'], 'obs_size': r[k]['obs']['size'], 'n': r[k]['obs']['n']}
    out[tr] = {'fac_at_cap': pick('elective|facility|at cap'), 'fac_at_cap_surgeons_rose': pick('elective|facility|at cap, surgeons rose'),
               'fac_at_cap_surgeons_not_rose': pick('elective|facility|at cap, surgeons did not'), 'urgent_fac_at_cap': pick('urgent|facility|at cap'),
               'null_at_cap_fac_mean': sum(a for a, b in nc[tr]['null_at_cap'])/len(nc[tr]['null_at_cap']), 'obs_at_cap_fac': nc[tr]['obs_at_cap'][0]}
d['cap_test_null'] = {'runs': 200, 'transitions': out}
res = {}
for y in ('2019', '2023', '2025'):
    for tag, f in (('elective', f'paper/model_urgent_{y}_elective.json'), ('urgent', f'paper/model_urgent_{y}_urgent_instate_fixobs.json')):
        m = json.load(open(f)); N, K, n, o = m['n_fac'], m['bedbound_n'], m['capbound_n'], m['both_n']
        res.setdefault(tag, {})[y] = {'n_fac': N, 'bed_bound': K, 'cap_bound': n, 'overlap': o, 'expected_overlap': K*n/N,
                                      'p_overlap_le_obs': float(hypergeom.cdf(o, N, K, n)), 'unmet_share': m['unmet']/m['demand_mo']}
d['disjointness_overlap_test'] = res
# ---- face analysis (dist/review/face_analysis.py), resampling null, flatter months, bootstrap variants, audit results ----
face = {}
for y in ('2019', '2023', '2025'):
    f = json.load(open(f'dist/review/face_{y}.json')); m = f['milp']
    face[y] = {'n_fac': f['n_fac'], 'reported': f['reported_vertex'], 'class_gt_095': f['classification']['A_gt_0.95'], 'class_ge_0999999': f['classification']['B_ge_0.999999'],
               'bed_class': f['bed_classification'], 'bed_bound_min': round(m['bed_min']['obj']), 'bed_bound_max': round(-m['bed_max']['obj']),
               'both_max_gt_095': round(-m['both_max_A']['obj']), 'both_max_ge_0999999': round(-m['both_max_B']['obj']),
               'cap_min': round(m['cap_min']['obj']), 'cap_max': round(-m['cap_max']['obj']), 'unused_min': m['unused_min']['obj'], 'unused_max': -m['unused_max']['obj'],
               'all_milps_proved': all(v['status'] == 0 for v in m.values())}
d['optimal_face'] = face
rs = json.load(open('dist/review/null_cap_resample_v2.json')); rso = {}
for tr, v in rs.items():
    r = v['res']['elective|facility|at cap']
    rso[tr] = {k: r[k] for k in ('null_exceed_mean', 'null_exceed_lo', 'null_exceed_hi', 'p', 'null_size_median', 'null_size_p025', 'null_size_p975')} | {'obs_exceed': r['obs']['exceed'], 'obs_size': r['obs']['size'], 'n': r['obs']['n']}
d['cap_test_resampling_null'] = {'runs': 200, 'transitions': rso}
d['flat_months_test'] = json.load(open('dist/sprint/WS4c_flatter.json'))
bf = {}
for tag, f in (('shrink_all_records', 'dist/review/boot_fixed_all.json'), ('shrink_model_facilities_only', 'dist/review/boot_fixed.json')):
    j = json.load(open(f)); bf[tag] = {}
    for y in ('2019', '2023', '2025'):
        pt = j['point'][y]['gap']; bf[tag][y] = {'point': pt}
        for var in ('full', 'kfix', 'dfix'):
            v = j['variants'][var][y]; bf[tag][y][var] = {'mean_gap': v['mean_gap'], 'sd_gap': v['sd_gap'], 'pct_lo': v['pct_lo'], 'pct_hi': v['pct_hi'], 'shift_pp': 100*(v['mean_gap']-pt),
                                                          'basic_lo': 2*pt - v['pct_hi'], 'basic_hi': 2*pt - v['pct_lo'], 'unmet_share': v.get('mean_unmet')}
d['bootstrap_variants'] = bf
mn = json.load(open('dist/review/boot_mn.json')); d['bootstrap_m_out_of_n'] = {k: mn[k] for k in mn if k.startswith('m_')}
a24 = json.load(open('dist/review/audit2_4.json')); d['audit_timing_beds_coverage'] = {k: {kk: vv for kk, vv in v.items() if kk in ('n_fac', 'gap_J', 'gap_all', 'ratio_cap_over_demand', 'sum_cap_over_sum_mean', 'at_cap', 'bed_bound', 'bed_util', 'interleaved_zero_facilities', 'obs_over_B', 'single_over_roll')} for k, v in a24.items() if '|' in k and 'captest' not in k} | {k: v for k, v in a24.items() if k.startswith('captest')}
d['audit_cost_recode'] = json.load(open('dist/review/audit9_cost.json'))
d['audit_zone_sensitivity'] = json.load(open('dist/review/audit14_zone.json'))
dc = json.load(open('dist/review/audit7_decomp.json')); d['decomposition_orders'] = {pi: {'options_share': v['options_share'], 'served_share': v['served_share'], 'adj': v['adj']} for pi, v in dc.items()}
import pandas as pd
cb = pd.read_csv('dist/review/audit5_crossborder.csv'); d['audit_cap_bracket'] = json.load(open('dist/review/audit15_cap_bracket.json'))
for pi, v in json.load(open('dist/review/audit7_decomp_pi4_10.json')).items(): d['decomposition_orders'][pi] = {'options_share': v['options_share'], 'served_share': v['served_share'], 'adj': v['adj']}
d['optimal_face_v2'] = {y: json.load(open(f'dist/review/face2_{y}.json')) for y in ('2019', '2023', '2025')}
d['bed_row_test'] = json.load(open('dist/review/audit_bed.json'))
d['cap_test_contrast'] = {m: {tr: {k: v[tr][k] for k in ('contrast_obs', 'contrast_null_mean', 'contrast_null_lo', 'contrast_null_hi', 'contrast_p_ge', 'runs')} for tr in v} for m in ('poisson', 'resample') for v in [json.load(open(f'dist/review/null_contrast_{m}.json'))]}
d['always_at_cap_2023'] = json.load(open('dist/review/always_set.json'))
d['bootstrap_sensitivity'] = {v: json.load(open(f'dist/review/boot_sens_{v}.json')) for v in ('cv05', 'bothfixed')}
d['record_flow'] = json.load(open('dist/review/record_flow.json'))
d['entorno_and_health_regions'] = json.load(open('dist/review/audit_final12.json'))
d['crossborder_DF'] = {f"{r.year}|{r.area}": {'in_RDGO': int(r.in_RDGO), 'in_RDDF': int(r.in_RDDF), 'share_in_DF': float(r.share_in_DF)} for r in cb.itertuples()}
t15 = {}
for y in ('2019', '2023', '2025'):
    t = pd.read_csv(f'paper/flows_rank_{y}_roll3.csv', dtype={'i': str}); top = t.nlargest(15, 'excess').excess.sum()
    t15[y] = {'share_of_net': float(top/t.excess.sum()), 'share_of_positive': float(top/t.excess.clip(lower=0).sum())}
d['top15_denominators'] = t15
for k in ('alt_optima_2023', 'cap_test_null', 'disjointness_overlap_test', 'optimal_face', 'cap_test_resampling_null', 'flat_months_test', 'bootstrap_variants', 'bootstrap_m_out_of_n', 'audit_timing_beds_coverage', 'audit_cost_recode', 'audit_zone_sensitivity', 'audit_cap_bracket', 'optimal_face_v2', 'bed_row_test', 'cap_test_contrast', 'always_at_cap_2023', 'bootstrap_sensitivity', 'record_flow', 'entorno_and_health_regions', 'decomposition_orders', 'crossborder_DF', 'top15_denominators'): print(k, json.dumps(d[k])[:160])
if '--write' in sys.argv:
    json.dump(d, io.open(NJ, 'w', encoding='utf-8'), indent=1); print('written', NJ)

import json, pathlib

N = pathlib.Path('paper/numbers.json')
n = json.loads(N.read_text())

def load(p):
    f = pathlib.Path(p)
    if not f.exists():
        raise SystemExit(f'missing {p} -- run the model scripts first')
    return json.loads(f.read_text())

m19 = load('paper/model_2019_roll3.json')
m23 = load('paper/model_2023_roll3.json')
dec = load('paper/model_decomp_roll3.json')

assert dec['pi'] == 6.0, f"decomp pi is {dec['pi']}, expected 6.0"
assert m19['cap_roll'] == 3 and m23['cap_roll'] == 3

def row(m, want):
    r = [x for x in m['runs'] if x['label'].startswith(want)]
    assert len(r) == 1, f'{want}: {len(r)} matches'
    return r[0]

def pack(m):
    u = row(m, 'unconstrained'); c1 = row(m, 'cap 1x')
    return {'travel_obs': m['travel_obs'], 'demand_mo': m['demand_mo'],
            'n_fac': m['n_fac'], 'n_muni': m['n_muni'],
            'unconstrained': u['travel_adj'], 'unconstrained_gap': u['gap_adj'],
            'cap1x': c1['travel_adj'], 'cap1x_gap': c1['gap_adj'],
            'cap1x_util': c1['util'], 'cap1x_binding': c1['binding'],
            'ladder': [{'label': r['label'], 'travel_adj': r['travel_adj'],
                        'gap_adj': r['gap_adj'], 'util': r['util'],
                        'binding': r['binding'], 'unmet_share': r['unmet_share']}
                       for r in m['runs']]}

n['model_2019'] = pack(m19)
n['model_2023'] = pack(m23)
n['model_caps'] = {'rule': 'max 3-month rolling mean of monthly volume',
                   'pi': 6.0,
                   'why': 'raw monthly peak inflated by batch reporting; 37 of 136 '
                          'facilities with 2023 elective volume report interleaved '
                          'zeros, 12.4 per cent of volume',
                   'pi_invariance': 'A/B/C/D ordering unchanged at pi = 4, 6, 10'}
n['model_decomp'] = {'obs_2019': dec['obs_2019'], 'obs_2023': dec['obs_2023'],
                     'runs': [{'label': r['label'], 'travel_adj': r['travel_adj'],
                               'travel_served_only': r['travel_opt'],
                               'unmet_share': r['unmet_share'],
                               'scope_pairs': r['scope_pairs']} for r in dec['runs']],
                     'note': 'travel_adj charges unmet at pi and divides by total '
                             'demand; travel_served_only is selected on the served '
                             'subset and is not comparable across rows when unmet > 0'}
n['entrants_2023'] = {'new_pairs': 284, 'new_pair_cases': 21845, 'share_of_2023': 0.275,
                      'facility_absent_2019_cases': 18370, 'new_proc_existing_fac_cases': 3475,
                      'extensive_share': 0.841,
                      'conversion_cnes': '9680977', 'conversion_cases': 5568}

N.write_text(json.dumps(n, indent=1))
print('keys', len(n))
for k in ['model_2019', 'model_2023', 'model_decomp', 'model_caps', 'entrants_2023']:
    print(' ', k, 'ok' if k in n else 'MISSING')
print('2019 cap1x %.4f %+.1f%%' % (n['model_2019']['cap1x'], 100*n['model_2019']['cap1x_gap']))
print('2023 cap1x %.4f %+.1f%%' % (n['model_2023']['cap1x'], 100*n['model_2023']['cap1x_gap']))
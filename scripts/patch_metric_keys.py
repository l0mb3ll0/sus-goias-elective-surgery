import json, pathlib

N = pathlib.Path('paper/numbers.json')
n = json.loads(N.read_text())

def load(y):
    return json.loads(pathlib.Path(f'paper/model_metric_{y}.json').read_text())

def pack(m):
    d = {r['metric']: r for r in m['runs']}
    return {'obs_ordinal': m['obs_ordinal'], 'obs_km': m['obs_km'],
            'opt_ordinal': d['ordinal']['opt'], 'gap_ordinal': d['ordinal']['gap'],
            'opt_km': d['metric']['opt'], 'gap_km': d['metric']['gap'],
            'ordinal_soln_km': d['ordinal']['cross_eval'],
            'metric_soln_ordinal': d['metric']['cross_eval']}

n['model_metric'] = {'2019': pack(load('2019')), '2023': pack(load('2023')),
                     'note': 'great-circle km between municipal seats; ignores road network'}
N.write_text(json.dumps(n, indent=1))
print('keys', len(n))
print('2019 gap km %.1f%% | 2023 %.1f%%' % (100*n['model_metric']['2019']['gap_km'],
                                            100*n['model_metric']['2023']['gap_km']))

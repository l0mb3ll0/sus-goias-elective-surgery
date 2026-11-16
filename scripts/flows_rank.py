import pandas as pd, numpy as np, sys

YEAR = sys.argv[1] if len(sys.argv) > 1 else '2023'
SUF = 'roll3'
fl = pd.read_parquet(f'paper/flows_{YEAR}_{SUF}.parquet')
um = pd.read_parquet(f'paper/unmet_{YEAR}_{SUF}.parquet')
ob = pd.read_parquet(f'paper/obs_i_{YEAR}_{SUF}.parquet')
ref = pd.read_csv('data/ref/ibge_municipios_go.csv', dtype=str)
nm = dict(zip(ref.cod6, ref.nome))

print(f'arcs {len(fl)} | served {fl.x.sum():.1f} | unmet {um.u.sum():.1f} '
      f'| opt mean {np.average(fl.c, weights=fl.x):.4f}')

fp = fl[np.isclose(fl.ub, 0.5)]
fpb = fp[fp.x >= fp.ub - 1e-9]
print(f'floored pairs (ub=0.5): {fp[["j","p"]].drop_duplicates().shape[0]} arcs-at-pairs, '
      f'{fpb.x.sum():.1f} cases/mo at the floor ({fpb.x.sum()/fl.x.sum():.2%} of served)')

g = fl.groupby('i').apply(
    lambda t: pd.Series({'opt_c': np.average(t.c, weights=t.x), 'served': t.x.sum()}),
    include_groups=False).reset_index()
u = um.groupby('i').agg(d=('d','sum'), unmet=('u','sum')).reset_index()
m = g.merge(ob, on='i', how='outer').merge(u, on='i', how='outer').fillna(0)
m['nome'] = m.i.map(nm)
m['delta'] = m.obs_c - m.opt_c
m['excess'] = m.delta * m.served

t = m[m.served > 0].sort_values('excess', ascending=False)
print('\ntop origins by excess travel (cost-units/month)')
print(t.head(15)[['i','nome','obs_n','obs_c','opt_c','delta','served','unmet','excess']]
      .to_string(index=False, float_format=lambda v: f'{v:.3f}'))

print('\nwhere the top 5 should send patients')
for _, r in t.head(5).iterrows():
    a = fl[fl.i == r.i].groupby(['p','j','muni_mov']).x.sum().reset_index()
    a['dest'] = a.muni_mov.map(nm)
    a = a.sort_values('x', ascending=False).head(6)
    print(f"\n{r.nome} ({r.i})  obs {r.obs_c:.2f} -> opt {r.opt_c:.2f}")
    print(a[['p','j','dest','x']].to_string(index=False, float_format=lambda v: f'{v:.2f}'))

t.to_csv(f'paper/flows_rank_{YEAR}_{SUF}.csv', index=False)
print(f'\nwrote paper/flows_rank_{YEAR}_{SUF}.csv')

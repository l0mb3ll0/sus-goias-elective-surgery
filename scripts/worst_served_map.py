"""Map of the fifteen worst-served municipalities and where the optimum sends them.

Arrows run from municipality of residence to the municipality of the facility the
optimum assigns, weighted by volume. Origins are sized by excess ordinal cost.

    python -m scripts.worst_served_map 2025
"""
import sys
import numpy as np, pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

YEAR = sys.argv[1] if len(sys.argv) > 1 else '2025'

xy = pd.read_csv('data/ref/ibge_municipios_go_xy.csv', dtype={'cod6': str})
lon = dict(zip(xy.cod6, pd.to_numeric(xy.longitude, errors='coerce')))
lat = dict(zip(xy.cod6, pd.to_numeric(xy.latitude, errors='coerce')))
nm = dict(zip(xy.cod6, xy.nome))

rank = pd.read_csv(f'paper/flows_rank_{YEAR}_roll3.csv', dtype={'i': str})
fl = pd.read_parquet(f'paper/flows_{YEAR}_roll3.parquet')
worst = rank.nlargest(15, 'excess')

fig, ax = plt.subplots(figsize=(7.2, 7.0))
ax.scatter([lon[c] for c in xy.cod6 if c in lon], [lat[c] for c in xy.cod6 if c in lat],
           s=3, c='0.86', zorder=1, linewidths=0)

for r in worst.itertuples():
    if r.i not in lon: continue
    g = fl[fl.i == r.i].groupby('muni_mov').x.sum().sort_values(ascending=False)
    g = g[g.index != r.i].head(3)
    for m, v in g.items():
        if m not in lon: continue
        ax.annotate('', xy=(lon[m], lat[m]), xytext=(lon[r.i], lat[r.i]),
                    arrowprops=dict(arrowstyle='-|>', color='#c0392b',
                                    alpha=min(0.85, 0.25 + v/g.max()*0.5),
                                    linewidth=0.5 + 2.0*v/max(g.max(), 1e-9),
                                    shrinkA=3, shrinkB=3), zorder=2)

sz = worst.excess / worst.excess.max()
ax.scatter([lon.get(c) for c in worst.i], [lat.get(c) for c in worst.i],
           s=25 + 220*sz, c='#1f4e79', zorder=3, edgecolors='white', linewidths=0.8)
for r in worst.itertuples():
    if r.i not in lon: continue
    ax.annotate(nm.get(r.i, ''), (lon[r.i], lat[r.i]), textcoords='offset points',
                xytext=(6, 5), fontsize=7.2, zorder=4)

ax.set_title(f'Fifteen largest contributors to excess ordinal cost, {YEAR},\n'
             'and where the optimum would send their patients', fontsize=10)
ax.set_xlabel('longitude'); ax.set_ylabel('latitude')
ax.set_aspect('equal', adjustable='datalim')
for s in ('top', 'right'): ax.spines[s].set_visible(False)
fig.tight_layout()
fig.savefig(f'paper/fig4_worst_served_{YEAR}.pdf')
print(f'written paper/fig4_worst_served_{YEAR}.pdf | origins plotted '
      f'{sum(1 for c in worst.i if c in lon)} of 15')

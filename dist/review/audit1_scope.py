"""Audit item 1: what the elective_isect restriction removes. Aggregates only. PREREG_round4.md item 1."""
import sys, glob, numpy as np, pandas as pd
sys.path.insert(0, 'dist/review')
import _boot_src as S
ref = pd.read_csv('data/ref/ibge_municipios_go.csv', dtype=str); GO = set(ref.cod6)
for y in ('2019', '2023', '2025'):
    Y = S.Year(y); J = set(Y.J)
    a = pd.concat([pd.read_parquet(f, columns=['CNES', 'PROC_REA', 'CAR_INT', 'MUNIC_RES']) for f in sorted(glob.glob(f'data/interim/sih/RDGO{y[2:]}*.parquet'))])
    a = a[(a.PROC_REA.str[:2] == '04') & a.MUNIC_RES.astype(str).str[:6].isin(GO)].copy(); a['p'] = a.PROC_REA.str[:4]
    el = a[a.CAR_INT == '01']; ur = a[a.CAR_INT != '01']
    Se = set(zip(*[Y.pair_keys[k] for k in range(len(Y.pair_keys))]) ) if False else set(Y.pair_keys)       # (j,p) elective scope at J
    Su = set(zip(ur.CNES, ur.p))
    inter = Se & Su; only_e = Se - Su
    cnt = el.groupby(['CNES', 'p']).size(); tot = cnt[[k for k in cnt.index if k[0] in J]].sum()
    vol_only_e = cnt[[k for k in only_e if k in cnt.index]].sum()
    fac_inter = {j for j, p in inter}; dropped_fac = len(J) - len(fac_inter)
    # demand cells with no remaining option: procedures p with no facility in inter
    procs_e = {p for j, p in Se}; procs_i = {p for j, p in inter}
    dem = el.groupby('p').size(); lost = dem[[p for p in dem.index if p not in procs_i]].sum()
    print(f'{y}: elective scope pairs {len(Se)}, with urgent history {len(inter)} ({100*len(inter)/len(Se):.1f}%), elective-only {len(only_e)}; '
          f'elective cases at J pairs outside the intersection {100*vol_only_e/tot:.1f}%; facilities with no intersection pair {dropped_fac} of {len(J)}; '
          f'in-state elective cases in procedures with no intersection facility {100*lost/dem.sum():.1f}%')

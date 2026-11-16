"""Audit item 5: Goias-resident elective surgical AIH treated in DF (RDDF), and residence codes dropped by the paper's filter in RDGO. Aggregates only."""
import glob, numpy as np, pandas as pd
ref = pd.read_csv('data/ref/ibge_municipios_go.csv', dtype=str); GO = set(ref.cod6); nm = dict(zip(ref.cod6, ref.nome))
named = ['Águas Lindas de Goiás', 'Valparaíso de Goiás', 'Luziânia']
ents = ref[ref.nome.isin(named)]; regs = set(ents.reg_imediata); print('immediate regions of the three named municipalities:', sorted(regs))
ento_named = set(ents.cod6); ento_regions = set(ref[ref.reg_imediata.isin(regs)].cod6)
print(f'named {len(ento_named)} municipalities; municipalities in their immediate regions {len(ento_regions)}')
def load(path_glob):
    a = pd.concat([pd.read_parquet(f, columns=['PROC_REA', 'CAR_INT', 'MUNIC_RES', 'CNES']) for f in sorted(glob.glob(path_glob))])
    return a[(a.PROC_REA.str[:2] == '04') & (a.CAR_INT == '01')].copy()
rows = []
for y in ('19', '23', '25'):
    go = load(f'data/interim/sih/RDGO{y}*.parquet'); df = load(f'data/pilot/DF/interim/sih/RDDF{y}*.parquet')
    for d in (go, df): d['res'] = d.MUNIC_RES.astype(str).str[:6]
    go_in = go[go.res.isin(GO)]; df_go = df[df.res.isin(GO)]
    g = go_in.groupby('res').size(); d_ = df_go.groupby('res').size()
    for label, S in (('all Goias', set(GO)), ('3 named Entorno', ento_named), ('their immediate regions', ento_regions)):
        a_, b_ = int(g.reindex(list(S)).fillna(0).sum()), int(d_.reindex(list(S)).fillna(0).sum())
        rows.append(dict(year='20'+y, area=label, in_RDGO=a_, in_RDDF=b_, share_in_DF=b_/(a_+b_)))
    # dropped codes in RDGO
    drop = go[~go.res.isin(GO)]; uf = drop.res.str[:2]
    print(f'20{y}: RDGO elective surgical AIH {len(go):,}; residence not in Goias list {len(drop):,} ({100*len(drop)/len(go):.1f}%); by UF prefix:', uf.value_counts().head(8).to_dict(),
          '; invalid/blank:', int((~drop.res.str.isdigit() | (drop.res.str.len() < 6)).sum()), '; RDDF elective surgical AIH', len(df), '; of which Goias residents', len(df_go), f'({100*len(df_go)/len(df):.1f}%)')
    per = pd.DataFrame({'GO': g, 'DF': d_}).fillna(0); per['share'] = per.DF/(per.GO+per.DF); top = per.sort_values('DF', ascending=False).head(6)
    print('   top municipalities by AIH treated in DF (share of their treated elective surgical AIH):', {nm[k]: (int(r.DF), round(100*r.share, 1)) for k, r in top.iterrows()})
t = pd.DataFrame(rows); print(t.round(4).to_string(index=False)); t.to_csv('dist/review/audit5_crossborder.csv', index=False)

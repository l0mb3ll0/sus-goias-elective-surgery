import pandas as pd

BREAK = '202209'
PRE  = ('202112', '202207')
POST = ('202209', '202307')

st = pd.read_parquet('data/interim/cnes_st_raw.parquet')
st['CNES'] = st.CNES.astype(str).str.zfill(7)
st['comp'] = st.comp.astype(str)
pan = pd.read_parquet('data/interim/hospital_panel.parquet')
pan['comp'] = pan.COMPETENCIA.str.replace('-', '', regex=False)

s = st[st.CNES.isin(set(pan.CNES))].sort_values('comp')

sw, first, at_break = {}, {}, {}
for c, g in s.groupby('CNES'):
    v, m = g.TPGESTAO.tolist(), g.comp.tolist()
    first[c] = v[0]
    prior = [v[i] for i in range(len(v)) if m[i] < BREAK]
    at_break[c] = prior[-1] if prior else None
    for i in range(1, len(v)):
        if v[i] == 'E' and v[i-1] == 'M':
            sw[c] = m[i]
            break

def grp(c):
    if at_break.get(c) is None:
        return 'unknown'
    if at_break[c] != 'E':
        return 'municipal_at_break'
    return 'transferred' if first[c] == 'M' else 'always_state'

pan['treat_cnes'] = pan.CNES.map(sw)
pan['group'] = pan.CNES.map(grp)
pan.loc[pan.CNES == '5419662', 'group'] = 'excluded'

print(pan.groupby('group').CNES.nunique().to_string())
print('\nswitchers inside PRE:',
      sorted(c for c, m in sw.items() if PRE[0] <= m <= PRE[1]))
print('switchers after BREAK:',
      sorted(c for c, m in sw.items() if m >= BREAK))

def win(d, lo, hi, col):
    return d[d.comp.between(lo, hi)].groupby('comp')[col].sum().mean()

tot_pre, tot_post = win(pan, *PRE, 'elec'), win(pan, *POST, 'elec')
rows = []
for lab, d in pan.groupby('group'):
    if lab in ('unknown', 'excluded'):
        continue
    ea, eb = win(d, *PRE, 'elec'), win(d, *POST, 'elec')
    ua, ub = win(d, *PRE, 'urg'),  win(d, *POST, 'urg')
    rows.append({
        'group': lab, 'n': d.CNES.nunique(),
        'elec_pre': round(ea), 'elec_post': round(eb), 'elec_g': f'{eb/ea-1:+.1%}',
        'urg_pre': round(ua), 'urg_post': round(ub), 'urg_g': f'{ub/ua-1:+.1%}',
        'ratio_pre': round(ea/ua, 3), 'ratio_post': round(eb/ub, 3),
        'share_pre': f'{ea/tot_pre:.1%}', 'share_post': f'{eb/tot_post:.1%}',
    })
print()
print(pd.DataFrame(rows).to_string(index=False))
print(f'\nstate total elec {tot_pre:.0f} -> {tot_post:.0f} ({tot_post/tot_pre-1:+.1%})')

ex = pan[pan.group == 'excluded']
print(f"5419662 (excluded, switches 2022-04): elec "
      f"{win(ex,*PRE,'elec'):.0f} -> {win(ex,*POST,'elec'):.0f}")

pan['ym'] = pan.comp.astype(int)//100*12 + pan.comp.astype(int)%100
tc = pan.treat_cnes.dropna().astype(int)
pan['t_cnes'] = pan.ym - (tc//100*12 + tc%100).reindex(pan.index)
pan.drop(columns='ym').to_parquet('data/interim/hospital_panel_v2.parquet')
print('\nwrote hospital_panel_v2.parquet')


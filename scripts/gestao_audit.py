import pandas as pd

st = pd.read_parquet('data/interim/cnes_st_raw.parquet')
st['CNES'] = st.CNES.astype(str).str.zfill(7)
st['comp'] = st.comp.astype(str)
pan = pd.read_parquet('data/interim/hospital_panel.parquet')

s = st[st.CNES.isin(set(pan.CNES))].sort_values('comp')
g = s.groupby('CNES').TPGESTAO
tab = pd.DataFrame({'first': g.first(), 'last': g.last(), 'nuniq': g.nunique()})
print(pd.crosstab(tab['first'], tab['last']))
print()
print(tab.nuniq.value_counts().to_string())

sw = {}
for c, gg in s.groupby('CNES'):
    v, m = gg.TPGESTAO.tolist(), gg.comp.tolist()
    for i in range(1, len(v)):
        if v[i] == 'E' and v[i-1] == 'M':
            sw[c] = m[i]
            break
print()
print('switchers:', len(sw))
print(pd.Series(sw).sort_values().to_string())


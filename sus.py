"""Shared loader. Import this instead of re-globbing parquet in every script."""
import pandas as pd, glob

def load(kind='all'):
    df = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob('data/interim/sih/*.parquet'))],
                   ignore_index=True)
    assert df.index.is_unique, 'index not unique'
    df['grupo'] = df['PROC_REA'].astype(str).str[:2]
    df['GESTAO'] = df['GESTAO'].astype(str)
    df['CNES'] = df['CNES'].astype(str).str.zfill(7)
    df['adm'] = pd.to_datetime(df['DT_INTER'].astype(str), format='%Y%m%d',
                               errors='coerce').dt.to_period('M').astype(str)
    cir = df[df['grupo'] == '04']
    if kind == 'all':      return cir
    if kind == 'elective': return cir[cir['CAR_INT'] == '01'].copy()
    if kind == 'urgent':   return cir[cir['CAR_INT'] == '02'].copy()
    raise ValueError(kind)

def monthly_ratio(cir, index='COMPETENCIA'):
    p = cir.pivot_table(index=index, columns='CAR_INT', aggfunc='size', fill_value=0)
    r = pd.DataFrame({'elec': p['01'], 'urg': p['02']})
    r['ratio'] = r['elec'] / r['urg']
    return r

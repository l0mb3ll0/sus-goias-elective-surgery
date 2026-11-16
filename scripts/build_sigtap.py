"""Extract SIGTAP procedure names from the monthly TabelaUnificada ZIP.

Writes data/ref/sigtap_procedimentos.csv with the 10-digit code, name,
complexity, and official permanence days, plus a 4-digit subgroup name
table derived from it.
"""
import zipfile, pandas as pd, glob, pathlib

Z = sorted(glob.glob('data/ref/TabelaUnificada_*.zip'))[-1]
print('reading', Z)
z = zipfile.ZipFile(Z)

lay = pd.read_csv(z.open('tb_procedimento_layout.txt'), dtype=str)
lay['Inicio'] = lay.Inicio.astype(int); lay['Fim'] = lay.Fim.astype(int)
spec = [(r.Inicio - 1, r.Fim) for r in lay.itertuples()]

df = pd.read_fwf(z.open('tb_procedimento.txt'), colspecs=spec,
                 names=lay.Coluna.tolist(), dtype=str, encoding='latin-1')
for c in ['CO_PROCEDIMENTO', 'NO_PROCEDIMENTO', 'TP_COMPLEXIDADE']:
    df[c] = df[c].astype(str).str.strip()
df['QT_DIAS_PERMANENCIA'] = pd.to_numeric(df.QT_DIAS_PERMANENCIA, errors='coerce')

out = df[['CO_PROCEDIMENTO', 'NO_PROCEDIMENTO', 'TP_COMPLEXIDADE', 'QT_DIAS_PERMANENCIA']].copy()
out['subgrupo'] = out.CO_PROCEDIMENTO.str[:4]
out.to_csv('data/ref/sigtap_procedimentos.csv', index=False)
print('procedures', len(out), '| group 04', int((out.CO_PROCEDIMENTO.str[:2] == '04').sum()))

# check coverage against the codes actually used in the panel
sih = pd.concat([pd.read_parquet(f, columns=['PROC_REA', 'CAR_INT'])
                 for f in sorted(glob.glob('data/interim/sih/RDGO23*.parquet'))])
sih = sih[(sih.PROC_REA.str[:2] == '04') & (sih.CAR_INT == '01')]
used = set(sih.PROC_REA.unique()); have = set(out.CO_PROCEDIMENTO)
miss = used - have
print('distinct 2023 elective procedures', len(used), '| unmatched', len(miss))
if miss: print('  examples', sorted(miss)[:10])

sub = (out[out.CO_PROCEDIMENTO.str[:2] == '04']
       .groupby('subgrupo').size().rename('n_procedures').reset_index())
print(sub.to_string(index=False))
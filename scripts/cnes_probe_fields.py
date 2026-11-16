"""Phase 0 populatedness probe. Reads and reports; extracts no deliverable.

A column being present in the header says nothing about it carrying data. This
reports, per candidate column, how many rows are actually non-null, restricted to
Goias establishments. Goias is identified by CO_UNIDADE[:6] starting '52' --
CO_UNIDADE is municipality IBGE6 concatenated with the CNES code, which is the
only establishment-location key in the base dump; tbEstabelecimento has no
CO_MUNICIPIO column of its own.
"""
import io, zipfile
import pandas as pd

ZIP = 'data/raw/cnes/BASE_DE_DADOS_CNES_202606.ZIP'
V = '202606'
z = zipfile.ZipFile(ZIP)


def rd(name, cols=None):
    with z.open(f'{name}{V}.csv') as fh:
        return pd.read_csv(io.TextIOWrapper(fh, 'latin-1'), sep=';', dtype=str,
                           usecols=cols, quotechar='"', low_memory=False)


def nn(df, col):
    """Non-null and non-blank count. isna() first; blanks are '' after strip."""
    s = df[col]
    ok = s.notna() & (s.astype(str).str.strip() != '')
    return int(ok.sum()), 100.0 * ok.mean()


def report(df, name, cols, key='CO_UNIDADE'):
    if key in df.columns:
        df = df[df[key].astype(str).str[:2] == '52']
    print(f'\n{name}  ({len(df):,} Goias rows)')
    for c in cols:
        n, p = nn(df, c)
        u = df[c].nunique(dropna=True)
        print(f'   {c:26s} {n:>9,} non-null {p:5.1f}%  uniq={u}')
    return df


# ---- operating rooms -------------------------------------------------------
inst_lab = rd('tbInstalFisicaParaAssist')
print('=== tbInstalFisicaParaAssist: the physical-installation label table ===')
for r in inst_lab.itertuples():
    if any(k in str(r.DS_INSTALACAO).upper()
           for k in ('CIRUR', 'CIRÚR', 'PARTO', 'OBSTET', 'RECUPER')):
        print(f'   CO_INSTALACAO {r.CO_INSTALACAO:>4}  subtipo {r.CO_SUBTIPO_INSTALACAO:>3}'
              f'  TP {r.TP_INSTALACAO}  {r.DS_INSTALACAO}')

ifa = rd('rlEstabInstFisiAssist')
ifa = report(ifa, 'rlEstabInstFisiAssist', ['CO_INSTALACAO', 'QT_INSTALACAO', 'NU_LEITOS'])

# ---- equipment -------------------------------------------------------------
eq_lab = rd('tbEquipamento')
print('\n=== tbEquipamento: entries matching video/laparoscopy/endoscopy ===')
for r in eq_lab.itertuples():
    if any(k in str(r.DS_EQUIPAMENTO).upper()
           for k in ('VIDEO', 'VÍDEO', 'LAPAR', 'ENDOSC', 'CIRUR', 'CIRÚR')):
        print(f'   CO_EQUIPAMENTO {r.CO_EQUIPAMENTO:>4}  tipo {r.CO_TIPO_EQUIPAMENTO}'
              f'  {r.DS_EQUIPAMENTO}')

eqp = rd('rlEstabEquipamento')
eqp = report(eqp, 'rlEstabEquipamento',
             ['CO_EQUIPAMENTO', 'QT_EXISTENTE', 'QT_USO', 'QT_SUS', 'TP_SUS'])

# ---- beds ------------------------------------------------------------------
cmp_ = rd('rlEstabComplementar')
cmp_ = report(cmp_, 'rlEstabComplementar', ['CO_LEITO', 'QT_EXIST', 'QT_SUS'])
print('   CO_LEITO values present:', sorted(cmp_.CO_LEITO.dropna().unique())[:30])

# ---- professionals and contracted hours ------------------------------------
# tbCargaHorariaSus is 870 MB uncompressed; stream it and keep only Goias.
print('\n=== tbCargaHorariaSus (streamed, Goias only) ===')
keep, tot = [], 0
with z.open(f'tbCargaHorariaSus{V}.csv') as fh:
    for ch in pd.read_csv(io.TextIOWrapper(fh, 'latin-1'), sep=';', dtype=str,
                          quotechar='"', chunksize=500_000, low_memory=False):
        tot += len(ch)
        keep.append(ch[ch.CO_UNIDADE.astype(str).str[:2] == '52'])
ch_go = pd.concat(keep, ignore_index=True)
print(f'   {tot:,} rows nationally -> {len(ch_go):,} Goias vinculos')
for c in ['CO_PROFISSIONAL_SUS', 'CO_CBO', 'QT_CARGA_HORARIA_AMBULATORIAL',
          'QT_CARGA_HOR_HOSP_SUS', 'QT_CARGA_HORARIA_OUTROS', 'TP_SUS_NAO_SUS',
          'IND_VINCULACAO', 'CO_CONSELHO_CLASSE', 'NU_REGISTRO']:
    n, p = nn(ch_go, c)
    print(f'   {c:32s} {n:>9,} non-null {p:5.1f}%  uniq={ch_go[c].nunique()}')
for c in ['QT_CARGA_HORARIA_AMBULATORIAL', 'QT_CARGA_HOR_HOSP_SUS',
          'QT_CARGA_HORARIA_OUTROS']:
    v = pd.to_numeric(ch_go[c], errors='coerce')
    print(f'   {c:32s} >0 in {int((v > 0).sum()):>8,} rows  '
          f'({100*(v > 0).mean():4.1f}%)  mean|>0 {v[v > 0].mean():.1f}')
ch_go.to_parquet('data/interim/cnes_carga_GO.parquet')
print('   cached -> data/interim/cnes_carga_GO.parquet (interim, not tracked)')

# ---- services and specialties ----------------------------------------------
sc = rd('rlEstabServClass')
sc = report(sc, 'rlEstabServClass',
            ['CO_SERVICO', 'CO_CLASSIFICACAO', 'CO_HOSPITALAR', 'CO_HOSPITALAR_SUS',
             'CO_AMBULATORIAL_SUS', 'ST_ATIVO_SN', 'TP_CARACTERISTICA'])
sc.to_parquet('data/interim/cnes_servclass_GO.parquet')

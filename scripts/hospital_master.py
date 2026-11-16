"""Phase 1 -- one row per Goias establishment appearing in SIH elective surgery.

WINDOW BASIS. Everything is 2024-01..2025-12 (24 months) unless a column note
says otherwise. Resources and volume therefore share a window, which the 202606
base-ZIP snapshot could not provide.

THE ONE EXCEPTION, stated rather than hidden. Operating-room COUNTS exist only in
the base-ZIP snapshot (rlEstabInstFisiAssist.QT_INSTALACAO, vintage 2026-06). The
monthly ST file carries CENTRCIR, which is a 0/1 flag, not a count -- verified,
2 distinct values, max 1. So room counts are as-of 2026-06 and are marked _snap.
CENTRCIR is carried separately as the time-varying presence check.

FIELD NOTES
  - surgeon    = CBO 225225 exactly (MEDICO CIRURGIAO GERAL)
  - anaesth    = CBO 225151 exactly (MEDICO ANESTESIOLOGISTA)
  - nurse_2235 = CBO prefix 2235, a PROXY: the surgical-nurse code 223520 is
    unusable, recorded at only 14 establishments in the whole state.
  - Never match surgeons by label substring: 'CIRURGIAO' also matches 33 dental
    codes (223204-223293, CIRURGIAO DENTISTA).
  - EQ/LT/PF code fields are zero-padded before comparison. TIPEQUIP switched
    from '3' to '03' at 2025-09; an unpadded match silently loses every
    laparoscope from that month on.

    python -m scripts.hospital_master
"""
import glob, io, zipfile
import numpy as np
import pandas as pd

MONTHS = [f'{y}-{m:02d}' for y in (2024, 2025) for m in range(1, 13)]
COMPS = [int(m.replace('-', '')) for m in MONTHS]
SURG_BEDS = {'01','02','03','04','05','06','08','09','11','12','13','14','15',
             '16','67','90','91','10','68','83'}          # the panel's set
ROOMS = {'31': 'or_main_snap', '30': 'or_amb_t1_snap',
         '33': 'or_amb_snap', '37': 'or_obst_snap'}
ZIP = 'data/raw/cnes/BASE_DE_DADOS_CNES_202606.ZIP'


def z_read(name, **kw):
    z = zipfile.ZipFile(ZIP)
    with z.open(f'{name}202606.csv') as fh:
        return pd.read_csv(io.TextIOWrapper(fh, 'latin-1'), sep=';', dtype=str,
                           quotechar='"', low_memory=False, **kw)


unmatched = {}

# ---------------------------------------------------------------- SIH volume
files = sorted(glob.glob('data/interim/sih/RDGO24*.parquet')) + \
        sorted(glob.glob('data/interim/sih/RDGO25*.parquet'))
a = pd.concat([pd.read_parquet(f, columns=['CNES', 'PROC_REA', 'CAR_INT',
                                           'DIAS_PERM', 'COMPETENCIA'])
               for f in files])
sg = a.PROC_REA.str[:2] == '04'
el = a[sg & (a.CAR_INT == '01')]
ur = a[sg & (a.CAR_INT != '01')]
J = sorted(el.CNES.unique())                     # the universe: elective surgery
m = pd.DataFrame(index=pd.Index(J, name='CNES'))
m['elective_2425'] = el.groupby('CNES').size().reindex(J).fillna(0).astype(int)
m['urgent_2425'] = ur.groupby('CNES').size().reindex(J).fillna(0).astype(int)
print(f'universe: {len(J)} establishments with elective surgery 2024-25')

# ------------------------------------------------------------------ identity
est = z_read('tbEstabelecimento')
est['cnes'] = est.CO_UNIDADE.astype(str).str[6:]
est['mun'] = est.CO_UNIDADE.astype(str).str[:6]
est = est[est.CO_ESTADO_GESTOR.astype(str).str.strip() == '52']
est = est.drop_duplicates('cnes').set_index('cnes')
hit = est.index.intersection(J)
unmatched['tbEstabelecimento'] = len(J) - len(hit)
for src, dst in [('NO_FANTASIA', 'name'), ('NO_LOGRADOURO', 'street'),
                 ('NU_ENDERECO', 'street_no'), ('NO_BAIRRO', 'district'),
                 ('CO_CEP', 'cep'), ('NU_LATITUDE', 'lat'),
                 ('NU_LONGITUDE', 'lon'), ('mun', 'mun_ibge6')]:
    m[dst] = est[src].reindex(J)

# ---------------------------------------------- type / management, monthly ST
st = pd.read_parquet('data/interim/cnes_st_raw.parquet')
st = st[st.comp.astype(int).isin(COMPS)]
mode = lambda s: s.mode().iat[0] if len(s.mode()) else np.nan
g = st.groupby('CNES')
m['tp_unid'] = g.TP_UNID.agg(mode).reindex(J)
m['tp_gestao'] = g.TPGESTAO.agg(mode).reindex(J)
m['mun_st'] = g.CODUFMUN.agg(mode).reindex(J)
m['centrcir_flag'] = pd.to_numeric(g.CENTRCIR.max(), errors='coerce').reindex(J)
unmatched['cnes_st (monthly)'] = int(m.tp_unid.isna().sum())

# ------------------------------------------------------------- beds, monthly
lt = pd.read_parquet('data/interim/cnes_lt_raw.parquet')
lt = lt[lt.comp.astype(int).isin(COMPS)].copy()
lt['co'] = lt.CODLEITO.astype(str).str.strip().str.zfill(2)
lt['sus'] = pd.to_numeric(lt.QT_SUS, errors='coerce').fillna(0)
surg = lt[lt.co.isin(SURG_BEDS)]
m['beds_surg_sus'] = surg.groupby(['CNES', 'comp']).sus.sum() \
                         .groupby('CNES').mean().reindex(J)
m['beds_total_sus'] = lt.groupby(['CNES', 'comp']).sus.sum() \
                        .groupby('CNES').mean().reindex(J)
for co in ['03', '01', '02', '04', '05']:                # top surgical types
    s = lt[lt.co == co].groupby(['CNES', 'comp']).sus.sum().groupby('CNES').mean()
    m[f'beds_co{co}'] = s.reindex(J)
unmatched['cnes_lt (monthly)'] = int(m.beds_total_sus.isna().sum())

# ------------------------------------------ operating rooms, SNAPSHOT 202606
ifa = z_read('rlEstabInstFisiAssist')
ifa['cnes'] = ifa.CO_UNIDADE.astype(str).str[6:]
ifa = ifa[ifa.CO_UNIDADE.astype(str).str[:2] == '52']
ifa['q'] = pd.to_numeric(ifa.QT_INSTALACAO, errors='coerce').fillna(0)
ifa['co'] = ifa.CO_INSTALACAO.astype(str).str.strip().str.zfill(2)
for co, name in ROOMS.items():
    m[name] = ifa[ifa.co == co].groupby('cnes').q.sum().reindex(J)
unmatched['rlEstabInstFisiAssist (snapshot)'] = int(m.or_main_snap.isna().sum())

# ------------------------------------------------------ equipment, monthly EQ
eq = pd.read_parquet('data/interim/cnes/cnes_eq_GO_raw.parquet')
for c in ('TIPEQUIP', 'CODEQUIP'):
    eq[c] = eq[c].astype(str).str.strip().str.zfill(2)
eq['qe'] = pd.to_numeric(eq.QT_EXIST, errors='coerce').fillna(0)
lap = eq[(eq.TIPEQUIP == '03') & (eq.CODEQUIP == '35')]
m['laparoscope'] = lap.groupby(['CNES', 'cm']).qe.sum().groupby('CNES').mean().reindex(J)
m['laparoscope_sus'] = lap[lap.IND_SUS.astype(str).str.strip() == '1'] \
    .groupby(['CNES', 'cm']).qe.sum().groupby('CNES').mean().reindex(J)

# ------------------------------------------------------ professionals, PF
pf = pd.read_parquet('data/interim/cnes/cnes_pf_GO_raw.parquet',
                     columns=['CNES', 'CBO', 'cm', 'HORAHOSP', 'CPFUNICO'])
pf['CBO'] = pf.CBO.astype(str).str.strip()
pf['hh'] = pd.to_numeric(pf.HORAHOSP, errors='coerce').fillna(0)
# Operating specialties, each its own column. NOT summed into a general-surgeon
# total: cholecystectomy is general-surgery work, so surgeon_225225 must stay
# 225225 alone. Selection is by explicit code, never by label substring, since
# 'CIRURGIAO' also matches 33 dental codes. Every code below is a 2251/2252/2253
# family member that performs operations and appears at >=5 Goias establishments
# in the master universe; non-operating specialties present at higher volume
# (225125 clinico, 225124 pediatra, 225320 radiologia) are deliberately absent.
SPEC_CBO = {
    '225270': 'orthopaedics',   '225250': 'obgyn',        '225265': 'ophthalmology',
    '225203': 'vascular',       '225285': 'urology',      '225260': 'neurosurgery',
    '225275': 'ent',            '225235': 'plastic',      '225310': 'endoscopy',
    '225220': 'digestive',      '225210': 'cardiovascular','225230': 'paediatric',
    '225290': 'cancer',         '225255': 'mastology',    '225280': 'coloproctology',
    '225240': 'thoracic',       '225215': 'headneck',     '225295': 'hand',
}
SPECS = [('surgeon_225225', pf.CBO == '225225'),
         ('anaesth_225151', pf.CBO == '225151'),
         ('nurse_2235_proxy', pf.CBO.str.startswith('2235'))]
SPECS += [(f'spec_{code}_{nm}', pf.CBO == code) for code, nm in SPEC_CBO.items()]
pf['cpf'] = pf.CPFUNICO.astype(str).str.strip()
blank_share = float((pf.cpf == '').mean())
for name, mask in SPECS:
    s = pf[mask]
    # Headcount: distinct CPFUNICO per facility-month, averaged over the window.
    # CPFUNICO is blank on a quarter of PF rows, and nunique() would collapse
    # every blank into one person. Blank rows are counted individually instead,
    # which over-counts if one professional has two blank rows at one facility
    # in one month. Both directions are wrong; this one is the smaller error and
    # the blank share is reported.
    named = s[s.cpf != ''].groupby(['CNES', 'cm']).cpf.nunique()
    anon = s[s.cpf == ''].groupby(['CNES', 'cm']).size()
    m[name] = named.add(anon, fill_value=0).groupby('CNES').mean().reindex(J)
    # FTE: contracted hospital hours per month / 40h week * 4.33
    m[name + '_fte'] = (s.groupby(['CNES', 'cm']).hh.sum()
                        .groupby('CNES').mean() / 173.2).reindex(J)
# Absence from the SOURCE is a different fact from absence of a CBO. All 163 are
# present in PF; a null surgeon count means no general surgeon on record, which
# for an eye or maternity hospital is correct rather than missing -- those carry
# ophthalmologists (225265) and obstetricians (225250) instead. Conflating the
# two would report a join failure that did not happen.
unmatched['cnes_pf (monthly)'] = int((~pd.Index(J).isin(pf.CNES.unique())).sum())
no_cbo = {n: int(m[n].isna().sum()) for n, _ in SPECS[:3]}
print(f'  PF CPFUNICO blank on {100*blank_share:.1f}% of rows -- see headcount note')
print('  present in PF but no record of that CBO: '
      + ', '.join(f'{k} {v}' for k, v in no_cbo.items()))

m = m.reset_index()
m.to_csv('data/ref/hospital_master_2425.csv', index=False)

# ------------------------------------------------------------------- coverage
print(f'\nunmatched on join (reported, not dropped):')
for k, v in unmatched.items():
    print(f'  {k:36s} {v:>4} of {len(J)} establishments absent')
print(f'\ncoverage per column, of {len(J)} establishments:')
print(f'  {"column":24s}{"non-null":>10s}{"non-zero":>10s}{"pct nz":>8s}')
for c in m.columns:
    if c == 'CNES':
        continue
    s = m[c]
    nnull = int(s.notna().sum())
    v = pd.to_numeric(s, errors='coerce')
    # != 0 rather than > 0, because Goias lat/lon are both negative; and
    # notna() first, because NaN != 0 evaluates True and would count missing
    # values as populated.
    nz = int((v.notna() & (v != 0)).sum()) if v.notna().any() else \
        int((s.astype(str).str.strip() != '').sum())
    print(f'  {c:24s}{nnull:>10d}{nz:>10d}{100*nz/len(J):>7.1f}%')
print(f'\n-> data/ref/hospital_master_2425.csv')

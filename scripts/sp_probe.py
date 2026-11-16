"""Gap A -- inventory ONE month of the SIH SP (servicos profissionais) file.

One month only, 2024-06, Goias. Nothing is bulk-downloaded.

    python -m scripts.sp_probe
"""
import ftplib, os, sys, tempfile
import pandas as pd
import datasus_dbc
sys.path.insert(0, 'scripts')
from dbf_read import read_dbf

BASE = '/dissemin/publicos/SIHSUS/200801_/Dados'
FN = 'SPGO2406.dbc'
RAW = 'data/raw/sih_sp'
os.makedirs(RAW, exist_ok=True)
dbc = os.path.join(RAW, FN)

if not os.path.exists(dbc):
    f = ftplib.FTP('ftp.datasus.gov.br', timeout=120); f.login(); f.cwd(BASE)
    with open(dbc, 'wb') as fh:
        f.retrbinary(f'RETR {FN}', fh.write)
    try: f.quit()
    except Exception: pass          # quit() raises on server-side timeout
print(f'{FN}: {os.path.getsize(dbc):,} bytes')

t = tempfile.mktemp(suffix='.dbf')
datasus_dbc.decompress(dbc, t)
d = read_dbf(t)
os.unlink(t)
out = 'data/interim/sih_sp_GO_202406.parquet'
d.to_parquet(out)
print(f'{len(d):,} rows x {len(d.columns)} columns -> {out}\n')

print(f'{"column":14s}{"dtype":10s}{"non-null":>10s}{"non-blank":>11s}{"%":>7s}{"uniq":>9s}  sample')
for c in d.columns:
    s = d[c]
    nn = s.notna()
    blank = s.astype(str).str.strip().isin(['', 'nan'])
    ok = int((nn & ~blank).sum())
    smp = s[nn & ~blank].astype(str).str.strip().unique()[:3]
    print(f'{c:14s}{str(s.dtype):10s}{int(nn.sum()):>10,}{ok:>11,}'
          f'{100*ok/len(d):>6.1f}%{s.nunique():>9,}  {list(smp)}')

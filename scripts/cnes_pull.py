from ftplib import FTP
from datasus_dbc import decompress
from scripts.dbf_read import read_dbf
import pandas as pd, os

MONTHS = [f'{y%100:02d}{m:02d}' for y in range(2019, 2026) for m in range(1, 13)]
BASE = '/dissemin/publicos/CNES/200508_/Dados'
os.makedirs('data/raw/cnes', exist_ok=True)

ST_COLS = ['CNES','CODUFMUN','REGSAUDE','TPGESTAO','TP_UNID','ESFERA_A','NAT_JUR',
           'LEITHOSP','CENTRCIR','CENTROBS','URGEMERG','QTLEITP1','QTLEITP2','QTLEITP3','COMPETEN']
LT_COLS = ['CNES','TP_LEITO','CODLEITO','QT_EXIST','QT_SUS','QT_CONTR','COMPETEN']

def grab(kind, mm, cols):
    fn = f'{kind}GO{mm}.dbc'
    p = f'data/raw/cnes/{fn}'
    d = p.replace('.dbc', '.dbf')
    if not os.path.exists(d):
        f = FTP('ftp.datasus.gov.br', timeout=180); f.login(); f.cwd(f'{BASE}/{kind}')
        remote = f.size(fn)
        if not os.path.exists(p) or os.path.getsize(p) != remote:
            with open(p, 'wb') as fh:
                f.retrbinary(f'RETR {fn}', fh.write)
        f.quit()
        assert os.path.getsize(p) == remote, f'{fn} size mismatch'
        decompress(p, d)
    return read_dbf(d, columns=cols)

for kind, cols in [('ST', ST_COLS), ('LT', LT_COLS)]:
    out = []
    for mm in MONTHS:
        try:
            r = grab(kind, mm, cols)
        except Exception as e:
            print(f'  {kind}{mm} FAILED: {e}')
            continue
        r['comp'] = '20' + mm
        out.append(r)
        print(f'  {kind}{mm} {len(r)}')
    pd.concat(out).to_parquet(f'data/interim/cnes_{kind.lower()}_raw.parquet')
    print(f'{kind}: {sum(len(x) for x in out)} rows -> data/interim/cnes_{kind.lower()}_raw.parquet')

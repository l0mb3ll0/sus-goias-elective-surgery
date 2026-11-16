from ftplib import FTP
from datasus_dbc import decompress
import pandas as pd, os
from scripts.dbf_read import read_dbf

MONTHS = ['1901','2001','2101','2106','2111','2201','2206','2209','2301','2401','2501','2512']
DIR = '/dissemin/publicos/CNES/200508_/Dados/ST'
os.makedirs('data/raw/cnes', exist_ok=True)

def fetch(mm):
    fn, p = f'STGO{mm}.dbc', f'data/raw/cnes/STGO{mm}.dbc'
    f = FTP('ftp.datasus.gov.br', timeout=120); f.login(); f.cwd(DIR)
    remote = f.size(fn)
    if not os.path.exists(p) or os.path.getsize(p) != remote:
        with open(p, 'wb') as fh:
            f.retrbinary(f'RETR {fn}', fh.write)
    f.quit()
    got = os.path.getsize(p)
    assert got == remote, f'{fn}: got {got}, expected {remote}'
    d = p.replace('.dbc', '.dbf')
    if os.path.exists(d) and os.path.getsize(d) < 100000:
        os.remove(d)
    if not os.path.exists(d):
        decompress(p, d)
    with open(d, 'rb') as fh:
        hdr = fh.read(32)
    assert len(hdr) == 32 and hdr[0] in (0x03, 0x83, 0x30), \
        f'{fn}: bad dbf header {hdr[:4].hex()}, size {os.path.getsize(d)}'
    return d

out = []
for mm in MONTHS:
    d = fetch(mm)
    r = read_dbf(d, columns=['CNES','TPGESTAO','REGSAUDE'])
    r['comp'] = '20' + mm
    out.append(r)
    print(mm, len(r), 'rows')

a = pd.concat(out)
a['CNES'] = a.CNES.astype(str).str.zfill(7)
pan = pd.read_parquet('data/interim/hospital_panel.parquet')
key = [c for c in pan.columns if 'CNES' in c.upper()][0]
a = a[a.CNES.isin(set(pan[key].astype(str).str.zfill(7)))]
print()
print(a.pivot_table(index='comp', columns='TPGESTAO', values='CNES', aggfunc='count').fillna(0).astype(int).to_string())
a.to_parquet('data/interim/cnes_tpgestao_probe.parquet')

"""Fetch SIH SP (servicos profissionais) months for Goias, staged by year.

Staged deliberately: 2024 first, report, then 2025.

Resumable. Each month is downloaded to .part, size-checked against the server,
converted, and only then counted as done, so an interrupted or blocked run can be
re-run without re-fetching what already landed. Retries are patient and widely
spaced because DATASUS throttles, and an aggressive retry risks prolonging a
block rather than clearing it.

    python -m scripts.sp_fetch --year 2024
"""
import argparse, ftplib, hashlib, json, os, sys, tempfile, time
from datetime import datetime, timezone
import datasus_dbc
import pandas as pd
sys.path.insert(0, 'scripts')
from dbf_read import read_dbf

BASE = '/dissemin/publicos/SIHSUS/200801_/Dados'
RAW = 'data/raw/sih_sp'
INTERIM = 'data/interim/sih_sp'
ATTEMPTS, WAIT = 40, 900          # up to 10h at 15-minute spacing


def fetch_one(fn, dest):
    tmp = dest + '.part'
    f = ftplib.FTP('ftp.datasus.gov.br', timeout=300)
    f.login(); f.cwd(BASE)
    size = f.size(fn)
    with open(tmp, 'wb') as fh:
        f.retrbinary(f'RETR {fn}', fh.write)
    try: f.quit()
    except Exception: pass
    got = os.path.getsize(tmp)
    if got != size:
        os.remove(tmp)
        raise IOError(f'{fn}: got {got:,} of {size:,} bytes')
    os.replace(tmp, dest)
    return got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--year', required=True)
    ap.add_argument('--uf', default='GO')
    A = ap.parse_args()
    os.makedirs(RAW, exist_ok=True); os.makedirs(INTERIM, exist_ok=True)
    yy = A.year[2:]
    todo = [f'SP{A.uf}{yy}{m:02d}.dbc' for m in range(1, 13)]
    man, frames = [], []
    for fn in todo:
        dest = os.path.join(RAW, fn)
        for k in range(ATTEMPTS):
            if os.path.exists(dest):
                break
            try:
                n = fetch_one(fn, dest)
                print(f'  {fn} ok {n:,} bytes', flush=True)
                break
            except Exception as e:
                print(f'  {fn} attempt {k+1}/{ATTEMPTS}: {type(e).__name__}: {e}',
                      flush=True)
                if k == ATTEMPTS - 1:
                    raise
                time.sleep(WAIT)
        h = hashlib.sha256(open(dest, 'rb').read()).hexdigest()
        t = tempfile.mktemp(suffix='.dbf')
        datasus_dbc.decompress(dest, t)
        d = read_dbf(t); os.unlink(t)
        # Month comes from the filename SP{UF}{YY}{MM}.dbc -> fn[6:8]. Slicing
        # fn[8:10] yields '.d' and collapses every month into one bucket, which
        # the per-month stability table then cannot detect. Cross-check against
        # the file's own SP_AA/SP_MM before trusting either.
        mm = fn[6:8]
        aa_mm = (d.SP_AA.astype(str).str.strip() + '-' +
                 d.SP_MM.astype(str).str.strip().str.zfill(2))
        assert aa_mm.nunique() == 1, f'{fn}: mixed SP_AA/SP_MM {aa_mm.unique()[:5]}'
        assert aa_mm.iat[0] == f'{A.year}-{mm}', \
            f'{fn}: filename says {A.year}-{mm}, data says {aa_mm.iat[0]}'
        d['cm'] = f'{A.year}-{mm}'
        frames.append(d)
        man.append({'file': fn, 'sha256': h, 'rows': len(d),
                    'pulled_at': datetime.now(timezone.utc).isoformat(),
                    'status': 'ok'})
        print(f'  {fn} -> {len(d):,} rows', flush=True)
    out = os.path.join(INTERIM, f'sp_{A.uf}_{A.year}.parquet')
    pd.concat(frames, ignore_index=True).to_parquet(out)
    ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    mp = f'data/manifest_sih_sp_{A.year}_{ts}.json'
    json.dump(man, open(mp, 'w'), indent=1)
    print(f'\n{len(man)}/12 ok -> {out}\nmanifest -> {mp}')


if __name__ == '__main__':
    main()

"""Rebuild data/interim/cnes_lt_raw.parquet and cnes_st_raw.parquet.

These two files feed the bed endowment in scripts/model_solve.py, model_decomp.py,
bootstrap_gap.py and equity_frontier.py, and until now had no generating script
and no manifest -- they were produced by an ad-hoc process and survived only as
committed blobs. Purging the data directories from git history would have left
the paper's capacity parameter unreproducible, so this script exists to close
that gap rather than to add a feature.

Reads data/raw/cnes/{LT,ST}GO{YY}{MM}.dbc if present, and fetches from DATASUS
otherwise. Writes a SHA-256 manifest in the same form as the SIH and CNES
manifests, so a re-fetch can be checked against the files this paper used.

    python -m scripts.build_cnes_interim [--check]

--check rebuilds into a temp location and compares against the committed files
instead of overwriting them.
"""
import argparse, ftplib, hashlib, json, os, sys, tempfile
from datetime import datetime, timezone
import datasus_dbc
import pandas as pd
sys.path.insert(0, 'scripts')
from dbf_read import read_dbf

BASE = '/dissemin/publicos/CNES/200508_/Dados'
RAW, INTERIM = 'data/raw/cnes', 'data/interim'
COLS = {
    'LT': ['CNES', 'TP_LEITO', 'CODLEITO', 'QT_EXIST', 'QT_CONTR', 'QT_SUS',
           'COMPETEN'],
    'ST': ['CNES', 'CODUFMUN', 'REGSAUDE', 'TPGESTAO', 'ESFERA_A', 'TP_UNID',
           'QTLEITP1', 'QTLEITP2', 'QTLEITP3', 'LEITHOSP', 'URGEMERG',
           'CENTRCIR', 'CENTROBS', 'COMPETEN', 'NAT_JUR'],
}
MONTHS = [(y, m) for y in range(2019, 2026) for m in range(1, 13)]


def local_or_fetch(prefix, uf, y, m):
    fn = f'{prefix}{uf}{y % 100:02d}{m:02d}.dbc'
    p = os.path.join(RAW, fn)
    if os.path.exists(p):
        return p, False
    os.makedirs(RAW, exist_ok=True)
    tmp = p + '.part'
    f = ftplib.FTP('ftp.datasus.gov.br', timeout=300)
    f.login(); f.cwd(f'{BASE}/{prefix}')
    with open(tmp, 'wb') as fh:
        f.retrbinary(f'RETR {fn}', fh.write)
    try: f.quit()
    except Exception: pass          # quit() raises on a server-side timeout
    os.replace(tmp, p)
    return p, True


def build(prefix, uf='GO'):
    frames, man = [], []
    for y, m in MONTHS:
        p, fetched = local_or_fetch(prefix, uf, y, m)
        t = tempfile.mktemp(suffix='.dbf')
        datasus_dbc.decompress(p, t)
        d = read_dbf(t)[COLS[prefix]]
        os.unlink(t)
        frames.append(d)
        man.append({'file': os.path.basename(p), 'rows': len(d),
                    'sha256': hashlib.sha256(open(p, 'rb').read()).hexdigest(),
                    'fetched': fetched, 'status': 'ok'})
    out = pd.concat(frames, ignore_index=True)
    # 'comp' is COMPETEN as YYYYMM int-like string, the key every consumer joins on
    out['comp'] = out.COMPETEN.astype(str).str.strip()
    return out, man


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--uf', default='GO')
    A = ap.parse_args()
    ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    for prefix in ('LT', 'ST'):
        df, man = build(prefix, A.uf)
        dst = os.path.join(INTERIM, f'cnes_{prefix.lower()}_raw.parquet')
        if A.check:
            ref = pd.read_parquet(dst)
            same_cols = list(ref.columns) == list(df.columns)
            same_shape = ref.shape == df.shape
            eq = same_cols and same_shape and ref.reset_index(drop=True).equals(
                df.reset_index(drop=True))
            print(f'{prefix}: rebuilt {df.shape} vs committed {ref.shape}  '
                  f'columns {"match" if same_cols else "DIFFER"}  '
                  f'content {"IDENTICAL" if eq else "DIFFERS"}')
        else:
            df.to_parquet(dst)
            mp = f'data/manifest_cnes_{prefix.lower()}_{ts}.json'
            json.dump(man, open(mp, 'w'), indent=1)
            print(f'{prefix}: {df.shape} -> {dst}\nmanifest -> {mp}')

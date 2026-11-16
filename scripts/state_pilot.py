"""Disjointness replication pilot on other states (exploratory; see dist/sprint/WS7_prereg.md for the pre-specified rule).

    python -m scripts.state_pilot BA 2023 [--fetch-only] [--skip-fetch]

Fetches SIH RD (via fetch_sih.py) and CNES LT for the state-year from the public DATASUS FTP, and the IBGE municipality/region table from the IBGE
Localidades API, into data/pilot/<UF>/ (untracked). Then runs the Goias builder (scripts/bootstrap_paired.Year via BOOT_UF/BOOT_ROOT) at point values and reports
bed-bound vs capability-bound overlap with a hypergeometric test. Prints aggregates only. Official sources: DATASUS (SIHSUS, CNES), IBGE.
"""
import sys, os, subprocess, json, gzip, csv, urllib.request, time
UF, YEAR = sys.argv[1].upper(), sys.argv[2]
ROOT = f'data/pilot/{UF}'; UFCODE = {'BA': 29, 'PR': 41, 'MG': 31, 'GO': 52}
os.makedirs(f'{ROOT}/interim/sih', exist_ok=True)
if '--skip-fetch' not in sys.argv:
    yy = YEAR[2:]
    subprocess.run([sys.executable, 'fetch_sih.py', '--ufs', UF, '--start', f'{YEAR}-01', '--end', f'{YEAR}-12', '--outdir', ROOT, '--workers', '3'], check=True)
    if not os.path.exists(f'{ROOT}/ref.csv'):
        req = urllib.request.Request(f'https://servicodados.ibge.gov.br/api/v1/localidades/estados/{UFCODE[UF]}/municipios',
                                     headers={'Accept-Encoding': 'identity', 'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0'})
        for attempt in range(4):
            try:
                raw = urllib.request.urlopen(req, timeout=180).read(); break
            except Exception as e:
                print('IBGE attempt', attempt+1, 'failed:', type(e).__name__); time.sleep(20)
        else:
            raise SystemExit('IBGE API unreachable after 4 attempts (pilot failure, not a result)')
        raw = gzip.decompress(raw) if raw[:2] == b'\x1f\x8b' else raw
        rows = [{'cod6': str(m['id'])[:6], 'cod7': str(m['id']), 'nome': m['nome'], 'reg_imediata': m['regiao-imediata']['nome'],
                 'reg_intermediaria': m['regiao-imediata']['regiao-intermediaria']['nome']} for m in json.loads(raw.decode())]
        with open(f'{ROOT}/ref.csv', 'w', newline='', encoding='utf-8') as fh:
            w = csv.DictWriter(fh, fieldnames=['cod6', 'cod7', 'nome', 'reg_imediata', 'reg_intermediaria']); w.writeheader(); w.writerows(sorted(rows, key=lambda r: r['cod6']))
    if not os.path.exists(f'{ROOT}/interim/cnes_lt_raw.parquet'):
        from ftplib import FTP
        from datasus_dbc import decompress
        sys.path.insert(0, 'scripts'); from dbf_read import read_dbf
        import pandas as pd
        os.makedirs(f'{ROOT}/raw', exist_ok=True); out = []
        for m in range(1, 13):
            mm = f'{yy}{m:02d}'; fn = f'LT{UF}{mm}.dbc'; p = f'{ROOT}/raw/{fn}'; d = p.replace('.dbc', '.dbf')
            f = FTP('ftp.datasus.gov.br', timeout=180); f.login(); f.cwd('/dissemin/publicos/CNES/200508_/Dados/LT')
            with open(p, 'wb') as fh: f.retrbinary(f'RETR {fn}', fh.write)
            try: f.quit()
            except Exception: pass
            decompress(p, d); r = read_dbf(d, columns=['CNES', 'TP_LEITO', 'CODLEITO', 'QT_EXIST', 'QT_SUS', 'QT_CONTR', 'COMPETEN']); r['comp'] = '20' + mm; out.append(r)
        pd.concat(out).to_parquet(f'{ROOT}/interim/cnes_lt_raw.parquet')
if '--fetch-only' in sys.argv: sys.exit(0)

os.environ['BOOT_UF'], os.environ['BOOT_ROOT'], os.environ['BOOT_LAM'] = UF, ROOT, 'jonly'
sys.path.insert(0, 'dist/review')
import numpy as np
from scipy.stats import hypergeom
import pandas as pd, glob
# size gate before building (pre-registered: > 3,000,000 arcs is a failure for size)
ref = pd.read_csv(f'{ROOT}/ref.csv', dtype=str); GO = set(ref.cod6)
a = pd.concat([pd.read_parquet(f, columns=['CNES', 'PROC_REA', 'CAR_INT', 'MUNIC_RES']) for f in sorted(glob.glob(f'{ROOT}/interim/sih/RD{UF}{YEAR[2:]}*.parquet'))])
el = a[(a.PROC_REA.str[:2] == '04') & (a.CAR_INT == '01')].copy(); el['i'] = el.MUNIC_RES.astype(str).str[:6]; el = el[el.i.isin(GO)]; el['p'] = el.PROC_REA.str[:4]
ncell = el.groupby('p').i.nunique(); nfac = el.groupby('p').CNES.nunique()
arcs = int((ncell * nfac).sum())
print(f'{UF} {YEAR}: elective in-state AIH {len(el):,}, facilities {el.CNES.nunique()}, municipalities {el.i.nunique()}, procedure groups {el.p.nunique()}, arcs about {arcs:,}', flush=True)
if arcs > 3_000_000:
    print('SIZE GATE: not run (pre-registered failure for size)'); sys.exit(0)
import _boot_src as S
t0 = time.time(); Y = S.Year(YEAR); one = np.ones(len(Y.key)); r = S.gap_parts(Y, one, one, one)
x = r['x']; kj = r['kj']; fac = np.asarray(Y.Sc[:, :Y.nx] @ x).ravel()
# bed-bound: bed-day use / budget (lambda recomputed as in gap_parts, J-only target)
w = one; wJ = w[Y.sel]; cnt = np.bincount(Y.pairv_J, minlength=Y.npair); sm = np.bincount(Y.pairv_J, weights=Y.dias_J, minlength=Y.npair)
pc = np.bincount(Y.pkv_J, minlength=Y.NP); ps = np.bincount(Y.pkv_J, weights=Y.dias_J, minlength=Y.NP); pm = np.divide(ps, pc, out=np.zeros(Y.NP), where=pc > 0)
lam = (sm + S.K*pm[Y.pair_pk])/(cnt + S.K)
use = np.bincount(Y.rC, weights=lam[Y.colpair]*x, minlength=len(Y.J))
bb = use/np.maximum(Y.B, 1e-9) > 0.95; cb = fac/np.maximum(kj, 1e-12) > 0.95
N, K, n, o = len(Y.J), int(bb.sum()), int(cb.sum()), int((bb & cb).sum())
p = float(hypergeom.cdf(o, N, K, n)); D = r['dem'].sum()
verdict = 'UNINFORMATIVE (bed-bound < 3)' if K < 3 else ('REPLICATES' if p < 0.05 else 'DOES NOT REPLICATE')
print(f'RESULT {UF} {YEAR}: facilities {N} bed-bound {K} cap-bound {n} overlap {o} expected {K*n/N:.2f} p(<=obs) {p:.3f} gap {100*r["gap"]:.1f}% unmet {100*r["unmet"]:.1f}% '
      f'slack {kj.sum()/D:.2f} bed-util {use.sum()/Y.B.sum():.3f} -> {verdict}  ({time.time()-t0:.0f}s)')

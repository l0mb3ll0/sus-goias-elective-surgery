#!/usr/bin/env python3
"""fetch_sih.py — pull SIH/SUS RD files from DATASUS, DBC -> Parquet, with manifest."""

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

BASES = [
    "ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/200801_/Dados",
]

UFS = ["AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA",
       "PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"]

KEEP = [
    "N_AIH", "CAR_INT",
    "PROC_SOLIC", "PROC_REA",
    "CNES", "GESTAO", "COMPLEX", "FINANC", "ESPEC",
    "MUNIC_RES", "MUNIC_MOV",
    "DT_INTER", "DT_SAIDA", "DIAS_PERM",
    "IDADE", "COD_IDADE", "SEXO", "RACA_COR", "INSTRU",
    "DIAG_PRINC", "DIAG_SECUN",
    "VAL_TOT", "VAL_SH", "VAL_SP", "VAL_UTI",
    "MORTE", "INFEHOSP", "UTI_MES_TO",
]


def competencias(start, end):
    sy, sm = (int(x) for x in start.split("-"))
    ey, em = (int(x) for x in end.split("-"))
    y, m = sy, sm
    while (y, m) <= (ey, em):
        yield f"{y % 100:02d}", f"{m:02d}"
        m += 1
        if m > 12:
            m, y = 1, y + 1


def download(url, dest):
    r = subprocess.run(
        ["curl", "-fsSL", "--retry", "3", "--retry-delay", "2",
         "--connect-timeout", "30", "-o", str(dest), url],
        capture_output=True,
    )
    return r.returncode == 0 and dest.exists() and dest.stat().st_size > 0


def dbc_to_df(dbc_path):
    import datasus_dbc
    from dbfread import DBF

    with tempfile.NamedTemporaryFile(suffix=".dbf", delete=False) as tmp:
        dbf_path = Path(tmp.name)
    try:
        datasus_dbc.decompress(str(dbc_path), str(dbf_path))
        table = DBF(str(dbf_path), encoding="latin-1", ignore_missing_memofile=True)
        return pd.DataFrame(iter(table))
    finally:
        dbf_path.unlink(missing_ok=True)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_one(uf, yy, mm, raw, out, keep_cols):
    name = f"RD{uf}{yy}{mm}"
    parquet = out / f"{name}.parquet"
    if parquet.exists():
        return {"file": name, "status": "cached"}

    dbc = raw / f"{name}.dbc"
    if not dbc.exists():
        for base in BASES:
            if download(f"{base}/{name}.dbc", dbc):
                break
        else:
            return {"file": name, "status": "unavailable"}

    try:
        df = dbc_to_df(dbc)
    except Exception as e:
        return {"file": name, "status": f"parse_error: {e}"}

    if keep_cols:
        present = [c for c in KEEP if c in df.columns]
        missing = [c for c in KEEP if c not in df.columns]
        df = df[present]
    else:
        missing = []

    df["UF"] = uf
    df["COMPETENCIA"] = f"20{yy}-{mm}"
    df.to_parquet(parquet, index=False)

    return {
        "file": name,
        "status": "ok",
        "rows": len(df),
        "missing_cols": missing,
        "dbc_sha256": sha256(dbc),
        "pulled_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ufs", default="GO")
    p.add_argument("--start", default="2019-01")
    p.add_argument("--end", default="2025-12")
    p.add_argument("--outdir", default="data")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--all-cols", action="store_true")
    args = p.parse_args()

    ufs = UFS if args.ufs.lower() == "all" else [u.strip().upper() for u in args.ufs.split(",")]

    root = Path(args.outdir)
    raw, out = root / "raw" / "sih", root / "interim" / "sih"
    raw.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)

    jobs = [(uf, yy, mm) for uf in ufs for yy, mm in competencias(args.start, args.end)]
    print(f"{len(jobs)} files to fetch", file=sys.stderr)

    manifest = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {
            ex.submit(fetch_one, uf, yy, mm, raw, out, not args.all_cols): (uf, yy, mm)
            for uf, yy, mm in jobs
        }
        for i, fut in enumerate(as_completed(futures), 1):
            rec = fut.result()
            manifest.append(rec)
            print(f"[{i}/{len(jobs)}] {rec['file']:12s} {rec['status']:12s} {rec.get('rows','')}",
                  file=sys.stderr)

    mpath = root / f"manifest_sih_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
    mpath.write_text(json.dumps(manifest, indent=2))

    ok = [r for r in manifest if r["status"] in ("ok", "cached")]
    total = sum(r.get("rows", 0) for r in manifest if r["status"] == "ok")
    print(f"\n{len(ok)}/{len(jobs)} files, {total:,} new rows", file=sys.stderr)
    print(f"manifest -> {mpath}", file=sys.stderr)

    failed = [r for r in manifest if r["status"] not in ("ok", "cached")]
    if failed:
        print(f"{len(failed)} not retrieved:", file=sys.stderr)
        for r in failed[:20]:
            print(f"  {r['file']}: {r['status']}", file=sys.stderr)


if __name__ == "__main__":
    main()

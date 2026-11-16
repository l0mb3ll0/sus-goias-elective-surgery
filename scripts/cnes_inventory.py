"""Phase 0 inventory of BASE_DE_DADOS_CNES_202606.ZIP.

Streams every member to count data rows and read the header. Extracts nothing.
CNES ships CSV as latin-1, semicolon-separated, with quoted fields.

    python -m scripts.cnes_inventory [--csv data/ref/cnes/inventory_202606.csv]
"""
import csv, io, sys, zipfile

ZIP = 'data/raw/cnes/BASE_DE_DADOS_CNES_202606.ZIP'
OUT = 'data/ref/cnes/inventory_202606.csv'
CHUNK = 1 << 22


def scan(z, name):
    """Return (n_rows, header_cols). Counts newlines rather than parsing."""
    with z.open(name) as fh:
        head = fh.read(CHUNK)
        nl = head.find(b'\n')
        hdr = head[:nl].decode('latin-1').rstrip('\r')
        n = head.count(b'\n')
        while True:
            b = fh.read(CHUNK)
            if not b:
                break
            n += b.count(b'\n')
    cols = [c.strip().strip('"') for c in hdr.split(';')]
    return n - 1, cols          # minus the header line


if __name__ == '__main__':
    out = sys.argv[sys.argv.index('--csv') + 1] if '--csv' in sys.argv else OUT
    z = zipfile.ZipFile(ZIP)
    rows = []
    for name in sorted(z.namelist()):
        n, cols = scan(z, name)
        rows.append((name, n, len(cols), cols))
        print(f'{n:>12,}  {len(cols):>3} col  {name}')
    with io.open(out, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['table', 'rows', 'n_cols', 'columns'])
        for name, n, k, cols in rows:
            w.writerow([name, n, k, '|'.join(cols)])
    print(f'\n{len(rows)} tables -> {out}')

import struct
import pandas as pd

def read_dbf(path, columns=None, encoding='latin-1'):
    with open(path, 'rb') as fh:
        raw = fh.read()
    nrec = struct.unpack('<I', raw[4:8])[0]
    hlen = struct.unpack('<H', raw[8:10])[0]
    rlen = struct.unpack('<H', raw[10:12])[0]

    fields, off = [], 0
    for i in range(32, hlen - 32, 32):
        d = raw[i:i+32]
        if d[0] in (0x0d, 0x00):
            break
        name = d[:11].split(b'\x00')[0].decode('ascii', 'replace').strip()
        size = d[16]
        fields.append((name, off, size))
        off += size
    assert off + 1 == rlen, f'{path}: field widths {off+1} != record length {rlen}'

    want = fields if columns is None else [f for f in fields if f[0] in set(columns)]
    if columns:
        missing = set(columns) - {f[0] for f in want}
        assert not missing, f'{path}: missing fields {sorted(missing)}'

    out = {n: [] for n, _, _ in want}
    for r in range(nrec):
        base = hlen + r * rlen
        rec = raw[base:base+rlen]
        if len(rec) < rlen or rec[0:1] == b'*':
            continue
        for n, o, s in want:
            out[n].append(rec[1+o:1+o+s].decode(encoding, 'replace').strip())
    return pd.DataFrame(out)

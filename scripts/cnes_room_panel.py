"""Gap B -- operating rooms and laparoscopes across four archived CNES vintages.

The base ZIP is published monthly and archived under ftp://ftp.datasus.gov.br/cnes
(115 vintages, 201701..202607). This pulls four spread across 2024-25 and
extracts only two members from each, so the panel answers whether the 202606
snapshot limitation matters.

Members read: rlEstabInstFisiAssist (rooms) and rlEstabEquipamento (laparoscope).
Rooms: CO_INSTALACAO 31 primary; 30/33/37 separately.
Laparoscope: CO_TIPO_EQUIPAMENTO 3 + CO_EQUIPAMENTO 35.

All key fields are stripped and zero-padded before comparison. The EQ monthly
file changed TIPEQUIP from '3' to '03' at 2025-09, so padding drift is assumed
present here until checked rather than assumed absent.

    python -m scripts.cnes_room_panel
"""
import ftplib, io, os, time, zipfile
import pandas as pd

VINTAGES = ['202401', '202407', '202501', '202512']
RAW = 'data/raw/cnes'
ROOMS = {'31': 'or_main', '30': 'or_amb_t1', '33': 'or_amb', '37': 'or_obst'}


def get(v):
    """Download atomically. An interrupted fetch must not leave a file at the
    final path, or the next run treats the truncated bytes as a cached copy and
    fails with BadZipFile. Download to .part, verify, then rename."""
    fn = f'BASE_DE_DADOS_CNES_{v}.ZIP'
    p = os.path.join(RAW, fn)
    if os.path.exists(p) and zipfile.is_zipfile(p):
        return p
    tmp = p + '.part'
    # DATASUS throttles after repeated large transfers; a bare connect can time
    # out mid-run. Retry with backoff rather than losing the vintages already got.
    for attempt in range(12):
        try:
            f = ftplib.FTP('ftp.datasus.gov.br', timeout=300)
            f.login(); f.cwd('/cnes')
            size = f.size(fn)
            with open(tmp, 'wb') as fh:
                f.retrbinary(f'RETR {fn}', fh.write)
            try: f.quit()
            except Exception: pass
            break
        except Exception as e:
            print(f'  {fn} attempt {attempt+1} failed: {e}', flush=True)
            if os.path.exists(tmp):
                os.remove(tmp)
            if attempt == 11:
                raise
            time.sleep(min(600, 60 * (attempt + 1)))
    got = os.path.getsize(tmp)
    assert got == size, f'{fn}: got {got:,} bytes, server said {size:,}'
    assert zipfile.is_zipfile(tmp), f'{fn}: not a zip after download'
    os.replace(tmp, p)
    print(f'  fetched {fn} ({got:,} bytes)')
    return p


def member(z, stem, v):
    """Read one member; the suffix is the vintage, but confirm rather than assume."""
    names = [n for n in z.namelist() if n.lower().startswith(stem.lower())]
    assert len(names) == 1, f'{stem} in {v}: {names}'
    with z.open(names[0]) as fh:
        return pd.read_csv(io.TextIOWrapper(fh, 'latin-1'), sep=';', dtype=str,
                           quotechar='"', low_memory=False)


rows, laps, drift = {}, {}, []
for v in VINTAGES:
    z = zipfile.ZipFile(get(v))
    ifa = member(z, 'rlEstabInstFisiAssist', v)
    ifa = ifa[ifa.CO_UNIDADE.astype(str).str[:2] == '52'].copy()
    ifa['cnes'] = ifa.CO_UNIDADE.astype(str).str[6:]
    raw_codes = sorted(ifa.CO_INSTALACAO.astype(str).str.strip().unique())[:6]
    ifa['co'] = ifa.CO_INSTALACAO.astype(str).str.strip().str.zfill(2)
    ifa['q'] = pd.to_numeric(ifa.QT_INSTALACAO, errors='coerce').fillna(0)
    rows[v] = {n: ifa[ifa.co == c].groupby('cnes').q.sum() for c, n in ROOMS.items()}

    eq = member(z, 'rlEstabEquipamento', v)
    eq = eq[eq.CO_UNIDADE.astype(str).str[:2] == '52'].copy()
    eq['cnes'] = eq.CO_UNIDADE.astype(str).str[6:]
    raw_eq = sorted(eq.CO_TIPO_EQUIPAMENTO.astype(str).str.strip().unique())[:6]
    for c in ('CO_TIPO_EQUIPAMENTO', 'CO_EQUIPAMENTO'):
        eq[c] = eq[c].astype(str).str.strip().str.zfill(2)
    l = eq[(eq.CO_TIPO_EQUIPAMENTO == '03') & (eq.CO_EQUIPAMENTO == '35')]
    laps[v] = l.groupby('cnes').QT_EXISTENTE.apply(
        lambda s: pd.to_numeric(s, errors='coerce').fillna(0).sum())
    drift.append((v, raw_codes, raw_eq))
    print(f'{v}: {len(ifa):,} GO installation rows, {len(eq):,} GO equipment rows')

print('\nraw (unpadded) code samples per vintage -- checking for padding drift:')
for v, ic, ec in drift:
    print(f'  {v}  CO_INSTALACAO {ic}  CO_TIPO_EQUIPAMENTO {ec}')

m = pd.read_csv('data/ref/hospital_master_2425.csv', dtype={'CNES': str})
J = m.CNES.tolist()
out = pd.DataFrame(index=pd.Index(J, name='CNES'))
for v in VINTAGES:
    for n in ROOMS.values():
        out[f'{n}_{v}'] = rows[v][n].reindex(J)
    out[f'lap_{v}'] = laps[v].reindex(J)

print(f'\n=== operating rooms (code 31) across vintages, {len(J)} master facilities ===')
cols = [f'or_main_{v}' for v in VINTAGES]
print(f'  {"vintage":10s}{"facilities>0":>14s}{"total rooms":>13s}{"absent":>8s}')
for v in VINTAGES:
    c = out[f'or_main_{v}']
    print(f'  {v:10s}{int((c > 0).sum()):>14d}{int(c.fillna(0).sum()):>13d}{int(c.isna().sum()):>8d}')
sub = out[cols].fillna(0)
chg = (sub.nunique(axis=1) > 1)
print(f'\n  facilities whose code-31 count CHANGED across the four vintages: '
      f'{int(chg.sum())} of {len(J)} ({100*chg.mean():.1f}%)')
d = (sub[cols[-1]] - sub[cols[0]])
print(f'  net change 2024-01 -> 2025-12: total {int(d.sum()):+d} rooms; '
      f'{int((d > 0).sum())} gained, {int((d < 0).sum())} lost, {int((d == 0).sum())} flat')
print(f'  max absolute change at one facility: {int(d.abs().max())}')

print(f'\n=== laparoscopes across vintages ===')
print(f'  {"vintage":10s}{"facilities>0":>14s}{"total units":>13s}')
for v in VINTAGES:
    c = out[f'lap_{v}']
    print(f'  {v:10s}{int((c > 0).sum()):>14d}{int(c.fillna(0).sum()):>13d}')
lc = out[[f'lap_{v}' for v in VINTAGES]].fillna(0)
print(f'  facilities whose laparoscope count CHANGED: {int((lc.nunique(axis=1) > 1).sum())} of {len(J)}')

out.reset_index().to_csv('data/ref/room_panel_2425.csv', index=False)
print('\n-> data/ref/room_panel_2425.csv')

import json, csv, gzip, urllib.request

URL = 'https://servicodados.ibge.gov.br/api/v1/localidades/estados/52/municipios'
req = urllib.request.Request(URL, headers={
    'Accept-Encoding': 'identity',
    'Accept': 'application/json',
    'User-Agent': 'Mozilla/5.0',
})
with urllib.request.urlopen(req, timeout=60) as r:
    raw = r.read()
if raw[:2] == b'\x1f\x8b':
    raw = gzip.decompress(raw)
muni = json.loads(raw.decode('utf-8'))
print('goias municipalities returned:', len(muni))

rows = [{
    'cod7': str(m['id']),
    'cod6': str(m['id'])[:6],
    'nome': m['nome'],
    'reg_imediata': m['regiao-imediata']['nome'],
    'reg_intermediaria': m['regiao-imediata']['regiao-intermediaria']['nome'],
} for m in muni]

by6 = {r['cod6']: r for r in rows}
assert len(by6) == len(rows), 'cod6 collision'

with open('data/ref/ibge_municipios_go.csv', 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=['cod6','cod7','nome','reg_imediata','reg_intermediaria'])
    w.writeheader(); w.writerows(sorted(rows, key=lambda r: r['cod6']))

want = ['520870','520140','520110','522140','520510','521930','521880','521850']
print()
for c in want:
    r = by6.get(c)
    print(c, r['nome'] if r else 'NOT FOUND', '|', r['reg_imediata'] if r else '')
print('\nmissing:', [c for c in want if c not in by6])
print('wrote data/ref/ibge_municipios_go.csv:', len(rows), 'rows')

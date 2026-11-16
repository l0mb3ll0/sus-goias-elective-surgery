import json, pathlib, re

REFS = json.load(open('paper/refs.json'))
out = ['\\begin{thebibliography}{99}']
# Sort on `label`, which is surname-first. `author` begins with a given-name
# initial, so keying on it orders the bibliography by first initial.
for k in sorted(REFS, key=lambda k: (REFS[k]['label'], REFS[k]['year'])):
    r = REFS[k]
    assert {'author','year','label','title','venue'} <= set(r), k
    out.append(f"\\bibitem[{r['label']}({r['year']})]{{{k}}}")
    out.append(r['author'] + '.')
    out.append('\\newblock ' + r['title'] + '.')
    out.append('\\newblock \\emph{' + r['venue'] + '}' +
               (', ' + r['detail'] if r.get('detail') else '') + f", {r['year']}.")
out.append('\\end{thebibliography}')
bib = '\n'.join(out) + '\n'

p = pathlib.Path('paper/main.tex'); s = p.read_text()
m = re.search(r'\\begin\{thebibliography\}.*?\\end\{thebibliography\}\n', s, re.S)
assert m, 'no thebibliography block'
p.write_text(s[:m.start()] + bib + s[m.end():])

unver = [k for k, r in REFS.items() if not r.get('verified')]
print(f'{len(REFS)} entries written; unverified: {sorted(unver)}')

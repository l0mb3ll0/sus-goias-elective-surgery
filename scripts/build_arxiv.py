"""Assemble a self-contained arXiv submission tarball.

arXiv compiles what it is given, with no shell access and no bibtex run unless
a .bbl is supplied. The bibliography here is already an inlined thebibliography
block written by scripts.build_bib, so no .bbl or .bib is needed.

Verifies before packing:
  every \\input target and every \\includegraphics target is present
  the packed tree compiles standalone, twice, with zero undefined references
  the resulting page count matches the working copy

    python -m scripts.build_arxiv
"""
import io, os, re, shutil, subprocess, sys, tarfile

SRC = 'paper'
OUT = 'dist/arxiv'
TAR = 'dist/sus-goias-arxiv-v1.1.tar.gz'

def resolve(fn, seen):
    """Recursively collect \\input targets. tab2_falsification.tex is included
    from inside sections_2_3.tex, not from main.tex, so a one-level scan misses it."""
    body = io.open(f'{SRC}/{fn}', encoding='utf-8').read()
    out = [body]
    for t in re.findall(r'\\input\{([^}]+)\}', body):
        if t in seen:
            continue
        seen.append(t)
        out += resolve(t, seen)
    return out

main = io.open(f'{SRC}/main.tex', encoding='utf-8').read()
inputs = []
bodies = resolve('main.tex', inputs)
figs = sorted({g for b in bodies for g in re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', b)})

assert '\\begin{thebibliography}' in main, 'bibliography is not inlined in main.tex'
assert '\\bibliography{' not in main, 'main.tex still calls \\bibliography'
nbib = main.count('\\bibitem')

os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT):
    os.remove(os.path.join(OUT, f))

files = ['main.tex'] + inputs + figs
for f in files:
    src = f'{SRC}/{f}'
    assert os.path.exists(src), f'missing {src}'
    shutil.copy2(src, os.path.join(OUT, os.path.basename(f)))
print(f'packed {len(files)} files: main.tex, {len(inputs)} inputs, {len(figs)} figures, '
      f'{nbib} inlined bibitems')

for i in range(2):
    r = subprocess.run(['pdflatex', '-interaction=nonstopmode', 'main.tex'],
                       cwd=OUT, capture_output=True, text=True)
log = io.open(f'{OUT}/main.log', encoding='utf-8', errors='replace').read()
undef = len([l for l in log.split('\n') if 'undefined' in l.lower()])
pages = re.search(r'Output written on main\.pdf \((\d+) pages', log)
print(f'standalone compile: {pages.group(1) if pages else "?"} pages, {undef} undefined references')
assert undef == 0, 'standalone tree has undefined references'

ref_log = io.open(f'{SRC}/main.log', encoding='utf-8', errors='replace').read()
ref_pages = re.search(r'Output written on paper/main\.pdf \((\d+) pages', ref_log)
if ref_pages and pages:
    assert ref_pages.group(1) == pages.group(1), \
        f'page count differs: working {ref_pages.group(1)}, packed {pages.group(1)}'
    print(f'page count matches working copy ({pages.group(1)})')

os.makedirs('dist', exist_ok=True)
with tarfile.open(TAR, 'w:gz') as t:
    for f in files:
        t.add(os.path.join(OUT, os.path.basename(f)), arcname=os.path.basename(f))
print(f'written {TAR} ({os.path.getsize(TAR)/1024:.0f} KB)')
with tarfile.open(TAR) as t:
    print('contents:', ', '.join(sorted(t.getnames())))

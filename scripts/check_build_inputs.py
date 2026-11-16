"""Every file the LaTeX build reads must be tracked by git.

An untracked figure once left a tag that could not rebuild its own submission
tarball: the build only succeeded because the file happened to be on disk. This
resolves \\input, \\include, \\includegraphics, \\bibliography and \\lstinputlisting
recursively from main.tex, then asserts each resolved file is tracked.

Exit non-zero if any build input is untracked or ignored.

    python -m scripts.check_build_inputs
"""
import io, os, re, subprocess, sys

SRC = 'paper'
ROOT = 'main.tex'
# graphicx tries these when the \includegraphics argument has no suffix
GRAPHICS_EXT = ['', '.pdf', '.png', '.jpg', '.jpeg', '.eps']
TEX_EXT = ['', '.tex']
PAT = {
    'input':          (r'\\input\{([^}]+)\}', TEX_EXT),
    'include':        (r'\\include\{([^}]+)\}', TEX_EXT),
    'includegraphics':(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', GRAPHICS_EXT),
    'bibliography':   (r'\\bibliography\{([^}]+)\}', ['', '.bib']),
    'lstinputlisting':(r'\\lstinputlisting(?:\[[^\]]*\])?\{([^}]+)\}', ['']),
}


def resolve(name, exts):
    for e in exts:
        p = os.path.join(SRC, name + e)
        if os.path.isfile(p):
            return p
    return None


seen, inputs, missing = set(), [], []


def scan(relpath):
    if relpath in seen:
        return
    seen.add(relpath)
    body = io.open(relpath, encoding='utf-8').read()
    body = re.sub(r'(?<!\\)%.*', '', body)          # strip comments
    for kind, (rx, exts) in PAT.items():
        for m in re.findall(rx, body):
            for target in (t.strip() for t in m.split(',')):
                if not target:
                    continue
                p = resolve(target, exts)
                if p is None:
                    missing.append((relpath, kind, target))
                    continue
                inputs.append((kind, p))
                if p.endswith('.tex'):
                    scan(p)


scan(os.path.join(SRC, ROOT))
inputs = sorted(set(inputs))
tracked = set(subprocess.run(['git', 'ls-files'], capture_output=True, text=True,
                             check=True).stdout.split('\n'))

print(f'{os.path.join(SRC, ROOT)} pulls in {len(inputs)} build inputs\n')
bad = []
for kind, p in inputs:
    ok = p in tracked
    ign = subprocess.run(['git', 'check-ignore', '-q', p]).returncode == 0
    flag = 'tracked' if ok else ('IGNORED' if ign else 'UNTRACKED')
    if not ok:
        bad.append((p, flag))
    print(f'  {kind:16s} {p:44s} {flag}')

if missing:
    print('\nunresolved references:')
    for f, kind, t in missing:
        print(f'  {f}: \\{kind}{{{t}}} resolves to no file on disk')

print()
if bad or missing:
    for p, flag in bad:
        print(f'FAIL: {p} is {flag} but the build reads it')
    if missing:
        print(f'FAIL: {len(missing)} unresolved reference(s)')
    sys.exit(1)
print(f'PASS: all {len(inputs)} build inputs are tracked')

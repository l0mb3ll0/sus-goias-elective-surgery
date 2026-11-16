import pathlib

P = pathlib.Path('paper/sections_2_3.tex')
s = P.read_text()

OLD = """[TODO: merge monthly CNES establishment, bed and
professional files to compute cases per surgeon-month and cases per surgical
bed-month across the break. This is the measurement that distinguishes
activation of latent capacity from capacity expansion, and it is also the
capacity parameterisation required by the model in Section~[ref].]"""

NEW = """Cases per surgical bed-month across the break are reported in the following
subsection, and show that the additional volume was accommodated within existing
bed capacity. [TODO: the corresponding measurement on staffing, cases per
surgeon-month from the CNES professional files, is not yet done and would
distinguish activation of latent capacity from silent capacity expansion.]"""

assert s.count(OLD) == 1
P.write_text(s.replace(OLD, NEW))

t = pathlib.Path('paper/tab1_decomposition.tex')
if t.exists():
    t.rename('paper/tab1_decomposition.tex.dead')
    print('tab1 renamed to .dead')
else:
    print('tab1 not found at paper/')
print('ok', len(P.read_text()), 'chars')
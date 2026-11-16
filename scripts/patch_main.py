import pathlib

P = pathlib.Path('paper/main.tex')
s = P.read_text()

OLD = "% Section 1 (introduction) to be written last.\n\\input{sections_2_3.tex}"
NEW = "\\input{section_1_intro.tex}\n\\input{sections_2_3.tex}"
assert s.count(OLD) == 1, 'anchor not found'
s = s.replace(OLD, NEW)

P.write_text(s)
print('ok')

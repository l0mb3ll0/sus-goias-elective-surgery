import pathlib, re

S = pathlib.Path('paper/sections_2_3.tex')
s = S.read_text()
n = s.count('Section~[ref]')
s = s.replace('Section~[ref]', 'Section~\\ref{sec:model}')

OLD = 'Two limitations should be stated plainly.'
assert s.count(OLD) == 1
s = s.replace(OLD, '\\label{sec:limits}\nTwo limitations should be stated plainly.')
S.write_text(s)

M = pathlib.Path('paper/section_4_model.tex')
m = M.read_text()
print('model refs:', re.findall(r'\\ref\{([^}]*)\}', m))
print('model labels:', re.findall(r'\\label\{([^}]*)\}', m))
print('replaced', n, 'Section~[ref] |', len(s), 'chars')
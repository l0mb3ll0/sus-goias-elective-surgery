import pathlib

P = pathlib.Path('paper/figures.py')
s = P.read_text()
L = s.split('\n')

assert L[249].startswith('# ---') and L[285].startswith('"""'), (L[249], L[285])
assert 'tab1_decomposition' in '\n'.join(L[249:286])
assert L[302].strip() == 'sm = pan[pan["grp"] == "early"]', L[302]
print('line 10 was:', L[10])

NEW = '''# ----------------------------------------------------------------------
# Group assignment from panel v2 (TP_GESTAO status as of 2022-08).
# The old treat-date decomposition (never/early/late) is removed: panel
# treat dates are systematically late by 1-43 months and the resulting
# +143.9/+39.6 pair is retired. See sections_2_3.tex, "Provider
# composition and the bed-day constraint".
# ----------------------------------------------------------------------
_v2 = pd.read_parquet("data/interim/hospital_panel_v2.parquet")
_g = _v2.groupby("CNES")["group"].first()
pan["grp"] = pan["CNES"].map(_g)
N.pop("table1", None)'''

L[249:286] = NEW.split('\n')
L[10] = L[10].replace('tab1_decomposition.tex', '(tab1 removed)')
s2 = '\n'.join(L)
assert 'tab1_decomposition.tex", "w"' not in s2
assert 'always_state' not in s2
s2 = s2.replace('sm = pan[pan["grp"] == "early"]',
                'sm = pan[pan["grp"].isin(["always_state", "transferred"])]')
P.write_text(s2)
print('ok', len(s2), 'chars')
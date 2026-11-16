"""Rows for the sensitivity table, limitations on sources, conclusion, appendix restructure."""
import json, re
def edit(path, pairs):
    s = open(path, encoding='utf-8').read()
    for old, new in pairs:
        assert s.count(old) == 1, (path, s.count(old), old[:90]); s = s.replace(old, new)
    open(path, 'w', encoding='utf-8').write(s)
r = json.load(open('dist/review/audit_final12.json')); g = lambda y, k: f"{100*r[f'{y}|{k}']['gap']:.1f}"
S4 = 'paper/section_4_model.tex'; S23 = 'paper/sections_2_3.tex'; MAIN = 'paper/main.tex'
edit(S4, [("Baseline over all in-state records & 28.8 & 31.3 & 29.0 \\\\\n",
 "Baseline over all in-state records & 28.8 & 31.3 & 29.0 \\\\\n"
 f"Residents of the 29 RIDE-DF Entorno municipalities excluded & {g('2019','excl_entorno')} & {g('2023','excl_entorno')} & {g('2025','excl_entorno')} \\\\\n"
 f"Official health regions (SES-GO, 18) replace IBGE regions in the cost & {g('2019','health_cost_muni_zone')} & {g('2023','health_cost_muni_zone')} & {g('2025','health_cost_muni_zone')} \\\\\n"
 f"Origin zone = health region (cost 0/1/2) & {g('2019','health_zone')} & {g('2023','health_zone')} & {g('2025','health_zone')} \\\\\n"
 f"Origin zone = health macro-region (cost 0/1) & {g('2019','health_macro_zone')} & {g('2023','health_macro_zone')} & {g('2025','health_macro_zone')} \\\\\n")])
edit(S23, [("Six limitations should be stated plainly.", "Six limitations should be stated plainly, and two sources deserve a note. The health-region mapping used in one robustness row is the list of municipalities per region published on the SES-GO page ``Regi\\~oes de Sa\\'ude'' (18 regions, 246 municipalities, grouped into five macro-regions); it was read from that web page and not from the CIB resolution that established it, and the page lists 25 municipalities for one region but names 24 in one place, which we resolved by name matching to IBGE. The Entorno exclusion uses the 29 Goi\\'as municipalities listed for the RIDE-DF in Lei Complementar n.\\ 94/1998 as amended by Lei Complementar n.\\ 163/2018 (index page of the C\\^amara dos Deputados, which tags Planaltina as DF in its index; we read it as Planaltina de Goi\\'as).")])
CONC = r"""

\section*{Conclusion}
Elective surgery in Goi\'as roughly doubled between 2019 and 2025, and most of the facility-procedure pairs behind the 2019 to 2023 gain had operated before. Beds were slack in aggregate and limiting at a few
facilities. A transparent assignment benchmark shows no detectable change in allocation, but its level depends on how the cap, the cost, the zones and the bed budget are built, and the tests we ran on the cap are low-power or
not identified. The paper therefore claims a description and a benchmark with stated limits, not a cause or a policy lever. The most useful next steps are data that
the SIH files lack: the hospital contract targets, Goi\'as residents treated in the Federal District, and waiting times.
"""
s = open(MAIN, encoding='utf-8').read(); assert s.count("\n\\section*{Declarations}") == 1
s = s.replace("\n\\section*{Declarations}", CONC + "\n\\section*{Declarations}"); open(MAIN, 'w', encoding='utf-8').write(s)
# ---------- appendix restructure ----------
def cut(path, title):
    s = open(path, encoding='utf-8').read(); a = s.index("\\subsection{" + title + "}")
    m = re.search(r"\n\\subsection\{|\n\\section\{", s[a+10:]); b = a + 10 + m.start() + 1 if m else len(s)
    blk = s[a:b]; open(path, 'w', encoding='utf-8').write(s[:a] + s[b:]); return blk
A = [cut(S4, "Was capability placed where the model priced it?"), cut(S4, "What a budget of new capability would buy"), cut(S4, "Validation and extension")]
C = [cut(S23, "The 2022 change occurred in two waves"), cut(S23, "The July 2022 step came from existing facilities"), cut(S23, "Growth was highly unequal across facilities"), cut(S23, "Falsification and robustness")]
APP = "\\appendix\n\\section{Exploratory extension: opening new facility-procedure pairs}\n\\label{app:explore}\n\nThis appendix is exploratory. It rests on an assumed capability for new pairs, was not validated by choosing pairs on one year and evaluating them on a later one, and uses demand that omits Goi\\'as residents treated in the Federal District. It supports no recommendation.\n\n" + "\n".join(A) + "\n\\section{Timing of the 2022 change and growth across facilities (descriptive)}\n\\label{app:timing}\n\nThese subsections describe when and where elective volume grew in 2022. They do not identify the cause of the growth.\n\n" + "\n".join(C)
open('paper/appendix.tex', 'w', encoding='utf-8').write(APP)
s = open(MAIN, encoding='utf-8').read(); s = s.replace("\n\\section*{Declarations}", "\n\\section*{Declarations}", 1)
# insert appendix input before the bibliography
assert s.count("\\bibliographystyle{plainnat}") == 1
s = s.replace("\\bibliographystyle{plainnat}", "\\input{appendix.tex}\n\n\\bibliographystyle{plainnat}"); open(MAIN, 'w', encoding='utf-8').write(s)
print('appendix ok', [len(x) for x in A + C])

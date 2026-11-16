"""Final batch text edits (items 1, 2, 9, 10, 11, 12) except the capnull rewrite and bootstrap numbers, which follow the reruns."""
import json
def edit(path, pairs):
    s = open(path, encoding='utf-8').read()
    for old, new in pairs:
        assert s.count(old) == 1, (path, s.count(old), old[:90]); s = s.replace(old, new)
    open(path, 'w', encoding='utf-8').write(s)
rf = json.load(open('dist/review/record_flow.json')); f = lambda y, k: f"{rf[y][k]:,}".replace(',', '{,}')
FLOW = r"""
\begin{table}[t]
\centering
\caption{Flow of hospital authorisations (AIH) into the analysis sample, SIH/SUS RD files processed in Goi\'as (RECORD-style).}
\label{tab:recordflow}
\begin{tabular}{lrrr}
\toprule
 & 2019 & 2023 & 2025 \\
\midrule
All AIH processed in Goi\'as & %s & %s & %s \\
Surgical procedures (group 04) & %s & %s & %s \\
Elective (CAR\_INT 01) & %s & %s & %s \\
Resident in a Goi\'as municipality (IBGE list) & %s & %s & %s \\
At the model's facilities (net bed budget $> 0$) & %s & %s & %s \\
Facilities in the model & %d & %d & %d \\
\bottomrule
\end{tabular}
\end{table}
""" % tuple([f(y, k) for k in ('all_aih', 'surgical_group04', 'elective', 'elective_in_state', 'at_model_facilities') for y in ('2019', '2023', '2025')] + [rf[y]['facilities_in_J'] for y in ('2019', '2023', '2025')])
edit('paper/section_1_intro.tex', [
("Adding the pairs absent in 2019, with the caps they carry in 2023, moves the\nadjusted cost from 1.375 to 0.587; that step is 64 per cent of the improvement in the paper's order of steps and 22 per cent on a\nShapley split, because new pairs are worth nothing without their caps. Of the 284",
 "With the 2019 pairs 11.5 per cent of the 2023 demand is unserved; with the 2023 pairs all of it is served. We make no attribution of the change between\npairs and capacity (served-only travel and unmet share are reported separately in Table~\\ref{tab:decomp}). Of the 284"),
("(the gap is observed minus optimal, over observed),","(the gap is (observed $-$ optimum) / observed; 29 per cent less corresponds to about 41 per cent above the optimum on the index),"),
("First, physical bed capacity was never the binding constraint.","First, beds were slack in aggregate and bound at only a few facilities."),
])
print('batch 7 ok')

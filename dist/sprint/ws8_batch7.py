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
edit('paper/sections_2_3.tex', [("\\subsection{Two measurement concerns}", FLOW + "\n\\subsection{Two measurement concerns}")])
edit('paper/section_4_model.tex', [
("from the CNES bed file multiplied by days in the period, net of the bed-days","from the CNES bed file multiplied by 30 days per month (calendar days per month, 30.4 on average, move the 2023 gap by +0.5 points), net of the bed-days"),
("The comparison that isolates the option set is C against D. The two differ only\nin which facility-procedure pairs are permitted: 554 against 637, on identical\ndemand and identical capacity. The adjusted cost moves from 1.375 to 0.587, and\nunmet demand from 11.5 per cent to zero. Restricted to the pairs that existed in\n2019, the 2023 caseload cannot be routed as well as it was actually routed, and\npart of it cannot be served at all. Adding the pairs absent in 2019, with the caps they carry in 2023, moves the adjusted cost from 1.375 to 0.587; that step is 64 per cent of the improvement from the 2019 to the 2023 configuration in the paper's order of steps and 22 per cent on a Shapley split, because new pairs are worth nothing without their caps (Section~\\ref{sec:capnull}).",
 "Configurations C and D differ only in which facility-procedure pairs are permitted: 554 against 637, on identical\ndemand and identical capacity. With the 2019 pairs 11.5 per cent of the 2023 demand is unserved and travel over the cases served is 0.775; with the 2023 pairs\nall demand is served at 0.587. We do not attribute the change between options and capacity. The pairs absent in 2019 and the caps they carry arrive together,\nand any split depends on the order of steps and on the penalty $\\pi$ that prices unmet demand; the table reports served-only travel and the unmet share separately for that reason."),
("& Configuration & Options & Adjusted cost & Unmet \\\\","& Configuration & Options & Served-only travel & Adjusted cost & Unmet \\\\"),
("& 563 & 0.595 & 0.0\\% \\\\\nB &","& 563 & 0.595 & 0.595 & 0.0\\% \\\\\nB &"),
("2019 capacity & 563 & 1.823 & 20.8\\% \\\\","2019 capacity & 563 & 0.725 & 1.823 & 20.8\\% \\\\"),
("2023 capacity & 554 & 1.375 & 11.5\\% \\\\","2023 capacity & 554 & 0.775 & 1.375 & 11.5\\% \\\\"),
("2023 capacity & 637 & 0.587 & 0.0\\% \\\\","2023 capacity & 637 & 0.587 & 0.587 & 0.0\\% \\\\"),
("\\begin{tabular}{llrrr}\n\\toprule\n& Configuration","\\begin{tabular}{llrrrr}\n\\toprule\n& Configuration"),
("This follows the\nregionalisation on which SUS referral policy is actually written","This uses IBGE immediate and intermediate geographic regions, which resemble but are not the CIB health regions (regi\\~oes de sa\\'ude) on which SUS referral agreements are written"),
])
edit('paper/section_1_intro.tex', [
("Adding the pairs absent in 2019, with the caps they carry in 2023, moves the\nadjusted cost from 1.375 to 0.587; that step is 64 per cent of the improvement in the paper's order of steps and 22 per cent on a\nShapley split, because new pairs are worth nothing without the caps they bring. Of the 284",
 "With the 2019 pairs 11.5 per cent of the 2023 demand is unserved; with the 2023 pairs all of it is served. We make no attribution of the change between\npairs and capacity (served-only travel and unmet share are reported separately in Table~\\ref{tab:decomp}). Of the 284"),
("(the gap is observed minus optimal, over observed),","(the gap is (observed $-$ optimum) / observed; 29 per cent less corresponds to about 41 per cent above the optimum on the index),"),
("First, physical bed capacity was never the binding constraint.","First, beds were slack in aggregate and bound at only a few facilities."),
("The system was not full at any date.","The system was not full at any date."),
])
print('batch 7 ok')

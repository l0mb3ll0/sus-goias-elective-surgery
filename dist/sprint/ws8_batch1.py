"""Paper edits batch 1 (branch sprint/nov-2026): kappa rename, 'tightens' removal, finding 4 softened (DECISIONS item 4), '77 at cap' sites rewritten to the bounded range.
Each replacement must match exactly once. Run from repo root."""
import re, sys
def edit(path, pairs):
    s = open(path, encoding='utf-8').read()
    for old, new in pairs:
        assert s.count(old) == 1, (path, s.count(old), old[:70])
        s = s.replace(old, new)
    open(path, 'w', encoding='utf-8').write(s)

edit('paper/section_1_intro.tex', [
("Fourth, and this is the mechanism behind the third, the expansion ran entirely\nthrough the extensive margin. We decompose",
 "Fourth, and this is the mechanism behind the third, the change in what the system\ncould achieve came through the set of facility-procedure pairs, and mostly by\nreactivation rather than creation. We decompose"),
("their capability cap, while the 77 at their capability cap hold 26{,}269 unused\nsurgical bed-days per month between them against 10{,}902 consumed by all 131.\nThe separation is exact in 2019 and 2023 and holds for 144 of 145 facilities in\n2025.",
 "their peak-volume cap. At the reported optimum 77 facilities are at their cap and hold\n26{,}269 unused surgical bed-days per month between them, against 10{,}902 consumed by\nall 131; that count is one point on a set of equally good optima, across which it\nranges from 44 to 107 (Section~\\ref{sec:capnull}). No facility is at both limits at the\nreported optimum in 2019 and 2023, and one of 145 is in 2025."),
("that the capability constraint\ntightens across a period of rapid expansion while physical capacity does not\napproach its limit,",
 "that the ratio of aggregate peak-volume cap to demand falls across a period of rapid\nexpansion while physical capacity does not approach its limit,"),
])
edit('paper/main.tex', [
("those three operate at 0.58 of their capability cap; the 77\nfacilities at their capability cap hold 26{,}269 unused surgical bed-days per\nmonth between them, against 10{,}902 bed-days consumed per month by all 131\nfacilities in the solution. The separation is exact in 2019 and 2023 and holds\nfor 144 of 145 facilities in 2025.",
 "those three operate at 0.58 of their peak-volume cap. At the reported optimum 77\nfacilities are at their cap and hold 26{,}269 unused surgical bed-days per month\nbetween them, against 10{,}902 bed-days consumed per month by all 131 facilities\nin the solution; that count is not unique and ranges from 44 to 107 across optima\nof equal cost. No facility is at both limits at the reported optimum in 2019 and\n2023, and one of 145 is in 2025."),
("holds across the expansion and tightens: aggregate capability exceeds demand by\na factor of 1.37 in 2019, 1.32 in 2023 and 1.16 in 2025,",
 "holds across the expansion: the aggregate peak-volume cap exceeds demand by\na factor of 1.37 in 2019, 1.32 in 2023 and 1.16 in 2025,"),
])
edit('paper/section_4_model.tex', [
("The capability constraint tightens across the panel while physical capacity\nnever approaches its limit.",
 "The ratio of aggregate peak-volume cap to demand falls across the panel while physical\ncapacity never approaches its limit."),
("so the capability constraint\ntightens across the panel rather than loosening: by 2025 the state holds 16 per\ncent more capability than demand against 37 per cent in 2019.",
 "so the ratio of aggregate peak-volume cap to demand falls rather than rises: by 2025\nthe cap exceeds demand by 16 per cent against 37 per cent in 2019. Section~\\ref{sec:capnull}\nasks what the fall consists of."),
("direction the tightening series predicts, and by 2025 aggregate capability\nexceeds demand by only 16 per cent. Both constraints tighten\nover the panel and neither overtakes the other:",
 "direction of the falling cap-to-demand series, and by 2025 the aggregate cap\nexceeds demand by only 16 per cent. Both ratios move toward each other\nover the panel and neither overtakes the other:"),
("the ratio of aggregate capability\nto demand falls monotonically",
 "the ratio of aggregate peak-volume cap\nto demand falls monotonically"),
("0.58 of their capability cap; the 77 facilities at their capability cap have mean\nfacility utilisation 0.116 and hold 26{,}269 unused surgical bed-days per month\nbetween them,",
 "0.58 of their peak-volume cap. At the reported optimum 77 facilities are at their cap, with mean\nfacility utilisation 0.116, and hold 26{,}269 unused surgical bed-days per month\nbetween them,"),
("\\paragraph{The capability cap.} $\\kappa_{jp}$ and $\\kappa_{j}$ are facility $j$'s\ndemonstrated monthly throughput, for procedure $p$ and in total. The natural\nconstruction is the largest monthly caseload observed in the estimation year.",
 "\\paragraph{The peak-volume cap.} $\\kappa_{jp}$ and $\\kappa_{j}$ are facility $j$'s\npeak 3-month average volume in the estimation year, for procedure $p$ and in total. This is\na historical high-water mark, a lower bound on what the unit has delivered and not a measured\nceiling on what it can deliver (Section~\\ref{sec:capnull}); we call it a cap because the program\nimposes it as one. The natural construction is the largest monthly caseload observed in the estimation year."),
])
# generic renames after the specific edits
for path in ('paper/main.tex', 'paper/section_1_intro.tex', 'paper/sections_2_3.tex', 'paper/section_4_model.tex'):
    s = open(path, encoding='utf-8').read()
    s = re.sub(r'capability(\s+)caps\b', r'peak-volume\1caps', s)
    s = re.sub(r'capability(\s+)cap\b', r'peak-volume\1cap', s)
    s = re.sub(r'capability(\s+)constraint', r'peak-volume\1constraint', s)
    s = re.sub(r'demonstrated(\s+)capability', r'demonstrated\1peak volume', s)
    s = re.sub(r'aggregate(\s+)capability', r'aggregate\1peak-volume cap', s)
    s = re.sub(r'Aggregate(\s+)capability', r'Aggregate\1peak-volume cap', s)
    open(path, 'w', encoding='utf-8').write(s)
print('ok')

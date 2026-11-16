"""Paper batch 5: citation fixes, excess-commuting lineage, CIB 111/2021 paragraph, contribution wording, abstract and introduction rewritten around what survives."""
import re
def edit(path, pairs):
    s = open(path, encoding='utf-8').read()
    for old, new in pairs:
        assert s.count(old) == 1, (path, s.count(old), old[:80]); s = s.replace(old, new)
    open(path, 'w', encoding='utf-8').write(s)
def sub_between(path, start, end, new, include_end=False):
    s = open(path, encoding='utf-8').read(); a = s.index(start); b = s.index(end, a) + (len(end) if include_end else 0)
    open(path, 'w', encoding='utf-8').write(s[:a] + new + s[b:])

edit('paper/section_1_intro.tex', [
("\\citet{burdett2023} develop\nthe closest antecedent to the program below: a suite of models that assigns\npatient types across fifteen hospitals in a region, one maximising attainable\ncaseload and one minimising the travel time of spatially located patients, with\nresource consumption profiles that include length of stay. Our formulation is of\nthe same family.",
 "\\citet{burdett2023} develop\na regional case-mix planning framework of three models: one finds the largest cohort a region can treat,\nand a second assigns demand from sub-regions to hospitals, covering as much demand as possible while minimising\ntotal travel distance. Their case study is the Brisbane and Gold Coast regions (nineteen hospitals listed, four omitted for\nlack of information) with synthetic patient locations, and resource consumption profiles use average length of stay\nand treatment time. Our formulation is of the same family."),
("\\citet{helm2014} plan elective\nadmissions against downstream bed capacity and treat observed flows as\ncongestion-contaminated, a concern we meet differently by bounding facilities at\ntheir own demonstrated throughput; \\citet{meng2015} manage elective admission in\na public hospital under demand uncertainty, and \\citet{marques2014} schedule\nelective surgery in a public system with capacity constraints.",
 "\\citet{helm2014} plan elective\nadmissions against downstream bed capacity and treat observed hospital data as\n``congestion-contaminated'', a concern we meet differently by bounding facilities at\ntheir own peak volume; \\citet{meng2015} manage elective admission in\na public hospital under demand uncertainty, and \\citet{marques2014} schedule\nelective surgery at a single Portuguese public hospital."),
("\\citet{finlayson1999} document patient\npreference for local care, and \\citet{scharfe2025} find in systematic review that\nthe introduction of minimum volume standards raises travel distance while leaving\ncomplications and reoperations unaffected.",
 "\\citet{finlayson1999} elicit, in a hypothetical pancreatic-cancer scenario put to 100 patients at one Veterans Affairs\nmedical centre, how much added operative risk patients would accept to stay local, and \\citet{scharfe2025} report in a\nsystematic review of nine studies, with low-certainty evidence, that minimum volume standards raise travel distance and\ndo not affect complications or reoperations (very low certainty for mortality)."),
("its optimisation treatment, bounding each hospital's post-reallocation caseload\nat a multiple of its base-year volume; that constraint is the one we adopt.",
 "its optimisation treatment, bounding each hospital's post-reallocation caseload\nat a multiple of its base-year volume, $N'_h \\leq (1+v_{\\max})N_h$; that constraint is the one we adopt. Its mixed\ninteger program has four constraints (exclusion of hospitals below the threshold, reassignment, a travel-time share, and this\ncaseload bound) and no bed constraint; the beds implied by added caseload are calculated afterwards, in its Discussion, from\naverage length of stay."),
("\\citet{scarpin2008} optimise patient flow and\nre-regionalise the state of Paran\\'a by p-median with branch-and-price, the\nclosest methodological precedent within SUS.",
 "\\citet{scarpin2008} optimise patient flow and\nre-regionalise the state of Paran\\'a by p-median with branch-and-price, and \\citet{silva2010} allocate specialist\noutpatient appointments in regulation centres by combining multicriteria decision analysis with linear programming\n(it concerns appointments, not admissions or surgery, and its abstract mentions neither capacity constraints nor\ntravel distance)."),
("\\citet{ipea2022} estimate evasion", "\\citet{ipea2022} estimate evasion"),
("What is new is neither the program nor either constraint separately. It is that\nboth are imposed at once. The regional planning literature constrains physical\nresources; the minimum volume literature constrains demonstrated peak volume;\nneither carries the other, so neither can say which of the two limits a system.\nImposing both on the same allocation, over three years of one state, we find\nthat they bind on almost disjoint sets of facilities, that the ratio of aggregate peak-volume cap to demand falls across a period of rapid\nexpansion while physical capacity does not approach its limit, and that the facilities exhausting their peak-volume cap are\nthroughout the ones holding unused beds.",
 "The assignment benchmark itself is old: minimising aggregate travel for a given distribution of origins and destinations is the\ntransportation-problem comparison of the excess-commuting literature, in which \\citet{hamilton1982} compared observed commuting\nwith a monocentric model, \\citet{white1988} compared it with the cost-minimising assignment of households to residences\ntaking observed densities as given, and \\citet{smallsong1992} report that the estimates of excess ranged from about 11 to\nabout 87 per cent across the studies they discuss. Our gap is the same kind of object, and its size depends, as theirs did,\non the zone system and the cost measure (Section~\\ref{sec:capnull}).\n\nWhat we add is narrow: a physical bed-day constraint imposed alongside a peak-volume cap on the same allocation, and a\ntest of whether the two bind on disjoint facilities. At the reported optimum they do in 2019 and 2023 and overlap at one\nfacility in 2025; across all optima of equal cost the result holds only in 2023 (Section~\\ref{sec:capnull})."),
])
edit('paper/sections_2_3.tex', [
("We date this\nrestructuring by its operational effect rather than by its instruments, which\nhave not been read from the Di\\'ario Oficial do Estado de Goi\\'as.",
 "We date this\nrestructuring by its operational effect rather than by its instruments. One instrument has been read: Resolu\\c{c}\\~ao CIB\nn.\\ 111/2021 of 15 July 2021, which approves the state protocol for the regulation of elective surgery. It makes the\nSWALIS priority classification form mandatory for elective surgery requests, routes requests through the state elective\nsurgery regulation system (REGNET), and orders that patients be sequenced and ties broken automatically with weights, SWALIS\npriority carrying the greatest weight and ties broken by the longer wait. We do not claim that it caused any change in the data\nbelow; SIH records no queue entry date and therefore no waiting time."),
])
# abstract and intro findings
ABSTRACT = r"""Elective surgical volume in the Brazilian state of Goi\'as rose 71 per cent
between 2019 and 2023. Using the state's SUS-financed hospital authorisations (AIH)
processed in Goi\'as, we ask what constrained the system, with a capacitated assignment model that
matches municipalities of residence to facility-procedure pairs at least travel cost. The model imposes
a surgical bed-day budget and a cap on each pair equal to its peak 3-month average volume in the year,
a historical high-water mark and not a measured ceiling. Two results hold. Physical beds were far from
binding: net bed utilisation in the optimal allocation is 0.13, 0.18 and 0.22 in 2019, 2023 and 2025, and
stays below 0.1 when all admissions are netted against all inpatient beds. And the observed allocation used
about 29 to 31 per cent more travel, on an ordinal index, than the optimum under the peak-volume cap, with no
detectable change across years (the intervals on differences are about nine points wide). The level of that
gap is not robust to construction: it ranges from 25 to 41 per cent across alternative cost codings, bed
definitions and estimation windows, and the percentile bootstrap interval is shifted upward by resampling the
cap, so basic intervals are reported beside it. Several things we expected did not survive our own tests. The
number of facilities at their cap is not identified (44 to 107 of 131 in 2023 across equally good optima); bed-bound and
cap-bound facilities are disjoint across all optima only in 2023; a stationary-noise null reproduces the rate at
which at-cap units are exceeded; and the fall in the aggregate cap-to-demand ratio is partly coverage and partly
noise. The 2019 to 2023 gain in attainable travel comes with facility-procedure pairs absent in 2019 and the caps they
carry, and most of those pairs (195 of 284) had operated in 2020 to 2022. Residents of the Entorno do Distrito Federal
treated in Federal District hospitals are missing from the data (25 to 51 per cent of their elective surgical
admissions), so we draw no conclusion about them. A budgeted extension that lets the program open new pairs is
reported as exploratory. Code, automated checks and a record of corrections accompany the paper."""
sub_between('paper/main.tex', "Elective surgical volume in the Brazilian state of Goi", "\\end{abstract}", ABSTRACT + "\n", include_end=False)
FINDINGS = r"""Five findings follow, each stated with the tests that bound it.

First, physical bed capacity was never the binding constraint. Aggregate
utilisation of net surgical bed-days in the optimal solution is 0.132 in 2019,
0.178 in 2023 and 0.215 in 2025, and the number of facilities using more than 95 per
cent of their bed-day budget rises only from one of 131 to three to six of 145. Netting every admission
against all inpatient beds gives utilisation of 0.06 to 0.09 and no bed-bound facility. The system was not full at any date.

Second, the allocation was far from the optimum of its own program and showed no detectable
change. Holding every facility to its peak 3-month average volume, the observed 2019 volume could have been
delivered with 28.8 per cent less travel, the 2023 volume with 30.6 per cent less and the 2025 volume with 29.1 per cent
less, on an ordinal travel index. Differences between years are not distinguishable from zero, but the intervals on them
are about nine points wide, so this is no detectable change and not evidence of equality. The level is not robust to
how the inputs are built: it is 37 to 41 per cent when cost counts region-boundary crossings only, 29 to 40 per cent under
alternative bed definitions, and 25 to 31 per cent across estimation windows (Table~\ref{tab:measure}). Observed mean travel
did not fall: it rose from 0.835 to 0.846 to 0.906.

Third, the cap is a peak, not a demonstrated ceiling, and what we can say about it is limited. The two constraints bind on
disjoint sets of facilities at the reported optimum in 2019 and 2023 and overlap at one of 145 in 2025; with one, three and
six bed-bound facilities this is informative against chance only in 2025, and across all optima of equal cost disjointness holds
only in 2023. The number of facilities at their cap is not identified (44 to 107 of 131 in 2023 at the same cost). The rate at which
at-cap units are exceeded the following year is what a stationary system with the same monthly variation would produce, and
the fall in aggregate cap over demand (1.37, 1.32, 1.16) is coverage from 2019 to 2023 and flatter monthly series from 2023
to 2025, with a quarter of the excess over one present by construction (Section~\ref{sec:capnull}).

Fourth, the change in what the system could achieve between 2019 and 2023 came through the set of facility-procedure
pairs, and mostly by reactivation rather than creation. Adding the pairs absent in 2019, with the caps they carry in 2023, moves the
adjusted cost from 1.375 to 0.587; that step is 64 per cent of the improvement in the paper's order of steps and 22 per cent on a
Shapley split, because new pairs are worth nothing without their caps. Of the 284 such pairs, carrying 27.5 per cent of 2023
elective volume, 52 per cent by volume are at facilities absent from SIH altogether, or 84 per cent on the narrower test of absence from
its elective subset. On the monthly panel 195 of the 284 pairs are active in some month of 2020 to 2022 and carry 94.2 per cent of the
cases, so 25.9 of the 27.5 points are capability that lapsed and returned.

Fifth, and exploratory, the program can be asked which pairs it would open under a budget of $k$ new pairs. The answer
depends on the capability assumed for a new pair, was not validated on a later year, and rests on demand that omits residents of the
Entorno do Distrito Federal treated in Brasilia; we report it with those limits and draw no recommendation from it
(Section~\ref{sec:ksweep}).

"""
sub_between('paper/section_1_intro.tex', "Five findings follow.", "The implication for modelling is direct.", FINDINGS)
IMPL = r"""The implication for modelling is limited. A scheduling model that takes the machine set as given cannot represent a change in which
facility-procedure pairs exist, and would attribute to allocation a gain that came with pairs and their caps. The
fixed-machine-set assumption, usually a modelling convenience, is here a substantive question, which this paper treats descriptively.

"""
sub_between('paper/section_1_intro.tex', "The implication for modelling is direct.", "Two features of the setting make", IMPL)
CONTR = r"""The paper contributes in three limited ways. Substantively, it describes a large public-sector surgical expansion with
administrative microdata and what the expansion consisted of in terms of facility-procedure pairs. Methodologically, the program is
standard, the benchmark comes from the excess-commuting literature, and its constraints are drawn from existing work; what we add is a
physical bed-day constraint beside a peak-volume cap and a test of whether they bind on disjoint facilities, with that test's power and
its dependence on the optimum chosen reported. Practically, the paper offers a template: the gap and the two constraints can be
rebuilt from any claims record that identifies the treating facility and the procedure, and every number here can be regenerated and
checked from code. We do not claim that the allocation of surgery rather than queue management is the policy lever, and we do not date
or attribute the expansion to any policy.
"""
sub_between('paper/section_1_intro.tex', "The paper contributes in three ways.", "at queue management, which is where the state's own reform was directed.", CONTR, include_end=True)
print('batch 5 ok')

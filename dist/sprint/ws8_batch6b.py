"""Paper batch 6: fixes from the two outside reviews, each checked against the text and the results first (gap direction, narrative consistency, Vogel wording, cap bracket, duplicates, bootstrap wording, units)."""
import re
def edit(path, pairs):
    s = open(path, encoding='utf-8').read()
    for old, new in pairs:
        assert s.count(old) == 1, (path, s.count(old), old[:90]); s = s.replace(old, new)
    open(path, 'w', encoding='utf-8').write(s)
def between(path, start, end, new):
    s = open(path, encoding='utf-8').read(); a = s.index(start); b = s.index(end, a) + len(end); open(path, 'w', encoding='utf-8').write(s[:a] + new + s[b:])
S4 = 'paper/section_4_model.tex'
# (main.tex and section_1_intro.tex edits of batch 6 were applied by ws8_batch6.py before this part ran)
# --- section 4 narrative ---
edit(S4, [
("and the separation holds for 144 of 145\nfacilities in 2025.","and 144 of 145 facilities are not both bound in 2025 (at the reported optimum; Section~\\ref{sec:capnull} gives the weaker result across optima)."),
("Section~\\ref{sec:capbind} establishes this, and it is the paper's principal\nresult.","Section~\\ref{sec:capbind} reports this at the reported optimum, and Section~\\ref{sec:capnull} tests how much of it survives."),
("cannot represent the mechanism through which this system actually expanded.","cannot represent the change in the set of pairs through which this system expanded."),
("what identifies the mechanism behind the result of Section~\\ref{sec:capbind}.","which describes how the frontier moved."),
("Whatever the 2022 reform did, it did not move the allocation\ntoward the frontier.","The gap shows no detectable change across the panel, and we do not attribute that to any reform."),
("Misallocation in this\nsystem is persistent and identifiable, not a transient feature of any one year.","The distance from the program's optimum is persistent and identifiable in these municipalities, not a transient feature of any one year; whether it is misallocation or reflects patient choice, surgeon availability or regulation is not determined here."),
("The gap is large and well separated from zero at every date,\nwhich is the claim the paper needs.","These are intervals from the marginal bootstrap (300 draws). The paired run of Table~\\ref{tab:bootvar} gives slightly different endpoints, and the 2025 point estimate lies below the 2025 percentile interval, so neither is used for inference about the level. The replicates resample facility-months of what is close to a census of the state's authorisations, so the intervals describe sensitivity to the monthly pattern and not sampling from a larger population."),
("which is a stronger statement than the aggregate gap makes\nand points at the same instrument.","within this program. We did not test why a ceiling below 2.5 is infeasible and draw no inference from it about instruments."),
("This is a negative result and it is the more useful one for the paper's argument.\nThe instrument the system responds to is capability placement; the evidence here\nis that the instrument is not currently being aimed. A ranking",
 "The test finds no detectable concentration, and it could not have detected lifts below about 1.9 times chance, so we draw no conclusion about whether capability placement is aimed at the priced pairs. A ranking"),
("This is the sense in which the paper's diagnosis carries an\ninstrument: the binding constraint is where capability sits, and buying a little\nmore of it in the right places moves the frontier faster than any reshuffling of\nthe rest.","These are values of an exploratory program under assumed capability for new pairs, with demand that omits Entorno residents; they are not a recommendation."),
("Bounding facility throughput by observed case volume in this way follows","Bounding facility throughput by observed case volume in this way is in the spirit of"),
])
between(S4, "This is the leading edge of the panel rather than a counterexample to it:", "capability, not how to schedule the capability already in place.",
r"""The 2025 overlap is not a trend: in the 2019 optimal face a facility can already be both bed-bound and at cap
(Section~\ref{sec:capnull}), so an overlap appearing in 2025 at this vertex does not mark a leading edge. The ratio of aggregate peak-volume
cap to demand falls from 1.368 to 1.160 and state-wide bed utilisation moves from 0.132 to 0.178 to 0.215, and the facilities at their cap
are, at the reported optimum, mostly ones with bed-days to spare. The share of pairs that bind is not monotone, at 56.0, 50.8 and 60.2 per cent.
Beds, counted at full occupancy, are not scarce at any of the three dates in this program; operating-room sessions, surgeons and
anaesthetists are not modelled.

Read with Section~\ref{sec:results}, this describes the expansion without identifying its cause. Bed utilisation rose only from 0.13 to 0.21
while elective volume more than doubled, and routing showed no detectable improvement. What changed is that facilities absent from the 2019 elective
data began providing elective surgery, 84 per cent of that volume on the elective test of absence and 52 per cent counting only facilities
absent from SIH altogether, disproportionately in interior regions whose residents had previously crossed regional boundaries to be treated.
Whether the right response is to place capability or to change how existing capability is used is a policy question this model does not answer.""")
# --- counts, duplicate row, bootstrap wording, units ---
edit(S4, [
("At the reported optimum the counts are 72, 75 and 103 (77 in the stored 2023 solution).","The stored solution behind the tables has 79, 77 and 105 facilities at cap and 1, 3 and 6 bed-bound; a fresh solve of the same program lands on another vertex with 72, 75 and 103 and 1, 3 and 5, which is the non-uniqueness at work."),
("against 1, 3 and 5 at the reported optimum.","against 1, 3 and 6 in the stored solution."),
("Cost recoded to region-boundary crossings (0/0/1/2) & 37.1 & 39.9 & 41.0 \\\\\nOrigin zone = immediate health region (cost 0/1/2) & 37.1 & 39.9 & 41.0 \\\\\n","Cost recoded to region-boundary crossings (0/0/1/2); identical to origin zone = immediate health region & 37.1 & 39.9 & 41.0 \\\\\n"),
("Aggregating origins to the immediate health region, with cost 0 for a\nfacility in the same region, raises the gap to 37.1, 39.9 and 41.0 per cent, and aggregating","Aggregating origins to the immediate health region, with cost 0 for a\nfacility in the same region, is the same program as the boundary-crossing recoding (cost then depends only on the origin's region) and gives 37.1, 39.9 and 41.0 per cent; aggregating"),
("because a coarser zone hides which patients already travel within their zone; the gap is zone-dependent by more than five\npoints at every zone size, as in the excess-commuting literature.","because a coarser zone hides which patients already travel within their zone; the gap is zone-dependent by more than five\npoints at every zone size."),
("The basic interval lies at or below the point estimate's neighbourhood,\n$[22.4, 29.1]$, $[23.0, 30.9]$ and $[20.5, 28.6]$; neither interval is exact, and we read","The basic interval lies below the percentile interval,\n$[22.4, 29.1]$, $[23.0, 30.9]$ and $[20.5, 28.6]$; in 2025 the point estimate (29.1) lies outside both, a symptom of bootstrapping a statistic built on a maximum at a degenerate optimum, so neither is a valid confidence interval, and we read"),
("Capacity $B_j$ is facility $j$'s surgical bed-day endowment:","Throughout, $d_{ip}$, $B_j$ and $\\kappa$ are monthly quantities (annual totals divided by twelve). Capacity $B_j$ is facility $j$'s surgical bed-day endowment:"),
("That is the conservative reading, and","That is a deliberate reading, and"),
])
s = open(S4, encoding='utf-8').read()
s = s.replace('region-crossings per case', 'index units per case').replace('region-crossings per elective case', 'index units per elective case').replace('region-crossings against', 'index units against').replace('region-crossings in', 'index units in').replace('2.5 region-crossings', '2.5 index units').replace('3 region-crossings', '3 index units')
open(S4, 'w', encoding='utf-8').write(s)
edit('paper/sections_2_3.tex', [
("The two waves moved different facilities.","The movers in the two waves are uncorrelated across facilities."),
("these facts describe a single policy applied in stages","these facts are consistent with a policy applied in stages, which we do not identify"),
])
# --- cap bracket paragraph + decomposition table ---
NEW = r"""
\paragraph{The gap depends on the cap.} The cap is built from the same months it constrains and is a peak, so each pair is given
headroom of peak over mean. Replacing the peak with the unit's annual mean volume (the fixed-marginal benchmark of the
excess-commuting literature) leaves almost nothing to reallocate in 2019, a gap of 6.2 per cent with 0.3 per cent of demand unserved; in 2023 the gap is
22.7 per cent with 7.3 per cent unserved and in 2025 29.6 per cent with 9.8 per cent unserved, so those are not like-for-like. Deflating the peak by
the expected excess of the maximum of twelve Poisson months over their mean gives 22.7, 24.0 and 24.8 per cent, 6.0, 6.5 and 4.3 points below the
headline. The headline gap is therefore partly headroom that a peak always has over a mean, and is reported with this bracket.
Bed utilisation is not an artifact of the cap: it is 0.12, 0.178 and 0.198 at the 2$\times$ cap and 0.129, 0.188 and 0.199 with no cap (2019, 2023,
2025), against 0.132, 0.178 and 0.215 at 1$\times$. Across the optimal face it ranges from 0.122 to 0.166, 0.165 to 0.217 and 0.206 to 0.238.

\begin{table}[t]
\centering
\caption{Configurations behind the options share of the 2019-to-2023 improvement. Adjusted cost (cost plus $\pi$ times unmet, per case). B: 2023 demand, 2019
capacity and options; C: 2023 capacity added; D: 2023 options added (the paper's order is B, C, D); E: 2023 demand, 2019 capacity, 2023 options. Options share of
the improvement from B to D: forward = (C$-$D)/(B$-$D); reverse = (B$-$E)/(B$-$D); Shapley is their mean.}
\label{tab:shapley}
\begin{tabular}{rrrrrrrr}
\toprule
$\pi$ & B & C & D & E & Forward & Reverse & Shapley \\
\midrule
4 & 1.402 & 1.143 & 0.587 & 1.555 & 0.68 & $-0.19$ & 0.25 \\
6 & 1.823 & 1.375 & 0.587 & 2.078 & 0.64 & $-0.21$ & 0.22 \\
10 & 2.655 & 1.835 & 0.587 & 3.124 & 0.60 & $-0.23$ & 0.19 \\
\bottomrule
\end{tabular}
\end{table}
"""
edit(S4, [("\n\\begin{table}[t]\n\\centering\n\\caption{The gap (per cent) under alternative constructions of the inputs;", NEW + "\n\\begin{table}[t]\n\\centering\n\\caption{The gap (per cent) under alternative constructions of the inputs;")])
print('batch 6 ok')

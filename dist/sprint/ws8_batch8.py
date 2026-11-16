"""Final batch: capnull paragraphs rewritten for the stricter face search, the slack verdict, the bed-row result; abstract and introduction wording for disjointness and the at-cap count."""
def between(path, start, end, new):
    s = open(path, encoding='utf-8').read(); a = s.index(start); b = s.index(end, a); open(path, 'w', encoding='utf-8').write(s[:a] + new + s[b:])
def edit(path, pairs):
    s = open(path, encoding='utf-8').read()
    for old, new in pairs:
        assert s.count(old) == 1, (path, s.count(old), old[:90]); s = s.replace(old, new)
    open(path, 'w', encoding='utf-8').write(s)
S4 = 'paper/section_4_model.tex'
between(S4, "\\paragraph{The at-cap count is not identified.}", "\\paragraph{The cap test.}", r"""\paragraph{The at-cap count is not identified.} The program's optimum is a face, not a point: many allocations have the same
cost. We searched that face (cost within $10^{-9}$ of optimal; a margin of $10^{-4}$ of the cap for a facility to count as at cap; 200 seconds per
search; every count quoted in a row comes from one solution, and no row constraint was violated by more than $10^{-14}$ in relative terms). The number of facilities using more than 95 per cent of their
peak-volume cap has a proved minimum of 34 of 131 in 2019, 44 of 131 in 2023 and 64 of 145 in 2025. The largest value found is 101, 107 and 115, with upper bounds of
113, 108 and 131 that the solver did not close. At 90 per cent the proved minimums are 39, 52 and 69, and at 99 per cent 31, 43 and 53. At the reported optimum the counts
are 72, 75 and 103 (79, 77 and 105 in the stored solution; a fresh solve of the same program lands on another vertex, which is the non-uniqueness at work). Bed-bound facilities (more than 95 per cent of the
bed-day budget) range from 0 to 2 in 2019 (proved), from 2 to at least 4 (upper bound 5) in 2023 and from 4 to at least 7 (upper bound 9) in 2025, against 1, 3 and 5 at the
reported optimum (1, 3 and 6 in the stored solution). Statements about how many facilities ``are at their cap'' are therefore statements about one optimum among many. The unused surgical
bed-days at facilities at cap are at least about 9{,}700 (2019) and 12{,}100 (2023) at some optimum; we did not establish their upper range at these settings, so the 26{,}269 bed-days
quoted earlier for 2023 is the value at the stored solution only.

\paragraph{Disjointness.} At the reported optimum the two constraints bind on disjoint sets of facilities in 2019 and 2023 and overlap at one facility in 2025. Across the optimal
face, an overlap of one facility is attainable in 2019 (proved) and of two in 2025 (found; the solver could not rule out more, with an upper bound of five). In 2023 no overlap
was found, but the search did not prove that none exists (upper bound two within the time limit). Disjointness is therefore a statement about the reported optimum and not about
the face. How informative it is against chance depends on the vertex: with $K$ bed-bound and $n$ at-cap facilities among $N$, the probability under random assignment of an overlap as small as the one
observed ranges across the extreme vertices from 0.23 to 0.80 in 2019, 0.03 to 0.19 in 2023 and 0.001 to 0.17 in 2025 (0.40, 0.07 and 0.006 at the reported optimum). In 2019 the minimum number of
bed-bound facilities across the face is zero, so the claim can be vacuous there.

""")
between(S4, "\\paragraph{What the ratio of cap to demand contains.}", "\\paragraph{Measurement choices.}", r"""\paragraph{What the ratio of cap to demand contains.} The aggregate ratio of caps to demand (1.368, 1.321, 1.160) is not slack in
the sense of unused capacity. The sum of caps over the sum of mean volume at the same facilities is 1.37, 1.40 and 1.27, and the expected maximum 3-month mean of twelve Poisson months at those means would alone give a
ratio of about 1.09 (the one floor we use), so about a quarter of the excess over one exists by construction. We tested whether the fall in the ratio reflects flatter monthly series, with a rule stated for the
2019-to-2025 comparison: the volume-weighted peak-to-mean ratio net of that floor, over the 96 facilities present in both years, changes by $-0.07$ (95 per cent facility-bootstrap interval $[-0.15, +0.01]$). The interval includes
zero, so the explanation ``flatter months'' is not supported. The 2019-to-2023 fall coincides with falling coverage (the facilities in the model account for 100, 94 and 91 per cent of demand). A 2023-to-2025 contrast, chosen after seeing the
full-period result, gives $-0.12$ ($[-0.22, -0.05]$) and is exploratory. We do not describe the fall as a tightening of capacity.

""")
edit(S4, [("Bed utilisation stays low under every definition (0.06 to 0.22) and no facility is bed-bound\nwhen all admissions are netted against all inpatient beds. Observed elective bed-days exceed the budget at 1, 2 and 4 facilities.",
 "Bed utilisation stays low under every definition (0.06 to 0.22) and no facility is bed-bound\nwhen all admissions are netted against all inpatient beds, but the bed row is not inert: dropping it raises the gap by 0.0, 3.5 and 2.4 points (2019, 2023, 2025) because 1, 3 and 5\nfacilities would then exceed their bed-day budget, while replacing the shrunk stay lengths by facility-procedure means leaves the gap unchanged (0.0, 0.0 and $-0.1$ points). Beds are slack in aggregate and bind at a few facilities.\nObserved elective bed-days exceed the budget at 1, 2 and 4 facilities.")])
edit('paper/main.tex', [
("number of facilities at their cap is not identified (44 to 107 of 131 in 2023 across equally good optima); bed-bound and\ncap-bound facilities are disjoint across all optima only in 2023;","number of facilities at their cap is not identified (in 2023 it has a proved minimum of 44 of 131 and a largest value found of 107 across equally good optima); the disjointness of bed-bound and\ncap-bound facilities is a property of the reported optimum, since an overlap is attainable at other optima in 2019 and 2025;"),
("Physical beds were far from\nbinding: net bed utilisation","Beds were slack in aggregate and bound at a few facilities: net bed utilisation"),
])
print('batch 8 ok')

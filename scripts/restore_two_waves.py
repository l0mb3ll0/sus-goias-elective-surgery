import pathlib

P = pathlib.Path('paper/sections_2_3.tex')
s = P.read_text()

ANCHOR = '\\subsection{The July 2022 step came from existing facilities}'
assert s.count(ANCHOR) == 1, 'anchor not found exactly once'
assert 'two waves' not in s, 'section already present'

BLOCK = r"""\subsection{The 2022 change occurred in two waves}

The 2022 break date is not stable across specifications, and the instability is
informative rather than a nuisance. On the full sample PELT returns May 2022;
on the reliable subset it returns October 2022; a single-changepoint search
returns September. Running the reliable-subset series at a lower penalty
returns both May and October.

Inspection of the seasonally adjusted series shows why. The ratio is 0.334 in
January and February 2022, then 0.522, 0.493, 0.546, 0.510 and 0.505 from March
to July, then 0.665 in August. A fixed-cardinality search with two breaks over
the window June 2021 to June 2023 returns April 2022 and September 2022, with
segment means of 0.400, 0.469 and 0.633. There are two steps, not one, and
single-changepoint procedures report a date between them.

The two steps are driven by different facilities. Classifying reliable-subset
hospitals by whether their volume grew by more than 30 per cent across the
first step (August 2021 to February 2022 against March to July 2022) or the
second (March to July 2022 against August 2022 to January 2023) gives nine
facilities that move only in the first, twelve that move only in the second,
six that move in both and twenty-two that move in neither. The correlation
between the two growth ratios is $-0.05$ (Pearson), $-0.22$ in logs and
$-0.07$ by rank. Weighted by volume, second-wave movers contribute 1{,}147
elective cases per month by late 2022 against 461 for first-wave movers.
[TODO: the two ratios share a denominator, which biases their correlation
downward mechanically. Re-estimate by splitting the middle window into two
random halves and using one for each ratio, averaged over repetitions, before
asserting that the cohorts are disjoint.]

The case mix, by contrast, moves the same way in both steps. Across four-digit
SIGTAP subgroups the share changes in the first and second steps correlate at
0.86: subgroup 0407 gains 2.75 and then 2.89 percentage points of share, 0415
gains 1.40 and then 1.32, while 0406 and 0416 lose share in both. In SIGTAP
these are, respectively, surgery of the digestive tract and annexed organs,
whose highest-volume member is laparoscopic cholecystectomy; multiple procedures
performed in a single admission; vascular surgery, led by bilateral varicose
vein repair; and skin and subcutaneous tissue. Geographically, the state's
largest municipality by surgical volume grows by a factor of 1.0 in the first
step and 1.4 in the second, while several interior municipalities grow by
factors between 2.5 and 4.5, at different times.
[TODO: repeat at the level of the \emph{regiao de saude}, which is the unit
along which a state regulation reform would actually be rolled out. The
crosswalk is not in the SIH files.]

Taken together, these facts describe a single policy applied in stages to
different parts of the state, with a consistent effect on the mix of procedures
performed and a staggered effect on which facilities performed them.

"""

P.write_text(s.replace(ANCHOR, BLOCK + ANCHOR))
print('inserted, file now', len(P.read_text()), 'chars')
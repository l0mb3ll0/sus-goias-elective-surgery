# WS4 results: what kappa can and cannot be called

Inputs: dist/review/null_cap.txt/json (200 stationary-Poisson runs per transition, kappa rebuilt, LP re-solved, at-cap redefined per run),
ratio_decomp.txt, boot_fixed.txt, alt_optima*.txt. Decision rules: WS4_prereg.md (written before these outputs were read).

## Test A: cap-test null (items 1 and 2). Facility level, elective, share of at-cap units with kappa_{t+1} > kappa_t
| transition | observed | null mean [2.5, 97.5] | p (null >= obs) | obs median size | null median size |
|---|---|---|---|---|---|
| 2023->24 at cap (n 76) | 51.3% | 45.9% [35.5, 53.8] | 0.13 | +71% | +9% |
| 2023->24 not at cap (n 55) | 34.5% | 41.9% [11.1, 71.5] | 0.66 | +52% | +5% |
| 2024->25 at cap (n 84) | 52.4% | 44.2% [36.4, 53.6] | 0.05 | +54% | +9% |
| 2024->25 not at cap (n 48) | 31.2% | 57.2% [20.0, 91.8] | 0.92 | +33% | +4% |
Pair level at cap: 41.7% vs null 43.7% (p 0.75) and 42.5% vs 42.7% (p 0.51); sizes +98% and +59% vs +19% each.
Size = median of kappa_{t+1}/kappa_t - 1 among exceeders. "Not at cap" nulls rest on about 5 to 11 units per run, so their intervals are wide.
The null at-cap count is 112-126 of 131 (2023) and 124-131 (2024), against 76 and 84 observed: pure-noise kappa would leave far FEWER
facilities with slack than the data show.

Reading against the pre-registered rule:
1. Rate: the observed at-cap exceedance rate is inside the null interval in 2023->24 (p 0.13) and on its edge in 2024->25 (p 0.05, observed 52.4
   vs upper limit 53.6). The rate alone gives no evidence that kappa binds. The rule's "NO evidence from the aggregate test" branch applies:
   about 45% of at-cap units would exceed next year's kappa in a stationary system, purely because kappa is a maximum.
2. Size: when units exceed, the median exceedance is +54% to +71% at facility level, six to eight times the noise size (+9%). The pre-registered
   the pre-registered size reading is not used as a falsification: Poisson understates variation and the overdispersed null (below) is the relevant comparison. Under this POISSON null the exceedances are several times
   noise size. Poisson understates within-year variation, so this is not yet a statement about growth or loosened caps: the overdispersed resampling null (PREREG_round3.md T2) decides it, and 'growth' is not asserted. Also, demand grew over the window, so large exceedance is what an unconstrained expanding system produces too;
   this test cannot separate "cap broken" from "no cap".
3. Urgent placebo: urgent at-cap rates are at or BELOW null (38.9% vs 45.4%; 29.7% vs 44.4%, p 0.89 and 1.0), with sizes +21% and +41% vs +8%.
   Urgent volume is more volatile than Poisson but does not show the elective surgeon pattern.
4. Surgeon split (the one place the data beat the null): at-cap facilities where surgeons rose exceed 78.6% (null 46.8%, p<0.005, n 28) and 63.2%
   (null 46.1%, p<0.005, n 38); where surgeons did not rise 35.4% (null 45.3%) and 43.5% (null 42.2%), no excess. Pair level 53.9% vs 43.8% (p 0.005),
   49.0% vs 43.3% (p 0.07). Urgent placebo for surgeons-rose: 47.8% vs 46.2% (p 0.40) and 28.1% vs 43.6%, no excess.
   This is consistent with capability tracking staff, but it is correlational: surgeons rose by CNES count, which also rises when a hospital grows
   for any reason, resource flags are facility-level, and the null treats flags as independent of volume. Rooms and laparoscopes n 1-18: unreadable.

## What kappa can and cannot be called
- Cannot: "the most a unit can do", "sustainable capacity", or a ceiling that the cap test confirms. The test does not confirm it (rate inside null) and
  the size evidence argues against it (exceedances several times noise).
- Can: "peak 3-month average volume in the estimation year" (a historical high-water mark; lower bound on what the unit has done, not an upper bound on what it can do).
  "Demonstrated" can stay only in the sense "volume it has demonstrably delivered", with the lower-bound reading stated.
- Slack: aggregate capability/demand is 1.368, 1.321, 1.160. ratio_decomp: zero months explain 15-17% of the excess over base, active-month variation 83-85%,
  and a Poisson counting floor 20-27%, leaving 58-65% beyond counting noise. So net-of-noise slack is smaller than headline but the majority of the gross
  slack survives noise correction. The Poisson floor is a lower bound on noise (clinical batching, scheduling), so 58-65% is an upper bound on "real" slack.
- "Tightening": the fall in slack 1.368 -> 1.160 is not shown here to be flatter months. ratio_decomp does not partition the change across years;
  that is untested. Do not use "flatter months" as the interpretation unless a year-by-year decomposition supports it [OPEN].
- Bootstrap: resampling kappa is what lifts the bootstrap gap (full +3.3/+3.7/+4.8 pp; kappa fixed -0.9/-2.3/-2.1 pp; demand fixed +1.4/+2.0/+3.4 pp, 340 draws).
  The percentile interval therefore sits above the point estimate for a reason tied to kappa being a maximum, and the paper's description of that bias should say so.
  The fixed runs leave 0.3-0.5% of demand unmet, so they are not clean decompositions.

## kappa_urgent as a headline robustness result: does it hold?
Not assessed in this pass. Commit 0f55507 reports both-bound counts 0/0/0 under kappa_urgent with unmet demand 16-36%, which the paper's own rule retires as a
gap estimate. Disjointness under kappa_urgent is the only part that survives. Recommendation: report it as a robustness check of the disjointness
claim only, with the unmet-demand caveat, not as a headline. Decision for the author.

## Item 3: alternate optima (2023 at-cap count), objective held within 1e-9 (and 1e-6) of optimal
Read the z_sum / dual-bound figures, not the "count" column: the maximiser parks units at threshold + 1e-7, which a +1e-6 band hides, and the minimiser parks
units exactly on the threshold (so ">= threshold - 1e-6" is the loose count).
| level, threshold | min at-cap (strict) | max at-cap | status |
|---|---|---|---|
| facility, > 0.95 (paper's rule), tol 1e-6 | 44 (proved) | 107 (proved optimal, dual 107) | both solved |
| facility, > 0.95, tol 1e-9 | 44 (proved) | >= 107, dual bound 108.6 | max hit 600 s limit |
| facility, > 0.99 | 43 (proved) | >= 103, dual bound 105 | max hit limit |
| facility, >= 0.999999 (truly at kappa) | 37 (proved) | >= 103, dual bound 105 | max hit limit |
| pair, > 0.95, tol 1e-9 (517 non-floored pairs) | 112 (proved) | >= 343, dual bound 365 | max hit limit |
Stored 77 and fresh 76 (pair count 259) sit well inside these ranges. Conclusion: the facility at-cap count is NOT identified by the LP optimum; at fixed optimal
cost it can be anywhere from about 44 to 107 of 131 (at least 37 even at full binding). Any sentence using "77 at their capability cap" is reporting one vertex.
What is robust: the 3 bed-bound facilities and the 0.58 capability use at those 3 are properties of the chosen vertex too and should be checked across the face [OPEN];
the aggregate unused bed-days (26,269 across the 77) are also vertex-specific.
Files: alt_optima.txt (0.95, facility and pair), alt_optima_thr0.99.txt, alt_optima_thr0.999999.txt.

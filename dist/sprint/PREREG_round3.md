# Pre-registration, round 3 (written before computing; see the git commit time of this file)
Clock: system clock, EST. All four tests below were requested after the earlier rounds; none has been run when this is written.

## T1. Disjointness across the optimal face (years 2019, 2023, 2025; elective LP at point values; kappa = peak 3-month average volume)
Face F = {(x,u) feasible for the paper's LP with objective <= V*(1 + 1e-6)}. Thresholds: A = served/kappa > 0.95 (strict, 1e-6 band), B = served/kappa >= 0.999999.
Bed-bound: bed-day use / net bed-day budget > 0.95. Cap-bound: A or B, stated each time.
Outputs: (i) min and max number of bed-bound facilities over F (MILP, 300 s limit per solve, incumbent and dual bound both reported);
(ii) max number of facilities simultaneously bed-bound and cap-bound over F, at A and at B; (iii) for every facility the exact interval [min, max] of served/kappa over F (LP), classified
ALWAYS (min above threshold), NEVER (max at or below threshold), SOMETIMES, separately at A and at B; (iv) min and max over F of unused bed-days (budget minus use) summed over the facilities that are cap-bound at A in that solution (MILP).
Decision rule. The paper's disjointness claim SURVIVES in a year iff the PROVED maximum over F of the simultaneous count at threshold A is <= the overlap at the reported optimum (0 in 2019, 0 in 2023, 1 in 2025).
A max that is only an incumbent (dual bound above it) is reported as a lower bound on the true max and cannot support survival. If the proved max exceeds the reported overlap in a year, the claim for that year becomes "disjoint at the reported optimum; overlap up to M across optima of equal cost", and the paper must say so.
Falsifier: any year with proved max overlap > reported overlap. Also reported: whether min bed-bound = 0 (claim uninformative, as zero overlap is then trivially attainable).

## T2. Overdispersed (resampling) null for the cap test
Same pipeline as the Poisson null (dist/review/null_cap.py): kappa rebuilt, LP re-solved on simulated kappa, at-cap defined per run, 200 runs per transition, 2023->24 and 2024->25.
Simulated series: for each facility draw 12 month indices with replacement from its 12 observed year-t months (same indices for all of the facility's pairs, preserving within-facility co-movement), for year t; an independent draw of 12 indices for year t+1 (stationary at the year-t empirical distribution). Urgent likewise from observed urgent months.
Poisson results stay beside it. Decision rule: "exceedances are larger than within-year variation alone produces" is supported at a transition iff the observed median size of exceedance (facility level, at cap) exceeds the 97.5th percentile of the null's per-run medians, AND the observed exceedance rate lies above the null's 97.5th percentile or is reported as inside it.
Wording rule: until this finishes, no sentence says exceedances are "growth, not noise"; after it, 'growth' is not asserted at all because demand growth is not separated from loosened caps by this test.

## T3. Bootstrap interval for the 2025 gap
Problem: the 2025 point gap (29.1) lies below its percentile interval (paper: marginal [29.7, 38.0]; paired run [29.7, 37.8]). Test m-out-of-n multiplier bootstrap: for each draw choose m of the n facility-month-of-year slots with replacement (counts scaled n/m), m = floor(0.5 n) and floor(0.7 n), 340 draws, same seeds scheme, all three years paired.
Rule: an m-out-of-n interval is presentable only if it covers the point estimate in all three years. Whatever it shows, the paper reports FULL, KAPPA-FIXED and DEMAND-FIXED results side by side (dist/review/boot_fixed.txt, rerun with the all-record shrinkage if time), and never the percentile interval alone.

## T4. Surgeon lead-lag (EXPLORATORY)
Panel: facility x month for months with CNES PF available; y_t = in-state elective AIH count (SIH RD); s_t = count of distinct identified professionals with a surgeon CBO (list in dist/review/cap_test.py), aggregates only, no identifiers printed.
Spec: with 3-month rolling means smoothed, Dy_t = sum_{h=-6..+6} b_h Ds_{t-h} + facility FE + month FE, standard errors clustered by facility. h>0: surgeon change h months BEFORE the volume change; h<0: AFTER.
Verdict: "surgeon rises come before volume rises" iff sum_{h=1..6} b_h > 0 with a cluster-robust 95% interval excluding 0 AND exceeds sum_{h=-6..-1} b_h; "after" iff the reverse; otherwise "no temporal ordering detected". Exploratory regardless of result; correlational.

## Amendments written before T4 was run (same day, after seeing that CNES PF covers only 2024-01..2025-12, 24 months)
- T4 sample: facilities with mean >= 5 in-state elective AIH per month over 2024-01..2025-12 (the paper's low-base convention). Not tuned.
- With 24 months, 3-month rolling means and lags up to 6 leave about 9 usable months per facility; T4 is therefore low power and is reported as such. If fewer than 8 usable months remain, lags are limited to +/-4 and that is stated.

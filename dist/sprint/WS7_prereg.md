# WS7 pre-registration: disjointness replication pilot (written 2026-11-04 before any non-Goias data was downloaded)
Claim tested: bed-bound facilities (>0.95 of net surgical bed-day budget) and capability-bound facilities (>0.95 of the rolling-3 peak cap kappa) are disjoint, in the same optimum, on data from other states.
States, pre-specified by region (rule): the most populous state in each of three macro-regions other than Centre-West (Goias's own) and North, excluding Sao Paulo (memory): Northeast = BA, South = PR, Southeast (excl SP) = MG.
North is omitted for budget (not for results). If a state cannot be run (size, download failure) it is reported as failed and NOT replaced.
Year: 2023 only (SIH RD and CNES LT, 12 months), same builder as Goias (scripts/bootstrap_paired.py Year, via BOOT_UF/BOOT_ROOT), same constants (PI 6, K 30, rolling-3 cap, pair row), same thresholds.
Size gate: skip a state whose LP would have more than 3,000,000 arc variables (reported as failed for size).
Per state report: facilities, bed-bound n, cap-bound n, overlap, hypergeometric p(overlap <= observed), gap, unmet share, slack (sum kappa / demand).
Verdict per state: INFORMATIVE only if bed-bound n >= 3 (otherwise zero overlap is expected by chance, as in Goias 2019/2023). REPLICATES if informative and p < 0.05. DOES NOT REPLICATE if informative and p >= 0.05 or overlap exceeds expectation.
Expand beyond the pilot only if >= 2 of 3 states are INFORMATIVE and REPLICATE and the pilot ran in < 3 h wall time. Otherwise report the pilot as it stands. Nothing here goes in the main results; everything is labelled exploratory.
Not tuned after seeing results.

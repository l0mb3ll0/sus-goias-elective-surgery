"""Paper batch 3: bootstrap section (audit item 8, T3): correct explanation, disclosure, side-by-side variants, basic interval, 'no detectable change', p-values from the store."""
def edit(path, pairs):
    s = open(path, encoding='utf-8').read()
    for old, new in pairs:
        assert s.count(old) == 1, (path, s.count(old), old[:80]); s = s.replace(old, new)
    open(path, 'w', encoding='utf-8').write(s)
TABLE = r"""
\begin{table}[t]
\centering
\caption{The bootstrap gap with all inputs, only $\kappa$, or only demand resampled (340 paired draws; per cent). Mean and 95 per cent percentile interval; shift is the mean minus the point estimate in points; ``basic'' is the reverse-percentile interval of the full run, $[2\hat\theta - q_{97.5}, 2\hat\theta - q_{2.5}]$. Stay-length shrinkage over all elective records, as in the stored model; the earlier shrinkage over model facilities only gives the same figures to one decimal. The $\kappa$-fixed and demand-fixed runs leave 0.3 to 0.5 per cent and up to 0.03 per cent of demand unmet, so they are diagnostics, not a decomposition.}
\label{tab:bootvar}
\begin{tabular}{lrrrrr}
\toprule
Year & Point & Full: mean [interval] & $\kappa$ fixed: mean (shift) & Demand fixed: mean (shift) & Full: basic \\
\midrule
2019 & 28.8 & 32.1 [28.5, 35.1] & 27.9 ($-0.9$) & 30.2 ($+1.4$) & [22.4, 29.1] \\
2023 & 30.6 & 34.3 [30.3, 38.1] & 28.3 ($-2.3$) & 32.6 ($+2.0$) & [23.0, 30.9] \\
2025 & 29.1 & 34.0 [29.7, 37.8] & 27.0 ($-2.1$) & 32.5 ($+3.4$) & [20.5, 28.6] \\
\bottomrule
\end{tabular}
\end{table}
"""
edit('paper/section_4_model.tex', [
("zeroes facility-months deflates it mechanically, and Dirichlet weights keep every\nfacility-month present while perturbing its magnitude.",
 "zeroes facility-months deflates it mechanically, and Dirichlet weights keep every\nfacility-month present while perturbing its magnitude. The scheme resamples demand, caps, stay\nlengths and the observed baseline; it does not resample the bed-day budgets $B_j$, the facility set\n$J$ or the option scope, so the intervals understate uncertainty about those."),
("None of the three\ndifferences is distinguishable from zero, at $p = 0.27$, $0.91$ and $0.41$. The\nstability reported in Section~\\ref{sec:modelresults} is a finding about the\ndifferences and not merely an inference from overlapping marginals, and no trend\nshould be read into the ordering of 28.8, 30.6 and 29.1.",
 "None of the three\ndifferences is distinguishable from zero, at $p = 0.26$, $0.92$ and $0.41$ ($0.26$, $0.91$ and $0.41$\nwith the earlier stay-length shrinkage target). This is no detectable change, not evidence of equality: the\n95 per cent intervals on the differences are 8.2, 9.6 and 9.2 points wide, so changes of several points\nbetween years cannot be excluded, and no trend should be read into the ordering of 28.8, 30.6 and 29.1."),
("The bootstrap means sit 3 to 5 points above the point estimates. This is expected\nrather than anomalous: the optimal value of the program is convex in the demand\nvector, so perturbing demand raises it in expectation. We attempted a",
 "The bootstrap means sit 3 to 5 points above the point estimates, and the 2025 point estimate lies below\nits own percentile interval (29.1 against $[29.7, 37.8]$). The cause is not convexity in demand alone.\nTable~\\ref{tab:bootvar} perturbs only part of the inputs. Resampling demand with $\\kappa$ held at its point\nvalue lowers the gap, by 0.9, 2.3 and 2.1 points, which is what convexity of the optimal value in demand\nimplies. Resampling $\\kappa$ with demand held fixed raises it, by 1.4, 2.0 and 3.4 points: $\\kappa$ is a\nmaximum over windows, so reweighting months lifts it, loosening the cap. The two effects do not add (the\nfull-run shifts are 3.3, 3.7 and 4.8 points), so the upward shift in the paper's bootstrap comes from resampling\n$\\kappa$. We attempted a"),
("discrepancy is a systematic shift of the resampling distribution, which is what\nconvexity produces, not the skewness that BCa is built to correct. We therefore\nreport the percentile interval for width and the point estimate, computed on the\nrealised panel, for level.",
 "discrepancy is a systematic shift of the resampling distribution, which resampling a maximum\nproduces, not the skewness that BCa is built to correct. A subsampling variant (an $m$-out-of-$n$\nmultiplier bootstrap with $m = n/2$ and $0.7n$) did not help: its intervals cover the point estimate in one\nof six cases and its means sit higher still. We therefore report the percentile interval together with the\nbasic interval and the point estimate computed on the realised panel (Table~\\ref{tab:bootvar}), and never the\npercentile interval alone. The basic interval lies at or below the point estimate's neighbourhood,\n$[22.4, 29.1]$, $[23.0, 30.9]$ and $[20.5, 28.6]$; neither interval is exact, and we read the gap as\nabout 29 to 31 per cent with a plausible range from the low twenties to the high thirties.\n" + TABLE),
])
print('batch 3 ok')

def between(path, start, end, new):
    s = open(path, encoding='utf-8').read(); a = s.index(start); b = s.index(end, a); open(path, 'w', encoding='utf-8').write(s[:a] + new + s[b:])
def edit(path, pairs):
    s = open(path, encoding='utf-8').read()
    for old, new in pairs:
        assert s.count(old) == 1, (path, s.count(old), old[:90]); s = s.replace(old, new)
    open(path, 'w', encoding='utf-8').write(s)
S4 = 'paper/section_4_model.tex'
between(S4, "\\paragraph{The cap test.}", "\\paragraph{What the ratio of cap to demand contains.}", r"""\paragraph{The cap test.} If caps bind, units at their cap in year $t$ should be exceeded less often in year $t+1$ than a
stationary system would exceed them. Among facilities at cap, 51.3 per cent (2023 to 2024) and 52.4 per cent (2024 to 2025) have a
larger peak the next year. Rebuilding the peak, re-solving the program and redefining ``at cap'' on 200 simulated stationary years,
that rate is 45.9 per cent (95 per cent range 35.5 to 53.8; $p = 0.13$) and 44.2 per cent (36.4 to 53.6; $p = 0.05$) when each unit's
months are Poisson, and 47.9 per cent (36.3 to 58.1; $p = 0.24$) and 47.7 per cent (37.5 to 56.9; $p = 0.18$) when each facility's
months are resampled from its own observed months, which keeps its overdispersion. The observed rates are inside the null range. This is a
low-power non-rejection: it is not evidence that the cap binds and not evidence that it does not. The contrast between the at-cap and not-at-cap rates
(observed $+0.17$ and $+0.21$) is also inside the null range (Poisson $+0.04$ with range $-0.28$ to $+0.34$, $p = 0.21$, and $-0.14$ with $-0.60$ to $+0.40$, $p = 0.07$; resampling $+0.07$
with $-0.11$ to $+0.24$, $p = 0.13$, and $+0.07$ with $-0.11$ to $+0.25$, $p = 0.06$). Restricting to the 43 facilities that are at cap in every optimum of equal cost in 2023 (a fixed set, so the null does not simulate the
selection), 55.8 per cent exceed their cap in 2024 against a null of 43.4 per cent (27.9 to 58.1; $p = 0.07$). The size of the exceedance is larger than the resampling null produces
(a median of 71 and 54 per cent of the cap, against 19 and 21 per cent), but this test does not separate growth in demand from a cap that was never binding, and we
claim neither. Where the CNES count of registered surgeons rose, at-cap facilities exceeded their cap in 79 and 63 per cent of cases against null rates of about 48 and 50 per cent; we treat this as
exploratory and unidentified: it is a registration count, it does not control for facility growth, and the urgent-volume placebo shows no such excess.

""")
edit(S4, [
("A subsampling variant (an $m$-out-of-$n$\nmultiplier bootstrap with $m = n/2$ and $0.7n$) did not help: its intervals cover the point estimate in one\nof six cases and its means sit higher still.",
 "A subsampling variant (an $m$-out-of-$n$\nmultiplier bootstrap with $m = n/2$ and $0.7n$) did not help: its intervals cover the point estimate in one\nof six cases and its means sit higher still. Two further runs of 100 draws each locate the source. With the weight dispersion halved (coefficient of variation 0.5 instead of 1) the upward shift of\nthe mean falls to 1.7, 2.0 and 2.7 points, about half, so its size depends on the weighting scheme and is not a property of the data alone; with $\\kappa$ and demand both held fixed the mean gap lies 0.5, 0.9 and\n0.7 points below the point estimate and the interval covers it. A count-matched (multinomial) variant was not run."),
("neither interval is exact, and we read the gap as\nabout 29 to 31 per cent with a plausible range from the low twenties to the high thirties.","neither interval is exact. The BCa endpoints, whose target quantiles cannot be estimated, are $[27.3, 29.3]$, $[28.1, 31.3]$ and $[28.2, 28.7]$ against the point estimates 28.8, 30.6 and 29.1, and are not used. We make no interval statement about the level beyond the construction ranges of Table~\\ref{tab:measure}."),
("None of the three\ndifferences is distinguishable from zero, at $p = 0.26$, $0.92$ and $0.41$ ($0.26$, $0.91$ and $0.41$\nwith the earlier stay-length shrinkage target). This is no detectable change, not evidence of equality: the\n95 per cent intervals on the differences are 8.2, 9.6 and 9.2 points wide,",
 "None of the three\ndifferences is distinguishable from zero. This is no detectable change, not evidence of equality: the\n95 per cent percentile intervals on the differences from this scheme, whose width depends on the weighting dispersion (below), are 8.2, 9.6 and 9.2 points wide,"),
])
print('batch 9 ok')

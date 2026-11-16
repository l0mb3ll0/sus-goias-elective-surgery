def between(path, start, end, new):
    s = open(path, encoding='utf-8').read(); a = s.index(start); b = s.index(end, a); open(path, 'w', encoding='utf-8').write(s[:a] + new + s[b:])
def edit(path, pairs):
    s = open(path, encoding='utf-8').read()
    for old, new in pairs:
        assert s.count(old) == 1, (path, s.count(old), old[:90]); s = s.replace(old, new)
    open(path, 'w', encoding='utf-8').write(s)
S4 = 'paper/section_4_model.tex'
edit(S4, [
("A subsampling variant (an $m$-out-of-$n$\nmultiplier bootstrap with $m = n/2$ and $0.7n$) did not help: its intervals cover the point estimate in one\nof six cases and its means sit higher still.",
 "A subsampling variant (an $m$-out-of-$n$\nmultiplier bootstrap with $m = n/2$ and $0.7n$) did not help: its intervals cover the point estimate in one\nof six cases and its means sit higher still. Two further runs of 100 draws each locate the source. With the weight dispersion halved (coefficient of variation 0.5 instead of 1) the upward shift of\nthe mean falls to 1.7, 2.0 and 2.7 points, about half, so its size depends on the weighting scheme and is not a property of the data alone; with $\\kappa$ and demand both held fixed the mean gap lies 0.5, 0.9 and\n0.7 points below the point estimate and the interval covers it. A count-matched (multinomial) variant was not run."),
("so neither is a valid confidence interval, and we read the gap as\nabout 29 to 31 per cent with a plausible range from the low twenties to the high thirties.","so neither is a valid confidence interval. The BCa endpoints, whose target quantiles cannot be estimated, are $[27.3, 29.3]$, $[28.1, 31.3]$ and $[28.2, 28.7]$ against the point estimates 28.8, 30.6 and 29.1, and are not used. We make no interval statement about the level beyond the construction ranges of Table~\\ref{tab:measure}."),
("None of the three\ndifferences is distinguishable from zero, at $p = 0.26$, $0.92$ and $0.41$ ($0.26$, $0.91$ and $0.41$\nwith the earlier stay-length shrinkage target). This is no detectable change, not evidence of equality: the\n95 per cent intervals on the differences are 8.2, 9.6 and 9.2 points wide,",
 "None of the three\ndifferences is distinguishable from zero. This is no detectable change, not evidence of equality: the\n95 per cent percentile intervals on the differences from this scheme, whose width depends on the weighting dispersion (below), are 8.2, 9.6 and 9.2 points wide,"),
])
print('batch 9 ok')

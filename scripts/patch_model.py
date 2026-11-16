import pathlib, json

M = pathlib.Path('paper/section_4_model.tex')
s = M.read_text()

OLD_HEAD = """We therefore formulate the allocation of elective surgery in Goias as a
capacitated assignment problem with a travel-penalised access objective, and use
it to ask a counterfactual question: given the bed-day capacity that physically
existed in each month, what allocation of elective cases across facilities would
have minimised unmet and displaced demand, and how far was the observed
allocation from that frontier?"""

NEW_HEAD = """We therefore formulate the allocation of elective surgery in Goias as a
capacitated assignment problem with a travel-penalised access objective, and use
it to ask a counterfactual question: given the facilities, beds and demonstrated
capability that physically existed, what allocation of elective cases would have
delivered the same volume at least travel cost, and how far was the observed
allocation from it?

The answer is that bed-day capacity was not the binding constraint. In the 2019
solution, mean utilisation of net surgical bed-days is 0.13 and only two of 131
facilities reach 95 per cent of their bed-day budget. The constraint that
mattered was allocative. This is the model's first substantive result, and it is
obtained before any counterfactual is computed: a system in which capacity binds
nowhere and volume is nonetheless low is a system limited by its routing rule,
not by its physical plant."""

assert s.count(OLD_HEAD) == 1
s = s.replace(OLD_HEAD, NEW_HEAD)

OLD_VAL = s[s.index('\\subsection{Validation}'):]
NEW_VAL = r"""\subsection{Results on 2019}

We solve the program on calendar 2019, the last full pre-pandemic year and the
baseline the empirical sections establish as the appropriate counterfactual. The
instance has 246 municipalities of residence, 131 facilities with positive
elective volume and non-zero net bed-day capacity, and 16 procedure subgroups,
giving 99{,}025 assignment variables over 2{,}294 demand cells. It solves to
optimality in seconds.

The observed 2019 allocation carries a mean travel cost of 0.835 region-crossings
per elective case. The unconstrained optimum delivers identical volume, with no
unmet demand, at 0.414: a reduction of 50.4 per cent.

This unconstrained figure should not be the headline, because with bed-days slack
almost everywhere the program is free to route demand to any facility within its
licensed scope, including facilities that performed the procedure only a handful
of times. We therefore impose an additional constraint capping each facility at a
multiple of the largest monthly elective caseload it actually achieved in 2019,
and report the result across multiples. Table~\ref{tab:modelrobust} gives the
ladder.

\begin{table}[t]
\centering
\caption{Optimal mean travel cost under increasingly tight caps on facility
throughput. The cap restricts each facility to a multiple of the largest monthly
elective caseload it achieved in 2019. All specifications serve the full observed
volume with zero unmet demand.}
\label{tab:modelrobust}
\begin{tabular}{lrr}
\toprule
Specification & Mean travel cost & Reduction \\
\midrule
Observed 2019 allocation & 0.835 & --- \\
Unconstrained optimum & 0.414 & 50.4\% \\
Cap at 3$\times$ observed monthly peak & 0.423 & 49.3\% \\
Cap at 2$\times$ observed monthly peak & 0.428 & 48.7\% \\
Cap at 1.5$\times$ observed monthly peak & 0.441 & 47.2\% \\
Cap at 1$\times$ observed monthly peak & 0.497 & 40.5\% \\
\bottomrule
\end{tabular}
\end{table}

The result to take is the last row. Constraining every facility to do no more in
any month than the most it demonstrably did in 2019, the same volume of elective
surgery could have been delivered at 0.497 region-crossings per case against an
observed 0.835, a reduction of 40.5 per cent. This specification requires no
assumption about latent capability: each facility is held to its own revealed
maximum. That four fifths of the unconstrained gain survives the binding cap is
itself evidence that the gap is not an artefact of unlimited reallocation.

Two qualifications belong with the number. Travel cost here is ordinal, counting
region crossings rather than kilometres, so the result says the observed
allocation required roughly 1.7 times as many region crossings as necessary, not
that patients travelled 1.7 times as far. [TODO: re-estimate with road or
great-circle distance between municipal seats as a robustness check.] And the
model routes on procedure subgroup and licensed scope alone; it does not observe
surgeon subspecialty, equipment, or the case-volume thresholds that clinical
governance may impose within a subgroup. Some part of the observed travel is
therefore a constraint the data does not record. The cap at observed peak
absorbs the facility-level version of this concern but not the
procedure-specific version.

\subsection{Validation and extension}

Three questions remain, and the data supports all three.

First, does the gap narrow after the 2022 reform? Solving the same program on
2023 capacity and demand tests whether the reform moved the system toward the
frontier. The reform was not designed as an optimisation, so convergence would
be evidence that the pre-2022 constraint was allocative and that the regulation
change relaxed it.

Second, how much of the realised 2022--23 volume gain was reachable on 2019
capacity? The model delivers 2019 volume more efficiently; the complementary
exercise raises volume until capacity binds, and asks in what year the observed
system reached the level 2019 capacity could already have supported.

Third, does the objective survive replacement? The travel-penalised formulation
is the defensible choice given that SIH records no queue registration date and
therefore no waiting time. [TODO: a freedom-of-information request for aggregate
queue extracts from the state regulation system is pending. If it returns, a
weighted-tardiness objective becomes estimable and should be reported alongside.]

[TODO: the saturation of state-administered facilities at approximately 151
elective cases per facility-month in 2025 is a candidate hard constraint distinct
from the bed-day budget, plausibly reflecting operating-room session capacity.
The 2019 solution does not reach it, but the 2023 and 2025 instances may.]
"""
s = s.replace(OLD_VAL, NEW_VAL)
M.write_text(s)
print('ok', len(s), 'chars')
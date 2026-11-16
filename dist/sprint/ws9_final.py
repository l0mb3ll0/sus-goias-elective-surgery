"""Final paper pass (item numbers from the author's brief): thesis, abstract, date, conclusion, section titles, causal wording, Section 3 fixes, convexity statement, sensitivity rows, appendix restructure."""
import re, json
def edit(path, pairs):
    s = open(path, encoding='utf-8').read()
    for old, new in pairs:
        assert s.count(old) == 1, (path, s.count(old), old[:90]); s = s.replace(old, new)
    open(path, 'w', encoding='utf-8').write(s)
def between(path, start, end, new, include_end=False):
    s = open(path, encoding='utf-8').read(); a = s.index(start); b = s.index(end, a) + (len(end) if include_end else 0); open(path, 'w', encoding='utf-8').write(s[:a] + new + s[b:])
r = json.load(open('dist/review/audit_final12.json'))
g = lambda y, k: 100*r[f'{y}|{k}']['gap']
INTRO = 'paper/section_1_intro.tex'; S4 = 'paper/section_4_model.tex'; S23 = 'paper/sections_2_3.tex'; MAIN = 'paper/main.tex'
# ---------- thesis and introduction ----------
edit(INTRO, [
("pre-2020 level by early 2022 and stopped there, and the post-2022 level has no\nprecedent in the panel. Something changed in how the state produced elective\nsurgery, and the change was large.\n",
 "pre-2020 level by early 2022 and stopped there, and the post-2022 level has no\nprecedent in the panel. This paper describes what that expansion consisted of and how far the resulting allocation sits from a transparent benchmark.\n"),
])
between(INTRO, "This paper asks which constraint had been binding.", "We formulate the allocation of elective surgery", """The paper asks four descriptive questions. Which facility-procedure pairs
account for the gain between 2019 and 2023, and had they operated before? Were hospital beds limiting? How far is the realised allocation from the optimum of a
linear program that sends each municipality's patients to the facilities at least travel cost, and did that distance change? And how much of what we compute
about the program's constraints survives our own tests? None of these questions identifies the cause of the expansion, and the paper does not.

""")
edit(INTRO, [("Five findings follow, each stated with the tests that bound it.","Four findings follow, each stated with the tests that bound it.")])
FIND = r"""First, most of the facility-procedure pairs behind the change between 2019 and 2023 had operated before. Of the 284 pairs present in 2023 and absent in 2019,
carrying 27.5 per cent of 2023 elective volume, 195 are active in some month of 2020 to 2022 and carry 94.2 per cent of the cases, so 25.9 of the 27.5 points are
capability that lapsed and returned; 52 per cent by volume are at facilities absent from SIH altogether, or 84 per cent on the broader test of absence from its elective subset.
With the 2019 pairs 11.5 per cent of the 2023 demand cannot be served; with the 2023 pairs all of it is served. We make no attribution of the change between
pairs and capacity (Table~\ref{tab:decomp}).

Second, beds were slack in aggregate and limiting at a few facilities. Aggregate utilisation of net surgical bed-days in the optimal solution is 0.132 in 2019,
0.178 in 2023 and 0.215 in 2025 (0.06 to 0.09 when every admission is netted against all inpatient beds), and one, three and six of 131, 131 and 145 facilities use
more than 95 per cent of their bed-day budget. Dropping the bed row raises the benchmark gap by 0.0, 3.5 and 2.4 points, because 1, 3 and 5 facilities would then exceed their budget.
Beds are counted at full occupancy; operating-room sessions, surgeons and anaesthetists are not modelled.

Third, a transparent benchmark shows no detectable change in allocation, and its level depends on construction. The optimum under the peak-volume cap needs 28.8, 30.6 and 29.1 per cent less travel than the observed
allocation used (the gap is (observed $-$ optimum) / observed; 29 per cent less corresponds to about 41 per cent above the optimum on the index), and differences between years are not distinguishable from zero, with
intervals about nine points wide, so this is no detectable change and not evidence of equality. The level ranges from 23 to 55 per cent across cost codings, origin zone systems (including the official health regions), bed definitions, estimation windows
and caps deflated for counting noise, and is 6 per cent in 2019 when each pair is held to its annual mean volume (Table~\ref{tab:measure}). Observed mean travel did not fall: it rose from 0.835 to 0.846 to 0.906.

Fourth, what we can say about the constraints is limited. The cap is a peak, not a demonstrated ceiling. The number of facilities at their cap is not identified (in 2023 a proved minimum of 44 of 131 and a largest value found of 107 across optima of equal cost);
disjointness of bed-bound and cap-bound facilities is a property of the reported optimum, and an overlap is attainable at other optima in 2019 and 2025; the cap test is a low-power non-rejection; and the explanation ``flatter monthly series'' for the fall in aggregate cap over demand is not supported (Section~\ref{sec:capnull}).
Goi\'as residents treated in the Federal District are missing from the data, so we draw no conclusion about the Entorno. An exploratory extension that lets the program open new pairs is in Appendix~\ref{app:explore}.

"""
between(INTRO, "First, physical", "Two features of the setting make", "") if "First, physical" in open(INTRO).read() else None
s = open(INTRO, encoding='utf-8').read()
a = s.index("First, beds were slack in aggregate"); b = s.index("The implication for modelling is limited.")
open(INTRO, 'w', encoding='utf-8').write(s[:a] + FIND + s[b:])
edit(INTRO, [("checked from code. We do not claim that the allocation of surgery rather than queue management is the policy lever, and we do not date\nor attribute the expansion to any policy.","checked from code once a clean-checkout run passes (Section~\\ref{sec:limits}). We do not claim that the allocation of surgery rather than queue management is the policy lever, and we do not date\nor attribute the expansion to any policy.")]) if "checked from code. We do not claim" in open(INTRO).read() else print('intro claim sentence differs')
# ---------- abstract, date ----------
ABS = r"""Elective surgery in the Brazilian state of Goi\'as roughly doubled between 2019 and 2025 (71 per cent by 2023).
Using SUS-financed hospital authorisations processed in Goi\'as, we describe what the expansion consisted of and benchmark the allocation against a linear program.
Most facility-procedure pairs behind the 2019 to 2023 gain had operated before: 195 of 284 were active in 2020 to 2022.
Beds were slack in aggregate (utilisation 0.13 to 0.22) and limiting at a few facilities: removing the bed row raises the benchmark gap by 0 to 3.5 points.
The benchmark shows no detectable change in allocation across 2019, 2023 and 2025, but its level, 29 to 31 per cent less travel than observed, depends on construction: 23 to 55 per cent across cost codings,
zone systems, bed definitions, windows and caps, and 6 per cent in 2019 with caps at annual mean volume.
The number of facilities at their cap is not identified, and tests of the cap are low-power.
Goi\'as residents treated in the Federal District are missing from the data.
Code and checks accompany the paper."""
between(MAIN, "Elective surgical volume in the Brazilian state of Goi", "\\end{abstract}", ABS + "\n")
edit(MAIN, [("\\date{August 2026}", "\\date{November 2026}")])
# ---------- section titles and wording ----------
edit(S4, [
("\\subsection{Decomposing the frontier: options against capacity}", "\\subsection{How the attainable frontier moved between 2019 and 2023}"),
("\\subsection{The two constraints bind on almost disjoint facilities}", "\\subsection{Beds and the peak-volume cap at the reported optimum}"),
("The two diverge afterwards, in a way that illustrates the mechanism at the scale\nof a single municipality.","The two diverge afterwards, in a way that illustrates the pattern at the scale\nof a single municipality."),
("This is the priced object the paper's policy claim needs, and it\nrequires no assumption about what opening a pair would cost.","This is the priced object of the exploratory extension in Appendix~\\ref{app:explore}, and it\nrequires no assumption about what opening a pair would cost."),
("The largest single\nmisallocation of the first two years closed, and it closed in the direction the\nmodel identifies, with capability arriving where the patients already were. We do\nnot claim the model caused this. We claim the quantity it ranks is one that\nmoves.","The largest single\ndistance from the optimum of the first two years closed, in the direction of the\nmodel's ranking, with capability arriving where the patients already were. We do\nnot claim the model caused this; the quantity it ranks is one that\nmoves."),
("A count-matched (multinomial) variant was not run.","A count-matched (multinomial) variant was not run. That resampling a maximum raises the gap is an empirical result for these data and not a theorem; the convexity argument (the optimal value is convex in demand, so demand perturbation lowers the gap) applies to demand with the observed baseline held fixed, which is the $\\kappa$-fixed column of Table~\\ref{tab:bootvar}."),
])
edit(S23, [
("The two steps are driven by different facilities.","The two steps involve different sets of facilities."),
("\\subsection{The response was highly unequal across facilities}","\\subsection{Growth was highly unequal across facilities}"),
("A\nchange in the allocation rule activated part of that capacity, and the activation\nwas durable: facilities that expanded in 2022 were still operating at their new\nvolumes in 2025. The natural question is how much of the gain a deliberately\noptimised assignment would have captured, and how much sooner.","Facilities that expanded in 2022 were still operating at their new volumes in 2025, and\nwe do not identify what caused the expansion. The natural question is how far the realised allocation sits from a benchmark assignment."),
("was scarce was capability rather than beds.","reports beds slack in aggregate and limiting at a few facilities."),
("membership is pre-determined with respect to the reform:","membership is pre-determined with respect to the 2022 change:"),
("\\paragraph{The transfer event is not the mechanism.} Comparing the eleven months\nbefore the break (December 2021 to July 2022)","\\paragraph{Transfer status does not account for the growth.} Comparing the eight months\nbefore the break (December 2021 to July 2022)"),
("predicts the magnitude of the response;","predicts the magnitude of growth;"),
("mechanism the rest of this subsection documents is therefore confirmed by the\nconvergence rather than merely asserted from a single cross-section.","pattern the rest of this subsection documents is therefore consistent with the\nconvergence and not only with a single cross-section."),
("therefore describe the reform by its effect rather than by its instrument.","therefore describe the change by its effect rather than by its instrument."),
("July-to-August increase of 1{,}210 elective cases decomposes into 1{,}205 from\nfacilities already active and 8 from facilities not active in that window.","July-to-August increase of 1{,}215 elective cases decomposes into 1{,}210 from\nfacilities already active and 5 from facilities not active in that window."),
("the\ncorresponding acts of SES-GO have not been read from the Di\\'ario Oficial, and we","the\ncorresponding acts of SES-GO have not been read from the Di\\'ario Oficial (one, Resolu\\c{c}\\~ao CIB n.\\ 111/2021, is described in Section~\\ref{sec:data}), and we"),
("The break dates below are recovered","The break dates above are recovered"),
])
print('main edits ok')

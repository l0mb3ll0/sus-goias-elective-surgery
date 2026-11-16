"""Paper edits batch 2 (audit item 12 and related text): strict '>' wording, unsourced claims removed, 'exact' removed, ordinal-cost ratio removed, placement test wording, top-15 denominators, 'headroom consumed'."""
import re
def edit(path, pairs):
    s = open(path, encoding='utf-8').read()
    for old, new in pairs:
        assert s.count(old) == 1, (path, s.count(old), old[:80])
        s = s.replace(old, new)
    open(path, 'w', encoding='utf-8').write(s)
edit('paper/section_4_model.tex', [
("A pair is counted as binding when it carries at least 95 per cent\nof its cap.", "A pair is counted as binding when it carries more than 95 per cent\nof its cap."),
("it is infeasible at any aggregate cost, not merely an expensive one. No\nmunicipality's best attainable cost exceeds 2.25 when capacity is ignored, so what\nmakes the requirement impossible is not that the options are too far away but that\nthe nearer ones are already at their caps. Eighteen municipalities cannot average\nbelow 2.0 even with unlimited capacity at every facility in scope.",
 "it is infeasible at any aggregate cost, not merely an expensive one. Every\nvalue of the ceiling tried below 2.5 (2.25, 2.0 and lower) is infeasible at full service. We did not\ntest whether that is because the nearer options are at their caps or because the options are too\nfar away, so no explanation is offered."),
("This specification requires no assumption about latent capability: each\nfacility is held to its own revealed maximum.",
 "This specification needs no outside estimate of capacity: each facility is held to its own\npeak 3-month average volume. It does assume that this historical peak is a feasible level for the unit."),
("Travel cost here is ordinal, counting\nregion crossings rather than kilometres, so the result says the observed\nallocation required roughly 1.4 times as many region crossings as necessary,\nbetween 1.40 and 1.44 across the three years, not that patients travelled 1.4\ntimes as far.",
 "Travel cost here is an ordinal index (0 to 3), not kilometres and not a count of region\ncrossings, so a ratio of its means has no distance interpretation; the gap is a statement about\nthe index, and its level depends on the coding (Section~\\ref{sec:capnull})."),
("That is a\nusable negative result rather than an underpowered one, though it does not exclude\na modest tilt of 20 or 30 per cent above chance.",
 "The test's minimum detectable lift is about 1.8 to 1.9 times chance, so it does not exclude\na tilt of up to roughly that size, and pairs that are new in the later year (entrants) are excluded from it\nby construction."),
])
s = open('paper/section_4_model.tex', encoding='utf-8').read()
s = re.sub(r'facilities reaching 95 per cent of their bed-day budget', 'facilities using more than 95 per cent of their bed-day budget', s)
s = re.sub(r'facilities reach 95 per cent of their bed-day budget', 'facilities use more than 95 per cent of their bed-day budget', s)
s = s.replace("The fifteen largest origins carry 44.6\nper cent of it.", "The fifteen largest origins carry 44.6\nper cent of net total excess (44.3 per cent of the sum of the positive entries, the denominator\nused when negative entries are set aside).")
s = s.replace("fifteen-largest shares of 42.5 and 49.9 per cent.", "fifteen-largest shares of 42.5 and 49.9 per cent of net excess (42.5 and 47.3 per cent of the sum of positive entries).")
open('paper/section_4_model.tex', 'w', encoding='utf-8').write(s)
edit('paper/main.tex', [
("fifteen of\n246 municipalities carry 44.6 per cent of it,", "fifteen of\n246 municipalities carry 44.6 per cent of net excess travel,"),
("Six years of expansion consumed headroom under the peak-volume cap without approaching", "Over six years of expansion the ratio of the peak-volume cap to demand fell, without approaching"),
])
s = open('paper/main.tex', encoding='utf-8').read(); s = s.replace('facilities reach 95 per cent of their', 'facilities use more than 95 per cent of their'); open('paper/main.tex', 'w', encoding='utf-8').write(s)
s = open('paper/section_1_intro.tex', encoding='utf-8').read()
s = s.replace("Six years of expansion consumed headroom under the peak-volume cap without approaching the\nphysical limit.", "Over six years of expansion the ratio of the peak-volume cap to demand fell, without the system approaching the\nphysical limit.")
s = s.replace('facilities reach their bed-day budget', 'facilities use more than 95 per cent of their bed-day budget')
s = s.replace('facilities reaching 95 per cent of their bed-day budget', 'facilities using more than 95 per cent of their bed-day budget')
open('paper/section_1_intro.tex', 'w', encoding='utf-8').write(s)
print('batch 2 ok')

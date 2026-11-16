"""Final check (WS10): numbers printed in the compiled PDF's new text against paper/numbers.json. Each row: (label, string expected in the PDF text, store value formatted)."""
import json, re, pypdf
d = json.load(open('paper/numbers.json'))
t = re.sub(r'\s+', ' ', ' '.join((p.extract_text() or '') for p in pypdf.PdfReader('paper/main.pdf').pages)).replace('−', '-')
f = d['optimal_face']; f2 = d['optimal_face_v2']; cb = d['audit_cap_bracket']; bv = d['bootstrap_variants']['shrink_all_records']; ct = d['cap_test_null']['transitions']; rs = d['cap_test_resampling_null']['transitions']
pc = lambda x, n=1: f'{100*x:.{n}f}'
rows = [
 ('face v2 min cap', f"{round(f2['2019']['milp']['cap_min@0.95']['obj'])} of 131 in 2019, {round(f2['2023']['milp']['cap_min@0.95']['obj'])} of 131 in 2023 and {round(f2['2025']['milp']['cap_min@0.95']['obj'])} of 145", None),
 ('face v2 max found', f"{round(-f2['2019']['milp']['cap_max@0.95']['obj'])}, {round(-f2['2023']['milp']['cap_max@0.95']['obj'])} and {round(-f2['2025']['milp']['cap_max@0.95']['obj'])}", None),
 ('bed row', '0.0, 3.5 and 2.4 points', None), ('contrast poisson', f"{d['cap_test_contrast']['poisson']['2023->2024']['contrast_null_mean']:+.2f}".replace('+','+') , None),
 ('cap test Poisson 2023', f"{pc(ct['2023->2024']['fac_at_cap']['null_exceed_mean'])} per cent", None), ('cap test resampling 2023', f"{pc(rs['2023->2024']['null_exceed_mean'])} per cent", None),
 ('boot shift kfix', f"{abs(bv['2019']['kfix']['shift_pp']):.1f}, {abs(bv['2023']['kfix']['shift_pp']):.1f} and {abs(bv['2025']['kfix']['shift_pp']):.1f}", None),
 ('boot shift dfix', f"{bv['2019']['dfix']['shift_pp']:.1f}, {bv['2023']['dfix']['shift_pp']:.1f} and {bv['2025']['dfix']['shift_pp']:.1f}", None),
 ('noise-deflated gap', f"{pc(cb['2019']['kappa_noise_deflated']['gap'])}, {pc(cb['2023']['kappa_noise_deflated']['gap'])} and {pc(cb['2025']['kappa_noise_deflated']['gap'])} per cent", None),
 ('annual-mean gap 2019', f"{pc(cb['2019']['kappa_mean']['gap'])} per cent", None),
 ('face util 2019', f"{cb['2019']['bed_util_face']['min']:.3f} to {cb['2019']['bed_util_face']['max']:.3f}", None),
 ('DF Entorno share 2023', f"{pc(d['crossborder_DF']['2023|3 named Entorno']['share_in_DF'],0)} per cent", None),
 ('overlap p 2025', f"{d['disjointness_overlap_test']['elective']['2025']['p_overlap_le_obs']:.3f}", None),
]
bad = 0
for label, s, _ in rows:
    ok = s in t; bad += (not ok); print(('PASS ' if ok else 'FAIL ') + label + f'  [{s}]')
print('\nFAIL count', bad)

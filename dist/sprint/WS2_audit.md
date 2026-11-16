# WS2 number audit (partial; resumable)

## 76 vs 77 at-cap facilities (2023): RECONCILED
- Stored `capbound_n` = 77 comes from `paper/fac_2023_roll3.parquet` (scripts/capability.py, cap_use > 0.95).
- A fresh solve on the bootstrap's Year builder gives 76. Same kappa (max abs diff 0.0), same demand.
- 57 of 131 facilities have a different served/kappa between the two solves, so these are different
  vertices of the optimal face (degenerate LP), not a rounding artefact. In the fresh solve the 77th
  facility (CNES 9680977) sits at 0.94987, 0.00013 under the line; in the stored solve it is 0.9837.
- Bounds across alternate optima at the optimum objective: see alt_optima.txt (dist/review).
  Caution: the count is discontinuous at 0.95, and the minimiser parks many units exactly on 0.95
  (44 strict vs 74 at >= 0.95-1e-6). The headline "77 at cap" is one arbitrary vertex of a face on which the count varies.

## 0.006 pp and 0.001 pp gap differences: RECONCILED EXACTLY
- Bootstrap point gap vs stored: 30.6006 vs 30.5950 (2023, diff 0.0056 pp); 29.1278 vs 29.1290 (2025, diff 0.0012 pp).
- Cause: stay-length shrinkage. model_run.py shrinks pair mean LOS toward the procedure mean over ALL
  elective in-state records; bootstrap_paired.py's Year.gap uses the procedure mean over records at the
  131 model facilities only (pkv_J). Re-solving with the all-record procedure mean reproduces the stored
  travel to 1e-15 in both years (2023: 0.587325555919073; 2025: 0.6418849551102536 vs 0.6418849551102537).
- It is not LP degeneracy (objectives differ, travel moves in opposite directions in the two years).
- Recommendation (DECISIONS.md): align bootstrap_paired.py to model_run.py and rerun the 340 draws (compute only).
  Effect is below 0.01 pp on the gap; paper tables are unaffected.

## Surgeon figures: PARTLY TRACED, two figures untraceable
Source: scripts/sp_analysis.py on the SIH SP table (data/interim/sih_sp), via dist/review/run_sp_analysis.py.
Rerun by window (outputs dist/sprint/ws2_sp_2024.txt, ws2_sp_2025.txt, dist/review/sp_analysis_output.txt):
| figure | window | source line |
| top decile of 225225 surgeons carries 63.5% of cholecystectomy volume (46 of 463 surgeons) | 2024 only (12 mo) | ws2_sp_2024.txt:37 |
| same, 68.6% (58 of 585) | 2024-01..2025-12 (24 mo pooled) | sp_analysis_output.txt:51 |
| surgeons at >1 facility 25.7% (119 of 463) | 2024 only | ws2_sp_2024.txt:62 |
| same, 29.2% (171 of 585) | 24 months pooled | sp_analysis_output.txt:76 |
Notes: 2025 alone also gives 25.7% (129 of 501), a coincidence. Pooled shares rise with window length
(more months, more chances to appear at a second facility; surgeons also turn over), so the two sets are
not competing estimates, they are different windows. State the window with each.
- "23 of 258" and "23 of 151": NOT FOUND in the repo, paper, numbers.json, any output, or git history
  (git log -S). Marked [VERIFY]. Do not use until a generating script is identified.
- None of these surgeon figures are in paper/*.tex or numbers.json at HEAD. Paper only says the
  surgeon-month analysis "has not been made" (sections_2_3.tex:596), which is now stale.

## CBO coverage 32.6-34.5% (what it is)
scripts/sp_analysis.py:79-87. Per month, cbo_pct = 100 * (rows with SP_PF_CBO != '000000') / (all SP act rows).
Unit: SP act rows (one row per professional-act line attached to an AIH), ALL procedures, ALL facilities in
Goias, by month. It is NOT the share of AIHs, surgeries, or surgeons that have an identified surgeon.
CBO and DOC (CNS) populate on exactly the same rows (script line 89). Window 2024-01..2025-12.
AIH-level coverage for group-04 cases and for 225225 specifically: see WS2_coverage.txt (computed next).

## CBO coverage: RESOLVED (dist/sprint/WS2_coverage.txt, script ws2_coverage.py; aggregates only)
1. 32.6-34.5% is the monthly share of SP ACT ROWS (all procedures, all Goias facilities) whose professional
   id is populated. Row-level, not AIH-level and not surgeon-level.
2. It is low by construction. SP_ATOPROF act types 02, 08, 07 (47%, 7%, 2% of rows: hospital service /
   non-professional lines) are ~0% identified; types 03 and 04 (28% and 16% of rows, the professional acts)
   are 79% and 69% identified. The ~33% is mostly the share of rows that are professional acts.
3. At the AIH level coverage is complete in the sense that matters for "is a professional visible":
   100.0% of the 181,839 elective group-04 AIHs (2024-25) are in SP and 100.0% carry >=1 identified
   professional (median 3 identified rows per AIH); all 268 facilities have identified rows.
4. Do the surgeon figures rest only on the 32.6-34.5%? No, and that share is not their denominator.
   They rest on rows with CBO 225225 (general surgeon) and an identified CNS:
   - cholecystectomy (the 362 / 19,196-AIH analysis): 93.8% of 20,457 cholecystectomy AIHs carry an
     identified 225225. Well covered, 6.2% of AIHs have no identified general surgeon.
   - "all group-04 elective" (570 surgeons): only 30.9% of elective group-04 AIHs carry an identified
     225225. The other specialties (225270 orthopaedics, 225250 gynaecology, etc.) are excluded, and
     225151 (anaesthesia) is the most frequent CBO on these AIHs (31% of identified rows; 225225 is 13%).
     So that analysis describes general surgeons only, and its label is wrong or at least misleading.
   - A CBO on a row says the professional is registered in that occupation, not that they operated; 51.3% of
     225225 surgeons carry a second CBO (sp_analysis_output.txt B0). Surgeon identity is inferred, not observed.
   - Claim limits: concentration (top decile share) and multi-facility share are statements about
     identified 225225 professionals on the AIHs billed, window-dependent, not about all operating surgeons.
   Wording change recommended: say "AIHs with an identified general surgeon (CBO 225225)", give the window, give 93.8%.

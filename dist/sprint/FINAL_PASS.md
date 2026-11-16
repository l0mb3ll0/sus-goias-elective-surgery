# FINAL_PASS: final-pass report (2026-11-15; corrected 2026-11-15 after the correction round)

**Branch/worktree:** `final/nov-2026` in `~/sos-final`, created from `6f3671757c8dae3e65cc34de38686f652633851f` (research2/goias-robustness, which contains sprint/nov-2026 `fca2890`). Committed locally as 23bcd91 and 27771a3, and a third local commit for the second correction round (`git log -3` on `final/nov-2026`); not pushed, not merged. Original trees untouched.

## Gate: 284-pair reconciliation. CLOSES.
Re-derived from the RD files (`dist/review/reconcile_final_pass.py`, output `reconcile_final_pass.txt`; basis = all-resident elective surgical AIH, the combination that reproduces 574/666/284/192 and 21,845). New pairs by the panel's own `TP_GESTAO` group (`scripts/panel_v2.py`):

| group | pairs | cases |
|---|---|---|
| municipal-administered | 191 | 13,326 |
| always state | 43 | 6,330 |
| transferred | 42 | 2,096 |
| *subtotal* | *276* | *21,752* |
| facility with no CNES record before Sep 2022 ("unknown", CNES 4063112: subgroups 0407, 0409, 0415) | 3 | 33 |
| excluded April 2022 switch (CNES 5419662: 0401, 0403, 0406, 0409, 0412) | 5 | 60 |
| **total** | **284** | **21,845** |

The residual 8 pairs / 93 cases are the two facilities the paper (Sec. 2.3) already places outside the three groups. Classified by the documented rule; nothing invented. Paper text now states this.

## Other reconciliations (all from the same script unless noted)
- **"All 61 sums to 59":** 14+13+10+22 = 59 facilities with a defined growth ratio; 2 of the 61 are undefined (`scripts.subset_sensitivity`, n_defined 59, undefined 2). Text fixed.
- **Sec. 3.2 / Appendix B counts: all reproduce.** 195 of 284 active in 2020–22; 20,568 of 21,845 cases (94.2%); 25.9 and 1.6 points of the 27.5; median 5 active months, median 10 cases, 13,132 prior cases; 0407 78.1%/97.2%, 0409 80.0%/87.2%, 0408 78.9%/99.8%; 7,401 / 4,094 / 3,490 cases; 62 of 192 lost pairs active again in 2024–25. Note: the 2020–22 and 2019–22 windows give identical results because the pairs are absent in calendar 2019.
- **Table 1 decimals:** `check_tables` passes all 104 printed cells at printed precision (Table 1 included). I found no decimal discrepancy to fix; I did not locate the specific referee item beyond that.
- **Hamilton 1982 / White 1988:** text (Sec. 1) says Hamilton compared observed commuting with a monocentric model and White with the cost-minimising assignment of households to residences given observed densities. Consistent with the titles and `refs.json` (verified: true). I did not re-read the original papers in this pass.
- **Health-region mapping:** Sec. 2/3 already states it was read from the SES-GO web page, not from the CIB resolution (Res. 840/2025 was read afterwards and matches region/macro/polo counts only; see `dist/research2/RESULTS.md`). No change needed.
- **§3.1 phrases** ("a lag consistent with the time required to convert a federal financing instrument…", "In each case the break is recovered from the data alone"): **they were present**. The earlier check was wrong because the phrases wrap across lines in the .tex source and the PDF text and a line-by-line grep missed them. They are replaced in the correction round (see CHANGELOG, 'Correction round'); verification now collapses line breaks before searching.

## Addendum 3 and Section 4.8
Addendum 3 tested health-region (and macro/region-pair) shares on the optimal face; it did not examine municipalities. I judged that it does bear on 4.8 directionally (municipal ranks come from one optimum, a finer level than the tested health regions), so ONE sentence was added citing it, with no numbers. It does not contradict any paper number. Road-distance files remain untracked and out of the branch.

## Edits
All logged in `dist/sprint/CHANGELOG.md` (final-pass block). Patch `abstract_wording_fixes.patch` applied with `git apply`, no conflicts. Other edits: "reactivation" removed (Sec. 3 intermittency sentence); 4.8 "stable"/"persistent and identifiable" softened; A.1 "misallocation" reworded; gate and "61/59" text; declarations (funding none, competing interests none, AI statement verbatim, ethics paragraph verbatim + `% UPDATE WHEN IRB REPLIES`). README/LICENSE/pyproject copied from nested repo (**LICENSE is MIT** for code; paper text and figures all rights reserved). README rewritten. `requirements-snapshot.txt` added (Python 3.12.13, HiGHS 1.12.0 bundled in SciPy 1.18.0). `numbers.json` unchanged by the final pass (git diff empty; the three `complexity_2023` rows changed earlier on the sprint branch, see CHANGELOG).

## Tests / rebuild (on final tree)
`main.pdf` 36 pages, 0 undefined references, 0 citation warnings; `check_tables` PASS (104 cells); `check_coverage` PASS (70 generated, 3 hardcoded, 7 orphan allowed); `check_build_inputs` PASS (9); `final_number_check.py` 0 FAIL; every number in the abstract is found in the paper text. **I did not re-run `scripts.reproduce`** (it needs `data/interim` and rewrites stored files); the README cites the last full run (`dist/sprint/repro_run4.txt`: 25 steps, 3,724 values, 0 differing) and I verified the command list with `--list`. The `reproduce.py` instructions in the README are therefore verified by inspection plus that log, not by a fresh run.

## Deliverables
- `paper/main.pdf` copied to `Downloads/02 Research - SUS (loose files)/final/main.pdf` (new folder, nothing overwritten) together with `abstract_2page_v2.md` (~600 words). SHA-256 prefix of the PDF printed at copy time matches.

## Commit 27771a3 (final corrections, first correction round)
Control wording ("It is not a control group"; PNRF/PMAE described as temporal coincidences), cost wording ("higher mean cost index", "lower the regional cost score"), tubal ligation re-derived (`dist/review/tubal_check.py`: 347 of 414 at 16 of 35 facilities), "historical peak" labels in tables and `check_tables`, an external-validity sentence in Limitations, the staged-policy sentence in Appendix B.1, and header/status corrections in this file and the ledger. Rows are in the CHANGELOG final-pass block.

## Second correction round (after the second outside review)
- Applied the review's 10-item verdict list, its Section 4 cross-reference fixes and its Section 6 abstract changes, with amendments A to H; every edit is a row in the CHANGELOG block "Final correction round 2".
- **Check C** (`dist/review/obs_feasibility.py`, output `obs_feasibility.json`): the observed allocation, aggregated to municipality x facility x subgroup on the same demand cells and J, has 0 pair-cap and 0 facility-total violations in 2019, 2023 and 2025, and exceeds the bed-day row at 1, 2 and 4 facilities. The Section 4.4 sentence therefore went in as specified. Additional fact, not in the paper sentence: the observed allocation covers only 99.95 / 94.4 / 91.3 per cent of in-state demand (records at facilities outside J are not in it).
- **k = 20 breakdown** (central level, `paper/ksweep_2025_m1.json`): 9 oncological surgery (0416), 4 circulatory system (0406), 4 musculoskeletal (0408), 3 other surgeries (0415); municipalities Luziania 4, Rio Verde 4, Ceres 2, Aparecida de Goiania 2, six others 1 each. `numbers.json` stores only the 12-pair core chosen at all three levels (6 x 0416, 3 x 0406, 3 x 0408; no 0401). The earlier "nine in skin and subcutaneous tissue" was 0416 oncological surgery.
- **Number checks against `numbers.json`** (amendment A): 0.2146 = `capability/2025/bed_util` 0.21455 -> abstract and 2-page abstract 0.21 (done). **Disagreement with the review:** Section 4.7's "0.06 to 0.22" is a range over fresh solves of each bed definition (maximum 0.2173, `audit_timing_beds_coverage` 2025|paper), so it stays 0.22 and is now labelled "each definition solved afresh". 1,668.49 and 2,211.45 (`flows_panel/{2023,2025}/excess_total`) -> 1,668 and 2,211. -0.0448 (`subset_sensitivity/waves_reported49/pearson`) -> -0.04. 0.652 (`table2[7].post`) and +38.4 (Table 7) -> 0.652 and 38 per cent. `audit_timing_beds_coverage` 2025|bed_all_30 `bed_bound` = 1 (0 only with actual days) -> "at most one". Stored solution (`capability`): at cap 79 / 77 / 105, bed-bound 1 / 3 / 6, which is now the single meaning of "reported optimum"; fresh solve (`bed_row_test/base`, `optimal_face_v2/reported_vertex`): 72 / 75 / 103 and 1 / 3 / 5.
- **SIGTAP** checked against `data/ref/sigtap_subgrupos.csv` (DATASUS TabelaUnificada 202607): 0401 pequenas cirurgias e cirurgias de pele, tecido subcutaneo e mucosa; 0406 aparelho circulatorio; 0407 aparelho digestivo, orgaos anexos e parede abdominal; 0408 sistema osteomuscular; 0409 aparelho geniturinario; 0415 outras cirurgias; 0416 cirurgia em oncologia. Labels fixed in Section 3.2, Appendix A.2 and Appendix B.1.
- Figure 2 re-rendered (title "excess ordinal cost") by `scripts/worst_served_map.py` from stored files; no new analysis. Not run: `scripts.reproduce`.

### Trace table (amendment F; resolved in correction round 3)
Re-derived by `dist/review/untraced_numbers.py` (output `untraced_numbers.json`), stored as new `numbers.json` keys by `scripts/store_untraced_numbers.py`; all are now GENERATED in `check_coverage`.
| Value | Where | Source | Result |
|---|---|---|---|
| 36.6 / 39.7 / 31.6 per cent; 38.8, 31.5, 49.6 km; 0.634 and 0.595 | 4.1 | `paper/model_metric_{2019,2023,2025}.json` from `scripts/model_metric.py` (the `numbers.json` key was deleted as superseded) | traced, match; not in `numbers.json` |
| 42.7 / 70.3 / 30.4 per cent | 4 opening | `cross_municipal_share` (2019 to 2025, all 430,802 elective admissions) | 42.70 / 70.32 / 30.41: reproduces; window added to the text |
| about 151 cases per facility-month | A.3 | `state_plateau_2025` (state-administered facility-months with elective volume, 2025-04 to 2025-12) | 150.56: reproduces; definition added to the text |
| 5,986 per month and 0.648 | 3.1 | `ratio_window_2022_08` (2022-08 to 2023-07) | 5,985.8 and 0.6478: reproduce; text unchanged |
| mean displacements "to twelve months" | 3.3 | `entry_displacement` | 12.13 (D1 vs D2), 6.33, 7.51: twelve is the maximum, so the text now says "from six to twelve months" |

## Backups (pre-edit)
Local `~/sos-backups-20261115/` and OneDrive `Research Backups/Goias_2026-11-15_final-pass-prebackup/` (SHA256SUMS.txt in each). sos-main 3c52717877601cd1…, nested 2c148655… (full list in SHA256SUMS.txt). **Check the OneDrive sync icon; I have not confirmed sync.**

## Nested repo differences (not copied; main repo versions authoritative)
Nested vs main line differences: `check_tables.py` 6, `check_build_inputs.py` 6, `hooks/pre-commit` 6 (nested calls `python`, main `.venv/bin/python`), `bootstrap_paired.py` 237, `.gitignore` 22. Nested paper (Aug 26) is older and lacks appendix.tex.

## Release exclusion list (future public release = fresh export, no history)
Exclude: `data/pilot/`, `test.dbc`, all logs (`*.log`, `dist/sprint/repro_logs*`, `dist/sprint/WS7_pilot_BA*.txt`, `dist/research2/face_cont*.log`), `__pycache__/` and `*.pyc`, `dist/research2/_dl/`, `.venv`, `data/raw`, `data/interim`, any file with `/home/…` or `/mnt/c/Users` paths (scrub or drop), and the author's institutional email in commit metadata (no history is exported). The private backup keeps full history. No history was rewritten; nothing was `git rm`'d.

## Open items
1. Committed locally on final/nov-2026 (not pushed); see the status line at the top.
2. Ethics paragraph says an IRB determination "has been requested"; update when it replies.
3. Title changed per author decision (see CHANGELOG); applies to paper, README, pyproject and abstract v2.
4. `numbers.json` keys named `share_2023_reactivation` / `share_2023_genuinely_new` retain the old term (internal keys, not printed; changing them would alter numbers.json).
5. Left as is after review: "template" (Sec. 1 practical contribution), "binding constraint" for Entorno origins (hedged in context), Appendix B "the dispersion is the finding".
6. Funding/competing interests set to "None" per your standing instruction.
7. Old `dist/sprint/DRAFT_abstract_2page.md` still contains "reactivation" (a draft, superseded by v2; not edited).
8. The paper's Declarations still contain `[URL]` / `[DOI]` placeholders (the 2-page abstract now says "Paper and code available on request."). They must be filled or removed before the paper goes anywhere.
9. Security findings: see `dist/review/SECURITY_AUDIT.md`; no credentials found.

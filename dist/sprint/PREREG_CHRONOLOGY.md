# Chronology of the stated rules (system clock EST, 2026-11-04; from git commit times and file modification times)

Committed to git BEFORE any result file for that test existed: the Poisson cap-test null rule (WS4_prereg.md) and round-3 T1-T3 (PREREG_round3.md: face analysis, resampling null, m-out-of-n bootstrap). Everything else was written in the same step as the run, during it, after partial information, or cannot be verified from timestamps. Rules were also changed by amendment after first sight of data where noted in the files themselves (PREREG_round3.md T4 amendment; PREREG_round4.md item 9 clarification).

| rule file | first commit of the rule file | modification time of a result file | result file |
|---|---|---|---|
| WS4_prereg.md | 00:38:00 | 00:45:34 | dist/review/null_cap.txt |
| PREREG_round3.md | 07:23:51 | 08:34:48 | dist/review/face_2019.json |
| PREREG_round3.md | 07:23:51 | 08:45:25 | dist/review/null_cap_resample_v2.json |
| PREREG_round3.md | 07:23:51 | 08:33:43 | dist/review/boot_mn.txt |
| WS4b_kurgent_prereg.md | 07:10:48 | 07:10:20 | WS4b_kurgent_results.txt |
| WS4c_flatter_prereg.md | 07:10:48 | 07:11:40 | WS4c_flatter_results.txt |
| WS5_prereg.md | 07:05:14 | 07:05:05 | WS5_bunching.txt |
| WS7_prereg.md | 07:13:42 | 07:18:04 | WS7_pilot_BA.txt |
| PREREG_round4.md | 07:44:41 | 07:54:39 | dist/review/audit2_4.txt |
| PREREG_round4.md | 07:44:41 | 07:46:36 | dist/review/audit1_scope.txt |
| PREREG_final.md | uncommitted | 10:38:46 | dist/review/audit_bed.json |

Reading: a commit time earlier than the result file mtime means the rule was committed first. Where the rule file mtime equals or follows the result file (WS4b, WS4c, WS5, PREREG_final) the rule was written during or after the run, and is not a pre-registration. The WS7 rule predates any non-Goias download but no result exists. PREREG_round4.md item 1 job was running when the file was written and items 2-9 and 14 were committed before their outputs were read. T4 was run after its amendment but the "before/after" verdict rule was found flawed after the output was read.

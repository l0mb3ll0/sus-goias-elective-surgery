# Repository decision (2026-11-15)

## Ancestry (Addition A)
`git merge-base --is-ancestor fca2890 6f36717` -> YES. (The instructions wrote `6f36716`; actual HEAD is `6f36717`, full hash 6f3671757c8dae3e65cc34de38686f652633851f.)
research2/goias-robustness is 19 commits ahead of sprint/nov-2026 (fca2890da5d76f5f76ba27778a85ac03951016e0) and 0 behind. Nothing exists only on the sprint branch.

## Recommended target
Commit 6f3671757c8dae3e65cc34de38686f652633851f (research2/goias-robustness), as the base of a NEW branch `final/nov-2026` in worktree `~/sos-final`. Approved by the author 2026-11-15; worktree ~/sos-final created.

## What changed after Nov 4 (fca2890..6f36717)
- 141 files, all under dist/research2/ (pre-registrations, Addenda 1-3, engine, results, logs, result JSONs).
- paper/*.tex, paper/numbers.json, tables, figures, scripts/: ZERO differences.
- ~/sos-cloud (492a2de) paper files (main.tex, appendix.tex, section_*.tex, sections_2_3.tex, numbers.json) are byte-identical to ~/sos HEAD. The patch written against sos-cloud therefore targets identical paper text.
- Untracked in ~/sos: data/road_km_GO_municipalities.csv, dist/research2/road_{results.json,results.md,run.py} (road-distance robustness, statewide only). Not committed; included in backup. They are NOT carried into final/nov-2026 unless approved.
- Working tree paper/ has no uncommitted changes.

## Addendum 3 vs main paper
RESULTS.md says "main text untouched". Addendum 3 (post hoc) concludes: below state level, results hold at the exact optimum but not within 1% of it; reading A ("claims data cannot support conclusions below state level") NOT adopted. It concerns the ordinal-cost identification of health-region/flow-level reallocation, a question the main paper (statewide benchmark) does not make claims about. No paper number depends on it. To be confirmed during Section 2: grep paper for any health-region/pair-level opportunity claims; if any, they must be qualified by reference to Addendum 3, but no new analysis is added. Road-distance results (untracked) are not in the paper and will not be added.

## Nested repo paper/sus-goias-public (HEAD 4101c6e, 2026-08-26, branch master, no remote)
- Older paper version: main.tex, section_*.tex and numbers.json all differ from the Nov paper; it has no appendix.tex. NOT authoritative.
- Unique content absent from ~/sos: README.md, LICENSE, pyproject.toml; slightly different .gitignore, hooks/pre-commit, scripts/{bootstrap_paired,check_build_inputs,check_tables}.py. Also its Aug history (6 commits) and a compiled PDF.
- ~/sos has NO README.md/LICENSE/pyproject.toml. The README task (Section 4) needs a decision on where the README lives.
- Another copy: ~/sos-snapshot-20261104/none/sus-goias-public (also HEAD 4101c6e).
- It is gitignored by ~/sos and has never been pushed -> preserved separately (tar + bundle).

## Other copies
sos-cloud 492a2de (single "snapshot" commit, Nov 4, paper identical to HEAD); sos-snapshot-20261104 649342f (Aug 26, historical); sos-repro..4 detached worktrees of ~/sos (preserved in one tar).

## Unresolved
1. Approve target 6f36717 and creation of ~/sos-final (final/nov-2026).
2. Where should README.md / LICENSE / pyproject.toml for the reproducibility section live (copy from nested into the final branch)?
3. Untracked road-distance files: leave untracked, or commit to research2? (not part of the final pass).
4. Ethics wording: main.tex currently reads "[PENDING BABSON IRB DETERMINATION.]" - need your decision.
5. data/pilot (BA/DF raw+interim SIH, 161 MB) is tracked in both branches contrary to data/README.md ("Do not push data/").

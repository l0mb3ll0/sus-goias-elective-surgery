# Security audit (2026-11-15). Values deliberately not reproduced.
Scope: working tree of ~/sos (tracked, untracked, ignored; excl. .venv, data/raw), `git log -p --all` of ~/sos (all 3 branches; 129 commits), full history + tree of nested sus-goias-public (21k diff lines), config (no remote URLs, no tokens/extraheader in .git/config). GitHub auth files not read.

## Credentials / keys / tokens
None found in any text file, any commit, or the nested repo. (PROGRESS.md notes an earlier refused attempt to put a token in ~/.bashrc; not in repo.) Binary data not scannable for secrets.

## Person-level identifiers
- No CPF-formatted strings, no professional CNS values, no "Dr./Dra." names in text or tracked CSV/parquet headers.
- 15-digit matches: manifest JSON line (SHA-256 substring, false positive); res840.txt (a government process number in a downloaded PDF text, public); two parquet hits (random byte matches). All false positives.
- Keyword matches `cpf`/`cns`: code/docs referencing the columns (scripts/hospital_master.py:147, scripts/sp_analysis.py:10, data/README.md:19, paper/main.tex:48 [Ethics paragraph], dist notes). Code reads CPFUNICO/SP_PF_DOC but docs state aggregates-only; no values committed.
- data/ref/hospital_master_2425.csv: columns name/street/cep are facility data; surgeon_225225(_fte) are counts. ~3% of `name` values (5 rows) do not match institution keywords - eyeball before release.

## Machine-specific paths (/home/<user>/, /mnt/c/Users)
- dist/research2/face_cont.log:24; dist/sprint/WS7_pilot_BA.txt:18 (x17); dist/sprint/repro_logs/20_figures.log:2; dist/sprint/repro_logs2/01_figures.log:2 (first committed c978964 / 7480230).
- Committed __pycache__/*.pyc in history (first commits 0e887c1, 7aed119, 2cce479) embed absolute paths.
- Remediation: for a public release, publish from a fresh export that omits dist/sprint/repro_logs*, WS7_pilot_BA*.txt, face_cont.log and pycache; do not rewrite history in place.

## Other sensitive / policy items
1. data/pilot/{BA,DF}/{raw,interim}/sih (101 files, 161 MB: DATASUS SIH-RD AIH extracts, no professional ids found by header scan) tracked since 98a56c6 on both research2 and sprint branches. data/README.md says "Do not push data/". Recommend excluding data/pilot from any push (or confirming it is public-redistributable DATASUS data); would need history rewrite to remove from a push of existing branches -> publish a squashed fresh export instead.
2. test.dbc tracked in root since 1a89bcb: unknown sample file, recommend removal from release export.
3. Git author metadata: 128 commits use the institutional email, 1 uses a placeholder. Published history exposes it. Decide before any public push.
4. dist/research2/_dl/page.html contains a public contact email from a government webpage; downloaded third-party pages (_dl/) are ignored by git (not in history) - exclude from release.
5. Ethics paragraph is a placeholder.
Nested repo: no findings in history or tree.

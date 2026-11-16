# Elective surgical allocation in Brazil's public health system: a statewide benchmark from Goiás, 2019–2025

Sole-authored paper (Gustavo Lombello Bargieri). It describes recorded elective surgical activity in Goiás in the SIH/SUS inpatient claims for 2019–2025 and builds a capacitated assignment benchmark (historical peak-volume cap, constructed bed-day budget) against which the observed allocation is compared. The benchmark is a diagnostic counterfactual under those rules, not a measure of operational capacity or a policy recommendation.

Paper: [`paper/main.pdf`](paper/main.pdf)

## One command for the main pipeline

```bash
python -m scripts.reproduce            # default: 25 steps, about 2 minutes on the author's machine
python -m scripts.reproduce --list     # print the steps without running
python -m scripts.reproduce --full     # adds the paired bootstrap and k-sweep summary (hours)
```

Prerequisite: `data/interim/` populated from the DATASUS fetch (`data/README.md`, `fetch_sih.py`); the intermediate Parquet is not committed. Run it in a clean checkout, because it compares every numeric leaf of `paper/numbers.json` and `paper/model_*.json` with the committed version (`--ref`, default `HEAD`).

**What it regenerates:** the model runs for 2019, 2023, 2025 (`paper/model_*.json`), the decomposition and capability stores, the four figures (`paper/fig1`–`fig4`, via `paper/figures.py`), the stored keys of `paper/numbers.json` that have a computing script, then runs `check_coverage`, `check_tables` (104 printed table cells) and `test_recompute`, and compiles `paper/main.pdf`.

**What it does not rebuild:** the review-pass results. These come from separate scripts in `dist/review/` and `dist/sprint/`, which `reproduce.py` does not run (except the bootstrap combine and k-sweep summary under `--full`).

| Review-pass output | Generating script(s) | Approx. runtime | Covered by `reproduce.py`? |
|---|---|---|---|
| Alternate optima / at-cap counts | `dist/review/alt_optima.py`, `alt_optima_thr.py` | not recorded | No |
| Peak-cap null simulations | `dist/review/null_cap.py` | not recorded | No |
| Paired bootstrap, fixed variants | `scripts/bootstrap_paired.py` (`--full`); `dist/review/boot_*.py` | hours | `--full` covers `scripts/` bootstrap only |
| k-sweep (2025) | `scripts/ksweep.py` (summary: `ksweep_summary`) | hours | Summary only, under `--full` |
| Audit and sensitivity rows | `dist/review/audit*.py`, `dist/sprint/ws*.py` | not recorded | No |

Two PELT changepoint keys, regime means, the Table 2 non-lag rows and a few other stored keys are explicitly allowed by `check_coverage` as non-regenerating; the list with reasons is in `scripts/check_coverage.py`.

## What the checks are

`check_coverage`, `check_tables` and the `reproduce.py` comparison re-run the same code on the same data, so they are **reproducibility checks, not independent verification** of correctness. The last full run reproduced 3,724 numeric values with none differing (`dist/sprint/repro_run4.txt`).

## Environment

`requirements-snapshot.txt` is a snapshot of the environment the stored numbers were produced under (Python 3.12.13; HiGHS 1.12.0 as bundled in SciPy 1.18.0; package versions from `pip freeze`). It is a snapshot, not a lockfile. `pyproject.toml` pins the main dependencies. No container is provided. Building the PDF needs a TeX Live installation (pdfTeX 2025 used).

## Layout

```
fetch_sih.py          DATASUS ingestion (SIH, DBC to Parquet), writes the manifest
data/ref/             IBGE, SIGTAP and CNES reference tables
paper/                LaTeX sources, figures, generated result files, numbers.json
scripts/              analysis, model and repository checks (reproduce.py, check_*.py)
dist/sprint/          audit record, pre-registrations, CHANGELOG, FINAL_PASS.md
dist/review/          review-pass scripts and results
hooks/pre-commit      runs the repository checks before a commit
```

Not committed: `data/raw/` and `data/interim/` (rebuild with `fetch_sih.py`).

## Data and privacy

Source data are public DATASUS files (SIH/SUS, CNES) and IBGE codes. Files with professional identifiers (`SP_PF_DOC`) are never committed or published; analysis scripts emit aggregates only. A public release is exported fresh, without history.

## License

MIT for the code (see `LICENSE`). The paper text and figures under `paper/` are © 2026 Gustavo Lombello Bargieri, all rights reserved. DATASUS data are not covered by this licence.

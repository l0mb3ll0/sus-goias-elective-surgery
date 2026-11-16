# Data sources

Nothing under `data/raw/` or `data/interim/` is tracked (size, and the SP files carry professional identifiers). Everything is re-fetched from public DATASUS
sources, which are maintained by the Brazilian Ministry of Health (Ministerio da Saude, DATASUS). Manifests in `data/manifest_*.json` record a SHA-256 and row count per
downloaded file so a re-fetch can be checked against the one the paper used.

| dataset | official source | fetched by | lands in |
|---|---|---|---|
| SIH/SUS RD (reduced AIH), Goias, 2019-01..2025-12 | DATASUS FTP `ftp://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/200801_/Dados` (files `RDGOyymm.dbc`) | `fetch_sih.py --ufs GO --start 2019-01 --end 2025-12` | `data/interim/sih/` |
| SIH/SUS SP (professional services), Goias, 2024-2025 | same FTP directory (files `SPGOyymm.dbc`) | `python -m scripts.sp_fetch --year 2024` (and 2025) | `data/interim/sih_sp/` |
| CNES ST (establishments), LT (beds), PF (professionals), EQ (equipment), HB, SR | DATASUS FTP `ftp://ftp.datasus.gov.br/dissemin/publicos/CNES/200508_/Dados/<ST|LT|PF|EQ|HB|SR>` | `scripts/cnes_pull.py`, `scripts/build_cnes_interim.py` (staffing_layer/) | `data/raw/cnes`, `data/interim/cnes/` |
| CNES monthly base ZIPs (installations, equipment members) | DATASUS FTP `ftp://ftp.datasus.gov.br/cnes` (`BASE_DE_DADOS_CNES_yyyymm.ZIP`) | `scripts/cnes_room_panel.py` | `data/raw/cnes/` |
| IBGE municipalities of Goias (codes, immediate and intermediate regions) | IBGE Localidades API `https://servicodados.ibge.gov.br/api/v1/localidades/estados/52/municipios` | `scripts/ref_ibge.py` | `data/ref/ibge_municipios_go.csv` (tracked) |
| SIGTAP procedure table (names, complexity, permanence days) | DATASUS SIGTAP `TabelaUnificada_YYYYMM` ZIP | `scripts/build_sigtap.py` | `data/ref/sigtap_*.csv` (tracked) |

DATASUS specifics: HTTPS endpoints are dead, FTP only; `.dbc` needs `datasus-dbc`; the FTP `quit()` can raise on timeout; DATASUS throttles (sp_fetch retries slowly on purpose).
Known data traps recorded in the repo: CNES EQ zero-pads TIPEQUIP from 2025-09 (`'3'` becomes `'03'`); CNES registers state with lag, not events.

Privacy: SP rows contain a 15-digit professional CNS (`SP_PF_DOC`). It is never printed, committed or published; analysis scripts emit aggregates only. Do not push `data/`.
Footprint: SIH about 1.5 GB of `.dbc` converting to 76 MB of Parquet; SP 2024-25 about 11.5 million act rows (peak 4.7 GB RAM in `scripts.sp_analysis`).

## Added reference files (final pass)
| file | official source | note |
|---|---|---|
| `data/ref/regioes_saude_go.csv` | SES-GO, page "Regioes de Saude" (https://goias.gov.br/saude/regioes-de-saude-planejamento/), read 2026-11-04: municipalities per health region and macro-region grouping | 18 health regions, 246 municipalities, 5 macro-regions; read from the web page, not from the CIB resolution; matched to IBGE codes by name (four spelling fixes: Alto Paraiso de Goias, Campo Limpo de Goias, Varjao, Vianopolis) |
| `data/ref/ride_df_goias.csv` | Lei Complementar 94/1998 as amended by Lei Complementar 163/2018 (index page of the Camara dos Deputados, https://www2.camara.leg.br/legin/fed/leicom/2018/leicomplementar-163-14-junho-2018-786859-norma-pl.html, read 2026-11-04) | 29 Goias municipalities; the index tags Planaltina as DF, read as Planaltina de Goias |

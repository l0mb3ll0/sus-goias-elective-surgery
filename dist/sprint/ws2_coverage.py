"""AIH-level identification coverage in the SIH SP table, 2024-01..2025-12. Aggregates only, no IDs printed.
Denominator for 'elective group-04 AIHs' is RD (N_AIH, PROC_REA group 04, CAR_INT=01), which SP lacks CAR_INT for.
Questions: (a) of RD elective group-04 AIHs, what share appear in SP at all; (b) of those, share with >=1 act row carrying
a professional id; (c) share with a 225225 id; (d) same for cholecystectomy AIHs; (e) facility-level spread."""
import glob, numpy as np, pandas as pd
CHOL = {'0407030026', '0407030034'}
sp = pd.concat([pd.read_parquet(f, columns=['SP_NAIH','SP_CNES','SP_PROCREA','SP_PF_CBO','SP_PF_DOC'])
                for f in sorted(glob.glob('data/interim/sih_sp/sp_GO_202[45].parquet'))])
for c in sp.columns: sp[c] = sp[c].astype(str).str.strip()
sp['id'] = sp.SP_PF_DOC != '0'*15; sp['surg'] = sp.id & (sp.SP_PF_CBO == '225225')
print('SP act rows', len(sp), 'row-level id share', round(sp.id.mean()*100, 1))
rd = pd.concat([pd.read_parquet(f, columns=['N_AIH','CAR_INT','PROC_REA','CNES'])
                for f in sorted(glob.glob('data/interim/sih/RDGO2[45]*.parquet'))])
rd = rd[(rd.PROC_REA.str[:2] == '04') & (rd.CAR_INT == '01')]
rd['N_AIH'] = rd.N_AIH.astype(str).str.strip(); rd['CNES'] = rd.CNES.astype(str).str.strip()
a = sp.groupby('SP_NAIH').agg(any_id=('id', 'max'), any_surg=('surg', 'max'), n_rows=('id', 'size'), fac=('SP_CNES', 'first'))
chol_aih = set(sp[sp.SP_PROCREA.isin(CHOL)].SP_NAIH)
el = rd.drop_duplicates('N_AIH'); in_sp = el.N_AIH.isin(a.index)
print(f'RD elective group-04 AIHs {len(el):,}; present in SP {in_sp.mean()*100:.1f}%')
e = a.loc[el.N_AIH[in_sp]]
print(f'  of those: >=1 identified professional {e.any_id.mean()*100:.1f}%   >=1 identified 225225 {e.any_surg.mean()*100:.1f}%')
ch = a.loc[[x for x in chol_aih if x in a.index]]
print(f'cholecystectomy AIHs in SP {len(ch):,}: >=1 identified professional {ch.any_id.mean()*100:.1f}%  >=1 identified 225225 {ch.any_surg.mean()*100:.1f}%')
print('  AIHs where all rows unidentified (invisible to every surgeon figure):', f'{(~ch.any_id).mean()*100:.1f}%')
cov = a.groupby('fac').any_id.mean(); n = a.groupby('fac').size()
big = cov[n >= 100]
print(f'facility-level AIH id coverage (facilities with >=100 AIHs, n={len(big)}): min {big.min()*100:.0f}% p25 {big.quantile(.25)*100:.0f}% median {big.median()*100:.0f}% p75 {big.quantile(.75)*100:.0f}% max {big.max()*100:.0f}%')
print(f'  facilities with ZERO identified rows: {int((cov == 0).sum())} of {len(cov)}; with >=1: {int((cov > 0).sum())}')
m = sp.assign(cm_=0)
print('\n--- what the unidentified rows are: SP_ATOPROF (act type) by identified flag, share of rows ---')
sp2 = pd.concat([pd.read_parquet(f, columns=['SP_ATOPROF','SP_PF_DOC']) for f in sorted(glob.glob('data/interim/sih_sp/sp_GO_202[45].parquet'))])
sp2['ato'] = sp2.SP_ATOPROF.astype(str).str.strip().str[:2]; sp2['id'] = sp2.SP_PF_DOC.astype(str).str.strip() != '0'*15
t = sp2.groupby('ato').id.agg(['size', 'mean']); t['share_rows'] = t['size']/t['size'].sum()
print(t.sort_values('size', ascending=False).head(8).round(3).to_string())
nid = (sp.id.groupby(sp.SP_NAIH).sum()); print('identified rows per AIH: median', nid.median(), 'p10', nid.quantile(.1), 'p90', nid.quantile(.9))
# group-04 elective AIHs: CBO mix of identified rows
print('top CBOs among identified rows of elective group-04 AIHs (share of identified rows):')
x = sp[sp.SP_NAIH.isin(set(el.N_AIH)) & sp.id].SP_PF_CBO.value_counts(normalize=True).head(8).round(3); print(x.to_string())

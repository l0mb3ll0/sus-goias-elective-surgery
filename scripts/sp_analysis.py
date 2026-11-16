"""Surgeon-level analysis of the SIH SP panel (tasks A-D).

Runs on whatever SP months are present. Pass --months to name them explicitly;
by default it reads every sp_GO_*.parquet under data/interim/sih_sp plus the
single-month probe file, and STATES the window it actually used rather than
assuming a full panel.

FIELD BASIS, all verified on the 2024-06 probe before use:
  SP_NAIH    AIH number, links to RD
  SP_PF_DOC  15-digit professional CNS. Placeholder '000000000000000'.
  SP_PF_CBO  professional CBO. Placeholder '000000'. Populates on exactly the
             same rows as SP_PF_DOC.
  SP_CNES    billing facility
No meaning is assigned to IN_TP_VAL or SP_PJ_DOC: both are undocumented in any
label table held here, and SP_TIPO / SP_TP_ATO, the natural candidates for an
internal-vs-external flag, are 100% blank.

    python -m scripts.sp_analysis [--months 2024-06]
"""
import argparse, glob, os
import numpy as np
import pandas as pd

CHOL = {'0407030026': 'open', '0407030034': 'laparoscopic'}
PH_DOC, PH_CBO = '000000000000000', '000000'
SURGEON = '225225'
ROLL = 3


# Only these columns are used below. Reading all 36 columns of ~11.5 million rows exceeded 7.6 GB
# (OOM kill, exit 137); projecting the read peaks near 5 GB for the 24-month panel and changes no result.
USECOLS = ['SP_AA', 'SP_MM', 'SP_NAIH', 'SP_CNES', 'SP_PROCREA', 'SP_ATOPROF', 'SP_PF_CBO', 'SP_PF_DOC',
           'SP_PJ_DOC', 'SP_M_HOSP', 'SP_TIPO', 'SP_TP_ATO', 'cm']


def load(paths):
    import pyarrow.parquet as pq
    fr = []
    for p in paths:
        d = pd.read_parquet(p, columns=[c for c in USECOLS if c in pq.read_schema(p).names])
        if 'cm' not in d.columns:
            d['cm'] = d.SP_AA.astype(str).str.strip() + '-' + \
                      d.SP_MM.astype(str).str.strip()
        fr.append(d)
    d = pd.concat(fr, ignore_index=True)
    for c in ('SP_NAIH', 'SP_PF_DOC', 'SP_PF_CBO', 'SP_CNES', 'SP_PROCREA',
              'SP_ATOPROF', 'SP_M_HOSP', 'cm'):
        d[c] = d[c].astype(str).str.strip()
    return d


def q(s, label):
    if not len(s):
        return f'  {label}: no observations'
    v = s.describe(percentiles=[.5, .75, .9, .95])
    return (f'  {label}: n={int(v["count"])}  median={v["50%"]:.1f}  '
            f'p75={v["75%"]:.1f}  p90={v["90%"]:.1f}  p95={v["95%"]:.1f}  '
            f'max={v["max"]:.1f}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--months', nargs='*')
    A = ap.parse_args()
    paths = sorted(glob.glob('data/interim/sih_sp/sp_GO_*.parquet')) or \
            sorted(glob.glob('data/interim/sih_sp_GO_*.parquet'))
    assert paths, 'no SP parquet found'
    d = load(paths)
    if A.months:
        d = d[d.cm.isin(A.months)]
    months = sorted(d.cm.unique())
    print(f'WINDOW: {len(months)} month(s) {months[0]}..{months[-1]}  '
          f'{len(d):,} act rows, {d.SP_NAIH.nunique():,} AIHs')
    if len(months) < 24:
        print(f'  PARTIAL PANEL -- {24 - len(months)} of 24 months absent. '
              f'Rolling-mean and multi-facility results are not the panel result.')

    # ---------------- D: stability, run FIRST because A-C depend on it -------
    print('\n=== D. identifier stability ===')
    p = d[d.SP_PF_DOC != PH_DOC]
    print(f'  SP_PF_DOC length distribution: {p.SP_PF_DOC.str.len().value_counts().to_dict()}')
    print(f'  non-numeric ids: {int((~p.SP_PF_DOC.str.isdigit()).sum())}')
    print(f'  SP_PF_CBO length distribution: '
          f'{d.loc[d.SP_PF_CBO != PH_CBO, "SP_PF_CBO"].str.len().value_counts().to_dict()}')
    g = d.groupby('cm').agg(rows=('SP_NAIH', 'size'),
                            cbo_real=('SP_PF_CBO', lambda s: (s != PH_CBO).sum()),
                            doc_real=('SP_PF_DOC', lambda s: (s != PH_DOC).sum()),
                            profs=('SP_PF_DOC', lambda s: s[s != PH_DOC].nunique()))
    g['cbo_pct'] = (100 * g.cbo_real / g.rows).round(1)
    g['doc_pct'] = (100 * g.doc_real / g.rows).round(1)
    print(g[['rows', 'cbo_pct', 'doc_pct', 'profs']].to_string())
    if len(g) > 1:
        sp = g.cbo_pct
        print(f'  CBO population rate range across months: '
              f'{sp.min():.1f}% - {sp.max():.1f}% (spread {sp.max()-sp.min():.1f}pp)')
    same = int((d.SP_PF_CBO != PH_CBO).sum()) == int((d.SP_PF_DOC != PH_DOC).sum())
    print(f'  CBO and DOC populate on the same rows: {same}')

    # Reuse test. If an identifier were recycled to a different person mid-panel,
    # the giveaway is one id carrying several CBOs. Multiple CBOs can also be
    # legitimate (one professional registered under two occupations), so this
    # bounds the problem rather than proving it.
    ncbo = p.groupby('SP_PF_DOC').SP_PF_CBO.nunique()
    print(f'  ids carrying >1 CBO across the window: {int((ncbo > 1).sum())} of '
          f'{len(ncbo)} ({100*(ncbo > 1).mean():.1f}%), max {int(ncbo.max())} CBOs')
    nm = p.groupby('SP_PF_DOC').cm.nunique()
    print(f'  months present per id: median {nm.median():.0f}, '
          f'appearing in only one month {int((nm == 1).sum())} '
          f'({100*(nm == 1).mean():.1f}%), in all {len(months)} '
          f'{int((nm == len(months)).sum())} ({100*(nm == len(months)).mean():.1f}%)')
    first = p.groupby('SP_PF_DOC').cm.min().value_counts().reindex(months, fill_value=0)
    print(f'  first appearance by month: {first.to_dict()}')

    surg = d[(d.SP_PF_CBO == SURGEON) & (d.SP_PF_DOC != PH_DOC)]
    print(f'\n  CBO {SURGEON} act rows {len(surg):,}, '
          f'distinct professionals {surg.SP_PF_DOC.nunique():,}')

    # ---------------- A: surgeon throughput ---------------------------------
    print('\n=== A. surgeon throughput (CBO 225225) ===')
    chol_aih = set(d[d.SP_PROCREA.isin(CHOL)].SP_NAIH)
    for name, sub in [('cholecystectomy', surg[surg.SP_NAIH.isin(chol_aih)]),
                      ('all group-04 elective', surg[surg.SP_PROCREA.str[:2] == '04'])]:
        # one case = one AIH the surgeon appears on
        cm_counts = sub.groupby(['SP_PF_DOC', 'cm']).SP_NAIH.nunique()
        per_month = cm_counts.groupby('SP_PF_DOC').mean()
        print(f'\n  -- {name}: {sub.SP_NAIH.nunique():,} AIHs, '
              f'{sub.SP_PF_DOC.nunique():,} surgeons')
        print(q(per_month, 'cases/month per surgeon'))
        if len(months) >= ROLL:
            # largest 3-month rolling mean, matching the capability-cap construction
            t = cm_counts.unstack('cm').reindex(columns=months).fillna(0)
            rm = t.T.rolling(ROLL, min_periods=ROLL).mean().max()
            print(q(rm, f'largest {ROLL}-month rolling mean'))
        else:
            print(f'  largest {ROLL}-month rolling mean: needs >={ROLL} months, '
                  f'have {len(months)} -- not computed')
        tot = sub.groupby('SP_PF_DOC').SP_NAIH.nunique().sort_values(ascending=False)
        if len(tot):
            cs = tot.cumsum() / tot.sum()
            half = int((cs < .5).sum()) + 1
            print(f'  surgeons accounting for half of volume: {half} of {len(tot)} '
                  f'({100*half/len(tot):.1f}%)')
            # Annual concentration, over the whole 225225 population rather than
            # over performers only: a surgeon doing none of this work is a real
            # zero, and dropping them would overstate how spread the work is.
            n_all = surg.SP_PF_DOC.nunique()
            dec = max(1, int(round(0.10 * n_all)))
            print(f'  of {n_all} surgeons on 225225, {len(tot)} perform any '
                  f'({100*len(tot)/n_all:.1f}%)')
            print(f'  top decile = top {dec} of {n_all}: '
                  f'{100*tot.head(dec).sum()/tot.sum():.1f}% of volume '
                  f'({int(tot.head(dec).sum()):,} of {int(tot.sum()):,} cases)')
            print(f'  annual cases per performing surgeon: median '
                  f'{tot.median():.0f}, p90 {tot.quantile(.9):.0f}, max {int(tot.max())}')

    # ---------------- B: multi-facility -------------------------------------
    print('\n=== B0. surgeons carrying a second CBO ===')
    surg_ids = set(surg.SP_PF_DOC.unique())
    cbo_per_id = p[p.SP_PF_DOC.isin(surg_ids)].groupby('SP_PF_DOC').SP_PF_CBO.nunique()
    multi = set(cbo_per_id[cbo_per_id > 1].index)
    print(f'  of {len(surg_ids)} surgeons on 225225, {len(multi)} carry a second '
          f'CBO ({100*len(multi)/len(surg_ids):.1f}%)')
    other = (p[p.SP_PF_DOC.isin(multi) & (p.SP_PF_CBO != SURGEON)]
             .SP_PF_CBO.value_counts().head(6))
    print(f'  their other CBOs (top 6): {other.to_dict()}')

    def concentration(sg, label):
        chol = sg[sg.SP_NAIH.isin(chol_aih)]
        tot = chol.groupby('SP_PF_DOC').SP_NAIH.nunique().sort_values(ascending=False)
        if not len(tot):
            print(f'  {label}: no volume'); return
        cs = tot.cumsum() / tot.sum()
        half = int((cs < .5).sum()) + 1
        n_all = sg.SP_PF_DOC.nunique()
        dec = max(1, int(round(0.10 * n_all)))
        rows = []
        for cnes, gg in chol.groupby('SP_CNES'):
            ta = gg.SP_NAIH.nunique()
            per = gg.groupby('SP_PF_DOC').SP_NAIH.nunique()
            rows.append((ta, len(per), per.max() / ta))
        b = pd.DataFrame(rows, columns=['aihs', 'n_surg', 'top_share'])
        print(f'  {label}: {n_all} surgeons, {len(tot)} performing, '
              f'{int(tot.sum()):,} cases')
        print(f'    half of volume from {half} surgeons ({100*half/len(tot):.1f}% '
              f'of performers); top decile ({dec}) carries '
              f'{100*tot.head(dec).sum()/tot.sum():.1f}%')
        print(f'    facilities: {len(b)}; exactly one surgeon '
              f'{int((b.n_surg == 1).sum())}; >=90% from one surgeon '
              f'{int((b.top_share >= .9).sum())}; median surgeons/facility '
              f'{b.n_surg.median():.0f}')

    print('\n  concentration with and without the second-CBO surgeons:')
    concentration(surg, 'ALL 225225 surgeons')
    concentration(surg[~surg.SP_PF_DOC.isin(multi)], 'EXCLUDING second-CBO surgeons')

    print('\n=== B. multi-facility surgeons (priority) ===')
    fac = surg.groupby('SP_PF_DOC').SP_CNES.nunique()
    mun = surg.groupby('SP_PF_DOC').SP_M_HOSP.nunique()
    print(f'  facilities per surgeon: {fac.value_counts().sort_index().to_dict()}')
    print(f'  >1 facility, POOLED over {len(months)} months: '
          f'{int((fac > 1).sum())} of {len(fac)} '
          f'({100*(fac > 1).mean():.1f}%)   max {int(fac.max())}')
    # Pooled and per-month answer different questions. Pooled asks whether a
    # surgeon ever works at more than one site in the year; per-month asks
    # whether they do so within a single month. Pooled is mechanically the
    # larger, so both are reported rather than one standing for the other.
    pm = surg.groupby(['cm', 'SP_PF_DOC']).SP_CNES.nunique()
    rate = pm.groupby('cm').apply(lambda s: (s > 1).mean())
    print(f'  >1 facility, PER MONTH then averaged: {100*rate.mean():.1f}% '
          f'(range {100*rate.min():.1f}%-{100*rate.max():.1f}% across months)')
    print(f'  municipalities per surgeon: {mun.value_counts().sort_index().to_dict()}')
    print(f'  >1 municipality: {int((mun > 1).sum())} of {len(mun)} '
          f'({100*(mun > 1).mean():.1f}%)')
    share = surg.groupby(['SP_PF_DOC', 'SP_CNES']).SP_NAIH.nunique()
    tot = share.groupby('SP_PF_DOC').sum()
    top = (share / tot).groupby('SP_PF_DOC').max()
    print(q(top[fac > 1], 'share at their busiest facility, multi-facility only'))

    nonexcl = set(fac[fac > 1].index)
    ch_s = surg[surg.SP_NAIH.isin(chol_aih)]
    by_fac = ch_s.groupby('SP_CNES').agg(
        aihs=('SP_NAIH', 'nunique'),
        by_nonexcl=('SP_PF_DOC', lambda s: 0))
    rows = []
    for cnes, gg in ch_s.groupby('SP_CNES'):
        tot_a = gg.SP_NAIH.nunique()
        ne = gg[gg.SP_PF_DOC.isin(nonexcl)].SP_NAIH.nunique()
        # dependence on one person: how many distinct 225225 surgeons operate
        # here, and what share of the facility's volume the busiest one carries
        per = gg.groupby('SP_PF_DOC').SP_NAIH.nunique()
        rows.append((cnes, tot_a, ne, ne / tot_a if tot_a else np.nan,
                     len(per), per.max() / tot_a if tot_a else np.nan))
    bf = pd.DataFrame(rows, columns=['CNES', 'chol_aihs', 'aihs_nonexcl', 'share',
                                     'n_surgeons', 'top_surgeon_share'])
    bf = bf.sort_values('chol_aihs', ascending=False)
    print(f'\n  facilities with cholecystectomy volume: {len(bf)}')
    print(q(bf.share, 'share of facility chol volume by non-exclusive surgeons'))
    full = bf[(bf.share == 1.0)]
    print(f'  facilities where ALL cholecystectomy volume is performed by '
          f'non-exclusive surgeons: {len(full)} of {len(bf)}')
    print('\n  -- dependence on a single surgeon --')
    print(f'  distinct 225225 surgeons per facility: '
          f'{bf.n_surgeons.value_counts().sort_index().to_dict()}')
    print(q(bf.n_surgeons, 'surgeons per facility'))
    print(q(bf.top_surgeon_share, 'share of facility volume from its busiest surgeon'))
    one = bf[bf.n_surgeons == 1]
    print(f'  facilities with exactly ONE 225225 surgeon: {len(one)} of {len(bf)} '
          f'({100*len(one)/len(bf):.1f}%), carrying {int(one.chol_aihs.sum()):,} '
          f'of {int(bf.chol_aihs.sum()):,} cholecystectomy AIHs')
    for thr in (0.75, 0.90):
        k = int((bf.top_surgeon_share >= thr).sum())
        print(f'  facilities with >={int(100*thr)}% of volume from one surgeon: '
              f'{k} of {len(bf)} ({100*k/len(bf):.1f}%)')
    print(bf.head(12).to_string(index=False))

    # ---------------- C: team composition -----------------------------------
    print('\n=== C. team composition on cholecystectomy AIHs ===')
    ch = d[d.SP_NAIH.isin(chol_aih)]
    approach = d[d.SP_PROCREA.isin(CHOL)].groupby('SP_NAIH').SP_PROCREA.first().map(CHOL)
    team = ch[ch.SP_PF_DOC != PH_DOC].groupby('SP_NAIH').SP_PF_DOC.nunique()
    tt = pd.DataFrame({'team': team, 'approach': approach}).dropna()
    print(q(tt.team, 'distinct professionals per AIH, all'))
    for k, gg in tt.groupby('approach'):
        print(q(gg.team, f'team size, {k}'))
    # The laparoscopic-vs-open difference in means is deliberately NOT printed.
    # On one month it is a number without a test behind it; the distributions
    # above are the honest presentation until the panel supports a comparison.

    m = pd.read_csv('data/ref/hospital_master_2425.csv', dtype={'CNES': str})
    fa = ch[ch.SP_PF_DOC != PH_DOC].groupby('SP_NAIH').agg(
        team=('SP_PF_DOC', 'nunique'), cnes=('SP_CNES', 'first'))
    unmatched = int((~fa.cnes.isin(m.CNES)).sum())
    print(f'\n  AIHs whose facility is absent from the master record: {unmatched} '
          f'(reported, not dropped)')
    # The with/without-laparoscope comparison is HELD until the room panel lands.
    # It would split facilities on the 202606 equipment snapshot, and whether that
    # snapshot represents 2024-25 is precisely what the room panel exists to test.
    print('  team size by registered laparoscopic equipment: HELD -- requires the '
          'room panel, not the 202606 snapshot')
    print(f'\n  team size by facility, top 10 by volume:')
    fb = fa.groupby('cnes').team.agg(['size', 'mean', 'median']).sort_values(
        'size', ascending=False).head(10).round(2)
    print(fb.to_string())


if __name__ == '__main__':
    main()

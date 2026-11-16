"""Cap test: does an at-cap pair or facility exceed its year-t cap in year t+1, and does that
depend on whether surgeons, operating rooms or laparoscopes rose?

Year t in {2023, 2024}, t+1 in {2024, 2025}. Built on the bootstrap's own Year class.

AT CAP in year t, from the year-t optimum at point values (the paper's thresholds, as in
scripts/model_urgent.py): facility if served / kappa_j > 0.95; pair if kappa_jp > 0.5 (not
floored) and served / kappa_jp > 0.95. All other facilities / non-floored pairs are 'slack'.

EXCEEDANCE in t+1, same in-state elective records and same construction:
  roll   kappa_{t+1} > kappa_t   (next year's largest 3-month rolling mean beats this year's cap)
  month  share of the 12 months of t+1 with volume > kappa_t

COMPARISON: non-at-cap ('slack') facilities and non-floored pairs, same measures.

PLACEBO: urgent surgical volume (group 04, CAR_INT != '01', in-state residents) at the same
facilities and pairs, with the same groups. Urgent kappa_t and kappa_{t+1} are built the same way
from urgent records; units with urgent kappa_t <= 0.5 are left out (no meaningful urgent cap).
If at-cap units' urgent volume also beats its own prior maximum at a similar rate, elective
exceedance reflects general growth rather than a binding cap being broken.

RESOURCES ARE FACILITY-LEVEL. CNES PF and EQ record staff and equipment per facility, not per
procedure, and rooms are per facility too. A pair is assigned its facility's change, so a
pair-level split says whether the facility gained a resource, not whether that procedure did.

RESOURCE ROSE DURING t+1 (facility level; pairs inherit their facility's value), start vs end of
t+1, rose = strictly greater, a facility absent from a source in a month counts as 0:
  surgeons     distinct CPF_PROF in CNES PF with an operating-surgeon CBO (225225 plus 18
               specialty codes), January vs December of t+1
  laparoscopes CNES EQ TIPEQUIP 03 / CODEQUIP 35 QT_EXIST, January vs December of t+1
               (codes zero-padded: TIPEQUIP changed from '3' to '03' in 2025-09)
  rooms        CNES base rlEstabInstFisiAssist CO_INSTALACAO 31 (centro cirurgico);
               2024: 202401 vs 202501, 2025: 202501 vs 202512. No monthly series exists.
"""
import glob, io, json, sys, zipfile
import numpy as np, pandas as pd
sys.path.insert(0, 'dist/review')
import _boot_src as S

SURG = {'225225','225270','225250','225265','225203','225285','225260','225275','225235','225310',
        '225220','225210','225230','225290','225255','225280','225240','225215','225295'}
ROOM_SNAP = {'2024': ('202401', '202501'), '2025': ('202501', '202512')}
ref = pd.read_csv('data/ref/ibge_municipios_go.csv', dtype=str); GO = set(ref.cod6)

pf = pd.read_parquet('data/interim/cnes/cnes_pf_GO_raw.parquet', columns=['CNES','CBO','cm','CPF_PROF'])
for c in ('CNES','CBO','CPF_PROF','cm'): pf[c] = pf[c].astype(str).str.strip()
blank = float(pf.CPF_PROF.isin(['', 'nan', 'None']).mean())
pf = pf[pf.CBO.isin(SURG)]
eq = pd.read_parquet('data/interim/cnes/cnes_eq_GO_raw.parquet', columns=['CNES','TIPEQUIP','CODEQUIP','QT_EXIST','cm'])
for c in ('TIPEQUIP','CODEQUIP'): eq[c] = eq[c].astype(str).str.strip().str.zfill(2)
eq = eq[(eq.TIPEQUIP == '03') & (eq.CODEQUIP == '35')].copy()
eq['CNES'] = eq.CNES.astype(str).str.strip(); eq['q'] = pd.to_numeric(eq.QT_EXIST, errors='coerce').fillna(0)

rooms = {}
for v in sorted({s for p in ROOM_SNAP.values() for s in p}):
    z = zipfile.ZipFile(f'data/raw/cnes/BASE_DE_DADOS_CNES_{v}.ZIP')
    name = [n for n in z.namelist() if n.lower().startswith('rlestabinstfisiassist')][0]
    with z.open(name) as fh:
        f = pd.read_csv(io.TextIOWrapper(fh, 'latin-1'), sep=';', dtype=str, quotechar='"', low_memory=False)
    f = f[f.CO_UNIDADE.astype(str).str[:2] == '52']
    f = f[f.CO_INSTALACAO.astype(str).str.strip().str.zfill(2) == '31']
    rooms[v] = f.assign(cnes=f.CO_UNIDADE.astype(str).str[6:],
                        q=pd.to_numeric(f.QT_INSTALACAO, errors='coerce').fillna(0)).groupby('cnes').q.sum()


def rose(t1):
    jan, dec = f'{t1}-01', f'{t1}-12'
    s = pf.groupby(['CNES', 'cm']).CPF_PROF.nunique()
    l = eq.groupby(['CNES', 'cm']).q.sum()
    a, b = ROOM_SNAP[t1]
    def chg(ser, m0, m1):
        x0 = ser.xs(m0, level='cm') if m0 in ser.index.get_level_values('cm') else pd.Series(dtype=float)
        x1 = ser.xs(m1, level='cm') if m1 in ser.index.get_level_values('cm') else pd.Series(dtype=float)
        idx = x0.index.union(x1.index)
        return x1.reindex(idx).fillna(0) > x0.reindex(idx).fillna(0)
    r_room = (rooms[b].reindex(rooms[a].index.union(rooms[b].index)).fillna(0) >
              rooms[a].reindex(rooms[a].index.union(rooms[b].index)).fillna(0))
    return {'surgeons': chg(s, jan, dec), 'rooms': r_room, 'laparoscopes': chg(l, jan, dec)}


def next_year_volumes(t1, J, pair_keys, urgent=False):
    a = pd.concat([pd.read_parquet(f, columns=['CNES','PROC_REA','CAR_INT','COMPETENCIA','MUNIC_RES'])
                   for f in sorted(glob.glob(f'data/interim/sih/RDGO{t1[2:]}*.parquet'))])
    car = (a.CAR_INT != '01') if urgent else (a.CAR_INT == '01')
    el = a[(a.PROC_REA.str[:2] == '04') & car].copy()
    el = el[el.MUNIC_RES.astype(str).str[:6].isin(GO)]
    el['p'] = el.PROC_REA.str[:4]
    months = sorted(el.COMPETENCIA.unique()); assert len(months) == 12
    jm = el.groupby(['CNES', 'COMPETENCIA']).size().unstack(fill_value=0).reindex(index=J, columns=months, fill_value=0)
    pm = el.groupby(['CNES', 'p', 'COMPETENCIA']).size().unstack(fill_value=0)
    pm = pm.reindex(index=pd.MultiIndex.from_tuples(pair_keys), columns=months, fill_value=0)
    return jm.to_numpy(float), pm.to_numpy(float)


def rates(cap, nxt_k, nxt_m, mask):
    if mask.sum() == 0:
        return dict(n=0)
    c = cap[mask]
    return dict(n=int(mask.sum()),
                roll_exceed=float((nxt_k[mask] > c).mean()),
                month_exceed=float((nxt_m[mask] > c[:, None]).mean()),
                median_ratio=float(np.median(nxt_k[mask]/c)))


out, L = {'cpf_blank_share_pf': blank}, [__doc__,
     f'CNES PF CPF_PROF blank share (all months): {blank:.4f}', '']
for t, t1 in (('2023', '2024'), ('2024', '2025')):
    Y = S.Year(t); one = np.ones(len(Y.key))
    r = S.gap_parts(Y, one, one, one)
    x, kj, kp = r['x'], r['kj'], r['kp']
    served = np.bincount(Y.colpair, weights=x, minlength=Y.npair)
    fac = np.asarray(Y.Sc[:, :Y.nx] @ x).ravel()
    J = list(Y.J)
    f_at = fac/np.maximum(kj, 1e-12) > 0.95
    nf = kp > 0.5001
    p_at = nf & (served/kp > 0.95)
    p_slack = nf & ~p_at
    jm1, pm1 = next_year_volumes(t1, J, Y.pair_keys)
    kj1, kp1 = S.r3(jm1), S.r3(pm1)
    R = rose(t1)
    fj = pd.Index(J)
    fac_rose = {k: v.reindex(fj).fillna(False).to_numpy(bool) for k, v in R.items()}
    jpos = {c: n for n, c in enumerate(J)}
    pair_fac = np.array([jpos[j] for j, p in Y.pair_keys])
    res = {'gap_point': r['gap'], 'n_fac': len(J), 'fac_at_cap': int(f_at.sum()),
           'pairs_nonfloored': int(nf.sum()), 'pairs_at_cap': int(p_at.sum()), 'facility': {}, 'pair': {}}
    L += [f'=== {t} -> {t1} ===',
          f'year-{t} optimum: gap {r["gap"]*100:.1f}%, |J| {len(J)}, facilities at cap {f_at.sum()}, '
          f'non-floored pairs {nf.sum()}, pairs at cap {p_at.sum()}',
          f'resources rose during {t1} (facilities in J): ' +
          ', '.join(f'{k} {int(v.sum())}' for k, v in fac_rose.items()) +
          f', any {int(np.any(np.vstack(list(fac_rose.values())), axis=0).sum())}', '',
          f"{'level':9s}{'group':30s}{'n':>6s}{'kappa_t1>kappa_t':>18s}{'months>kappa_t':>16s}{'median k1/k':>13s}"]
    for lvl, cap, k1, m1, at, slack, rmap in (
            ('facility', kj, kj1, jm1, f_at, ~f_at, fac_rose),
            ('pair', kp, kp1, pm1, p_at, p_slack, {k: v[pair_fac] for k, v in fac_rose.items()})):
        anyr = np.any(np.vstack(list(rmap.values())), axis=0)
        groups = [('at cap', at), ('not at cap', slack)]
        for k in ('surgeons', 'rooms', 'laparoscopes'):
            groups += [(f'at cap, {k} rose', at & rmap[k]), (f'at cap, {k} did not', at & ~rmap[k])]
        groups += [('at cap, any resource rose', at & anyr), ('at cap, none rose', at & ~anyr)]
        for g, mask in groups:
            q = rates(cap, k1, m1, mask); res[lvl][g] = q
            if q['n']:
                L.append(f"{lvl:9s}{g:30s}{q['n']:>6d}{q['roll_exceed']*100:>17.1f}%{q['month_exceed']*100:>15.1f}%{q['median_ratio']:>13.2f}")
            else:
                L.append(f"{lvl:9s}{g:30s}{0:>6d}{'-':>18s}{'-':>16s}{'-':>13s}")
        L.append('')
    # ---- placebo: urgent volume, same units and groups ----
    ujm0, upm0 = next_year_volumes(t, J, Y.pair_keys, urgent=True)
    ujm1, upm1 = next_year_volumes(t1, J, Y.pair_keys, urgent=True)
    ukj0, ukp0, ukj1, ukp1 = S.r3(ujm0), S.r3(upm0), S.r3(ujm1), S.r3(upm1)
    res['placebo_urgent'] = {'facility': {}, 'pair': {}}
    L += [f'PLACEBO, urgent volume {t} -> {t1} (units with urgent kappa_{t} > 0.5 only)',
          f"{'level':9s}{'group':30s}{'n':>6s}{'kappa_t1>kappa_t':>18s}{'months>kappa_t':>16s}{'median k1/k':>13s}"]
    for lvl, cap, k1, m1, at, slack, rmap in (
            ('facility', ukj0, ukj1, ujm1, f_at, ~f_at, fac_rose),
            ('pair', ukp0, ukp1, upm1, p_at, p_slack, {k: v[pair_fac] for k, v in fac_rose.items()})):
        ok = cap > 0.5
        anyr = np.any(np.vstack(list(rmap.values())), axis=0)
        groups = [('at cap', at), ('not at cap', slack)]
        for k in ('surgeons', 'rooms', 'laparoscopes'):
            groups += [(f'at cap, {k} rose', at & rmap[k]), (f'at cap, {k} did not', at & ~rmap[k])]
        groups += [('at cap, any resource rose', at & anyr), ('at cap, none rose', at & ~anyr)]
        for g, mask in groups:
            q = rates(cap, k1, m1, mask & ok); res['placebo_urgent'][lvl][g] = q
            L.append(f"{lvl:9s}{g:30s}{q['n']:>6d}" + (f"{q['roll_exceed']*100:>17.1f}%{q['month_exceed']*100:>15.1f}%{q['median_ratio']:>13.2f}"
                     if q['n'] else f"{'-':>18s}{'-':>16s}{'-':>13s}"))
        L.append('')
    out[f'{t}->{t1}'] = res
txt = '\n'.join(L); print(txt[len(__doc__):])
open('dist/review/cap_test.txt', 'w').write(txt + '\n')
json.dump(out, open('dist/review/cap_test.json', 'w'), indent=1)

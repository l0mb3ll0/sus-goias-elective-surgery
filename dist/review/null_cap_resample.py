"""T2 (dist/sprint/PREREG_round3.md): OVERDISPERSED resampling null for the cap test. Same as null_cap.py except the simulated months.

RESAMPLING. For each facility, 12 month indices are drawn with replacement from its 12 observed year-t months for year t, and an independent 12 for t+1; every pair of the facility
uses the same indices (within-facility co-movement preserved; facility series = sum of its pairs exactly as observed). Urgent volume likewise from observed urgent months.
Original docstring of the Poisson version follows.

Items 1-2: stationary-Poisson null for the cap test, with size of exceedance.

NULL. Each (facility, procedure) pair's monthly elective volume is Poisson at its year-t mean
monthly rate (12 months for year t, 12 independent months for t+1). A facility's volume is the
sum of its pairs, so facility and pair series are consistent, as in the data. kappa is built
with the same statistic (largest 3-month rolling mean; pair kappa floored at 0.5). The LP is
re-solved on the simulated kappa (demand, stay lengths lambda, beds B held at point values;
only kappa changes). AT CAP is defined from that solve with the paper's thresholds
(facility served/kappa_j > 0.95; non-floored pair kappa_jp > 0.5 and served/kappa_jp > 0.95).
Exceedance = simulated kappa_{t+1} > simulated kappa_t. 200 runs per transition.

SIZE of exceedance = median over exceeding units of kappa_{t+1}/kappa_t - 1.

RESOURCE ROWS. Resource changes are not simulated. The observed facility flags (surgeons / rooms /
laparoscopes rose) are applied to the simulated at-cap set, i.e. the null assumes volume is
independent of resource change. Rows with fewer than 5 units in a run are dropped from that run.

URGENT. Urgent volume is simulated the same way (pairs Poisson at their urgent mean; facility =
pair sum + Poisson residual), independently of elective. At-cap membership comes from the
ELECTIVE simulated solve, as in the observed placebo; units with simulated urgent kappa_t <= 0.5
are dropped, as observed.
"""
import sys, json
import numpy as np, pandas as pd
from scipy import sparse
from scipy.optimize import linprog
sys.path.insert(0, 'dist/review')
_src = open('dist/review/cap_test.py', encoding='utf-8').read()
exec(compile(_src[:_src.index('\nout, L =')], 'cap_test_head', 'exec'))   # S, rose, next_year_volumes, ...

NRUN, SEED = 200, 20261105
MINN = 5


def lam_point(Y):
    w = np.ones(len(Y.key)); wJ = w[Y.sel]
    cnt = np.bincount(Y.pairv_J, weights=wJ, minlength=Y.npair)
    sm = np.bincount(Y.pairv_J, weights=wJ*Y.dias_J, minlength=Y.npair)
    pc = np.bincount(Y.pkv_J, weights=wJ, minlength=Y.NP)
    ps = np.bincount(Y.pkv_J, weights=wJ*Y.dias_J, minlength=Y.NP)
    pm = np.divide(ps, pc, out=np.zeros(Y.NP), where=pc > 0)
    return (sm + S.K*pm[Y.pair_pk])/(cnt + S.K)


def solve(Y, Cb, dem, kj, kp):
    res = linprog(Y.obj, A_ub=sparse.vstack([Cb, Y.Sc, Y.Pb]).tocsr(),
                  b_ub=np.concatenate([Y.B, kj, kp]), A_eq=Y.A, b_eq=dem, bounds=(0, None), method='highs')
    assert res.status == 0, res.status
    x = res.x[:Y.nx]
    return np.asarray(Y.Sc[:, :Y.nx] @ x).ravel(), np.bincount(Y.colpair, weights=x, minlength=Y.npair)


def stats(cap, k1, mask):
    n = int(mask.sum())
    if n == 0:
        return dict(n=0, exceed=np.nan, size=np.nan)
    ex = k1[mask] > cap[mask]
    pos = ex & (cap[mask] > 0)                      # size undefined where the cap is 0
    return dict(n=n, exceed=float(ex.mean()),
                size=float(np.median(k1[mask][pos]/cap[mask][pos] - 1)) if pos.any() else np.nan)


def rowdefs(at, slack, rmap):
    anyr = np.any(np.vstack(list(rmap.values())), axis=0)
    g = [('at cap', at), ('not at cap', slack)]
    for k in ('surgeons', 'rooms', 'laparoscopes'):
        g += [(f'at cap, {k} rose', at & rmap[k]), (f'at cap, {k} did not', at & ~rmap[k])]
    return g + [('at cap, any resource rose', at & anyr), ('at cap, none rose', at & ~anyr)]


def poisson_series(rng, mu, n=24):
    return rng.poisson(mu[:, None], size=(len(mu), n)).astype(float)


out, L = {}, [__doc__]
rng = np.random.default_rng(SEED)
for t, t1 in (('2023', '2024'), ('2024', '2025')):
    Y = S.Year(t); one = np.ones(len(Y.key)); J = list(Y.J)
    r = S.gap_parts(Y, one, one, one)
    kj, kp, jm, pmm = S.kappas(Y, one)
    fac, served = np.asarray(Y.Sc[:, :Y.nx] @ r['x']).ravel(), np.bincount(Y.colpair, weights=r['x'], minlength=Y.npair)
    f_at = fac/np.maximum(kj, 1e-12) > 0.95
    nf = kp > 0.5001; p_at = nf & (served/kp > 0.95); p_sl = nf & ~p_at
    jpos = {c: n for n, c in enumerate(J)}; pair_fac = np.array([jpos[j] for j, p in Y.pair_keys])
    R = rose(t1); fj = pd.Index(J)
    frose = {k: v.reindex(fj).fillna(False).to_numpy(bool) for k, v in R.items()}
    prose = {k: v[pair_fac] for k, v in frose.items()}
    # observed elective and urgent
    jm1, pm1 = next_year_volumes(t1, J, Y.pair_keys); kj1, kp1 = S.r3(jm1), S.r3(pm1)
    ujm0, upm0 = next_year_volumes(t, J, Y.pair_keys, urgent=True)
    ujm1, upm1 = next_year_volumes(t1, J, Y.pair_keys, urgent=True)
    ukj0, ukp0, ukj1, ukp1 = S.r3(ujm0), S.r3(upm0), S.r3(ujm1), S.r3(upm1)
    obs = {}
    for lvl, cap, k1, at, sl, rm, ucap, uk1 in (('facility', kj, kj1, f_at, ~f_at, frose, ukj0, ukj1),
                                               ('pair', kp, kp1, p_at, p_sl, prose, ukp0, ukp1)):
        for g, m in rowdefs(at, sl, rm):
            obs[('elective', lvl, g)] = stats(cap, k1, m)
            obs[('urgent', lvl, g)] = stats(ucap, uk1, m & (ucap > 0.5))
    # null
    mu_p = pmm.mean(axis=1); mu_f = jm.mean(axis=1)
    u_mu_p = upm0.mean(axis=1); u_mu_f = ujm0.mean(axis=1)
    u_res = np.maximum(u_mu_f - np.bincount(pair_fac, weights=u_mu_p, minlength=len(J)), 0)
    lam = lam_point(Y); Cb = sparse.coo_matrix((lam[Y.colpair], (Y.rC, Y.cC)), shape=(len(J), Y.nx+Y.nu)).tocsr()
    dem = r['dem']
    sims = {k: [] for k in obs}; nat = []
    for run in range(NRUN):
        idx = rng.integers(0, 12, size=(len(J), 24))                       # 12 month indices for year t, 12 for t+1, per facility
        P = pmm[np.arange(len(pmm))[:, None], idx[pair_fac]]; F = jm[np.arange(len(J))[:, None], idx]
        skj0, skj1 = S.r3(F[:, :12]), S.r3(F[:, 12:])
        skp0, skp1 = np.maximum(S.r3(P[:, :12]), 0.5), np.maximum(S.r3(P[:, 12:]), 0.5)
        fa, sv = solve(Y, Cb, dem, skj0, skp0)
        s_f_at = fa/np.maximum(skj0, 1e-12) > 0.95
        s_nf = skp0 > 0.5001; s_p_at = s_nf & (sv/skp0 > 0.95); s_p_sl = s_nf & ~s_p_at
        nat.append((int(s_f_at.sum()), int(s_p_at.sum())))
        uidx = rng.integers(0, 12, size=(len(J), 24))
        UP = upm0[np.arange(len(upm0))[:, None], uidx[pair_fac]]; UF = ujm0[np.arange(len(J))[:, None], uidx]
        us = (S.r3(UF[:, :12]), S.r3(UF[:, 12:]), np.maximum(S.r3(UP[:, :12]), 0.5), np.maximum(S.r3(UP[:, 12:]), 0.5))
        for lvl, cap, k1, at, sl, rm, ucap, uk1 in (('facility', skj0, skj1, s_f_at, ~s_f_at, frose, us[0], us[1]),
                                                   ('pair', skp0, skp1, s_p_at, s_p_sl, prose, us[2], us[3])):
            for g, m in rowdefs(at, sl, rm):
                sims[('elective', lvl, g)].append(stats(cap, k1, m))
                sims[('urgent', lvl, g)].append(stats(ucap, uk1, m & (ucap > 0.5)))
        if (run+1) % 25 == 0: print(t, run+1, flush=True)
    res = {}
    L += [f'\n=== {t} -> {t1}: observed at-cap facilities {int(f_at.sum())}, pairs {int(p_at.sum())}; '
          f'null at-cap facilities mean {np.mean([a for a, b in nat]):.1f} (range {min(a for a, b in nat)}-{max(a for a, b in nat)}), '
          f'pairs mean {np.mean([b for a, b in nat]):.1f} (range {min(b for a, b in nat)}-{max(b for a, b in nat)}) ===',
          'exceed = share with kappa_t+1 > kappa_t; size = median kappa_t+1/kappa_t - 1 among exceeders; '
          'null = mean [2.5,97.5 pct] over runs; p = share of runs with null exceed >= observed (ties count)']
    for kind in ('elective', 'urgent'):
        L += ['', f'{kind.upper()}', f"{'level':9s}{'group':28s}{'n_obs':>6s}{'obs exceed':>11s}{'null exceed [2.5,97.5]':>26s}{'p':>7s}"
              f"{'obs size':>10s}{'null size':>12s}{'n_null':>8s}"]
        for lvl in ('facility', 'pair'):
            for (kd, lv, g), o in obs.items():
                if kd != kind or lv != lvl: continue
                sm = sims[(kd, lv, g)]
                ex = np.array([s['exceed'] for s in sm]); sz = np.array([s['size'] for s in sm]); nn = np.array([s['n'] for s in sm])
                ok = nn >= MINN
                if o['n'] == 0 or ok.sum() == 0:
                    L.append(f'{lvl:9s}{g:28s}{o["n"]:>6d}   (no observed units)' if o['n'] == 0 else f'{lvl:9s}{g:28s}{o["n"]:>6d}   (null: too few units)')
                    res[f'{kd}|{lvl}|{g}'] = dict(obs=o); continue
                e, z = ex[ok], sz[ok]
                p = float((e >= o['exceed'] - 1e-12).mean())
                osz = f"{o['size']*100:.0f}%" if not np.isnan(o['size']) else '-'
                nz = f"{np.nanmedian(z)*100:.0f}%" if np.isfinite(z).any() else '-'
                L.append(f"{lvl:9s}{g:28s}{o['n']:>6d}{o['exceed']*100:>10.1f}%"
                         f"{np.mean(e)*100:>9.1f}% [{np.percentile(e,2.5)*100:4.1f},{np.percentile(e,97.5)*100:4.1f}]{p:>8.3f}"
                         f"{osz:>10s}{nz:>12s}{int(np.mean(nn[ok])):>8d}")
                res[f'{kd}|{lvl}|{g}'] = dict(obs=o, null_exceed_mean=float(np.mean(e)), null_exceed_lo=float(np.percentile(e, 2.5)),
                    null_exceed_hi=float(np.percentile(e, 97.5)), p=p, null_size_median=float(np.nanmedian(z)) if np.isfinite(z).any() else None,
                    null_n_mean=float(np.mean(nn[ok])), runs_used=int(ok.sum()))
    out[f'{t}->{t1}'] = dict(res=res, obs_at_cap=(int(f_at.sum()), int(p_at.sum())), null_at_cap=nat)
txt = '\n'.join(L); print(txt[len(__doc__):])
open('dist/review/null_cap_resample.txt', 'w').write(txt + '\n')
json.dump(out, open('dist/review/null_cap_resample.json', 'w'), indent=1)

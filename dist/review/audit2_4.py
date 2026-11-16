"""Audit items 2, 3, 4 (PREREG_round4.md). Aggregates only; no identifiers."""
import sys, json, numpy as np
sys.path.insert(0, 'dist/review')
import audit_year as AY
out, L = {}, []
def P(s): print(s, flush=True); L.append(s)
def summ(tag, Y, r):
    k = r['kj']; ratio = k.sum()/r['dem'].sum(); fa = r['fac']/np.maximum(k, 1e-12) > 0.95; bb = r['use']/r['B'] > 0.95
    jm = Y.kappas()[2]; mu = jm.mean(axis=1); single = jm.max(axis=1)
    pos = jm > 0; first = np.argmax(pos, axis=1); last = 11 - np.argmax(pos[:, ::-1], axis=1)
    inter = np.array([((~pos[j, first[j]:last[j]+1]).any()) if pos[j].any() else False for j in range(Y.nj)])
    d = dict(n_fac=Y.nj, gap_J=r['gap_J'], gap_all=r['gap_all'], unmet=r['unmet'], ratio_cap_over_demand=float(ratio), sum_cap_over_sum_mean=float(k.sum()/mu.sum()),
             single_over_roll=float(single.sum()/k.sum()), at_cap=int(fa.sum()), bed_bound=int(bb.sum()), overlap=int((fa & bb).sum()), bed_util=float(r['use'].sum()/r['B'].sum()),
             interleaved_zero_facilities=int(inter.sum()), obs_over_B=int((np.bincount(Y.jkv_J, weights=Y.dias_J, minlength=Y.nj)/12.0 > r['B']).sum()), outside_window_records=Y.n_outside)
    out[tag] = d; P(f"{tag:34s} nJ {d['n_fac']:3d} gapJ {100*d['gap_J']:5.2f} gapAll {100*d['gap_all']:5.2f} unmet {100*d['unmet']:4.1f} cap/dem {d['ratio_cap_over_demand']:.3f} capSum/meanSum {d['sum_cap_over_sum_mean']:.3f} "
                    f"single/roll {d['single_over_roll']:.3f} atcap {d['at_cap']:3d} bedbound {d['bed_bound']:2d} overlap {d['overlap']} util {d['bed_util']:.3f} interleaved0 {d['interleaved_zero_facilities']:3d} obsElec>B {d['obs_over_B']:3d}")
    return fa
cfgs = [('paper', {}), ('days_actual', dict(days='actual')), ('bed_all_30', dict(bed='all')), ('bed_all_actual', dict(bed='all', days='actual')), ('time_saida', dict(time='saida')), ('window_jul', dict(window='jul'))]
res = {}
for y in ('2019', '2023', '2025'):
    for name, kw in cfgs:
        if name == 'window_jul' and y == '2019': continue
        Y = AY.AYear(y, **kw); r = Y.solve(); fa = summ(f'{y}|{name}', Y, r); res[(y, name)] = (Y, r, fa)
# cap-test observed rates under timing variants (facility level, at-cap exceedance, kappa_{t+1} > kappa_t)
def rate(name, y0, y1, kw):
    Y0, r0, fa = res[(y0, name)] if (y0, name) in res else (None, None, None)
    if Y0 is None:
        Y0 = AY.AYear(y0, **kw); r0 = Y0.solve(); fa = r0['fac']/np.maximum(r0['kj'], 1e-12) > 0.95
    Y1 = AY.AYear(y1, **kw); k1 = dict(zip(Y1.J, Y1.kappas()[0]))
    kn = np.array([k1.get(j, 0.0) for j in Y0.J]); ex = kn > r0['kj']
    return float(ex[fa].mean()), float(ex[~fa].mean()), int(fa.sum())
for name, kw in [('paper', {}), ('time_saida', dict(time='saida')), ('window_jul', dict(window='jul'))]:
    for y0, y1 in (('2023', '2024'), ('2024', '2025')):
        try:
            a_, n_, k_ = rate(name, y0, y1, kw); out[f'captest|{name}|{y0}->{y1}'] = dict(at_cap_rate=a_, not_at_cap_rate=n_, n_at_cap=k_); P(f'cap test {name:11s} {y0}->{y1}: at cap {100*a_:5.1f}% (n {k_}), not at cap {100*n_:5.1f}%')
        except Exception as e: P(f'cap test {name} {y0}->{y1} FAILED {type(e).__name__} {e}')
json.dump(out, open('dist/review/audit2_4.json', 'w'), indent=1); open('dist/review/audit2_4.txt', 'w').write('\n'.join(L) + '\n')

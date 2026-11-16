"""Decompose the capability/demand ratio (1.37 / 1.32 / 1.16) into zero months vs real variation.

The ratio is sum_j kappa_j / D: kappa_j is facility j's largest 3-month rolling mean of in-state
elective volume over the year's 12 months, summed over the model's facility set J, and D is all
in-state elective demand per month. Built with the bootstrap's own Year class at unit weights.

For each facility, with m = annual volume / 12, n_span = months from first to last active month,
n_pos = months with positive volume:

  kappa_j - m = [m_span - m]                       zeros outside the active span (entry / exit)
              + [m_pos  - m_span]                   zeros inside the span: volume concentrated
              + Zw                                  zeros inside the span: effect on 3-month windows
              + V                                   real variation among active months

Zw and V are a Shapley split over two counterfactual series: positive months flattened to m_pos
(zeros kept) and zero months dropped (variation kept). kappa(no zeros, no variation) = m_pos.
With fewer than 3 active months no window exists after dropping zeros, so that series uses m_pos.
Summed over J and divided by D the four terms plus sum(m)/D reproduce the ratio exactly.

Batching signature (diagnostic only): a run of interior zero months followed by a month of at
least 1.5 x m_pos, the pattern a bill covering several months leaves.
"""
import sys, json, numpy as np
sys.path.insert(0, 'dist/review')
import _boot_src as S

def r3row(v):
    return S.r3(v[None, :])[0] if len(v) >= S.ROLL else None

out, lines = {}, []
for y in ('2019', '2023', '2025'):
    Y = S.Year(y)
    one = np.ones(len(Y.key))
    kj, _, jm, _ = S.kappas(Y, one)
    D = float((np.bincount(Y.cellv, weights=one, minlength=Y.nu)/12.0).sum())
    R = kj.sum()/D
    T = dict(base=0., ext=0., inter_conc=0., inter_win=0., var=0.)
    nf = dict(any_int_zero=0, batch_sig=0, ext_zero=0)
    batch_part = 0.
    for j in range(len(Y.J)):
        v = jm[j]; tot = v.sum(); m = tot/12.0
        pos = np.flatnonzero(v > 0)
        if tot == 0:
            continue
        span = pos[-1] - pos[0] + 1; npos = len(pos)
        m_span, m_pos = tot/span, tot/npos
        kZV = kj[j]
        flat = np.where(v > 0, m_pos, 0.0); kZ0 = r3row(flat)
        k0V = r3row(v[pos]) if npos >= S.ROLL else m_pos
        k00 = m_pos
        Zw = 0.5*((kZV - k0V) + (kZ0 - k00)); V = 0.5*((kZV - kZ0) + (k0V - k00))
        T['base'] += m; T['ext'] += m_span - m; T['inter_conc'] += m_pos - m_span
        T['inter_win'] += Zw; T['var'] += V
        assert abs((m_span-m)+(m_pos-m_span)+Zw+V - (kZV-m)) < 1e-9
        inner = v[pos[0]:pos[-1]+1]
        if (inner == 0).any():
            nf['any_int_zero'] += 1
            sig = any(inner[k] >= 1.5*m_pos and inner[k-1] == 0 for k in range(1, len(inner)))
            if sig:
                nf['batch_sig'] += 1; batch_part += (m_pos - m_span) + Zw
        if span < 12:
            nf['ext_zero'] += 1
    tot = sum(T.values())
    assert abs(tot - kj.sum()) < 1e-6
    zero_int = T['inter_conc'] + T['inter_win']
    excess = R - T['base']/D
    r = {k: v/D for k, v in T.items()}
    r.update(ratio=R, J=len(Y.J), D=D, zero_interior=zero_int/D, zero_total=(zero_int+T['ext'])/D,
             excess_over_base=excess, facilities=nf, interior_zero_at_batch_signature=batch_part/D)
    out[y] = r
    lines += [f"{y}: ratio {R:.3f}  (|J| {len(Y.J)}, demand {D:,.0f}/month)",
              f"   base: volume at in-scope facilities, sum(m)/D        {r['base']:.3f}",
              f"   + zeros outside the active span (entry/exit)         {r['ext']:+.3f}",
              f"   + zeros inside the span, concentration               {r['inter_conc']:+.3f}",
              f"   + zeros inside the span, 3-month window effect       {r['inter_win']:+.3f}",
              f"   + real variation among active months                 {r['var']:+.3f}",
              f"   = {r['base']+r['ext']+r['inter_conc']+r['inter_win']+r['var']:.3f}   (check)",
              f"   excess over base {excess:.3f}: zero months {r['zero_total']:.3f} "
              f"({100*r['zero_total']/excess:.0f}%), of which interior {r['zero_interior']:.3f} "
              f"({100*r['zero_interior']/excess:.0f}%) and entry/exit {r['ext']:.3f} "
              f"({100*r['ext']/excess:.0f}%); real variation {r['var']:.3f} ({100*r['var']/excess:.0f}%)",
              f"   facilities with interior zero months {nf['any_int_zero']}; with batching signature "
              f"{nf['batch_sig']} (carrying {r['interior_zero_at_batch_signature']:.3f} of the interior-zero "
              f"term); active part-year only {nf['ext_zero']}", '']
txt = '\n'.join(lines)
print(txt)
open('dist/review/ratio_decomp.txt', 'w').write(__doc__ + '\n' + txt + '\n')
json.dump(out, open('dist/review/ratio_decomp.json', 'w'), indent=1)

"""Split the 'real variation' term of ratio_decomp into a counting-noise floor and the rest.

Null: each facility's active months are independent Poisson draws at a constant rate m_pos.
Under that null the largest 3-month rolling mean still exceeds m_pos, by sampling alone. The
expected excess, E[max r3] - m_pos, estimated by 2,000 simulations per facility, is the noise
floor. V - noise is variation beyond what a constant rate would produce. Poisson understates
dispersion if cases arrive in clusters, so the noise floor here is a lower bound.
"""
import sys, json, numpy as np
sys.path.insert(0, 'dist/review')
import _boot_src as S
rng = np.random.default_rng(7)
dec = json.load(open('dist/review/ratio_decomp.json'))
lines = []
for y in ('2019', '2023', '2025'):
    Y = S.Year(y); one = np.ones(len(Y.key))
    kj, _, jm, _ = S.kappas(Y, one)
    D = float((np.bincount(Y.cellv, weights=one, minlength=Y.nu)/12.0).sum())
    noise = 0.0
    for j in range(len(Y.J)):
        v = jm[j]; pos = v[v > 0]
        if len(pos) < S.ROLL:
            continue
        m_pos = pos.mean()
        sim = rng.poisson(m_pos, size=(2000, len(pos))).astype(float)
        noise += S.r3(sim).mean() - m_pos
    V = dec[y]['var']; n = noise/D
    dec[y]['var_noise_floor'] = n; dec[y]['var_beyond_noise'] = V - n
    ex = dec[y]['excess_over_base']
    lines.append(f"{y}: real variation {V:.3f} = Poisson noise floor {n:.3f} ({100*n/ex:.0f}% of excess) "
                 f"+ beyond noise {V-n:.3f} ({100*(V-n)/ex:.0f}% of excess)")
txt = '\n'.join(lines); print(txt)
open('dist/review/ratio_decomp.txt', 'a').write('\nNOISE FLOOR (dist/review/ratio_noise.py)\n' + __doc__ + '\n' + txt + '\n')
json.dump(dec, open('dist/review/ratio_decomp.json', 'w'), indent=1)

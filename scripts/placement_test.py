"""Out-of-sample test: did capability appear where the 2023 model said it was worth most?

The literal test -- rank 2023 pairs by dual, check whether pairs newly appearing
in 2025 sit at the top -- is not identified. A pair absent from the 2023 option
set has no 2023 dual, so new pairs cannot be scored on the ranking they are
supposed to be tested against. Two well-posed versions are run instead.

  Test A (pair margin)  Among pairs in scope and non-floored in 2023, does the
                        2023->2025 growth in kappa_jp concentrate in pairs the
                        2023 model priced highly?
  Test B (facility margin)  Do pairs genuinely new in 2025 appear at facilities
                        whose 2023 duals summed high?

Value is the dual times a fixed increment INC, so it is expressed in
region-crossings saved per month rather than per case.

Null in both cases: the top group is drawn at random without replacement with
probability proportional to facility size, so a finding is not just "big
facilities grow".

    python -m scripts.placement_test [--write]
"""
import json, io, sys
import numpy as np, pandas as pd

INC = 5.0          # cases per month
DECILE = 0.10
B = 5000
SEED = 20260807
NJ = 'paper/numbers.json'

rng = np.random.default_rng(SEED)

d23 = pd.read_parquet('paper/duals_2023_roll3.parquet')
d25 = pd.read_parquet('paper/duals_2025_roll3.parquet')
f23 = pd.read_parquet('paper/fac_2023_roll3.parquet')

d23['value'] = d23.dual * INC
size = dict(zip(f23.j, f23.cap_cases))


def concentration(value, weight, growth, n_top, draws=B):
    """Share of `growth` in the top `n_top` by `value`, against a size-weighted null."""
    order = np.argsort(-value)
    top = order[:n_top]
    obs = growth[top].sum() / growth.sum()
    p = weight / weight.sum()
    idx = np.arange(len(value))
    null = np.empty(draws)
    for b in range(draws):
        pick = rng.choice(idx, size=n_top, replace=False, p=p)
        null[b] = growth[pick].sum() / growth.sum()
    return obs, null


# ---------------- Test A: pair margin ----------------
a = d23[d23.kappa > 0.5001][['j', 'p', 'kappa', 'value']].copy()
a = a.merge(d25[['j', 'p', 'kappa']].rename(columns={'kappa': 'kappa25'}), on=['j', 'p'], how='left')
a['kappa25'] = a.kappa25.fillna(0.0)
a['growth'] = (a.kappa25 - a.kappa).clip(lower=0)
a['size'] = a.j.map(size).fillna(0.0)
a = a[a['size'] > 0].reset_index(drop=True)

nA = max(1, int(round(len(a) * DECILE)))
obsA, nullA = concentration(a.value.values, a['size'].values, a.growth.values, nA)
pA = float((nullA >= obsA).mean())

# ---------------- Test B: facility margin ----------------
new25 = d25.merge(d23[['j', 'p']].assign(seen=1), on=['j', 'p'], how='left')
new25 = new25[new25.seen.isna()]
fv = d23.groupby('j').value.sum().rename('fac_value').reset_index()
fv['size'] = fv.j.map(size).fillna(0.0)
fv = fv[fv['size'] > 0].reset_index(drop=True)
cnt = new25.groupby('j').size().rename('n_new')
fv['n_new'] = fv.j.map(cnt).fillna(0.0).values

nB = max(1, int(round(len(fv) * DECILE)))
obsB, nullB = concentration(fv.fac_value.values, fv['size'].values, fv.n_new.values, nB)
pB = float((nullB >= obsB).mean())

def mde(null, power=0.80):
    """Smallest true concentration this test rejects at 5 per cent with `power`.

    The critical value is the null's 95th percentile, which gives 50 per cent
    power. Shifting the sampling distribution up by z_power standard deviations
    gives the conventional 80 per cent figure. The null's spread is used for the
    alternative's, which is the usual approximation for a share statistic.
    """
    from scipy.stats import norm
    crit = float(np.quantile(null, 0.95))
    return crit, float(crit + norm.ppf(power)*null.std(ddof=1))

critA, mdeA = mde(nullA)
critB, mdeB = mde(nullB)

res = {
    'increment_cases_mo': INC, 'top_fraction': DECILE, 'draws': B, 'seed': SEED,
    'A_crit_5pct': critA, 'A_mde_80pct_power': mdeA, 'A_null_sd': float(nullA.std(ddof=1)),
    'B_crit_5pct': critB, 'B_mde_80pct_power': mdeB, 'B_null_sd': float(nullB.std(ddof=1)),
    'A_pairs': int(len(a)), 'A_top_n': nA,
    'A_growth_total': float(a.growth.sum()),
    'A_observed_share': float(obsA), 'A_null_mean': float(nullA.mean()),
    'A_null_p95': float(np.quantile(nullA, 0.95)), 'A_p': pA,
    'B_facilities': int(len(fv)), 'B_top_n': nB,
    'B_new_pairs_total': float(fv.n_new.sum()),
    'B_observed_share': float(obsB), 'B_null_mean': float(nullB.mean()),
    'B_null_p95': float(np.quantile(nullB, 0.95)), 'B_p': pB,
    'note': 'new-in-2025 pairs have no 2023 dual; test A uses growth in kappa on '
            'surviving pairs, test B uses facility-aggregated 2023 value',
}

if '--write' in sys.argv:
    d = json.load(io.open(NJ, encoding='utf-8'))
    d['placement_test'] = res
    json.dump(d, io.open(NJ, 'w', encoding='utf-8'), indent=1)
    print('written', NJ)

print(f'Test A, pair margin: {len(a)} non-floored 2023 pairs, top decile n={nA}')
print(f'  total kappa growth to 2025: {a.growth.sum():.0f} cases/mo')
print(f'  observed share in top decile by model value: {obsA*100:.1f}%')
print(f'  null (size-weighted) mean {nullA.mean()*100:.1f}%, 95th pct {np.quantile(nullA,0.95)*100:.1f}%, p = {pA:.4f}')
print()
print(f'Test B, facility margin: {len(fv)} facilities, top decile n={nB}')
print(f'  pairs new in 2025: {fv.n_new.sum():.0f}')
print(f'  observed share at top-decile facilities by 2023 value: {obsB*100:.1f}%')
print(f'  null (size-weighted) mean {nullB.mean()*100:.1f}%, 95th pct {np.quantile(nullB,0.95)*100:.1f}%, p = {pB:.4f}')
print()
print('minimum detectable effect, as a top-decile concentration:')
print(f'  pair margin:     reject above {critA*100:.1f}% (50% power), {mdeA*100:.1f}% at 80% power'
      f'  [null mean {nullA.mean()*100:.1f}%, lift {mdeA/nullA.mean():.2f}x]')
print(f'  facility margin: reject above {critB*100:.1f}% (50% power), {mdeB*100:.1f}% at 80% power'
      f'  [null mean {nullB.mean()*100:.1f}%, lift {mdeB/nullB.mean():.2f}x]')

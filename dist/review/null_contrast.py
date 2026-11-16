"""Final-batch item 3: at-cap minus not-at-cap exceedance contrast with per-run nulls (Poisson and resampling), 2023->24 and 2024->25, plus a fixed-set rerun on the facilities that are always at cap in 2023 (v1 face intervals, tolerance 1e-6) with a no-re-solve fixed-set null.
Usage: python dist/review/null_contrast.py poisson|resample"""
import sys, json
MODE = sys.argv[1]; sys.argv = ['x']
src = open('dist/review/null_cap.py' if MODE == 'poisson' else 'dist/review/null_cap_resample_v2.py', encoding='utf-8').read()
# record per-run contrast: patch the loop where at-cap sets are defined, keep everything else identical
src = src.replace("nat.append((int(s_f_at.sum()), int(s_p_at.sum())))", "nat.append((int(s_f_at.sum()), int(s_p_at.sum()))); CON.append(float((skj1 > skj0)[s_f_at].mean() - (skj1 > skj0)[~s_f_at].mean()) if (s_f_at.any() and (~s_f_at).any()) else float('nan'))")
src = src.replace("out, L = {}, [__doc__]", "out, L = {}, [__doc__]; CONS = {}")
src = src.replace("sims = {k: [] for k in obs}; nat = []", "sims = {k: [] for k in obs}; nat = []; CON = []")
src = src.replace("    out[f'{t}->{t1}'] = dict(res=res, obs_at_cap=(int(f_at.sum()), int(p_at.sum())), null_at_cap=nat)",
 "    import numpy as _np\n    c_obs = float((kj1 > kj)[f_at].mean() - (kj1 > kj)[~f_at].mean()); cc = _np.array([c for c in CON if c == c])\n    out[f'{t}->{t1}'] = dict(res=res, obs_at_cap=(int(f_at.sum()), int(p_at.sum())), null_at_cap=nat, contrast_obs=c_obs, contrast_null_mean=float(cc.mean()), contrast_null_lo=float(_np.percentile(cc, 2.5)), contrast_null_hi=float(_np.percentile(cc, 97.5)), contrast_p_ge=float((cc >= c_obs).mean()), runs=int(len(cc)))\n    print('CONTRAST', t, c_obs, cc.mean(), _np.percentile(cc, [2.5, 97.5]), (cc >= c_obs).mean(), flush=True)")
src = src.replace("null_cap.txt", f"null_contrast_{MODE}.txt").replace("null_cap.json", f"null_contrast_{MODE}.json").replace("null_cap_resample_v2.txt", f"null_contrast_{MODE}.txt").replace("null_cap_resample_v2.json", f"null_contrast_{MODE}.json")
exec(compile(src, 'null_contrast_exec', 'exec'))

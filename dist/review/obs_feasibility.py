"""Final correction round 2, check C: is the observed allocation a feasible point of the program?
Aggregates observed elective admissions (records at facilities in J, pairs in scope) to municipality x facility x subgroup,
monthly (count/12), and tests every pair cap, facility-total cap and the bed-day row. Run from the repository root with
data/interim present (python -m dist.review.obs_feasibility is not needed: python dist/review/obs_feasibility.py).
Result: dist/review/obs_feasibility.json (0 cap violations; bed row exceeded at 1 / 2 / 4 facilities).
"""
import sys, json, numpy as np
sys.path.insert(0, 'dist/review')
import audit_year as AY
out={}
for y in ('2019','2023','2025'):
    Y=AY.AYear(y); r=Y.solve()
    kj,kp,B,lam,Cb=r['kj'],r['kp'],r['B'],r['lam'],r['Cb']
    # observed allocation aggregated to (i,j,p) restricted to J, pair in scope (sel): monthly = count/12
    sel=Y.sel
    pairk=Y.pairv_J; jk=Y.jkv_J
    n_pair=np.bincount(pairk,minlength=Y.npair)/12.0
    n_fac=np.bincount(jk,minlength=Y.nj)/12.0
    # municipality x facility x subgroup aggregation: check every (i,j,p) triple used exists in the program's variable set (scope) -> pairk>=0 by construction of sel
    pair_viol=int((n_pair>kp*(1+1e-9)).sum()); fac_viol=int((n_fac>kj*(1+1e-9)).sum())
    lam_pair=lam[pairk]
    use_lam=np.bincount(jk,weights=lam_pair,minlength=Y.nj)/12.0
    use_act=np.bincount(jk,weights=Y.dias_J,minlength=Y.nj)/12.0
    bed_lam=int((use_lam>B*(1+1e-9)).sum()); bed_act=int((use_act>B*(1+1e-9)).sum())
    n_obs_in=len(sel); n_all=len(Y.cellv)
    # records at J facilities whose pair is missing from the scope? (sel excludes pairk<0)
    n_inJ=int(Y.inJ.sum())
    out[y]=dict(n_pairs=int(Y.npair),n_fac=int(Y.nj),pair_cap_viol=pair_viol,fac_cap_viol=fac_viol,
      max_pair_ratio=float((n_pair/kp).max()),max_fac_ratio=float((n_fac/kj).max()),
      bed_viol_lambda=bed_lam,bed_viol_actual_days=bed_act,
      records_all=int(n_all),records_inJ=n_inJ,records_in_program_vars=int(n_obs_in),
      share_demand_in_allocation=float(n_obs_in/n_all),gap_J=float(r['gap_J']))
    print(y,out[y],flush=True)
json.dump(out,open('dist/review/obs_feasibility.json','w'),indent=1)

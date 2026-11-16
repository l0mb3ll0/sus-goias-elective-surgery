"""Audit item 7: reverse order and Shapley split of the four-configuration decomposition, and served share as pi -> 0 (PREREG_round4.md)."""
import sys, json, io, contextlib
sys.argv = ['model_decomp']
src = open('scripts/model_decomp.py').read(); cut = src.index("el19,B19=load('2019')")
ns = {'__name__': 'decomp_exec'}; exec(compile(src[:cut], 'model_decomp_head', 'exec'), ns)
el19, B19 = ns['load']('2019'); el23, B23 = ns['load']('2023'); s19, s23 = ns['scope_of'](el19), ns['scope_of'](el23); run = ns['run']
res = {}
for pi in (4.0, 10.0):
    ns['PI'] = pi; r = {}
    with contextlib.redirect_stdout(io.StringIO()):
        r['A'] = run(el19, B19, s19, el19, 'A'); r['B'] = run(el23, B19, s19, el19, 'B'); r['C'] = run(el23, B23, s19, el23, 'C'); r['D'] = run(el23, B23, s23, el23, 'D')
        r['E'] = run(el23, B19, s23, el19, 'E')          # 2023 demand, 2019 capacity (B and caps), 2023 options
    adj = {k: v['travel_adj'] for k, v in r.items()}; served = {k: v['served']/v['demand_total'] for k, v in r.items()}
    tot = adj['B'] - adj['D']                              # improvement at 2023 demand from moving capacity AND options from 2019 to 2023
    opt_first = adj['B'] - adj['E']; cap_after = adj['E'] - adj['D']          # reverse order: options first, then capacity
    cap_first = adj['B'] - adj['C']; opt_after = adj['C'] - adj['D']          # forward order (paper): capacity first, then options
    sh_opt = 0.5*(opt_after + opt_first); sh_cap = 0.5*(cap_first + cap_after)
    res[str(pi)] = dict(adj=adj, served_share=served, total_improvement=tot, forward=dict(capacity=cap_first, options=opt_after), reverse=dict(options=opt_first, capacity=cap_after),
                        shapley=dict(options=sh_opt, capacity=sh_cap), options_share=dict(forward=opt_after/tot, reverse=opt_first/tot, shapley=sh_opt/tot))
    print(f"pi {pi:4.1f} | adj B {adj['B']:.3f} C {adj['C']:.3f} D {adj['D']:.3f} E {adj['E']:.3f} | served share B {served['B']:.3f} C {served['C']:.3f} D {served['D']:.3f} E {served['E']:.3f} | "
          f"options share of improvement: forward {opt_after/tot:.2f} reverse {opt_first/tot:.2f} Shapley {sh_opt/tot:.2f}", flush=True)
json.dump(res, open('dist/review/audit7_decomp_pi4_10.json', 'w'), indent=1)

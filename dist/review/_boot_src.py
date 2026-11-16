"""Shared LP construction for the review runs, taken verbatim from scripts/bootstrap_paired.py.

The module is not imported, because importing it runs os.makedirs('paper/_boot_paired') and
would recreate paper/ in the working tree. Instead its source up to the end of class Year is
executed as-is, with BOOT_CACHE pointed at dist/review/_cache. Nothing in that source writes
anything else. gap_parts() below is Year.gap() line for line, except that demand, kappa and the
remaining weighted quantities (lambda, observed baseline) can take different weight vectors,
and it also returns the optimum, unmet share and the solution.
"""
import os, sys, numpy as np
from scipy.optimize import linprog
from scipy import sparse

os.environ['BOOT_CACHE'] = 'dist/review/_cache'
_src = open('scripts/bootstrap_paired.py', encoding='utf-8').read()
_cut = _src.index("\nif __name__ == '__main__':")
_argv, sys.argv = sys.argv, ['bootstrap_paired']          # its argv parsing must not see ours
_ns = {'__name__': '_boot_src_exec'}
os.environ.setdefault('BOOT_LAM', 'jonly')   # review runs reproduce the earlier (J-only) shrinkage unless told otherwise
exec(compile(_src[:_cut], 'scripts/bootstrap_paired.py', 'exec'), _ns)
sys.argv = _argv
Year, ROLL, K = _ns['Year'], _ns['ROLL'], _ns['K']
LAM_TARGET = _ns['LAM_TARGET']
SRC_MD5 = __import__('hashlib').md5(_src.encode()).hexdigest()


def r3(M):
    cs = np.cumsum(np.pad(M, ((0, 0), (1, 0))), axis=1)
    return ((cs[:, ROLL:] - cs[:, :-ROLL]) / ROLL).max(axis=1)


def kappas(Y, w):
    wJ = w[Y.sel]
    jm = np.bincount(Y.jkv_J*Y.nmonth + Y.moy_J, weights=wJ,
                     minlength=len(Y.J)*Y.nmonth).reshape(len(Y.J), Y.nmonth)
    pmm = np.zeros((Y.npair, Y.nmonth)); np.add.at(pmm, (Y.pairv_J, Y.moy_J), wJ)
    return r3(jm), np.maximum(r3(pmm), 0.5), jm, pmm


def gap_parts(Y, w_dem, w_kap, w_rest):
    """Year.gap with demand / kappa / rest weighted separately. Same LP, same objective."""
    nu, nx, npair, J = Y.nu, Y.nx, Y.npair, Y.J
    dem = np.bincount(Y.cellv, weights=w_dem, minlength=nu)/12.0
    wJ = w_rest[Y.sel]
    cnt = np.bincount(Y.pairv_J, weights=wJ, minlength=npair)
    sm = np.bincount(Y.pairv_J, weights=wJ*Y.dias_J, minlength=npair)
    if LAM_TARGET == 'all':      # procedure mean over ALL elective in-state records (as scripts/model_run.py)
        pc = np.bincount(Y.pkv, weights=w_rest, minlength=Y.NP)
        ps = np.bincount(Y.pkv, weights=w_rest*Y.dias, minlength=Y.NP)
    else:
        pc = np.bincount(Y.pkv_J, weights=wJ, minlength=Y.NP)
        ps = np.bincount(Y.pkv_J, weights=wJ*Y.dias_J, minlength=Y.NP)
    pm = np.divide(ps, pc, out=np.zeros(Y.NP), where=pc > 0)
    lam = (sm + K*pm[Y.pair_pk])/(cnt + K)
    kj, kp, _, _ = kappas(Y, w_kap)
    Cb = sparse.coo_matrix((lam[Y.colpair], (Y.rC, Y.cC)), shape=(len(J), nx+nu)).tocsr()
    bub = np.concatenate([Y.B, kj, kp])
    res = linprog(Y.obj, A_ub=sparse.vstack([Cb, Y.Sc, Y.Pb]).tocsr(),
                  b_ub=bub, A_eq=Y.A, b_eq=dem, bounds=(0, None), method='highs')
    if res.status != 0:
        return dict(ok=False)
    x = res.x[:nx]
    obs = float(np.dot(wJ, Y.obsc_J)/wJ.sum())
    opt = float(np.dot(Y.c, x)/x.sum())
    return dict(ok=True, obs=obs, opt=opt, gap=(obs-opt)/obs, x=x, kj=kj, kp=kp,
                unmet=float(res.x[nx:].sum()/dem.sum()), dem=dem)

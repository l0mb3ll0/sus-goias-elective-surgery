"""Run scripts/sp_analysis.py unmodified, with read_parquet limited to the columns it uses.

The script reads every SP column for all 24 months (about 11 million rows x 36 columns),
which exceeds this machine's 7.6 GB and was killed (exit 137). Its logic touches only the
columns below, so projecting the read changes memory, not results. The script file is
executed as-is via runpy.
"""
import runpy, sys
import pandas as pd
import pyarrow.parquet as pq

USED = ['SP_AA', 'SP_MM', 'SP_NAIH', 'SP_CNES', 'SP_PROCREA', 'SP_ATOPROF', 'SP_PF_CBO',
        'SP_PF_DOC', 'SP_PJ_DOC', 'SP_M_HOSP', 'SP_TIPO', 'SP_TP_ATO', 'cm']
_orig = pd.read_parquet

def _projected(path, *a, **k):
    if 'columns' not in k:
        k['columns'] = [c for c in USED if c in pq.read_schema(path).names]
    return _orig(path, *a, **k)

pd.read_parquet = _projected
sys.argv = ['scripts/sp_analysis.py'] + sys.argv[1:]
runpy.run_path('scripts/sp_analysis.py', run_name='__main__')

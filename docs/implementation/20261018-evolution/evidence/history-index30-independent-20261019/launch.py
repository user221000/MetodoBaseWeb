"""The actual pytest child alone loads private loopback PG configuration."""
import sys
sys.dont_write_bytecode=True
import json
import os
from pathlib import Path

ROOT=Path(r'F:/mb-hidx30-qa-20261019')
OUT=Path(__file__).resolve().parent
TEMP=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-history-index30-independent-20261019')
PRIVATE=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-qa-pg55483-private-ok6hrpyq/env.json')
mode=sys.argv[1];phase=TEMP/mode
config=json.loads(PRIVATE.read_text(encoding='utf-8-sig'))
for key in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN']:os.environ[key]=config[key]
os.environ.update(QA_PHASE=str(phase),QA_PRIVATE=str(PRIVATE),METODOBASE_HISTORY_ORDERED_PROOF_DIR=str(phase),PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1')
os.chdir(ROOT);sys.path.insert(0,str(OUT));sys.path.insert(0,str(ROOT))
if mode=='maintained112':
    files=['tests/integration_personal_history_index_migrations.py','tests/integration_personal_history_ordered_query.py',
           'tests/test_personal_history_pagination.py','tests/test_personal_history_cursor.py',
           'tests/test_history_headers_followup.py','tests/test_history_error_boundary.py']
elif mode=='own8':files=[str(TEMP/'test_history30_review.py')]
else:raise ValueError('Unknown bounded review selection')
sys.argv=['tests/run_isolated.py',*files,'--rootdir='+str(ROOT),'-c',str(ROOT/'pytest.ini'),'--import-mode=importlib',
          '-p','observe','-q','--tb=short','--junitxml='+str(phase/'tests.xml')]
from tests.run_isolated import main
raise SystemExit(main())

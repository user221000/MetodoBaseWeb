"""Select frozen29 modules and an exact Temp driver, outside MAIN conftest ancestry."""
import sys
sys.dont_write_bytecode=True
import json
import os
from pathlib import Path

ROOT=Path(r'F:/MetodoBaseWeb-r12-core29-qa-20261019')
OUT=Path(__file__).resolve().parent
TEMP=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-r12-core29-independent-20261019')
PRIVATE=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-qa-pg55483-private-ok6hrpyq/env.json')
mode=sys.argv[1]
config=json.loads(PRIVATE.read_text(encoding='utf-8-sig'))
for key in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN']:
    os.environ[key]=config[key]
os.environ['QA_PRIVATE_ENV_PATH']=str(PRIVATE)
os.environ['QA_DB_RECEIPT']=str(OUT/(mode+'-owned-database-receipt.json'))
os.environ['PYTHONDONTWRITEBYTECODE']='1';os.environ['PYTHONUTF8']='1'
os.chdir(ROOT);sys.path.insert(0,str(OUT));sys.path.insert(0,str(ROOT))
if mode=='own-isolated':files=[str(TEMP/'test_r12_core29_review.py')]
elif mode=='preservation18':files=['tests/test_client_link_models.py','tests/integration_client_link_migrations.py']
else:raise ValueError('Unknown bounded QA selection')
sys.argv=['tests/run_isolated.py',*files,'--rootdir='+str(ROOT),'-c',str(ROOT/'pytest.ini'),'--import-mode=importlib',
          '-p','observe_owned_databases_v3','-q','--tb=short','--junitxml='+str(OUT/(mode+'.xml'))]
from tests.run_isolated import main
raise SystemExit(main())

"""Private PG configuration consumed only by the actual isolated pytest child."""
import sys
sys.dont_write_bytecode=True
import json
import os
from pathlib import Path

ROOT=Path(r'F:/MetodoBaseWeb-r12-core29-qa-20261019')
OUT=Path(__file__).resolve().parent
PRIVATE=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-qa-pg55483-private-ok6hrpyq/env.json')
mode=sys.argv[1]
config=json.loads(PRIVATE.read_text(encoding='utf-8-sig'))
for key in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN']:
    os.environ[key]=config[key]
os.environ['QA_PRIVATE_ENV_PATH']=str(PRIVATE)
os.environ['QA_DB_RECEIPT']=str(OUT/(mode+'-owned-database-receipt.json'))
os.environ['PYTHONDONTWRITEBYTECODE']='1';os.environ['PYTHONUTF8']='1'
os.chdir(ROOT);sys.path.insert(0,str(ROOT));sys.path.insert(0,str(OUT))
if mode=='author55':
    files=['tests/integration_client_link_canonical_postgres.py','tests/integration_client_link_projection_postgres.py',
           'tests/integration_client_link_root_review_adapted.py','tests/integration_client_link_owner_lock_review.py']
elif mode=='own':files=[str(OUT/'test_r12_core29_review.py')]
else:raise ValueError('Unknown bounded QA selection')
sys.argv=['tests/run_isolated.py',*files,'-p','observe_owned_databases','-q','--tb=short','--junitxml='+str(OUT/(mode+'.xml'))]
from tests.run_isolated import main
raise SystemExit(main())

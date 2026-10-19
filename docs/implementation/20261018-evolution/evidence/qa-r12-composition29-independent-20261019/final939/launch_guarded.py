"""Private config is loaded only in this actual isolated pytest child."""
import sys
sys.dont_write_bytecode=True
import json
import os
from pathlib import Path
ROOT=Path(r'F:/mb-r12-final939-qa-20261019')
OUT=Path(__file__).resolve().parent
TEMP=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-r12-composition29-independent-20261019\final939')
PRIVATE=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-qa-pg55483-private-ok6hrpyq/env.json')
def launch_main():
    mode=sys.argv[1];phase=TEMP/mode
    configuration=json.loads(PRIVATE.read_text(encoding='utf-8-sig'))
    for key in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN']:os.environ[key]=configuration[key]
    os.environ.update(QA_MODE=mode,QA_PHASE=str(phase),QA_PRIVATE=str(PRIVATE),METODOBASE_TEST_EVIDENCE_DIR=str(phase),
                      PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHON_DOTENV_DISABLED='1')
    os.chdir(ROOT);sys.path.insert(0,str(OUT));sys.path.insert(0,str(ROOT))
    if mode=='backend147':
        files=['tests/test_client_link_contract_before.py','tests/test_client_link_boundaries.py',
           'tests/integration_client_link_services.py','tests/integration_client_link_http.py',
           'tests/integration_client_link_service_races.py','tests/integration_client_link_publication_cas.py']
    elif mode=='restore1':files=['tests/integration_client_link_restore.py']
    elif mode=='UI10':files=['tests/test_r12_ui_pages.py']
    elif mode=='own28':files=[str(TEMP/'drivers'/'test_http_export_review.py')]
    elif mode=='race1':files=['tests/integration_client_link_service_races.py::test_two_processes_consume_one_proof_once_under_restricted_role[postgresql]']
    else:raise ValueError('Unknown frozen bounded phase')
    sys.argv=['tests/run_isolated.py',*files,'--rootdir='+str(ROOT),'-c',str(ROOT/'pytest.ini'),'--import-mode=importlib',
              '-p','observe','-q','--tb=short','--junitxml='+str(phase/'tests.xml')]
    from tests.run_isolated import main
    raise SystemExit(main())

if __name__=='__main__':
    launch_main()

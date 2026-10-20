"""Own-origin, isolated SQLite runner; never inherits external service URLs."""
from pathlib import Path
import importlib.util, json, os, sys, tempfile

ROOT=Path('F:/mb-qa-followup34-sqlfix-20261020').resolve()
TASK=Path(__file__).resolve().parent
PRIVATE=TASK/'private'
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT))
os.environ['TEMP']=str(PRIVATE)
os.environ['TMP']=str(PRIVATE)
tempfile.tempdir=None
from tests.isolation import prepare_environment,block_external_sockets
prepare_environment(discard_inherited=True)
block_external_sockets()
import pytest

spec=importlib.util.spec_from_file_location('qa_nutrition35_maintained_conftest',ROOT/'conftest.py')
maintained=importlib.util.module_from_spec(spec)
spec.loader.exec_module(maintained)
stage=sys.argv[1]

class Origins:
    def pytest_collection_finish(self,session):
        (PRIVATE/(stage+"-nodeids.json")).write_text(json.dumps([item.nodeid for item in session.items],indent=2),encoding="utf-8")
    def pytest_sessionfinish(self,session,exitstatus):
        origins={}
        bad=[]
        for name,module in list(sys.modules.items()):
            top=name.split('.')[0]
            if top not in {'web','api','core','tests','config','scripts','src'}:
                continue
            file=getattr(module,'__file__',None)
            if file:
                path=Path(file).resolve()
                origins[name]=str(path)
                if not path.is_relative_to(ROOT):
                    bad.append(name)
        from web.database.models import Base
        canonical=Path(sys.modules[Base.__module__].__file__).resolve()
        assert canonical.is_relative_to(ROOT)
        (PRIVATE/(stage+'-origins.json')).write_text(json.dumps({'origins':origins,'bad':bad,'canonical_Base_origin':str(canonical)},indent=2),encoding='utf-8')
        if bad:
            session.exitstatus=pytest.ExitCode.INTERNAL_ERROR

files=['tests/test_followup34_http.py', 'tests/test_followup34_boundaries.py', 'tests/test_followup34_races.py', 'tests/test_followup34_sql_error_classification.py', 'tests/test_followup34_lock_projection.py', 'tests/test_followup34_client_ssr_privacy.py']
args=[*files,'--noconftest','--import-mode=importlib','--rootdir',str(ROOT),'-q','--tb=short','-o','cache_dir='+str(PRIVATE/(stage+'-cache')),'--basetemp='+str(PRIVATE/(stage+'-data')),'--junitxml='+str(PRIVATE/(stage+'.xml'))]
if stage.startswith('collect'):
    args.append('--collect-only')
raise SystemExit(pytest.main(args,plugins=[maintained,Origins()]))

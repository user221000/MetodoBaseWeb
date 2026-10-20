from pathlib import Path
import importlib.util,json,os,sys,tempfile
ROOT=Path('F:/mb-qa-browser31-20261020').resolve();TASK=Path(__file__).resolve().parent;P=TASK/'private'
sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT))
os.environ['TEMP']=str(P);os.environ['TMP']=str(P);tempfile.tempdir=None
for key in ('_METODOBASE_TEST_ROOT','METODOBASE_TEST_DATABASE_URL','METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_REDIS_URL'):os.environ.pop(key,None)
from tests.isolation import prepare_environment,block_external_sockets,validate_postgres_test_url
prepare_environment(discard_inherited=True);block_external_sockets()
import pytest
spec=importlib.util.spec_from_file_location('qa_r31_own_maintained_conftest',ROOT/'conftest.py');maintained=importlib.util.module_from_spec(spec);spec.loader.exec_module(maintained)
profile=json.loads(Path('C:/Users/Consu/AppData/Local/Temp/metodobase-qa-pg55483-private-ok6hrpyq/env.json').read_bytes())
for name,alias in [('METODOBASE_TEST_MIGRATOR_URL','migrator_url'),('METODOBASE_TEST_POSTGRES_URL','app_url')]:
    value=profile.get(name,profile.get(alias));assert isinstance(value,str);validate_postgres_test_url(value);os.environ[name]=value
binpath=profile.get('METODOBASE_TEST_PG_BIN',profile.get('pg_bin'))
if binpath:os.environ['METODOBASE_TEST_PG_BIN']=binpath
os.environ['FOLLOWUP34_PRIVATE_LEASES']=str(TASK/'leases')
class Origins:
    def pytest_sessionfinish(self,session,exitstatus):
        origins={};bad=[]
        for name,module in list(sys.modules.items()):
            if name.split('.')[0] not in {'web','api','core','tests','config','src','scripts'}:continue
            file=getattr(module,'__file__',None)
            if file:
                path=Path(file).resolve();origins[name]=str(path)
                if not path.is_relative_to(ROOT):bad.append(name)
        from web.database.models import Base
        canonical=Path(sys.modules[Base.__module__].__file__).resolve();assert canonical.is_relative_to(ROOT)
        (P/'module-origins.json').write_text(json.dumps({'origins':origins,'bad':bad,'canonical_Base_origin':str(canonical),'external_companion':str(TASK/'test_r31_pg.py')},indent=2),encoding='utf-8')
        if bad:session.exitstatus=pytest.ExitCode.INTERNAL_ERROR
args=[str(TASK/'test_r31_pg.py'),'--noconftest','--import-mode=importlib','--rootdir',str(ROOT),'-q','--tb=short','-o','cache_dir='+str(P/'cache'),'--basetemp='+str(P/'data'),'--junitxml='+str(P/'r31.xml')]
raise SystemExit(pytest.main(args,plugins=[maintained,Origins()]))

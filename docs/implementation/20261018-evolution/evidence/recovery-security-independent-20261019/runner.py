from pathlib import Path
import os,sys,json
r=Path(__file__).parent;a=Path('F:/MetodoBaseWeb-recovery-20261019');sys.path.insert(0,str(a));sys.dont_write_bytecode=True
from tests.isolation import prepare_environment,block_external_sockets
prepare_environment(discard_inherited=True);block_external_sockets()
os.environ['METODOBASE_TEST_EVIDENCE_DIR']=str(r/'private-test-evidence')
import pytest
class Results:
 def __init__(self):self.rows=[]
 def pytest_runtest_logreport(self,report):
  if report.when=='call' or (report.when in {'setup','teardown'} and report.failed):self.rows.append({'nodeid':report.nodeid,'phase':report.when,'outcome':report.outcome})
p=Results();code=pytest.main([str(r/'test_recovery_security.py'),'-q','--tb=short','-o','cache_dir='+str(r/'cache'),'--junitxml='+str(r/'http-sqlite.xml')],plugins=[p])
(r/'http-sqlite.json').write_text(json.dumps({'scope':'Independent real factories and SQLite, synthetic accounts and capture-only mail; external sockets blocked; schema setup is explicit metadata, not migration acceptance','exit_code':int(code),'total':len(p.rows),'passed':sum(x['outcome']=='passed' for x in p.rows),'results':p.rows},indent=2)+'\n',encoding='utf8')
raise SystemExit(code)

from pathlib import Path
import json,os,sys
r=Path(__file__).parent;a=Path(os.environ.get('R16_REVIEW_SOURCE_ROOT','F:/MetodoBaseWeb-recovery-20261019'));sys.path.insert(0,str(a));sys.dont_write_bytecode=True
from tests.isolation import prepare_environment,block_external_sockets
prepare_environment(discard_inherited=True);block_external_sockets()
import pytest
class Results:
 def __init__(self):self.rows=[]
 def pytest_runtest_logreport(self,report):
  if report.when=='call' or (report.when in {'setup','teardown'} and report.failed):self.rows.append({'nodeid':report.nodeid,'phase':report.when,'outcome':report.outcome})
mode=sys.argv[1] if len(sys.argv)>1 else 'headers';test_file='test_recovery_headers_semantic_security.py' if mode=='headers-semantic' else 'test_recovery_headers_security.py'
p=Results();code=pytest.main([str(r/test_file),'-q','--tb=short','-o','cache_dir='+str(r/(mode+'-cache')),'--junitxml='+str(r/(mode+'.xml'))],plugins=[p])
(r/(mode+'.json')).write_text(json.dumps({'scope':'Independent exact route CSP and all-response recovery API privacy headers','exit_code':int(code),'total':len(p.rows),'passed':sum(x['outcome']=='passed' for x in p.rows),'results':p.rows},indent=2)+'\n',encoding='utf8')
raise SystemExit(code)

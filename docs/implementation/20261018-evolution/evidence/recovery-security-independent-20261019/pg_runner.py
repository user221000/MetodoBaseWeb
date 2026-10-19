from pathlib import Path
import json,os,sys
def main():
 r=Path(__file__).parent;a=Path('F:/MetodoBaseWeb-recovery-20261019');sys.path.insert(0,str(a));sys.dont_write_bytecode=True
 from tests.isolation import prepare_environment,block_external_sockets,validate_postgres_test_url
 prepare_environment(discard_inherited=True);block_external_sockets()
 private=json.loads(Path('C:/Users/Consu/AppData/Local/Temp/metodobase-qa-pg55483-private-ok6hrpyq/env.json').read_text())
 from urllib.parse import urlsplit
 for name in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL']:
  validate_postgres_test_url(private[name]);parsed=urlsplit(private[name]);assert parsed.hostname=='127.0.0.1' and parsed.port==55483
 for name,value in private.items():os.environ[name]=value
 os.environ['METODOBASE_TEST_EVIDENCE_DIR']=str(r/'pg-private-evidence')
 import pytest
 class Results:
  def __init__(self):self.rows=[]
  def pytest_runtest_logreport(self,report):
   if report.when=='call' or (report.when in {'setup','teardown'} and report.failed):self.rows.append({'nodeid':report.nodeid,'phase':report.when,'outcome':report.outcome})
 p=Results();code=pytest.main([str(r/'test_recovery_pg_security.py'),'-q','--tb=short','-o','cache_dir='+str(r/'pg-cache'),'--junitxml='+str(r/'pg.xml')],plugins=[p])
 (r/'pg.json').write_text(json.dumps({'scope':'Independent PostgreSQL reverse lock-order and RLS checks in exact owned UUID database; private loopback config loaded only in this child','exit_code':int(code),'total':len(p.rows),'passed':sum(x['outcome']=='passed' for x in p.rows),'results':p.rows},indent=2)+'\n',encoding='utf8')
 return code
if __name__=='__main__':raise SystemExit(main())

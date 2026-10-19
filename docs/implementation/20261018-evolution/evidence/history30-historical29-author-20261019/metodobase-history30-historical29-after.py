"""Replay unchanged historical29 criteria with an observational ownership plugin."""
from pathlib import Path
import hashlib,importlib.metadata,json,os,subprocess,sys,xml.etree.ElementTree as ET
root=Path(r'F:\mb-r12-history30-20261019');out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-history30-historical29-after-20261019');out.mkdir(exist_ok=False)
plugin=out/'metodobase_history29_owned_probe.py'
plugin.write_text('''import json,os,re
from pathlib import Path
from urllib.parse import urlsplit
import pytest,psycopg2
created=[]
pending={}
closed=[]
@pytest.hookimpl(hookwrapper=True)
def pytest_fixture_setup(fixturedef,request):
    outcome=yield
    if fixturedef.argname!='migration_database' or outcome.excinfo:return
    value=outcome.get_result()
    if value[1].dialect.name!='postgresql':return
    name=urlsplit(value[0]).path.removeprefix('/')
    assert re.fullmatch(r'metodobase_test_migrations_[0-9a-f]{12}',name)
    assert name not in created
    created.append(name);pending[id(fixturedef)]=name
def pytest_fixture_post_finalizer(fixturedef,request):
    name=pending.pop(id(fixturedef),None)
    if name is None:return
    url=os.environ['METODOBASE_TEST_MIGRATOR_URL'].replace('postgresql+psycopg2://','postgresql://',1)
    with psycopg2.connect(url) as db,db.cursor() as cursor:
        cursor.execute('SELECT count(*) FROM pg_database WHERE datname=%s',(name,))
        assert cursor.fetchone()[0]==0
    closed.append(name)
def pytest_sessionfinish(session,exitstatus):
    value={'created_exact':created,'closed_and_independently_absent':closed,'same_exact_names':sorted(created)==sorted(closed),'pending':pending}
    Path(os.environ['METODOBASE_HISTORICAL29_OWNED_PROOF']).write_text(json.dumps(value,indent=2)+'\\n',encoding='utf8')
    if len(created)!=5 or sorted(created)!=sorted(closed) or pending:session.exitstatus=1
''',encoding='utf8')
names=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')[:-1]
def photo():return {'files':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names},'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions()),'plugin_sha256':hashlib.sha256(plugin.read_bytes()).hexdigest()}
before=photo();(out/'before.json').write_text(json.dumps(before,indent=2)+'\n',encoding='utf8')
configuration=json.loads(Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-qa-pg55483-private-ok6hrpyq/env.json').read_text(encoding='utf-8-sig'))
environment=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHON_DOTENV_DISABLED='1',PYTHONPATH=str(out),METODOBASE_HISTORICAL29_OWNED_PROOF=str(out/'database-closure.json'))
for key in ['DATABASE_URL','MIGRATOR_DATABASE_URL','METODOBASE_TEST_DATABASE_URL','_METODOBASE_TEST_ROOT']:environment.pop(key,None)
for key in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL','METODOBASE_TEST_PG_BIN']:environment[key]=configuration[key]
result=subprocess.run([sys.executable,'-X','utf8','-B','tests/run_isolated.py','tests/integration_client_link_migrations.py','-p','metodobase_history29_owned_probe','-q','--tb=short','--junitxml='+str(out/'tests.xml')],cwd=root,env=environment,capture_output=True,timeout=200)
(out/'stdout.log').write_bytes(result.stdout);(out/'stderr.log').write_bytes(result.stderr)
after=photo();(out/'after.json').write_text(json.dumps(after,indent=2)+'\n',encoding='utf8')
pip=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True);(out/'pip.log').write_bytes(pip.stdout+pip.stderr)
cases=ET.parse(out/'tests.xml').findall('.//testcase') if (out/'tests.xml').exists() else []
summary={'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'exit':result.returncode,'cases':len(cases),'failures_errors_skips':sum(case.find(tag) is not None for case in cases for tag in ['failure','error','skipped']),'sources_packages_plugin_stable':before==after,'sources':len(names),'packages':len(before['packages']),'pip_exit':pip.returncode,'scope':'Same original historical29 migration/guard assertions, explicit29 target after model30, SQLite+actual restricted PG fixtures; only observer plugin checks exact five database closures.'}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8');print(json.dumps(summary))
assert result.returncode==0 and len(cases)==10 and summary['failures_errors_skips']==0 and before==after and pip.returncode==0

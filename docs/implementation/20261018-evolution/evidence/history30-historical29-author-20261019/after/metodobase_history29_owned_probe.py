import json,os,re
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
    Path(os.environ['METODOBASE_HISTORICAL29_OWNED_PROOF']).write_text(json.dumps(value,indent=2)+'\n',encoding='utf8')
    if len(created)!=5 or sorted(created)!=sorted(closed) or pending:session.exitstatus=1

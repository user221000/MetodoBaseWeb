"""Observation-only pytest plugin: record only returned owned UUID databases and verify absence."""
import sys
sys.dont_write_bytecode=True
import json
import os
from pathlib import Path
import re
import pytest

OWNED={}

@pytest.hookimpl(hookwrapper=True)
def pytest_fixture_setup(fixturedef,request):
    outcome=yield
    if fixturedef.argname not in {'lab','own_lab'} or outcome.excinfo is not None:return
    value=outcome.get_result()
    if not isinstance(value,dict) or 'admin' not in value:return
    name=value['admin'].url.database
    assert re.fullmatch(r'metodobase_test_migrations_[0-9a-f]{12}',name)
    OWNED[name]={'fixture':fixturedef.argname,'module':request.module.__name__}
    Path(os.environ['QA_DB_RECEIPT']).write_text(json.dumps({'created_owned_names':OWNED,'verification':'pending teardown'})+'\n',encoding='utf8')

def pytest_sessionfinish(session,exitstatus):
    target=Path(os.environ['QA_DB_RECEIPT'])
    try:
        import psycopg2
        config=json.loads(Path(os.environ['QA_PRIVATE_ENV_PATH']).read_text(encoding='utf-8-sig'))
        with psycopg2.connect(config['METODOBASE_TEST_MIGRATOR_URL'].replace('postgresql+psycopg2://','postgresql://',1)) as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT datname FROM pg_database WHERE datname=ANY(%s)',(list(OWNED),))
                remaining=[row[0] for row in cursor.fetchall()]
        value={'created_owned_names':OWNED,'remaining_exact_owned_names':remaining,
               'all_exact_owned_names_absent':not remaining,'observed_database_count':len(OWNED),
               'scope':'Only DB names returned by this process fixtures. No foreign database listed, modified or dropped by plugin.'}
        target.write_text(json.dumps(value,indent=2)+'\n',encoding='utf8')
        if remaining:session.exitstatus=1
    except Exception as error:
        target.write_text(json.dumps({'verification_error_class':type(error).__name__,'created_owned_names':OWNED})+'\n',encoding='utf8')
        session.exitstatus=1

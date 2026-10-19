"""Record exact owned names before fixture initialization can fail; assert module provenance."""
import sys
sys.dont_write_bytecode=True
import json
import os
from pathlib import Path
import re

OWNED={}
ROOT=Path(r'F:/MetodoBaseWeb-r12-core29-qa-20261019').resolve()
OUT=Path(__file__).resolve().parent

def persist_pending():
    Path(os.environ['QA_DB_RECEIPT']).write_text(json.dumps({'created_owned_names':OWNED,'verification':'pending teardown'})+'\n',encoding='utf8')

def pytest_configure(config):
    from tests.integration_schema_migrations import migration_database
    original=migration_database.__wrapped__
    def observed(request,tmp_path):
        owner=original(request,tmp_path)
        try:
            value=next(owner)
            name=value[1].url.database
            assert re.fullmatch(r'metodobase_test_migrations_[0-9a-f]{12}',name)
            OWNED[name]={'fixture':'migration_database','phase':'created-before-own-fixture-yield'}
            persist_pending()
            yield value
        finally:
            owner.close()
    migration_database.__wrapped__=observed

def pytest_runtest_setup(item):
    names=['tests.integration_schema_migrations','web.database.schema_control','web.database.models','web.database.tenant_context']
    paths={name:str(Path(sys.modules[name].__file__).resolve()) for name in names if name in sys.modules}
    assert all(Path(value).is_relative_to(ROOT) for value in paths.values()),'Wrong worktree module origin'
    (OUT/'own-isolated-module-origin.json').write_text(json.dumps({'root':str(ROOT),'modules':paths},indent=2)+'\n',encoding='utf8')

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
               'scope':'Only exact names returned by this process migration generator. No foreign DB listed/modified/dropped.'}
        target.write_text(json.dumps(value,indent=2)+'\n',encoding='utf8')
        if remaining:session.exitstatus=1
    except Exception as error:
        target.write_text(json.dumps({'verification_error_class':type(error).__name__,'created_owned_names':OWNED})+'\n',encoding='utf8')
        session.exitstatus=1

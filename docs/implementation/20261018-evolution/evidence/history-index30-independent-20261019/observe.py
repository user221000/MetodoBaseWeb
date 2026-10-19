"""Observe exact owned UUIDs before yield and assert isolated module origins."""
import sys
sys.dont_write_bytecode=True
import json
import os
from pathlib import Path
import re

ROOT=Path(r'F:/mb-hidx30-qa-20261019').resolve()
NAMES={}
def pytest_configure(config):
    from tests.integration_schema_migrations import migration_database
    original=migration_database.__wrapped__
    def observed(request,tmp_path):
        owner=original(request,tmp_path)
        try:
            value=next(owner)
            if value[1].dialect.name=='postgresql':
                name=value[1].url.database
                assert re.fullmatch(r'metodobase_test_migrations_[0-9a-f]{12}',name)
                NAMES[name]={'created_by_current_process_migration_generator':True}
                (Path(os.environ['QA_PHASE'])/'owned-pending.json').write_text(json.dumps(NAMES)+'\n',encoding='utf8')
            yield value
        finally:owner.close()
    migration_database.__wrapped__=observed
def pytest_runtest_setup(item):
    watched=['tests.integration_schema_migrations','web.database.schema_control','web.database.models',
             'web.database.alembic.history_index_contract_v1','web.services.personal_history_query']
    origins={name:str(Path(sys.modules[name].__file__).resolve()) for name in watched if name in sys.modules}
    assert all(Path(value).is_relative_to(ROOT) for value in origins.values()),'Wrong isolated worktree module origin'
    (Path(os.environ['QA_PHASE'])/'module-origins.json').write_text(json.dumps(origins,indent=2)+'\n',encoding='utf8')
def pytest_sessionfinish(session,exitstatus):
    import psycopg2
    config=json.loads(Path(os.environ['QA_PRIVATE']).read_text(encoding='utf-8-sig'))
    with psycopg2.connect(config['METODOBASE_TEST_MIGRATOR_URL'].replace('postgresql+psycopg2://','postgresql://',1)) as db,db.cursor() as cursor:
        cursor.execute('SELECT datname FROM pg_database WHERE datname=ANY(%s)',(list(NAMES),))
        remaining=[row[0] for row in cursor.fetchall()]
    proof={'exact_current_process_UUID_names':list(NAMES),'remaining_exact_owned_names':remaining,
           'count':len(NAMES),'all_owned_absent':not remaining,'scope':'Only names returned by this process generator; no foreign DB listed/changed/dropped.'}
    (Path(os.environ['QA_PHASE'])/'owned-absence.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')
    if remaining:session.exitstatus=1

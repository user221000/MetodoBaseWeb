"""Observe returned exact UUIDs and recheck their absence; enforce module origins."""
import sys
sys.dont_write_bytecode=True
import json
import os
from pathlib import Path
import re
ROOT=Path(r'F:/mb-r12-final939-qa-20261019').resolve()
OWNED={}
def record(names):
    for name in names:
        assert re.fullmatch(r'metodobase_test_(?:migrations|backup|restore)_[0-9a-f]{12}',name)
        OWNED[name]={'created_by_current_process_owned_generator':True}
    (Path(os.environ['QA_PHASE'])/'owned-pending.json').write_text(json.dumps(OWNED)+'\n',encoding='utf8')
def pytest_configure(config):
    from tests.integration_schema_migrations import migration_database
    original=migration_database.__wrapped__
    def migration(request,tmp_path):
        owner=original(request,tmp_path)
        try:
            value=next(owner)
            if value[1].dialect.name=='postgresql':record([value[1].url.database])
            yield value
        finally:owner.close()
    migration_database.__wrapped__=migration
    if os.environ['QA_MODE']=='restore1':
        from tests.integration_backup_restore_postgres import owned_databases
        original_restore=owned_databases.__wrapped__
        def restored():
            owner=original_restore()
            try:
                value=next(owner);record([name for name,url in value]);yield value
            finally:owner.close()
        owned_databases.__wrapped__=restored
def pytest_runtest_setup(item):
    watched=['tests.integration_schema_migrations','web.database.models','web.database.schema_control',
       'web.routes.client_links','web.services.client_link_context','web.services.client_link_invitations','web.services.client_link_plans']
    origins={name:str(Path(sys.modules[name].__file__).resolve()) for name in watched if name in sys.modules}
    assert all(Path(value).is_relative_to(ROOT) for value in origins.values()),'Incorrect composition module origin'
    (Path(os.environ['QA_PHASE'])/'module-origins.json').write_text(json.dumps(origins,indent=2)+'\n',encoding='utf8')
def pytest_sessionfinish(session,exitstatus):
    import psycopg2
    config=json.loads(Path(os.environ['QA_PRIVATE']).read_text(encoding='utf-8-sig'))
    with psycopg2.connect(config['METODOBASE_TEST_MIGRATOR_URL'].replace('postgresql+psycopg2://','postgresql://',1)) as db,db.cursor() as cursor:
        cursor.execute('SELECT datname FROM pg_database WHERE datname=ANY(%s)',(list(OWNED),))
        remaining=[row[0] for row in cursor.fetchall()]
    value={'exact_owned_UUID_names':list(OWNED),'count':len(OWNED),'remaining_exact_owned_names':remaining,'all_owned_absent':not remaining,
           'scope':'Only exact names returned by this process generator. No foreign DB listed/modified/dropped.'}
    (Path(os.environ['QA_PHASE'])/'owned-absence.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf8')
    if remaining:session.exitstatus=1

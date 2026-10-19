"""Revision29 from exact28, preserving historical rows and all twenty policies."""
from contextlib import contextmanager
import json
import os
import subprocess
import sys

import pytest
from sqlalchemy import inspect,text

from tests.integration_schema_migrations import migration_database,run_migration,ROOT
from tests.integration_account_recovery_migrations import populate27
from tests.integration_stored_objects_migrations import snapshot
from web.database.schema_control import verify_runtime_schema
from web.database.alembic.schema_contract_v1 import schema_signature
from web.database.alembic.security_contract_v1 import tenant_security_signature
from web.database.alembic.member_link_security_v1 import member_link_security_signature

PREVIOUS='20261019_account_recovery'
REVISION='20261019_client_account_links'
NEW={'client_account_links','client_link_invitations','client_plan_publications'}


def populate28(engine):
    populate27(engine)
    with engine.begin() as db:
        db.execute(text("UPDATE usuarios SET password_reset_hash=:hash,password_reset_expires_at='2027-10-01 12:30:00',password_reset_session_version=0 WHERE id='individual-migration'"),{'hash':'f'*64})


@pytest.mark.parametrize('populated',[False,True])
def test_exact28_upgrade_repeat_preserves_rows_and_old_policies(migration_database,populated):
    url,engine=migration_database
    run_migration(url,'db_bootstrap.py','--revision',PREVIOUS)
    if populated:populate28(engine)
    columns,before=snapshot(engine)
    with engine.connect() as db: old_security=tenant_security_signature(db)
    verify_runtime_schema(engine,expected_revision=PREVIOUS)
    with pytest.raises(RuntimeError,match='revision'):verify_runtime_schema(engine)
    run_migration(url,'db_bootstrap.py','--revision',REVISION)
    verify_runtime_schema(engine,expected_revision=REVISION)
    assert snapshot(engine,columns)[1]==before
    with engine.connect() as db:
        assert len(inspect(db).get_table_names())==30  #29 business + bookkeeping.
        assert set(inspect(db).get_table_names())-set(columns)-{'alembic_version'}==NEW
        security=tenant_security_signature(db)
        if engine.dialect.name=='postgresql':
            assert [row for row in security['tables'] if row[0] not in NEW]==old_security['tables']
            assert [row for row in security['policies'] if row[0] not in NEW]==old_security['policies']
            assert security['set_tenant']==old_security['set_tenant']
            assert len([row for row in security['tables'] if row[1] and row[2]])==23
            functions=member_link_security_signature(db)['functions']
            assert functions and all(row[3] is False and row[4]==['search_path=pg_catalog'] for row in functions)
        else:assert db.exec_driver_sql('PRAGMA foreign_key_check').all()==[]
        expected=json.loads((ROOT/'web/database/alembic/schema_targets'/('20261019_client_account_links_'+engine.dialect.name+'.json')).read_text())
        assert schema_signature(db)==expected['signature']
        assert member_link_security_signature(db)==expected['member_link_security']
    run_migration(url,'db_bootstrap.py','--revision',REVISION)
    assert snapshot(engine,columns)[1]==before


def test_unknown28_drift_aborts_before_link_ddl(migration_database):
    url,engine=migration_database
    run_migration(url,'db_bootstrap.py','--revision',PREVIOUS)
    with engine.begin() as db:db.execute(text('ALTER TABLE clientes ADD COLUMN unknown_member_drift integer'))
    result=subprocess.run([sys.executable,'-X','utf8','db_bootstrap.py'],cwd=ROOT,
        env=dict(os.environ,DATABASE_URL=url,METODOBASE_TEST_DATABASE_URL=''),capture_output=True,text=True)
    assert result.returncode!=0
    with engine.connect() as db:
        assert db.scalar(text('SELECT version_num FROM alembic_version'))==PREVIOUS
        assert NEW.isdisjoint(inspect(db).get_table_names())


def test_parent_rebuild_failure_rolls_back_constraints_rows_and_revision(migration_database,monkeypatch):
    import db_bootstrap
    from alembic.operations import Operations
    url,engine=migration_database
    run_migration(url,'db_bootstrap.py','--revision',PREVIOUS);populate28(engine)
    columns,before=snapshot(engine)
    original=Operations.batch_alter_table;reached=[]
    @contextmanager
    def rebuild(self,name,*args,**kwargs):
        with original(self,name,*args,**kwargs) as batch:yield batch
        if name=='planes_generados':
            reached.append(name);raise RuntimeError('Synthetic failure after actual member source DDL')
    monkeypatch.setattr(Operations,'batch_alter_table',rebuild)
    monkeypatch.setattr(db_bootstrap,'_migration_engine',lambda:engine)
    assert db_bootstrap.main()==1 and reached==['planes_generados']
    assert snapshot(engine,columns)[1]==before
    verify_runtime_schema(engine,expected_revision=PREVIOUS)


def test_member_helper_or_trigger_drift_fails_runtime_contract(migration_database):
    url,engine=migration_database
    run_migration(url,'db_bootstrap.py','--revision',REVISION)
    verify_runtime_schema(engine,expected_revision=REVISION)
    with engine.begin() as db:
        if engine.dialect.name=='postgresql':
            db.exec_driver_sql("ALTER TABLE client_account_links DISABLE TRIGGER r12_guard_link")
        else:db.exec_driver_sql('DROP TRIGGER r12_link_update')
    with pytest.raises(RuntimeError,match='guards'):verify_runtime_schema(engine,expected_revision=REVISION)

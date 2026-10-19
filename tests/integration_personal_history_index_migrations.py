"""Revision30 is a transactional index change; revision29 rows/guards survive."""
import os
import subprocess
import sys

import pytest
from sqlalchemy import inspect, text

from tests.integration_schema_migrations import run_migration, ROOT
from tests.history_index_fixtures import history_migration_database as migration_database
from tests.integration_client_link_migrations import populate28
from tests.integration_stored_objects_migrations import snapshot
from web.database.schema_control import verify_runtime_schema
from web.database.alembic.schema_contract_v1 import schema_signature
from web.database.tenant_policy import tenant_security_signature
from web.database.alembic.member_link_security_v1 import member_link_security_signature
from web.database.alembic.history_index_contract_v1 import (
    INDEX_NAME, create_history_index, expected_history_index, history_index_signature,
)

PREVIOUS = '20261019_client_account_links'
REVISION = '20261019_personal_history_index'


def bootstrap_result(url):
    return subprocess.run([sys.executable, '-X', 'utf8', 'db_bootstrap.py'], cwd=ROOT,
        env=dict(os.environ, DATABASE_URL=url, METODOBASE_TEST_DATABASE_URL=''),
        capture_output=True, text=True)


def security(engine):
    with engine.connect() as db:
        return tenant_security_signature(db), member_link_security_signature(db)


def test_populated29_upgrade_repeat_and_index_only_rollback(migration_database):
    url, engine = migration_database
    run_migration(url, 'db_bootstrap.py', '--revision', PREVIOUS)
    populate28(engine)
    columns, rows = snapshot(engine)
    guards = security(engine)
    verify_runtime_schema(engine, expected_revision=PREVIOUS)
    with pytest.raises(RuntimeError, match='revision'):
        verify_runtime_schema(engine)
    run_migration(url, 'db_bootstrap.py', '--revision', REVISION)
    verify_runtime_schema(engine)
    assert snapshot(engine, columns)[1] == rows
    assert security(engine) == guards
    with engine.connect() as db:
        assert history_index_signature(db) == expected_history_index(engine.dialect.name)
        assert len(inspect(db).get_table_names()) == 30
        assert 'ix_planes_gym_fecha' in {item['name'] for item in inspect(db).get_indexes('planes_generados')}
    run_migration(url, 'db_bootstrap.py', '--revision', REVISION)
    assert snapshot(engine, columns)[1] == rows
    run_migration(url, '-m', 'alembic', 'downgrade', PREVIOUS)
    verify_runtime_schema(engine, expected_revision=PREVIOUS)
    assert snapshot(engine, columns)[1] == rows
    assert security(engine) == guards
    with engine.connect() as db:
        assert history_index_signature(db) is None
        assert db.scalar(text('SELECT version_num FROM alembic_version')) == PREVIOUS
    run_migration(url, 'db_bootstrap.py', '--revision', REVISION)
    verify_runtime_schema(engine)


@pytest.mark.parametrize('drift', ['direction', 'identity_order', 'collation', 'missing'])
def test_same_columns_drift_or_missing_index_rejected_without_runtime_repair(migration_database, drift):
    url, engine = migration_database
    run_migration(url, 'db_bootstrap.py', '--revision', REVISION)
    with engine.begin() as db:
        structural = schema_signature(db)
        db.exec_driver_sql('DROP INDEX ' + INDEX_NAME)
        if drift != 'missing':
            direction = 'ASC' if drift == 'direction' else 'DESC'
            nulls = ' NULLS LAST' if engine.dialect.name == 'postgresql' else ''
            collation = '' if drift != 'collation' else (' COLLATE "C"' if engine.dialect.name == 'postgresql' else ' COLLATE NOCASE')
            identity_order = ('DESC NULLS FIRST' if drift == 'identity_order' else 'DESC NULLS LAST') if engine.dialect.name == 'postgresql' else ('ASC' if drift == 'identity_order' else 'DESC')
            db.exec_driver_sql('CREATE INDEX ' + INDEX_NAME + ' ON planes_generados '
                '(gym_id' + collation + ',id_cliente,fecha_generacion ' + direction + nulls + ',id ' + identity_order + ') WHERE deleted_at IS NULL')
            # Immutable v1 intentionally omits order and collation. The new
            # physical contract must catch what that older format cannot.
            assert schema_signature(db) == structural
        assert history_index_signature(db) != expected_history_index(engine.dialect.name)
    with pytest.raises(RuntimeError, match='ordering|structure'):
        verify_runtime_schema(engine)
    assert bootstrap_result(url).returncode != 0
    with engine.connect() as db:
        assert db.scalar(text('SELECT version_num FROM alembic_version')) == REVISION
        assert history_index_signature(db) != expected_history_index(engine.dialect.name)


def test_unknown29_drift_aborts_before_any_index_ddl(migration_database):
    url, engine = migration_database
    run_migration(url, 'db_bootstrap.py', '--revision', PREVIOUS)
    with engine.begin() as db:
        db.exec_driver_sql('ALTER TABLE clientes ADD COLUMN unknown_history_drift integer')
    assert bootstrap_result(url).returncode != 0
    with engine.connect() as db:
        assert db.scalar(text('SELECT version_num FROM alembic_version')) == PREVIOUS
        assert history_index_signature(db) is None


def test_failure_after_actual_index_ddl_rolls_back_rows_guards_and_revision(migration_database, monkeypatch):
    import db_bootstrap
    from web.database.alembic import history_index_contract_v1
    url, engine = migration_database
    run_migration(url, 'db_bootstrap.py', '--revision', PREVIOUS)
    populate28(engine)
    columns, rows = snapshot(engine)
    guards = security(engine)
    reached = []

    def fail_after_index(connection):
        create_history_index(connection)
        assert history_index_signature(connection) == expected_history_index(connection.dialect.name)
        reached.append(True)
        raise RuntimeError('Synthetic failure after actual history index DDL')

    monkeypatch.setattr(history_index_contract_v1, 'create_history_index', fail_after_index)
    monkeypatch.setattr(db_bootstrap, '_migration_engine', lambda: engine)
    assert db_bootstrap.main() == 1
    assert reached == [True]
    verify_runtime_schema(engine, expected_revision=PREVIOUS)
    assert snapshot(engine, columns)[1] == rows
    assert security(engine) == guards
    with engine.connect() as db:
        assert history_index_signature(db) is None

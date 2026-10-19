"""Actual PostgreSQL transaction hooks, before the separate RLS policy gate.

No policies are enabled here. These tests establish session/connection context,
failure propagation and pool cleanup; integration_postgres covers row access.
"""
import os
from urllib.parse import urlsplit, urlunsplit
import uuid

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from tests.isolation import validate_postgres_test_url
from tests.integration_schema_migrations import run_migration


@pytest.fixture
def context_engine():
    import psycopg2
    from psycopg2 import sql
    from web.database.tenant_context import configure_tenant_engine
    admin_url = os.environ['METODOBASE_TEST_MIGRATOR_URL']
    app_url = os.environ['METODOBASE_TEST_POSTGRES_URL']
    validate_postgres_test_url(admin_url)
    validate_postgres_test_url(app_url)
    parsed, app_parts = urlsplit(admin_url), urlsplit(app_url)
    assert (parsed.hostname, parsed.port) == (app_parts.hostname, app_parts.port)
    name = 'metodobase_test_context_' + uuid.uuid4().hex[:12]
    admin = psycopg2.connect(admin_url.replace('postgresql+psycopg2://', 'postgresql://', 1))
    admin.autocommit = True
    with admin.cursor() as cursor:
        cursor.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    database_admin = urlunsplit(parsed._replace(path='/' + name))
    database_app = urlunsplit(app_parts._replace(path='/' + name))
    app = None
    try:
        run_migration(database_admin, 'db_bootstrap.py')
        with psycopg2.connect(database_admin.replace('postgresql+psycopg2://', 'postgresql://', 1)) as db, db.cursor() as cursor:
            cursor.execute(sql.SQL('GRANT USAGE ON SCHEMA public TO {}').format(sql.Identifier(app_parts.username)))
        app = configure_tenant_engine(create_engine(database_app, pool_size=1, max_overflow=0, pool_timeout=3))
        from web.database.tenant_policy import verify_application_database_role
        verify_application_database_role(app)
        yield app
    finally:
        if app is not None:
            app.dispose()
        with admin.cursor() as cursor:
            assert name.startswith('metodobase_test_context_')
            cursor.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))
        admin.close()


def _identity(db):
    return db.execute(text("SELECT current_setting('app.current_tenant', true)")).scalar_one()


def test_direct_session_reinstalls_context_after_commit_and_rollback(context_engine):
    from web.database.tenant_context import tenant_scope
    with tenant_scope('owner-a'), Session(context_engine) as db:
        assert _identity(db) == 'owner-a'
        db.commit()
        assert _identity(db) == 'owner-a'
        db.rollback()
        assert _identity(db) == 'owner-a'


def test_one_connection_pool_never_inherits_previous_tenant(context_engine):
    from web.database.tenant_context import tenant_scope
    process_ids = []
    for identity in ('owner-a', 'owner-b'):
        with tenant_scope(identity), context_engine.connect() as db:
            process_ids.append(db.execute(text('SELECT pg_backend_pid()')).scalar_one())
            assert _identity(db) == identity
            db.commit()
            assert _identity(db) == identity
    with context_engine.connect() as db:
        process_ids.append(db.execute(text('SELECT pg_backend_pid()')).scalar_one())
        assert _identity(db) == ''
    assert len(set(process_ids)) == 1


def test_verified_callback_session_keeps_subject_across_internal_commits(context_engine):
    from web.database.tenant_context import bind_verified_subject
    with Session(context_engine) as db:
        assert _identity(db) == ''  # Only the control plane may be read now.
        bind_verified_subject(db, 'payment-subject')
        assert _identity(db) == 'payment-subject'
        db.commit()
        assert _identity(db) == 'payment-subject'
        db.rollback()
        assert _identity(db) == 'payment-subject'


def test_failed_set_local_blocks_the_business_query(context_engine):
    from web.database.tenant_context import tenant_scope
    executed = []
    def fail_context(connection, cursor, statement, parameters, context, executemany):
        if "set_config('app.current_tenant'" in statement:
            return 'SELECT metodobase_invalid_context_function(%(tenant)s)', parameters
        if '424242' in statement:
            executed.append(True)
        return statement, parameters
    event.listen(context_engine, 'before_cursor_execute', fail_context, retval=True)
    try:
        with tenant_scope('owner-a'), Session(context_engine) as db:
            with pytest.raises(ProgrammingError):
                db.execute(text('SELECT 424242'))
        assert executed == []
    finally:
        event.remove(context_engine, 'before_cursor_execute', fail_context)
    with context_engine.connect() as db:
        assert _identity(db) == ''

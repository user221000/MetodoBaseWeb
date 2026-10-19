"""Migration and startup policy gates, using only UUID-owned PostgreSQL DBs."""
import importlib
import os
import subprocess
import sys
from unittest.mock import patch

import pytest
from sqlalchemy import text

from tests.integration_schema_migrations import migration_database, run_migration, ROOT


@pytest.mark.parametrize('migration_database', ['postgresql'], indirect=True)
@pytest.mark.parametrize('factory_module', ['web.main_web', 'api.app'])
def test_real_factories_reject_privileged_database_role_before_auth(migration_database, monkeypatch, factory_module):
    from web.database.schema_control import verify_runtime_schema
    url, admin = migration_database
    run_migration(url, 'db_bootstrap.py', '--revision', 'head')
    verify_runtime_schema(admin)
    monkeypatch.setattr('web.database.engine.get_engine', lambda: admin)
    with patch('web.auth.init_auth') as auth:
        with pytest.raises(RuntimeError, match='NOSUPERUSER'):
            importlib.import_module(factory_module).create_app()
    auth.assert_not_called()


@pytest.mark.parametrize('migration_database', ['postgresql'], indirect=True)
@pytest.mark.parametrize('factory_module', ['web.main_web', 'api.app'])
def test_real_factories_reject_table_owner_application_role(migration_database, monkeypatch, factory_module):
    from tests.integration_provider_subjects import application_engine
    from web.database.schema_control import verify_runtime_schema
    from sqlalchemy import DDL
    url, admin = migration_database
    run_migration(url, 'db_bootstrap.py', '--revision', 'head')
    application = application_engine(url, admin)
    try:
        role = application.url.username
        quote = admin.dialect.identifier_preparer.quote
        with admin.begin() as connection:
            connection.execute(DDL('ALTER TABLE clientes OWNER TO %(role)s', context={'role': quote(role)}))
        verify_runtime_schema(application)
        monkeypatch.setattr('web.database.engine.get_engine', lambda: application)
        with patch('web.auth.init_auth') as auth:
            with pytest.raises(RuntimeError, match='DDL owner'):
                importlib.import_module(factory_module).create_app()
        auth.assert_not_called()
    finally:
        application.dispose()


@pytest.mark.parametrize('migration_database', ['postgresql'], indirect=True)
@pytest.mark.parametrize('tamper', [
    'ALTER TABLE clientes NO FORCE ROW LEVEL SECURITY',
    'ALTER TABLE clientes DISABLE ROW LEVEL SECURITY',
    'CREATE POLICY unexpected_permissive_policy ON clientes USING (true)',
    'ALTER FUNCTION set_tenant(text) SECURITY DEFINER',
])
def test_runtime_rejects_policy_flag_and_helper_drift(migration_database, tamper):
    from web.database.schema_control import verify_runtime_schema
    url, admin = migration_database
    run_migration(url, 'db_bootstrap.py', '--revision', 'head')
    with admin.begin() as connection:
        connection.execute(text(tamper))
    with pytest.raises(RuntimeError, match='tenant policies'):
        verify_runtime_schema(admin)


@pytest.mark.parametrize('migration_database', ['postgresql'], indirect=True)
def test_activation_aborts_on_unknown_policy_without_mutating_prior_boundary(migration_database):
    url, admin = migration_database
    run_migration(url, 'db_bootstrap.py', '--revision', '20261018_provider_subjects')
    with admin.begin() as connection:
        connection.execute(text('CREATE POLICY unexpected_permissive_policy ON clientes USING (true)'))
    environment = dict(os.environ, DATABASE_URL=url, METODOBASE_TEST_DATABASE_URL='')
    result = subprocess.run([sys.executable, '-X', 'utf8', 'db_bootstrap.py'], cwd=ROOT,
        env=environment, capture_output=True, text=True)
    assert result.returncode != 0
    with admin.connect() as connection:
        assert connection.scalar(text('SELECT version_num FROM alembic_version')) == '20261018_provider_subjects'
        assert connection.execute(text("SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE relname='clientes'")).one() == (False, False)
        assert connection.scalar(text("SELECT count(*) FROM pg_policies WHERE policyname='unexpected_permissive_policy'")) == 1


@pytest.mark.parametrize('migration_database', ['postgresql'], indirect=True)
def test_already_active_historical_boundary_converges_without_disabling_it(migration_database):
    from web.database.schema_control import verify_runtime_schema
    url, admin = migration_database
    run_migration(url, 'db_bootstrap.py', '--revision', '20261018_provider_subjects')
    with admin.begin() as connection:
        for table in ('clientes', 'planes_generados', 'subscriptions', 'payments'):
            connection.execute(text('ALTER TABLE ' + table + ' ENABLE ROW LEVEL SECURITY'))
            connection.execute(text('ALTER TABLE ' + table + ' FORCE ROW LEVEL SECURITY'))
        connection.execute(text('ALTER FUNCTION set_tenant(text) SECURITY DEFINER'))
    run_migration(url, 'db_bootstrap.py', '--revision', 'head')
    verify_runtime_schema(admin)

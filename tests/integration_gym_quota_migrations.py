"""Quota head extends accepted R04 without accepting structural/security drift."""
import json
import os
import subprocess
import sys

import pytest
from sqlalchemy import inspect, text

from tests.integration_schema_migrations import migration_database, run_migration, _fixture, ROOT
from web.database.schema_control import verify_runtime_schema


@pytest.mark.parametrize('origin', ['empty','unversioned-legacy'])
def test_empty_and_legacy_upgrade_to_frozen_quota_head(migration_database, origin):
    url, engine = migration_database
    arguments = ['db_bootstrap.py','--revision','head']
    if origin == 'unversioned-legacy':
        _fixture(engine)
        arguments.append('--adopt-verified-legacy')
    run_migration(url, *arguments)
    verify_runtime_schema(engine)
    with engine.connect() as connection:
        assert connection.scalar(text('SELECT version_num FROM alembic_version')) == '20261018_gym_generation_quota'
        assert len(inspect(connection).get_table_names()) == 25  # 24 business + Alembic version.


@pytest.mark.parametrize('migration_database', ['postgresql'], indirect=True)
@pytest.mark.parametrize('drift', ['schema','policy'])
def test_source_drift_aborts_before_creating_ledger(migration_database, drift):
    url, engine = migration_database
    run_migration(url, 'db_bootstrap.py','--revision','20261018_tenant_isolation')
    with engine.begin() as connection:
        if drift == 'schema':
            connection.execute(text('ALTER TABLE clientes ADD COLUMN unreviewed_column integer'))
        else:
            connection.execute(text('CREATE POLICY unreviewed_policy ON clientes USING (true)'))
    environment = dict(os.environ, DATABASE_URL=url, METODOBASE_TEST_DATABASE_URL='')
    result = subprocess.run([sys.executable,'-X','utf8','db_bootstrap.py'],cwd=ROOT,
        env=environment,capture_output=True,text=True)
    assert result.returncode != 0
    with engine.connect() as connection:
        assert connection.scalar(text('SELECT version_num FROM alembic_version')) == '20261018_tenant_isolation'
        assert 'gym_generation_reservations' not in inspect(connection).get_table_names()

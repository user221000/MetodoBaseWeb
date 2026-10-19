"""Real migration paths; frozen SQL represents fixtures, never a repair fallback.

Invoke explicitly. PostgreSQL needs the synthetic loopback migrator URL used by
the independent QA job. Each case creates and removes only its owned database.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlsplit, urlunsplit
import uuid

import pytest
from sqlalchemy import create_engine, text

from tests.isolation import validate_postgres_test_url
from web.database.alembic.schema_contract_v1 import schema_signature

ROOT = Path(__file__).resolve().parents[1]


def run_migration(url, *arguments):
    environment = os.environ.copy()
    environment['DATABASE_URL'] = url
    environment['METODOBASE_TEST_DATABASE_URL'] = ''
    result = subprocess.run([sys.executable, '-X', 'utf8', *arguments], cwd=ROOT,
                            env=environment, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return result


@pytest.fixture(params=['sqlite', 'postgresql'])
def migration_database(request, tmp_path):
    if request.param == 'sqlite':
        url = 'sqlite:///' + (tmp_path / 'migration.db').as_posix()
        engine = create_engine(url)
        yield url, engine
        engine.dispose()
        return
    import psycopg2
    from psycopg2 import sql
    admin_url = os.environ['METODOBASE_TEST_MIGRATOR_URL']
    validate_postgres_test_url(admin_url)
    parsed = urlsplit(admin_url)
    name = 'metodobase_test_migrations_' + uuid.uuid4().hex[:12]
    admin = psycopg2.connect(admin_url.replace('postgresql+psycopg2://', 'postgresql://', 1))
    admin.autocommit = True
    with admin.cursor() as cursor:
        cursor.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    url = urlunsplit(parsed._replace(path='/' + name))
    engine = create_engine(url)
    try:
        yield url, engine
    finally:
        engine.dispose()
        with admin.cursor() as cursor:
            assert name.startswith('metodobase_test_migrations_')
            cursor.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))
        admin.close()


def _fixture(engine):
    statement = (ROOT / 'tests/fixtures/schema' /
                 ('legacy_20260402_' + engine.dialect.name + '.sql')).read_text(encoding='utf-8')
    with engine.begin() as connection:
        raw = connection.connection.driver_connection
        if engine.dialect.name == 'sqlite':
            raw.executescript(statement)
        else:
            with raw.cursor() as cursor:
                cursor.execute(statement)


@pytest.mark.parametrize('origin', ['empty', 'legacy'])
def test_empty_and_legacy_reach_exact_frozen_contract(migration_database, origin):
    url, engine = migration_database
    arguments = ['db_bootstrap.py']
    if origin == 'legacy':
        _fixture(engine)
        arguments.append('--adopt-verified-legacy')
    run_migration(url, *arguments)
    target = json.loads((ROOT / 'web/database/alembic/schema_targets' /
                         ('20261018_reconciled_' + engine.dialect.name + '.json')).read_text())['signature']
    with engine.connect() as connection:
        assert schema_signature(connection) == target
        assert connection.execute(text('SELECT version_num FROM alembic_version')).scalar_one() == '20261018_schema_reconciliation'
        if engine.dialect.name == 'postgresql':
            flags = connection.execute(text("SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE relname IN ('clientes','planes_generados','subscriptions','payments') AND relnamespace=current_schema()::regnamespace")).all()
            assert flags == [(False, False)] * 4
    # A second release is read-only/idempotent with an already migrated schema.
    run_migration(url, 'db_bootstrap.py')


def test_unrecognized_unversioned_schema_is_never_adopted(migration_database):
    url, engine = migration_database
    _fixture(engine)
    with engine.begin() as connection:
        connection.execute(text('ALTER TABLE usuarios ADD COLUMN unknown_drift INTEGER'))
    environment = os.environ.copy()
    environment['DATABASE_URL'] = url
    result = subprocess.run([sys.executable, '-X', 'utf8', 'db_bootstrap.py', '--adopt-verified-legacy'],
                            cwd=ROOT, env=environment, text=True, capture_output=True)
    assert result.returncode != 0
    from sqlalchemy import inspect
    with engine.connect() as connection:
        assert 'alembic_version' not in inspect(connection).get_table_names()


def test_historical_rows_and_custom_prices_survive_reconciliation(migration_database):
    url, engine = migration_database
    run_migration(url, '-m', 'alembic', 'upgrade', '20261018_billing_integrity')
    with engine.begin() as connection:
        for gym in ('old-gym', 'empty-gym'):
            connection.execute(text("INSERT INTO usuarios(id,email,password_hash,nombre,apellido,tipo,role,activo,fecha_registro) VALUES(:id,:email,'synthetic','Synthetic','','gym','OWNER',true,'2026-10-01')"),
                               {'id': gym, 'email': gym + '@example.test'})
        connection.execute(text("INSERT INTO gym_settings(id,gym_id,created_at,updated_at) VALUES('original-settings-uuid','old-gym','2026-10-01','2026-10-01')"))
        connection.execute(text("INSERT INTO gym_licenses(id,gym_id,license_key,plan_tier,max_clients,created_at,updated_at) VALUES('original-license-uuid','old-gym','synthetic-license','free',10,'2026-10-01','2026-10-01')"))
        for price in (500, 500, 725):
            connection.execute(text("INSERT INTO planes_suscripcion(gym_id,nombre,duracion_dias,precio,moneda,activo) VALUES('old-gym','1 Mes',30,:price,'MXN',true)"), {'price': price})
    run_migration(url, 'db_bootstrap.py')
    with engine.connect() as connection:
        assert connection.execute(text("SELECT legacy_id FROM gym_settings WHERE gym_id='old-gym'")).scalar_one() == 'original-settings-uuid'
        assert connection.execute(text("SELECT legacy_id FROM gym_licenses WHERE gym_id='old-gym'")).scalar_one() == 'original-license-uuid'
        prices = connection.execute(text("SELECT precio,template_key FROM planes_suscripcion WHERE gym_id='old-gym' ORDER BY precio")).all()
        assert prices == [(500.0, 'duration_30'), (725.0, None)]
        assert connection.execute(text("SELECT count(*) FROM planes_suscripcion WHERE gym_id='empty-gym'")).scalar_one() == 5
    # Integer defaults/sequences remain usable after converting the legacy PK.
    from sqlalchemy.orm import Session
    from web.database.models import GymSettings, GymLicense
    with Session(engine) as db:
        settings = GymSettings(gym_id='empty-gym')
        license = GymLicense(gym_id='empty-gym', license_key='synthetic-license-two', plan_tier='free', max_clients=10)
        db.add_all([settings, license])
        db.commit()
        assert settings.id > 1 and license.id > 1


def test_versioned_unknown_unique_constraint_aborts_instead_of_dropping_it(migration_database):
    url, engine = migration_database
    run_migration(url, '-m', 'alembic', 'upgrade', '20261018_billing_integrity')
    with engine.begin() as connection:
        connection.execute(text('CREATE UNIQUE INDEX custom_unknown_unique ON usuarios(nombre)'))
    environment = os.environ.copy()
    environment['DATABASE_URL'] = url
    result = subprocess.run([sys.executable, '-X', 'utf8', 'db_bootstrap.py'], cwd=ROOT,
                            env=environment, text=True, capture_output=True)
    assert result.returncode != 0
    from sqlalchemy import inspect
    with engine.connect() as connection:
        assert connection.execute(text('SELECT version_num FROM alembic_version')).scalar_one() == '20261018_billing_integrity'
        assert 'custom_unknown_unique' in {item['name'] for item in inspect(connection).get_indexes('usuarios')}


def test_legacy_roles_only_backfill_gym_owners(migration_database):
    url, engine = migration_database
    _fixture(engine)
    with engine.begin() as connection:
        for identity, kind, parent in (('owner', 'gym', None), ('person', 'usuario', None), ('member', 'gym', 'owner')):
            connection.execute(text("INSERT INTO usuarios(id,email,password_hash,nombre,apellido,tipo,role,team_gym_id,activo,fecha_registro) VALUES(:id,:email,'synthetic','Synthetic','',:kind,'viewer',:parent,true,'2026-10-01')"),
                               {'id': identity, 'email': identity + '@example.test', 'kind': kind, 'parent': parent})
    run_migration(url, 'db_bootstrap.py', '--adopt-verified-legacy')
    with engine.connect() as connection:
        roles = dict(connection.execute(text('SELECT id,role FROM usuarios')).all())
        assert roles == {'owner': 'OWNER', 'person': 'VIEWER', 'member': 'VIEWER'}
        assert connection.execute(text('SELECT DISTINCT session_version FROM usuarios')).scalars().all() == [0]


def test_parallel_onboarding_uses_five_templates(migration_database):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from sqlalchemy.orm import Session
    from web.database.models import Usuario, UserRole
    from web.database.repository import _crear_planes_default
    url, engine = migration_database
    run_migration(url, 'db_bootstrap.py')
    with Session(engine) as db:
        db.add(Usuario(id='parallel-owner', email='parallel@example.test', password_hash='synthetic',
                       nombre='Synthetic', tipo='gym', role=UserRole.OWNER))
        db.commit()
    start = Barrier(2)
    def onboard():
        with Session(engine) as db:
            start.wait(5)
            _crear_planes_default(db, 'parallel-owner')
            db.commit()
    with ThreadPoolExecutor(max_workers=2) as pool:
        tasks = [pool.submit(onboard) for _ in range(2)]
        for task in tasks:
            task.result(timeout=15)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM planes_suscripcion WHERE gym_id='parallel-owner'")).scalar_one() == 5


def test_invalid_role_aborts_and_rolls_back_adoption(migration_database):
    url, engine = migration_database
    _fixture(engine)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO usuarios(id,email,password_hash,nombre,apellido,tipo,role,activo,fecha_registro) VALUES('invalid-role','invalid@example.test','synthetic','Synthetic','','usuario','unrecognized',true,'2026-10-01')"))
    environment = os.environ.copy()
    environment['DATABASE_URL'] = url
    result = subprocess.run([sys.executable, '-X', 'utf8', 'db_bootstrap.py', '--adopt-verified-legacy'],
                            cwd=ROOT, env=environment, text=True, capture_output=True)
    assert result.returncode != 0
    from sqlalchemy import inspect
    with engine.connect() as connection:
        inspector = inspect(connection)
        assert 'alembic_version' not in inspector.get_table_names()
        assert 'session_version' not in {column['name'] for column in inspector.get_columns('usuarios')}
        assert connection.execute(text("SELECT role FROM usuarios WHERE id='invalid-role'")).scalar_one() == 'unrecognized'


def test_previously_active_rls_is_never_disabled(migration_database):
    url, engine = migration_database
    run_migration(url, '-m', 'alembic', 'upgrade', '20261018_billing_integrity')
    if engine.dialect.name == 'postgresql':
        with engine.begin() as connection:
            for statement in (
                'ALTER TABLE clientes ENABLE ROW LEVEL SECURITY', 'ALTER TABLE clientes FORCE ROW LEVEL SECURITY',
                'ALTER TABLE planes_generados ENABLE ROW LEVEL SECURITY', 'ALTER TABLE planes_generados FORCE ROW LEVEL SECURITY',
                'ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY', 'ALTER TABLE subscriptions FORCE ROW LEVEL SECURITY',
                'ALTER TABLE payments ENABLE ROW LEVEL SECURITY', 'ALTER TABLE payments FORCE ROW LEVEL SECURITY',
            ):
                connection.execute(text(statement))
    run_migration(url, 'db_bootstrap.py')
    with engine.connect() as connection:
        if engine.dialect.name == 'postgresql':
            flags = connection.execute(text("SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE relname IN ('clientes','planes_generados','subscriptions','payments') AND relnamespace=current_schema()::regnamespace")).all()
            assert flags == [(True, True)] * 4
        else:
            assert connection.exec_driver_sql('PRAGMA foreign_key_check').all() == []


@pytest.mark.parametrize('migration_database', ['postgresql'], indirect=True)
def test_postgres_timezone_drift_is_not_treated_as_exact_legacy(migration_database):
    url, engine = migration_database
    _fixture(engine)
    with engine.begin() as connection:
        before = schema_signature(connection)
        connection.execute(text('ALTER TABLE usuarios ALTER COLUMN fecha_registro TYPE TIMESTAMP WITH TIME ZONE'))
        after = schema_signature(connection)
        assert before != after
        changed = next(column for column in after['tables']['usuarios']['columns'] if column['name'] == 'fecha_registro')
        assert changed['type_attributes']['timezone'] is True
    environment = os.environ.copy()
    environment['DATABASE_URL'] = url
    result = subprocess.run([sys.executable, '-X', 'utf8', 'db_bootstrap.py', '--adopt-verified-legacy'],
                            cwd=ROOT, env=environment, text=True, capture_output=True)
    assert result.returncode != 0
    from sqlalchemy import inspect
    with engine.connect() as connection:
        assert 'alembic_version' not in inspect(connection).get_table_names()


@pytest.mark.parametrize('migration_database', ['postgresql'], indirect=True)
@pytest.mark.parametrize('condition', ["tipo IN ('gym','usuario','admin','injected')", "tipo IN ('gym','usuario','admin') OR true"])
def test_pg_check_normalization_rejects_changed_values_or_conditions(migration_database, condition):
    url, engine = migration_database
    _fixture(engine)
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    with engine.begin() as connection:
        operations = Operations(MigrationContext.configure(connection))
        operations.drop_constraint('ck_usuario_tipo', 'usuarios', type_='check')
        operations.create_check_constraint('ck_usuario_tipo', 'usuarios', condition)
    environment = os.environ.copy()
    environment['DATABASE_URL'] = url
    result = subprocess.run([sys.executable, '-X', 'utf8', 'db_bootstrap.py', '--adopt-verified-legacy'],
                            cwd=ROOT, env=environment, text=True, capture_output=True)
    assert result.returncode != 0
    from sqlalchemy import inspect
    with engine.connect() as connection:
        assert 'alembic_version' not in inspect(connection).get_table_names()

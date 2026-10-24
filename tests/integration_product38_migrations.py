"""One new38 transition UUID: genuine37 predecessor, no create_all/stamp."""
import os
from pathlib import Path
import subprocess
import sys

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from tests.ci_web38.pg_fixtures import (database_schema, isolated_database, pg38_runtime)  # noqa: F401
from tests.integration_schema_migrations import run_migration
from tests.integration_stored_objects_migrations import snapshot
from web.database.schema_control import verify_runtime_schema
from web.database.models import Cliente, Usuario, UserRole

PREVIOUS = '20261020_account_security'
REVISION = '20261023_product_facts'


def test_real37_to38_preserves_rows_empty_downgrade_and_nonempty_refusal(pg38_runtime, tmp_path):
    with pg38_runtime.database(tmp_path) as (url, admin):
        run_migration(url, 'db_bootstrap.py', '--revision', PREVIOUS)
        with Session(admin) as db:
            db.add(Usuario(id='transition38-owner', email='transition38@example.invalid',
                password_hash='not-a-login', nombre='Synthetic', tipo='gym', role=UserRole.OWNER))
            db.flush()
            db.add(Cliente(id_cliente='transition38-client', gym_id='transition38-owner', nombre='Synthetic'))
            db.commit()
        columns, rows = snapshot(admin)
        verify_runtime_schema(admin, expected_revision=PREVIOUS)
        run_migration(url, 'db_bootstrap.py', '--revision', REVISION)
        verify_runtime_schema(admin, expected_revision=REVISION)
        assert snapshot(admin, columns)[1] == rows
        with admin.connect() as db:
            assert 'product_analytics_facts' in inspect(db).get_table_names()
            assert db.scalar(text('SELECT count(*) FROM product_analytics_facts')) == 0
        run_migration(url, 'db_bootstrap.py', '--revision', REVISION)
        assert snapshot(admin, columns)[1] == rows
        run_migration(url, '-m', 'alembic', 'downgrade', PREVIOUS)
        verify_runtime_schema(admin, expected_revision=PREVIOUS)
        assert snapshot(admin, columns)[1] == rows
        run_migration(url, 'db_bootstrap.py', '--revision', REVISION)
        with admin.begin() as db:
            db.execute(text("INSERT INTO product_analytics_facts(id,owner_id,context,client_id,event_type,"
                "source_id,source_version,origin) VALUES(:id,'transition38-owner','gym','transition38-client',"
                "'origin_declared','transition38-client',1,'demo')"), {'id': 'f' * 32})
        with admin.connect() as db:
            retained = tuple(db.execute(text('SELECT id,origin,occurred_at FROM product_analytics_facts')).one())
        env = dict(os.environ, DATABASE_URL=url, METODOBASE_TEST_DATABASE_URL='')
        result = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-m', 'alembic', 'downgrade', PREVIOUS],
            cwd=Path(__file__).resolve().parents[1], env=env, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False, timeout=90,
            **({'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}))
        assert result.returncode != 0
        verify_runtime_schema(admin, expected_revision=REVISION)
        with admin.connect() as db:
            assert tuple(db.execute(text('SELECT id,origin,occurred_at FROM product_analytics_facts')).one()) == retained
        assert snapshot(admin, columns)[1] == rows

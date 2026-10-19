"""Real PostgreSQL acceptance, invoked separately by the mandatory CI PG job.

Ordinary `tests/` discovery does not collect this integration filename. Invoke
it explicitly after prepare_postgres.py; absent configuration fails, never skips.
"""
import os
from urllib.parse import urlsplit

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from tests.isolation import validate_postgres_test_url


@pytest.fixture
def postgres_case(monkeypatch):
    """Seed two synthetic tenants through the separate migrator connection."""
    from web.database import engine as module
    from web.database.models import Cliente, Usuario, UserRole

    admin_url = os.environ["METODOBASE_TEST_MIGRATOR_URL"]
    app_url = os.environ["METODOBASE_TEST_POSTGRES_URL"]
    validate_postgres_test_url(admin_url)
    validate_postgres_test_url(app_url)
    assert urlsplit(admin_url).path == urlsplit(app_url).path
    admin = create_engine(admin_url)
    app = create_engine(app_url, pool_size=1, max_overflow=0)
    factory = sessionmaker(bind=app, expire_on_commit=False)
    monkeypatch.setattr(module, "_engine", app)
    monkeypatch.setattr(module, "_SessionLocal", factory)
    with admin.begin() as connection:
        connection.execute(text("TRUNCATE usuarios CASCADE"))
    with sessionmaker(bind=admin)() as db:
        for suffix in ("a", "b"):
            gym = "pg-synthetic-gym-" + suffix
            db.add(Usuario(id=gym, email=f"{gym}@example.test", password_hash="unused-synthetic",
                           nombre=gym, tipo="gym", role=UserRole.OWNER, activo=True))
        db.commit()
        for suffix in ("a", "b"):
            db.add(Cliente(id_cliente="pg-client-" + suffix, gym_id="pg-synthetic-gym-" + suffix,
                           nombre="Synthetic " + suffix, edad=30, peso_kg=70, estatura_cm=170,
                           nivel_actividad="moderada", objetivo="mantenimiento"))
        db.commit()
    yield app, factory
    with admin.begin() as connection:
        connection.execute(text("TRUNCATE usuarios CASCADE"))
    app.dispose()
    admin.dispose()


def test_real_app_role_cannot_bypass_rls(postgres_case):
    app, _ = postgres_case
    with app.connect() as db:
        flags = db.execute(text("SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user")).one()
        assert flags == (False, False)
        tables = db.execute(text("SELECT relname,relrowsecurity,relforcerowsecurity FROM pg_class WHERE relname IN ('clientes','planes_generados','subscriptions')")).all()
        assert len(tables) == 3
        assert all(enabled and forced for _, enabled, forced in tables)


def test_rls_denies_missing_tenant_and_pool_does_not_leak_it(postgres_case):
    from web.database.models import Cliente
    _, factory = postgres_case
    with factory() as db:
        assert db.scalars(select(Cliente)).all() == []
        db.execute(text("SELECT set_config('app.current_tenant', :tenant, true)"), {"tenant": "pg-synthetic-gym-a"})
        assert [row.id_cliente for row in db.scalars(select(Cliente)).all()] == ["pg-client-a"]
        assert db.scalars(select(Cliente).where(Cliente.id_cliente == "pg-client-b")).all() == []
        db.commit()
    with factory() as db:
        assert db.scalars(select(Cliente)).all() == []


def test_application_reinstalls_tenant_after_internal_commit(postgres_case):
    from web.database.engine import get_db
    from web.database.models import Cliente
    from web.middleware.tenant import current_tenant

    token = current_tenant.set("pg-synthetic-gym-a")
    session = get_db()
    try:
        db = next(session)
        assert [row.id_cliente for row in db.scalars(select(Cliente)).all()] == ["pg-client-a"]
        db.commit()
        assert [row.id_cliente for row in db.scalars(select(Cliente)).all()] == ["pg-client-a"]
    finally:
        session.close()
        current_tenant.reset(token)

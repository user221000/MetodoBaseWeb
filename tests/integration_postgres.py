"""Real PostgreSQL acceptance, invoked separately by the mandatory CI PG job.

Ordinary `tests/` discovery does not collect this integration filename. Invoke
it explicitly after prepare_postgres.py; absent configuration fails, never skips.
"""
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlsplit, urlunsplit
import uuid

import pytest
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.orm import Session, sessionmaker

from tests.isolation import validate_postgres_test_url


TENANT_A = "pg-synthetic-gym-a"
TENANT_B = "pg-synthetic-gym-b"
PERSONAL = "pg-synthetic-member"
CLIENT_IDS = {TENANT_A: "pg-client-a", TENANT_B: "pg-client-b", PERSONAL: PERSONAL}
PROTECTED = {
    "clientes": "gym_id", "planes_generados": "gym_id", "client_progress": "gym_id",
    "subscriptions": "gym_id", "payments": "gym_id", "stripe_customers": "gym_id",
    "invoices": "gym_id", "checkout_sessions": "gym_id", "gym_profiles": "gym_id",
    "gym_branding": "gym_id", "gym_settings": "gym_id", "gym_licenses": "gym_id",
    "planes_suscripcion": "gym_id", "audit_log": "gym_id", "user_subscriptions": "user_id",
    "generation_reservations": "user_id",
    "license_activations": "gym_id",
}


@pytest.fixture(scope="module")
def owned_postgres_database():
    """Migrate and seed only a database created by this fixture, never shared."""
    import psycopg2
    from psycopg2 import sql
    from web.database import models as m

    admin_url = os.environ["METODOBASE_TEST_MIGRATOR_URL"]
    app_url = os.environ["METODOBASE_TEST_POSTGRES_URL"]
    validate_postgres_test_url(admin_url)
    validate_postgres_test_url(app_url)
    admin_parts, app_parts = urlsplit(admin_url), urlsplit(app_url)
    assert (admin_parts.hostname, admin_parts.port) == (app_parts.hostname, app_parts.port)
    name = "metodobase_test_rls_" + uuid.uuid4().hex[:12]
    control = psycopg2.connect(admin_url.replace("postgresql+psycopg2://", "postgresql://", 1), connect_timeout=5)
    control.autocommit = True
    with control.cursor() as cursor:
        cursor.execute("SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=%s", (app_parts.username,))
        assert cursor.fetchone() == (False, False, False, False)
        cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    owned_admin = urlunsplit(admin_parts._replace(path="/" + name))
    owned_app = urlunsplit(app_parts._replace(path="/" + name))
    admin = create_engine(owned_admin)
    try:
        environment = dict(os.environ, DATABASE_URL=owned_admin, METODOBASE_TEST_DATABASE_URL="")
        migrated = subprocess.run([sys.executable, "-X", "utf8", "db_bootstrap.py"],
            cwd=Path(__file__).resolve().parents[1], env=environment,
            capture_output=True, text=True, encoding="utf-8", timeout=90)
        assert migrated.returncode == 0, migrated.stdout + migrated.stderr
        with admin.begin() as connection:
            connection.exec_driver_sql(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(app_parts.username)).as_string(control))
            connection.exec_driver_sql(sql.SQL("GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO {}").format(sql.Identifier(app_parts.username)).as_string(control))
            connection.exec_driver_sql(sql.SQL("GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO {}").format(sql.Identifier(app_parts.username)).as_string(control))
        with Session(admin) as db:
            for identity in (TENANT_A, TENANT_B):
                db.add(m.Usuario(id=identity, email=identity + "@example.test", password_hash="unused-synthetic",
                    nombre="Synthetic", tipo="gym", role=m.UserRole.OWNER, activo=True, session_version=0))
            db.commit()
            db.add(m.Usuario(id=PERSONAL, email="pg-member@example.test", password_hash="unused-synthetic",
                nombre="Personal member", tipo="usuario", role=m.UserRole.NUTRIOLOGO,
                team_gym_id=TENANT_A, activo=True, session_version=0))
            db.commit()
            for identity in (TENANT_A, TENANT_B, PERSONAL):
                client = CLIENT_IDS[identity]
                db.add(m.Cliente(id_cliente=client, gym_id=identity, nombre="Synthetic " + identity,
                    edad=30, peso_kg=70, estatura_cm=170, nivel_actividad="moderada", objetivo="mantenimiento"))
                db.flush()
                plan = m.PlanGenerado(id_cliente=client, gym_id=identity, ruta_pdf="synthetic.pdf")
                db.add(plan)
                db.flush()
                db.add_all([
                    m.ClientProgress(id_cliente=client, gym_id=identity, peso_kg=70),
                    m.Subscription(gym_id=identity, plan="free", status="active", max_clientes=10),
                    m.Payment(gym_id=identity, amount_cents=100, status="succeeded", currency="mxn"),
                    m.StripeCustomer(gym_id=identity, stripe_customer_id="cus_synthetic_" + identity),
                    m.Invoice(gym_id=identity, stripe_invoice_id="in_synthetic_" + identity,
                        amount_due=100, total=100, status="paid"),
                    m.CheckoutSession(id="cs_synthetic_" + identity, gym_id=identity, plan="standard",
                        email=identity + "@example.test"),
                    m.GymProfile(gym_id=identity, nombre_negocio="Synthetic"),
                    m.GymBranding(gym_id=identity, nombre_gym="Synthetic"),
                    m.GymSettings(gym_id=identity),
                    m.GymLicense(gym_id=identity, license_key="synthetic_" + identity,
                        plan_tier="free", max_clients=10),
                    m.PlanSuscripcion(gym_id=identity, nombre="Synthetic", duracion_dias=30, precio=100, moneda="MXN"),
                    m.AuditLog(gym_id=identity, accion="synthetic"),
                    m.UserSubscription(user_id=identity, mes_actual="2026-10", plan="starter", status="active"),
                    m.GenerationReservation(user_id=identity, request_key="synthetic-request",
                        period="2026-10", status="completed", plan_id=plan.id),
                    m.LicenseActivation(gym_id=identity, hardware_id="hardware_" + identity,
                        clave_hash="a" * 64, email=identity + "@example.test", plan="free", expira=None),
                ])
            db.add(m.AuditLog(gym_id=None, accion="synthetic-control-plane-null"))
            db.add(m.LicenseActivation(gym_id=None, hardware_id="unassociated-synthetic-hardware",
                clave_hash="b" * 64, email="unassociated@example.test", plan="standard", expira=None))
            db.commit()
        yield admin, owned_app
    finally:
        admin.dispose()
        with control.cursor() as cursor:
            assert name.startswith("metodobase_test_rls_")
            cursor.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
        control.close()


@pytest.fixture
def postgres_case(monkeypatch, owned_postgres_database):
    from web.database import engine as module

    _, app_url = owned_postgres_database
    app = create_engine(app_url, pool_size=1, max_overflow=0)
    factory = sessionmaker(bind=app, expire_on_commit=False)
    try:
        with monkeypatch.context() as patcher:
            patcher.setattr(module, "_engine", app)
            patcher.setattr(module, "_SessionLocal", factory)
            assert module.get_engine() is app
            yield app, factory
    finally:
        app.dispose()


def test_real_app_role_cannot_bypass_rls(postgres_case):
    app, _ = postgres_case
    with app.connect() as db:
        flags = db.execute(text("SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user")).one()
        assert flags == (False, False)
        tables = db.execute(text("SELECT relname,relrowsecurity,relforcerowsecurity FROM pg_class WHERE relnamespace='public'::regnamespace")).all()
        tables = [row for row in tables if row[0] in PROTECTED]
        assert len(tables) == len(PROTECTED)
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


@pytest.mark.parametrize("table,column", sorted(PROTECTED.items()))
def test_all_protected_tables_filter_real_rows_for_direct_sessions(postgres_case, table, column):
    from web.database.models import Base
    from web.middleware.tenant import current_tenant

    app, _ = postgres_case
    token = current_tenant.set(TENANT_A)
    try:
        with Session(app) as db:
            record = Base.metadata.tables[table]
            assert db.scalars(select(record.c[column])).all() == [TENANT_A]
    finally:
        current_tenant.reset(token)


@pytest.mark.parametrize("table,column", sorted(PROTECTED.items()))
def test_missing_tenant_cannot_read_any_protected_family_including_null_legacy_rows(postgres_case, table, column):
    from web.database.models import Base
    from web.middleware.tenant import current_tenant

    app, _ = postgres_case
    token = current_tenant.set("")
    try:
        with Session(app) as db:
            assert db.scalars(select(Base.metadata.tables[table].c[column])).all() == []
    finally:
        current_tenant.reset(token)


@pytest.mark.parametrize("table,column", sorted(PROTECTED.items()))
def test_protected_tables_allow_own_writes_but_hide_foreign_update_delete(postgres_case, table, column):
    """Real DML proves a deny-all policy cannot satisfy the read boundary."""
    from web.database.models import Base
    from web.middleware.tenant import current_tenant

    app, _ = postgres_case
    record = Base.metadata.tables[table]
    token = current_tenant.set(TENANT_A)
    try:
        with Session(app) as db:
            original = dict(db.execute(select(record)).mappings().one())
            assert db.execute(record.update().where(record.c[column] == TENANT_B)
                              .values({column: TENANT_A})).rowcount == 0
            assert db.execute(record.delete().where(record.c[column] == TENANT_B)).rowcount == 0
            assert db.execute(record.update().where(record.c[column] == TENANT_A)
                              .values({column: TENANT_A})).rowcount == 1
            # A savepoint restores cascaded dependants after testing own DELETE
            # and INSERT with the original synthetic row and foreign keys.
            savepoint = db.begin_nested()
            assert db.execute(record.delete().where(record.c[column] == TENANT_A)).rowcount == 1
            assert db.execute(record.insert().values(**original)).rowcount == 1
            assert db.scalar(select(record.c[column])) == TENANT_A
            savepoint.rollback()
            db.rollback()
    finally:
        current_tenant.reset(token)


@pytest.mark.parametrize("table,column", sorted(PROTECTED.items()))
def test_protected_tables_reject_moving_own_row_to_foreign_tenant(postgres_case, table, column):
    from sqlalchemy.exc import DBAPIError
    from web.database.models import Base
    from web.middleware.tenant import current_tenant

    app, _ = postgres_case
    record = Base.metadata.tables[table]
    token = current_tenant.set(TENANT_A)
    try:
        with Session(app) as db, pytest.raises(DBAPIError) as failure:
            db.execute(record.update().where(record.c[column] == TENANT_A).values({column: TENANT_B}))
            db.commit()
        assert failure.value.orig.pgcode == "42501"
    finally:
        current_tenant.reset(token)


def test_direct_connection_and_session_reinstall_context_after_commit_and_rollback(postgres_case):
    from web.middleware.tenant import current_tenant

    app, _ = postgres_case
    token = current_tenant.set(TENANT_A)
    try:
        with app.connect() as connection:
            assert connection.scalar(text("SELECT current_setting('app.current_tenant', true)")) == TENANT_A
            connection.commit()
            assert connection.scalar(text("SELECT current_setting('app.current_tenant', true)")) == TENANT_A
            connection.rollback()
            assert connection.scalar(text("SELECT current_setting('app.current_tenant', true)")) == TENANT_A
        with Session(app) as db:
            assert db.scalar(text("SELECT current_setting('app.current_tenant', true)")) == TENANT_A
            db.commit()
            assert db.scalar(text("SELECT current_setting('app.current_tenant', true)")) == TENANT_A
            db.rollback()
            assert db.scalar(text("SELECT current_setting('app.current_tenant', true)")) == TENANT_A
    finally:
        current_tenant.reset(token)


def test_pool_one_connection_serves_two_tenants_then_denies_anonymous(postgres_case):
    from web.database.models import Cliente
    from web.middleware.tenant import current_tenant

    app, _ = postgres_case
    connection_ids = []
    for identity in (TENANT_A, TENANT_B, ""):
        token = current_tenant.set(identity)
        try:
            with Session(app) as db:
                connection_ids.append(db.scalar(text("SELECT pg_backend_pid()")))
                expected = [CLIENT_IDS[identity]] if identity else []
                assert db.scalars(select(Cliente.id_cliente)).all() == expected
                db.commit()
        finally:
            current_tenant.reset(token)
    assert len(set(connection_ids)) == 1


def test_empty_context_overrides_stale_session_setting(postgres_case):
    from web.database.models import Cliente

    app, _ = postgres_case
    with app.connect() as connection:
        connection.execute(text("SELECT set_config('app.current_tenant', :tenant, false)"), {"tenant": TENANT_B})
        connection.commit()
        try:
            assert connection.scalar(text("SELECT current_setting('app.current_tenant', true)")) == ""
            assert connection.scalars(select(Cliente.id_cliente)).all() == []
        finally:
            connection.rollback()
            connection.execute(text("SELECT set_config('app.current_tenant', '', false)"))
            connection.commit()


@pytest.mark.parametrize("scoped_tenant", ["", TENANT_A])
def test_unscoped_or_foreign_tenant_insert_is_rejected_by_postgres(postgres_case, scoped_tenant):
    from sqlalchemy.exc import DBAPIError
    from web.database.models import Cliente
    from web.middleware.tenant import current_tenant

    app, _ = postgres_case
    token = current_tenant.set(scoped_tenant)
    try:
        with Session(app) as db, pytest.raises(DBAPIError) as failure:
            db.add(Cliente(id_cliente="forbidden-insert", gym_id=TENANT_B, nombre="Synthetic rejected"))
            db.commit()
        assert failure.value.orig.pgcode == "42501"
    finally:
        current_tenant.reset(token)


@pytest.mark.parametrize("mode", ["direct", "dependency"])
def test_context_install_failure_blocks_business_queries(postgres_case, mode):
    from web.database.engine import get_db
    from web.middleware.tenant import current_tenant

    app, _ = postgres_case
    business_queries = []

    def reject_context(connection, cursor, statement, parameters, context, many):
        if "set_config('app.current_tenant'" in statement:
            raise RuntimeError("synthetic context install failed")
        if statement.strip() == "SELECT 1":
            business_queries.append(True)

    event.listen(app, "before_cursor_execute", reject_context)
    token = current_tenant.set(TENANT_A)
    generator = None
    try:
        with pytest.raises(RuntimeError, match="synthetic context install failed"):
            if mode == "direct":
                with Session(app) as db:
                    db.execute(text("SELECT 1"))
            else:
                generator = get_db()
                db = next(generator)
                db.execute(text("SELECT 1"))
        assert not business_queries
    finally:
        if generator is not None:
            generator.close()
        current_tenant.reset(token)
        event.remove(app, "before_cursor_execute", reject_context)


def test_verified_callback_subject_survives_commits_and_cannot_switch_account(postgres_case):
    from web.database.models import Cliente
    from web.database.tenant_context import bind_verified_subject

    app, _ = postgres_case
    with Session(app) as db:
        bind_verified_subject(db, TENANT_A)
        assert db.scalars(select(Cliente.id_cliente)).all() == [CLIENT_IDS[TENANT_A]]
        db.commit()
        assert db.scalars(select(Cliente.id_cliente)).all() == [CLIENT_IDS[TENANT_A]]
        db.rollback()
        assert db.scalars(select(Cliente.id_cliente)).all() == [CLIENT_IDS[TENANT_A]]
        with pytest.raises(ValueError, match="mismatch"):
            bind_verified_subject(db, TENANT_B)


def test_background_worker_carries_scope_and_resets_context(postgres_case):
    from concurrent.futures import ThreadPoolExecutor
    from web.database.models import Cliente
    from web.database.tenant_context import current_tenant, tenant_task

    app, _ = postgres_case

    @tenant_task("gym_id")
    def worker(gym_id):
        with Session(app) as db:
            return db.scalars(select(Cliente.id_cliente)).all()

    def invoke():
        result = worker(TENANT_A)
        assert current_tenant.get() == ""
        return result

    with ThreadPoolExecutor(max_workers=1) as executor:
        assert executor.submit(invoke).result(timeout=10) == [CLIENT_IDS[TENANT_A]]
    assert current_tenant.get() == ""


def test_real_member_token_uses_team_scope_for_professional_and_own_scope_for_personal(postgres_case):
    from fastapi import Depends, FastAPI
    from fastapi.testclient import TestClient
    from web.auth import crear_access_token, identity_from_user, init_auth
    from web.database.engine import get_db
    from web.database.models import Cliente, Usuario
    from web.middleware.tenant import TenantMiddleware

    init_auth()
    app = FastAPI()
    app.add_middleware(TenantMiddleware)

    @app.get("/api/clients-synthetic")
    @app.get("/api/usuario/profile-synthetic")
    def read_scope(db=Depends(get_db)):
        return {"clients": db.scalars(select(Cliente.id_cliente)).all()}

    _, factory = postgres_case
    with factory() as db:
        token = crear_access_token(identity_from_user(db.get(Usuario, PERSONAL), db))
    with TestClient(app, headers={"Authorization": "Bearer " + token,
            "X-Tenant-ID": TENANT_B}) as client:
        professional = client.get("/api/clients-synthetic", params={"gym_id": TENANT_B})
        assert professional.status_code == 200
        assert professional.json()["clients"] == [CLIENT_IDS[TENANT_A]]
        personal = client.get("/api/usuario/profile-synthetic", params={"gym_id": TENANT_B})
        assert personal.status_code == 200
        assert personal.json()["clients"] == [PERSONAL]

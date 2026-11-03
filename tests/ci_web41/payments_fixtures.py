"""One genuinely migrated payments41 UUID, restricted pool2 and normal closure."""
import json
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from tests.ci_web41 import payments_contract as contract


def pytest_addoption(parser):
    group = parser.getgroup("payments41-postgres")
    for name in ("profile", "generation", "ack", "evidence"):
        group.addoption("--payments41-" + name, type=Path)


@pytest.fixture(scope="module", autouse=True)
def database_schema():
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


@pytest.fixture(scope="module")
def payments41_database(request):
    from scripts.scan_secrets import _private_evidence
    from tests.ci_web37.pg_lease import profile as read_profile
    from tests.ci_web41.pg_control import check_control_generation
    from tests.integration_schema_migrations import run_migration
    from web.database.tenant_context import configure_tenant_engine
    from web.database.schema_control import verify_runtime_schema
    from web.database.models import Base
    import psycopg2
    from psycopg2 import sql

    paths = {key: request.config.getoption("--payments41-" + key) for key in ("profile", "generation", "ack", "evidence")}
    if any(path is None or not path.is_absolute() for path in paths.values()):
        raise pytest.UsageError("Four explicit absolute payments41 authorities are required")
    value = contract.build_contract(paths["profile"], paths["generation"])
    contract.require_ack(paths["ack"], value)
    config = read_profile(paths["profile"], expected_sha256=value["profile_sha256"])
    check_control_generation(value, config)
    evidence = _private_evidence(paths["evidence"])

    def record(name, body):
        (evidence / name).write_text(json.dumps(body, indent=2) + "\n", encoding="utf8")

    name = "metodobase_test_payments41_" + uuid.uuid4().hex
    record("planned-before-create.json", {"name": name, "contract_sha256": contract.digest(value), "plan": contract.PLAN})
    control_url = make_url(config["METODOBASE_TEST_MIGRATOR_URL"])
    admin_url = control_url.set(database=name)
    app_url = make_url(config["METODOBASE_TEST_POSTGRES_URL"]).set(database=name)
    admin = app = None
    oid = None
    result = {"accepted": False, "created_UUIDs": 0, "normally_closed_UUIDs": 0,
              "forced_DROP_or_backend_termination": False, "plan": contract.PLAN}

    @contextmanager
    def control():
        db = psycopg2.connect(control_url.render_as_string(hide_password=False).replace("postgresql+psycopg2://", "postgresql://", 1))
        db.autocommit = True
        try:
            yield db
        finally:
            db.close()

    try:
        with control() as db, db.cursor() as cursor:
            contract.require_ack(paths["ack"], value)
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
            result["created_UUIDs"] = 1
            cursor.execute("SELECT oid FROM pg_database WHERE datname=%s", (name,))
            oid = cursor.fetchone()[0]
        run_migration(admin_url.render_as_string(hide_password=False), "db_bootstrap.py", "--revision", "head")
        admin = create_engine(admin_url, pool_size=1, max_overflow=0)
        app_identifier = admin.dialect.identifier_preparer.quote(str(app_url.username))
        with admin.begin() as db:
            db.exec_driver_sql("GRANT USAGE ON SCHEMA public TO " + app_identifier)
            db.exec_driver_sql("GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO " + app_identifier)
            db.exec_driver_sql("GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO " + app_identifier)
        app = configure_tenant_engine(create_engine(app_url, pool_size=2, max_overflow=0, pool_timeout=15))
        verify_runtime_schema(app, expected_revision="20261102_payment_refund_facts")
        with app.connect() as db:
            flags = tuple(db.execute(text("SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole,rolreplication FROM pg_roles WHERE rolname=current_user")).one())
            assert flags == (False,) * 5
            assert db.scalar(text("SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace AND relkind='r' AND relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)")) == 0
            assert db.scalar(text("SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace AND relkind='r' AND relrowsecurity AND relforcerowsecurity")) == 35
        result["restricted_role_five_flags"] = list(flags)
        yield SimpleNamespace(admin=admin, app=app, name=name, record=record)
        result["case_payload_completed"] = True
    finally:
        if app is not None:
            assert app.pool.checkedout() == 0
            app.dispose()
        if admin is not None:
            assert admin.pool.checkedout() == 0
            admin.dispose()
        if oid is not None:
            check_control_generation(value, config)
            with control() as db, db.cursor() as cursor:
                cursor.execute("SELECT oid FROM pg_database WHERE datname=%s", (name,))
                assert cursor.fetchone() == (oid,)
                cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE datname=%s", (name,))
                assert cursor.fetchone() == (0,)
                cursor.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))
                cursor.execute("SELECT count(*) FROM pg_database WHERE datname=%s OR oid=%s", (name, oid))
                assert cursor.fetchone() == (0,)
                result["normally_closed_UUIDs"] = 1
                result["fresh_database_and_OID_absent"] = True
        result["source_profile_generation_quiet"] = contract.build_contract(paths["profile"], paths["generation"]) == value
        result["accepted"] = (result.get("case_payload_completed") is True and result["source_profile_generation_quiet"]
                              and result["created_UUIDs"] == result["normally_closed_UUIDs"] == 1)
        record("closure.json", result)


@pytest.fixture
def payments41_case(payments41_database, monkeypatch):
    from web.database import engine as database
    from web.database.models import Base, Usuario, UserRole, UserSubscription
    from web.database.tenant_context import tenant_scope
    from sqlalchemy.orm import sessionmaker
    from tests.test_stripe_invoice_authority_peer import invoice_case

    fixture = payments41_database
    # The complete UUID is owned by this five-case campaign. No external rows
    # exist in it; each case starts with an independent synthetic A/B portfolio.
    with fixture.admin.begin() as db:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
    actors = [{"id": "payments41-a", "email": "payments41-a@example.invalid", "nombre": "Synthetic A", "tipo": "usuario", "role": "owner"},
              {"id": "payments41-b", "email": "payments41-b@example.invalid", "nombre": "Synthetic B", "tipo": "usuario", "role": "owner"}]
    with Session(fixture.admin) as db:
        for actor in actors:
            db.add(Usuario(id=actor["id"], email=actor["email"], nombre=actor["nombre"], password_hash="unused-offline",
                           tipo="usuario", role=UserRole.OWNER, activo=True, session_version=0))
        db.flush()
        db.add(UserSubscription(user_id=actors[1]["id"], plan="starter", max_planes_mes=1, planes_usados_mes=1, mes_actual="2026-11"))
        db.commit()
    factory = sessionmaker(bind=fixture.app, expire_on_commit=False)
    monkeypatch.setattr(database, "_engine", fixture.app)
    monkeypatch.setattr(database, "_SessionLocal", factory)
    with tenant_scope(actors[0]["id"]):
        case = invoice_case.__wrapped__((None, factory, actors[0]), monkeypatch)
    yield case, fixture
    assert fixture.app.pool.checkedout() == 0 and fixture.admin.pool.checkedout() == 0

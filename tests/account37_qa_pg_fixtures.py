"""Independent current37 PostgreSQL transport, never a historical retarget.

The service replay's shared factory explicitly scopes its assertion-oracle
MFA reads. That transport cannot establish production actor binding. Separate
normal-factory controls and all HTTP cases use no such prebinding.
"""
import base64
import json
import os
from pathlib import Path
import uuid

import pytest
from sqlalchemy import event, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from tests.ci_web37.pg_close import owned_database
from tests.integration_provider_subjects import application_engine
from tests.integration_schema_migrations import run_migration

REVISION = "20261020_account_security"


def assert_blank_pool(engine):
    assert engine.pool.size() == 1 and engine.pool._max_overflow == 0
    assert engine.pool.checkedout() == 0
    with engine.connect() as db:
        assert tuple(db.execute(text("SELECT current_setting('app.current_tenant',true),"
            "current_setting('app.mfa_actor',true),current_setting('app.client_invitation_digest',true),"
            "current_setting('app.notification_exclude_digest',true)")).one()) == ("", "", "", "")
    assert engine.pool.checkedout() == 0


def witness(engine):
    from web.database.models import Base
    from web.database.schema_control import verify_runtime_schema
    from web.database.alembic.history_index_contract_v1 import expected_history_index, history_index_signature
    verify_runtime_schema(engine, expected_revision=REVISION)
    with engine.connect() as db:
        flags = tuple(db.execute(text("SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole,"
            "pg_has_role(current_user,(SELECT relowner FROM pg_class WHERE oid='usuarios'::regclass),'MEMBER') "
            "FROM pg_roles WHERE rolname=current_user")).one())
        force = db.scalar(text("SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace "
            "AND relkind='r' AND relrowsecurity AND relforcerowsecurity"))
        physical = len(inspect(db).get_table_names())
        nonowner = db.scalar(text("SELECT datdba<>(SELECT oid FROM pg_roles WHERE rolname=current_user) "
            "FROM pg_database WHERE datname=current_database()"))
        index = history_index_signature(db)
    assert flags == (False,) * 5 and force == 32 and nonowner is True
    assert physical == 42 and len(Base.metadata.tables) == 41
    assert index == expected_history_index("postgresql")
    assert_blank_pool(engine)
    return {"revision": REVISION, "physical": physical, "ORM": len(Base.metadata.tables),
            "FORCE_RLS": force, "role_flags_and_owner_membership": list(flags),
            "nonowner": nonowner, "pool_size": 1, "max_overflow": 0, "history_index": index}


@pytest.fixture(scope="module")
def peer37_database(tmp_path_factory):
    with owned_database("postgresql", tmp_path_factory.mktemp("qa-account37")) as (url, admin):
        run_migration(url, "db_bootstrap.py", "--revision", REVISION)
        application = application_engine(url, admin)
        try:
            record = witness(application)
            output = Path(os.environ["METODOBASE_TEST_EVIDENCE_DIR"])
            (output / "peer37-role-witness.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
            yield admin, application
        finally:
            application.dispose()


@pytest.fixture(autouse=True)
def pool_released_after_case(peer37_database):
    yield
    assert_blank_pool(peer37_database[1])


def seeded_case(database, monkeypatch, *, oracle_mfa_context=False):
    from tests.account_security37_fixtures import PASSWORD
    from web.auth import crear_token_pair, hash_password, identity_from_user
    from web.database.models import Usuario, UserRole
    from web.settings import get_settings
    admin, application = database
    monkeypatch.setattr(get_settings(), "RESEND_API_KEY", "synthetic-independent37-no-network")
    monkeypatch.setattr(get_settings(), "MFA_ENCRYPTION_KEY", base64.urlsafe_b64encode(b"Q" * 32).decode())
    user = str(uuid.uuid4())
    with Session(admin) as db:
        row = Usuario(id=user, email=uuid.uuid4().hex + "@example.invalid", nombre="Synthetic independent37",
                      password_hash=hash_password(PASSWORD), tipo="usuario", role=UserRole.VIEWER)
        db.add(row)
        db.flush()
        expected = identity_from_user(row, db)
        pair = crear_token_pair(expected, db=db)
        db.commit()
    class OracleSession(Session):
        pass
    if oracle_mfa_context:
        @event.listens_for(OracleSession, "after_begin")
        def oracle_actor(_session, _transaction, connection):
            connection.execute(text("SELECT set_config('app.mfa_actor',:actor,true)"), {"actor": user})
    factory = sessionmaker(bind=application, class_=OracleSession if oracle_mfa_context else Session,
                           expire_on_commit=True, autoflush=False)
    return {"factory": factory, "engine": application, "admin": admin, "expected": expected,
            "user": user, "access": pair["access_token"], "refresh": pair["refresh_token"],
            "oracle_mfa_context": oracle_mfa_context}


@pytest.fixture
def account37(peer37_database, monkeypatch):
    return seeded_case(peer37_database, monkeypatch, oracle_mfa_context=True)


@pytest.fixture
def normal37(peer37_database, monkeypatch):
    return seeded_case(peer37_database, monkeypatch, oracle_mfa_context=False)

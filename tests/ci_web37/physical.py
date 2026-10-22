"""Physical current37 witnesses from a restricted connection, never model-only."""
from __future__ import annotations

import hashlib
import json

from sqlalchemy import inspect, text

REVISION = "20261020_account_security"


def physical_contract(engine, *, expected_pool=1):
    """Fail closed on a historical schema, permissive role, or leaking pool."""
    from web.database.alembic.history_index_contract_v1 import (
        expected_history_index,
        history_index_signature,
    )
    from web.database.models import Base
    from web.database.schema_control import expected_head, verify_runtime_schema

    assert engine.dialect.name == "postgresql"
    assert expected_head() == REVISION and len(Base.metadata.tables) == 41
    assert type(expected_pool) is int and expected_pool in {1, 6}
    assert engine.pool.size() == expected_pool and engine.pool._max_overflow == 0
    verify_runtime_schema(engine, expected_revision=REVISION)
    with engine.connect() as db:
        revision = db.scalar(text("SELECT version_num FROM alembic_version"))
        tables = inspect(db).get_table_names()
        flags = tuple(db.execute(text(
            "SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole "
            "FROM pg_roles WHERE rolname=current_user")).one())
        nonowner = db.scalar(text("SELECT pg_get_userbyid(datdba)<>current_user "
                                 "FROM pg_database WHERE datname=current_database()"))
        owned = db.scalar(text("SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace "
                               "AND relkind='r' AND relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)"))
        force = db.scalar(text("SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace "
                               "AND relkind='r' AND relrowsecurity AND relforcerowsecurity"))
        member = db.scalar(text("SELECT pg_has_role(current_user,relowner,'MEMBER') "
                                "FROM pg_class WHERE oid='usuarios'::regclass"))
        gucs = tuple(db.execute(text(
            "SELECT current_setting('app.current_tenant',true),"
            "current_setting('app.mfa_actor',true),"
            "current_setting('app.client_invitation_digest',true),"
            "current_setting('app.notification_exclude_digest',true)")).one())
        fks = db.execute(text("SELECT c.relname,k.conname,pg_get_constraintdef(k.oid),k.convalidated "
            "FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid "
            "WHERE c.relnamespace='public'::regnamespace AND k.contype='f' "
            "ORDER BY c.relname,k.conname")).all()
        history_index = history_index_signature(db)
        assert revision == REVISION and len(tables) == 42
        assert flags == (False,) * 4 and nonowner is True and owned == 0 and member is False
        assert force == 32 and gucs == ("", "", "", "")
        assert fks and all(row[3] for row in fks)
        assert history_index == expected_history_index("postgresql")
    assert engine.pool.checkedout() == 0
    value = {"revision": revision, "model_tables": 41, "physical_tables": len(tables),
            "FORCE_RLS_tables": force, "role_flags4": list(flags), "nonowner": True,
            "owner_membership": False, "owned_tables": owned, "pool_size": expected_pool,
            "max_overflow": 0, "blank_contexts4": True,
            "history_index": history_index,
            "validated_foreign_keys_sha256": hashlib.sha256(json.dumps(
                [list(row) for row in fks], separators=(",", ":")).encode()).hexdigest()}
    from tests.ci_web37.pg_observer import record
    record("current37", value)
    return value


def blank_pool(engine):
    """Observe a new checkout after the business request released its Session."""
    assert engine.pool.checkedout() == 0
    with engine.connect() as db:
        assert tuple(db.execute(text(
            "SELECT current_setting('app.current_tenant',true),"
            "current_setting('app.mfa_actor',true),"
            "current_setting('app.client_invitation_digest',true),"
            "current_setting('app.notification_exclude_digest',true)")).one()) == ("", "", "", "")
    assert engine.pool.checkedout() == 0

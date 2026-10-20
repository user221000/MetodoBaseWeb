"""Own critical-operation controls using normal Sessions without oracle actor binding."""
import base64
from datetime import UTC, datetime
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi import HTTPException
from sqlalchemy import event, inspect, select, text
from sqlalchemy.orm import Session

from tests.account37_qa_pg_fixtures import assert_blank_pool, seeded_case
from tests.account_security37_owned import owned_database
from tests.integration_schema_migrations import run_migration
from tests.integration_stored_objects_migrations import snapshot
from web.database.models import MfaAuthorization, MfaCredential, MfaRecoveryCode, RefreshToken, Usuario
from web.database.tenant_context import current_tenant, tenant_scope
from web.services import account_security as account, mfa_service as mfa


def issue(case):
    packets = []
    reply = account.issue_email(case["expected"], factory=case["factory"],
        sender=lambda recipient, link: packets.append((recipient, link)) or True)
    assert reply["delivery"] == "provider_accepted" and len(packets) == 1
    return parse_qs(urlsplit(packets[0][1]).fragment)["token"][0]


def primary(case):
    from tests.account_security37_fixtures import PASSWORD
    assert case["oracle_mfa_context"] is False
    with case["factory"]() as db:
        return mfa.reauthenticate(db, case["expected"], case["access"], password=PASSWORD)["reauthentication_token"]


def current_factor(case):
    from web.auth import identity_from_user
    from web.services.mfa_crypto import totp
    proof = primary(case)
    with case["factory"]() as db:
        enrollment = mfa.enroll(db, case["expected"], case["access"], proof)
    now = datetime.now(UTC)
    with case["factory"]() as db:
        kit = mfa.confirm_enrollment(db, case["expected"], enrollment["enrollment_id"],
            totp(base64.b32decode(enrollment["secret"]), int(now.timestamp()) // 30), now=now)
    with Session(case["admin"]) as db:
        case["expected"] = identity_from_user(db.get(Usuario, case["user"]), db)
    with case["factory"]() as db:
        challenge = mfa.login(db, case["expected"])
    with case["factory"]() as db:
        pair = mfa.verify_login(db, challenge["challenge"], recovery_code=kit["recovery_codes"][0])
    case["access"] = pair["token"]
    return kit["recovery_codes"][1:]


def test_normal_factory_email_request_persists_only_contact_purpose(normal37):
    case = normal37
    assert case["oracle_mfa_context"] is False
    proof = issue(case)
    with Session(case["admin"]) as db:
        actor = db.get(Usuario, case["user"])
        assert actor.email_verification_hash == account.digest(proof) and proof != actor.email_verification_hash
        assert actor.email_verification_session_version == case["expected"]["session_version"]
        assert actor.email_verification_contact_version == actor.notification_contact_version == 0
        assert actor.email_verified_at is None
        assert actor.email_verification_expires_at > actor.email_verification_issued_at
    assert_blank_pool(case["engine"])


def test_normal_factory_confirmation_uses_empty_context_then_restores_caller(normal37):
    case = normal37
    proof = issue(case)
    observed = []
    in_probe = False
    def probe(connection, _cursor, statement, _parameters, _context, _many):
        nonlocal in_probe
        if not in_probe and "WHERE usuarios.email_verification_hash =" in statement:
            in_probe = True
            try:
                observed.append(tuple(connection.execute(text("SELECT current_setting('app.current_tenant',true),"
                    "current_setting('app.mfa_actor',true)")).one()))
            finally:
                in_probe = False
    event.listen(case["engine"], "before_cursor_execute", probe)
    foreign = "synthetic-caller-context"
    marker = current_tenant.set(foreign)
    try:
        assert account.confirm_email(proof, factory=case["factory"])["email_verified"] is True
        assert current_tenant.get() == foreign
    finally:
        current_tenant.reset(marker)
        event.remove(case["engine"], "before_cursor_execute", probe)
    assert observed and all(row == ("", "") for row in observed)
    with Session(case["admin"]) as db:
        actor = db.get(Usuario, case["user"])
        assert actor.session_version == case["expected"]["session_version"]
        assert actor.email_verified_contact_version == actor.notification_contact_version
        assert all(getattr(actor, field) is None for field in account.PENDING)
        assert db.scalar(select(RefreshToken.revoked).where(RefreshToken.user_id == actor.id)) is False
    assert_blank_pool(case["engine"])


def test_normal_factory_reauthentication_and_current_factor_require_real_actor_binding(normal37):
    case = normal37
    codes = current_factor(case)
    proof = primary(case)
    assert len(codes) == 7
    with Session(case["admin"]) as db:
        credential = db.get(MfaCredential, case["user"])
        assert credential.enabled_at is not None
        authorization = db.get(MfaAuthorization, mfa.opaque_digest("reauth", proof))
        assert authorization.consumed_at is None and authorization.user_id == case["user"]
        assert len(db.scalars(select(MfaRecoveryCode).where(MfaRecoveryCode.user_id == case["user"],
            MfaRecoveryCode.used_at.is_(None))).all()) == 7
    with case["factory"]() as db:
        assert db.scalars(select(MfaCredential)).all() == []
    assert_blank_pool(case["engine"])


def test_normal_factory_password_uses_current_factor_and_revokes_all_prior_authority(normal37):
    from tests.account_security37_fixtures import NEW_PASSWORD
    from web.auth import verify_password
    case = normal37
    codes = current_factor(case)
    contact = issue(case)
    proof = primary(case)
    before_sv = case["expected"]["session_version"]
    reply = account.change_password(case["expected"], case["access"], proof, NEW_PASSWORD,
        recovery_code=codes[0], factory=case["factory"])
    assert reply == {"code": "account_password_changed", "reauthenticate": True, "sessions_revoked": True}
    with Session(case["admin"]) as db:
        actor = db.get(Usuario, case["user"])
        assert actor.session_version == before_sv + 1 and verify_password(NEW_PASSWORD, actor.password_hash)
        assert all(db.scalars(select(RefreshToken.revoked).where(RefreshToken.user_id == actor.id)))
        assert db.get(MfaCredential, actor.id).enabled_at is not None
        assert len(db.scalars(select(MfaRecoveryCode).where(MfaRecoveryCode.user_id == actor.id,
            MfaRecoveryCode.used_at.is_(None))).all()) == 6
        assert db.get(MfaAuthorization, mfa.opaque_digest("reauth", proof)).consumed_at is not None
        assert all(getattr(actor, field) is None for field in account.PENDING)
    with pytest.raises(HTTPException) as failure:
        account.confirm_email(contact, factory=case["factory"])
    assert failure.value.status_code == 400
    with pytest.raises(HTTPException) as failure:
        account.change_password(case["expected"], case["access"], proof, NEW_PASSWORD,
            recovery_code=codes[0], factory=case["factory"])
    assert failure.value.status_code == 401
    assert_blank_pool(case["engine"])


def test_normal_pool1_mfa_rows_require_explicit_actor_and_session_residue_is_shadowed(normal37, peer37_database, monkeypatch):
    from web.database.mfa_policy import bind_mfa_actor
    case = normal37
    current_factor(case)
    other = seeded_case(peer37_database, monkeypatch)
    current_factor(other)
    app = case["engine"]
    for tenant in (case["user"], other["user"]):
        with tenant_scope(tenant), Session(app) as db:
            assert db.scalars(select(MfaCredential)).all() == []
    for actor in (case["user"], other["user"]):
        with Session(app) as db:
            bind_mfa_actor(db, actor)
            assert db.scalars(select(MfaCredential.user_id)).all() == [actor]
    with app.begin() as db:
        for key in ("app.current_tenant", "app.mfa_actor", "app.client_invitation_digest", "app.notification_exclude_digest"):
            db.execute(text("SELECT set_config(:key,:value,false)"), {"key": key, "value": case["user"]})
    assert_blank_pool(app)
    with Session(app) as db:
        assert db.scalars(select(MfaCredential)).all() == []


def test_predecessor_type_drift_is_rejected_before_contact_ddl_and_preserves_rows(tmp_path):
    from web.database.alembic.schema_contract_v1 import schema_signature
    from tests.integration_client_link_migrations import populate28
    with owned_database("postgresql", tmp_path) as (url, engine):
        run_migration(url, "db_bootstrap.py", "--revision", "20261020_notifications")
        populate28(engine)
        columns, rows = snapshot(engine)
        with engine.begin() as db:
            db.exec_driver_sql("ALTER TABLE usuarios ALTER COLUMN nombre TYPE TEXT")
        with engine.connect() as db:
            damaged = schema_signature(db)
        result = subprocess.run([sys.executable, "-B", "-X", "utf8", "db_bootstrap.py", "--revision", "20261020_account_security"],
            cwd=Path(__file__).resolve().parents[1], env=dict(os.environ, DATABASE_URL=url,
                METODOBASE_TEST_DATABASE_URL=""), capture_output=True)
        output = Path(os.environ["METODOBASE_TEST_EVIDENCE_DIR"])
        (output / "predecessor-drift.stdout").write_bytes(result.stdout)
        (output / "predecessor-drift.stderr").write_bytes(result.stderr)
        assert result.returncode != 0
        assert snapshot(engine, columns)[1] == rows
        with engine.connect() as db:
            assert db.scalar(text("SELECT version_num FROM alembic_version")) == "20261020_notifications"
            assert "email_verified_at" not in {row["name"] for row in inspect(db).get_columns("usuarios")}
            assert schema_signature(db) == damaged

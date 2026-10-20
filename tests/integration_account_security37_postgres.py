"""New37 restricted pool1 HTTP gate; requires ROOT's explicit exclusive lease.

No PostgreSQL operation occurs on import/collection. No historical fixture,
target or assertion is edited. Password and MFA setup use the real factories.
"""
import os
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import event, inspect, select, text
from sqlalchemy.orm import Session, sessionmaker

from tests import followup34_http as authentic
from tests import test_account_security37_http as own_http
from tests.account_security37_owned import owned_database
from tests.integration_provider_subjects import application_engine
from tests.integration_schema_migrations import run_migration
from web.database.models import RefreshToken, Usuario
from web.database.schema_control import verify_runtime_schema
from web.services import mfa_service as mfa

REVISION = "20261020_account_security"
followup_http = authentic.followup_http
account_http = authentic.followup_http


def blank_pool(engine):
    assert engine.pool.size() == 1 and engine.pool.checkedout() == 0
    with engine.connect() as db:
        assert tuple(db.execute(text("SELECT current_setting('app.current_tenant',true),"
            "current_setting('app.mfa_actor',true),current_setting('app.client_invitation_digest',true),"
            "current_setting('app.notification_exclude_digest',true)")).one()) == ("", "", "", "")
    assert engine.pool.checkedout() == 0


@pytest.fixture(scope="module")
def followup_db(tmp_path_factory):
    if not os.environ.get("METODOBASE_TEST_MIGRATOR_URL"):
        pytest.fail("Current37 integration requires an explicit own PostgreSQL lease profile")
    with owned_database("postgresql", tmp_path_factory.mktemp("account37-postgres")) as (url, admin):
        run_migration(url, "db_bootstrap.py", "--revision", REVISION)
        application = application_engine(url, admin)
        try:
            verify_runtime_schema(application)
            yield admin, application
        finally:
            application.dispose()


@pytest.fixture(autouse=True)
def released_checkout_after_each(followup_db):
    yield
    blank_pool(followup_db[1])


test_explicit_contact_request_provider_ack_public_confirmation_and_replay = own_http.test_explicit_contact_request_provider_ack_public_confirmation_and_replay
test_public_get_does_not_consume_and_contains_no_auth_bootstrap = own_http.test_public_get_does_not_consume_and_contains_no_auth_bootstrap
test_foreign_bearer_cannot_retarget_email_confirmation = own_http.test_foreign_bearer_cannot_retarget_email_confirmation
test_closed_duplicate_nonfinite_body_is_not_reflected = own_http.test_closed_duplicate_nonfinite_body_is_not_reflected
test_admission_precedes_optional_bearer_lookup_and_finite_neighbors = own_http.test_admission_precedes_optional_bearer_lookup_and_finite_neighbors
test_body_limit_and_missing_header_do_not_touch_provider = own_http.test_body_limit_and_missing_header_do_not_touch_provider
test_password_uses_real_primary_proof_current_totp_and_revokes_cookie = own_http.test_password_uses_real_primary_proof_current_totp_and_revokes_cookie


def test_actual_role_nonowner_force32_and_pool1(followup_db):
    _admin, application = followup_db
    with application.connect() as db:
        assert tuple(db.execute(text("SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole,"
            "pg_has_role(current_user,(SELECT relowner FROM pg_class WHERE oid='usuarios'::regclass),'MEMBER') "
            "FROM pg_roles WHERE rolname=current_user")).one()) == (False, False, False, False, False)
        assert db.scalar(text("SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace "
                              "AND relkind='r' AND relrowsecurity AND relforcerowsecurity")) == 32
        assert len(inspect(db).get_table_names()) == 42
    blank_pool(application)


def request_proof(case, monkeypatch):
    packets = own_http.provider(monkeypatch)
    response = case["raw"].post(own_http.PREFIX + "/email/request", json={}, headers=own_http.headers(case))
    assert response.status_code == 200 and len(packets) == 1
    return own_http.token_from_packet(packets[0])


def test_real_NOWAIT_contact_lock_denies_without_consuming_proof(account_http, monkeypatch):
    case = account_http
    token = request_proof(case, monkeypatch)
    with case["admin"].connect() as lock:
        lock.execute(text("SELECT id FROM usuarios WHERE id=:id FOR UPDATE"), {"id": case["user"]})
        response = case["raw"].post(own_http.PREFIX + "/email/confirm", json={"token": token}, headers=own_http.headers(case))
        assert response.status_code == 409 and response.json()["detail"]["code"] == "account_security_busy"
        own_http.private(response)
        assert lock.scalar(text("SELECT email_verified_at FROM usuarios WHERE id=:id"), {"id": case["user"]}) is None
    assert case["raw"].post(own_http.PREFIX + "/email/confirm", json={"token": token}, headers=own_http.headers(case)).status_code == 200
    blank_pool(case["engine"])


@pytest.mark.parametrize("confirmed", [False, True])
def test_real_PG_contact_ABA_invalidates_pending_and_confirmed_status(account_http, monkeypatch, confirmed):
    case = account_http
    token = request_proof(case, monkeypatch)
    if confirmed:
        assert case["raw"].post(own_http.PREFIX + "/email/confirm", json={"token": token}, headers=own_http.headers(case)).status_code == 200
    with Session(case["admin"]) as db:
        user = db.get(Usuario, case["user"])
        original = user.email
        user.email = uuid.uuid4().hex + "@example.invalid"
        db.commit()
        user.email = original
        db.commit()
        assert user.notification_contact_version == 2
    response = case["raw"].get(own_http.PREFIX)
    assert response.status_code == 200 and response.json()["email_verified"] is False
    assert response.json()["email_verified_at"] is None
    assert case["raw"].post(own_http.PREFIX + "/email/confirm", json={"token": token}, headers=own_http.headers(case)).status_code == 400
    blank_pool(case["engine"])


def test_public_proof_lookup_runs_with_actual_empty_PG_context(account_http, monkeypatch):
    case = account_http
    token = request_proof(case, monkeypatch)
    observed = []
    inspecting = False
    def inspect_context(connection, cursor, statement, parameters, context, many):
        nonlocal inspecting
        if not inspecting and "WHERE usuarios.email_verification_hash =" in statement:
            inspecting = True
            try:
                observed.append(connection.execute(text("SELECT current_setting('app.current_tenant',true),"
                    "current_setting('app.mfa_actor',true)")).one())
            finally:
                inspecting = False
    event.listen(case["engine"], "before_cursor_execute", inspect_context)
    try:
        response = case["raw"].post(own_http.PREFIX + "/email/confirm", json={"token": token}, headers=own_http.headers(case))
        assert response.status_code == 200
    finally:
        event.remove(case["engine"], "before_cursor_execute", inspect_context)
    assert observed and all(tuple(row) == ("", "") for row in observed)
    assert case["raw"].get("/api/auth/me").json()["id"] == case["user"]
    blank_pool(case["engine"])


def test_issue_commit_ACK_lost_never_calls_provider(account_http, monkeypatch):
    from web.database import engine as database
    case = account_http
    packets = own_http.provider(monkeypatch)
    class LostAck(Session):
        def commit(self):
            issuing = any(isinstance(user, Usuario) and inspect(user).attrs.email_verification_hash.history.has_changes() for user in self.dirty)
            super().commit()
            if issuing:
                raise RuntimeError("Synthetic37 issue ACK lost")
    monkeypatch.setattr(database, "_SessionLocal", sessionmaker(bind=case["engine"], class_=LostAck, expire_on_commit=True, autoflush=False))
    response = case["raw"].post(own_http.PREFIX + "/email/request", json={}, headers=own_http.headers(case))
    assert response.status_code == 503 and response.json()["detail"]["code"] == "account_security_unconfirmed"
    assert packets == []
    with Session(case["admin"]) as db:
        assert db.get(Usuario, case["user"]).email_verification_hash is not None
    blank_pool(case["engine"])


def test_confirmation_commit_ACK_lost_is_not_public_success(account_http, monkeypatch):
    from web.database import engine as database
    case = account_http
    token = request_proof(case, monkeypatch)
    class LostAck(Session):
        def commit(self):
            publishing = self.info.get("contact37_write", False)
            super().commit()
            if publishing:
                raise RuntimeError("Synthetic37 contact ACK lost")
    @event.listens_for(LostAck, "do_orm_execute")
    def target_write(state):
        if state.is_update and "email_verified_at" in str(state.statement):
            state.session.info["contact37_write"] = True
    monkeypatch.setattr(database, "_SessionLocal", sessionmaker(bind=case["engine"], class_=LostAck, expire_on_commit=True, autoflush=False))
    response = case["raw"].post(own_http.PREFIX + "/email/confirm", json={"token": token}, headers=own_http.headers(case))
    assert response.status_code == 503 and response.json()["detail"]["code"] == "account_security_unconfirmed"
    assert "email_verified" not in response.json() and "Synthetic37" not in response.text
    with Session(case["admin"]) as db:
        assert db.get(Usuario, case["user"]).email_verified_at is not None
    assert case["raw"].post(own_http.PREFIX + "/email/confirm", json={"token": token}, headers=own_http.headers(case)).status_code == 400
    blank_pool(case["engine"])


def test_password_commit_ACK_lost_preserves_factor_and_denies_old_access(account_http, monkeypatch):
    from tests.account_security37_fixtures import NEW_PASSWORD
    from web.auth import verify_password
    from web.database import engine as database
    from web.database.models import MfaCredential
    from web.services.mfa_crypto import decrypt, totp
    case = account_http
    clock = mfa.instant
    now = clock().replace(microsecond=0)
    with Session(case["admin"]) as db:
        row = db.get(MfaCredential, case["user"])
        counter = max(int(now.timestamp()) // 30, row.last_counter + 1)
        now = datetime.fromtimestamp(counter * 30 + 1, UTC)
        seed = decrypt(row.secret_ciphertext, mfa.configuration(), mfa._aad(row, row.generation, "active"))
    monkeypatch.setattr(mfa, "instant", lambda value=None: clock(now if value is None else value))
    proof = case["raw"].post("/api/auth/mfa/reauth", json={"password": authentic.PASSWORD}, headers=own_http.headers(case))
    assert proof.status_code == 200
    class LostAck(Session):
        def commit(self):
            publishing = any(isinstance(user, Usuario) and inspect(user).attrs.password_hash.history.has_changes() for user in self.dirty)
            super().commit()
            if publishing:
                raise RuntimeError("Synthetic37 password ACK lost")
    monkeypatch.setattr(database, "_SessionLocal", sessionmaker(bind=case["engine"], class_=LostAck, expire_on_commit=True, autoflush=False))
    response = case["raw"].post(own_http.PREFIX + "/password", headers=own_http.headers(case), json={
        "reauthentication_token": proof.json()["reauthentication_token"], "new_password": NEW_PASSWORD,
        "confirm_password": NEW_PASSWORD, "code": totp(seed, counter)})
    assert response.status_code == 503 and response.json()["detail"]["code"] == "account_security_unconfirmed"
    assert "token" not in response.json() and "sessions_revoked" not in response.json()
    assert case["raw"].get("/api/auth/me").status_code == 401
    with Session(case["admin"]) as db:
        user = db.get(Usuario, case["user"])
        assert user.session_version == 2 and verify_password(NEW_PASSWORD, user.password_hash)
        assert db.get(MfaCredential, user.id).enabled_at is not None
        assert all(db.scalars(select(RefreshToken.revoked).where(RefreshToken.user_id == user.id)))
    blank_pool(case["engine"])

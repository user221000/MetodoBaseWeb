"""Actual32 factories, password proof and optional existing MFA; no minted login."""
# ruff: noqa: F811 -- pytest fixture parameters intentionally use fixture names
import base64
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session, sessionmaker

from tests.test_personal_progress_http import (  # noqa:F401
    accepted,
    grant,
    progress_db,
    progress_http,
)

PASSWORD = "Synthetic progress password 42!"
METADATA = "/api/auth/progress-retirement/metadata"
WITHDRAW = "/api/auth/progress-retirement/withdraw"


@pytest.fixture
def retired_scope(progress_http, monkeypatch):
    from web.database.models import Usuario
    from web.services import mfa_service
    from web.settings import get_settings
    case = progress_http
    clock = [datetime.now(UTC)]
    actual = mfa_service.instant
    monkeypatch.setattr(mfa_service, "instant", lambda now=None: actual(clock[0] if now is None else now))
    monkeypatch.setattr(get_settings(), "MFA_ENCRYPTION_KEY", base64.urlsafe_b64encode(bytes(range(32))).decode())
    link = accepted(case)
    response, _ = grant(case, link)
    assert response.status_code == 200
    consent = response.json()["consent"]
    # Explicit synthetic membership transition isolates the parent barrier.
    # The unmodified SEC canary separately covers invite->accept->login lineage.
    with Session(case["admin"]) as db:
        db.get(Usuario, case["person"]).team_gym_id = case["gym"]
        db.get(Usuario, case["gym"]).activo = False
        db.commit()
    return {**case, "link": link, "consent": consent, "clock": clock}


def primary(case, **changes):
    return {"method": "password", "email": case["emails"]["person"], "password": PASSWORD, **changes}


def query(case, **changes):
    return {"primary": primary(case), "limit": 10, **changes}


def withdrawal(case, **changes):
    return {"primary": primary(case), "link_id": case["link"],
            "expected_consent_id": case["consent"]["id"], "expected_version": 1, **changes}


def enrollment(case):
    from web.database.models import Usuario
    from web.services.mfa_crypto import totp
    client = case["client_http"]
    with Session(case["admin"]) as db:
        db.get(Usuario, case["gym"]).activo = True
        db.commit()
    login = client.post("/api/auth/login", json={"email": case["emails"]["person"], "password": PASSWORD})
    assert login.status_code == 200
    headers = {"Authorization": "Bearer " + login.json()["token"]}
    reauth = client.post("/api/auth/mfa/reauth", headers=headers, json={"password": PASSWORD})
    assert reauth.status_code == 200
    started = client.post("/api/auth/mfa/enroll", headers=headers,
        json={"reauthentication_token": reauth.json()["reauthentication_token"]})
    assert started.status_code == 200
    seed = base64.b32decode(started.json()["secret"])
    done = client.post("/api/auth/mfa/enroll/confirm", headers=headers, json={
        "enrollment_id": started.json()["enrollment_id"],
        "code": totp(seed, int(case["clock"][0].timestamp()) // 30)})
    assert done.status_code == 200
    with Session(case["admin"]) as db:
        db.get(Usuario, case["gym"]).activo = False
        db.commit()
    return seed, done.json()["recovery_codes"]


def snapshot(case):
    from web.database.models import (
        Cliente,
        MfaAuthorization,
        ProgressConsent,
        RefreshToken,
        Usuario,
    )
    with Session(case["admin"]) as db:
        actor = db.get(Usuario, case["person"])
        return {"sv": actor.session_version, "role": actor.role.value, "parent": actor.team_gym_id,
                "password": actor.password_hash,
                "refresh": db.scalar(select(func.count()).select_from(RefreshToken).where(RefreshToken.user_id == actor.id)),
                "proofs": db.scalar(select(func.count()).select_from(MfaAuthorization).where(MfaAuthorization.user_id == actor.id)),
                "profiles": db.scalars(select(Cliente.id_cliente).where(Cliente.gym_id == actor.id)).all(),
                "events": [(r.id, r.event, r.version) for r in db.scalars(select(ProgressConsent).where(ProgressConsent.user_id == actor.id).order_by(ProgressConsent.version))]}


def test_password_only_retirement_succeeds_without_general_session_or_source_reads(retired_scope):
    c = retired_scope; client = c["client_http"]
    before = snapshot(c)
    assert client.get("/api/usuario/progreso/consentimientos", headers=c["headers"]["person"]).status_code == 401
    observed = []
    def read(connection, cursor, statement, parameters, context, many):
        observed.append(statement.lower())
    event.listen(c["engine"], "before_cursor_execute", read)
    try:
        metadata = client.post(METADATA, json=query(c))
        assert metadata.status_code == 200
        own = metadata.json()["items"][0]
        assert own["link_id"] == c["link"] and own["consent"]["id"] == c["consent"]["id"]
        assert "source_profile_id" not in own["consent"]
        result = client.post(WITHDRAW, json=withdrawal(c))
    finally:
        event.remove(c["engine"], "before_cursor_execute", read)
    assert result.status_code == 200 and result.json()["consent"]["event"] == "withdraw"
    assert all(" from clientes " not in s and " from planes_generados " not in s for s in observed)
    after = snapshot(c)
    assert {k: v for k, v in after.items() if k != "events"} == {k: v for k, v in before.items() if k != "events"}
    assert [r[1:] for r in after["events"]] == [("grant", 1), ("withdraw", 2)]
    assert set(result.json()) == {"scope", "link_id", "consent", "capabilities", "effective"}
    assert client.post(WITHDRAW, json=withdrawal(c)).status_code == 409
    assert client.get("/api/usuario/progreso/consentimientos", headers=c["headers"]["person"]).status_code == 401


def test_active_factor_requires_new_otp_or_unused_recovery_for_each_operation(retired_scope):
    from web.services.mfa_crypto import totp
    c = retired_scope; client = c["client_http"]
    seed, codes = enrollment(c)
    assert client.post(METADATA, json=query(c)).status_code == 401
    c["clock"][0] += timedelta(seconds=30)
    factor = {"code": totp(seed, int(c["clock"][0].timestamp()) // 30)}
    assert client.post(METADATA, json=query(c, factor=factor)).status_code == 200
    assert client.post(WITHDRAW, json=withdrawal(c, factor=factor)).status_code == 401
    done = client.post(WITHDRAW, json=withdrawal(c, factor={"recovery_code": codes[0]}))
    assert done.status_code == 200
    assert client.post(METADATA, json=query(c, factor={"recovery_code": codes[0]})).status_code == 401
    assert client.post(METADATA, json=query(c, factor={"recovery_code": codes[1]})).status_code == 200


@pytest.mark.parametrize("mutation", ["inactive", "deleted", "invited", "empty_invitation", "negative_sv"])
def test_actor_eligibility_ignores_only_parent_not_account_state(retired_scope, mutation):
    from web.database.models import Usuario
    c = retired_scope
    with Session(c["admin"]) as db:
        actor = db.get(Usuario, c["person"])
        if mutation == "inactive": actor.activo = False
        if mutation == "deleted": actor.deleted_at = c["clock"][0]
        if mutation == "invited": actor.invitation_token = uuid.uuid4().hex + uuid.uuid4().hex
        if mutation == "empty_invitation": actor.invitation_token = ""
        if mutation == "negative_sv": actor.session_version = -1
        db.commit()
    response = c["client_http"].post(METADATA, json=query(c))
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "progress_retirement_verification_failed"
    # The migrated module DB persists across factories. Release the unique
    # empty-string witness; this fixture state is not an invitation workflow.
    if mutation == "empty_invitation":
        with Session(c["admin"]) as db:
            db.get(Usuario, c["person"]).invitation_token = None
            db.commit()


def test_wrong_password_unknown_account_and_foreign_cas_never_authorize(retired_scope):
    c = retired_scope; client = c["client_http"]
    wrong = client.post(METADATA, json=query(c, primary=primary(c, password="Not the account password")))
    unknown = client.post(METADATA, json=query(c, primary=primary(c, email=uuid.uuid4().hex + "@example.invalid")))
    assert wrong.status_code == unknown.status_code == 401 and wrong.json() == unknown.json()
    foreign = {"method": "password", "email": c["emails"]["other"], "password": PASSWORD}
    assert client.post(WITHDRAW, json=withdrawal(c, primary=foreign)).status_code == 404
    assert client.post(WITHDRAW, json=withdrawal(c, expected_consent_id=str(uuid.uuid4()))).status_code == 409
    assert client.post(WITHDRAW, json=withdrawal(c, expected_version=True)).status_code == 422


def test_commit_ack_loss_does_not_return_success_or_refund_factor(retired_scope, monkeypatch, caplog):
    from web.database import engine as database
    from web.database.models import ProgressConsent
    c = retired_scope; _, codes = enrollment(c)
    class LostAck(Session):
        def commit(self):
            publication = any(isinstance(row, ProgressConsent) and row.event == "withdraw" for row in self.new)
            # flush() already made the event persistent, so use audited outcome.
            publication = publication or any(getattr(row, "event_type", None) == "progress_retirement_withdraw" for row in self.new)
            super().commit()
            if publication: raise RuntimeError("PRIVATE_RETIREMENT_ACK_PARAMETERS")
    monkeypatch.setattr(database, "_SessionLocal", sessionmaker(bind=c["engine"], class_=LostAck, expire_on_commit=True))
    response = c["client_http"].post(WITHDRAW, json=withdrawal(c, factor={"recovery_code": codes[0]}))
    assert response.status_code == 503 and response.json()["detail"]["code"] == "progress_retirement_unconfirmed"
    assert [e[1] for e in snapshot(c)["events"]] == ["grant", "withdraw"]
    assert c["client_http"].post(METADATA, json=query(c, factor={"recovery_code": codes[0]})).status_code == 401
    assert "PRIVATE_RETIREMENT_ACK_PARAMETERS" not in response.text + caplog.text
    reread = c["client_http"].post(METADATA, json=query(c, factor={"recovery_code": codes[1]}))
    assert reread.status_code == 200 and reread.json()["items"][0]["consent"]["event"] == "withdraw"


def test_cas_rollback_preserves_factor_but_cannot_reset_durable_admission(retired_scope):
    from web.database.models import AuthAuditLog, MfaRecoveryCode
    from web.progress_retirement_schemas import Withdrawal
    from web.services import progress_retirement as service
    c = retired_scope; _, codes = enrollment(c)
    # Service boundary intentionally bypasses only HTTP admission to prove the
    # independent durable actor budget, not identity/factor/consent authority.
    for _ in range(10):
        with Session(c["engine"]) as db:
            with pytest.raises(Exception) as failed:
                service.perform(db, Withdrawal.model_validate(withdrawal(c, expected_version=2,
                    factor={"recovery_code": codes[0]})), operation="withdraw", now=c["clock"][0])
            assert getattr(failed.value, "status_code", None) == 409
    with Session(c["engine"]) as db:
        with pytest.raises(Exception) as limited:
            service.perform(db, Withdrawal.model_validate(withdrawal(c, factor={"recovery_code": codes[0]})), operation="withdraw", now=c["clock"][0])
        assert getattr(limited.value, "status_code", None) == 429
    with Session(c["admin"]) as db:
        assert db.scalar(select(func.count()).select_from(AuthAuditLog).where(AuthAuditLog.user_id == c["person"], AuthAuditLog.event_type == service.ATTEMPT_EVENT)) == 10
        assert all(r.used_at is None for r in db.scalars(select(MfaRecoveryCode).where(MfaRecoveryCode.user_id == c["person"])))


def test_google_and_missing_factor_key_are_closed_without_email_fallback(retired_scope, monkeypatch):
    from web.settings import get_settings
    c = retired_scope; client = c["client_http"]
    before = snapshot(c)
    response = client.post(METADATA, json={"primary": {"method": "google", "google_credential": "synthetic-unverified"}})
    assert response.status_code == 503 and response.json()["detail"]["code"] == "progress_retirement_primary_unavailable"
    assert snapshot(c) == before
    _, codes = enrollment(c)
    monkeypatch.setattr(get_settings(), "MFA_ENCRYPTION_KEY", "")
    result = client.post(METADATA, json=query(c, factor={"recovery_code": codes[0]}))
    assert result.status_code == 503


@pytest.mark.parametrize("path", [METADATA, WITHDRAW, METADATA + "/", WITHDRAW + "/"])
def test_private_headers_apply_to_methods_redirects_and_validation(progress_http, path):
    client = progress_http["client_http"]
    response = client.get(path, follow_redirects=False)
    assert response.status_code in {307, 405}
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "default-src 'none'" in response.headers["content-security-policy"]

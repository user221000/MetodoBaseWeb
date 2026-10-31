"""Google/email orchestration on current RAM SQLite and a Redis protocol double.

No provider is contacted. The Redis double models one atomic consume call;
these cases do not claim execution of Redis's Lua engine or deployment.
"""
import asyncio
import base64
from datetime import datetime, timezone
import json
from types import SimpleNamespace
import uuid

from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request


@pytest.fixture(scope="module")
def database_schema():
    """This module owns a separate current-schema RAM database per case."""
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    """No shared suite database is used; otp_case disposes its private engine."""
    yield


class AtomicMemory:
    """Deterministic Redis wire model with a monotonic clock and atomic eval."""
    def __init__(self):
        self.rows = {}
        self.now = 0
        self.fail_set = False
        self.fail_eval = False
        self.eval_calls = 0
        self.lock = asyncio.Lock()

    async def set(self, key, value, *, ex=None, nx=False):
        if self.fail_set:
            raise ConnectionError("synthetic transport detail must remain private")
        if nx and key in self.rows:
            return False
        self.rows[key] = (value, self.now + ex * 1000)
        return True

    async def delete(self, key):
        return int(self.rows.pop(key, None) is not None)

    async def eval(self, script, keys, key, digest, maximum):
        assert keys == 1
        assert "PTTL" in script and "DEL" in script
        self.eval_calls += 1
        if self.fail_eval:
            raise ConnectionError("synthetic transport detail must remain private")
        async with self.lock:
            row = self.rows.get(key)
            if row is None:
                return [0]
            raw, expiry = row
            if expiry <= self.now:
                del self.rows[key]
                return [0]
            item = json.loads(raw)
            if item["code_digest"] != digest:
                item["attempts"] += 1
                if item["attempts"] >= maximum:
                    del self.rows[key]
                else:
                    self.rows[key] = (json.dumps(item), expiry)
                return [0]
            del self.rows[key]
            return [1, item["payload"], item["signature"]]


@pytest.fixture
def otp_case(monkeypatch):
    from web.database import engine as database
    from web.database.models import Base
    from web.database.tenant_context import current_tenant
    from web.services import email_service, google_email_login as service
    from web.settings import get_settings

    engine = create_engine("sqlite://", poolclass=StaticPool,
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    monkeypatch.setattr(database, "_engine", engine)
    monkeypatch.setattr(database, "_SessionLocal", sessions)
    settings = get_settings()
    monkeypatch.setattr(settings, "REDIS_URL", "redis://127.0.0.1:56379/15")
    monkeypatch.setattr(settings, "RESEND_API_KEY", "synthetic-not-a-provider-key")
    monkeypatch.setattr(settings, "RESEND_FROM_EMAIL", "MetodoBase <no-reply@example.invalid>")
    monkeypatch.setattr(settings, "MFA_ENCRYPTION_KEY", base64.urlsafe_b64encode(b"Q" * 32).decode())
    cache, mail, limits = AtomicMemory(), [], []
    real_limit = service._limit

    async def redis():
        return cache

    async def limit(request, purpose, email=None):
        limits.append((purpose, email))

    def send(email, code):
        mail.append((email, code))
        return True

    monkeypatch.setattr(service, "_redis", redis)
    monkeypatch.setattr(service, "_limit", limit)
    monkeypatch.setattr(email_service, "send_google_login_code", send)
    token = current_tenant.set("")
    info = {"iss": "https://accounts.google.com", "sub": "synthetic-subject-1",
            "email": "google-owner@example.invalid", "given_name": "Synthetic", "family_name": "Owner"}
    request = Request({"type": "http", "method": "POST", "path": "/api/auth/google",
                       "headers": [], "client": ("192.0.2.37", 50000)})
    case = SimpleNamespace(service=service, sessions=sessions, cache=cache, info=info,
                           request=request, mail=mail, limits=limits, settings=settings, real_limit=real_limit)
    try:
        yield case
    finally:
        current_tenant.reset(token)
        engine.dispose()


def seed(case, *, binding=None, revoked=False, mfa=False):
    from web.database.models import AuthExternalIdentity, MfaCredential, Usuario, UserRole
    user_id = str(uuid.uuid4())
    with case.sessions() as db:
        db.add(Usuario(id=user_id, email=case.info["email"], password_hash="synthetic-unused-hash",
                       nombre="Existing", apellido="Owner", tipo="usuario", role=UserRole.VIEWER,
                       activo=True, session_version=3))
        db.flush()
        if binding is not None:
            db.add(AuthExternalIdentity(user_id=user_id, issuer=case.info["iss"], subject=binding,
                                       created_at=datetime.now(timezone.utc), version=1,
                                       revoked_at=datetime.now(timezone.utc) if revoked else None))
        if mfa:
            db.add(MfaCredential(user_id=user_id, factor_id=uuid.uuid4().hex, generation=1,
                                 secret_ciphertext="synthetic-encrypted-factor", enabled_at=datetime.now(timezone.utc)))
        db.commit()
    return user_id


def counts(case):
    from web.database.models import AuthExternalIdentity, RefreshToken, Usuario
    with case.sessions() as db:
        return tuple(db.scalar(select(func.count()).select_from(model))
                     for model in (Usuario, AuthExternalIdentity, RefreshToken))


async def start(case, tipo="usuario"):
    return await case.service.begin(dict(case.info), tipo, case.request)


async def verify(case, challenge, code=None):
    return await case.service.verify(challenge, case.mail[-1][1] if code is None else code, case.request)


def error_code(error):
    return error.value.detail["code"]


@pytest.mark.asyncio
@pytest.mark.parametrize("existing", [False, True])
async def test_start_sends_only_an_email_challenge_without_account_binding_or_session(otp_case, existing):
    c = otp_case
    if existing:
        seed(c, binding=c.info["sub"])
    before = counts(c)
    result = await start(c)
    assert set(result) == {"email_verification_required", "challenge", "expires_at", "masked_email"}
    assert result["email_verification_required"] is True
    assert c.service.CHALLENGE_PATTERN.fullmatch(result["challenge"])
    assert counts(c) == before
    assert len(c.mail) == 1 and c.mail[0][0] == c.info["email"]
    assert c.service.CODE_PATTERN.fullmatch(c.mail[0][1])
    assert c.info["email"] not in json.dumps(result)
    key, (raw, expiry) = next(iter(c.cache.rows.items()))
    assert result["challenge"] not in key and c.mail[0][1] not in raw
    assert expiry == c.service.TTL_SECONDS * 1000


@pytest.mark.asyncio
async def test_legacy_email_ownership_authenticates_without_backfilling_or_merging_subject(otp_case):
    c = otp_case
    user_id = seed(c)
    result = await start(c, "gym")
    assert counts(c) == (1, 0, 0)
    identity = await verify(c, result["challenge"])
    assert identity["id"] == user_id and identity["tipo"] == "usuario"
    assert identity["role"] == "viewer"
    assert counts(c) == (1, 0, 0)
    with c.sessions() as db:
        from web.database.models import Usuario
        user = db.get(Usuario, user_id)
        assert user.nombre == "Existing" and user.password_hash == "synthetic-unused-hash"
        assert user.session_version == 3


@pytest.mark.asyncio
@pytest.mark.parametrize("tipo,role", [("usuario", "viewer"), ("gym", "owner")])
async def test_new_account_is_created_only_after_correct_email_code(otp_case, tipo, role):
    c = otp_case
    result = await start(c, tipo)
    assert counts(c) == (0, 0, 0)
    identity = await verify(c, result["challenge"])
    assert identity["tipo"] == tipo and identity["role"] == role
    assert counts(c) == (1, 1, 0)
    with pytest.raises(HTTPException) as rejected:
        await verify(c, result["challenge"])
    assert error_code(rejected) == "google_email_code_invalid"
    assert counts(c) == (1, 1, 0)


@pytest.mark.asyncio
async def test_wrong_codes_preserve_expiry_and_five_failures_invalidate_the_challenge(otp_case):
    c = otp_case
    seed(c)
    result = await start(c)
    key = next(iter(c.cache.rows))
    expiry = c.cache.rows[key][1]
    wrong = "000000" if c.mail[-1][1] != "000000" else "000001"
    for attempt in range(c.service.MAX_ATTEMPTS):
        c.cache.now += 1000
        with pytest.raises(HTTPException) as rejected:
            await verify(c, result["challenge"], wrong)
        assert error_code(rejected) == "google_email_code_invalid"
        if attempt < c.service.MAX_ATTEMPTS - 1:
            assert c.cache.rows[key][1] == expiry
    assert not c.cache.rows
    with pytest.raises(HTTPException) as rejected:
        await verify(c, result["challenge"])
    assert error_code(rejected) == "google_email_code_invalid"
    assert counts(c) == (1, 0, 0)


@pytest.mark.asyncio
async def test_expired_code_never_creates_an_account(otp_case):
    c = otp_case
    result = await start(c)
    c.cache.now = c.service.TTL_SECONDS * 1000
    with pytest.raises(HTTPException) as rejected:
        await verify(c, result["challenge"])
    assert error_code(rejected) == "google_email_code_invalid"
    assert counts(c) == (0, 0, 0)


@pytest.mark.asyncio
async def test_only_one_concurrent_verification_can_consume_a_code(otp_case):
    c = otp_case
    seed(c)
    result = await start(c)
    replies = await asyncio.gather(*(verify(c, result["challenge"]) for _ in range(2)), return_exceptions=True)
    assert sum(isinstance(reply, dict) for reply in replies) == 1
    assert sum(isinstance(reply, HTTPException) and reply.status_code == 400 for reply in replies) == 1
    assert counts(c) == (1, 0, 0)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["false", "exception"])
async def test_unconfirmed_delivery_discards_code_and_does_not_change_accounts(otp_case, monkeypatch, mode, caplog):
    from web.services import email_service
    c = otp_case

    def send(email, code):
        if mode == "exception":
            raise RuntimeError("private synthetic mailbox/code")
        return False

    monkeypatch.setattr(email_service, "send_google_login_code", send)
    with pytest.raises(HTTPException) as rejected:
        await start(c)
    assert error_code(rejected) == "google_email_delivery_unconfirmed"
    assert not c.cache.rows and counts(c) == (0, 0, 0)
    assert "private synthetic" not in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["start", "verify"])
async def test_redis_uncertainty_fails_closed_without_authentication(otp_case, stage, caplog):
    c = otp_case
    if stage == "start":
        c.cache.fail_set = True
        operation = start(c)
    else:
        result = await start(c)
        c.cache.fail_eval = True
        operation = verify(c, result["challenge"])
    with pytest.raises(HTTPException) as rejected:
        await operation
    assert rejected.value.status_code == 503
    assert counts(c) == (0, 0, 0)
    assert "synthetic transport detail" not in caplog.text
    if stage == "start":
        assert not c.mail


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", ["REDIS_URL", "RESEND_API_KEY", "RESEND_FROM_EMAIL"])
async def test_incomplete_configuration_is_not_reported_as_sent(otp_case, monkeypatch, missing):
    c = otp_case
    monkeypatch.setattr(c.settings, missing, "")
    with pytest.raises(HTTPException) as rejected:
        await start(c)
    assert error_code(rejected) == "google_email_unavailable"
    assert not c.mail and not c.cache.rows and counts(c) == (0, 0, 0)


@pytest.mark.asyncio
@pytest.mark.parametrize("changed", ["session_version", "email", "activo", "notification_contact_version"])
async def test_changed_legacy_authority_or_contact_cannot_use_an_old_email_proof(otp_case, changed):
    from web.database.models import Usuario
    c = otp_case
    user_id = seed(c)
    result = await start(c)
    values = {"session_version": 4, "email": "changed@example.invalid", "activo": False,
              "notification_contact_version": 1}
    with c.sessions() as db:
        setattr(db.get(Usuario, user_id), changed, values[changed])
        db.commit()
    with pytest.raises(HTTPException):
        await verify(c, result["challenge"])
    assert counts(c) == (1, 0, 0) and not c.cache.rows


@pytest.mark.asyncio
@pytest.mark.parametrize("binding", ["same", "different"])
async def test_revoked_or_other_subject_binding_cannot_be_adopted_through_email(otp_case, binding):
    c = otp_case
    seed(c, binding=c.info["sub"] if binding == "same" else "different-subject", revoked=True)
    with pytest.raises(HTTPException) as rejected:
        await start(c)
    assert error_code(rejected) == "google_link_required"
    assert not c.mail and counts(c) == (1, 1, 0)


@pytest.mark.asyncio
async def test_binding_revoked_after_send_cannot_complete_the_old_proof(otp_case):
    from web.database.models import AuthExternalIdentity
    c = otp_case
    seed(c, binding=c.info["sub"])
    result = await start(c)
    with c.sessions() as db:
        db.scalar(select(AuthExternalIdentity)).revoked_at = datetime.now(timezone.utc)
        db.commit()
    with pytest.raises(HTTPException) as rejected:
        await verify(c, result["challenge"])
    assert error_code(rejected) == "google_email_identity_changed"
    assert counts(c) == (1, 1, 0)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["new-subject-occupied", "legacy-binding-added", "bound-version-changed"])
async def test_binding_lifecycle_changes_cannot_transfer_a_sent_proof(otp_case, mode):
    from web.database.models import AuthExternalIdentity, Usuario
    c = otp_case
    if mode == "legacy-binding-added":
        user_id = seed(c)
    elif mode == "bound-version-changed":
        seed(c, binding=c.info["sub"])
    result = await start(c)
    with c.sessions() as db:
        if mode == "legacy-binding-added":
            db.add(AuthExternalIdentity(user_id=user_id, issuer=c.info["iss"], subject="later-subject",
                                       created_at=datetime.now(timezone.utc), version=1))
        elif mode == "bound-version-changed":
            db.scalar(select(AuthExternalIdentity)).version = 2
        else:
            user_id = str(uuid.uuid4())
            db.add(Usuario(id=user_id, email="different-owner@example.invalid", password_hash="unused",
                           nombre="Different", tipo="usuario", role="viewer", activo=True, session_version=0))
            db.flush()
            db.add(AuthExternalIdentity(user_id=user_id, issuer=c.info["iss"], subject=c.info["sub"],
                                       created_at=datetime.now(timezone.utc), version=1))
        db.commit()
    with pytest.raises(HTTPException) as rejected:
        await verify(c, result["challenge"])
    assert error_code(rejected) == "google_email_identity_changed"
    assert counts(c) == (1, 1, 0)


@pytest.mark.asyncio
async def test_correct_code_remains_usable_after_four_wrong_attempts(otp_case):
    c = otp_case
    user_id = seed(c)
    result = await start(c)
    wrong = "000000" if c.mail[-1][1] != "000000" else "000001"
    for _ in range(c.service.MAX_ATTEMPTS - 1):
        with pytest.raises(HTTPException):
            await verify(c, result["challenge"], wrong)
    assert (await verify(c, result["challenge"]))["id"] == user_id
    assert not c.cache.rows and counts(c) == (1, 0, 0)


@pytest.mark.asyncio
@pytest.mark.parametrize("challenge,code", [("x" * 42, "123456"), ("x" * 44, "123456"),
                                          ("x" * 43, "12345"), ("x" * 43, "1234567"),
                                          ("x" * 43, "１２３４５６"), ("x" * 43, 123456)])
async def test_malformed_proofs_never_reach_the_consume_operation(otp_case, challenge, code):
    c = otp_case
    with pytest.raises(HTTPException) as rejected:
        await c.service.verify(challenge, code, c.request)
    assert error_code(rejected) == "google_email_code_invalid"
    assert c.cache.eval_calls == 0 and not c.mail and counts(c) == (0, 0, 0)


@pytest.mark.asyncio
async def test_registration_appearing_after_send_is_not_adopted(otp_case):
    c = otp_case
    result = await start(c)
    seed(c)
    with pytest.raises(HTTPException) as rejected:
        await verify(c, result["challenge"])
    assert error_code(rejected) == "google_email_identity_changed"
    assert counts(c) == (1, 0, 0)


@pytest.mark.asyncio
async def test_tampered_snapshot_is_consumed_but_never_resolved(otp_case):
    c = otp_case
    result = await start(c)
    key = next(iter(c.cache.rows))
    raw, expiry = c.cache.rows[key]
    item = json.loads(raw)
    state = json.loads(item["payload"])
    state["tipo"] = "gym"
    item["payload"] = json.dumps(state)
    c.cache.rows[key] = (json.dumps(item), expiry)
    with pytest.raises(HTTPException) as rejected:
        await verify(c, result["challenge"])
    assert error_code(rejected) == "google_email_unconfirmed"
    assert counts(c) == (0, 0, 0) and not c.cache.rows


@pytest.mark.asyncio
async def test_authenticated_snapshots_cannot_be_transplanted_between_email_challenges(otp_case):
    c = otp_case
    seed(c)
    first = await start(c)
    first_code = c.mail[-1][1]
    first_key = c.service._key(first["challenge"])
    c.info = {**c.info, "sub": "other-subject", "email": "other-owner@example.invalid"}
    seed(c)
    second = await start(c)
    second_key = c.service._key(second["challenge"])
    first_raw, expiry = c.cache.rows[first_key]
    first_item = json.loads(first_raw)
    second_item = json.loads(c.cache.rows[second_key][0])
    first_item.update(payload=second_item["payload"], signature=second_item["signature"])
    c.cache.rows[first_key] = (json.dumps(first_item), expiry)
    with pytest.raises(HTTPException) as rejected:
        await verify(c, first["challenge"], first_code)
    assert error_code(rejected) == "google_email_unconfirmed"
    assert counts(c) == (2, 0, 0)


@pytest.mark.asyncio
async def test_email_proof_preserves_a_preexisting_personal_mfa_requirement(otp_case):
    from web.database.models import MfaAuthorization, MfaCredential
    from web.routes.auth import _primary_result
    c = otp_case
    user_id = seed(c, mfa=True)
    result = await start(c)
    identity = await verify(c, result["challenge"])
    response = _primary_result(identity, remember=True, method="google")
    body = json.loads(response.body)
    assert response.status_code == 202 and body["mfa_required"] is True
    assert "token" not in body and "refresh_token" not in body
    assert counts(c) == (1, 0, 0)
    with c.sessions() as db:
        factor = db.get(MfaCredential, user_id)
        assert factor.enabled_at is not None and factor.generation == 1
        proof = db.scalar(select(MfaAuthorization))
        assert proof.primary_method == "google" and proof.consumed_at is None


@pytest.mark.asyncio
async def test_send_budget_uses_opaque_email_and_ip_keys_and_never_falls_back(otp_case, monkeypatch):
    from web import rate_limiter_redis
    c = otp_case
    seen = []

    async def denied(key, limit, window, *, use_redis, sensitive):
        seen.append((key, limit, window, use_redis, sensitive))
        return not key.split(":")[-2] == "email", {"retry_after": 42}, "redis"

    monkeypatch.setattr(rate_limiter_redis, "check_rate_limit", denied)
    with pytest.raises(HTTPException) as rejected:
        await c.real_limit(c.request, "send", c.info["email"])
    assert error_code(rejected) == "google_email_throttled" and rejected.value.headers["Retry-After"] == "42"
    assert len(seen) == 2 and all(row[3:] == (True, True) for row in seen)
    assert all(c.info["email"] not in row[0] and "192.0.2.37" not in row[0] for row in seen)
    assert not c.mail and counts(c) == (0, 0, 0)

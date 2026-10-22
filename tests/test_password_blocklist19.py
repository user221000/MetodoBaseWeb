"""Offline B19 corpus and real current37 password-setting HTTP contracts."""
import hashlib
import json
import time
import uuid
from contextlib import contextmanager
from datetime import UTC, timedelta
from itertools import pairwise
from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests import account_security37_http
from tests.followup34_http import PASSWORD
from tests.test_account_security37_http import headers
from tests.test_password_blocklist19_canary import common_candidate

account37_engine = account_security37_http.account37_engine
followup_db = account_security37_http.followup_db
account_http = account_security37_http.account_http
STRONG = "Synthetic B19 complete passphrase 926!"


@pytest.fixture(autouse=True)
def no_password_values_in_logs(caplog):
    yield
    assert common_candidate() not in caplog.text and STRONG not in caplog.text


@contextmanager
def policy_fault(monkeypatch, tmp_path, kind):
    from web import password_blocklist as blocklist
    with monkeypatch.context() as patch:
        if kind != "common":
            path = tmp_path / "unavailable-corpus.bin"
            if kind == "tampered":
                raw = bytearray(blocklist._CORPUS_PATH.read_bytes())
                raw[0] ^= 1
                path.write_bytes(raw)
            patch.setattr(blocklist, "_CORPUS_PATH", path)
        yield common_candidate() if kind == "common" else STRONG


def assert_private_rejection(response, candidate):
    assert response.status_code in {400, 422}
    assert candidate not in response.text
    assert hashlib.sha256(candidate.encode()).hexdigest() not in response.text
    assert "traceback" not in response.text.lower()
    assert not any("mb_refresh" in value for value in response.headers.get_list("set-cookie"))


def state(case, identity):
    from web.database.models import (
        MfaAuthorization,
        MfaCredential,
        RefreshToken,
        Usuario,
    )
    with Session(case["admin"]) as db:
        user = db.get(Usuario, identity)
        actor = (user.password_hash, user.session_version, user.activo, user.role, user.tipo,
                 user.team_gym_id, user.invitation_token, user.password_reset_hash,
                 user.password_reset_session_version, user.password_reset_expires_at)
        factor = db.get(MfaCredential, identity)
        factor_state = None if factor is None else (factor.generation, factor.last_counter)
        proofs = tuple(db.execute(select(MfaAuthorization.token_hash, MfaAuthorization.consumed_at,
            MfaAuthorization.attempts).where(MfaAuthorization.user_id == identity)
            .order_by(MfaAuthorization.token_hash)).all())
        refresh = tuple(db.execute(select(RefreshToken.jti, RefreshToken.revoked)
            .where(RefreshToken.user_id == identity).order_by(RefreshToken.jti)).all())
        return actor, factor_state, proofs, refresh


def wait_mail(case):
    dispatcher = case["raw"].app.state.recovery_dispatcher
    deadline = time.monotonic() + 8
    while dispatcher.pending and time.monotonic() < deadline:
        time.sleep(.01)
    assert dispatcher.pending == 0


def test_real_artifact_manifest_integrity_sorting_and_license():
    from web import password_blocklist as blocklist
    directory = blocklist._CORPUS_PATH.parent
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    raw = blocklist._CORPUS_PATH.read_bytes()
    assert len(raw) == manifest["payload_bytes"] == blocklist._CORPUS_BYTES
    assert hashlib.sha256(raw).hexdigest() == manifest["payload_sha256"] == blocklist._CORPUS_SHA256
    entries = [raw[offset:offset + 32] for offset in range(0, len(raw), 32)]
    assert len(entries) == manifest["unique_digests"] == 99999
    assert all(len(value) == 32 for value in entries)
    assert all(before < after for before, after in pairwise(entries))
    assert hashlib.sha256((directory / "LICENSE.SecLists").read_bytes()).hexdigest() == manifest["license_sha256"]
    assert manifest["source_commit"] == "c205c36a445bff37f8e58a9ec829105cd4975c58"


@pytest.mark.parametrize("value", [STRONG, chr(49) * 12 + "-B19-unique", "é" * 36, "a\u0301" * 12, " " + STRONG + " "])
def test_full_password_only_and_unicode_are_preserved(value):
    from web.account_values import validate_new_password
    assert validate_new_password(value) == value


@pytest.mark.parametrize("value", [None, 42, "x" * 11, "é" * 37, "z" * 73, "x" * 12 + "\ud800"])
def test_existing_type_length_and_utf8_bounds_remain_closed(value):
    from web.account_values import validate_new_password
    with pytest.raises(ValueError):
        validate_new_password(value)


@pytest.mark.parametrize("kind", ["missing", "tampered", "oversized", "truncated"])
def test_artifact_failure_is_closed_even_after_success(monkeypatch, tmp_path, kind):
    from web import password_blocklist as blocklist
    from web.account_values import validate_new_password
    assert validate_new_password(STRONG) == STRONG
    path = tmp_path / "candidate-secret-not-a-real-file.bin"
    if kind != "missing":
        raw = blocklist._CORPUS_PATH.read_bytes()
        if kind == "tampered":
            raw = bytes([raw[0] ^ 1]) + raw[1:]
        elif kind == "oversized":
            raw += b"x"
        else:
            raw = raw[:-1]
        path.write_bytes(raw)
    monkeypatch.setattr(blocklist, "_CORPUS_PATH", path)
    with pytest.raises(ValueError) as error:
        validate_new_password(STRONG)
    assert STRONG not in str(error.value) and str(path) not in str(error.value)


@pytest.mark.parametrize("kind", ["common", "missing", "tampered"])
def test_registration_policy_failure_never_persists_then_strong_succeeds(account_http, monkeypatch, tmp_path, kind):
    from web import auth
    from web.database.models import Usuario
    case = account_http
    email = uuid.uuid4().hex + "@example.invalid"
    payload = {"email": email, "password": STRONG, "nombre": "Synthetic B19", "tipo": "usuario"}
    with policy_fault(monkeypatch, tmp_path, kind) as candidate:
        response = case["raw"].post("/api/auth/registro", json={**payload, "password": candidate})
        assert_private_rejection(response, candidate)
    with Session(case["admin"]) as db:
        assert db.scalar(select(Usuario.id).where(Usuario.email == email)) is None
    assert case["raw"].post("/api/auth/registro", json=payload).status_code == 200
    with Session(case["admin"]) as db:
        user = db.scalar(select(Usuario).where(Usuario.email == email))
        assert user is not None and auth.verify_password(STRONG, user.password_hash)


@pytest.mark.parametrize("kind", ["common", "missing", "tampered"])
@pytest.mark.parametrize("account_http", ["web.main_web"], indirect=True)
def test_invitation_policy_failure_preserves_same_token_then_strong_succeeds(account_http, monkeypatch, tmp_path, kind):
    from datetime import datetime

    from web import auth
    from web.database.models import Subscription, Usuario
    from web.services import email_service
    case = account_http
    monkeypatch.setattr(email_service, "_send", lambda *args, **kwargs: False)
    with Session(case["admin"]) as db:
        subscription = db.scalar(select(Subscription).where(Subscription.gym_id == case["user"]))
        if subscription is None:
            subscription = Subscription(gym_id=case["user"])
            db.add(subscription)
        subscription.plan = "clinica"
        subscription.status = "active"
        subscription.current_period_end = datetime.now(UTC) + timedelta(days=30)
        db.commit()
    invitation = case["client"].post("/api/gym/team/invite", json={
        "email": uuid.uuid4().hex + "@example.invalid", "nombre": "Synthetic B19", "apellido": "", "role": "nutriologo"})
    assert invitation.status_code == 200
    body = invitation.json()
    before = state(case, body["member_id"])
    with policy_fault(monkeypatch, tmp_path, kind) as candidate:
        response = case["raw"].post("/api/auth/accept-invite", json={"token": body["invitation_token"], "password": candidate})
        assert_private_rejection(response, candidate)
    assert state(case, body["member_id"]) == before
    accepted = case["raw"].post("/api/auth/accept-invite", json={"token": body["invitation_token"], "password": STRONG})
    assert accepted.status_code == 200
    with Session(case["admin"]) as db:
        user = db.get(Usuario, body["member_id"])
        assert user.activo and user.invitation_token is None
        assert auth.verify_password(STRONG, user.password_hash)


@pytest.mark.parametrize("account_http", ["api.app"], indirect=True)
def test_api_factory_preserves_existing_absence_of_team_routes(account_http):
    case = account_http
    assert case["raw"].post("/api/gym/team/invite", json={}).status_code == 404
    assert case["raw"].post("/api/auth/accept-invite", json={}).status_code == 404


def test_password_validation_attempts_no_outbound_socket(monkeypatch):
    import socket

    from web.account_values import validate_new_password
    calls = []
    def forbidden(*args, **kwargs):
        calls.append(True)
        raise AssertionError("Password blocklist attempted outbound connection")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    assert validate_new_password(STRONG) == STRONG
    with pytest.raises(ValueError):
        validate_new_password(common_candidate())
    assert calls == []


@pytest.mark.parametrize("account_http", ["web.main_web"], indirect=True)
@pytest.mark.parametrize("path", ["/api/auth/accept-invite", "/api/auth/accept-invite/"])
@pytest.mark.parametrize("shape", ["password", "nested", "extra"])
def test_saas_invitation_validation_never_echoes_candidate_or_context(account_http, path, shape):
    marker = "Synthetic-B19-private-validation-context"
    payload = {"token": "A" * 43, "password": common_candidate()}
    if shape == "nested":
        payload["password"] = {marker: [STRONG]}
    elif shape == "extra":
        payload[marker] = STRONG
    response = account_http["raw"].post(path, json=payload)
    assert_private_rejection(response, common_candidate())
    assert marker not in response.text and STRONG not in response.text
    assert "A" * 43 not in response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert set(response.json()["detail"]) == {"code", "message", "fields"}
    assert set(response.json()["detail"]["fields"]) <= {"token", "password"}


@pytest.mark.parametrize("account_http", ["web.main_web"], indirect=True)
def test_saas_invitation_validation_preserves_methods_and_neighbor_contract(account_http):
    raw = account_http["raw"]
    assert raw.get("/api/auth/accept-invite").status_code == 405
    neighbor = raw.post("/api/auth/invite-info", json={"token": "invalid"})
    assert neighbor.status_code == 422 and isinstance(neighbor.json()["detail"], list)
    assert raw.post("/api/auth/accept-invite-extra", json={}).status_code == 404


@pytest.mark.parametrize("kind", ["common", "missing", "tampered"])
def test_recovery_policy_failure_preserves_link_then_strong_succeeds(account_http, monkeypatch, tmp_path, kind):
    from web import auth
    from web.database.models import Usuario
    from web.services import email_service
    from web.settings import get_settings
    case = account_http
    email = uuid.uuid4().hex + "@example.invalid"
    made = case["raw"].post("/api/auth/registro", json={"email": email, "password": STRONG, "nombre": "Synthetic B19", "tipo": "usuario"})
    assert made.status_code == 200
    with Session(case["admin"]) as db:
        identity = db.scalar(select(Usuario.id).where(Usuario.email == email))
    messages = []
    monkeypatch.setattr(get_settings(), "RESEND_API_KEY", "synthetic-b19-no-send")
    monkeypatch.setattr(email_service, "send_password_reset", lambda email, name, link: messages.append(link) or True)
    monkeypatch.setattr(email_service, "send_password_changed", lambda *args: True)
    case["raw"].headers.pop("Authorization", None)
    case["raw"].cookies.clear()
    request = case["raw"].post("/api/auth/password-reset/request", json={"email": email})
    assert request.status_code == 202
    wait_mail(case)
    assert len(messages) == 1
    token = parse_qs(urlsplit(messages[0]).fragment)["token"][0]
    before = state(case, identity)
    with policy_fault(monkeypatch, tmp_path, kind) as candidate:
        response = case["raw"].post("/api/auth/password-reset/confirm", json={"token": token, "new_password": candidate, "confirm_password": candidate})
        assert_private_rejection(response, candidate)
    assert state(case, identity) == before
    changed = STRONG + "-changed"
    response = case["raw"].post("/api/auth/password-reset/confirm", json={"token": token, "new_password": changed, "confirm_password": changed})
    assert response.status_code == 200
    wait_mail(case)
    with Session(case["admin"]) as db:
        user = db.get(Usuario, identity)
        assert user.password_reset_hash is None and user.session_version == before[0][1] + 1
        assert auth.verify_password(changed, user.password_hash)


@pytest.mark.parametrize("kind", ["common", "missing", "tampered"])
def test_account_policy_failure_preserves_primary_and_factor_then_strong_succeeds(account_http, monkeypatch, tmp_path, kind):
    from web import auth
    from web.database.models import MfaCredential, Usuario
    from web.services import mfa_service as mfa
    from web.services.mfa_crypto import decrypt, totp
    case = account_http
    original = mfa.instant
    now = original() + timedelta(seconds=31)
    monkeypatch.setattr(mfa, "instant", lambda value=None: original(now if value is None else value))
    proof = case["raw"].post("/api/auth/mfa/reauth", json={"password": PASSWORD}, headers=headers(case))
    assert proof.status_code == 200
    with Session(case["admin"]) as db:
        credential = db.get(MfaCredential, case["user"])
        secret = decrypt(credential.secret_ciphertext, mfa.configuration(), mfa._aad(credential, credential.generation, "active"))
    body = {"reauthentication_token": proof.json()["reauthentication_token"], "code": totp(secret, int(now.timestamp()) // 30)}
    before = state(case, case["user"])
    with policy_fault(monkeypatch, tmp_path, kind) as candidate:
        response = case["raw"].post("/api/account/security/password", headers=headers(case), json={**body, "new_password": candidate, "confirm_password": candidate})
        assert_private_rejection(response, candidate)
    assert state(case, case["user"]) == before
    response = case["raw"].post("/api/account/security/password", headers=headers(case), json={**body, "new_password": STRONG, "confirm_password": STRONG})
    assert response.status_code == 200 and response.json()["sessions_revoked"] is True
    assert "access_token" not in response.json() and "refresh_token" not in response.json()
    with Session(case["admin"]) as db:
        user = db.get(Usuario, case["user"])
        assert user.session_version == before[0][1] + 1 and auth.verify_password(STRONG, user.password_hash)


def test_login_existing_common_password_and_reads_do_not_use_blocklist(account_http, monkeypatch):
    from web import auth
    from web import password_blocklist as blocklist
    from web.database.models import Usuario
    case = account_http
    with Session(case["admin"]) as db:
        user = db.get(Usuario, case["member"])
        user.password_hash = auth.hash_password(common_candidate())
        email = user.email
        db.commit()
    def forbidden(*args, **kwargs):
        raise AssertionError("Login or read consulted password-setting policy")
    monkeypatch.setattr(blocklist, "contains_password", forbidden)
    monkeypatch.setattr("web.account_values.contains_password", forbidden)
    response = case["raw"].post("/api/auth/login", json={"email": email, "password": common_candidate()})
    assert response.status_code == 200
    case["raw"].headers["Authorization"] = "Bearer " + response.json()["token"]
    assert case["raw"].get("/api/auth/me").status_code == 200

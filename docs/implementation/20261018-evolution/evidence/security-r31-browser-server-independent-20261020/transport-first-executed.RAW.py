"""Independent persisted-cookie boundaries and uncertainty, without a provider.

Proofs stay in RAM; injected failures delegate the actual durable operation.
"""
import logging

import pytest

from tests import test_browser_session31_transport as fixtures
from web import auth
from web.settings import get_settings

followup_db = fixtures.followup_db
followup_http = fixtures.followup_http
browser = fixtures.browser


def test_cookie_identity_is_independent_of_the_existing_bearer(browser):
    bearer = browser["raw"].headers["Authorization"][7:]
    bearer_identity = auth.verificar_token(bearer)
    assert bearer_identity is not None
    _, made = fixtures.account(browser, browser_mode=True)
    access = fixtures.pair(made)
    identity = auth.verificar_token(access)
    assert identity is not None and identity["id"] != bearer_identity["id"]
    old = fixtures.cookie(browser)
    renewed = fixtures.pair(fixtures.post(browser, "/api/auth/refresh"))
    assert auth.verificar_token(renewed)["id"] == identity["id"]
    assert auth.verificar_refresh_token(old) is None
    result = fixtures.post(browser, "/api/auth/browser/logout")
    assert result.status_code == 200 and result.json()["server_confirmed"] is True
    assert auth.verificar_token(renewed) is None
    assert auth.verificar_token(bearer)["id"] == bearer_identity["id"]
    fixtures.private(result)


@pytest.mark.parametrize("variant", ["separate-cookie-headers", "dev-name-over-HTTPS"])
def test_ambiguous_or_other_scheme_cookie_does_not_supply_refresh_authority(browser, variant):
    _, made = fixtures.account(browser, browser_mode=True)
    fixtures.pair(made)
    proof = fixtures.cookie(browser)
    headers = list(fixtures.HEADERS.items())
    if variant == "separate-cookie-headers":
        headers += [("Cookie", "__Host-mb_refresh="+proof)]*2
    else:
        headers += [("Cookie", "mb_refresh_dev="+proof)]
    result = browser["raw"].post("/api/auth/refresh", json={}, headers=headers)
    assert result.status_code == 401
    assert result.json()["detail"]["code"] == "browser_session_unavailable"
    assert auth.verificar_refresh_token(proof) is not None
    fixtures.private(result)


def test_lost_ack_after_real_rotation_returns_no_proof_and_never_retries(browser, monkeypatch, caplog):
    _, made = fixtures.account(browser, browser_mode=True)
    fixtures.pair(made)
    old = fixtures.cookie(browser)
    rotated = []
    original = auth.rotar_refresh_token
    marker = "synthetic-private-rotation-ack-marker"

    def lost_ack(proof):
        result = original(proof)
        assert result is not None
        rotated.append(result)
        raise RuntimeError(marker)

    with caplog.at_level(logging.ERROR, logger="web.browser_session"):
        with monkeypatch.context() as patch:
            patch.setattr(auth, "rotar_refresh_token", lost_ack)
            result = fixtures.post(browser, "/api/auth/refresh")
    assert result.status_code == 503
    assert result.json()["detail"]["code"] == "browser_session_unconfirmed"
    assert all(key not in result.json() for key in ("token", "access_token", "refresh_token", "server_confirmed"))
    assert marker not in result.text
    assert len(rotated) == 1
    assert auth.verificar_refresh_token(old) is None
    assert auth.verificar_refresh_token(rotated[0]["refresh_token"]) is not None
    assert browser["raw"].cookies.get("__Host-mb_refresh") is None
    records = [r for r in caplog.records if r.name == "web.browser_session"]
    assert len(records) == 1 and "RuntimeError" in records[0].getMessage()
    assert marker not in records[0].getMessage() and records[0].exc_info is None
    fixtures.private(result)


def test_explicit_migration_replay_uses_existing_reuse_defense_only_for_its_owner(browser):
    bearer = browser["raw"].headers["Authorization"][7:]
    _, made = fixtures.account(browser)
    old = made.json()["refresh_token"]
    first = fixtures.post(browser, "/api/auth/browser/migrate", {"refresh_token": old})
    access = fixtures.pair(first)
    current = fixtures.cookie(browser)
    replay = fixtures.post(browser, "/api/auth/browser/migrate", {"refresh_token": old})
    assert replay.status_code == 401
    assert replay.json()["detail"]["code"] == "browser_session_unavailable"
    assert auth.verificar_refresh_token(current) is None
    assert auth.verificar_token(access) is None
    assert auth.verificar_token(bearer) is not None
    assert browser["raw"].cookies.get("__Host-mb_refresh") is None
    fixtures.private(replay)


def test_cookie_does_not_replace_bearer_or_legacy_body_authority(browser):
    _, made = fixtures.account(browser, browser_mode=True)
    fixtures.pair(made)
    proof = fixtures.cookie(browser)
    browser["raw"].headers.pop("Authorization", None)
    private_resource = browser["raw"].get("/api/clientes")
    assert private_resource.status_code == 401
    legacy = browser["raw"].post("/api/auth/refresh", json={})
    assert legacy.status_code == 400
    assert all(not value.startswith("__Host-mb_refresh=") for value in legacy.headers.get_list("set-cookie"))
    assert fixtures.cookie(browser) == proof
    assert auth.verificar_refresh_token(proof) is not None


@pytest.mark.parametrize("body", [
    '{"unexpected":"synthetic-private-browser-body"}',
    '[{"refresh_token":"synthetic-private-browser-body"}]',
    '"synthetic-private-browser-body"',
    '{"unexpected":NaN}',
    '{"unexpected":{"nested":"synthetic-private-browser-body"}}',
])
def test_closed_refresh_body_never_consumes_valid_cookie_or_echoes_input(browser, body):
    _, made = fixtures.account(browser, browser_mode=True)
    fixtures.pair(made)
    proof = fixtures.cookie(browser)
    result = browser["raw"].post("/api/auth/refresh", content=body,
        headers={**fixtures.HEADERS, "Content-Type": "application/json"})
    assert result.status_code == 422
    assert "synthetic-private-browser-body" not in result.text
    assert all(key not in result.json() for key in ("token", "access_token", "refresh_token", "server_confirmed"))
    assert auth.verificar_refresh_token(proof) is not None
    assert browser["raw"].cookies.get("__Host-mb_refresh") is None
    fixtures.private(result)


def test_actual_nonproduction_loopback_transport_has_only_dev_cookie(browser, monkeypatch):
    origin = "http://127.0.0.1:8000"
    assert not get_settings().is_production
    monkeypatch.setattr(get_settings(), "BASE_URL", origin)
    browser["raw"].base_url = origin
    email, _ = fixtures.account(browser)
    result = browser["raw"].post("/api/auth/login", json={
        "email": email, "password": fixtures.historical.PASSWORD},
        headers={"Origin": origin, "X-MetodoBase-Browser": "1"})
    fixtures.pair(result)
    header = result.headers["set-cookie"].lower()
    assert header.startswith("mb_refresh_dev=")
    assert "httponly" in header and "samesite=strict" in header and "path=/" in header
    assert "secure" not in header and "domain=" not in header and "__host-mb_refresh=" not in header
    assert auth.verificar_refresh_token(browser["raw"].cookies.get("mb_refresh_dev")) is not None

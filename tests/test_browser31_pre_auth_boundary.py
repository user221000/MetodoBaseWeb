"""Finite browser admission before even optional real Bearer lookup or SQL."""
import pytest
from sqlalchemy import event

from tests import test_browser_session31_transport as fixtures
from web import auth

followup_db = fixtures.followup_db
followup_http = fixtures.followup_http
browser = fixtures.browser


@pytest.mark.parametrize("variant", ["origin", "header", "content-type", "query", "slash", "method"])
def test_rejected_cookie_transport_never_reaches_authentication_or_SQL(browser, monkeypatch, variant):
    _, registered = fixtures.account(browser, browser_mode=True)
    fixtures.pair(registered)
    proof = fixtures.cookie(browser)
    verifier = auth.verificar_token
    calls, statements = [], []

    def observed(*args, **kwargs):
        calls.append(True)
        return verifier(*args, **kwargs)

    def sql(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    monkeypatch.setattr(auth, "verificar_token", observed)
    headers = {**fixtures.HEADERS, "Content-Type": "application/json"}
    path, method = "/api/auth/login", "POST"
    if variant == "origin":
        headers["Origin"] = "https://other.example.invalid"
    elif variant == "header":
        headers["X-MetodoBase-Browser"] = "0"
    elif variant == "content-type":
        headers["Content-Type"] = "text/plain"
    elif variant == "query":
        path += "?unexpected=1"
    elif variant == "slash":
        path += "/"
    else:
        method = "GET"
    event.listen(browser["engine"], "before_cursor_execute", sql)
    try:
        response = browser["raw"].request(method, path, content='{}', headers=headers)
    finally:
        event.remove(browser["engine"], "before_cursor_execute", sql)
    assert response.status_code == (415 if variant == "content-type" else 403)
    assert calls == [] and statements == []
    fixtures.private(response)
    assert all(not value.startswith("__Host-mb_refresh=") for value in response.headers.get_list("set-cookie"))
    assert fixtures.cookie(browser) == proof
    assert auth.verificar_refresh_token(proof) is not None


def test_legacy_Bearer_authority_and_browser_neighbors_keep_their_contract(browser, monkeypatch):
    from web.middleware import tenant
    original = tenant.admit
    admitted = []

    def observed(request):
        admitted.append(request.url.path)
        return original(request)

    monkeypatch.setattr(tenant, "admit", observed)
    me = browser["raw"].get("/api/auth/me")
    assert me.status_code == 200 and me.json()["id"] == browser["user"]
    adjacent = browser["raw"].post("/api/auth/login-neighbor", json={},
        headers={**fixtures.HEADERS, "Origin": "https://other.example.invalid"})
    assert adjacent.status_code == 404
    assert adjacent.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert admitted == []

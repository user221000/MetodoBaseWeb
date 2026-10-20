"""Independent admission ordering with genuine persisted bearer verification."""
from sqlalchemy import event

from tests import test_browser_session31_transport as fixtures
from web import auth

followup_db = fixtures.followup_db
followup_http = fixtures.followup_http
browser = fixtures.browser


def test_rejected_origin_precedes_tenant_bearer_verification_and_SQL(browser, monkeypatch):
    c = browser
    email, made = fixtures.account(c, browser_mode=True)
    fixtures.pair(made)
    proof = fixtures.cookie(c)
    assert c["raw"].headers["Authorization"].startswith("Bearer ")
    verification_calls, SQL_calls = [], []
    original = auth.verificar_token

    def observed(provided):
        verification_calls.append(True)
        return original(provided)  # Real signature/current-identity verification.

    def SQL_observed(connection, cursor, statement, parameters, context, executemany):
        SQL_calls.append(True)  # No statement/parameters or credential values retained.

    event.listen(c["engine"], "before_cursor_execute", SQL_observed)
    try:
        with monkeypatch.context() as patch:
            patch.setattr(auth, "verificar_token", observed)
            response = c["raw"].post("/api/auth/login", json={
                "email": email, "password": fixtures.historical.PASSWORD},
                headers={**fixtures.HEADERS, "Origin": "https://foreign.example.invalid"})
    finally:
        event.remove(c["engine"], "before_cursor_execute", SQL_observed)
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "browser_origin_invalid"
    fixtures.private(response)
    assert fixtures.cookie(c) == proof
    assert all(not value.startswith("__Host-mb_refresh=") for value in response.headers.get_list("set-cookie"))
    assert auth.verificar_refresh_token(proof) is not None
    assert verification_calls == [], "Invalid Origin must precede even middleware bearer verification"
    assert SQL_calls == [], "Invalid Origin must precede authentication SQL"

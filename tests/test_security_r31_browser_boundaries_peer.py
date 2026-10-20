"""Finite middleware admission preserves genuine verifier/neighbor behavior."""
import pytest

from tests import test_browser_session31_transport as fixtures
from web import auth

followup_db = fixtures.followup_db
followup_http = fixtures.followup_http
browser = fixtures.browser


@pytest.mark.parametrize("variant", ["slash", "duplicate-browser-header", "empty-browser-header",
    "content-type", "query", "legacy-no-header", "neighbor", "double-slash"])
def test_finite_pre_tenant_admission_preserves_legacy_and_neighbors(browser, monkeypatch, variant):
    _, made = fixtures.account(browser, browser_mode=True)
    fixtures.pair(made)
    proof = fixtures.cookie(browser)
    original = auth.verificar_token
    calls = []

    def observed(token):
        calls.append(True)
        return original(token)

    headers = {**fixtures.HEADERS, "Content-Type": "application/json"}
    path = "/api/auth/login"
    expected_status = 403
    if variant == "slash":
        path += "/"
    elif variant == "duplicate-browser-header":
        headers = list(headers.items())+[("X-MetodoBase-Browser", "1")]
    elif variant == "empty-browser-header":
        headers["X-MetodoBase-Browser"] = ""
    elif variant == "content-type":
        headers["Content-Type"] = "text/plain"
        expected_status = 415
    elif variant == "query":
        path += "?unrecognized=1"
    elif variant == "legacy-no-header":
        headers.pop("X-MetodoBase-Browser")
        expected_status = 422
    elif variant == "neighbor":
        path += "-extra"
        expected_status = 404
    elif variant == "double-slash":
        path += "//"
        expected_status = 307
    with monkeypatch.context() as patch:
        patch.setattr(auth, "verificar_token", observed)
        response = browser["raw"].post(path, content='{}', headers=headers, follow_redirects=False)
    assert response.status_code == expected_status
    if variant in {"legacy-no-header", "neighbor", "double-slash"}:
        assert bool(calls) == (browser["factory_name"] == "api.app")
        if variant == "double-slash":
            assert response.headers["location"] == str(browser["raw"].base_url.join("/api/auth/login"))
    else:
        assert calls == []
        fixtures.private(response)
    assert fixtures.cookie(browser) == proof
    assert auth.verificar_refresh_token(proof) is not None
    assert all(not v.startswith("__Host-mb_refresh=") for v in response.headers.get_list("set-cookie"))

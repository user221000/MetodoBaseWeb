"""Registration SSR exposes public Google configuration and separate proof forms."""
from html.parser import HTMLParser
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from tests.test_google_email_login import database_schema, isolated_database  # noqa: F401


class Forms(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.nested = False
        self.nodes = []

    def handle_starttag(self, tag, attrs):
        self.nodes.append((tag, dict(attrs)))
        if tag == "form":
            self.nested |= self.depth > 0
            self.depth += 1

    def handle_endtag(self, tag):
        if tag == "form":
            self.depth -= 1


@pytest.mark.parametrize("tipo", ["gym", "usuario"])
@pytest.mark.parametrize("client_id", ["", "synthetic-client</script><script>unsafe()"])
def test_registration_mounts_google_with_separate_email_and_factor_forms(monkeypatch, tipo, client_id):
    from config import settings
    from web.routes import pages

    monkeypatch.setattr(settings, "Settings", lambda: SimpleNamespace(GOOGLE_CLIENT_ID=client_id))
    app = FastAPI()

    @app.middleware("http")
    async def nonce(request, call_next):
        request.state.csp_nonce = "synthetic-registration-nonce"
        return await call_next(request)

    app.include_router(pages.router)
    with TestClient(app) as client:
        response = client.get("/registro", params={"tipo": tipo})
    assert response.status_code == 200
    assert "unsafe()</script>" not in response.text
    if client_id:
        assert r"\u003c/script\u003e" in response.text
    assert 'MfaLogin.mount({formId:"registroForm",registration:true' in response.text
    assert "email_verification_required" not in response.text
    inventory = Forms()
    inventory.feed(response.text)
    assert inventory.depth == 0 and not inventory.nested
    ids = [attrs["id"] for _, attrs in inventory.nodes if "id" in attrs]
    assert len(ids) == len(set(ids))
    assert {"googleBtnContainer", "registroForm", "mfa-login-email", "mfa-login-factor"}.issubset(ids)
    for tag, attrs in inventory.nodes:
        if tag == "script":
            assert attrs["nonce"] == "synthetic-registration-nonce"
        if attrs.get("id") in {"mfa-login-email", "mfa-login-factor"}:
            assert "hidden" in attrs
        if attrs.get("id") == "mfa-login-email-code":
            assert attrs["maxlength"] == "6" and attrs["autocomplete"] == "one-time-code"
            assert "value" not in attrs

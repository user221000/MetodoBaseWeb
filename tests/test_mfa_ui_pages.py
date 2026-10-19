"""Page-only ASGI composition; no MFA service/provider or identity claim."""
from html.parser import HTMLParser
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class FormInventory(HTMLParser):
    def __init__(self):
        super().__init__()
        self.forms = 0
        self.nested = False
        self.ids = []
        self.attrs = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        self.ids.append(values.get("id", ""))
        self.attrs.extend(value for _, value in attrs if value)
        if tag == "form":
            self.nested |= self.forms > 0
            self.forms += 1

    def handle_endtag(self, tag):
        if tag == "form":
            self.forms -= 1


@pytest.mark.parametrize("client_id", ["", "synthetic-public-client</script><script>unsafe()"])
@pytest.mark.parametrize("route", ["/login-usuario", "/login-gym", "/mi-perfil", "/configuracion"])
def test_mfa_page_public_configuration_and_forms(monkeypatch, client_id, route):
    from config import settings
    from web.routes import pages

    monkeypatch.setattr(settings, "Settings", lambda: SimpleNamespace(GOOGLE_CLIENT_ID=client_id))
    app = FastAPI()

    @app.middleware("http")
    async def nonce(request, call_next):
        request.state.csp_nonce = "synthetic-page-nonce"
        return await call_next(request)

    app.include_router(pages.router)
    with TestClient(app) as client:
        response = client.get(route)
    assert response.status_code == 200
    assert "unsafe()</script>" not in response.text
    if client_id:
        assert "synthetic-public-client" in response.text
        assert r"\u003c/script\u003e" in response.text
    inventory = FormInventory()
    inventory.feed(response.text)
    assert not inventory.nested
    assert inventory.forms == 0
    ids = [value for value in inventory.ids if value.startswith("mfa-")]
    assert len(ids) == len(set(ids))
    assert ids
    assert all("otpauth://" not in value for value in inventory.attrs)
    if route.startswith("/login"):
        assert "MfaLogin.mount" in response.text
        assert "localStorage.setItem" not in response.text
        assert "mfa-login-destination" in ids
    else:
        assert "MfaUI.mountAccount" in response.text
        assert "mfa-account" in ids

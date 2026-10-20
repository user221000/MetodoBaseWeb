"""Actual web shells preserve boot order and parse without a browser/network provider."""
import importlib
import json
import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
ROUTES = ["/dashboard", "/clientes", "/generar-plan", "/planes", "/suscripciones",
          "/configuracion", "/equipo", "/equipo/inicio", "/mi-plan", "/mi-perfil",
          "/mi-historial", "/mi-suscripcion", "/mis-vinculos", "/mi-progreso",
          "/clientes/legacy42/vinculacion", "/clientes/legacy42/progreso", "/seguimiento",
          "/clientes/legacy42/seguimiento", "/cuenta/google", "/auth/accept-client-link",
          "/login-gym", "/login-usuario", "/registro", "/auth/accept-invite"]


class Scripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.scripts.append(dict(attrs))


@pytest.mark.parametrize("factory", ["api.app", "web.main_web"])
@pytest.mark.parametrize("route", ROUTES)
def test_current_auth_shell_uses_versioned_ram_client_and_valid_inline_scripts(factory, route):
    with TestClient(importlib.import_module(factory).create_app(), raise_server_exceptions=False) as client:
        response = client.get(route)
    assert response.status_code == 200
    markup = Scripts()
    markup.feed(response.text)
    api = [row for row in markup.scripts if row.get("src", "").startswith("/static/js/api.js")]
    assert len(api) == 1
    assert "r31browser1" in api[0]["src"]
    assert not re.search(r"(?:localStorage|sessionStorage)\.(?:getItem|setItem)\(['\"]mb_(?:token|refresh_token|nombre|email|tipo)", response.text)
    if route in ROUTES[:12]:
        paths = [row.get("src", "") for row in markup.scripts]
        assert next(i for i, path in enumerate(paths) if path.startswith("/static/js/api.js")) < next(i for i, path in enumerate(paths) if path.startswith("/static/js/session-shell.js"))
    executable = shutil.which("node")
    assert executable
    result = subprocess.run([executable, "tests/e2e/browser_session31_ssr.cjs"],
                            input=json.dumps({"html": response.text, "route": route}),
                            capture_output=True, text=True, cwd=ROOT, check=False, timeout=20)
    assert result.returncode == 0, result.stderr[-1000:]
    assert json.loads(result.stdout)["parsed"] is True


@pytest.mark.parametrize("factory", ["api.app", "web.main_web"])
@pytest.mark.parametrize("route", ["/", "/auth/reset-password", "/retirar-consentimientos"])
def test_public_proof_pages_do_not_bootstrap_or_adopt_an_authenticated_cookie(factory, route):
    with TestClient(importlib.import_module(factory).create_app(), raise_server_exceptions=False) as client:
        response = client.get(route)
    assert response.status_code == 200
    assert "/static/js/api.js" not in response.text
    assert "mb_token" not in response.text and "mb_refresh_token" not in response.text


def test_session_storage_access_is_only_the_single_purge_and_migration_block():
    api = (ROOT / "web/static/js/api.js").read_text(encoding="utf8")
    start, end = api.index("  function _takeLegacy()"), api.index("  async function _bootstrap()")
    legacy = api[start:end]
    remainder = api[:start] + api[end:]
    assert "store.getItem('mb_token')" in legacy and "store.getItem('mb_refresh_token')" in legacy
    assert "store.removeItem(key)" in legacy
    assert "setItem" not in legacy
    assert "getRefreshToken" not in api
    for path in [*(ROOT / "web/static/js").glob("*.js"), *(ROOT / "web/templates").glob("*.html")]:
        text = remainder if path.name == "api.js" else path.read_text(encoding="utf8")
        assert not re.search(r"(?:localStorage|sessionStorage|store)\.(?:getItem|setItem)\(['\"]mb_(?:token|refresh_token|nombre|email|tipo)", text), path.name
    assert not re.search(r"indexedDB|caches\.(?:open|put)", api)


def test_recovery_transport_keeps_its_separate_one_time_proof_contract():
    text = (ROOT / "web/static/js/account-recovery.js").read_text(encoding="utf8")
    assert "credentials: 'omit'" in text
    assert "history.replaceState" in text
    assert "Api." not in text

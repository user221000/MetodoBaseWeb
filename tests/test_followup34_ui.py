"""SSR privacy and actual HTTP DTO/consumer compatibility, with no browser lease."""
import json
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests import nutrition35_fixtures as fixtures

followup_db = fixtures.followup_db
followup_http = fixtures.followup_http
create = fixtures.create


class Markup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.nodes = []

    def handle_starttag(self, tag, attrs):
        self.nodes.append((tag, dict(attrs)))


@pytest.mark.parametrize("factory", ["api.app", "web.main_web"])
@pytest.mark.parametrize("route", ["/seguimiento", "/seguimiento/", "/clientes/legacy42/seguimiento", "/clientes/legacy42/seguimiento/"])
def test_followup_shell_is_inert_local_and_private(factory, route):
    import importlib
    with TestClient(importlib.import_module(factory).create_app(), raise_server_exceptions=False) as client:
        response = client.get(route)
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "default-src 'none'" in response.headers["Content-Security-Policy"]
    assert "https:" not in response.headers["Content-Security-Policy"]
    markup = Markup()
    markup.feed(response.text)
    identifiers = [attrs["id"] for _, attrs in markup.nodes if "id" in attrs]
    assert len(identifiers) == len(set(identifiers))
    assert "tasks-page" in identifiers
    roots = [attrs for _, attrs in markup.nodes if attrs.get("id") == "tasks-page"]
    assert roots[0].get("data-client-id") == ("legacy42" if "/clientes/" in route else None)
    labels = {attrs.get("for") for tag, attrs in markup.nodes if tag == "label"}
    for tag, attrs in markup.nodes:
        assert not any(key.startswith("on") for key in attrs)
        if tag in {"script", "link"}:
            assert attrs.get("src", attrs.get("href", "")).startswith("/static/")
        if tag == "script":
            assert "nonce" in attrs
        if tag in {"select", "input"}:
            assert attrs["id"] in labels or attrs.get("type") == "checkbox"
            assert "name" not in attrs
        if tag == "dialog":
            assert attrs["aria-labelledby"] == "tasks-form-title"
            assert "open" not in attrs
    assert "<table" not in response.text
    assert "Synthetic task client" not in response.text


def test_followup_consumer_parses_actual_http_dtos_from_both_factories(followup_http):
    raw = followup_http["raw"]
    created, body, key = create(followup_http)
    assert created.status_code == 200
    identifier = created.json()["task"]["id"]
    replayed = raw.post("/api/seguimiento/tareas", json=body, headers={"Idempotency-Key": key})
    assert replayed.status_code == 200
    routes = {
        "context": "/api/seguimiento/contexto",
        "list": "/api/seguimiento/tareas?status=open&limit=50",
        "task": "/api/seguimiento/tareas/" + identifier,
        "candidates": "/api/seguimiento/clientes/" + followup_http["profile"] + "/candidatos",
        "history": "/api/seguimiento/tareas/" + identifier + "/historial?limit=20&after_version=0",
        "metrics": "/api/seguimiento/metricas",
    }
    values = {"created": created.json(), "replayed": replayed.json(), "client": followup_http["profile"], "command": body}
    for name, route in routes.items():
        response = raw.get(route)
        assert response.status_code == 200, name
        values[name] = response.json()
    node = shutil.which("node")
    assert node is not None
    result = subprocess.run([node, "tests/e2e/followup_tasks_http_dto.cjs"],
                            input=json.dumps(values), text=True, capture_output=True,
                            cwd=Path(__file__).resolve().parents[1], timeout=30, check=False)
    assert result.returncode == 0, "Actual HTTP DTOs failed maintained JavaScript parser: " + result.stderr[-2000:]
    assert json.loads(result.stdout)["parsers"] == 8


@pytest.mark.parametrize("factory", ["api.app", "web.main_web"])
def test_followup_shell_redirect_alias_has_exact_private_destination(factory):
    import importlib
    with TestClient(importlib.import_module(factory).create_app(), raise_server_exceptions=False) as client:
        response = client.get("/clientes/legacy42/seguimiento//", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["Location"] == "http://testserver/clientes/legacy42/seguimiento"
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "default-src 'none'" in response.headers["Content-Security-Policy"]
    assert "https:" not in response.headers["Content-Security-Policy"]


def test_followup_discovery_is_explicit_without_automatic_mutations():
    root = Path(__file__).resolve().parents[1]
    assert 'href="/seguimiento"' in (root / "web/templates/dashboard.html").read_text(encoding="utf8")
    assert 'href="/seguimiento"' in (root / "web/templates/equipo_inicio.html").read_text(encoding="utf8")
    assert "'/seguimiento'" in (root / "web/templates/clientes.html").read_text(encoding="utf8")

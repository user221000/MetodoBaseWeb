"""Current35 SSR semantics and actual SQLite HTTP→JavaScript-controller→HTTP compatibility."""
import importlib
import json
import shutil
import subprocess
import uuid
from html.parser import HTMLParser
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests import test_nutrition35_http as fixtures
from web.database.models import Cliente, GymGenerationReservation

followup_db = fixtures.followup_db
followup_http = fixtures.followup_http
personal35_http = fixtures.personal35_http


def node(values):
    executable = shutil.which("node")
    assert executable is not None
    result = subprocess.run([executable, "tests/e2e/nutrition35_http_contract.cjs"],
                            input=json.dumps(values), capture_output=True, text=True,
                            cwd=Path(__file__).resolve().parents[1], timeout=30, check=False)
    assert result.returncode == 0, "Maintained JavaScript contract failed: " + result.stderr[-1000:]
    return json.loads(result.stdout)


class Markup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.nodes = []

    def handle_starttag(self, tag, attrs):
        self.nodes.append((tag, dict(attrs)))


@pytest.mark.parametrize("factory,route,key", [
    ("api.app", "/clientes", "client"), ("web.main_web", "/clientes", "client"),
    ("api.app", "/generar-plan", "new-client"), ("web.main_web", "/generar-plan", "new-client"),
    ("web.main_web", "/mi-perfil", "personal"), ("web.main_web", "/mi-plan", None),
])
def test_nutrition_declaration_form_is_explicit_local_and_inert(factory, route, key):
    with TestClient(importlib.import_module(factory).create_app(), raise_server_exceptions=False) as client:
        response = client.get(route)
    assert response.status_code == 200
    markup = Markup()
    markup.feed(response.text)
    ids = [attrs["id"] for _, attrs in markup.nodes if "id" in attrs]
    assert len(ids) == len(set(ids))
    assert "/static/js/nutrition35.js" in response.text
    if key:
        roots = [attrs for _, attrs in markup.nodes if attrs.get("id") == "nutrition35-" + key]
        assert len(roots) == 1
        assert roots[0]["data-nutrition-key"] == key
        for tag, attrs in markup.nodes:
            if attrs.get("id", "").startswith("nutrition35-" + key + "-"):
                assert not any(name.startswith("on") for name in attrs)
                if tag in {"input", "select"}:
                    assert "name" not in attrs
                    assert "disabled" in attrs
                    assert "value" not in attrs
                    if tag == "input":
                        assert attrs["autocomplete"] == "off"
    assert "ni autoriza clínicamente" in response.text or "no se interpretan" in response.text.lower()
    parsed = node({"mode": "parse_html", "html": response.text})
    assert parsed["passed"] and parsed["inline_scripts"] > 0


def test_weight_only_real_http_preserves_a_concurrent_declaration(followup_http):
    c = followup_http
    raw = c["raw"]
    assert raw.put("/api/clientes/" + c["profile"], json=fixtures.VALID).status_code == 200
    profile = raw.get("/api/clientes/" + c["profile"])
    catalog = raw.get("/api/alimentos/catalogo")
    assert profile.status_code == catalog.status_code == 200
    intent = node({"kind": "client", "mode": "weight", "profile": profile.json(), "catalog": catalog.json()})
    assert "restricciones_nutricionales" not in intent["body"]
    concurrent = fixtures.declaration(reported=True)
    assert raw.put("/api/clientes/" + c["profile"], json={"restricciones_nutricionales": concurrent}).status_code == 200
    assert raw.put("/api/clientes/" + c["profile"], json=intent["body"]).status_code == 200
    assert raw.get("/api/clientes/" + c["profile"]).json()["restricciones_nutricionales"] == concurrent


def test_explicit_ui_declaration_reaches_http_guard_before_generation_quota(followup_http):
    c = followup_http
    raw = c["raw"]
    profile = raw.get("/api/clientes/" + c["profile"])
    catalog = raw.get("/api/alimentos/catalogo")
    assert profile.status_code == catalog.status_code == 200
    intent = node({"kind": "client", "mode": "report", "profile": profile.json(), "catalog": catalog.json()})
    assert raw.put("/api/clientes/" + c["profile"], json=intent["body"]).status_code == 200
    response = raw.post("/api/generar-plan", json={"id_cliente": c["profile"], "plan_numero": 1,
                                                 "tipo_plan": "menu_fijo"},
                        headers={"Idempotency-Key": str(uuid.uuid4())})
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "nutrition_professional_review_required"
    current = raw.get("/api/clientes/" + c["profile"])
    assert current.headers["Cache-Control"] == "no-store"
    assert current.headers["Referrer-Policy"] == "no-referrer"
    verified = node({"kind": "client", "mode": "read", "profile": current.json(), "catalog": catalog.json()})
    assert verified["blocked"] is True
    with Session(c["admin"]) as db:
        assert db.query(GymGenerationReservation).filter_by(gym_id=c["user"]).count() == 0


def test_corrupt_real_profile_never_becomes_a_no_allergy_default(followup_http):
    c = followup_http
    with Session(c["admin"]) as db:
        client = db.query(Cliente).filter_by(id_cliente=c["profile"], gym_id=c["user"]).one()
        client.nutrition_restrictions_json = '{"version": true}'
        db.commit()
    response = c["raw"].get("/api/clientes/" + c["profile"])
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "nutrition_restrictions_invalid"
    catalog = c["raw"].get("/api/alimentos/catalogo")
    verified = node({"kind": "client", "mode": "read", "profile": {"id_cliente": c["profile"]},
                     "catalog": catalog.json(), "read_status": response.status_code,
                     "read_code": response.json()["detail"]["code"]})
    assert verified["phase"] == "error" and verified["blocked"] is True


def test_personal_ui_partial_and_explicit_updates_use_only_saas_profile(personal35_http):
    raw = personal35_http["raw"]
    email = uuid.uuid4().hex + "@example.invalid"
    assert raw.post("/api/auth/registro", json={"email": email, "password": fixtures.PASSWORD,
                                                "nombre": "Synthetic individual", "tipo": "usuario"}).status_code == 200
    login = raw.post("/api/auth/login", json={"email": email, "password": fixtures.PASSWORD})
    assert login.status_code == 200
    raw.headers["Authorization"] = "Bearer " + login.json()["token"]
    assert raw.put("/api/usuario/perfil", json=fixtures.VALID).status_code == 200
    profile = raw.get("/api/usuario/perfil")
    catalog = raw.get("/api/usuario/catalogo-alimentos")
    assert profile.status_code == catalog.status_code == 200
    intent = node({"kind": "personal", "mode": "report", "profile": profile.json(), "catalog": catalog.json()})
    assert raw.put("/api/usuario/perfil", json=intent["body"]).status_code == 200
    reported = raw.get("/api/usuario/perfil").json()
    partial = node({"kind": "personal", "mode": "weight", "profile": reported, "catalog": catalog.json()})
    assert "restricciones_nutricionales" not in partial["body"]
    assert raw.put("/api/usuario/perfil", json=partial["body"]).status_code == 200
    assert raw.get("/api/usuario/perfil").json()["restricciones_nutricionales"] == reported["restricciones_nutricionales"]
    blocked = raw.post("/api/usuario/generar-plan", headers={"Idempotency-Key": str(uuid.uuid4())})
    assert blocked.status_code == 422 and blocked.json()["detail"]["code"] == "nutrition_professional_review_required"

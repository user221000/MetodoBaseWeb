"""Closed profile-write errors; read and neighboring route contracts remain."""
import uuid

from sqlalchemy.orm import Session

from tests import test_nutrition35_http as fixtures
from web.database.models import Cliente

followup_db = fixtures.followup_db
followup_http = fixtures.followup_http
personal35_http = fixtures.personal35_http
SENTINEL = "SYNTHETIC_NUTRITION35_ERROR_BOUNDARY"


def _invalid_envelopes():
    return [
        [{"restricciones_nutricionales": {"private": SENTINEL}}],
        [[{"restricciones_nutricionales": {"private": SENTINEL}}]],
        SENTINEL, 5, True, None,
        {"unknown": SENTINEL},
        {"peso_kg": SENTINEL},
    ]


def _private_invalid(response):
    assert response.status_code == 422
    assert response.json() == {"detail": {"code": "nutrition_profile_invalid_input",
        "message": "Revisa los datos del perfil."}}
    assert SENTINEL not in response.text
    assert response.headers.get("cache-control") == "no-store"
    assert response.headers.get("referrer-policy") == "no-referrer"


def test_client_write_routes_redact_all_invalid_envelopes(followup_http):
    c = followup_http
    for method, path in [("POST", "/api/clientes"), ("PUT", "/api/clientes/" + c["profile"])]:
        for body in _invalid_envelopes():
            _private_invalid(c["raw"].request(method, path, json=body))
        _private_invalid(c["raw"].request(method, path,
            content='{"restricciones_nutricionales": "' + SENTINEL + '"',
            headers={"Content-Type": "application/json"}))
    with Session(c["admin"]) as db:
        clients = db.query(Cliente).filter_by(gym_id=c["user"]).all()
        assert len(clients) == 1 and clients[0].nutrition_restrictions_json is None
        assert clients[0].peso_kg is None


def test_personal_write_route_redacts_every_invalid_envelope(personal35_http):
    c = personal35_http
    raw = c["raw"]
    email = uuid.uuid4().hex + "@example.invalid"
    assert raw.post("/api/auth/registro", json={"email": email, "password": fixtures.PASSWORD,
        "nombre": "Synthetic personal error boundary", "tipo": "usuario"}).status_code == 200
    login = raw.post("/api/auth/login", json={"email": email, "password": fixtures.PASSWORD})
    assert login.status_code == 200
    raw.headers["Authorization"] = "Bearer " + login.json()["token"]
    for body in _invalid_envelopes():
        _private_invalid(raw.put("/api/usuario/perfil", json=body))
    assert raw.get("/api/usuario/perfil").json()["restricciones_nutricionales"] == fixtures.declaration()


def test_read_queries_methods_and_route_neighbors_preserve_validation_contract(followup_http):
    raw = followup_http["raw"]
    invalid = raw.get("/api/clientes", params={"limite": "synthetic-invalid-limit"})
    assert invalid.status_code == 422
    assert isinstance(invalid.json()["detail"], list)
    assert invalid.json()["detail"][0]["loc"] == ["query", "limite"]
    assert invalid.json()["detail"][0]["input"] == "synthetic-invalid-limit"
    for method, path, status in [("PATCH", "/api/clientes/" + followup_http["profile"], 405),
                                  ("POST", "/api/clientes-neighbor", 404)]:
        response = raw.request(method, path, json={"private": SENTINEL})
        assert response.status_code == status
        assert response.json()["detail"] in {"Method Not Allowed", "Not Found"}
        assert SENTINEL not in response.text

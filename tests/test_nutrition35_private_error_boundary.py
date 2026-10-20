"""Private nutrition failures and aliases without altering neighboring APIs."""
import importlib
import logging

from tests import test_nutrition35_http as fixtures
from web.nutrition_paths import is_nutrition_private

followup_db = fixtures.followup_db
followup_http = fixtures.followup_http


def test_nutrition_matcher_has_exact_paths_and_one_slash_only():
    for path in ["/api/clientes", "/api/clientes/legacy42", "/api/generar-plan",
                 "/api/usuario/perfil", "/api/usuario/generar-plan"]:
        assert is_nutrition_private(path)
        assert is_nutrition_private(path + "/")
    for path in ["/api/clientes-neighbor", "/api/clientes//",
                 "/api/clientes/legacy42/extra", "/api/clientes/legacy42//",
                 "/api/usuario/perfil-neighbor", "/api/usuario/perfil//",
                 "/api/generar-plan/extra", "/api/generar-plan//",
                 "/api/usuario/generar-plan/extra", "/clientes", "/mi-perfil",
                 "/static/js/nutrition35.js"]:
        assert not is_nutrition_private(path)


def test_unsupported_methods_aliases_and_neighbors_have_distinct_headers(followup_http):
    c = followup_http
    raw = c["raw"]
    for path in ["/api/clientes", "/api/clientes/" + c["profile"], "/api/generar-plan",
                 "/api/usuario/perfil", "/api/usuario/generar-plan"]:
        absent = c["factory_name"] == "api.app" and path.startswith("/api/usuario/")
        for method in ["OPTIONS", "PATCH"]:
            for slash in ["", "/"]:
                response = raw.request(method, path + slash, follow_redirects=False)
                assert response.status_code == (404 if absent else 307 if slash else 405)
                assert response.headers.get("cache-control") == "no-store"
                assert response.headers.get("referrer-policy") == "no-referrer"
                if response.status_code == 307:
                    assert response.headers["location"] == "http://testserver" + path
    for path in ["/api/clientes-neighbor", "/api/clientes/" + c["profile"] + "/extra",
                 "/api/usuario/perfil-neighbor", "/api/generar-plan/extra"]:
        response = raw.get(path, follow_redirects=False)
        assert response.status_code == 404
        assert response.headers.get("cache-control") == "no-store, max-age=0"
        assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


def test_read_query_validation_retains_detail_and_gains_private_headers(followup_http):
    response = followup_http["raw"].get("/api/clientes", params={"limite": "synthetic-invalid-limit"})
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)
    detail = response.json()["detail"][0]
    assert detail["loc"] == ["query", "limite"] and detail["input"] == "synthetic-invalid-limit"
    assert response.headers.get("cache-control") == "no-store"
    assert response.headers.get("referrer-policy") == "no-referrer"


def test_unexpected_failure_logs_class_without_exception_values(followup_http, monkeypatch, caplog):
    c = followup_http
    module = importlib.import_module("api.routes.clientes" if c["factory_name"] == "api.app" else "web.routes.clientes")
    marker = "SYNTHETIC_NUTRITION35_PRIVATE_EXCEPTION"

    def fail(*args, **kwargs):
        raise RuntimeError(marker)

    monkeypatch.setattr(module.repo, "obtener_cliente", fail)
    with caplog.at_level(logging.ERROR, logger="web.nutrition_http"):
        response = c["raw"].get("/api/clientes/" + c["profile"])
    assert response.status_code == 500
    assert response.json()["detail"] == "Error interno del servidor"
    records = [record for record in caplog.records if record.name == "web.nutrition_http"]
    assert len(records) == 1
    assert records[0].getMessage() == "Nutrition request failed class=RuntimeError"
    assert records[0].exc_info is None and marker not in response.text

"""Independent real-factory/auth/SQL statistics boundary checks.

The only injected failure is a named SQLAlchemy driver boundary error. SQLite
here proves HTTP composition/session cleanup, not PostgreSQL RLS acceptance.
"""
import importlib
import logging
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import Session


FACTORIES = ["web.main_web", "api.app"]
PRIVATE = "SYNTHETIC-STATS-DRIVER-PARAMETER"


@pytest.fixture
def stats_accounts(test_gym_user):
    from web.auth import crear_access_token
    from web.database.engine import get_engine
    from web.database.models import Cliente, Usuario, UserRole

    foreign = str(uuid.uuid4())
    viewer = str(uuid.uuid4())
    with Session(get_engine()) as db:
        db.add(Usuario(id=foreign, email=f"{foreign}@example.invalid", nombre="Foreign",
                       password_hash="not-a-login", tipo="gym", role=UserRole.OWNER, activo=True))
        db.commit()
        db.add_all([
            Cliente(gym_id=foreign, nombre="SYNTHETIC-FOREIGN-CLIENT", activo=True),
            Usuario(id=viewer, email=f"{viewer}@example.invalid", nombre="Viewer",
                    password_hash="not-a-login", tipo="gym", role=UserRole.VIEWER,
                    team_gym_id=test_gym_user["id"], session_version=0, activo=True),
        ])
        db.commit()
    token = crear_access_token({"id": viewer, "email": f"{viewer}@example.invalid",
                               "nombre": "Viewer", "tipo": "gym", "role": "viewer",
                               "team_gym_id": test_gym_user["id"]})
    return test_gym_user, {"Authorization": f"Bearer {token}"}


def assert_empty(response):
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_clientes"] == body["planes_periodo"] == 0
    assert body["top_clientes"] == []
    assert len(body["planes_por_dia"]) == 7
    assert body["planes_por_dia"] == [0] * 7
    assert "SYNTHETIC-FOREIGN" not in response.text


@pytest.mark.parametrize("factory", FACTORIES)
def test_real_statistics_confirms_zero_without_foreign_rows(factory, stats_accounts):
    owner, _ = stats_accounts
    with TestClient(importlib.import_module(factory).create_app(),
                    raise_server_exceptions=False) as client:
        assert_empty(client.get("/api/estadisticas", headers=owner["auth_headers"]))


@pytest.mark.parametrize("factory", FACTORIES)
@pytest.mark.parametrize("query_name", ["obtener_estadisticas", "obtener_planes_por_dia"])
def test_real_driver_error_is_503_sanitized_and_session_recovers(
    factory, query_name, stats_accounts, monkeypatch, caplog
):
    from web.database import repository
    from web.database.engine import get_engine

    owner, _ = stats_accounts
    actual = getattr(repository, query_name)
    observed = []

    def instrumented(db, *args, **kwargs):
        connection = db.connection()
        observed.append((db, connection))
        connection.info["qa_stats_failure"] = True
        try:
            return actual(db, *args, **kwargs)
        finally:
            connection.info.pop("qa_stats_failure", None)

    def driver_error(conn, cursor, statement, parameters, context, executemany):
        if conn.info.get("qa_stats_failure"):
            raise StatementError("synthetic driver failure", "SELECT synthetic_secret=:value",
                                 {"value": PRIVATE}, RuntimeError(PRIVATE))

    app = importlib.import_module(factory).create_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        monkeypatch.setattr(repository, query_name, instrumented)
        event.listen(get_engine(), "before_cursor_execute", driver_error)
        try:
            with caplog.at_level(logging.ERROR):
                response = client.get("/api/estadisticas", headers=owner["auth_headers"])
            assert response.status_code == 503, response.text
            assert response.json()["detail"]["code"] == "statistics_unavailable"
            assert "total_clientes" not in response.text
            assert PRIVATE not in response.text + caplog.text
            assert "synthetic_secret" not in response.text + caplog.text
            name = "web.routes.stats" if factory == "web.main_web" else "api.routes.stats"
            records = [r for r in caplog.records if r.name == name]
            assert len(records) == 1
            assert records[0].getMessage() == "Statistics unavailable class=StatementError"
            assert records[0].exc_info is None and records[0].stack_info is None
            assert len(observed) == 1
            assert observed[0][1].closed
            assert not observed[0][0].in_transaction()
        finally:
            event.remove(get_engine(), "before_cursor_execute", driver_error)
            monkeypatch.setattr(repository, query_name, actual)
        assert_empty(client.get("/api/estadisticas", headers=owner["auth_headers"]))


@pytest.mark.parametrize("factory", FACTORIES)
def test_real_auth_and_viewer_denials_precede_statistics_reads(factory, stats_accounts, monkeypatch):
    from web.database import repository

    _, viewer_headers = stats_accounts

    def unexpected(*args, **kwargs):
        pytest.fail("Unauthorized identities must not enter statistics queries")

    monkeypatch.setattr(repository, "obtener_estadisticas", unexpected)
    monkeypatch.setattr(repository, "obtener_planes_por_dia", unexpected)
    with TestClient(importlib.import_module(factory).create_app(),
                    raise_server_exceptions=False) as client:
        assert client.get("/api/estadisticas").status_code == 401
        response = client.get("/api/estadisticas", headers=viewer_headers)
        assert response.status_code == 403, response.text
        assert "statistics_unavailable" not in response.text

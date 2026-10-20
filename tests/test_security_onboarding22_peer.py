"""Independent SQLite/real-factory review of the two preparation facts.

Persisted principals and signed bearer validation are real. Fixture-issued
bearers are not browser login/MFA acceptance; metadata is not PostgreSQL RLS.
SQL observers attach only after synthetic setup and app startup.
"""
import importlib
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

FACTORIES = ("api.app", "web.main_web")


def foreign_owner():
    from web.auth import crear_access_token
    from web.database.engine import get_engine
    from web.database.models import UserRole, Usuario

    actor = {"id": str(uuid.uuid4()), "email": f"{uuid.uuid4()}@example.invalid",
             "nombre": "Synthetic peer gym B", "tipo": "gym", "role": "owner",
             "session_version": 0}
    with Session(get_engine()) as db:
        db.add(Usuario(**{k: actor[k] for k in ("id", "email", "nombre", "tipo")},
                       role=UserRole.OWNER, password_hash="not-a-login",
                       activo=True, session_version=0))
        db.commit()
    return {**actor, "auth_headers": {"Authorization": f"Bearer {crear_access_token(actor)}"}}


def client_row(gym):
    from web.database.engine import get_engine
    from web.database.models import Cliente

    identifier = str(uuid.uuid4())
    with Session(get_engine()) as db:
        db.add(Cliente(id_cliente=identifier, gym_id=gym,
                       nombre="Synthetic peer client", activo=True))
        db.commit()
    return identifier


def plan_row(gym, identifier):
    from web.database.engine import get_engine
    from web.database.models import PlanGenerado

    with Session(get_engine()) as db:
        row = PlanGenerado(gym_id=gym, id_cliente=identifier,
                           fecha_generacion=datetime.now(UTC)-timedelta(days=800),
                           plan_json="{}")
        db.add(row)
        db.commit()
        return row.id


@contextmanager
def observed_reads():
    from web.database.engine import get_engine

    statements = []

    def observe(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement.lstrip().split(None, 1)[0].upper())

    event.listen(get_engine(), "before_cursor_execute", observe)
    try:
        yield statements
    finally:
        event.remove(get_engine(), "before_cursor_execute", observe)
    assert statements
    assert not {"INSERT", "UPDATE", "DELETE", "REPLACE"}.intersection(statements)


def facts(response, client, plan):
    assert response.status_code == 200
    value = response.json()["onboarding"]
    assert value == {"client_registered": client, "plan_saved": plan}
    assert set(value) == {"client_registered", "plan_saved"}
    assert all(type(item) is bool for item in value.values())


@pytest.mark.parametrize("factory", FACTORIES)
@pytest.mark.parametrize("client_gym,plan_gym", [("A", "A"), ("A", "B"),
                                                  ("B", "A"), ("B", "B")])
def test_both_join_keys_are_required_with_independent_active_clients(
        factory, client_gym, plan_gym, test_gym_user):
    other = foreign_owner()
    actors = {"A": test_gym_user, "B": other}
    clients = {key: client_row(actor["id"]) for key, actor in actors.items()}
    plan_row(actors[plan_gym]["id"], clients[client_gym])
    with TestClient(importlib.import_module(factory).create_app()) as http, observed_reads():
        for key, actor in actors.items():
            response = http.get("/api/estadisticas", headers=actor["auth_headers"],
                                params={"periodo": "semana"})
            facts(response, True, key == client_gym == plan_gym)
            assert response.json()["planes_periodo"] == 0


@pytest.mark.parametrize("factory", FACTORIES)
def test_query_and_header_gym_hints_cannot_adopt_another_actors_progress(factory, test_gym_user):
    other = foreign_owner()
    client_row(test_gym_user["id"])
    plan_row(other["id"], client_row(other["id"]))
    with TestClient(importlib.import_module(factory).create_app()) as http, observed_reads():
        for actor, hint, expected in [(test_gym_user, other, False), (other, test_gym_user, True)]:
            headers = {**actor["auth_headers"], "X-Gym-Id": hint["id"],
                       "X-Tenant-Id": hint["id"]}
            for period in ("mes", "anio"):
                response = http.get("/api/estadisticas", headers=headers,
                                    params={"gym_id": hint["id"], "tenant_id": hint["id"],
                                            "periodo": period})
                facts(response, True, expected)


@pytest.mark.parametrize("factory", FACTORIES)
def test_current_rows_are_recomputed_after_retirement_and_restoration(factory, test_gym_user):
    from web.database.engine import get_engine
    from web.database.models import Cliente, PlanGenerado

    identifier = client_row(test_gym_user["id"])
    plan = plan_row(test_gym_user["id"], identifier)
    transitions = [(None, True, None, True, True),
                   (None, False, None, False, False),
                   (datetime.now(UTC), True, None, False, False),
                   (None, True, datetime.now(UTC), True, False),
                   (None, True, None, True, True)]
    app = importlib.import_module(factory).create_app()
    for deleted_client, active, deleted_plan, expected_client, expected_plan in transitions:
        with Session(get_engine()) as db:
            row = db.query(Cliente).filter_by(id_cliente=identifier).one()
            row.deleted_at, row.activo = deleted_client, active
            db.get(PlanGenerado, plan).deleted_at = deleted_plan
            db.commit()
        # A fresh client/request cannot resume a browser-local completion flag.
        with TestClient(app) as http, observed_reads():
            facts(http.get("/api/estadisticas", headers=test_gym_user["auth_headers"]),
                  expected_client, expected_plan)


@pytest.mark.parametrize("factory", FACTORIES)
def test_statistics_failure_remains_unknown_and_does_not_echo_the_query(factory, test_gym_user,
                                                                       monkeypatch):
    from web.database import repository

    marker = "SYNTHETIC-PRIVATE-QUERY-DETAIL@example.invalid"

    def unavailable(*args, **kwargs):
        raise RuntimeError(marker)

    monkeypatch.setattr(repository, "_onboarding_facts", unavailable)
    with TestClient(importlib.import_module(factory).create_app(),
                    raise_server_exceptions=False) as http, observed_reads():
        response = http.get("/api/estadisticas", headers=test_gym_user["auth_headers"])
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "statistics_unavailable"
    assert marker not in response.text
    assert "onboarding" not in response.json()


@pytest.mark.parametrize("factory", FACTORIES)
@pytest.mark.parametrize("credential", ["missing", "revoked"])
def test_unavailable_authority_never_reaches_the_preparation_port(factory, credential,
                                                                test_gym_user, monkeypatch):
    from web.database import repository
    from web.database.engine import get_engine
    from web.database.models import Usuario

    called = []
    monkeypatch.setattr(repository, "_onboarding_facts", lambda *args: called.append(True))
    if credential == "revoked":
        with Session(get_engine()) as db:
            db.get(Usuario, test_gym_user["id"]).session_version += 1
            db.commit()
    with TestClient(importlib.import_module(factory).create_app(),
                    raise_server_exceptions=False) as http:
        response = http.get("/api/estadisticas", headers=(
            test_gym_user["auth_headers"] if credential == "revoked" else {}))
    assert response.status_code == 401
    assert not called
    assert "onboarding" not in response.json()


def test_preparation_port_is_exactly_two_selects_in_a_clean_readonly_session(test_gym_user):
    from web.database import repository
    from web.database.engine import SessionLocal

    plan_row(test_gym_user["id"], client_row(test_gym_user["id"]))
    with SessionLocal() as db, observed_reads() as statements:
        value = repository._onboarding_facts(db, test_gym_user["id"])
        assert value == {"client_registered": True, "plan_saved": True}
        assert not db.new and not db.dirty and not db.deleted
    assert statements == ["SELECT", "SELECT"]

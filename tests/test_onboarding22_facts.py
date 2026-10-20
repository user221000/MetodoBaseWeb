"""Real HTTP/SQL preparation facts; SQLite here does not establish PG RLS.

The backend reports only two booleans. Export, delivery, clinical review and
human activation measurements are deliberately outside these facts.
"""
from datetime import datetime, timedelta, timezone
import importlib
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session


FACTORIES = ["web.main_web", "api.app"]


def seed(owner, *, foreign=False, inactive=False, deleted_client=False,
         deleted_plan=False, crossed=False):
    from web.database.engine import get_engine
    from web.database.models import Cliente, PlanGenerado, Usuario, UserRole

    now = datetime.now(timezone.utc)
    gym = str(uuid.uuid4()) if foreign or crossed else owner["id"]
    client_id = str(uuid.uuid4())
    with Session(get_engine()) as db:
        if gym != owner["id"]:
            db.add(Usuario(id=gym, email=f"{gym}@example.invalid", nombre="Synthetic other gym",
                           password_hash="not-a-login", tipo="gym", activo=True,
                           role=UserRole.OWNER, session_version=0))
            db.commit()
        db.add(Cliente(id_cliente=client_id, gym_id=gym, nombre="Synthetic onboarding client",
                       activo=not inactive, deleted_at=now if deleted_client else None))
        db.commit()
        db.add(PlanGenerado(id_cliente=client_id, gym_id=owner["id"] if crossed else gym,
                            fecha_generacion=now-timedelta(days=90), plan_json="{}",
                            deleted_at=now if deleted_plan else None))
        db.commit()


@pytest.mark.parametrize("factory", FACTORIES)
@pytest.mark.parametrize("case", ["empty", "foreign", "crossed"])
def test_other_gym_rows_and_legacy_crossed_associations_prove_no_step(factory, case, test_gym_user):
    if case != "empty":
        seed(test_gym_user, foreign=case == "foreign", crossed=case == "crossed")
    with TestClient(importlib.import_module(factory).create_app(), raise_server_exceptions=False) as client:
        response = client.get("/api/estadisticas", headers=test_gym_user["auth_headers"])
    assert response.status_code == 200
    assert response.json()["onboarding"] == {"client_registered": False, "plan_saved": False}


@pytest.mark.parametrize("factory", FACTORIES)
def test_saved_plan_resumes_in_another_request_outside_the_selected_period(factory, test_gym_user):
    seed(test_gym_user)
    app = importlib.import_module(factory).create_app()
    for period in ["semana", "mes", "anio"]:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/estadisticas", params={"periodo": period},
                                  headers=test_gym_user["auth_headers"])
        assert response.status_code == 200
        body = response.json()
        assert body["onboarding"] == {"client_registered": True, "plan_saved": True}
        assert set(body["onboarding"]) == {"client_registered", "plan_saved"}
        assert all(type(v) is bool for v in body["onboarding"].values())
        assert body["planes_periodo"] == (1 if period == "anio" else 0)


@pytest.mark.parametrize("factory", FACTORIES)
@pytest.mark.parametrize("case", ["inactive", "deleted_client", "deleted_plan"])
def test_retired_rows_do_not_resume_a_current_preparation_step(factory, case, test_gym_user):
    seed(test_gym_user, **{case: True})
    with TestClient(importlib.import_module(factory).create_app(), raise_server_exceptions=False) as client:
        response = client.get("/api/estadisticas", headers=test_gym_user["auth_headers"])
    assert response.status_code == 200
    assert response.json()["onboarding"] == {
        "client_registered": case == "deleted_plan", "plan_saved": False,
    }


@pytest.mark.parametrize("factory", FACTORIES)
def test_consulting_preparation_never_writes_or_returns_delivery_authority(factory, test_gym_user):
    from web.database.engine import get_engine

    seed(test_gym_user)
    verbs = []

    def observe(conn, cursor, statement, parameters, context, executemany):
        verbs.append(statement.lstrip().split(None, 1)[0].upper())

    with TestClient(importlib.import_module(factory).create_app(), raise_server_exceptions=False) as client:
        event.listen(get_engine(), "before_cursor_execute", observe)
        try:
            response = client.get("/api/estadisticas", headers=test_gym_user["auth_headers"])
        finally:
            event.remove(get_engine(), "before_cursor_execute", observe)
    assert response.status_code == 200
    assert verbs and not {"INSERT", "UPDATE", "DELETE", "REPLACE"}.intersection(verbs)
    assert response.json()["onboarding"] == {"client_registered": True, "plan_saved": True}

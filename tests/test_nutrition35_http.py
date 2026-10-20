"""Real auth, persistence, quota and PDF publication boundaries in both factories."""
import importlib
import uuid

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

from tests.followup34_fixtures import owned_database
from tests.followup34_http import PASSWORD, followup_http
from tests.integration_schema_migrations import run_migration
from tests.test_nutrition35_profile_contract import declaration
from web.database.models import (
    Cliente,
    GenerationReservation,
    GymGenerationReservation,
    PlanGenerado,
    StoredObject,
    UserSubscription,
)
from web.services.nutrition_profiles import capture_profile, encode_declaration

VALID = {"edad": 30, "peso_kg": 75, "estatura_cm": 175, "grasa_corporal_pct": 20,
         "nivel_actividad": "moderada", "objetivo": "mantenimiento", "sexo": "M"}


@pytest.fixture(scope="module")
def followup_db(tmp_path_factory):
    # Reuse the real34 identity/MFA fixture body; only its own DB target is35.
    with owned_database("sqlite", tmp_path_factory.mktemp("nutrition35-http")) as (url, engine):
        run_migration(url, "db_bootstrap.py", "--revision", "20261020_nutrition_profile")

        @event.listens_for(engine, "connect")
        def foreign_keys(connection, record):
            connection.execute("PRAGMA foreign_keys=ON")

        engine.dispose()
        yield engine


@pytest.fixture(params=["web.main_web"])
def personal35_http(followup_db, request, monkeypatch):
    # API intentionally exposes only reviewed personal history GET. The SaaS
    # factory owns profile/generation; do not silently widen API's surface.
    yield from followup_http.__wrapped__(followup_db, request, monkeypatch)


def _put(case, **changes):
    return case["raw"].put("/api/clientes/"+case["profile"], json=changes)


def _new_plan(case):
    return case["raw"].post("/api/generar-plan", json={"id_cliente": case["profile"],
        "plan_numero": 1, "tipo_plan": "menu_fijo"}, headers={"Idempotency-Key": str(uuid.uuid4())})


def _snapshot(case):
    with Session(case["admin"]) as db:
        client = db.query(Cliente).filter_by(id_cliente=case["profile"], gym_id=case["user"]).one()
        return capture_profile(client)


def test_gym_declaration_survives_omitted_and_null_edits_and_reads_are_private(followup_http):
    c = followup_http
    payload = declaration(reported=True)
    assert _put(c, **VALID, restricciones_nutricionales=payload).status_code == 200
    assert _put(c, peso_kg=76).status_code == 200
    assert _put(c, restricciones_nutricionales=None).status_code == 200
    assert _snapshot(c).declaration_payload() == payload
    response = c["raw"].get("/api/clientes/"+c["profile"])
    assert response.status_code == 200
    assert response.json()["restricciones_nutricionales"] == payload
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"


@pytest.mark.parametrize("declared", ["allergy", "review"])
def test_declared_profile_is_rejected_before_any_quota_CPU_or_object(followup_http, declared, monkeypatch):
    c = followup_http
    payload = declaration(reported=declared == "allergy", review=declared == "review")
    assert _put(c, **VALID, restricciones_nutricionales=payload).status_code == 200
    module = importlib.import_module("api.routes.planes" if c["factory_name"] == "api.app" else "web.routes.planes")

    def forbidden(*args, **kwargs):
        raise AssertionError("The declared profile reached CPU")

    monkeypatch.setattr(module, "_generar_plan_sync", forbidden)
    response = _new_plan(c)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "nutrition_professional_review_required"
    with Session(c["admin"]) as db:
        assert db.query(GymGenerationReservation).filter_by(gym_id=c["user"]).count() == 0
        assert db.query(PlanGenerado).filter_by(gym_id=c["user"]).count() == 0
        assert db.query(StoredObject).filter_by(gym_id=c["user"]).count() == 0


def test_worker_rechecks_a_new_declaration_and_compensates_the_reservation(followup_http, monkeypatch):
    c = followup_http
    assert _put(c, **VALID).status_code == 200
    module = importlib.import_module("api.routes.planes" if c["factory_name"] == "api.app" else "web.routes.planes")
    original = module._generar_plan_sync

    def changed_before_worker(*args, **kwargs):
        with Session(c["admin"]) as db:
            client = db.query(Cliente).filter_by(id_cliente=c["profile"], gym_id=c["user"]).one()
            client.nutrition_restrictions_json = encode_declaration(declaration(review=True))
            db.commit()
        return original(*args, **kwargs)

    monkeypatch.setattr(module, "_generar_plan_sync", changed_before_worker)
    response = _new_plan(c)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "nutrition_professional_review_required"
    with Session(c["admin"]) as db:
        reservation = db.query(GymGenerationReservation).filter_by(gym_id=c["user"]).one()
        assert reservation.status == "released" and reservation.persisted_at is None
        assert db.query(PlanGenerado).filter_by(gym_id=c["user"]).count() == 0
        assert db.query(StoredObject).filter_by(gym_id=c["user"]).count() == 0


def test_real_PDF_cannot_become_ready_after_restrictions_change(followup_http, monkeypatch):
    from web.services import private_objects
    from web.storage.objects import ObjectUnavailable

    c = followup_http
    assert _put(c, **VALID).status_code == 200
    original = private_objects.publish_pending_object

    def changed_after_pending(*args, **kwargs):
        result = original(*args, **kwargs)
        with Session(c["admin"]) as db:
            client = db.query(Cliente).filter_by(id_cliente=c["profile"], gym_id=c["user"]).one()
            client.alimentos_excluidos = '["huevo"]'
            db.commit()
        return result

    monkeypatch.setattr(private_objects, "publish_pending_object", changed_after_pending)
    response = _new_plan(c)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "nutrition_restrictions_changed"
    with Session(c["admin"]) as db:
        reservation = db.query(GymGenerationReservation).filter_by(gym_id=c["user"]).one()
        assert reservation.status == "released" and reservation.persisted_at is None
        assert db.query(PlanGenerado).filter_by(gym_id=c["user"]).count() == 0
        pending = db.query(StoredObject).filter_by(gym_id=c["user"]).one()
        assert pending.status == "pending"  # Existing orphan reconciliation owns this durable side effect.
        with pytest.raises(ObjectUnavailable):
            private_objects.read_private_object(db, c["user"], pending.id, "plan_pdf")


def test_invalid_declaration_is_not_echoed_or_saved(followup_http):
    c = followup_http
    payload = declaration(reported=True)
    payload["allergies"]["foods"] = ["SENSITIVE_HEALTH_SENTINEL"]
    before = _snapshot(c).snapshot_digest()
    response = _put(c, restricciones_nutricionales=payload)
    assert response.status_code == 422
    assert "SENSITIVE_HEALTH_SENTINEL" not in response.text
    assert response.json()["detail"]["code"] == "nutrition_profile_invalid_input"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert _snapshot(c).snapshot_digest() == before


def test_independent_personal_profile_preserves_declaration_without_consuming_quota(personal35_http):
    c = personal35_http
    raw = c["raw"]
    email = uuid.uuid4().hex+"@example.invalid"
    registered = raw.post("/api/auth/registro", json={"email": email, "password": PASSWORD,
        "nombre": "Synthetic individual", "tipo": "usuario"})
    assert registered.status_code == 200
    logged = raw.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert logged.status_code == 200
    raw.headers["Authorization"] = "Bearer "+logged.json()["token"]
    me = raw.get("/api/auth/me")
    assert me.status_code == 200
    user_id = me.json()["id"]
    payload = declaration(reported=True)
    assert raw.put("/api/usuario/perfil", json={**VALID, "restricciones_nutricionales": payload}).status_code == 200
    assert raw.put("/api/usuario/perfil", json={"restricciones_nutricionales": None, "peso_kg": 76}).status_code == 200
    assert raw.get("/api/usuario/perfil").json()["restricciones_nutricionales"] == payload
    response = raw.post("/api/usuario/generar-plan", headers={"Idempotency-Key": str(uuid.uuid4())})
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "nutrition_professional_review_required"
    assert raw.get("/api/clientes/"+c["profile"]).status_code in (403, 404)
    with Session(c["admin"]) as db:
        assert db.query(GenerationReservation).filter_by(user_id=user_id).count() == 0
        subscription = db.query(UserSubscription).filter_by(user_id=user_id).one_or_none()
        assert subscription is None or subscription.planes_usados_mes == 0
        assert db.query(PlanGenerado).filter_by(gym_id=user_id).count() == 0

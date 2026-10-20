"""Independent current35 authorization, publication and failure controls."""
import importlib
import uuid

import pytest
from sqlalchemy.orm import Session

from tests import test_nutrition35_http as fixtures
from tests.mfa31_contract_client import MfaContractClient
from web.database.models import Cliente, GymGenerationReservation, PlanGenerado, StoredObject, Usuario, UserRole
from web.services.nutrition_profiles import encode_declaration

followup_db = fixtures.followup_db
followup_http = fixtures.followup_http
SENTINEL = "SYNTHETIC_NUTRITION35_UNEXPECTED_ERROR"


def _private(response):
    assert response.headers.get("cache-control") == "no-store"
    assert response.headers.get("referrer-policy") == "no-referrer"
    assert SENTINEL not in response.text


def _generate(c):
    return c["raw"].post("/api/generar-plan", json={"id_cliente": c["profile"],
        "plan_numero": 1, "tipo_plan": "menu_fijo"}, headers={"Idempotency-Key": str(uuid.uuid4())})


def _no_generation(c):
    with Session(c["admin"]) as db:
        assert db.query(GymGenerationReservation).filter_by(gym_id=c["user"]).count() == 0
        assert db.query(PlanGenerado).filter_by(gym_id=c["user"]).count() == 0
        assert db.query(StoredObject).filter_by(gym_id=c["user"]).count() == 0


def test_real_viewer_can_read_but_cannot_reset_declaration_or_generate(followup_http):
    c = followup_http
    payload = fixtures.declaration(reported=True)
    assert c["raw"].put("/api/clientes/" + c["profile"], json={
        **fixtures.VALID, "restricciones_nutricionales": payload}).status_code == 200
    with Session(c["admin"]) as db:
        db.get(Usuario, c["member"]).role = UserRole.VIEWER
        db.commit()
    MfaContractClient(c["raw"], {"id": c["member"]}, c["factory"], fixtures.PASSWORD).authenticate()
    read = c["raw"].get("/api/clientes/" + c["profile"])
    if c["factory_name"] == "api.app":
        # The legacy API's get_usuario_gym remains OWNER-only for this read.
        assert read.status_code == 403 and "allergies" not in read.text
    else:
        assert read.status_code == 200 and read.json()["restricciones_nutricionales"] == payload
    _private(read)
    for response in [c["raw"].put("/api/clientes/" + c["profile"], json={
        "restricciones_nutricionales": fixtures.declaration()}), _generate(c)]:
        assert response.status_code == 403
        _private(response)
    with Session(c["admin"]) as db:
        row = db.query(Cliente).filter_by(gym_id=c["user"], id_cliente=c["profile"]).one()
        assert row.nutrition_restrictions_json == encode_declaration(payload)
    _no_generation(c)


@pytest.mark.parametrize("invalidation", ["stale_sv", "parent_off"])
def test_current_authority_revocation_denies_health_read_write_and_work(followup_http, invalidation):
    c = followup_http
    if invalidation == "parent_off":
        MfaContractClient(c["raw"], {"id": c["member"]}, c["factory"], fixtures.PASSWORD).authenticate()
    with Session(c["admin"]) as db:
        owner = db.get(Usuario, c["user"])
        if invalidation == "stale_sv":
            owner.session_version += 1
        else:
            owner.activo = False
        db.commit()
    for response in [c["raw"].get("/api/clientes/" + c["profile"]),
        c["raw"].put("/api/clientes/" + c["profile"], json={
            "restricciones_nutricionales": fixtures.declaration()}), _generate(c)]:
        assert response.status_code in {401, 403}
        assert "allergies" not in response.text
        _private(response)
    _no_generation(c)


def test_body_authority_cannot_move_profile_or_alter_account(followup_http):
    c = followup_http
    for authority in ["gym_id", "id_cliente", "role", "team_gym_id", "session_version"]:
        response = c["raw"].put("/api/clientes/" + c["profile"], json={
            authority: SENTINEL, "peso_kg": 77, "restricciones_nutricionales": fixtures.declaration()})
        assert response.status_code == 422
        _private(response)
    with Session(c["admin"]) as db:
        row = db.query(Cliente).filter_by(gym_id=c["user"], id_cliente=c["profile"]).one()
        assert row.peso_kg is None and row.nutrition_restrictions_json is None
        assert db.get(Usuario, c["user"]).role == UserRole.OWNER
    _no_generation(c)


def test_deactivated_profile_after_pending_PDF_never_becomes_readable(followup_http, monkeypatch):
    from web.services import private_objects
    from web.storage.objects import ObjectUnavailable

    c = followup_http
    assert c["raw"].put("/api/clientes/" + c["profile"], json=fixtures.VALID).status_code == 200
    original = private_objects.publish_pending_object
    observed = []

    def deactivate(*args, **kwargs):
        descriptor = original(*args, **kwargs)
        observed.append(descriptor.id)
        with Session(c["admin"]) as db:
            row = db.query(Cliente).filter_by(gym_id=c["user"], id_cliente=c["profile"]).one()
            row.activo = False
            db.commit()
        return descriptor

    monkeypatch.setattr(private_objects, "publish_pending_object", deactivate)
    response = _generate(c)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "nutrition_restrictions_changed"
    _private(response)
    assert len(observed) == 1
    with Session(c["admin"]) as db:
        assert db.query(PlanGenerado).filter_by(gym_id=c["user"]).count() == 0
        reservation = db.query(GymGenerationReservation).filter_by(gym_id=c["user"]).one()
        assert reservation.status == "released" and reservation.persisted_at is None
        pending = db.query(StoredObject).filter_by(gym_id=c["user"]).one()
        assert pending.id == observed[0] and pending.status == "pending"
        with pytest.raises(ObjectUnavailable):
            private_objects.read_private_object(db, c["user"], pending.id, "plan_pdf")
    unavailable = c["raw"].get("/api/descargar-pdf/" + c["profile"])
    assert unavailable.status_code == 404
    _private(unavailable)


def test_unexpected_profile_failure_keeps_private_error_headers(followup_http, monkeypatch):
    c = followup_http
    module = importlib.import_module("api.routes.clientes" if c["factory_name"] == "api.app" else "web.routes.clientes")

    def failed(*args, **kwargs):
        raise RuntimeError(SENTINEL)

    monkeypatch.setattr(module.repo, "obtener_cliente", failed)
    response = c["raw"].get("/api/clientes/" + c["profile"])
    assert response.status_code == 500
    assert SENTINEL not in response.text
    _private(response)

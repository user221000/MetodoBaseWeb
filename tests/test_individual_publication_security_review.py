"""Independent legacy association negatives; isolated SQLite, no worker/provider."""
from datetime import datetime, timezone
import json

from fastapi import HTTPException
import pytest

from tests.test_billing_integrity import billing_case  # noqa: F401


def completed_legacy_with_foreign_client(factory, owner):
    """A legacy FK can exist without its client's tenant matching the Plan row.

    This fixture is deliberately inconsistent, not a claimed exploit of the
    new repository. Existing single-column FKs permit this historical state.
    """
    from web.database.models import Cliente, GenerationReservation, PlanGenerado, Usuario, UserSubscription

    with factory() as db:
        db.add(Usuario(id="synthetic-foreign-person", email="foreign@example.invalid", password_hash="unused",
                       nombre="Foreign", tipo="usuario", activo=True))
        db.add(Cliente(id_cliente="synthetic-foreign-profile", gym_id="synthetic-foreign-person",
                       nombre="Foreign profile", edad=32, peso_kg=70, estatura_cm=170,
                       objetivo="mantenimiento", nivel_actividad="moderada", activo=True))
        db.flush()
        plan = PlanGenerado(gym_id=owner, id_cliente="synthetic-foreign-profile",
                            plan_json=json.dumps({"synthetic_private_other_client": "must-not-be-returned"}))
        db.add(plan)
        db.flush()
        reservation = GenerationReservation(user_id=owner, request_key="synthetic-legacy-mixed-client",
            period="2026-10", status="completed", plan_id=plan.id, publication_protocol=0)
        db.add(reservation)
        db.add(UserSubscription(user_id=owner, plan="starter", max_planes_mes=1, planes_usados_mes=1,
                                mes_actual="2026-10", status="active"))
        db.commit()
        return reservation.id, plan.id


def test_legacy_replay_does_not_return_a_plan_whose_client_belongs_to_another_subject(billing_case, monkeypatch):
    client, factory, principal = billing_case
    identity, _ = completed_legacy_with_foreign_client(factory, principal["id"])
    from web.routes import planes
    monkeypatch.setattr(planes, "_generar_plan_sync", lambda *args, **kwargs: pytest.fail("Replay must not generate"))
    response = client.post("/api/usuario/generar-plan", headers={"Idempotency-Key": "synthetic-legacy-mixed-client"})
    assert "synthetic_private_other_client" not in response.text
    assert response.status_code in (404, 409, 503)
    from web.database.models import GenerationReservation, UserSubscription
    with factory() as db:
        assert db.get(GenerationReservation, identity).status == "completed"
        assert db.query(UserSubscription).filter_by(user_id=principal["id"]).one().planes_usados_mes == 1


def test_success_verifier_rejects_a_mixed_client_legacy_association_without_refunding(billing_case):
    _, factory, principal = billing_case
    identity, plan = completed_legacy_with_foreign_client(factory, principal["id"])
    from web.services.generation_quota import finish_generation
    with factory() as db:
        with pytest.raises(HTTPException) as unavailable:
            finish_generation(db, identity, principal["id"], plan, success=True)
        assert unavailable.value.status_code == 503


def test_foreign_existing_account_cannot_compensate_another_subjects_reservation(billing_case):
    from web.database.models import GenerationReservation, Usuario, UserSubscription
    from web.services.generation_quota import finish_generation, reserve_generation

    _, factory, principal = billing_case
    with factory() as db:
        identity = reserve_generation(db, principal["id"], "synthetic-owned-reservation").id
        db.add(Usuario(id="synthetic-other-caller", email="other-caller@example.invalid", password_hash="unused",
                       nombre="Other", tipo="usuario", activo=True))
        db.add(UserSubscription(user_id="synthetic-other-caller", plan="starter", max_planes_mes=1,
                               planes_usados_mes=1, mes_actual="2026-10", status="active"))
        db.commit()
        with pytest.raises(HTTPException) as unavailable:
            finish_generation(db, identity, "synthetic-other-caller", None, success=False)
        assert unavailable.value.status_code == 503
        db.rollback()
    with factory() as db:
        assert db.get(GenerationReservation, identity).status == "reserved"
        assert db.query(UserSubscription).filter_by(user_id=principal["id"]).one().planes_usados_mes == 1
        assert db.query(UserSubscription).filter_by(user_id="synthetic-other-caller").one().planes_usados_mes == 1

"""Independent malformed-envelope privacy probes over real authenticated HTTP."""
import pytest
from sqlalchemy.orm import Session

from tests.test_nutrition35_http import followup_db, followup_http
from tests.test_nutrition35_profile_contract import declaration
from web.database.models import Cliente, GymGenerationReservation, PlanGenerado

SENTINEL = "SYNTHETIC_NUTRITION35_PRIVATE_INPUT"


@pytest.mark.parametrize("method", ["POST", "PUT"])
def test_nonobject_declaration_envelope_is_not_reflected(followup_http, method):
    c = followup_http
    value = declaration(reported=True)
    value["allergies"]["foods"] = [SENTINEL]
    path = "/api/clientes" + ("/" + c["profile"] if method == "PUT" else "")
    response = c["raw"].request(method, path, json=[{"restricciones_nutricionales": value}])
    assert response.status_code == 422
    assert SENTINEL not in response.text, "A rejected envelope must not reflect declared health input"
    assert response.headers.get("cache-control") == "no-store"
    assert response.headers.get("referrer-policy") == "no-referrer"
    with Session(c["admin"]) as db:
        row = db.query(Cliente).filter_by(gym_id=c["user"], id_cliente=c["profile"]).one()
        assert row.nutrition_restrictions_json is None
        assert db.query(Cliente).filter_by(gym_id=c["user"]).count() == 1
        assert db.query(GymGenerationReservation).filter_by(gym_id=c["user"]).count() == 0
        assert db.query(PlanGenerado).filter_by(gym_id=c["user"]).count() == 0


def test_object_declaration_validation_control_is_private(followup_http):
    c = followup_http
    response = c["raw"].put("/api/clientes/" + c["profile"], json={
        "restricciones_nutricionales": {"private": SENTINEL}})
    assert response.status_code == 422
    assert SENTINEL not in response.text
    assert response.headers.get("cache-control") == "no-store"
    assert response.headers.get("referrer-policy") == "no-referrer"

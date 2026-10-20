"""Progressive profile updates must work without manufacturing missing facts."""
import pytest

from tests import test_nutrition35_http as http35

VALID = http35.VALID
followup_db = http35.followup_db
followup_http = http35.followup_http


@pytest.mark.parametrize("changes", [{"peso_kg": 76}, {"nivel_actividad": "moderada"}, VALID],
    ids=["weight-only", "activity-only", "complete-profile"])
def test_partial_profile_does_not_require_other_fields_or_invent_them(followup_http, changes):
    case = followup_http
    path = "/api/clientes/"+case["profile"]
    before = case["raw"].get(path)
    assert before.status_code == 200
    assert all(before.json()[field] is None for field in VALID)
    saved = case["raw"].put(path, json=changes)
    assert saved.status_code == 200
    after = case["raw"].get(path)
    assert after.status_code == 200
    assert all(after.json()[field] == changes.get(field) for field in VALID)
    assert after.json()["restricciones_nutricionales"] == before.json()["restricciones_nutricionales"]
    assert after.headers["cache-control"] == "no-store"
    assert after.headers["referrer-policy"] == "no-referrer"


def test_invalid_partial_update_never_applies_the_other_submitted_fields(followup_http):
    case = followup_http
    path = "/api/clientes/"+case["profile"]
    before = case["raw"].get(path)
    assert before.status_code == 200
    result = case["raw"].put(path, json={"peso_kg": -1, "objetivo": "mantenimiento"})
    assert result.status_code == 422
    after = case["raw"].get(path)
    assert after.status_code == 200
    assert after.json() == before.json()

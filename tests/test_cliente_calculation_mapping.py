"""Web DTO mapping preserves declared inputs and marks the legacy estimate."""
from copy import deepcopy
from dataclasses import fields
import sys
from types import ModuleType

import pytest

from api.dependencies import build_cliente_from_dict
from core.modelos import ClienteEvaluacion


BASE = {"nombre": "MapperPrivateName", "telefono": "5550009191", "edad": 30,
        "peso_kg": 80, "estatura_cm": 175, "nivel_actividad": "moderada", "objetivo": "deficit"}


@pytest.fixture(autouse=True)
def local_catalog_without_database(monkeypatch):
    """The real formula runs; catalog import cannot seed or open any database."""
    catalog = ModuleType("src.alimentos_base")
    catalog.ALIMENTOS_BASE = {
        "huevo": {"proteina": 13, "carbs": 1, "grasa": 11, "kcal": 155, "meal_idx": [0, 1]},
    }
    monkeypatch.setitem(sys.modules, "src.alimentos_base", catalog)


@pytest.mark.parametrize("extra", [{}, {"grasa_corporal_pct": None}])
def test_missing_body_fat_retains_twenty_policy_and_marks_estimate(extra):
    client = build_cliente_from_dict({**BASE, **extra})
    assert client.grasa_corporal_pct == 20.0
    assert client.grasa_corporal_estimada is True


@pytest.mark.parametrize("value", [20, 20.0, "20", 15.0])
def test_reported_value_is_not_mislabeled_as_an_estimate(value):
    client = build_cliente_from_dict({**BASE, "grasa_corporal_pct": value, "grasa_corporal_estimada": True})
    assert client.grasa_corporal_pct == float(value)
    assert client.grasa_corporal_estimada is False


@pytest.mark.parametrize("value", [0, 0.0, "0", False, -1, 61, "", float("nan"), float("inf"), float("-inf")])
def test_invalid_present_body_fat_is_rejected_before_running_motor(value, monkeypatch):
    from core.motor_nutricional import MotorNutricional

    called = []
    monkeypatch.setattr(MotorNutricional, "calcular_motor", lambda client: called.append(client))
    with pytest.raises(ValueError):
        build_cliente_from_dict({**BASE, "grasa_corporal_pct": value})
    assert called == []


@pytest.mark.parametrize("raw,normalized", [(None, None), ("", None), ("  ", None),
    ("m", "M"), (" Masculino ", "M"), ("f", "F"), (" Femenino ", "F"), ("otro", "Otro")])
def test_sex_is_normalized_and_retained(raw, normalized):
    client = build_cliente_from_dict({**BASE, "sexo": raw})
    assert client.sexo == normalized


def test_unknown_sex_uses_existing_validator():
    with pytest.raises(ValueError, match="Sexo"):
        build_cliente_from_dict({**BASE, "sexo": "unsupported"})


@pytest.mark.parametrize("template", ["general", "menu_fijo", "opciones"])
def test_existing_template_type_is_preserved(template):
    assert build_cliente_from_dict({**BASE, "plantilla_tipo": template}).plantilla_tipo == template


@pytest.mark.parametrize("extra", [{}, {"plantilla_tipo": None}])
def test_absent_template_retains_general_default(extra):
    assert build_cliente_from_dict({**BASE, **extra}).plantilla_tipo == "general"


def test_current_katch_formula_and_outputs_are_unchanged_for_control_case():
    estimated = build_cliente_from_dict({**BASE, "sexo": "F", "plantilla_tipo": "opciones"})
    reported = build_cliente_from_dict({**BASE, "sexo": "M", "grasa_corporal_pct": 20})
    expected = {"factor_actividad": 1.55, "masa_magra": 64.0, "tmb": 1752.4,
                "get_total": 2716.22, "kcal_objetivo": 2308.787,
                "proteina_g": 144.0, "grasa_g": 64.0, "carbs_g": 289.19675,
                "kcal_proteína": 576.0, "kcal_grasa": 576.0, "kcal_carbs": 1156.787}
    for field, value in expected.items():
        assert getattr(estimated, field) == pytest.approx(value)
        assert getattr(reported, field) == getattr(estimated, field)
    assert estimated.grasa_corporal_estimada is True
    assert reported.grasa_corporal_estimada is False


def test_new_dto_fields_are_appended_and_legacy_positional_arguments_still_bind():
    old_names = ["nombre", "telefono", "edad", "peso_kg", "estatura_cm", "grasa_corporal_pct",
        "nivel_actividad", "objetivo", "plantilla_tipo", "id_cliente", "factor_actividad",
        "fecha_creacion", "validado", "errores", "masa_magra", "tmb", "get_total", "kcal_objetivo",
        "proteina_g", "grasa_g", "carbs_g", "kcal_proteína", "kcal_grasa", "kcal_carbs", "nutrition_restrictions"]
    names = [field.name for field in fields(ClienteEvaluacion)]
    assert names == old_names + ["sexo", "grasa_corporal_estimada"]
    legacy = ClienteEvaluacion("Synthetic", None, 30, 80, 175, 20, "moderada", "deficit", "opciones",
        "LEGACY", 1.55, "2026-10-31", False, [], None, None, None, None, None, None, None, None, None, None, None)
    assert legacy.id_cliente == "LEGACY" and legacy.plantilla_tipo == "opciones"
    assert legacy.nutrition_restrictions is None
    assert legacy.sexo is None and legacy.grasa_corporal_estimada is False


def test_input_dict_is_unchanged_and_no_new_sensitive_diagnostics(caplog):
    data = {**BASE, "sexo": "F", "grasa_corporal_pct": None, "plantilla_tipo": "opciones"}
    before = deepcopy(data)
    caplog.clear()
    client = build_cliente_from_dict(data)
    assert data == before
    assert "MapperPrivateName" not in caplog.text and "5550009191" not in caplog.text
    assert "sexo=" not in repr(client) and "grasa_corporal_estimada" not in repr(client)
    by_name = {field.name: field for field in fields(ClienteEvaluacion)}
    assert by_name["sexo"].repr is False and by_name["grasa_corporal_estimada"].repr is False

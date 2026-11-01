"""Bundled source integrity and attribution after catalog customization."""
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from src import alimentos_catalogo_usda as usda


@pytest.fixture
def records():
    return json.loads(usda.USDA_DATA_FILE.read_bytes())


def test_frozen_source_bytes_complete_values_and_nine_non_menu_roles(records):
    assert hashlib.sha256(usda.USDA_DATA_FILE.read_bytes()).hexdigest() == usda.USDA_DATA_SHA256
    catalog = usda.load_usda_catalog()
    assert len(catalog["foods"]) == 70
    assert {key: len(items) for key, items in catalog["categories"].items()} == {
        "proteina": 14, "carbs": 14, "grasa": 14, "verdura": 14, "fruta": 14,
    }
    assert sum(item["auto_generation"] for item in catalog["metadata"].values()) == 61
    for record in records:
        row = catalog["foods"][record["id"]]
        assert set(row) == {"proteina", "carbs", "grasa", "kcal", "meal_idx"}
        for field, (nid, _number, unit) in usda._NUTRIENTS.items():
            nutrient = next(n for n in record["nutrients_source"] if n["nutrient"]["id"] == nid)
            assert row[field] == nutrient["amount"]
            assert nutrient["nutrient"]["unitName"].lower() == unit
        assert row["meal_idx"] and all(type(meal) is int and 0 <= meal <= 3 for meal in row["meal_idx"])
        assert catalog["limits"][record["id"]] > 0
        assert catalog["equivalences"][record["id"]].startswith("Pesar en gramos")
        assert catalog["metadata"][record["id"]]["editorial"]["provider"] == "MetodoBase"


def test_runtime_append_preserves_all_legacy_profiles_categories_and_defaults():
    from src import alimentos_seed as original
    from src import alimentos_seed_runtime as runtime

    assert len(runtime.ALIMENTOS_BASE_SEED) == 171
    assert len(runtime.ALIMENTOS_BASE_EXTRA) == 16
    for food_id, row in {**original.ALIMENTOS_BASE_SEED, **runtime.ALIMENTOS_BASE_EXTRA}.items():
        assert runtime.ALIMENTOS_BASE_SEED[food_id] == row
    for category, items in original.CATEGORIAS_SEED.items():
        assert runtime.CATEGORIAS_SEED[category][:len(items)] == items
    for food_id, value in {**original.LIMITES_ALIMENTOS_SEED, **runtime.LIMITES_ALIMENTOS_EXTRA}.items():
        assert runtime.LIMITES_ALIMENTOS_SEED[food_id] == value
    for food_id, value in {**original.EQUIVALENCIAS_PRACTICAS_SEED, **runtime.EQUIVALENCIAS_PRACTICAS_EXTRA}.items():
        assert runtime.EQUIVALENCIAS_PRACTICAS_SEED[food_id] == value


def test_new_vegetables_are_available_at_breakfast_but_condiments_stay_blocked():
    catalog = usda.load_usda_catalog()
    vegetables = catalog["categories"]["verdura"]
    assert len(vegetables) == 14
    for food_id in vegetables:
        assert catalog["foods"][food_id]["meal_idx"] == [0, 1, 2, 3]
        assert catalog["metadata"][food_id]["editorial"]["meal_idx"] == [0, 1, 2, 3]
    menu_foods = [food_id for food_id in vegetables if catalog["metadata"][food_id]["auto_generation"]]
    assert len(menu_foods) == 12
    for food_id in ("chile_serrano_crudo", "chile_jalapeno_crudo"):
        assert food_id in vegetables
        assert catalog["metadata"][food_id]["role"] == "condiment"
        assert catalog["metadata"][food_id]["auto_generation"] is False


def test_whey_is_exact_usda_based_powder_and_not_an_isolate_or_legacy_repair():
    catalog = usda.load_usda_catalog()
    row = catalog["foods"]["proteina_suero_polvo_usda"]
    assert {key: row[key] for key in usda._NUTRIENTS} == {"proteina": 78.1, "carbs": 6.25, "grasa": 1.56, "kcal": 352}
    meta = catalog["metadata"]["proteina_suero_polvo_usda"]
    assert meta["source"]["fdc_id"] == 173180
    assert meta["source"]["description"] == "Beverages, Protein powder whey based"
    assert meta["auto_generation"] is False
    assert "proteina_suero" not in catalog["foods"]


@pytest.mark.parametrize("field", ["proteina", "carbs", "grasa", "kcal"])
def test_each_changed_current_nutrient_loses_usda_attribution(field):
    current = usda.load_usda_catalog()["foods"]
    food_id = "tilapia_cocida_calor_seco"
    current[food_id][field] += .01
    result = usda.metadata_by_id(current)
    assert result[food_id] == {"source": None, "provenance_status": "customized", "auto_generation": False}
    assert result["trucha_arcoiris_cultivo_cocida_calor_seco"]["provenance_status"] == "reference_match"


@pytest.mark.parametrize("bad", [None, {}, {"kcal": 105}, {"proteina": "26", "carbs": 0, "grasa": 2, "kcal": 128}])
def test_malformed_or_missing_current_values_never_inherit_source(bad):
    result = usda.metadata_by_id({"tilapia_cocida_calor_seco": bad})
    assert result["tilapia_cocida_calor_seco"]["source"] is None
    assert result["tilapia_cocida_calor_seco"]["auto_generation"] is False


def test_no_legacy_or_unknown_id_is_attributed_to_usda():
    assert usda.metadata_by_id({"proteina_suero": {}, "private_custom_food": {}}) == {}


def test_sqlite_floats_and_decimal_values_match_but_booleans_do_not():
    current = usda.load_usda_catalog()["foods"]
    food_id = "tilapia_cocida_calor_seco"
    for field in usda._NUTRIENTS:
        current[food_id][field] = Decimal(str(float(current[food_id][field])))
    assert usda.metadata_by_id(current)[food_id]["source"]["fdc_id"] == 175177
    current[food_id]["carbs"] = False
    assert usda.metadata_by_id(current)[food_id]["source"] is None


@pytest.mark.parametrize("key", ["estado", "state"])
def test_explicit_changed_state_loses_attribution(key):
    current = usda.load_usda_catalog()["foods"]
    current["tilapia_cocida_calor_seco"][key] = "crudo"
    assert usda.metadata_by_id(current)["tilapia_cocida_calor_seco"]["source"] is None


def test_editorial_meal_change_does_not_relabel_it_as_usda_advice():
    current = usda.load_usda_catalog()["foods"]
    current["tilapia_cocida_calor_seco"]["meal_idx"] = [0]
    result = usda.metadata_by_id(current)["tilapia_cocida_calor_seco"]
    assert result["source"]["fdc_id"] == 175177
    assert result["editorial"]["provider"] == "MetodoBase"
    assert result["editorial"]["meal_idx"] == [1, 2, 3]


def test_returned_snapshots_cannot_poison_future_catalog_or_attribution():
    first = usda.load_usda_catalog()
    first["foods"]["tilapia_cocida_calor_seco"]["kcal"] = 1
    first["categories"]["proteina"].clear()
    first["metadata"]["tilapia_cocida_calor_seco"]["source"]["fdc_id"] = -1
    second = usda.load_usda_catalog()
    assert second["foods"]["tilapia_cocida_calor_seco"]["kcal"] == 128
    assert len(second["categories"]["proteina"]) == 14
    meta = usda.metadata_by_id(second["foods"])
    meta["tilapia_cocida_calor_seco"]["source"]["fdc_id"] = -1
    assert usda.metadata_by_id(second["foods"])["tilapia_cocida_calor_seco"]["source"]["fdc_id"] == 175177


@pytest.mark.parametrize("bad", [None, True, "1", -1, float("nan"), float("inf")])
def test_bad_reference_amount_is_rejected_not_imputed(records, bad):
    records[0]["proteina"] = bad
    with pytest.raises(usda.USDACatalogError):
        usda._validate_records(records)


@pytest.mark.parametrize("corruption", ["missing_nutrient", "unit", "amount", "source_hash", "basis", "duplicate_id", "auto_role"])
def test_incomplete_or_inconsistent_source_records_fail_closed(records, corruption):
    record = records[0]
    if corruption == "missing_nutrient":
        record["nutrients_source"].pop()
    elif corruption == "unit":
        record["nutrients_source"][0]["nutrient"]["unitName"] = "mg"
    elif corruption == "amount":
        record["nutrients_source"][0]["amount"] += 1
    elif corruption == "source_hash":
        record["source"]["json_artifact_sha256"] = "0" * 64
    elif corruption == "basis":
        record["porcion_base_g"] = 1
    elif corruption == "duplicate_id":
        records[1]["id"] = record["id"]
    elif corruption == "auto_role":
        record["auto_generation"] = True
    with pytest.raises(usda.USDACatalogError):
        usda._validate_records(records)


def test_altered_bundled_bytes_are_rejected_even_if_json_still_valid(tmp_path):
    path = tmp_path / "altered.json"
    path.write_bytes(usda.USDA_DATA_FILE.read_bytes() + b"\n")
    with pytest.raises(usda.USDACatalogError, match="checksum"):
        usda._read_records(path)


def test_import_and_load_need_no_database_or_network_modules():
    script = '''
import builtins
original = builtins.__import__
blocked = ('sqlite3', 'src.alimentos_base', 'src.alimentos_sqlite', 'socket', 'http.client', 'urllib.request', 'requests', 'httpx')
def guarded(name, *args, **kwargs):
    if any(name == item or name.startswith(item + '.') for item in blocked):
        raise AssertionError('Unexpected database/network import: ' + name)
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
from src.alimentos_catalogo_usda import load_usda_catalog, metadata_by_id
catalog = load_usda_catalog()
assert len(catalog['foods']) == len(metadata_by_id(catalog['foods'])) ==70
'''
    completed = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", script],
                               cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=15)
    assert completed.returncode == 0, completed.stderr

"""Local USDA SR Legacy profiles; no database or network access.

Nutrients and source records are exact per100g references. Meal eligibility and
gram limits below are editorial application settings, never USDA recommendations.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re


USDA_DATA_FILE = Path(__file__).with_name("data") / "food_catalog_usda_2018.json"
USDA_DATA_SHA256 = "3ff159929282344c6fbefc9a21b11d1b41b297edd915711b6de5607c2f54091d"
USDA_SOURCE_ZIP_SHA256 = "0fe8ae486a2c8eb42cb96413f058deb51863a46c8fb8eeb4b1fb45006dd338ef"
USDA_SOURCE_JSON_SHA256 = "70d4235ae3a2bdf48a7b9eaa1286a83fa67b6f3270436c9ce8b008213f500129"
USDA_DOWNLOAD_URL = "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_json_2018-04.zip"
_NUTRIENTS = {
    "proteina": (1003, "203", "g"),
    "carbs": (1005, "205", "g"),
    "grasa": (1004, "204", "g"),
    "kcal": (1008, "208", "kcal"),
}
_CATEGORIES = ("proteina", "carbs", "grasa", "verdura", "fruta")
_ROLE_COUNTS = {"menu_food": 61, "condiment": 4, "ingredient_requires_preparation": 4, "protein_powder": 1}

# Editorial availability for meal slots, not dietary advice or USDA data.
_MEALS = {"proteina": (1, 2, 3), "carbs": (0, 1, 2, 3),
          "grasa": (0, 1, 2, 3), "verdura": (0, 1, 2, 3), "fruta": (0, 3)}
_MEAL_OVERRIDES = {
    "proteina_suero_polvo_usda": (0, 3),
    "queso_mozzarella_leche_parcialmente_descremada": (0, 1, 3),
    "queso_fresco_usda": (0, 1, 3),
    "pan_centeno_usda": (0, 3),
    "pan_pita_trigo_integral": (0, 1, 3),
}
# Technical per-item caps in grams of the declared state. These do not convert
# raw/cooked mass and do not imply a household serving or clinical prescription.
_LIMITS_G = {"proteina": 220, "carbs": 220, "grasa": 35, "verdura": 200, "fruta": 200}
_LIMIT_OVERRIDES_G = {
    "proteina_suero_polvo_usda": 40,
    "queso_mozzarella_leche_parcialmente_descremada": 80,
    "queso_fresco_usda": 80,
    "aceite_girasol_linoleico_65": 15,
    "aceite_canola": 15,
    "aceite_soya_ensalada_cocina": 15,
    "aceite_ajonjoli_ensalada_cocina": 15,
    "aceitunas_maduras_enlatadas_pequenas_extragrandes": 80,
    "amaranto_grano_sin_cocer": 70,
    "harina_gruesa_maiz_amarillo_grano_entero": 80,
    "tapioca_perlas_secas": 80,
    "salvado_avena_crudo": 30,
    "chile_serrano_crudo": 15,
    "chile_jalapeno_crudo": 15,
    "limon_amarillo_crudo_sin_cascara": 30,
    "lima_cruda_usda": 30,
    "tamarindo_crudo": 40,
}


class USDACatalogError(ValueError):
    """The bundled reference is incomplete, changed, or internally inconsistent."""


def _number(value) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise USDACatalogError("Invalid USDA nutrient value")
    try:
        result = Decimal(str(value))
        if not result.is_finite() or result < 0:
            raise USDACatalogError("Invalid USDA nutrient value")
        return result
    except (InvalidOperation, ValueError) as exc:
        raise USDACatalogError("Invalid USDA nutrient value") from exc


def _validate_records(records: list[dict]) -> None:
    """Validate identities, completeness, units and copies of original amounts."""
    try:
        if not isinstance(records, list) or len(records) != 70:
            raise USDACatalogError("Expected 70 USDA food profiles")
        ids, fdc_ids = set(), set()
        for record in records:
            food_id = record["id"]
            if not isinstance(food_id, str) or not re.fullmatch(r"[a-z][a-z0-9_]+", food_id) or food_id in ids:
                raise USDACatalogError("Invalid or duplicate USDA food ID")
            ids.add(food_id)
            if record["categoria"] not in _CATEGORIES or record["porcion_base_g"] != 100:
                raise USDACatalogError("Invalid USDA food basis or category")
            if not isinstance(record["estado"], str) or not record["estado"].strip():
                raise USDACatalogError("Missing USDA food state")
            if not isinstance(record["nombre_es"], str) or not record["nombre_es"].strip():
                raise USDACatalogError("Missing USDA food label")
            if type(record["auto_generation"]) is not bool or record["role"] not in _ROLE_COUNTS:
                raise USDACatalogError("Invalid USDA generation role")
            if record["auto_generation"] != (record["role"] == "menu_food"):
                raise USDACatalogError("Non-menu USDA ingredient cannot be generated automatically")
            source = record["source"]
            fdc_id = source["fdc_id"]
            if type(fdc_id) is not int or fdc_id <= 0 or fdc_id in fdc_ids:
                raise USDACatalogError("Invalid or duplicate FDC ID")
            fdc_ids.add(fdc_id)
            if (source["provider"] != "USDA FoodData Central" or source["dataset"] != "SR Legacy"
                    or source["release"] != "2018-04" or source["license"] != "CC0-1.0"
                    or source["url"] != USDA_DOWNLOAD_URL or source["download_url"] != USDA_DOWNLOAD_URL
                    or source["json_artifact_sha256"] != USDA_SOURCE_JSON_SHA256
                    or not source["description"].strip() or not re.fullmatch(r"\d{5}", source["ndb_number"])):
                raise USDACatalogError("Invalid USDA source identity")
            locator = source["record_locator"]
            if (locator["fdcId"] != fdc_id
                    or locator["json_member"] != "FoodData_Central_sr_legacy_food_json_2018-04.json"
                    or not re.fullmatch(r"/SRLegacyFoods/\d+", locator["json_pointer"])):
                raise USDACatalogError("Invalid USDA source locator")
            nutrients = record["nutrients_source"]
            if not isinstance(nutrients, list) or len(nutrients) != 4:
                raise USDACatalogError("Missing USDA nutrient source records")
            for field, (nutrient_id, number, unit) in _NUTRIENTS.items():
                matching = [item for item in nutrients if item["nutrient"]["id"] == nutrient_id]
                if len(matching) != 1:
                    raise USDACatalogError("Missing or duplicate USDA nutrient")
                nutrient = matching[0]
                if (nutrient["nutrient"]["number"] != number
                        or nutrient["nutrient"]["unitName"].lower() != unit
                        or _number(record[field]) != _number(nutrient["amount"])):
                    raise USDACatalogError("USDA nutrient amount or unit mismatch")
        if Counter(item["categoria"] for item in records) != Counter({category:14 for category in _CATEGORIES}):
            raise USDACatalogError("Invalid USDA category coverage")
        if Counter(item["role"] for item in records) != Counter(_ROLE_COUNTS):
            raise USDACatalogError("Invalid USDA role coverage")
    except (KeyError, TypeError, AttributeError) as exc:
        raise USDACatalogError("Malformed USDA reference") from exc


def _read_records(path: Path) -> list[dict]:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != USDA_DATA_SHA256:
        raise USDACatalogError("Bundled USDA reference checksum mismatch")
    try:
        records = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise USDACatalogError("Malformed USDA reference JSON") from exc
    _validate_records(records)
    return records


@lru_cache(maxsize=1)
def _reference_catalog() -> dict:
    records = _read_records(USDA_DATA_FILE)
    result = {"foods": {}, "categories": {key: [] for key in _CATEGORIES},
              "limits": {}, "equivalences": {}, "metadata": {}}
    for record in records:
        food_id, category = record["id"], record["categoria"]
        meals = list(_MEAL_OVERRIDES.get(food_id, _MEALS[category]))
        limit = _LIMIT_OVERRIDES_G.get(food_id, _LIMITS_G[category])
        result["foods"][food_id] = {key: record[key] for key in _NUTRIENTS} | {"meal_idx": meals}
        result["categories"][category].append(food_id)
        result["limits"][food_id] = limit
        result["equivalences"][food_id] = f"Pesar en gramos de porción comestible: {record['estado']}."
        result["metadata"][food_id] = {
            "nombre_es": record["nombre_es"], "categoria": category, "estado": record["estado"],
            "porcion_base_g": 100, "role": record["role"], "auto_generation": record["auto_generation"],
            "source": deepcopy(record["source"]), "nutrients_source": deepcopy(record["nutrients_source"]),
            "energy_diagnostic": deepcopy(record["energy_diagnostic"]),
            "review_notes": deepcopy(record["review_notes"]), "provenance_status": "reference_match",
            "editorial": {"provider": "MetodoBase", "meal_idx": list(meals), "limit_g": limit,
                          "note": "Disponibilidad y límite técnico de la aplicación; no son datos ni recomendaciones USDA."},
        }
    return result


def load_usda_catalog() -> dict:
    """Return owned copies of 70 profiles and their separate source metadata."""
    return deepcopy(_reference_catalog())


def metadata_by_id(current_foods: Mapping) -> dict[str, dict]:
    """Attribute USDA only to rows whose four current amounts exactly match.

    This must receive the catalog actually loaded after SQLite/customization.
    Modified, malformed or state-changed rows have no USDA source attribution and
    are conservatively ineligible for automatic generation by this helper.
    Editorial meal-slot changes alone do not alter nutrient provenance.
    """
    result = {}
    reference = _reference_catalog()
    for food_id, current in current_foods.items():
        if food_id not in reference["foods"]:
            continue
        matches = isinstance(current, Mapping)
        if matches:
            try:
                matches = all(_number(current[field]) == _number(reference["foods"][food_id][field]) for field in _NUTRIENTS)
                for state_key in ("estado", "state"):
                    if state_key in current and current[state_key] != reference["metadata"][food_id]["estado"]:
                        matches = False
            except (KeyError, USDACatalogError):
                matches = False
        if matches:
            result[food_id] = deepcopy(reference["metadata"][food_id])
        else:
            result[food_id] = {"source": None, "provenance_status": "customized", "auto_generation": False}
    return result

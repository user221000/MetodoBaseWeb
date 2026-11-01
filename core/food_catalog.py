"""Immutable request catalog and explicit food-restriction failures.

This domain module receives data; it does not read configuration, persist
records or import HTTP/database/provider adapters. Food IDs are the existing
catalog identifiers, nutrients are per 100 g, and portions remain grams.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any


class FoodRestrictionError(ValueError):
    """A requested restriction cannot be met; generation must not publish."""

    code = "food_restriction_unavailable"


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def validate_catalog_data(foods: Mapping, categories: Mapping) -> None:
    """Validate data shape without changing identifiers or nutrition values.

    Additional categories and metadata are allowed. This is a finite-number
    and reference contract, not a clinical or energy-factor certification.
    It does not require generation groups and has no side effects.
    """
    message = "El catálogo de alimentos no es válido. Revisa los datos con tu profesional."
    if not isinstance(foods, Mapping) or not isinstance(categories, Mapping):
        raise FoodRestrictionError(message)
    for name, nutrients in foods.items():
        if not isinstance(name, str) or not name or not isinstance(nutrients, Mapping):
            raise FoodRestrictionError(message)
        for field in ("proteina", "carbs", "grasa", "kcal"):
            value = nutrients.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise FoodRestrictionError(message)
            try:
                valid = math.isfinite(value) and value >= 0
            except (OverflowError, TypeError):
                valid = False
            if not valid:
                raise FoodRestrictionError(message)
        meals = nutrients.get("meal_idx")
        if "auto_generation" in nutrients and type(nutrients["auto_generation"]) is not bool:
            raise FoodRestrictionError(message)
        if (not isinstance(meals, Sequence) or isinstance(meals, (str, bytes))
                or not meals or any(type(index) is not int or index not in range(4) for index in meals)):
            raise FoodRestrictionError(message)
    for category, names in categories.items():
        if (not isinstance(category, str) or not category or not isinstance(names, Sequence)
                or isinstance(names, (str, bytes))):
            raise FoodRestrictionError(message)
        if any(not isinstance(name, str) or name not in foods for name in names):
            raise FoodRestrictionError(message)


@dataclass(frozen=True)
class FoodCatalog:
    """Deeply immutable foods/categories snapshot owned by one generation.

    ``from_data`` rejects unknown exclusions and empty required categories.
    An unavailable alternative raises ``FoodRestrictionError``; callers must
    compensate reserved quota and preserve the previous published plan.
    """

    alimentos: Mapping[str, Mapping[str, Any]]
    categorias: Mapping[str, tuple[str, ...]]
    excluidos: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        validate_catalog_data(self.alimentos, self.categorias)
        for category in ("proteina", "carbs", "grasa", "verdura"):
            if not self.categorias.get(category):
                raise FoodRestrictionError("No hay alternativas suficientes para respetar tus exclusiones. Revisa la selección con tu profesional.")
        object.__setattr__(self, "alimentos", _freeze(self.alimentos))
        object.__setattr__(self, "categorias", _freeze(self.categorias))

    @classmethod
    def from_data(
        cls,
        foods: Mapping[str, Mapping[str, Any]],
        categories: Mapping[str, Sequence[str]],
        excluded: Sequence[str] | set[str] = (),
    ) -> FoodCatalog:
        # Check source references before exclusion filtering could hide them.
        validate_catalog_data(foods, categories)
        exclusions = frozenset(excluded)
        if exclusions.difference(foods):
            raise FoodRestrictionError("Hay restricciones fuera del catálogo disponible.")
        permitted = {name: nutrients for name, nutrients in foods.items()
                     if name not in exclusions and nutrients.get("auto_generation", True)}
        filtered = {category: tuple(name for name in names if name in permitted) for category, names in categories.items()}
        return cls(permitted, filtered, exclusions)

    def require_candidates(self, names: Sequence[str]) -> list[str]:
        """Return permitted alternatives or fail without restoring exclusions."""
        result = [name for name in names if self._automatic_food(name)]
        if not result:
            raise FoodRestrictionError("No hay alternativas para una de las comidas con estas exclusiones.")
        return result

    def _automatic_food(self, name: str) -> bool:
        return name in self.alimentos and self.alimentos[name].get("auto_generation", True)

    def validate_plan(self, plan: Mapping[str, Any]) -> None:
        """Reject forbidden foods in the final fixed or alternative menu.

        Run after all emergency adjustments and before external effects; a
        selector regression must never leak a forbidden food into a PDF.
        """
        def inspect(value):
            if isinstance(value, Mapping):
                if "alimentos" in value and any(not self._automatic_food(name) for name in value["alimentos"]):
                    raise FoodRestrictionError("El plan no respeta las exclusiones solicitadas.")
                if "alimento" in value and not self._automatic_food(value["alimento"]):
                    raise FoodRestrictionError("El plan no respeta las exclusiones solicitadas.")
                for child in value.values():
                    inspect(child)
            elif isinstance(value, (tuple, list)):
                for child in value:
                    inspect(child)

        inspect(plan)

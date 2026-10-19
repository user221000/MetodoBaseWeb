"""Immutable request catalog and explicit food-restriction failures.

This domain module receives data; it does not read configuration, persist
records or import HTTP/database/provider adapters. Food IDs are the existing
catalog identifiers, nutrients are per 100 g, and portions remain grams.
"""
from __future__ import annotations

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

    @classmethod
    def from_data(
        cls,
        foods: Mapping[str, Mapping[str, Any]],
        categories: Mapping[str, Sequence[str]],
        excluded: Sequence[str] | set[str] = (),
    ) -> FoodCatalog:
        exclusions = frozenset(excluded)
        if exclusions.difference(foods):
            raise FoodRestrictionError("Hay restricciones fuera del catálogo disponible.")
        permitted = {name: nutrients for name, nutrients in foods.items() if name not in exclusions}
        filtered = {category: tuple(name for name in names if name in permitted) for category, names in categories.items()}
        for category in ("proteina", "carbs", "grasa", "verdura"):
            if not filtered.get(category):
                raise FoodRestrictionError("No hay alternativas suficientes para respetar tus exclusiones. Revisa la selección con tu profesional.")
        return cls(_freeze(permitted), _freeze(filtered), exclusions)

    def require_candidates(self, names: Sequence[str]) -> list[str]:
        """Return permitted alternatives or fail without restoring exclusions."""
        result = [name for name in names if name in self.alimentos]
        if not result:
            raise FoodRestrictionError("No hay alternativas para una de las comidas con estas exclusiones.")
        return result

    def validate_plan(self, plan: Mapping[str, Any]) -> None:
        """Reject forbidden foods in the final fixed or alternative menu.

        Run after all emergency adjustments and before external effects; a
        selector regression must never leak a forbidden food into a PDF.
        """
        def inspect(value):
            if isinstance(value, Mapping):
                if "alimentos" in value:
                    if any(name not in self.alimentos for name in value["alimentos"]):
                        raise FoodRestrictionError("El plan no respeta las exclusiones solicitadas.")
                if "alimento" in value and value["alimento"] not in self.alimentos:
                    raise FoodRestrictionError("El plan no respeta las exclusiones solicitadas.")
                for child in value.values():
                    inspect(child)
            elif isinstance(value, (tuple, list)):
                for child in value:
                    inspect(child)

        inspect(plan)

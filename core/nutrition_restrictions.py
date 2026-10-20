"""Structured declarations, separate from clinically validated nutrition rules.

Food identifiers come from the caller's catalog. An allergy declaration or a
request for professional review prevents automated generation: this module has
no validated ingredient/allergen or cross-contact model. Unknown declarations
remain unknown and never become an assertion that a profile is allergy-free.
No role, subscription, note interpretation, persistence or network effects.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from core.food_catalog import FoodCatalog, FoodRestrictionError

_STATUSES = frozenset({"not_reported", "none_reported", "reported"})
MAX_DECLARED_FOODS = 250


class NutritionRestrictionInputError(ValueError):
    """The bounded structured declaration is invalid; do not infer a default."""

    code = "nutrition_restrictions_invalid"


class ProfessionalNutritionReviewRequired(FoodRestrictionError):
    """The available generator cannot validate this declared clinical context."""

    code = "nutrition_professional_review_required"


class NutritionRestrictionsChanged(FoodRestrictionError):
    """A generation's captured restrictions differ from the current profile."""

    code = "nutrition_restrictions_changed"


def _invalid() -> None:
    # Public errors never repeat declared foods or other health information.
    raise NutritionRestrictionInputError("Revisa la declaración de restricciones alimentarias.")


def _food_tuple(value: object, known: Collection[str]) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or len(value) > MAX_DECLARED_FOODS:
        _invalid()
    if any(type(food) is not str or not 0 < len(food) <= 128 or food not in known for food in value):
        _invalid()
    return tuple(sorted(set(value)))


@dataclass(frozen=True, slots=True)
class AllergyDeclaration:
    """User-declared facts only; foods are catalog IDs, never inferred allergens.

    ``other_reported`` records a declaration not expressible by catalog IDs.
    It contains no free text and has the same generation guard as known IDs.
    No supported input can claim a professional approval or clinical clearance.
    """

    status: str = "not_reported"
    foods: tuple[str, ...] = ()
    other_reported: bool = False

    def __post_init__(self) -> None:
        if (type(self.status) is not str or self.status not in _STATUSES
                or type(self.other_reported) is not bool or type(self.foods) is not tuple
                or len(self.foods) > MAX_DECLARED_FOODS
                or any(type(food) is not str or not 0 < len(food) <= 128 for food in self.foods)
                or self.foods != tuple(sorted(set(self.foods)))):
            _invalid()
        if (self.status == "reported") != bool(self.foods or self.other_reported):
            _invalid()

    @classmethod
    def from_payload(cls, value: object, known_foods: Collection[str]) -> AllergyDeclaration:
        """Parse one closed version1 object; null preserves legacy unknown.

        Reject extras, coercion, unknown food IDs and contradictory status.
        ``none_reported`` is a person's declaration, not a diagnosis or guarantee.
        """
        if value is None:
            return cls()
        if (type(value) is not dict or set(value) != {"version", "status", "foods", "other_reported"}
                or type(value["version"]) is not int or value["version"] != 1):
            _invalid()
        return cls(value["status"], _food_tuple(value["foods"], known_foods), value["other_reported"])

    def as_dict(self) -> dict[str, Any]:
        """Return a fresh JSON-compatible declaration, without external state."""
        return {"version": 1, "status": self.status, "foods": list(self.foods),
                "other_reported": self.other_reported}


@dataclass(frozen=True, slots=True)
class NutritionRestrictions:
    """Immutable restrictions captured for one generation and finalization.

    The application must compare the current persisted declaration under its
    authorized client write lock before publishing. The digest is sensitive
    derived profile data; do not send it to analytics or public logs.
    """

    allergies: AllergyDeclaration
    excluded_foods: tuple[str, ...]
    professional_review_requested: bool = False

    def __post_init__(self) -> None:
        if (type(self.allergies) is not AllergyDeclaration
                or type(self.professional_review_requested) is not bool
                or type(self.excluded_foods) is not tuple
                or len(self.excluded_foods) > MAX_DECLARED_FOODS
                or any(type(food) is not str or not 0 < len(food) <= 128 for food in self.excluded_foods)
                or self.excluded_foods != tuple(sorted(set(self.excluded_foods)))):
            _invalid()

    @classmethod
    def from_profile(
        cls, known_foods: Collection[str], *, allergies: object = None,
        excluded_foods: object = (), professional_review_requested: bool = False,
    ) -> NutritionRestrictions:
        """Capture explicit persisted fields; never inspect profile notes."""
        return cls(AllergyDeclaration.from_payload(allergies, known_foods),
                   _food_tuple(excluded_foods, known_foods), professional_review_requested)

    @classmethod
    def from_declaration(
        cls, value: object, known_foods: Collection[str], *, excluded_foods: object = (),
    ) -> NutritionRestrictions:
        """Parse the closed profile declaration without duplicating exclusions.

        A missing legacy declaration remains unknown. An explicit declaration
        requires all version1 fields; neither a clinical approval nor notes are
        accepted. Exclusions retain their existing independent profile field.
        """
        if value is None:
            return cls.from_profile(known_foods, excluded_foods=excluded_foods)
        if (type(value) is not dict
                or set(value) != {"version", "allergies", "professional_review_requested"}
                or type(value["version"]) is not int or value["version"] != 1
                or value["allergies"] is None):
            _invalid()
        return cls.from_profile(
            known_foods, allergies=value["allergies"], excluded_foods=excluded_foods,
            professional_review_requested=value["professional_review_requested"],
        )

    def declaration_payload(self) -> dict[str, Any]:
        """Return fresh declared facts; exclusions have a separate wire field."""
        return {"version": 1, "allergies": self.allergies.as_dict(),
                "professional_review_requested": self.professional_review_requested}

    def require_automated_generation(self) -> None:
        """Fail before quota use, CPU, PDF or publication for declared reviews.

        The caller also enforces this in the worker and before final publication.
        A paid plan or privileged role cannot bypass this domain precondition.
        """
        if self.allergies.status == "reported" or self.professional_review_requested:
            raise ProfessionalNutritionReviewRequired(
                "Este perfil requiere revisión profesional. La generación automática no está disponible."
            )

    def catalog(
        self, foods: Mapping[str, Mapping[str, Any]], categories: Mapping[str, Sequence[str]],
    ) -> FoodCatalog:
        """Build the existing per-request exclusion catalog after the review guard."""
        self.require_automated_generation()
        return FoodCatalog.from_data(foods, categories, self.excluded_foods)

    def snapshot_digest(self) -> str:
        """Fingerprint only the captured restriction facts for in-transaction CAS."""
        body = {"version": 1, "allergies": self.allergies.as_dict(),
                "excluded_foods": self.excluded_foods,
                "professional_review_requested": self.professional_review_requested}
        return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False,
                                         separators=(",", ":")).encode("utf-8")).hexdigest()

    def require_current(self, current: NutritionRestrictions) -> None:
        """Reject stale publication without adopting the newly read restrictions."""
        if type(current) is not NutritionRestrictions or self.snapshot_digest() != current.snapshot_digest():
            raise NutritionRestrictionsChanged(
                "Las restricciones cambiaron. Revisa el perfil antes de preparar otro plan."
            )
        current.require_automated_generation()


def generation_catalog(
    restrictions: object,
    foods: Mapping[str, Mapping[str, Any]],
    categories: Mapping[str, Sequence[str]],
    catalog: FoodCatalog | None = None,
) -> FoodCatalog:
    """Enforce a constructor's declaration before seeds, CPU or filesystem work.

    A supplied catalog cannot bypass a review or restore the client's excluded
    foods. The resulting snapshot preserves the supplied catalog's exclusions
    and any stricter filtering. Legacy clients with no declaration keep the
    existing catalog contract. No caller-owned data is changed.
    """
    if restrictions is not None:
        if type(restrictions) is not NutritionRestrictions:
            _invalid()
        restrictions.require_automated_generation()
        if set(restrictions.excluded_foods).difference(foods):
            _invalid()
    selected = catalog if catalog is not None else FoodCatalog.from_data(foods, categories)
    if restrictions is None or not restrictions.excluded_foods:
        return selected
    exclusions = frozenset(restrictions.excluded_foods)
    filtered = FoodCatalog.from_data(
        selected.alimentos, selected.categorias, exclusions.intersection(selected.alimentos),
    )
    return FoodCatalog(filtered.alimentos, filtered.categorias, selected.excluidos | exclusions)

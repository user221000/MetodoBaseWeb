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

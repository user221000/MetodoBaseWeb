"""Bounded inputs for stateless PPL previews; no identity or mass assignment."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ExerciseId = Annotated[str, Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9-]*$")]
Equipment = Literal["machine", "cable", "dumbbell", "barbell", "bench", "bodyweight"]


class RoutineRequirements(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activity_level: Literal["nula", "leve", "normal", "moderada", "intensa"]
    experience: Literal["inicial", "intermedio", "avanzado"]
    goal: Literal["fuerza_general", "hipertrofia"]
    equipment: list[Equipment] = Field(min_length=1, max_length=6)
    exercises_per_session: Annotated[int, Field(strict=True, ge=6, le=8)] = 6
    days_per_week: Annotated[int, Field(strict=True, ge=3, le=6)] = 3
    variant: Annotated[int, Field(strict=True, ge=0, le=9)] = 0
    excluded_exercises: list[ExerciseId] = Field(default_factory=list, max_length=120)
    session_minutes: Literal[45, 60, 75, 90] = 60
    expected_inventory_revision: Annotated[int | None, Field(strict=True, ge=0, le=2147483647)] = None

    @field_validator("expected_inventory_revision", mode="before")
    @classmethod
    def explicit_revision_is_integer(cls, value):
        if type(value) is not int:
            raise ValueError("Inventory revision must be an integer")
        return value

    @field_validator("equipment", "excluded_exercises")
    @classmethod
    def no_duplicate_values(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("Repeated requirement value")
        return value

    @field_validator("session_minutes", mode="before")
    @classmethod
    def strict_minutes(cls, value):
        if type(value) is not int:
            raise ValueError("Minutes must be an integer")
        return value

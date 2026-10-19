"""Personal diary input values; identity and nutritional totals are server-owned.

R14 preparation: these DTOs are not wired to a route or persistence model yet.
Every mutation replaces one stated value and carries its observed day version.
"""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool

MealName = Literal['desayuno', 'almuerzo', 'comida', 'cena']
OptionIndex = Annotated[int, Field(strict=True, ge=0)]


class MealSelection(BaseModel):
    model_config = ConfigDict(extra='forbid')
    proteinas: OptionIndex | None = None
    carbohidratos: OptionIndex | None = None
    grasas: OptionIndex | None = None
    include_vegetables: StrictBool = False


class DiaryOperation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: int = Field(strict=True, ge=0, le=2147483647)


class WaterOperation(DiaryOperation):
    operation: Literal['water']
    water_ml: int = Field(strict=True, ge=0, le=20000)


class MealOperation(DiaryOperation):
    operation: Literal['meal']
    meal: MealName
    source_plan_id: int = Field(strict=True, gt=0)
    selections: MealSelection


class CompletionOperation(DiaryOperation):
    operation: Literal['completion']
    meal: MealName
    completed: StrictBool


DiaryPatch = Annotated[
    WaterOperation | MealOperation | CompletionOperation,
    Field(discriminator='operation'),
]

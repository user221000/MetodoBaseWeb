"""Personal diary input values; identity and nutritional totals are server-owned.

Mounted diary DTOs for explicit personal mutations, including verified R12
publication consumption. Each change carries its observed personal day version;
source identity, authority and nutritional values are resolved by the service.
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
    include_fixed_menu: StrictBool = False


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


class PublicationMealOperation(DiaryOperation):
    operation: Literal['publication_meal']
    source_kind: Literal['publication']
    link_id: str = Field(min_length=36,max_length=36,pattern=r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
    publication_id: str = Field(min_length=36,max_length=36,pattern=r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
    expected_link_version: int = Field(strict=True,ge=1,le=2147483647)
    expected_publication_version: int = Field(strict=True,ge=1,le=2147483647)
    meal: MealName
    selections: MealSelection


class RemoveMealOperation(DiaryOperation):
    operation: Literal['remove_meal']
    meal: MealName


DiaryPatch = Annotated[
    WaterOperation | MealOperation | CompletionOperation | PublicationMealOperation | RemoveMealOperation,
    Field(discriminator='operation'),
]

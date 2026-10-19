"""Strict self-report and exact-scope consent commands, protocol32.

Numbers are explicitly reported units, never medically verified measurements.
Technical bounds reject the entire request; no truncation or clinical advice.
"""
from datetime import date
import math
import re
from typing import Annotated, Literal

from pydantic import BeforeValidator, BaseModel, ConfigDict, Field, StrictBool, StrictInt, field_validator, model_validator

MAX_VERSION = 2147483647
Version = Annotated[StrictInt, Field(ge=0, le=MAX_VERSION)]


def uuid_text(value):
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", value) is None:
        raise ValueError("Use the exact lowercase UUID")
    return value


def civil_date(value):
    if type(value) is date:return value
    if not isinstance(value,str) or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}",value) is None:
        raise ValueError("Report an explicit ISO civil date, not an epoch")
    return date.fromisoformat(value)


CivilDate=Annotated[date,BeforeValidator(civil_date)]


class Command(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MeasurementValues(Command):
    peso_kg: float | None = None
    grasa_corporal_pct: float | None = None
    masa_magra_kg: float | None = None

    @field_validator("*", mode="before")
    @classmethod
    def finite_numbers(cls, value):
        if value is not None and (type(value) not in {int, float} or not math.isfinite(value)):
            raise ValueError("Use a finite number in the declared unit")
        return value

    @model_validator(mode="after")
    def bounds(self):
        if all(getattr(self, key) is None for key in type(self).model_fields):
            raise ValueError("Report at least one measurement")
        for key, minimum, maximum in (("peso_kg",20,300),("grasa_corporal_pct",3,60),("masa_magra_kg",0,300)):
            value = getattr(self,key)
            if value is not None and (value < minimum or value > maximum or key == "masa_magra_kg" and value == 0):
                raise ValueError("Value exceeds the technical input bound")
        return self


class MeasurementWrite(Command):
    expected_version: Version
    source_profile_id: str
    measured_on: date
    values: MeasurementValues
    _profile = field_validator("source_profile_id")(uuid_text)
    _date = field_validator("measured_on",mode="before")(civil_date)


class MeasurementWithdraw(Command):
    expected_version: Annotated[StrictInt, Field(ge=1, le=MAX_VERSION)]


class Categories(Command):
    weight: StrictBool
    body_fat: StrictBool
    lean_mass: StrictBool
    completion: StrictBool


class ConsentGrant(Command):
    expected_consent_id: str | None
    expected_version: Version
    expected_link_version: Annotated[StrictInt, Field(ge=1, le=MAX_VERSION)]
    event: Literal["grant"]
    protocol: Literal["progress_share_v1"]
    source_profile_id: str | None
    categories: Categories
    from_date: date
    through_date: date | None
    ongoing: StrictBool

    @field_validator("from_date","through_date",mode="before")
    @classmethod
    def dates(cls,value):
        return civil_date(value) if value is not None else None

    @field_validator("expected_consent_id", "source_profile_id")
    @classmethod
    def optional_uuid(cls, value):
        return uuid_text(value) if value is not None else None

    @model_validator(mode="after")
    def scope(self):
        if (self.expected_consent_id is None) != (self.expected_version == 0):
            raise ValueError("Observe the exact consent id and version")
        if not any(self.categories.model_dump().values()):
            raise ValueError("Select explicit categories")
        if (self.categories.weight or self.categories.body_fat or self.categories.lean_mass) and self.source_profile_id is None:
            raise ValueError("Select the personal source profile explicitly")
        if self.ongoing != (self.through_date is None) or self.through_date is not None and self.through_date < self.from_date:
            raise ValueError("Select an explicit date scope")
        return self


class ConsentWithdraw(Command):
    expected_consent_id: str
    expected_version: Annotated[StrictInt, Field(ge=1, le=MAX_VERSION)]
    _consent = field_validator("expected_consent_id")(uuid_text)

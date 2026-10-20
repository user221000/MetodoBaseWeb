"""Closed36 input; no recipient, user, provider fact, free text or URL input."""
from typing import Annotated,Literal
from pydantic import BaseModel,ConfigDict,Field,StrictBool,StrictInt,StrictStr,field_validator

KEY=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
Identifier=Annotated[StrictStr,Field(min_length=36,max_length=36,pattern=KEY)]
Purpose=Literal["account_period_end","confirmed_payment_issue"]
Context=Literal["personal","gym"]
Counter=Annotated[StrictInt,Field(ge=1,le=2147483647)]


class Command(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    confirm:StrictBool

    @field_validator("confirm")
    @classmethod
    def explicit(cls,value):
        if value is not True:raise ValueError("Explicit confirmation required")
        return value


class PreferenceWrite(Command):
    expected_version:Annotated[StrictInt,Field(ge=0,le=2147483647)]
    enabled:StrictBool
    interval_hours:StrictInt=24

    @field_validator("interval_hours")
    @classmethod
    def interval(cls,value):
        if value not in {24,72,168}:raise ValueError("Unreviewed interval")
        return value


class QueueWrite(Command):
    purpose:Purpose
    preference_id:Identifier
    expected_preference_version:Counter
    fact_id:Identifier
    source_hash:Annotated[StrictStr,Field(min_length=64,max_length=64,pattern=r"^[0-9a-f]{64}$")]


class CancelWrite(Command):
    expected_version:Counter


class ObserveWrite(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)


class ExclusionWrite(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    token:Annotated[StrictStr,Field(min_length=43,max_length=43,pattern=r"^[A-Za-z0-9_-]{43}$")]

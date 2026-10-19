"""Closed wire34 inputs. No client-supplied identity, timestamps or free text."""
from datetime import date
import re
import unicodedata
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StrictInt


def _legacy(value):
    if (not isinstance(value, str) or not 1 <= len(value) <= 36
            or unicodedata.normalize("NFC", value) != value
            or any(unicodedata.category(c).startswith("C") for c in value)):
        raise ValueError("Invalid resource identifier")
    return value


def _confirmed(value):
    if value is not True:
        raise ValueError("Explicit confirmation required")
    return value


def _civil(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("Civil ISO date required")
    return date.fromisoformat(value)


ResourceId = Annotated[str, BeforeValidator(_legacy)]
Version = Annotated[StrictInt, Field(ge=1, le=2147483647)]
Confirmed = Annotated[bool, BeforeValidator(_confirmed)]
CivilDate = Annotated[date, BeforeValidator(_civil)]
Cause = Literal["no_saved_plan", "no_plan_in_window", "plan_date_missing", "membership_date_passed"]
NextStep = Literal["review_client_record", "review_plan_history", "review_membership_date"]
Status = Literal["open", "completed", "cancelled"]
KEY = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"


class Command(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class CreateTask(Command):
    client_id: ResourceId
    cause: Cause
    cause_evidence_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    next_step: NextStep
    assignee_id: ResourceId | None
    expected_active_task_id: None
    confirm: Confirmed


class EditTask(Command):
    expected_version: Version
    next_step: NextStep
    assignee_id: ResourceId | None
    confirm: Confirmed


class CompleteTask(Command):
    expected_version: Version
    outcome: Literal["review_recorded"]
    confirm: Confirmed


class CancelTask(Command):
    expected_version: Version
    reason: Literal["created_in_error", "no_longer_applicable", "duplicate"]
    confirm: Confirmed

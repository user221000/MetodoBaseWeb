"""Boundary witnesses independent of the SQL/service implementation."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from pydantic import TypeAdapter, ValidationError

from web.followup_schemas import CivilDate, CreateTask, EditTask
from web.services.followup_domain import causes, cursor_encode, cursor_decode, period


def test_evidence_hash_does_not_move_with_observation_clock_but_tracks_relevant_facts():
    now=datetime(2026,10,19,18,tzinfo=timezone.utc)
    row=SimpleNamespace(id_cliente="synthetic-client",plan_count=2,last_plan_at=now-timedelta(days=60),membership_end=None)
    first=causes(row,"gym-a",now)[0];second=causes(row,"gym-a",now+timedelta(seconds=1))[0]
    assert first["cause_evidence_hash"]==second["cause_evidence_hash"]
    assert first["observed_at"]!=second["observed_at"]
    row.plan_count=3
    assert causes(row,"gym-a",now)[0]["cause_evidence_hash"]!=first["cause_evidence_hash"]
    assert causes(row,"gym-b",now)[0]["cause_evidence_hash"]!=first["cause_evidence_hash"]


def test_range_uses_mexico_civil_day_not_environment_timezone(monkeypatch):
    monkeypatch.setenv("TZ","Pacific/Auckland")
    start=TypeAdapter(CivilDate).validate_python("2026-10-01")
    through=TypeAdapter(CivilDate).validate_python("2026-10-19")
    first,last,lower,upper=period(start,through,datetime(2026,10,20,3,tzinfo=timezone.utc))
    assert first.isoformat()=="2026-10-01" and last.isoformat()=="2026-10-19"
    assert lower.isoformat()=="2026-10-01T06:00:00+00:00" and upper.isoformat()=="2026-10-20T06:00:00+00:00"


@pytest.mark.parametrize("value",[0,True,"0","2026-1-01","2026-02-30","2026-10-19T00:00:00Z"])
def test_civil_date_never_accepts_epoch_or_datetime(value):
    with pytest.raises((ValueError,ValidationError)):TypeAdapter(CivilDate).validate_python(value)


def test_cursor_roundtrip_is_strict_and_not_an_authority_claim():
    value=cursor_encode(datetime(2026,10,19,18,tzinfo=timezone.utc),"11111111-1111-4111-8111-111111111111")
    at,identifier=cursor_decode(value)
    assert at.hour==18 and identifier=="11111111-1111-4111-8111-111111111111"
    with pytest.raises(ValueError):cursor_decode(value+"=")


@pytest.mark.parametrize("changes",[{"expected_version":True},{"expected_version":1.0},{"confirm":1},{"actor_id":"fake"}])
def test_edit_rejects_type_coercion_and_untrusted_actor(changes):
    base={"expected_version":1,"next_step":"review_plan_history","assignee_id":None,"confirm":True}
    with pytest.raises(ValidationError):EditTask.model_validate({**base,**changes})


def test_creation_requires_explicit_null_absence_and_confirm():
    base={"client_id":"legacy","cause":"no_saved_plan","cause_evidence_hash":"a"*64,
        "next_step":"review_plan_history","assignee_id":None,"expected_active_task_id":None,"confirm":True}
    assert CreateTask.model_validate(base).expected_active_task_id is None
    del base["expected_active_task_id"]
    with pytest.raises(ValidationError):CreateTask.model_validate(base)

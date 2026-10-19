"""Counter algorithm tests only: no migration/auth/RLS acceptance is claimed."""
from copy import deepcopy
from datetime import date, datetime, timezone
import json
from types import SimpleNamespace

from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine, text

from web.services.progress_readers import _counts
from web.services.personal_diary_service import resolve_consumed_meal
from web.personal_diary_schemas import MealSelection


def meals():
    plan=SimpleNamespace(id=1,gym_id="self",deleted_at=None,plan_json=json.dumps({"desayuno":{"alimentos":{"huevo":50}}}))
    return {"desayuno":{**resolve_consumed_meal(plan,"self","desayuno",MealSelection(include_fixed_menu=True),now=datetime.now(timezone.utc)),"completed":True}}


def read(raw):
    engine=create_engine("sqlite://")
    try:
        with engine.begin() as db:
            db.exec_driver_sql("CREATE TABLE personal_diary_days(local_date TEXT,version INTEGER,timezone TEXT,user_id TEXT,meals_json TEXT)")
            db.execute(text("INSERT INTO personal_diary_days VALUES ('2026-10-19',1,'America/Mexico_City','self',:raw)"),{"raw":raw})
            return _counts(db,"self",date(2026,10,19),date(2026,10,19))
    finally:engine.dispose()


def test_actual_resolver_snapshot_and_empty_day_produce_only_observed_scalars():
    result=read(json.dumps(meals()))
    assert result==[{"local_date":"2026-10-19","registered_snapshots":1,"completed_snapshots":1,"ratio":1.0,"status":"observed"}]
    assert read("{}")==[{"local_date":"2026-10-19","registered_snapshots":0,"completed_snapshots":0,"ratio":None,"status":"no_registered_snapshots"}]


@pytest.mark.parametrize("change",["parse","oversize","completion","selection","timestamp","context","macro_total","missing_food_field","unknown_meal"])
def test_corrupt_source_rejects_whole_instead_of_returning_a_partial_counter(change):
    value=meals();snapshot=value["desayuno"]
    if change=="completion":snapshot["completed"]="true"
    if change=="selection":snapshot["selections"]["arbitrary_key"]=True
    if change=="timestamp":snapshot["recorded_at"]="2026-10-19T12:00:00"
    if change=="context":snapshot["source_context"]={"kind":"unverified"}
    if change=="macro_total":snapshot["totals"]["kcal"]+=100
    if change=="missing_food_field":snapshot["foods"][0]["other"]=snapshot["foods"][0].pop("grams")
    if change=="unknown_meal":value["unknown"]=value.pop("desayuno")
    raw="{broken" if change=="parse" else " "*65537+"{}" if change=="oversize" else json.dumps(value)
    with pytest.raises(HTTPException) as error:read(raw)
    assert error.value.status_code==409 and error.value.detail["code"]=="progress_source_requires_review"

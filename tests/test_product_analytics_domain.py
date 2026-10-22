"""Measurement semantics and baseline privacy, not implementation mirrors."""
import hashlib
from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from web import product_analytics_domain as d
from web.product_analytics_baseline import baseline_bytes, build_baseline

NOW = datetime(2026, 10, 21, 18, tzinfo=UTC)


def report(saved=(), *, now=NOW, start=None, through=None, context="personal", **kwargs):
    preparation = {"profile_present": False, "plan_present": False} if context == "personal" else {
        "client_registered": False, "plan_saved": False}
    return d.build_report(context, preparation, saved, [], [], now=now, start=start, through=through,
        schema_revision="20261020_account_security", **kwargs)


def test_empty_is_observed_zero_not_an_invented_baseline():
    value = report()
    assert len(value["weekly"]) == 4
    assert all(row["saved_publications"] == 0 for row in value["weekly"])
    assert value["cohort"]["population_units"] == 0
    assert value["cohort"]["anchor_week"] is None
    assert value["cohort"]["observed_repeat_publication_d7"] == {
        "mature": False, "denominator": 0, "numerator": None, "ratio": None}
    assert value["business_baseline"] == {"status": "not_measured", "targets": None}
    assert value["coverage"]["demo_classification"] == "unclassified_no_persisted_flag"


def test_anchor_ignores_from_and_repeat_windows_are_half_open():
    anchor = NOW - timedelta(days=50)
    saved = [anchor, anchor + timedelta(days=7), anchor + timedelta(days=14), anchor + timedelta(days=37)]
    a = report(saved, start="2026-10-12", through="2026-10-21")
    b = report(saved, start="2026-09-28", through="2026-10-21")
    assert a["cohort"] == b["cohort"]
    assert a["cohort"]["observed_repeat_publication_d7"]["numerator"] == 1
    assert a["cohort"]["observed_repeat_publication_d30"]["numerator"] == 0
    assert a["cohort"]["observed_repeat_publication_d30"]["ratio"] == 0.0
    assert sum(row["saved_publications"] for row in a["weekly"]) == 0


@pytest.mark.parametrize("days,key,end", [(7, "d7", 14), (30, "d30", 37)])
def test_maturity_changes_at_exact_complete_window(days, key, end):
    anchor = datetime(2026, 9, 1, 12, tzinfo=UTC)
    event = anchor + timedelta(days=days)
    before = report([anchor, event], now=anchor + timedelta(days=end) - timedelta(microseconds=1))
    at = report([anchor, event], now=anchor + timedelta(days=end))
    assert before["cohort"]["observed_repeat_publication_" + key]["numerator"] is None
    assert at["cohort"]["observed_repeat_publication_" + key] == {
        "mature": True, "denominator": 1, "numerator": 1, "ratio": 1.0}


def test_mexico_monday_and_through_asof_boundaries():
    before_monday = datetime(2026, 10, 19, 5, 59, 59, tzinfo=UTC)
    monday = before_monday + timedelta(seconds=1)
    value = report([before_monday, monday, NOW + timedelta(microseconds=1)],
        start="2026-10-12", through="2026-10-21")
    assert [row["saved_publications"] for row in value["weekly"]] == [1, 1]
    assert value["weekly"][0]["complete"] is True and value["weekly"][1]["complete"] is False
    exclusive = datetime(2026, 10, 20, 6, tzinfo=UTC)
    ended = report([exclusive - timedelta(microseconds=1), exclusive],
        start="2026-10-19", through="2026-10-19")
    assert ended["weekly"][0]["saved_publications"] == 1


@pytest.mark.parametrize("start,end", [
    ("0", "2026-10-21"), ("2026-10-19", None), (None, "2026-10-21"),
    ("2026-10-20", "2026-10-21"), ("2026-10-19", "2026-10-22"),
    ("2026-10-26", "2026-10-21"), ("2026-06-02", "2026-10-21"),
    (20261019, "2026-10-21"), (True, "2026-10-21"), ("2026-02-30", "2026-10-21"),
])
def test_invalid_periods_reject_without_date_coercion(start, end):
    with pytest.raises(d.AnalyticsInput):
        d.period(start, end, now=NOW)


def test_dictionary_and_build_metadata_do_not_attest_a_checkout():
    value = report(reported_build="a" * 40)
    assert value["snapshot"]["source_revision_status"] == "reported_by_build"
    assert report()["snapshot"]["source_revision"] is None
    assert report(reported_build="not-a-commit")["snapshot"]["source_revision_status"] == "unavailable"
    definition = d.dictionary()
    assert hashlib.sha256(d.canonical(definition)).hexdigest() == d.DEFINITION_HASH
    definition["version"] = "modified"
    assert d.dictionary()["version"] == d.VERSION


def test_baseline_is_pure_repeatable_unreviewed_and_does_not_mutate_report():
    value = report([NOW - timedelta(days=8)])
    before = deepcopy(value)
    one, two = build_baseline(value), build_baseline(value)
    assert one == two and value == before
    assert one["validation_state"] == "unreviewed"
    assert one["business_baseline_established"] is False and one["targets"] is None
    assert hashlib.sha256(d.canonical(one["measurement_dictionary"])).hexdigest() == value["definition_hash"]
    assert one["report_hash"] == hashlib.sha256(d.canonical(value)).hexdigest()
    assert baseline_bytes(value).endswith(b"\n")


@pytest.mark.parametrize("mutate", [
    lambda v: v.update(email="synthetic@example.invalid"),
    lambda v: v["snapshot"].update(token="not-accepted"),
    lambda v: v["preparation_as_of"].update(peso_kg=70),
    lambda v: v["weekly"][0].update(saved_publications=True),
    lambda v: v["weekly"][0].update(saved_publications=-1),
    lambda v: v["cohort"]["observed_repeat_publication_d7"].update(ratio=float("nan")),
    lambda v: v["business_baseline"].update(targets={"retention": 0.9}),
    lambda v: v["coverage"].update(history="complete"),
    lambda v: v.update(result_hash="0" * 64),
    lambda v: v.update(definition_hash="0" * 64),
])
def test_baseline_rejects_unknown_private_fields_invalid_numbers_and_forged_coverage(mutate):
    value = report()
    mutate(value)
    with pytest.raises((d.AnalyticsInput, d.AnalyticsVolume)):
        build_baseline(value)


@pytest.mark.parametrize("mutate", [
    lambda v: v["weekly"][0].update(complete=False),
    lambda v: v["preparation_as_of"].update(plan_present=True),
    lambda v: v["weekly"][0].update(saved_publications=1),
    lambda v: v["cohort"].update(anchor_week="2026-11-02", population_units=1),
    lambda v: [row.update(saved_publications=10000) for row in v["weekly"]],
])
def test_even_rehashed_artifact_cannot_claim_incoherent_facts(mutate):
    value = report()
    mutate(value)
    value["result_hash"] = hashlib.sha256(d.canonical({k: v for k, v in value.items() if k != "result_hash"})).hexdigest()
    with pytest.raises(d.AnalyticsInput):
        build_baseline(value)

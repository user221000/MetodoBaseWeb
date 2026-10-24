"""Pure v2 aggregation. Technical identifiers are inputs only, never report fields."""
import hashlib
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from web import product_analytics_domain as v1
from web.database.product_analytics_schema_v2 import EVENTS, ORIGINS

VERSION = "product-facts-v2"
DICTIONARY = {"version": VERSION, "origins": list(ORIGINS), "events": list(EVENTS),
    "origin": "immutable_snapshot_visible_at_append_not_payment", "timezone": v1.ZONE,
    "observed_subject": "own_client_or_personal_space_with_non_declaration_fact_in_window",
    "publication_origin": "plan_saved_snapshot_or_unknown_if_legacy",
    "served": "first_complete_assigned_plan_http200_asgi_body_per_publication_version",
    "limits": {"facts": v1.MAX_FACTS, "bytes": v1.MAX_BYTES},
    "retention": "null_without_reviewed_population_cohort", "targets": None}
DEFINITION_HASH = hashlib.sha256(v1.canonical(DICTIONARY)).hexdigest()


def aggregate(rows, period, *, now, context):
    # v1 period parsing is reused as a value parser only; v1 reports/validators
    # and their historical baseline/population semantics are unchanged.
    start, through = period
    first, end, _ = v1.boundaries(start, through, now)
    if len(rows) > v1.MAX_FACTS:
        raise v1.AnalyticsVolume('Fact budget exceeded')
    totals = {origin: {event: 0 for event in EVENTS} for origin in ORIGINS}
    subjects = {origin: set() for origin in ORIGINS}
    weeks = {}
    earliest = None
    for event, origin, stamp, client, source in rows:
        instant = v1.storage_instant(stamp)
        if event not in EVENTS or origin not in ORIGINS:
            raise ValueError("Unsupported product fact vocabulary")
        if instant > now:
            raise ValueError("Product fact is in the future")
        if event != 'origin_declared':
            earliest = instant if earliest is None else min(earliest, instant)
        if not (first <= instant < end and instant <= now) or event == "origin_declared":
            continue
        totals[origin][event] += 1
        subjects[origin].add(client or "personal")
        civil = instant.astimezone(ZoneInfo(v1.ZONE)).date()
        monday = civil - timedelta(days=civil.weekday())
        week = weeks.setdefault(monday.isoformat(), {o: {e: 0 for e in EVENTS if e != "origin_declared"} for o in ORIGINS})
        week[origin][event] += 1
    result = {"definition_version": VERSION, "definition_hash": DEFINITION_HASH, "context": context,
        "period": {"from": start.isoformat(), "through": through.isoformat(), "as_of": now.isoformat()},
        "classification": {"values": list(ORIGINS), "historical": "unknown_until_observed",
            "semantics": "snapshot_at_fact", "customer_is_payment": False},
        "baseline": {"status": "observed" if any(subjects.values()) else "not_observed",
            "first_observed_fact": earliest.isoformat() if earliest else None,
            "observed_subjects_by_origin": {o: len(subjects[o]) for o in ORIGINS},
            "event_counts_by_origin": totals, "retention_D7": None, "retention_D30": None,
            "retention_reason": "no_reviewed_population_cohort", "targets": None},
        "weeks": [{"week": week, "by_origin": counts} for week, counts in sorted(weeks.items())],
        "coverage": {"past_events_backfilled": False, "delivery": "not_measured",
            "assigned_plan_http200": "complete_body_accepted_by_asgi_not_tcp_or_human_read",
            "observation_gaps": "crash_commit_failure_or_changed_authority_after_response_can_lose_observation",
            "cohort_scope": "own_workspace_observed_subjects_by_snapshot_origin_not_population",
            "identifiers": "pseudonymous_linkable_inputs_aggregate_output"}}
    result["result_hash"] = hashlib.sha256(v1.canonical(result)).hexdigest()
    validate_report(result)
    return result


def validate_report(value):
    """Version-specific bounded contract; never loosen the historical v1 validator."""
    def check(ok):
        if not ok:
            raise ValueError("Invalid product analytics v2 report")

    check(type(value) is dict and set(value) == {"definition_version", "definition_hash", "context",
        "period", "classification", "baseline", "weeks", "coverage", "result_hash"})
    check(value["definition_version"] == VERSION and value["definition_hash"] == DEFINITION_HASH)
    check(value["context"] in ("gym", "personal"))
    unsigned = {k: v for k, v in value.items() if k != "result_hash"}
    check(value["result_hash"] == hashlib.sha256(v1.canonical(unsigned)).hexdigest())
    check(len(v1.canonical(value)) <= v1.MAX_BYTES)
    check(type(value["period"]) is dict and set(value["period"]) == {"from", "through", "as_of"})
    stamp = v1.instant(datetime.fromisoformat(value["period"]["as_of"]))
    first, last = v1.period(value["period"]["from"], value["period"]["through"], now=stamp)
    check(v1.canonical(value["classification"]) == v1.canonical({"values": list(ORIGINS), "historical": "unknown_until_observed",
        "semantics": "snapshot_at_fact", "customer_is_payment": False}))
    baseline = value["baseline"]
    check(type(baseline) is dict and set(baseline) == {"status", "first_observed_fact", "observed_subjects_by_origin",
        "event_counts_by_origin", "retention_D7", "retention_D30", "retention_reason", "targets"})
    check(baseline["retention_D7"] is None and baseline["retention_D30"] is None and baseline["targets"] is None
        and baseline["retention_reason"] == "no_reviewed_population_cohort")
    check(type(baseline["observed_subjects_by_origin"]) is dict and set(baseline["observed_subjects_by_origin"]) == set(ORIGINS))
    check(type(baseline["event_counts_by_origin"]) is dict and set(baseline["event_counts_by_origin"]) == set(ORIGINS))
    for origin in ORIGINS:
        count = baseline["observed_subjects_by_origin"][origin]
        check(type(count) is int and 0 <= count <= v1.MAX_FACTS)
        counts = baseline["event_counts_by_origin"][origin]
        check(type(counts) is dict and set(counts) == set(EVENTS))
        check(all(type(v) is int and 0 <= v <= v1.MAX_FACTS for v in counts.values()))
        check(counts["origin_declared"] == 0 and count <= sum(counts.values()))
        if value["context"] == "personal":
            check(count <= 1 and all(counts[e] == 0 for e in EVENTS if e not in ("plan_saved", "origin_declared")))
    check(baseline["status"] == ("observed" if any(baseline["observed_subjects_by_origin"].values()) else "not_observed"))
    earliest = baseline["first_observed_fact"]
    check(not any(baseline['observed_subjects_by_origin'].values()) or earliest is not None)
    if earliest is not None:
        check(v1.instant(datetime.fromisoformat(earliest)) <= stamp)
    check(type(value["weeks"]) is list and len(value["weeks"]) <= 13)
    seen = set()
    totals = {o: {e: 0 for e in EVENTS if e != "origin_declared"} for o in ORIGINS}
    for week in value["weeks"]:
        check(type(week) is dict and set(week) == {"week", "by_origin"})
        day = v1.civil(week["week"])
        check(day.weekday() == 0 and first <= day <= last and day not in seen)
        seen.add(day)
        check(type(week["by_origin"]) is dict and set(week["by_origin"]) == set(ORIGINS))
        for origin, counts in week["by_origin"].items():
            check(type(counts) is dict and set(counts) == set(totals[origin]))
            for event, count in counts.items():
                check(type(count) is int and 0 <= count <= v1.MAX_FACTS)
                totals[origin][event] += count
    check([r["week"] for r in value["weeks"]] == sorted(r["week"] for r in value["weeks"]))
    check(all(totals[o][e] == baseline["event_counts_by_origin"][o][e] for o in ORIGINS for e in totals[o]))
    check(v1.canonical(value["coverage"]) == v1.canonical({"past_events_backfilled": False, "delivery": "not_measured",
        "assigned_plan_http200": "complete_body_accepted_by_asgi_not_tcp_or_human_read",
        "observation_gaps": "crash_commit_failure_or_changed_authority_after_response_can_lose_observation",
        "cohort_scope": "own_workspace_observed_subjects_by_snapshot_origin_not_population",
        "identifiers": "pseudonymous_linkable_inputs_aggregate_output"}))
    return value

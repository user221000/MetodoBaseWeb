"""R30 observed business facts, not person retention or clinical adherence.

The dictionary hash describes these measurements, not code authenticity or a
real-world baseline. Source build metadata is optional and never inferred from
the current Git checkout. No identity, health field or event payload is output.
"""
import hashlib
import json
import math
import re
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

ZONE = "America/Mexico_City"
MAX_FACTS = 10_000
MAX_BYTES = 65_536
VERSION = "r30-observed-facts-v1"
_DICTIONARY = {
    "version": VERSION, "timezone": ZONE, "unit": {"gym": "workspace", "personal": "personal_account"},
    "saved_gym": "own ledger persisted_at; reserved|completed; coherent remaining references or SET NULL",
    "saved_personal": "own ledger protocol1 completed persisted_at; coherent remaining plan reference or SET NULL",
    "preparation": "current active nondeleted own profile/client and double-owned nondeleted Plan existence; no bootstrap",
    "accepted": "own coherent R12 consumed invitation/link acceptance; historical fact, not current access",
    "assigned": "own coherent R12 exact link/client/Plan assignment; current published|withdrawn state grouped by published_at",
    "anchor": "minimum retained saved timestamp up to effective cutoff, independent of from; not first-ever",
    "repeat_windows_days": {"d7": [7, 14], "d30": [30, 37]},
    "ratio": "numerator/denominator0..1; NULL until complete window; no anchor denominator0/NULL",
    "weekly": "Monday Mexico; inclusive civil through, exclusive next-day boundary, never beyond as_of",
    "limits": {"weeks": 13, "source_rows": MAX_FACTS, "bytes": MAX_BYTES},
    "coverage": "retained facts only; legacy unmarked excluded; demo unclassified; no open/delivery/actor-gym/global attribution",
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


DEFINITION_HASH = hashlib.sha256(canonical(_DICTIONARY)).hexdigest()


class AnalyticsInput(ValueError):
    pass


class AnalyticsVolume(ValueError):
    pass


def dictionary():
    return json.loads(canonical(_DICTIONARY))


def instant(value=None):
    value = value if value is not None else datetime.now(UTC)
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise AnalyticsInput("Aware report clock required")
    return value.astimezone(UTC)


def storage_instant(value):
    """Existing UTCDateTime results can be UTC-naive; do not reinterpret rows."""
    if not isinstance(value, datetime):
        raise AnalyticsInput("Invalid stored instant")
    return instant(value.replace(tzinfo=UTC) if value.tzinfo is None else value)


def iso(value):
    return instant(value).isoformat().replace("+00:00", "Z")


def civil(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise AnalyticsInput("Civil ISO date required")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise AnalyticsInput("Invalid civil date") from None


def period(start=None, through=None, *, now=None):
    stamp = instant(now)
    today = stamp.astimezone(ZoneInfo(ZONE)).date()
    if (start is None) != (through is None):
        raise AnalyticsInput("Both dates required")
    lower = civil(start) if start is not None else today - timedelta(days=today.weekday() + 21)
    upper = civil(through) if through is not None else today
    if lower.weekday() != 0 or lower > upper or upper > today or (upper - lower).days > 90:
        raise AnalyticsInput("Invalid reporting period")
    return lower, upper


def boundaries(start, through, now):
    zone = ZoneInfo(ZONE)
    lower = datetime.combine(start, time.min, zone).astimezone(UTC)
    upper = datetime.combine(through + timedelta(days=1), time.min, zone).astimezone(UTC)
    return lower, upper, min(instant(now), upper)


def coverage(scope):
    return {"history": "retained_facts_only", "legacy_without_marker": "excluded_not_reconstructed",
            "demo_classification": "unclassified_no_persisted_flag", "first_open": "not_instrumented",
            "delivery": "not_measured", "actor_attribution": "workspace_only" if scope == "gym" else "subject_bound",
            "global_cohorts": "not_in_scope"}


def build_report(scope, preparation, saved, accepted, assigned, *, now, start=None, through=None,
                 schema_revision, reported_build=None):
    if scope not in ("gym", "personal"):
        raise AnalyticsInput("Unknown scope")
    stamp = instant(now)
    first, last = period(start, through, now=stamp)
    lower, upper, cutoff = boundaries(first, last, stamp)
    if any(len(rows) > MAX_FACTS for rows in (saved, accepted, assigned)):
        raise AnalyticsVolume("Fact budget exceeded")
    # The next civil midnight is exclusive; as_of itself is inclusive.
    observed = lambda value: value < upper and value <= stamp
    saved = [instant(value) for value in saved if observed(instant(value))]
    accepted = [instant(value) for value in accepted if observed(instant(value))]
    assigned = [(instant(value), state) for value, state in assigned if observed(instant(value))]
    if scope == "personal" and (accepted or assigned):
        raise AnalyticsInput("Personal facts cannot include gym assignments")
    weeks = []
    day = first
    while day <= last:
        end = datetime.combine(day + timedelta(days=7), time.min, ZoneInfo(ZONE)).astimezone(UTC)
        begin = datetime.combine(day, time.min, ZoneInfo(ZONE)).astimezone(UTC)
        def in_week(value, begin=begin, end=end):
            return max(begin, lower) <= value < end
        row = {"week_start": day.isoformat(), "complete": end <= cutoff,
               "saved_publications": sum(in_week(value) for value in saved)}
        if scope == "gym":
            row.update(link_acceptances=sum(in_week(value) for value in accepted),
                plan_assignments_published=sum(in_week(value) and state == "published" for value, state in assigned),
                plan_assignments_withdrawn=sum(in_week(value) and state == "withdrawn" for value, state in assigned))
        weeks.append(row)
        day += timedelta(days=7)
    anchor = min(saved) if saved else None

    def repeated(begin, end):
        mature = anchor is not None and cutoff >= anchor + timedelta(days=end)
        numerator = int(any(anchor + timedelta(days=begin) <= value < anchor + timedelta(days=end)
                            for value in saved)) if mature else None
        return {"mature": mature, "denominator": int(anchor is not None), "numerator": numerator,
                "ratio": float(numerator) if numerator is not None else None}

    anchor_day = anchor.astimezone(ZoneInfo(ZONE)).date() if anchor else None
    revision = reported_build if isinstance(reported_build, str) and re.fullmatch(r"[0-9a-f]{40}", reported_build) else None
    result = {"version": 1, "definition_version": VERSION, "definition_hash": DEFINITION_HASH,
        "scope": scope, "unit": "workspace" if scope == "gym" else "personal_account",
        "period": {"from": first.isoformat(), "through": last.isoformat(), "timezone": ZONE},
        "snapshot": {"as_of": iso(stamp), "schema_revision": schema_revision,
            "source_revision": revision, "source_revision_status": "reported_by_build" if revision else "unavailable"},
        "preparation_as_of": preparation, "weekly": weeks,
        "cohort": {"anchor_week": (anchor_day - timedelta(days=anchor_day.weekday())).isoformat() if anchor else None,
            "anchor_kind": "first_observed_publication", "population_units": int(anchor is not None),
            "evaluated_at": iso(cutoff), "observed_repeat_publication_d7": repeated(7, 14),
            "observed_repeat_publication_d30": repeated(30, 37)},
        "coverage": coverage(scope), "business_baseline": {"status": "not_measured", "targets": None}}
    result["result_hash"] = hashlib.sha256(canonical(result)).hexdigest()
    validate_report(result)
    return result


def _keys(value, names):
    if not isinstance(value, dict) or set(value) != set(names.split()):
        raise AnalyticsInput("Unknown report fields")


def _count(value, *, maximum=MAX_FACTS):
    if type(value) is not int or not 0 <= value <= maximum:
        raise AnalyticsInput("Invalid report count")


def _iso_input(value):
    if not isinstance(value, str) or not value.endswith("Z") or len(value) > 27:
        raise AnalyticsInput("Invalid report timestamp")
    try:
        parsed = datetime.fromisoformat(value)
        if iso(parsed) != value:
            raise AnalyticsInput("Noncanonical report timestamp")
        return parsed
    except (ValueError, TypeError):
        raise AnalyticsInput("Invalid report timestamp") from None


def validate_report(value):
    """Strict allowlist for baseline bytes; validation is not provenance proof."""
    try:
        encoded = canonical(value)
    except (TypeError, ValueError, OverflowError, RecursionError):
        raise AnalyticsInput("Invalid report") from None
    if len(encoded) > MAX_BYTES:
        raise AnalyticsVolume("Response budget exceeded")
    _keys(value, "version definition_version definition_hash scope unit period snapshot preparation_as_of weekly cohort coverage business_baseline result_hash")
    scope = value["scope"]
    if (type(value["version"]) is not int or value["version"] != 1 or scope not in ("gym", "personal")
            or value["definition_version"] != VERSION or value["definition_hash"] != DEFINITION_HASH
            or value["unit"] != ("workspace" if scope == "gym" else "personal_account")):
        raise AnalyticsInput("Unknown measurement definition")
    _keys(value["snapshot"], "as_of schema_revision source_revision source_revision_status")
    snapshot = value["snapshot"]
    now = _iso_input(snapshot["as_of"])
    if not isinstance(snapshot["schema_revision"], str) or not re.fullmatch(r"[a-z0-9_]{1,64}", snapshot["schema_revision"]):
        raise AnalyticsInput("Invalid schema revision")
    revision = snapshot["source_revision"]
    if revision is None:
        if snapshot["source_revision_status"] != "unavailable":
            raise AnalyticsInput("Unattested build")
    elif not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision) or snapshot["source_revision_status"] != "reported_by_build":
        raise AnalyticsInput("Invalid reported build")
    _keys(value["period"], "from through timezone")
    if value["period"]["timezone"] != ZONE:
        raise AnalyticsInput("Unknown timezone")
    first, last = period(value["period"]["from"], value["period"]["through"], now=now)
    prep = "client_registered plan_saved" if scope == "gym" else "profile_present plan_present"
    _keys(value["preparation_as_of"], prep)
    if any(type(item) is not bool for item in value["preparation_as_of"].values()):
        raise AnalyticsInput("Invalid preparation fact")
    prepared, planned = (value["preparation_as_of"][key] for key in prep.split())
    if planned and not prepared:
        raise AnalyticsInput("Plan preparation requires an own live profile")
    weeks = value["weekly"]
    if not isinstance(weeks, list) or len(weeks) != (last - first).days // 7 + 1 or len(weeks) > 13:
        raise AnalyticsInput("Invalid week coverage")
    cutoff = boundaries(first, last, now)[2]
    for index, row in enumerate(weeks):
        names = "week_start complete saved_publications" + (" link_acceptances plan_assignments_published plan_assignments_withdrawn" if scope == "gym" else "")
        _keys(row, names)
        if row["week_start"] != (first + timedelta(days=index * 7)).isoformat() or type(row["complete"]) is not bool:
            raise AnalyticsInput("Invalid week label")
        end = datetime.combine(first + timedelta(days=(index + 1) * 7), time.min,
                               ZoneInfo(ZONE)).astimezone(UTC)
        if row["complete"] != (end <= cutoff):
            raise AnalyticsInput("Invalid week maturity")
        for key in set(row) - {"week_start", "complete"}:
            _count(row[key])
    for key in ("saved_publications", "link_acceptances") if scope == "gym" else ("saved_publications",):
        _count(sum(row[key] for row in weeks))
    if scope == "gym":
        _count(sum(row["plan_assignments_published"] + row["plan_assignments_withdrawn"] for row in weeks))
    cohort = value["cohort"]
    _keys(cohort, "anchor_week anchor_kind population_units evaluated_at observed_repeat_publication_d7 observed_repeat_publication_d30")
    if cohort["anchor_kind"] != "first_observed_publication":
        raise AnalyticsInput("Unknown cohort anchor")
    _count(cohort["population_units"], maximum=1)
    if cohort["anchor_week"] is None:
        if cohort["population_units"] != 0:
            raise AnalyticsInput("Missing anchor")
    elif (civil(cohort["anchor_week"]).weekday() != 0 or cohort["population_units"] != 1
            or civil(cohort["anchor_week"]) > cutoff.astimezone(ZoneInfo(ZONE)).date()):
        raise AnalyticsInput("Invalid anchor week")
    if cohort["population_units"] == 0 and any(row["saved_publications"] for row in weeks):
        raise AnalyticsInput("Observed publications require an anchor")
    if _iso_input(cohort["evaluated_at"]) != boundaries(first, last, now)[2]:
        raise AnalyticsInput("Invalid observation cutoff")
    for key in ("observed_repeat_publication_d7", "observed_repeat_publication_d30"):
        row = cohort[key]
        _keys(row, "mature denominator numerator ratio")
        if type(row["mature"]) is not bool or type(row["denominator"]) is not int or row["denominator"] != cohort["population_units"]:
            raise AnalyticsInput("Invalid maturity")
        if row["mature"]:
            _count(row["numerator"], maximum=1)
            if row["denominator"] != 1 or type(row["ratio"]) not in (int, float) or not math.isfinite(row["ratio"]) or row["ratio"] != row["numerator"]:
                raise AnalyticsInput("Invalid observed ratio")
        elif row["numerator"] is not None or row["ratio"] is not None:
            raise AnalyticsInput("Immature values must be unknown")
    if value["coverage"] != coverage(scope) or value["business_baseline"] != {"status": "not_measured", "targets": None}:
        raise AnalyticsInput("Unknown coverage or invented baseline")
    candidate = {key: item for key, item in value.items() if key != "result_hash"}
    if value["result_hash"] != hashlib.sha256(canonical(candidate)).hexdigest():
        raise AnalyticsInput("Altered report")
    return json.loads(encoded)

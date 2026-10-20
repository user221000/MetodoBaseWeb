"""Pure, bounded operational evidence, dates and cursors; never clinical data."""
import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
from zoneinfo import ZoneInfo

from config.constantes import PERIODO_MES_DIAS
from web.services.followup_policy import utc

REPORT_TIMEZONE = "America/Mexico_City"
MAX_VERSION = 2147483647
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z")


def instant(now=None):
    now = datetime.now(timezone.utc) if now is None else now
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Aware follow-up clock required")
    return now.astimezone(timezone.utc)


def iso(value):
    return utc(value).astimezone(timezone.utc).isoformat().replace("+00:00", "Z") if value is not None else None


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def request_hash(actor, gym, method, path, command):
    return hashlib.sha256(canonical({"actor": actor, "gym": gym, "method": method, "path": path,
        "body": command.model_dump(mode="json")})).hexdigest()


def causes(row, gym, now):
    """Hash facts only: the moving cutoff and observation clock are NOT facts.

    A stable fact hash can still stop qualifying as time moves or data changes;
    creation must check both hash equality AND current presence in the TX.
    """
    active = []
    if row.plan_count == 0:
        active.append(("no_saved_plan", 1, {"plan_count": 0}))
    elif row.last_plan_at is None:
        active.append(("plan_date_missing", 3, {"plan_count": row.plan_count, "last_plan_at": None}))
    elif utc(row.last_plan_at) < now - timedelta(days=PERIODO_MES_DIAS):
        active.append(("no_plan_in_window", 2, {"plan_count": row.plan_count, "last_plan_at": iso(row.last_plan_at)}))
    if row.membership_end is not None and utc(row.membership_end) < now:
        active.append(("membership_date_passed", 4, {"membership_end": row.membership_end.isoformat()}))
    return [{"cause": cause, "priority": priority, "cause_evidence_hash": hashlib.sha256(canonical({
        "gym_id": gym, "client_id": row.id_cliente, "cause": cause, "facts": facts})).hexdigest(),
        "observed_at": iso(now)} for cause, priority, facts in active]


def allowed_step(cause, step):
    return step == "review_client_record" or step == (
        "review_membership_date" if cause == "membership_date_passed" else "review_plan_history")


def cursor_encode(created_at, identifier):
    return base64.urlsafe_b64encode(canonical([iso(created_at), identifier])).decode("ascii").rstrip("=")


def cursor_decode(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 256 or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ValueError("Invalid follow-up cursor")
    decoded = json.loads(base64.b64decode(value + "="*((-len(value)) % 4), altchars=b"-_", validate=True))
    if not isinstance(decoded, list) or len(decoded) != 2 or not isinstance(decoded[0], str) or not UUID.fullmatch(decoded[1]):
        raise ValueError("Invalid follow-up cursor")
    at = datetime.fromisoformat(decoded[0].replace("Z", "+00:00"))
    at = instant(at)
    if cursor_encode(at, decoded[1]) != value:
        raise ValueError("Noncanonical follow-up cursor")
    return at, decoded[1]


def period(start, through, now):
    today = now.astimezone(ZoneInfo(REPORT_TIMEZONE)).date()
    if start is None and through is None:
        through, start = today, today - timedelta(days=29)
    if start is None or through is None or not 0 <= (through-start).days < 62 or through > today:
        raise ValueError("Invalid follow-up reporting range")
    zone = ZoneInfo(REPORT_TIMEZONE)
    lower = datetime.combine(start, datetime.min.time(), zone).astimezone(timezone.utc)
    upper = datetime.combine(through+timedelta(days=1), datetime.min.time(), zone).astimezone(timezone.utc)
    return start, through, lower, upper

"""Finite PG429 lease transport; validating this contract performs no SQL."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from tests.ci_web37.pg_plan import phases

PROFILE_KEYS = {"METODOBASE_TEST_MIGRATOR_URL", "METODOBASE_TEST_POSTGRES_URL", "METODOBASE_TEST_PG_BIN"}
FUNCTION_DATABASES = {
    "legacy-mfa-services": 12,
    "legacy-followup": 2,
    "legacy-diary": 13,
    "legacy-google-onboarding": 4,
    "migration37": 12,
    "independent-qa": 2,
    "restore": 2,
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def budgets():
    rows = [{"group": row["key"], "module": row["module"], "cases": row["cases"], "pool": row["pool"],
             "UUIDs": FUNCTION_DATABASES.get(row["key"], 1),
             "concurrent_UUIDs": 2 if row["key"] in {"independent-qa", "restore"} else 1} for row in phases()]
    if len(rows) != 29 or sum(row["UUIDs"] for row in rows) != 69:
        raise ValueError("The source-bound PG429/69 UUID budget differs")
    return rows


def profile(path, *, expected_sha256=None):
    path = Path(path).resolve(strict=True)
    raw = path.read_bytes()
    if expected_sha256 is not None and hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("The readonly PG profile changed after the Root ACK")
    value = json.loads(raw)
    if set(value) != PROFILE_KEYS or any(not isinstance(item, str) or not item for item in value.values()):
        raise ValueError("The exclusive PG profile must contain exactly its three explicit variables")
    from urllib.parse import urlsplit

    from tests.isolation import validate_postgres_test_url
    urls = [urlsplit(validate_postgres_test_url(value[key])) for key in sorted(PROFILE_KEYS) if key.endswith("_URL")]
    if (any(item.hostname not in {"127.0.0.1", "localhost"} or item.port != 55483 for item in urls)
            or urls[0].username == urls[1].username or not Path(value["METODOBASE_TEST_PG_BIN"]).is_dir()):
        raise ValueError("The explicit profile must bind the local55483 distinct migrator/application roles")
    return value


def contract(root, source, profile_path, selected):
    root = Path(root)
    profile_path = Path(profile_path).resolve(strict=True)
    profile(profile_path)
    rows = [row for row in budgets() if row["group"] in selected]
    if len(rows) != len(selected) or len(set(selected)) != len(selected):
        raise ValueError("The PG lease selection is duplicated or unknown")
    pins = {}
    for name in ("tests/ci_web37/run_postgres.py", "tests/ci_web37/pg_lease.py", "tests/ci_web37/pg_plan.py",
                 "tests/ci_web37/pg-legacy37.json", "tests/ci_web37/pg-current37-nodeids.json"):
        pins[name] = hashlib.sha256((root / name).read_bytes()).hexdigest()
    return {"schema": "actual37-pg429-exclusive-v1", "source_commit": source["HEAD"],
            "source_files_sha256": digest(source["files"]), "runner_and_plan_RAW_sha256": pins,
            "profile_path": str(profile_path), "profile_sha256": hashlib.sha256(profile_path.read_bytes()).hexdigest(),
            "server_port": 55483, "phases": rows, "max_UUIDs": sum(row["UUIDs"] for row in rows),
            "max_concurrent_UUIDs": max(row["concurrent_UUIDs"] for row in rows),
            "closure": "planned_before_CREATE_exact_OID_normal_DROP_zero_sessions_fresh_absence",
            "Desktop": False, "VM": False, "Chrome": False, "Redis": False, "N2": False}


def require_ack(path, value, *, now=None):
    path = Path(path)
    if not path.is_absolute():
        raise ValueError("An absolute Root lease ACK is required before any PostgreSQL connection")
    ack = json.loads(path.read_bytes())
    expected = {"approved", "scope", "contract_sha256", "expires_at_UTC"}
    if (set(ack) != expected or ack["approved"] is not True or ack["scope"] != "actual37-pg429-exclusive-v1"
            or ack["contract_sha256"] != digest(value)):
        raise ValueError("The exclusive Root ACK does not bind this exact PG source/profile/selection")
    expiry = datetime.fromisoformat(ack["expires_at_UTC"])
    current = now or datetime.now(UTC)
    if expiry.tzinfo is None or not 0 < (expiry - current).total_seconds() <= 8 * 60 * 60:
        raise ValueError("The exclusive Root ACK has expired or exceeds the finite eight-hour window")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def phase_budget(group, new_UUIDs, *, succeeded):
    limit = next(row["UUIDs"] for row in budgets() if row["group"] == group)
    if type(new_UUIDs) is not int or not 0 <= new_UUIDs <= limit or (succeeded and new_UUIDs != limit):
        raise ValueError("The child did not preserve its exact source-bound UUID budget")
    return limit

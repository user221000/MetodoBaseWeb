"""Separate authentic PG53 source/identity contract; legacy429 stays unchanged."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from tests.ci_web37.pg_lease import digest, profile

ROOT = Path(__file__).resolve().parents[2]
SCOPE = "actual37-pg53-exclusive-v1"


def phase(root=ROOT):
    value = json.loads((root / "tests/ci_web37/pg-r30-ppl53.json").read_bytes())
    rows = value["expected"]
    if (value["module"] != "tests/integration_r30_ppl37_postgres.py" or value["cases"] != 53
            or len(rows) != 53 or len(set(map(tuple, rows))) != 53 or value["UUIDs"] != 1
            or value["concurrent_UUIDs"] != 1 or value["restricted_application_pool_size"] != 5
            or value["max_overflow"] != 0 or value["historical429_UUID_budget_unchanged"] != 69):
        raise ValueError("The separate original53 identity or UUID contract differs")
    current = value["current_fixture_bindings"]
    if set(current) != {value["module"], "tests/ci_web37/pg_close.py"}:
        raise ValueError("The explicit current53 fixture close bindings differ")
    for name, pin in current.items():
        raw = (root / name).read_bytes()
        if (set(pin) != {"bytes", "sha256"} or type(pin["bytes"]) is not int
                or (len(raw), hashlib.sha256(raw).hexdigest()) != (pin["bytes"], pin["sha256"])):
            raise ValueError("A current53 direct assertion or fixture source differs")
    for name, pin in value["source_bindings"].items():
        if name in current:
            continue  # Its original RAW binding remains recorded; current transport is explicit above.
        raw = (root / name).read_bytes()
        observed = (len(raw), hashlib.sha256(raw).hexdigest())
        allowed = {(pin["captured_bytes"], pin["captured_raw_sha256"]),
                   (pin["git_raw_bytes"], pin["git_raw_sha256"])}
        if observed not in allowed:
            raise ValueError("An original53 direct assertion or fixture source differs")
        if observed == (pin["git_raw_bytes"], pin["git_raw_sha256"]):
            oid = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw, usedforsecurity=False).hexdigest()
            if oid != pin["Git_blob"]:
                raise ValueError("Original53 source Git object differs")
    return value


def contract(root, source, profile_path):
    value = phase(root)
    profile_path = Path(profile_path).resolve(strict=True)
    profile(profile_path)
    return {"schema": SCOPE, "source_commit": source["HEAD"], "source_files_sha256": digest(source["files"]),
            "profile_path": str(profile_path), "profile_sha256": hashlib.sha256(profile_path.read_bytes()).hexdigest(),
            "phase": {key: value[key] for key in ("group", "module", "cases", "UUIDs", "concurrent_UUIDs",
                                                 "restricted_application_pool_size", "max_overflow", "expected")},
            "server_port": 55483, "max_UUIDs": 1, "max_concurrent_UUIDs": 1,
            "closure": "planned_before_CREATE_exact_OID_normal_DROP_zero_sessions_fresh_absence",
            "historical429_runtime_reattributed": False}


def require_ack(path, value, *, now=None):
    path = Path(path)
    if not path.is_absolute():
        raise ValueError("The separate PG53 ACK must use an absolute path")
    ack = json.loads(path.read_bytes())
    if (set(ack) != {"approved", "scope", "contract_sha256", "expires_at_UTC"}
            or ack["approved"] is not True or ack["scope"] != SCOPE or value.get("schema") != SCOPE
            or ack["contract_sha256"] != digest(value)):
        raise ValueError("The separate PG53 ACK does not bind its source/profile/53 identities")
    expiry = datetime.fromisoformat(ack["expires_at_UTC"])
    if expiry.tzinfo is None or not 0 < (expiry - (now or datetime.now(UTC))).total_seconds() <= 8 * 3600:
        raise ValueError("The separate PG53 ACK is expired or exceeds eight hours")
    return hashlib.sha256(path.read_bytes()).hexdigest()

"""Separate PG53 authorization and source controls; no SQL or fixture bodies."""
import copy
import json
import shutil
import sys
from datetime import UTC, datetime, timedelta

import pytest

from tests.ci_web37 import pg53, pg_lease, run_postgres53

NOW = datetime(2026, 10, 21, tzinfo=UTC)


def acknowledgement(tmp_path, value, **changes):
    ack = {"approved": True, "scope": pg53.SCOPE, "contract_sha256": pg_lease.digest(value),
           "expires_at_UTC": (NOW + timedelta(hours=1)).isoformat(), **changes}
    path = tmp_path / "ack.json"
    path.write_text(json.dumps(ack), encoding="utf8")
    return path


def test_original53_are_separate_from_the_unchanged_429_and_69_UUID_budget():
    value = pg53.phase()
    legacy = pg_lease.budgets()
    assert value["cases"] == len(value["expected"]) == 53
    assert value["UUIDs"] == value["concurrent_UUIDs"] == 1
    assert value["restricted_application_pool_size"] == 5 and value["max_overflow"] == 0
    assert len(legacy) == 29 and sum(row["cases"] for row in legacy) == 429
    assert sum(row["UUIDs"] for row in legacy) == 69


def test_separate53_ACK_rejects_legacy_scope_expiry_or_untyped_authority(tmp_path):
    value = {"schema": pg53.SCOPE, "source": "frozen", "profile": "private", "cases": 53}
    path = acknowledgement(tmp_path, value)
    assert len(pg53.require_ack(path, value, now=NOW)) == 64
    mutations = [{"scope": "actual37-pg429-exclusive-v1"}, {"approved": 1}, {"approved": False},
                 {"expires_at_UTC": NOW.isoformat()}, {"expires_at_UTC": "2026-10-21T01:00:00"},
                 {"expires_at_UTC": (NOW + timedelta(hours=8, seconds=1)).isoformat()},
                 {"contract_sha256": "0" * 64}, {"extra": "authority"}]
    for mutation in mutations:
        path = acknowledgement(tmp_path, value, **mutation)
        with pytest.raises(ValueError):
            pg53.require_ack(path, value, now=NOW)


def test_new_source_profile_or_selection_is_not_authorized_by_an_old_ACK(tmp_path):
    value = {"schema": pg53.SCOPE, "source": "frozen", "profile": "private", "cases": 53}
    path = acknowledgement(tmp_path, value)
    for key in ("source", "profile", "cases"):
        changed = {**value, key: "changed"}
        with pytest.raises(ValueError, match="source/profile/53 identities"):
            pg53.require_ack(path, changed, now=NOW)


def test_changed_original_source_or_duplicate_identity_cannot_enter53(tmp_path):
    value = pg53.phase()
    mapping = tmp_path / "tests/ci_web37/pg-r30-ppl53.json"
    mapping.parent.mkdir(parents=True)
    for name in value["source_bindings"]:
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(pg53.ROOT / name, destination)
    mapping.write_text(json.dumps(value), encoding="utf8")
    assert pg53.phase(tmp_path)["cases"] == 53
    target = tmp_path / value["module"]
    target.write_bytes(target.read_bytes() + b"# changed source\n")
    with pytest.raises(ValueError, match="direct assertion or fixture source"):
        pg53.phase(tmp_path)
    changed = copy.deepcopy(value)
    changed["expected"][1] = changed["expected"][0]
    mapping.write_text(json.dumps(changed), encoding="utf8")
    with pytest.raises(ValueError, match="identity or UUID"):
        pg53.phase(tmp_path)


def test_missing_runtime_ACK_refuses_before_private_creation_or_SQL(tmp_path, monkeypatch):
    import psycopg2

    def forbidden(*args, **kwargs):
        pytest.fail("No SQL or private payload is allowed before the separate runtime ACK arguments")
    monkeypatch.setattr(psycopg2, "connect", forbidden)
    monkeypatch.setattr(run_postgres53, "_private_evidence", forbidden)
    monkeypatch.setattr(sys, "argv", ["run_postgres53.py", "--private", str(tmp_path / "private"),
                                     "--output", str(tmp_path / "public")])
    with pytest.raises(SystemExit) as error:
        run_postgres53.main()
    assert error.value.code == 2

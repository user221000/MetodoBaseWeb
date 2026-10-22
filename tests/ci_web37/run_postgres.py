"""Run source-bound PG37 phases only after an exclusive local/CI lease.

Plan-only performs collection and offline provenance checks. Runtime preserves
the original account37 UUID owner and authentic global Temp namespace. This
runner never creates roles, changes HBA, terminates backends or forces a DROP.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import traceback
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.scan_secrets import _private_evidence as private_directory
from tests.ci_google33.run_postgres import photo, role_catalog
from tests.ci_web37.evidence import boundary_before_payload, seal, write
from tests.ci_web37.pg_lease import contract, phase_budget, profile, require_ack
from tests.ci_web37.pg_plan import phases
from tests.ci_web37.reports import require_exact_junit
from tests.ci_web37.run_web import environment_photo, execute, observe_junit


def require_witnesses(path, phase):
    if phase["witness"] == "transition37":
        return 0
    records = [json.loads(line) for line in path.read_bytes().splitlines()]
    selected = [row["value"] for row in records if row["kind"] == phase["witness"]]
    if not selected:
        raise ValueError("A current37 runtime phase has no actual physical witness")
    expected_pools = [phase["pool"]] * len(selected)
    if phase["key"] == "legacy-r24-race":
        # The original fixture proves its base pool1 around the distinct real
        # race pool6. Keep every witness, with the exact setup/teardown trace.
        expected_pools = [1, 6, 6, 6, 6, 1]
        identity = phase["module"] + "::" + phase["expected"][0][1]
        expected_tests = [identity + " (setup)"] * 3 + [identity + " (teardown)"] * 3
        if (phase["pool"] != 6 or len(phase["expected"]) != 1 or len(records) != 6 or len(selected) != 6
                or [row["test"] for row in records] != expected_tests):
            raise ValueError("The original R24 baseline1/race6 witness trace differs")
    for row, expected_pool in zip(selected, expected_pools, strict=True):
        if phase["witness"] == "independent_qa37":
            valid = (row["revision"] == "20261020_account_security" and row["ORM"] == 41 and row["physical"] == 42
                     and row["FORCE_RLS"] == 32 and row["nonowner"] is True
                     and len(row["role_flags_and_owner_membership"]) == 5
                     and all(flag is False for flag in row["role_flags_and_owner_membership"]))
        else:
            valid = (row["revision"] == "20261020_account_security" and row["model_tables"] == 41
                     and row["physical_tables"] == 42 and row["FORCE_RLS_tables"] == 32
                     and row["nonowner"] is True and row["owner_membership"] is False and row["owned_tables"] == 0
                     and len(row["role_flags4"]) == 4 and all(flag is False for flag in row["role_flags4"])
                     and row["blank_contexts4"] is True and len(row["validated_foreign_keys_sha256"]) == 64)
        if (not valid or type(row["pool_size"]) is not int or row["pool_size"] != expected_pool
                or row["max_overflow"] != 0 or not row["history_index"]):
            raise ValueError("Actual37 role/schema/FORCE/index/context/pool witness differs")
    return len(selected)


def audit_leases(directory, environment):
    import psycopg2

    records = []
    for path in sorted(directory.glob("lease-*.json")):
        row = json.loads(path.read_bytes())
        if (row["state"] != "closed_absent" or row["sessions_before_drop"] != 0
                or row["absence_verified"] != "fresh_control_connection" or type(row["oid"]) is not int
                or row["initial_creation"] != "exclusive_xb_before_CREATE" or not row["planned_at"]
                or row["launcher_birth"] != row["launcher_birth_after_create"]
                or row["server_port"] != 55483 or row["server_host"] not in {"127.0.0.1", "127.0.0.1/32"}
                or row["database"] != "metodobase_test_account37_" + row["plan_id"]):
            raise ValueError("An actual37 UUID lease did not close with its original identity")
        records.append(row)
    if not records:
        raise ValueError("A runtime phase has no attributable current37 UUID")
    url = environment["METODOBASE_TEST_MIGRATOR_URL"].replace("postgresql+psycopg2://", "postgresql://", 1)
    with psycopg2.connect(url, connect_timeout=5) as db, db.cursor() as cursor:
        names = [row["database"] for row in records]
        cursor.execute("SELECT datname FROM pg_database WHERE datname=ANY(%s)", (names,))
        if cursor.fetchall():
            raise ValueError("An owned current37 database remains after normal closure")
        cursor.execute("SELECT datname,pid FROM pg_stat_activity WHERE datname=ANY(%s)", (names,))
        if cursor.fetchall():
            raise ValueError("An owned current37 session remains after normal closure")
    return len(records)


def journal(path, value):
    with path.open("ab") as output:
        output.write((json.dumps(value, sort_keys=True) + "\n").encode())
        output.flush()
        os.fsync(output.fileno())


def main():
    plan = phases()
    from web.database.schema_control import expected_head
    if expected_head() != "20261020_account_security":
        raise ValueError("Actual PG37 requires the current37 product; no historical fallback")
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--groups", nargs="+", choices=[row["key"] for row in plan])
    parser.add_argument("--pg-profile", type=Path)
    parser.add_argument("--lease-ack", type=Path)
    args = parser.parse_args()
    if not args.private.is_absolute() or not args.output.is_absolute() or args.output.exists():
        parser.error("Fresh absolute private/public paths are required")
    selected = args.groups or [row["key"] for row in plan]
    if len(selected) != len(set(selected)):
        parser.error("A current PG phase cannot be counted twice")
    if not args.plan_only and (args.pg_profile is None or args.lease_ack is None):
        parser.error("Runtime requires an explicit readonly profile and a source-bound Root ACK")
    private = private_directory(args.private)
    acl = boundary_before_payload(private)
    environment = dict(os.environ, PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1", PYTHON_DOTENV_DISABLED="1")
    for key in list(environment):
        upper = key.upper()
        if (upper == "DATABASE_URL" or upper.endswith("_DATABASE_URL") or upper.startswith(("AWS_", "S3_"))
                or any(name in upper for name in ("STRIPE", "MERCADOPAGO", "SMTP", "RESEND", "SENTRY", "GOOGLE_CLIENT", "OPENAI_API"))):
            environment.pop(key, None)
    environment.pop("_METODOBASE_TEST_ROOT", None)
    environment["_METODOBASE_TEST_ROOT"] = str(private / "metodobase-test-data")
    environment["METODOBASE_TEST_REDIS_URL"] = ""
    before = environment_photo()
    write(private / "before.json", before)
    result = {"accepted": False, "scope": "plan_only_no_SQL" if args.plan_only else "selected_actual37_PG_phases",
              "PostgreSQL_executed": False, "Redis": False, "Chrome": False, "Docker": False,
              "Desktop_runtime": False, "selected_groups": selected, "selected_complete_current429_catalog": len(selected) == 29,
              "current429_runtime_accepted": False,
              "phases": [], "source_commit": before["source"]["HEAD"]}
    leases = None
    pg_before = roles = None
    pip_before = execute([sys.executable, "-m", "pip", "check"], ROOT, environment, private / "pip-before.private.log")
    try:
        if pip_before:
            raise ValueError("Dependency consistency failed before current PG preparation")
        argv = [sys.executable, "-B", "-X", "utf8", "tests/ci_web37/collect.py", "--output", str(private / "oracle.json"),
                "--fixture-output", str(private / "bindings.json"), *[row["module"] for row in plan]]
        code = execute(argv, ROOT, environment, private / "collection.private.log")
        if code or set(map(tuple, json.loads((private / "oracle.json").read_bytes()))) != {
                tuple(identity) for row in plan for identity in row["expected"]}:
            raise ValueError("Actual current37 PG collection differs from the complete429 required identities")
        result["collected_cases"] = 429
        if not args.plan_only:
            lease_contract = contract(ROOT, before["source"], args.pg_profile, selected)
            result["lease_ACK_sha256"] = require_ack(args.lease_ack, lease_contract)
            write(private / "lease-contract.json", lease_contract)
            environment.update(profile(args.pg_profile, expected_sha256=lease_contract["profile_sha256"]))
            pg_bin = Path(environment["METODOBASE_TEST_PG_BIN"]).resolve(strict=True)
            pg_before = photo(ROOT, pg_bin)
            roles = role_catalog(environment)
            result["PostgreSQL_executed"] = True
            write(private / "PG-before.json", pg_before)
            write(private / "roles-before.private.json", roles)
            lease_root = private_directory(Path(tempfile.gettempdir()) / ("metodobase-account37-author-pg-ci37-" + uuid.uuid4().hex))
            leases = lease_root / "leases"
            leases.mkdir()
            environment["ACCOUNT37_PRIVATE_LEASES"] = str(leases)
            write(private / "lease-namespace.private.json", {"path": str(leases), "TEMP_TMP_unchanged": True})
            for phase in plan:
                if phase["key"] not in selected:
                    continue
                phase_ACK_sha256 = require_ack(args.lease_ack, lease_contract)
                directory = private / phase["key"]
                directory.mkdir()
                for name in ("evidence", "r24", "r25", "races", "journal"):
                    (directory / name).mkdir()
                child_env = dict(environment, METODOBASE_TEST_EVIDENCE_DIR=str(directory / "evidence"),
                    R24_PG_OUTPUT=str(directory / "r24"), R25_EVIDENCE_DIR=str(directory / "r25"),
                    SEC_GOOGLE_PRIVATE_RECEIPTS=str(directory / "races"),
                    CI_WEB37_PG_WITNESSES=str(directory / "witnesses.private.jsonl"))
                argv = [sys.executable, "-B", "-X", "utf8", "tests/run_isolated.py", phase["module"],
                    "-p", "tests.ci_web37.pg_observer", "-p", "tests.ci_web37.scope",
                    "--web37-execution-journal", str(directory / "journal"), "-q", "--tb=short",
                    "--basetemp=" + str(directory / "pytest-data"), "--junitxml=" + str(directory / "pytest.xml")]
                write(directory / "command.private.json", argv)
                leases_before = len(list(leases.glob("lease-*.json")))
                journal(private / "phases.private.jsonl", {"event": "START", "group": phase["key"],
                    "closed_UUIDs_before": leases_before, "lease_ACK_sha256": phase_ACK_sha256})
                code = execute(argv, ROOT, child_env, directory / "pytest.private.log")
                observed = observe_junit(directory / "pytest.xml", phase["expected"]) if (directory / "pytest.xml").exists() else {}
                row = {"group": phase["key"], "pytest_exit": code, **observed, "accepted": False}
                result["phases"].append(row)
                row["normally_closed_UUIDs_fresh_absent_after_child"] = audit_leases(leases, environment)
                row["new_UUIDs"] = row["normally_closed_UUIDs_fresh_absent_after_child"] - leases_before
                row["UUID_budget"] = phase_budget(phase["key"], row["new_UUIDs"], succeeded=code == 0)
                journal(private / "phases.private.jsonl", {"event": "FINISH", **row})
                if code:
                    break
                require_exact_junit((directory / "pytest.xml").read_bytes(), phase["expected"])
                row["physical_witnesses"] = require_witnesses(directory / "witnesses.private.jsonl", phase)
                row["accepted"] = True
        result["accepted"] = args.plan_only or len(result["phases"]) == len(selected) and all(row["accepted"] for row in result["phases"])
    except Exception as error:  # noqa: BLE001 -- retain the exact refusal before public rejection
        (private / "runner-error.private.log").write_text(traceback.format_exc(), encoding="utf8")
        result.update(accepted=False, runner_error_class=type(error).__name__)
    finally:
        if leases is not None:
            try:
                result["normally_closed_UUIDs_fresh_absent"] = audit_leases(leases, environment)
                for path in sorted(leases.glob("lease-*.json")):
                    (private / path.name).write_bytes(path.read_bytes())
                pg_after = photo(ROOT, pg_bin)
                write(private / "PG-after.json", pg_after)
                after_roles = role_catalog(environment)
                write(private / "roles-after.private.json", after_roles)
                result["PG_binaries_sources_packages_roles_quiet"] = pg_before == pg_after and roles == after_roles
                result["accepted"] = result["accepted"] and result["PG_binaries_sources_packages_roles_quiet"]
            except Exception as error:  # noqa: BLE001 -- no destructive cleanup fallback
                (private / "lease-refusal.private.log").write_text(traceback.format_exc(), encoding="utf8")
                result.update(accepted=False, lease_refusal_class=type(error).__name__)
        after = environment_photo()
        write(private / "after.json", after)
        pip_after = execute([sys.executable, "-m", "pip", "check"], ROOT, environment, private / "pip-after.private.log")
        quiet = before == after
        result.update(source_packages_binaries_quiet=quiet, packages=len(before["packages"]), pip_before=pip_before,
                      pip_after=pip_after, accepted=result["accepted"] and quiet and pip_before == pip_after == 0)
        result["current429_runtime_accepted"] = result["accepted"] and not args.plan_only and len(selected) == 29
    print(json.dumps(seal(private, args.output, result, acl)))
    return int(not result["accepted"])


if __name__ == "__main__":
    raise SystemExit(main())

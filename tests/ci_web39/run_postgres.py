"""Run the separate current39 PostgreSQL phases with exact private evidence.

The historical429/53/27 assertions retain their own37 source and lease. This
entrypoint requires a fresh39 profile/generation/phase ACK and does not provision
roles, restart PostgreSQL, terminate a backend, or force a database drop.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import traceback
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.scan_secrets import _private_evidence
from tests.ci_google33.run_postgres import photo, role_catalog
from tests.ci_web37.evidence import boundary_before_payload, seal, write
from tests.ci_web37.run_postgres import audit_leases
from tests.ci_web39.run_web import environment_photo, execute, observe_junit
from tests.ci_web38.reports import require_exact_junit
from tests.ci_web39 import pg_contract
from tests.ci_web39.pg_control import check_control_generation

CASES = {
    "core": (
        "test_pg39_restricted_role_durable_self_requests_and_persisted_A_B_RLS",
        "test_pg39_MFA_actor_factor_budget_atomic_closure_and_real_deletes_preserve_B",
        "test_pg39_missing_policy_commit_failure_and_prior_flush_have_zero_destructive_effect",
        "test_pg39_personal_facts_keysets_and_owner_exclusion_preserve_B",
    ),
    "restore": (
        "test_pg39_old_active_snapshot_requires_live_suppression_and_physical_binding_before_access",
    ),
}


def identities(name):
    selected = pg_contract.phase(name)
    module = selected["module"].removesuffix(".py").replace("/", ".")
    return [(module, case) for case in CASES[name]]


def require_runtime_evidence(directory, name, value):
    """Require the fixture's actual source-bound close and physical witnesses."""
    selected = pg_contract.phase(name)
    runtime = json.loads((directory / ("pg39-" + name + "-runtime.json")).read_bytes())
    if (any(type(runtime.get(key)) is not int for key in ("created_UUIDs", "normally_closed_UUIDs", "max_concurrent_UUIDs"))
            or runtime != {"phase": name, "contract_sha256": pg_contract.digest(value),
                    "FileSetDigest": value["FileSetDigest"],
                    "created_UUIDs": selected["UUIDs"],
                    "normally_closed_UUIDs": selected["UUIDs"], "max_concurrent_UUIDs": 1}):
        raise ValueError("The actual39 fixture did not close its exact source-bound UUID budget")
    if name == "core":
        physical = json.loads((directory / "pg39-core-physical.json").read_bytes())
        if (physical.get("revision") != "20261023_privacy_disposition"
                or physical.get("ORM_tables_observed") != 44
                or physical.get("physical_tables_observed") != 45
                or physical.get("FORCE_RLS_observed") != 35
                or physical.get("role_five_flags") != [False] * 5
                or physical.get("application_pool") != 1 or physical.get("overflow") != 0
                or set(physical.get("protected_tables_FORCE_RLS", [])) != {
                    "privacy_requests", "privacy_disposition_items", "product_analytics_facts"}):
            raise ValueError("The actual39 restricted role/schema/FORCE RLS witness differs")
    else:
        for phase, expected_count in (("source", 2), ("target", 1)):
            tools = json.loads((directory / ("pg39-restore-" + phase + "-tools.json")).read_bytes())
            rows = tools.get("tools", [])
            if (tools.get("phase") != phase or tools.get("FileSetDigest") != value["FileSetDigest"]
                    or tools.get("no_process_or_backend_termination_by_observer") is not True
                    or len(rows) != expected_count or any(
                        row.get("normally_waited") is not True or type(row.get("exit_code")) is not int or row["exit_code"] != 0
                        or row.get("fresh_absent_after_wait") is not True for row in rows)):
                raise ValueError("Actual backup/restore tools lack normal attributed closure")
    return selected["UUIDs"]


def child_environment(private):
    """Providers remain off; the explicit profile is the only PG authority."""
    result = dict(os.environ, PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1", PYTHON_DOTENV_DISABLED="1")
    for key in list(result):
        upper = key.upper()
        if (upper == "DATABASE_URL" or upper.endswith("_DATABASE_URL") or upper.startswith(("AWS_", "S3_"))
                or any(word in upper for word in ("STRIPE", "MERCADOPAGO", "SMTP", "RESEND", "SENTRY", "GOOGLE_CLIENT", "OPENAI_API"))):
            result.pop(key, None)
    result.update(_METODOBASE_TEST_ROOT=str(Path(tempfile.gettempdir()) /
                  ("metodobase-test-privacy39-" + uuid.uuid4().hex)), METODOBASE_TEST_REDIS_URL="")
    return result


def pytest_alias_target(path, raw_target, base):
    """Recognize only pytest's own current-to-numbered-sibling directory alias."""
    target = Path(raw_target)
    stem = path.name.removesuffix("current")
    if (not path.name.endswith("current") or not stem or not path.is_relative_to(base)
            or not target.is_absolute() or target.parent != path.parent
            or not target.name.startswith(stem) or not target.name[len(stem):].isdigit()):
        raise ValueError("Unexpected pytest scratch alias; no unlink permitted")
    return target


def close_pytest_aliases(private):
    """Journal/remove only generated scratch aliases after the child has closed.

    Pytest creates these convenience symlinks on Linux. The unchanged private
    archive gate forbids symlinks. Their real sibling directories and every
    payload byte stay intact; unknown links, junctions and targets fail closed.
    """
    base = private / "pytest-data"
    rows = []
    if base.exists():
        for path in sorted(base.rglob("*")):
            info = path.lstat()
            if not stat.S_ISLNK(info.st_mode):
                continue
            raw = os.readlink(path)
            target = pytest_alias_target(path, raw, base)
            if target.resolve(strict=True) != target or not stat.S_ISDIR(target.lstat().st_mode):
                raise ValueError("The pytest alias target is not its plain numbered sibling")
            rows.append((path, raw, info.st_dev, info.st_ino, target))
    write(private / "pytest-aliases-before-unlink.private.json", {
        "scope": "closed_child_generated_pytest_scratch_symlinks_only",
        "targets_and_payloads_preserved": True,
        "aliases": [{"path": path.relative_to(private).as_posix(),
                     "target": target.relative_to(private).as_posix(), "device": device, "inode": inode}
                    for path, _, device, inode, target in rows]})
    for path, raw, device, inode, _ in rows:
        current = path.lstat()
        if (not stat.S_ISLNK(current.st_mode) or (current.st_dev, current.st_ino) != (device, inode)
                or os.readlink(path) != raw):
            raise ValueError("A generated pytest alias changed after its private receipt")
        path.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--phase", choices=tuple(CASES), required=True)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pg-profile", type=Path, required=True)
    parser.add_argument("--pg-generation", type=Path, required=True)
    parser.add_argument("--lease-ack", type=Path, required=True)
    args = parser.parse_args(argv)
    from web.database.schema_control import expected_head
    if expected_head() != "20261023_privacy_disposition":
        parser.error("The separate current39 gate requires the actual39 product")
    if not args.private.is_absolute() or not args.output.is_absolute() or args.output.exists():
        parser.error("Fresh absolute private and public paths are required")
    private = _private_evidence(args.private)
    acl = boundary_before_payload(private)
    environment = child_environment(private)
    before = environment_photo()
    write(private / "before.json", before)
    selected = pg_contract.phase(args.phase)
    expected = identities(args.phase)
    result = {"accepted": False, "scope": "separate_current39_PG_" + args.phase,
              "phase": args.phase, "source_commit": before["source"]["HEAD"],
              "PostgreSQL_executed": False, "historical429_53_27_retargeted": False,
              "Desktop_runtime": False, "Chrome": False, "Docker": False, "Redis": False,
              "current39_complete_PG_suite": False}
    leases = pg_before = roles = None
    pip_before = execute([sys.executable, "-m", "pip", "check"], ROOT, environment, private / "pip-before.private.log")
    try:
        if pip_before:
            raise ValueError("Dependency consistency failed before current39 execution")
        collected = execute([sys.executable, "-B", "-X", "utf8", "tests/ci_web38/collect.py",
            "--output", str(private / "oracle.json"), selected["module"]], ROOT,
            environment, private / "collection.private.log")
        if collected or json.loads((private / "oracle.json").read_bytes()) != list(map(list, expected)):
            raise ValueError("The independently collected original39 identities differ")
        value = pg_contract.build_contract(args.phase, args.pg_profile, args.pg_generation)
        result["lease_ACK_sha256"] = pg_contract.require_ack(args.lease_ack, value)
        write(private / "lease-contract.private.json", value)
        from tests.ci_web37.pg_lease import profile
        config = profile(args.pg_profile, expected_sha256=value["profile_sha256"])
        environment.update(config, PG39_PHASE=args.phase, PG39_PROFILE=str(args.pg_profile),
                           PG39_GENERATION=str(args.pg_generation), PG39_ACK=str(args.lease_ack))
        check_control_generation(value, config)
        pg_bin = Path(config["METODOBASE_TEST_PG_BIN"])
        pg_before, roles = photo(ROOT, pg_bin), role_catalog(environment)
        write(private / "PG-before.json", pg_before)
        write(private / "roles-before.private.json", roles)
        lease_root = _private_evidence(Path(tempfile.gettempdir()) /
            ("metodobase-account37-author-pg-privacy39-" + uuid.uuid4().hex))
        leases = lease_root / "leases"
        leases.mkdir()
        evidence = private / "evidence"
        journal = private / "execution-journal"
        evidence.mkdir()
        journal.mkdir()
        environment.update(ACCOUNT37_PRIVATE_LEASES=str(leases), METODOBASE_TEST_EVIDENCE_DIR=str(evidence))
        write(private / "lease-namespace.private.json", {"path": str(lease_root), "TEMP_TMP_unchanged": True})
        command = [sys.executable, "-B", "-X", "utf8", "tests/run_isolated.py", selected["module"],
            "-p", "tests.ci_web39.pg_admission", "--pg39-phase", args.phase,
            "--pg39-profile", str(args.pg_profile), "--pg39-generation", str(args.pg_generation),
            "--pg39-ack", str(args.lease_ack),
            "-p", "tests.ci_web37.scope", "--web37-execution-journal", str(journal), "-q", "--tb=short",
            "--basetemp=" + str(private / "pytest-data"), "--junitxml=" + str(private / "pytest.xml")]
        write(private / "command.private.json", command)
        pg_contract.require_ack(args.lease_ack, value)
        result["PostgreSQL_executed"] = True
        code = execute(command, ROOT, environment, private / "pytest.private.log")
        result.update(pytest_exit=code, **observe_junit(private / "pytest.xml", expected))
        if code == 0:
            require_exact_junit((private / "pytest.xml").read_bytes(), expected)
            result["runtime_UUIDs"] = require_runtime_evidence(evidence, args.phase, value)
            result["accepted"] = True
    except Exception as error:  # noqa: BLE001 -- preserve every refused phase privately
        (private / "runner-error.private.log").write_text(traceback.format_exc(), encoding="utf8")
        result.update(accepted=False, runner_error_class=type(error).__name__)
    finally:
        if leases is not None:
            try:
                count = audit_leases(leases, environment)
                result["normally_closed_UUIDs_fresh_absent"] = count
                for path in sorted(leases.glob("*.json")):
                    (private / path.name).write_bytes(path.read_bytes())
                closed = list((leases.parent / "pool-close").glob("*.json"))
                if count != selected["UUIDs"] or len(closed) != count:
                    raise ValueError("The current39 UUID/common-close receipt budget differs")
                for path in closed:
                    receipt = json.loads(path.read_bytes())
                    if receipt.get("accepted") is not True or receipt.get("natural_drain_confirmed") is not True:
                        raise ValueError("A current39 common-close receipt was rejected")
                    (private / ("close-" + path.name)).write_bytes(path.read_bytes())
                pg_after, roles_after = photo(ROOT, pg_bin), role_catalog(environment)
                write(private / "PG-after.json", pg_after)
                write(private / "roles-after.private.json", roles_after)
                unchanged = pg_before == pg_after and roles == roles_after
                result["PG_binaries_sources_packages_roles_quiet"] = unchanged
                result["accepted"] = result["accepted"] and unchanged
                if pg_contract.build_contract(args.phase, args.pg_profile, args.pg_generation) != value:
                    raise ValueError("The current39 source/profile/generation changed during execution")
            except Exception as error:  # noqa: BLE001 -- no destructive cleanup fallback
                (private / "lease-refusal.private.log").write_text(traceback.format_exc(), encoding="utf8")
                result.update(accepted=False, lease_refusal_class=type(error).__name__)
        after = environment_photo()
        write(private / "after.json", after)
        pip_after = execute([sys.executable, "-m", "pip", "check"], ROOT, environment, private / "pip-after.private.log")
        quiet = before == after
        result.update(source_packages_binaries_quiet=quiet, pip_before=pip_before, pip_after=pip_after,
                      accepted=result["accepted"] and quiet and pip_before == pip_after == 0)
    close_pytest_aliases(private)
    print(json.dumps(seal(private, args.output, result, acl)))
    return int(not result["accepted"])


if __name__ == "__main__":
    raise SystemExit(main())

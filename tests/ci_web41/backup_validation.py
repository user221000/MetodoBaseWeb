"""Private, finite backup checks; this runner never owns a PostgreSQL cluster.

Only a fixed count/identity summary is public. Logs, JUnit and database/object
fixtures stay below a new private boundary. Timeouts stop this runner's child
only and require coordinated fixture cleanup; no SQL termination is attempted.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "metodobase-backup-validation-v1"
JUNIT_LIMIT = 2 * 1024 * 1024
LOG_LIMIT = 16 * 1024 * 1024
SOURCE_LIMIT = 2 * 1024 * 1024
CHILD_TIMEOUT = 880  # Two bounded five-second termination waits keep total below900.
REASONS = frozenset({"arguments", "artifact_boundary", "artifact_changed", "source_graph", "private_boundary",
                     "postgres_environment", "junit_invalid", "junit_identities", "child_timeout", "source_changed",
                     "log_bound", "test_gate", "validation_error", "output_boundary", "linux_required"})
PG_NAMES = (
    ("tests.integration_backup_capture_s3_postgres", "test_pg18_exported_snapshot_excludes_concurrent_new_reference_from_dump_and_objects"),
    ("tests.integration_backup_capture_s3_postgres", "test_pg18_restricted_rls_reader_is_rejected_instead_of_empty_success"),
    ("tests.integration_backup_capture_s3_postgres", "test_pg18_actual_legacy_reference_count_produces_partial_snapshot"),
    ("tests.integration_backup_capture_full_postgres", "test_full_current_schema_and_two_tenants_survive_encrypted_capture_restore"),
)
JOB_NAMES = (
    "test_current_and_partial_are_published_and_exactly_read_back[20261031_gym_equipment-legacy0-verified_current_resources-0]",
    "test_current_and_partial_are_published_and_exactly_read_back[20261031_gym_equipment-legacy1-partial_legacy_references-2]",
    "test_current_and_partial_are_published_and_exactly_read_back[20261102_payment_refund_facts-legacy0-verified_current_resources-0]",
    "test_current_and_partial_are_published_and_exactly_read_back[20261102_payment_refund_facts-legacy1-partial_legacy_references-2]",
    "test_capture_failure_prevents_any_publication_and_withholds_private_error",
    "test_tampered_local_manifest_prevents_publication",
    "test_fetch_readback_failure_never_seals_success",
    *("test_receipt_requires_nonce_authentication_coverage_and_exact_exit[" + value + "]" for value in ("nonce", "truncated", "mac", "exit", "coverage", "readback")),
    "test_partial_worker_exit_without_receipt_is_not_success",
    "test_cli_exception_output_has_no_secret_or_traceback",
    "test_cli_preserves_exact_explicit_supported_revision[20261031_gym_equipment]",
    "test_cli_preserves_exact_explicit_supported_revision[20261102_payment_refund_facts]",
    *("test_cli_rejects_unknown_or_absent_revision_before_worker_or_publication[" + value + "]" for value in ("unknown", "private-secret-must-not-be-logged", "None")),
    "test_non_linux_entrypoint_fails_before_any_private_or_worker_payload",
    "test_supervisor_accepts_only_nonce_bound_verified_receipt[legacy0-0]",
    "test_supervisor_accepts_only_nonce_bound_verified_receipt[legacy1-2]",
    "test_worker_withholds_secret_exception_and_incomplete_result",
    "test_worker_exit_two_requires_published_and_readback_receipt[legacy0-0]",
    "test_worker_exit_two_requires_published_and_readback_receipt[legacy1-2]",
    *("test_complete_receipt_cannot_override_failed_supervision[outcome" + str(value) + "]" for value in range(4)),
    "test_esrch_does_not_turn_unknown_proc_state_into_verified_closure",
    "test_leader_observation_reserves_identity_without_poll_or_reap",
    "test_malformed_proc_rows_remain_unknown[1 (process) R 1 invalid]",
    "test_malformed_proc_rows_remain_unknown[1 (process) R]",
    "test_malformed_proc_rows_remain_unknown[malformed]",
    "test_observation_failure_cannot_block_owned_term_and_kill[IndexError]",
    "test_observation_failure_cannot_block_owned_term_and_kill[OSError]",
    "test_observation_failure_cannot_block_owned_term_and_kill[PermissionError]",
    "test_observation_failure_cannot_block_owned_term_and_kill[ValueError]",
    "test_real_proc_failure_still_kills_owned_worker_and_preserves_bystander",
    "test_recovered_observation_preserves_failure_even_after_verified_empty_group",
    "test_signal_failure_still_attempts_kill_and_never_claims_closure",
    "test_verified_empty_group_needs_no_signals",
    "test_real_child_exit_and_secret_environment_are_not_logged",
    "test_wall_timeout_kills_only_own_group_including_term_ignoring_descendant",
    "test_leader_success_with_living_descendant_is_failure_and_closes_group",
)
MODULES = {"job": ("tests/test_backup_job.py",), "postgres": (
    "tests/integration_backup_capture_s3_postgres.py", "tests/integration_backup_capture_full_postgres.py")}
PG_ENV = ("METODOBASE_BACKUP_CAPTURE_TEST_ACK", "METODOBASE_TEST_MIGRATOR_URL", "METODOBASE_TEST_PG_BIN")
SOURCE_BASE = (
    "scripts/backup_capture_s3.py", "scripts/backup_restore.py", "scripts/backup_remote.py", "scripts/backup_job.py",
    "scripts/scan_secrets.py", "scripts/reviewed_scan_locations.py", "tests/isolation.py", "tests/__init__.py",
    "tests/ci_web41/__init__.py", "tests/ci_web41/backup_validation.py", "tests/test_backup_validation.py",
    "tests/test_backup_job.py", "tests/test_backup_capture_s3.py", "tests/test_backup_remote.py",
    "tests/integration_backup_capture_s3_postgres.py", "tests/integration_backup_capture_full_postgres.py",
    "db_bootstrap.py", "alembic.ini", "web/__init__.py", "web/settings.py", "config/settings.py",
    "requirements_web.lock", "requirements-container.lock", "requirements-test.lock",
)
SOURCE_PATTERNS = ("web/database/**/*.py", "web/database/**/*.json", "web/storage/*.py", "config/*.py")


class ValidationError(ValueError):
    def __init__(self, reason):
        self.reason = reason
        super().__init__("Backup validation failed")


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValidationError("arguments")


def expected(mode):
    if mode == "job":
        return tuple(("tests.test_backup_job", name) for name in JOB_NAMES)
    if mode == "postgres":
        return PG_NAMES
    raise ValidationError("arguments")


def _plain(path, maximum):
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > maximum
            or getattr(info, "st_file_attributes", 0) & 1024 or path.resolve(strict=True) != path.absolute()):
        raise ValidationError("artifact_boundary")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        raw = stream.read(maximum + 1)
        finished = os.fstat(stream.fileno())
    after = path.lstat()
    identities = {(row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns, row.st_mode, row.st_nlink)
                  for row in (info, opened, finished, after)}
    if (len(identities) != 1 or info.st_ctime_ns != after.st_ctime_ns
            or opened.st_ctime_ns != finished.st_ctime_ns or len(raw) != info.st_size or len(raw) > maximum):
        raise ValidationError("artifact_changed")
    return raw


def source_photo(root=ROOT):
    names = set(SOURCE_BASE)
    for pattern in SOURCE_PATTERNS:
        names.update(path.relative_to(root).as_posix() for path in root.glob(pattern))
    if (root / "scripts/__init__.py").exists():
        names.add("scripts/__init__.py")
    if not len(SOURCE_BASE) < len(names) <= 512:
        raise ValidationError("source_graph")
    result = {}
    for name in sorted(names):
        raw = _plain(root / name, SOURCE_LIMIT)
        result[name] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    if sum(row["bytes"] for row in result.values()) > 16 * 1024 * 1024:
        raise ValidationError("source_graph")
    return result


def source_digest(photo):
    return hashlib.sha256(json.dumps(photo, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _new_path(value):
    path = Path(value)
    if (not path.is_absolute() or path.exists() or path.is_symlink()
            or path.parent.resolve(strict=True) != path.parent.absolute()
            or path.resolve().is_relative_to(ROOT.resolve())):
        raise ValidationError("private_boundary")
    return path


def _private_boundary(path):
    from scripts.scan_secrets import _private_evidence, _verify_private_boundary
    _private_evidence(path)
    sid = None
    if os.name == "nt":
        identity = subprocess.run(["whoami", "/user", "/fo", "csv", "/nh"],
                                  capture_output=True, text=True, check=True, timeout=10)
        if len(identity.stdout) > 8192:
            raise ValidationError("private_boundary")
        sid = next(csv.reader(io.StringIO(identity.stdout)))[1]
    _verify_private_boundary(path, sid)
    info = path.lstat()
    return (info.st_dev, info.st_ino), sid


def _require_private(path, identity, sid):
    from scripts.scan_secrets import _verify_private_boundary
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or (info.st_dev, info.st_ino) != identity
            or path.resolve(strict=True) != path.absolute() or getattr(info, "st_file_attributes", 0) & 1024):
        raise ValidationError("private_boundary")
    _verify_private_boundary(path, sid)


def _pg_values(values):
    from tests.isolation import validate_postgres_test_url
    if (set(values) != set(PG_ENV) or any(type(value) is not str for value in values.values())
            or values[PG_ENV[0]] != "isolated-pg18"):
        raise ValidationError("postgres_environment")
    validate_postgres_test_url(values[PG_ENV[1]])
    port = urlsplit(values[PG_ENV[1]]).port
    if port is not None and not 1 <= port <= 65535:
        raise ValidationError("postgres_environment")
    binary = Path(values[PG_ENV[2]])
    if not binary.is_absolute() or binary.resolve(strict=True) != binary.absolute() or not binary.is_dir():
        raise ValidationError("postgres_environment")
    suffix = ".exe" if os.name == "nt" else ""
    for name in ("pg_dump", "pg_restore"):
        info = (binary / (name + suffix)).lstat()
        path = binary / (name + suffix)
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or path.resolve(strict=True) != path.absolute() or getattr(info, "st_file_attributes", 0) & 1024):
            raise ValidationError("postgres_environment")
    return dict(values)


def child_environment(mode, private, inherited):
    pg = _pg_values({name: inherited.get(name, "") for name in PG_ENV}) if mode == "postgres" else {}
    result = {name: inherited[name] for name in ("PATH", "SystemRoot", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "LANG", "LC_ALL", "TZ") if name in inherited}
    for name in ("home", "temp"):
        (private / name).mkdir(mode=0o700)
    result.update(TEMP=str(private / "temp"), TMP=str(private / "temp"), TMPDIR=str(private / "temp"),
                  HOME=str(private / "home"), USERPROFILE=str(private / "home"),
                  PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8",
                  PYTHON_DOTENV_DISABLED="1", _METODOBASE_TEST_ROOT=str(private / "temp/metodobase-test-backup"))
    result.update(pg)
    return result


def child_main(mode, private):
    """Internal entry: fixed pytest arguments after the existing isolation API."""
    expected(mode)
    private = Path(private)
    values = _pg_values({name: os.environ.get(name, "") for name in PG_ENV}) if mode == "postgres" else {}
    for name in PG_ENV:
        os.environ.pop(name, None)
    from tests.isolation import block_external_sockets, prepare_environment
    prepare_environment(discard_inherited=True)
    os.environ.update(values)
    block_external_sockets()
    import pytest
    return int(pytest.main([*MODULES[mode], "--noconftest", "-o", "addopts=", "-p", "no:cacheprovider", "-q",
                           "--tb=short", "--basetemp=" + str(private / "pytest-data"),
                           "--junitxml=" + str(private / "junit.private.xml")]))


def run_child(mode, private, environment):
    command = [sys.executable, "-B", "-X", "utf8", "-c",
               "import sys;from tests.ci_web41.backup_validation import child_main;raise SystemExit(child_main(sys.argv[1],sys.argv[2]))",
               mode, str(private)]
    fd = os.open(private / "pytest.private.log", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as log:
        process = subprocess.Popen(command, cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=os.name == "posix")
        try:
            return process.wait(timeout=CHILD_TIMEOUT), False
        except subprocess.TimeoutExpired:
            # This PID only. The fixture owner must inspect/close any databases;
            # this generic runner never terminates SQL sessions or a cluster.
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass  # Still fail with cleanup_required; never touch a cluster.
            return None, True


def parse_junit(raw, mode):
    if type(raw) is not bytes or not 0 < len(raw) <= JUNIT_LIMIT or b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValidationError("junit_invalid")
    text = raw.decode("utf8")
    if "\x00" in text:
        raise ValidationError("junit_invalid")
    root = ET.fromstring(text)
    if root.tag != "testsuites" or len(root) != 1 or root[0].tag != "testsuite":
        raise ValidationError("junit_invalid")
    suite = root[0]
    if any(row.tag != "testcase" for row in suite):
        raise ValidationError("junit_invalid")
    rows = list(suite)
    if list(root.iter("testcase")) != rows or len(list(root.iter("testsuite"))) != 1:
        raise ValidationError("junit_invalid")
    ids = [(row.get("classname"), row.get("name")) for row in rows]
    if len(ids) != len(set(ids)) or set(ids) != set(expected(mode)):
        raise ValidationError("junit_identities")
    counts = {"tests": len(rows), "failures": 0, "errors": 0, "skips": 0}
    for row in rows:
        outcomes = [node.tag for node in row if node.tag in {"failure", "error", "skipped"}]
        if len(outcomes) > 1 or any(node.tag not in {"failure", "error", "skipped", "system-out", "system-err", "properties"} for node in row):
            raise ValidationError("junit_invalid")
        for tag in ("system-out", "system-err", "properties"):
            if sum(node.tag == tag for node in row) > 1:
                raise ValidationError("junit_invalid")
        for node in row:
            if node.tag == "properties":
                if any(item.tag != "property" or len(item) or set(item.attrib) != {"name", "value"} for item in node):
                    raise ValidationError("junit_invalid")
            elif len(node):
                raise ValidationError("junit_invalid")
        if outcomes:
            counts[{"failure": "failures", "error": "errors", "skipped": "skips"}[outcomes[0]]] += 1
    for attr, key in (("tests", "tests"), ("failures", "failures"), ("errors", "errors"), ("skipped", "skips")):
        text = suite.get(attr, "")
        if not re.fullmatch(r"0|[1-9][0-9]*", text) or int(text) != counts[key]:
            raise ValidationError("junit_invalid")
    return counts


def _write_new(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf8") as stream:
        stream.write(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")


def validate(mode, private, summary):
    expected(mode)
    if mode == "job" and not (os.name == "posix" and sys.platform.startswith("linux")):
        raise ValidationError("linux_required")
    before = source_photo()
    summary.update(source_sha256=before["tests/ci_web41/backup_validation.py"]["sha256"],
                   source_files_digest=source_digest(before), source_file_count=len(before))
    identity, sid = _private_boundary(private)
    _write_new(private / "source-before.private.json", before)
    environment = child_environment(mode, private, os.environ)
    child_exit, timed_out = run_child(mode, private, environment)
    summary.update(pytest_exit=child_exit, cleanup_required=timed_out)
    _require_private(private, identity, sid)
    after = source_photo()
    _write_new(private / "source-after.private.json", after)
    summary["source_quiet"] = before == after
    if timed_out:
        raise ValidationError("child_timeout")
    if not summary["source_quiet"]:
        raise ValidationError("source_changed")
    if (private / "pytest.private.log").stat().st_size > LOG_LIMIT:
        raise ValidationError("log_bound")
    counts = parse_junit(_plain(private / "junit.private.xml", JUNIT_LIMIT), mode)
    summary.update(observed_cases=counts["tests"], passed=counts["tests"] - counts["failures"] - counts["errors"] - counts["skips"],
                   failures=counts["failures"], errors=counts["errors"], skips=counts["skips"])
    if type(child_exit) is not int or child_exit != 0 or any(counts[key] for key in ("failures", "errors", "skips")):
        raise ValidationError("test_gate")
    summary["accepted"] = True


def main(argv=None):
    summary = {"schema": SCHEMA, "mode": "invalid", "accepted": False, "source_sha256": None,
               "source_files_digest": None, "source_file_count": 0, "expected_cases": 0, "observed_cases": 0,
               "passed": 0, "failures": 0, "errors": 0, "skips": 0, "pytest_exit": None,
               "source_quiet": False, "cleanup_required": False, "failure_reason": None, "error_class": None,
               "gate_exit": 1, "limits": {"private_log_and_JUnit": True, "child_timeout_seconds": CHILD_TIMEOUT,
               "JUnit_max_bytes": JUNIT_LIMIT, "no_cluster_lifecycle": True, "no_provider_calls": True,
               "no_production_or_scheduler_acceptance": True}}
    output = None
    try:
        parser = _Parser(description="Run finite private backup validation")
        parser.add_argument("--mode", required=True, choices=("job", "postgres"))
        parser.add_argument("--private", required=True)
        parser.add_argument("--output", required=True)
        args = parser.parse_args(argv)
        summary.update(mode=args.mode, expected_cases=len(expected(args.mode)))
        output = _new_path(args.output)
        private = _new_path(args.private)
        if private == output:
            raise ValidationError("private_boundary")
        validate(args.mode, private, summary)
        summary["gate_exit"] = 0
    except (ValueError, OSError, RuntimeError, TypeError, LookupError, StopIteration,
            ArithmeticError, ImportError, subprocess.SubprocessError, ET.ParseError, AssertionError) as error:
        summary["failure_reason"] = error.reason if isinstance(error, ValidationError) and error.reason in REASONS else "validation_error"
        summary["error_class"] = type(error).__name__ if type(error).__name__ in {"ValidationError", "ValueError", "OSError", "FileNotFoundError", "PermissionError", "RuntimeError", "ParseError", "TimeoutExpired"} else "Exception"
    if output is not None:
        try:
            _write_new(output, summary)
        except OSError:
            summary.update(accepted=False, gate_exit=1, failure_reason="output_boundary", error_class="OSError")
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
    return summary["gate_exit"]


if __name__ == "__main__":
    raise SystemExit(main())

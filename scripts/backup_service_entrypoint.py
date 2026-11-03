"""Run one bounded backup and accept only its authenticated, closed receipt.

This entrypoint does not configure a schedule, send alerts, create credentials,
delete backups or authorize serving recovered data. The existing job owns its
Linux worker and process-group cleanup; this adapter adds no second supervisor.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from uuid import uuid4

from scripts import backup_job as job
from scripts.scan_secrets import _private_evidence

# Parent only: every payload gets a fresh boundary with verified private permissions.
LINUX_WORK_ROOT = Path("/tmp")  # nosec B108


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError("Invalid backup service arguments")


def _workspace(parent: Path) -> Path:
    """New private payload boundary; local project writes stay on E/F."""
    if not parent.is_absolute() or parent.resolve() != parent or not parent.is_dir():
        raise ValueError("An existing absolute work root without links is required")
    if os.name == "nt":
        if parent.drive.upper() not in {"E:", "F:"}:
            raise ValueError("Local backup evidence must stay on E/F")
    elif not parent.is_relative_to(LINUX_WORK_ROOT):
        raise ValueError("Linux backup work must stay under the temporary root")
    return _private_evidence(parent / ("metodobase-backup-" + uuid4().hex))


def _receipt(stage: Path, config: dict, returned: dict) -> dict:
    """Bind the sealed result to this invocation and independently read closure."""
    request = json.loads(job._read(stage / "request.private.json"))
    if (not isinstance(request, dict) or request.get("schema") != job.SCHEMA
        or not isinstance(request.get("nonce"), str)
        or not re.fullmatch(r"[0-9a-f]{32}", request["nonce"])
        or request.get("config") != config or not isinstance(returned, dict)
        or type(returned.get("exit_code")) is not int or returned["exit_code"] not in {0, 2}):
        raise ValueError("Backup invocation identity differs")
    result = job._validated_receipt(stage / "job-receipt.json", request["nonce"],
        config["expected_revision"], returned["exit_code"])
    supervision = json.loads(job._read(stage / "supervision.json"))
    expected_supervision = {"schema": job.SCHEMA, "nonce": request["nonce"],
        "exit_code": returned["exit_code"], "timed_out": False,
        "descendants_detected": False, "active_owned_processes": 0}
    if (result != returned or result.get("supervision_verified") is not True
        or type(result.get("active_owned_processes")) is not int
        or result["active_owned_processes"] != 0 or result.get("scheduled") is not False
        or supervision != expected_supervision
        or any(type(supervision.get(name)) is not int for name in ("exit_code", "active_owned_processes"))
        or any(supervision.get(name) is not False for name in ("timed_out", "descendants_detected"))):
        raise ValueError("Backup receipt or process closure differs")
    return result


def run_service(*, expected_database: str, expected_revision: str, pg_bin: Path,
                work_root: Path, timeout_seconds: int = 900,
                capture_timeout_seconds: int = 300) -> dict:
    if (not job._linux() or not isinstance(expected_database, str)
        or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,62}", expected_database)
        or expected_revision not in job.REVISIONS or not pg_bin.is_absolute()
        or type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 3600
        or type(capture_timeout_seconds) is not int
        or not 1 <= capture_timeout_seconds <= timeout_seconds):
        raise ValueError("Explicit source identity and bounded Linux execution are required")
    config = {"expected_database": expected_database, "expected_revision": expected_revision,
        "pg_bin": str(pg_bin), "capture_timeout_seconds": capture_timeout_seconds,
        "max_objects": 128, "max_object_bytes": 256 * 1024**2,
        "max_dump_bytes": 128 * 1024**2, "max_publish_bytes": 512 * 1024**2,
        "prefix": "backups/metodobase"}
    previous = {name: os.environ.get(name) for name in ("TEMP", "TMP", "TMPDIR")}
    old_mask = os.umask(0o077)
    try:
        workspace = _workspace(work_root)
        os.environ.update({name: str(workspace) for name in previous})
        stage = workspace / "job"
        result = job.run_job(stage, config, timeout_seconds=timeout_seconds)
        verified = _receipt(stage, config, result)
        return {"status": verified["status"], "exit_code": verified["exit_code"],
            "inventory_counts": verified["coverage"]["inventory_counts"],
            "readback_verified": True, "supervision_verified": True,
            "retention_deletions": 0, "serving_authorized": False,
            "schedule_attested": False, "alarm_delivery_attested": False}
    finally:
        os.umask(old_mask)
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def main(argv=None) -> int:
    parser = _Parser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--expected-database", required=True)
    parser.add_argument("--expected-revision", required=True, choices=job.REVISIONS)
    parser.add_argument("--pg-bin", required=True, type=Path)
    parser.add_argument("--work-root", type=Path, default=LINUX_WORK_ROOT)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--capture-timeout-seconds", type=int, default=300)
    try:
        args = parser.parse_args(argv)
        result = run_service(**vars(args))
        print(json.dumps(result, sort_keys=True))
        return result["exit_code"]
    except Exception:  # noqa: BLE001 - no provider errors, arguments, paths or credentials in logs
        print(json.dumps({"status": "failed", "error": "backup_service_failed"}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

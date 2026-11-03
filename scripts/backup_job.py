"""One Linux backup job: bounded capture, publication, readback and a sealed receipt.

Secrets remain in the environment. Only the newly created session is stopped;
partial legacy coverage is published as contingency and remains exit 2.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import signal
import stat
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
REVISION = "20261102_payment_refund_facts"
REVISIONS = ("20261031_gym_equipment", REVISION)
SCHEMA = "metodobase-backup-job-v1"
RECEIPT_LIMIT = 16384
COMPLETE = "verified_current_resources"
PARTIAL = "partial_legacy_references"


class _JobParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError("Invalid backup job arguments")


@dataclass(frozen=True)
class Supervision:
    exit_code: int
    timed_out: bool
    descendants_detected: bool
    active_owned_processes: int


def _linux() -> bool:
    return os.name == "posix" and sys.platform.startswith("linux")


def _json(path: Path, value: dict) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf8") as stream:
        json.dump(value, stream, sort_keys=True)
        stream.write("\n")


def _read(path: Path, maximum: int = RECEIPT_LIMIT) -> bytes:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or not 0 < info.st_size <= maximum:
        raise ValueError("Invalid bounded job artifact")
    with path.open("rb") as stream:
        raw = stream.read(maximum + 1)
    if len(raw) != info.st_size or len(raw) > maximum:
        raise ValueError("Job artifact changed or is truncated")
    return raw


def _active_group(group: int) -> list[int]:
    """Linux process-group members that can still execute; never inspect argv."""
    active = []
    for path in Path("/proc").iterdir():
        if not path.name.isdecimal():
            continue
        try:
            fields = (path / "stat").read_text().rsplit(")", 1)[1].split()
            if int(fields[2]) == group and fields[0] not in {"Z", "X"}:
                active.append(int(path.name))
        except FileNotFoundError:
            continue  # A process that already exited is not an active member.
    return active


def _observe_group(group: int) -> list[int] | None:
    try:
        return _active_group(group)
    except (OSError, ValueError, IndexError):
        return None  # Unreadable/malformed proc data never means an empty group.


def _leader_exited(process: subprocess.Popen) -> bool | None:
    """Observe without reaping: the owned leader reserves its PID until cleanup."""
    try:
        return os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None
    except OSError:
        return None


def _close_group(process: subprocess.Popen, grace: float, *, observation_failed: bool = False) -> int:
    uncertain = observation_failed
    for sig, wait in ((signal.SIGTERM, grace), (signal.SIGKILL, grace)):
        observed = _observe_group(process.pid)
        uncertain |= observed is None
        if observed != []:
            try:
                os.killpg(process.pid, sig)
            except ProcessLookupError:
                pass  # ESRCH is a race, not sufficient evidence of closure.
            except OSError:
                uncertain = True
        deadline = time.monotonic() + wait
        while time.monotonic() < deadline:
            observed = _observe_group(process.pid)
            exited = _leader_exited(process)
            uncertain |= observed is None or exited is None
            if observed == [] and exited is True:
                return -1 if uncertain else 0
            time.sleep(0.02)
    observed = _observe_group(process.pid)
    return -1 if uncertain or observed is None else len(observed)


def supervise(command: list[str], *, environment: dict, timeout_seconds: float,
              grace_seconds: float = 2) -> Supervision:
    """Bound the known worker and descendants that retain its process group.

    This controls the backup pipeline, whose children do not change SID/PGID;
    it is not containment of an adversarial worker. No other code reaps this
    newly created leader before signals finish, so its PGID cannot be recycled.
    """
    if not _linux() or not 0 < timeout_seconds <= 3600 or not 0 < grace_seconds <= 5:
        raise ValueError("Linux process supervision and bounded durations are required")
    if signal.getsignal(signal.SIGCHLD) != signal.SIG_DFL:
        raise ValueError("The supervisor must own child reaping")
    started = time.monotonic()
    process = subprocess.Popen(command, cwd=ROOT, env=environment, start_new_session=True,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    timed_out = False
    descendants = False
    active = 1
    observation_failed = False
    try:
        while True:
            exited = _leader_exited(process)
            if exited is None:
                observation_failed = True
                break
            if exited:
                break
            if time.monotonic() - started >= timeout_seconds:
                timed_out = True
                break
            time.sleep(min(0.02, max(0.001, timeout_seconds - (time.monotonic() - started))))
        if not timed_out:
            observed = _observe_group(process.pid)
            observation_failed |= observed is None
            descendants = bool(observed) if observed is not None else True
    finally:
        # Exactly one cleanup attempt, independent of proc observation success.
        active = _close_group(process, grace_seconds, observation_failed=observation_failed)
        try:
            process.wait(timeout=grace_seconds)
        except subprocess.TimeoutExpired:
            active = -1
    return Supervision(process.returncode if process.returncode is not None else -1,
        timed_out, descendants, active)


def _coverage(manifest: dict, expected_revision: str) -> dict:
    capture = manifest.get("capture", {})
    counts = capture.get("inventory_counts", {})
    names = {"ready_objects", "pending_objects", "object_references",
             "legacy_plan_references_uncovered", "legacy_logo_references_uncovered"}
    if (capture.get("contract") != "postgresql18-s3-exported-snapshot-v1"
        or capture.get("source_revision") != expected_revision
        or capture.get("postgresql_consistency") != "same_exported_snapshot"
        or capture.get("objects_consistency") != "immutable_descriptors_from_that_snapshot"
        or capture.get("serving_authorized") is not False or set(counts) != names
        or any(type(value) is not int or value < 0 for value in counts.values())
        or not 180000 <= capture.get("server_version_num", 0) < 190000
        or sorted(item.get("kind", "") for item in manifest.get("artifacts", [])) != ["objects", "postgres"]):
        raise ValueError("Current capture coverage is not verified")
    expected = PARTIAL if counts["legacy_plan_references_uncovered"] + counts["legacy_logo_references_uncovered"] else COMPLETE
    if capture.get("status") != expected:
        raise ValueError("Capture status differs from authenticated inventory")
    return {"status": expected, "inventory_counts": counts, "source_revision": expected_revision,
        "current_resources_verified": True, "legacy_bytes": "not_captured",
        "suppression_journal": "not_captured", "global_roles": "not_captured", "serving_authorized": False}


def run_pipeline(stage: Path, config: dict, nonce: str) -> dict:
    """Worker-only pipeline. Callers cannot promote transport coverage to recovery."""
    from scripts import backup_capture_s3 as capture
    from scripts import backup_remote as remote
    from scripts.backup_restore import checksum, verified_artifacts

    store = None
    client = None
    try:
        store = capture._configured_store()
        result = capture.capture_backup(stage / "capture", database_url=os.environ.get("BACKUP_DATABASE_URL", ""),
            expected_database=config["expected_database"], expected_revision=config["expected_revision"],
            pg_bin=Path(config["pg_bin"]), object_store=store,
            limits=capture.CaptureLimits(timeout_seconds=config["capture_timeout_seconds"],
                max_objects=config["max_objects"], max_object_bytes=config["max_object_bytes"],
                max_dump_bytes=config["max_dump_bytes"]))
        store.client.close()
        store = None
        manifest_path = Path(result["manifest"])
        if manifest_path.parent != stage / "capture":
            raise ValueError("Capture manifest escaped the private stage")
        manifest_raw = _read(manifest_path, 64 * 1024)
        with verified_artifacts(manifest_path) as (manifest, _):
            coverage = _coverage(manifest, config["expected_revision"])
            if result["status"] != coverage["status"] or result["snapshot_id"] != manifest["snapshot_id"]:
                raise ValueError("Capture result differs from authenticated manifest")
        client = remote._client()
        options = {"client": client, "bucket": os.environ["BACKUP_S3_BUCKET"],
            "prefix": config["prefix"], "max_bytes": config["max_publish_bytes"]}
        publication = remote.publish_backup(manifest_path, **options)
        if (publication.get("status") != "verified_remote_backup"
            or publication.get("snapshot_id") != manifest["snapshot_id"]
            or publication.get("retention_deletions") != 0):
            raise ValueError("Publication receipt differs")
        quarantine = stage / "readback"
        readback = remote.fetch_backup(manifest["snapshot_id"], quarantine, **options)
        recovered_manifest = quarantine / (manifest["snapshot_id"] + "-manifest.json")
        if (_read(recovered_manifest, 64 * 1024) != manifest_raw
            or readback.get("status") != "verified_local_quarantine"
            or readback.get("snapshot_id") != manifest["snapshot_id"]):
            raise ValueError("Remote readback differs from captured snapshot")
        with verified_artifacts(recovered_manifest) as (recovered, _):
            if _coverage(recovered, config["expected_revision"]) != coverage:
                raise ValueError("Readback coverage differs")
        client.close()
        client = None
        return {"schema": SCHEMA, "nonce": nonce, "status": coverage["status"],
            "snapshot_id": manifest["snapshot_id"], "coverage": coverage,
            "manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
            "completion_sha256": publication["completion_sha256"],
            "readback_manifest_sha256": checksum(recovered_manifest),
            "publication_verified": True, "readback_verified": True,
            "retention_deletions": 0, "scheduled": False, "serving_authorized": False}
    finally:
        if store is not None:
            store.client.close()
        if client is not None:
            client.close()


def _seal(value: dict) -> dict:
    from scripts.backup_restore import encryption_key, manifest_authentication
    key = encryption_key()
    if key is None:
        raise ValueError("A backup key is required")
    return {**value, "manifest_mac": manifest_authentication(value, key)}


def _validated_receipt(path: Path, nonce: str, expected_revision: str, worker_exit: int) -> dict:
    from scripts.backup_restore import encryption_key, manifest_authentication
    value = json.loads(_read(path))
    key = encryption_key()
    if (key is None or not isinstance(value, dict) or value.get("schema") != SCHEMA
        or value.get("nonce") != nonce or not isinstance(value.get("manifest_mac"), str)
        or not hmac.compare_digest(value["manifest_mac"], manifest_authentication(value, key))):
        raise ValueError("Job receipt authentication or nonce differs")
    if (value.get("status") not in {COMPLETE, PARTIAL}
        or worker_exit != (2 if value["status"] == PARTIAL else 0)
        or not re.fullmatch(r"[0-9]{8}T[0-9]{12}Z", value.get("snapshot_id", ""))
        or any(value.get(name) is not True for name in ("publication_verified", "readback_verified"))
        or value.get("retention_deletions") != 0 or value.get("serving_authorized") is not False):
        raise ValueError("Job receipt is incomplete")
    coverage = value.get("coverage", {})
    counts = coverage.get("inventory_counts", {})
    count_names = {"ready_objects", "pending_objects", "object_references",
        "legacy_plan_references_uncovered", "legacy_logo_references_uncovered"}
    if (coverage.get("source_revision") != expected_revision or coverage.get("status") != value["status"]
        or coverage.get("current_resources_verified") is not True or coverage.get("serving_authorized") is not False
        or set(counts) != count_names or any(type(counts[name]) is not int or counts[name] < 0 for name in count_names)
        or any(coverage.get(name) != "not_captured" for name in ("legacy_bytes", "suppression_journal", "global_roles"))
        or bool(counts["legacy_plan_references_uncovered"] + counts["legacy_logo_references_uncovered"]) != (value["status"] == PARTIAL)):
        raise ValueError("Job receipt coverage differs")
    for name in ("manifest_sha256", "completion_sha256", "readback_manifest_sha256"):
        if not re.fullmatch(r"[0-9a-f]{64}", value.get(name, "")):
            raise ValueError("Job receipt digest is invalid")
    if value["manifest_sha256"] != value["readback_manifest_sha256"]:
        raise ValueError("Job receipt does not bind exact readback")
    return value


def _worker(request_path: Path) -> int:
    try:
        request = json.loads(_read(request_path))
        nonce = request["nonce"]
        if not _linux() or not re.fullmatch(r"[0-9a-f]{32}", nonce):
            return 1
        stage = request_path.parent
        result = run_pipeline(stage, request["config"], nonce)
        pending = stage / "worker-result.pending"
        _json(pending, _seal(result))
        pending.rename(stage / "worker-result.json")
        return 2 if result["status"] == PARTIAL else 0
    except Exception:  # noqa: BLE001 - no provider/SQL errors in cron output or logs
        return 1


def run_job(output: Path, config: dict, *, timeout_seconds: int) -> dict:
    if not _linux() or type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 3600:
        raise ValueError("This job requires Linux and a bounded wall duration")
    from scripts.backup_restore import encryption_key
    from scripts.scan_secrets import _private_evidence
    if encryption_key() is None:
        raise ValueError("A backup key is required")
    stage = _private_evidence(output)
    nonce = uuid4().hex
    request = stage / "request.private.json"
    _json(request, {"schema": SCHEMA, "nonce": nonce, "config": config})
    environment = {name: value for name, value in os.environ.items() if name in {
        "PATH", "LANG", "LC_ALL", "SSL_CERT_FILE", "SSL_CERT_DIR", "BACKUP_DATABASE_URL", "BACKUP_ENCRYPTION_KEY",
        "BACKUP_S3_ENDPOINT", "BACKUP_S3_REGION", "BACKUP_S3_BUCKET", "BACKUP_S3_ACCESS_KEY", "BACKUP_S3_SECRET_KEY",
        "OBJECT_STORAGE_S3_ENDPOINT", "OBJECT_STORAGE_S3_REGION", "OBJECT_STORAGE_S3_BUCKET",
        "OBJECT_STORAGE_S3_ACCESS_KEY", "OBJECT_STORAGE_S3_SECRET_KEY", "OBJECT_STORAGE_S3_SESSION_TOKEN"}}
    environment.update(TEMP=str(stage), TMP=str(stage), TMPDIR=str(stage), HOME=str(stage),
        PYTHONDONTWRITEBYTECODE="1", PYTHON_DOTENV_DISABLED="1", AWS_EC2_METADATA_DISABLED="true")
    result = supervise([sys.executable, "-B", "-X", "utf8", "-m", "scripts.backup_job", "--worker", str(request)],
        environment=environment, timeout_seconds=timeout_seconds)
    _json(stage / "supervision.json", {"schema": SCHEMA, "nonce": nonce, **result.__dict__})
    if result.timed_out or result.descendants_detected or result.active_owned_processes or result.exit_code not in {0, 2}:
        raise ValueError("Backup worker did not finish and close within its wall bound")
    value = _validated_receipt(stage / "worker-result.json", nonce, config["expected_revision"], result.exit_code)
    final = _seal({**{name: item for name, item in value.items() if name != "manifest_mac"},
        "supervision_verified": True, "active_owned_processes": 0, "exit_code": result.exit_code})
    _json(stage / "job-receipt.json", final)
    return final


def main(argv=None) -> int:
    parser = _JobParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--expected-database")
    parser.add_argument("--expected-revision", choices=REVISIONS)
    parser.add_argument("--pg-bin", type=Path)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--capture-timeout-seconds", type=int, default=300)
    parser.add_argument("--max-objects", type=int, default=128)
    parser.add_argument("--max-object-bytes", type=int, default=256 * 1024**2)
    parser.add_argument("--max-dump-bytes", type=int, default=128 * 1024**2)
    parser.add_argument("--max-publish-bytes", type=int, default=512 * 1024**2)
    parser.add_argument("--prefix", default="backups/metodobase")
    try:
        args = parser.parse_args(argv)
    except ValueError:
        print(json.dumps({"status": "failed", "error": "backup_job_failed"}, sort_keys=True))
        return 1
    if args.worker is not None:
        return _worker(args.worker)
    try:
        if (not args.output or not args.expected_database or not args.expected_revision
            or not args.pg_bin or not args.pg_bin.is_absolute()):
            raise ValueError("Explicit job inputs are required")
        config = {"expected_database": args.expected_database, "expected_revision": args.expected_revision,
            "pg_bin": str(args.pg_bin), "capture_timeout_seconds": args.capture_timeout_seconds,
            "max_objects": args.max_objects, "max_object_bytes": args.max_object_bytes,
            "max_dump_bytes": args.max_dump_bytes, "max_publish_bytes": args.max_publish_bytes, "prefix": args.prefix}
        result = run_job(args.output, config, timeout_seconds=args.timeout_seconds)
        print(json.dumps({"status": result["status"], "snapshot_id": result["snapshot_id"],
            "nonce": result["nonce"], "readback_verified": True, "retention_deletions": 0,
            "serving_authorized": False}, sort_keys=True))
        return result["exit_code"]
    except Exception:  # noqa: BLE001 - never print credentials, customer paths or SDK exception details
        print(json.dumps({"status": "failed", "error": "backup_job_failed"}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

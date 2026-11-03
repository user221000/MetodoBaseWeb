"""Service boundary tests with real receipt authentication and isolated files.

These tests do not claim Linux process execution or provider access. The job's
Linux/PG suites remain the independent execution gates for the final image.
"""
import base64
import copy
import json
import os
from pathlib import Path

import pytest

from scripts import backup_job as job
from scripts import backup_service_entrypoint as service
from scripts.backup_restore import manifest_authentication
from scripts.scan_secrets import _private_evidence

KEY = bytes(range(32))  # Deterministic synthetic key, never a provider credential.
NONCE = "d" * 32


def _sealed(value):
    return {**value, "manifest_mac": manifest_authentication(value, KEY)}


def _write(path, value):
    path.write_text(json.dumps(value), encoding="utf8")


def _worker_receipt(config, *, partial=False):
    status = "partial_legacy_references" if partial else "verified_current_resources"
    counts = {"ready_objects": 3, "pending_objects": 0, "object_references": 3,
        "legacy_plan_references_uncovered": 39 if partial else 0,
        "legacy_logo_references_uncovered": 1 if partial else 0}
    return {"schema": "metodobase-backup-job-v1", "nonce": NONCE,
        "snapshot_id": "20261103T120000123456Z", "status": status,
        "coverage": {"status": status, "inventory_counts": counts,
            "source_revision": config["expected_revision"], "current_resources_verified": True,
            "legacy_bytes": "not_captured", "suppression_journal": "not_captured",
            "global_roles": "not_captured", "serving_authorized": False},
        "manifest_sha256": "a" * 64, "completion_sha256": "b" * 64,
        "readback_manifest_sha256": "a" * 64, "publication_verified": True,
        "readback_verified": True, "retention_deletions": 0, "scheduled": False,
        "serving_authorized": False}


@pytest.fixture
def invocation(tmp_path, monkeypatch):
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", base64.b64encode(KEY).decode())
    # Only the wrapper boundary is portable; no emulated process test is claimed.
    monkeypatch.setattr(job, "_linux", lambda: True)
    seen = {}
    options = {"expected_database": "synthetic_backup", "expected_revision": job.REVISIONS[0],
        "pg_bin": tmp_path / "pg-bin", "work_root": tmp_path,
        "timeout_seconds": 30, "capture_timeout_seconds": 10}

    def completed(stage, config, *, timeout_seconds):
        stage = _private_evidence(stage)
        seen.update(stage=stage, config=config, timeout=timeout_seconds,
            temporary={name: os.environ[name] for name in ("TEMP", "TMP", "TMPDIR")})
        request = {"schema": job.SCHEMA, "nonce": NONCE, "config": config}
        supervision = {"schema": job.SCHEMA, "nonce": NONCE, "exit_code": 0,
            "timed_out": False, "descendants_detected": False, "active_owned_processes": 0}
        result = _sealed({**_worker_receipt(config), "supervision_verified": True,
            "active_owned_processes": 0, "exit_code": 0})
        _write(stage / "request.private.json", request)
        _write(stage / "supervision.json", supervision)
        _write(stage / "job-receipt.json", result)
        return result

    monkeypatch.setattr(job, "run_job", completed)
    return options, completed, seen


def test_complete_requires_authentication_and_preserves_private_environment(invocation):
    options, _, seen = invocation
    before = {name: os.environ.get(name) for name in ("TEMP", "TMP", "TMPDIR")}
    result = service.run_service(**options)
    assert result["exit_code"] == 0 and result["readback_verified"]
    assert result["supervision_verified"] and not result["serving_authorized"]
    assert not result["schedule_attested"] and not result["alarm_delivery_attested"]
    assert seen["config"]["expected_revision"] == options["expected_revision"]
    assert seen["config"]["expected_database"] == "synthetic_backup" and seen["timeout"] == 30
    assert set(seen["temporary"].values()) == {str(seen["stage"].parent)}
    assert {name: os.environ.get(name) for name in before} == before


def test_partial_preserves_exit_two_and_exact_uncovered_counts(invocation, monkeypatch):
    options, completed, _ = invocation

    def partial(stage, config, **kwargs):
        completed(stage, config, **kwargs)
        result = _sealed({**_worker_receipt(config, partial=True), "supervision_verified": True,
            "active_owned_processes": 0, "exit_code": 2})
        _write(stage / "job-receipt.json", result)
        supervision = json.loads((stage / "supervision.json").read_bytes())
        supervision["exit_code"] = 2
        _write(stage / "supervision.json", supervision)
        return result

    monkeypatch.setattr(job, "run_job", partial)
    result = service.run_service(**options)
    assert result["exit_code"] == 2 and result["status"] == "partial_legacy_references"
    assert result["inventory_counts"]["legacy_plan_references_uncovered"] == 39
    assert result["inventory_counts"]["legacy_logo_references_uncovered"] == 1


@pytest.mark.parametrize("damage", ["missing", "truncated", "oversized", "forged_mac", "stale_nonce",
    "request_database", "request_revision", "active_child", "boolean_child_count", "timeout",
    "descendant", "supervisor_nonce", "return_only", "returned_different", "signed_unclosed",
    "signed_scheduled", "signed_wrong_revision", "hardlink", "receipt_array"])
def test_false_success_is_rejected(invocation, monkeypatch, damage):
    options, completed, _ = invocation

    def damaged(stage, config, **kwargs):
        result = completed(stage, config, **kwargs)
        receipt = stage / "job-receipt.json"
        if damage == "missing":
            receipt.unlink()
        elif damage == "truncated":
            receipt.write_bytes(receipt.read_bytes()[:-11])
        elif damage == "oversized":
            receipt.write_bytes(b" " * (job.RECEIPT_LIMIT + 1))
        elif damage in {"forged_mac", "stale_nonce", "signed_unclosed", "signed_scheduled", "signed_wrong_revision"}:
            result = copy.deepcopy(result)
            if damage == "forged_mac":
                result["manifest_mac"] = "0" * 64
            else:
                if damage == "stale_nonce":
                    result["nonce"] = "e" * 32
                elif damage == "signed_unclosed":
                    result["supervision_verified"] = False
                elif damage == "signed_scheduled":
                    result["scheduled"] = True
                else:
                    result["coverage"]["source_revision"] = job.REVISIONS[1]
                result = _sealed(result)
            _write(receipt, result)
        elif damage.startswith("request_"):
            request = json.loads((stage / "request.private.json").read_bytes())
            request["config"]["expected_" + damage.split("_", 1)[1]] = "other"
            _write(stage / "request.private.json", request)
        elif damage in {"active_child", "boolean_child_count", "timeout", "descendant", "supervisor_nonce"}:
            supervision = json.loads((stage / "supervision.json").read_bytes())
            changes = {"active_child": ("active_owned_processes", 1),
                "boolean_child_count": ("active_owned_processes", False), "timeout": ("timed_out", True),
                "descendant": ("descendants_detected", True), "supervisor_nonce": ("nonce", "f" * 32)}
            key, value = changes[damage]
            supervision[key] = value
            _write(stage / "supervision.json", supervision)
        elif damage == "return_only":
            return {"exit_code": 0}
        elif damage == "returned_different":
            return {**result, "extra": "not on disk"}
        elif damage == "hardlink":
            os.link(receipt, stage / "also-receipt.json")
        elif damage == "receipt_array":
            _write(receipt, [])
        return result

    monkeypatch.setattr(job, "run_job", damaged)
    with pytest.raises((ValueError, OSError)):
        service.run_service(**options)


def test_authentic_run_job_boundary_and_return_receipt(invocation, monkeypatch):
    options, _, _ = invocation
    # Retrieve the real function without changing its module or worker contract.
    monkeypatch.undo()
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", base64.b64encode(KEY).decode())
    monkeypatch.setattr(job, "_linux", lambda: True)

    def worker(command, *, environment, timeout_seconds):
        request_path = Path(command[-1])
        request = json.loads(request_path.read_bytes())
        value = _worker_receipt(request["config"])
        value["nonce"] = request["nonce"]
        _write(request_path.parent / "worker-result.json", _sealed(value))
        assert command[-3:-1] == ["scripts.backup_job", "--worker"]
        assert timeout_seconds == options["timeout_seconds"]
        assert environment["TMPDIR"] == str(request_path.parent)
        assert "SENTRY_DSN" not in environment
        return job.Supervision(0, False, False, 0)

    monkeypatch.setattr(job, "supervise", worker)
    assert service.run_service(**options)["exit_code"] == 0


def test_failure_withholds_sensitive_exception_and_restores_environment(invocation, monkeypatch, capsys):
    options, _, _ = invocation
    before = {name: os.environ.get(name) for name in ("TEMP", "TMP", "TMPDIR")}

    def timeout(*args, **kwargs):
        raise TimeoutError("synthetic-private-provider-details")

    monkeypatch.setattr(job, "run_job", timeout)
    argv = ["--expected-database", options["expected_database"], "--expected-revision", options["expected_revision"],
        "--pg-bin", str(options["pg_bin"]), "--work-root", str(options["work_root"])]
    assert service.main(argv) == 1
    assert json.loads(capsys.readouterr().out) == {"status": "failed", "error": "backup_service_failed"}
    assert {name: os.environ.get(name) for name in before} == before


@pytest.mark.parametrize("change", [{"expected_database": ""}, {"expected_revision": "head"},
    {"expected_database": "postgresql://synthetic:private@host/db"}, {"timeout_seconds": 0},
    {"timeout_seconds": True}, {"timeout_seconds": 3601}, {"capture_timeout_seconds": 31},
    {"pg_bin": Path("relative")}, {"work_root": Path("relative")}])
def test_invalid_configuration_never_starts_job(invocation, change):
    options, _, seen = invocation
    with pytest.raises(ValueError):
        service.run_service(**{**options, **change})
    assert not seen


def test_non_linux_never_starts_job(invocation, monkeypatch):
    options, _, seen = invocation
    monkeypatch.setattr(job, "_linux", lambda: False)
    with pytest.raises(ValueError):
        service.run_service(**options)
    assert not seen


def test_explicit_identity_required_without_reflecting_cli_input(capsys):
    assert service.main(["--unexpected", "synthetic-private-argument"]) == 1
    output = capsys.readouterr()
    assert "synthetic-private-argument" not in output.out + output.err
    assert json.loads(output.out)["status"] == "failed"


def test_work_root_outside_platform_boundary_is_rejected():
    root, reason = (Path("C:/"), "E/F") if os.name == "nt" else (Path("/"), "temporary root")
    with pytest.raises(ValueError, match=reason):
        service._workspace(root)

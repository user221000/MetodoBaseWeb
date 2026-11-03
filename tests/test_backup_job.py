"""Offline crypto/publication controls and real Linux process-group supervision."""
import base64
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import backup_capture_s3 as capture
from scripts import backup_job as job
from scripts import backup_remote as remote
from scripts.backup_restore import BackupError
from tests.test_backup_capture_s3 import prepared as capture_prepared
from tests.test_backup_remote import Store

LINUX = pytest.mark.skipif(not job._linux(), reason="Actual Linux session supervision; no Windows emulation")


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    root, connection, source, descriptor, arguments = capture_prepared.__wrapped__(tmp_path, monkeypatch)
    connection.revision = job.REVISION
    destination = Store()
    destination.closes = 0

    def close():
        destination.closes += 1

    destination.close = close
    monkeypatch.setattr(capture, "_configured_store", lambda: arguments["object_store"])
    monkeypatch.setattr(remote, "_client", lambda: destination)
    monkeypatch.setenv("BACKUP_DATABASE_URL", arguments["database_url"])
    monkeypatch.setenv("BACKUP_S3_BUCKET", "synthetic-bucket")
    config = {"expected_database": arguments["expected_database"], "expected_revision": job.REVISION,
        "pg_bin": str(arguments["pg_bin"]), "capture_timeout_seconds": 30, "max_objects": 8,
        "max_object_bytes": 1024**2, "max_dump_bytes": 1024**2,
        "max_publish_bytes": 8 * 1024**2, "prefix": "backups/metodobase"}
    stage = root / "job"
    stage.mkdir()
    return stage, connection, source, descriptor, destination, config


@pytest.mark.parametrize("legacy,expected,exit_code", [((0, 0), job.COMPLETE, 0), ((39, 1), job.PARTIAL, 2)])
@pytest.mark.parametrize("revision", job.REVISIONS)
def test_current_and_partial_are_published_and_exactly_read_back(pipeline, legacy, expected, exit_code, revision):
    stage, connection, _, _, destination, config = pipeline
    connection.legacy = legacy
    connection.revision = revision
    config["expected_revision"] = revision
    nonce = "a" * 32
    result = job.run_pipeline(stage, config, nonce)
    assert result["status"] == expected and result["nonce"] == nonce
    assert result["publication_verified"] and result["readback_verified"]
    assert result["manifest_sha256"] == result["readback_manifest_sha256"]
    assert result["retention_deletions"] == 0 and result["serving_authorized"] is False
    assert result["coverage"]["inventory_counts"]["legacy_plan_references_uncovered"] == legacy[0]
    assert result["coverage"]["inventory_counts"]["legacy_logo_references_uncovered"] == legacy[1]
    assert destination.writes[-1].endswith("complete.json") and destination.closes == 1
    assert len(destination.objects) == 4
    receipt = stage / "worker-result.json"
    job._json(receipt, job._seal(result))
    assert job._validated_receipt(receipt, nonce, revision, exit_code)["status"] == expected
    assert result["coverage"]["source_revision"] == revision
    # The transport keeps its own deliberately narrower attestation.
    index = json.loads(next(value for key, value in destination.objects.items() if key.endswith("complete.json")))
    assert index["coverage"]["cross_resource_consistency"] == "not_attested"


def test_capture_failure_prevents_any_publication_and_withholds_private_error(pipeline, monkeypatch, capsys):
    stage, _, _, _, destination, config = pipeline
    secret = "postgresql://sensitive:password@private.example/customer"
    monkeypatch.setattr(capture, "capture_backup", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError(secret)))
    with pytest.raises(RuntimeError, match="sensitive"):
        job.run_pipeline(stage, config, "b" * 32)
    assert not destination.writes and not (stage / "worker-result.json").exists()
    assert secret not in capsys.readouterr().out


def test_tampered_local_manifest_prevents_publication(pipeline, monkeypatch):
    stage, _, _, _, destination, config = pipeline
    original = capture.capture_backup

    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        path = Path(result["manifest"])
        value = json.loads(path.read_bytes())
        value["capture"]["inventory_counts"]["legacy_logo_references_uncovered"] = 0
        value["capture"]["status"] = "forged"
        path.write_text(json.dumps(value), encoding="utf8")
        return result

    monkeypatch.setattr(capture, "capture_backup", changed)
    with pytest.raises(BackupError, match="authentication"):
        job.run_pipeline(stage, config, "c" * 32)
    assert not destination.writes


def test_fetch_readback_failure_never_seals_success(pipeline, monkeypatch):
    stage, _, _, _, destination, config = pipeline
    original = remote.fetch_backup

    def corrupted(snapshot, output, **kwargs):
        destination.corrupt_read = next(key for key in destination.objects if key.endswith("postgres.dump.enc"))
        return original(snapshot, output, **kwargs)

    monkeypatch.setattr(remote, "fetch_backup", corrupted)
    with pytest.raises(BackupError, match="integrity"):
        job.run_pipeline(stage, config, "d" * 32)
    assert destination.writes[-1].endswith("complete.json")  # Transport completion alone is insufficient.
    assert not (stage / "worker-result.json").exists() and destination.closes == 1


@pytest.mark.parametrize("failure", ["nonce", "truncated", "mac", "exit", "coverage", "readback"])
def test_receipt_requires_nonce_authentication_coverage_and_exact_exit(pipeline, failure):
    stage, _, _, _, _, config = pipeline
    nonce = "e" * 32
    value = job.run_pipeline(stage, config, nonce)
    if failure == "coverage":
        value["coverage"]["current_resources_verified"] = False
    if failure == "readback":
        value["readback_verified"] = False
    value = job._seal(value)
    if failure == "mac":
        value["manifest_mac"] = "0" * 64
    path = stage / "result.json"
    job._json(path, value)
    if failure == "truncated":
        path.write_bytes(path.read_bytes()[:-4])
    with pytest.raises((ValueError, KeyError)):
        job._validated_receipt(path, "f" * 32 if failure == "nonce" else nonce,
            job.REVISION, 2 if failure == "exit" else 0)


def test_partial_worker_exit_without_receipt_is_not_success(tmp_path, monkeypatch):
    if not job._linux():
        pytest.skip("The supervising entrypoint is Linux-only")
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", base64.b64encode(bytes(range(32))).decode())
    monkeypatch.setattr(job, "supervise", lambda *args, **kwargs: job.Supervision(2, False, False, 0))
    with pytest.raises(FileNotFoundError):
        job.run_job(tmp_path / "private-job", {"expected_revision": job.REVISION}, timeout_seconds=2)
    assert not (tmp_path / "private-job/job-receipt.json").exists()


def test_cli_exception_output_has_no_secret_or_traceback(monkeypatch, capsys, tmp_path):
    secret = "sensitive-token-not-for-logs"
    monkeypatch.setattr(job, "run_job", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError(secret)))
    assert job.main(["--output", str(tmp_path / "out"), "--expected-database", "synthetic",
        "--expected-revision", job.REVISION, "--pg-bin", str(tmp_path.absolute())]) == 1
    assert capsys.readouterr().out == '{"error": "backup_job_failed", "status": "failed"}\n'


@pytest.mark.parametrize("revision", job.REVISIONS)
def test_cli_preserves_exact_explicit_supported_revision(monkeypatch, tmp_path, revision):
    observed = []

    def run(output, config, **kwargs):
        observed.append(config["expected_revision"])
        return {"status": job.COMPLETE, "snapshot_id": "20261103T120000000000Z", "nonce": "a" * 32, "exit_code": 0}

    monkeypatch.setattr(job, "run_job", run)
    assert job.main(["--output", str(tmp_path / "out"), "--expected-database", "synthetic",
        "--expected-revision", revision, "--pg-bin", str(tmp_path.absolute())]) == 0
    assert observed == [revision] and set(job.REVISIONS) == capture.REVISIONS


@pytest.mark.parametrize("revision", ["unknown", "private-secret-must-not-be-logged", None])
def test_cli_rejects_unknown_or_absent_revision_before_worker_or_publication(monkeypatch, tmp_path, capsys, revision):
    monkeypatch.setattr(job, "run_job", lambda *args, **kwargs: pytest.fail("Unsupported revision reached worker"))
    args = ["--output", str(tmp_path / "out"), "--expected-database", "synthetic", "--pg-bin", str(tmp_path.absolute())]
    if revision is not None:
        args += ["--expected-revision", revision]
    assert job.main(args) == 1 and not (tmp_path / "out").exists()
    observed = capsys.readouterr()
    assert observed.out == '{"error": "backup_job_failed", "status": "failed"}\n' and not observed.err


def test_non_linux_entrypoint_fails_before_any_private_or_worker_payload(tmp_path, monkeypatch):
    """Portable rejection-branch unit control; not a foreign-OS process test."""
    monkeypatch.setattr(job, "_linux", lambda: False)
    with pytest.raises(ValueError, match="requires Linux"):
        job.run_job(tmp_path / "rejected", {}, timeout_seconds=1)
    assert not (tmp_path / "rejected").exists()


@LINUX
@pytest.mark.parametrize("legacy,expected_exit", [((0, 0), 0), ((39, 1), 2)])
def test_supervisor_accepts_only_nonce_bound_verified_receipt(pipeline, monkeypatch, legacy, expected_exit):
    stage, connection, _, _, _, config = pipeline
    connection.legacy = legacy
    value = job.run_pipeline(stage, config, "a" * 32)
    secret = "synthetic-database-secret"
    monkeypatch.setenv("BACKUP_DATABASE_URL", secret)

    def supervised(command, *, environment, timeout_seconds):
        assert secret not in " ".join(command) and environment["BACKUP_DATABASE_URL"] == secret
        assert command[1:7] == ["-B", "-X", "utf8", "-m", "scripts.backup_job", "--worker"]
        request_path = Path(command[-1])
        request = json.loads(request_path.read_bytes())
        assert secret not in request_path.read_text()
        worker_value = {**value, "nonce": request["nonce"]}
        job._json(request_path.parent / "worker-result.json", job._seal(worker_value))
        return job.Supervision(expected_exit, False, False, 0)

    monkeypatch.setattr(job, "supervise", supervised)
    final = job.run_job(stage / "supervised", config, timeout_seconds=5)
    assert final["exit_code"] == expected_exit and final["supervision_verified"]
    assert final["nonce"] != "a" * 32 and final["active_owned_processes"] == 0
    assert job._validated_receipt(stage / "supervised/job-receipt.json", final["nonce"], job.REVISION,
        expected_exit)["manifest_mac"] == final["manifest_mac"]


@LINUX
def test_worker_withholds_secret_exception_and_incomplete_result(tmp_path, monkeypatch, capsys):
    request = tmp_path / "request.json"
    job._json(request, {"nonce": "f" * 32, "config": {}})
    monkeypatch.setattr(job, "run_pipeline", lambda *args: (_ for _ in ()).throw(RuntimeError("private-url-secret")))
    assert job._worker(request) == 1
    assert not (tmp_path / "worker-result.json").exists()
    assert "private-url-secret" not in capsys.readouterr().out


@LINUX
@pytest.mark.parametrize("legacy,exit_code", [((0, 0), 0), ((39, 1), 2)])
def test_worker_exit_two_requires_published_and_readback_receipt(pipeline, legacy, exit_code):
    stage, connection, _, _, destination, config = pipeline
    connection.legacy = legacy
    request = stage / "request.json"
    job._json(request, {"nonce": "9" * 32, "config": config})
    assert job.main(["--worker", str(request)]) == exit_code
    result = job._validated_receipt(stage / "worker-result.json", "9" * 32, job.REVISION, exit_code)
    assert result["publication_verified"] and result["readback_verified"]
    assert destination.writes[-1].endswith("complete.json")


@LINUX
@pytest.mark.parametrize("outcome", [job.Supervision(0, True, False, 0),
    job.Supervision(0, False, True, 0), job.Supervision(0, False, False, 1), job.Supervision(0, False, False, -1)])
def test_complete_receipt_cannot_override_failed_supervision(pipeline, monkeypatch, outcome):
    stage, _, _, _, _, config = pipeline
    value = job.run_pipeline(stage, config, "a" * 32)

    def failed_supervision(command, **kwargs):
        request_path = Path(command[-1])
        nonce = json.loads(request_path.read_bytes())["nonce"]
        job._json(request_path.parent / "worker-result.json", job._seal({**value, "nonce": nonce}))
        return outcome

    monkeypatch.setattr(job, "supervise", failed_supervision)
    with pytest.raises(ValueError, match="wall bound"):
        job.run_job(stage / "failed-supervision", config, timeout_seconds=5)
    assert not (stage / "failed-supervision/job-receipt.json").exists()


@LINUX
def test_real_child_exit_and_secret_environment_are_not_logged(tmp_path, capsys):
    secret = "synthetic-secret-for-child-environment"
    marker = tmp_path / "observed.json"
    code = "import json,os,sys;from pathlib import Path;Path(sys.argv[1]).write_text(json.dumps({'env':os.getenv('SECRET'),'argv':sys.argv}));print(os.getenv('SECRET'));sys.stderr.write(os.getenv('SECRET'))"
    result = job.supervise([sys.executable, "-c", code, str(marker)],
        environment={**os.environ, "SECRET": secret}, timeout_seconds=5)
    assert result == job.Supervision(0, False, False, 0)
    observed = json.loads(marker.read_bytes())
    assert observed["env"] == secret and secret not in " ".join(observed["argv"])
    assert secret not in capsys.readouterr().out


@LINUX
def test_wall_timeout_kills_only_own_group_including_term_ignoring_descendant(tmp_path):
    child_pid = tmp_path / "descendant.pid"
    marker = tmp_path / "late-publication"
    child = "import signal,time;from pathlib import Path;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(2);Path(" + repr(str(marker)) + ").write_text('must not publish')"
    worker = "import subprocess,sys,time;from pathlib import Path;p=subprocess.Popen([sys.executable,'-c'," + repr(child) + "]);Path(sys.argv[1]).write_text(str(p.pid));time.sleep(30)"
    bystander = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(30)"], start_new_session=True)
    try:
        started = time.monotonic()
        result = job.supervise([sys.executable, "-c", worker, str(child_pid)], environment=dict(os.environ),
            timeout_seconds=0.6, grace_seconds=0.2)
        assert result.timed_out and result.active_owned_processes == 0
        assert time.monotonic() - started < 3
        assert bystander.poll() is None and not marker.exists()
        pid = int(child_pid.read_text())
        stat_path = Path("/proc") / str(pid) / "stat"
        assert not stat_path.exists() or stat_path.read_text().rsplit(")", 1)[1].split()[0] in {"Z", "X"}
    finally:
        bystander.terminate()
        bystander.wait(timeout=5)


@LINUX
def test_leader_success_with_living_descendant_is_failure_and_closes_group(tmp_path):
    pidfile = tmp_path / "pid"
    code = "import subprocess,sys;from pathlib import Path;p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)']);Path(sys.argv[1]).write_text(str(p.pid))"
    result = job.supervise([sys.executable, "-c", code, str(pidfile)], environment=dict(os.environ),
        timeout_seconds=5, grace_seconds=0.2)
    assert result.exit_code == 0 and result.descendants_detected and result.active_owned_processes == 0


@pytest.fixture
def controller(monkeypatch):
    """Pure control-flow fixture; no OS platform spoof and no real signals."""
    signals = []
    process = SimpleNamespace(pid=123456789)
    monkeypatch.setattr(job.signal, "SIGKILL", 9, raising=False)
    monkeypatch.setattr(job.os, "killpg", lambda group, sig: signals.append((group, sig)), raising=False)
    monkeypatch.setattr(job, "_leader_exited", lambda process: True)
    return process, signals


@pytest.mark.parametrize("failure", [PermissionError, OSError, ValueError, IndexError])
def test_observation_failure_cannot_block_owned_term_and_kill(controller, monkeypatch, failure):
    process, signals = controller

    def unreadable(group):
        raise failure("synthetic proc observation failure")

    monkeypatch.setattr(job, "_active_group", unreadable)
    assert job._close_group(process, 0.001) == -1
    assert signals == [(process.pid, job.signal.SIGTERM), (process.pid, job.signal.SIGKILL)]


def test_recovered_observation_preserves_failure_even_after_verified_empty_group(controller, monkeypatch):
    process, signals = controller
    observations = iter([None, []])
    monkeypatch.setattr(job, "_observe_group", lambda group: next(observations))
    assert job._close_group(process, 0.01) == -1
    assert signals == [(process.pid, job.signal.SIGTERM)]


def test_verified_empty_group_needs_no_signals(controller, monkeypatch):
    process, signals = controller
    monkeypatch.setattr(job, "_active_group", lambda group: [])
    assert job._close_group(process, 0.01) == 0
    assert signals == []


def test_esrch_does_not_turn_unknown_proc_state_into_verified_closure(controller, monkeypatch):
    process, signals = controller
    monkeypatch.setattr(job, "_observe_group", lambda group: None)

    def missing(group, sig):
        signals.append((group, sig))
        raise ProcessLookupError("synthetic ESRCH")

    monkeypatch.setattr(job.os, "killpg", missing)
    assert job._close_group(process, 0.001) == -1
    assert [group for group, _ in signals] == [process.pid, process.pid]


def test_signal_failure_still_attempts_kill_and_never_claims_closure(controller, monkeypatch):
    process, signals = controller
    monkeypatch.setattr(job, "_active_group", lambda group: [process.pid])

    def denied(group, sig):
        signals.append((group, sig))
        raise PermissionError("synthetic signal failure")

    monkeypatch.setattr(job.os, "killpg", denied)
    assert job._close_group(process, 0.001) == -1
    assert signals == [(process.pid, job.signal.SIGTERM), (process.pid, job.signal.SIGKILL)]


@pytest.mark.parametrize("contents", ["malformed", "1 (process) R 1 invalid", "1 (process) R"])
def test_malformed_proc_rows_remain_unknown(monkeypatch, contents):
    entry = SimpleNamespace(name="123456789")
    entry_type = type("ProcEntry", (), {"name": entry.name,
        "__truediv__": lambda self, name: SimpleNamespace(read_text=lambda: contents)})
    monkeypatch.setattr(job, "Path", lambda value: SimpleNamespace(iterdir=lambda: [entry_type()]))
    assert job._observe_group(123456789) is None


def test_leader_observation_reserves_identity_without_poll_or_reap(monkeypatch):
    calls = []
    for name, value in (("P_PID", 1), ("WEXITED", 4), ("WNOHANG", 1), ("WNOWAIT", 0x1000000)):
        monkeypatch.setattr(job.os, name, value, raising=False)

    def waitid(*args):
        calls.append(args)
        return SimpleNamespace(si_pid=123456789)

    monkeypatch.setattr(job.os, "waitid", waitid, raising=False)
    assert job._leader_exited(SimpleNamespace(pid=123456789)) is True
    assert calls == [(job.os.P_PID, 123456789, job.os.WEXITED | job.os.WNOHANG | job.os.WNOWAIT)]


@LINUX
def test_real_proc_failure_still_kills_owned_worker_and_preserves_bystander(tmp_path, monkeypatch):
    pidfile = tmp_path / "worker-pid"
    worker = "import os,signal,time;from pathlib import Path;signal.signal(signal.SIGTERM,signal.SIG_IGN);Path(" + repr(str(pidfile)) + ").write_text(str(os.getpid()));time.sleep(30)"
    bystander = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(30)"], start_new_session=True)
    original_popen = subprocess.Popen
    original_killpg = os.killpg
    owned = []
    events = []

    def start_owned(*args, **kwargs):
        process = original_popen(*args, **kwargs)
        original_wait = process.wait

        def final_reap(*wait_args, **wait_kwargs):
            events.append("wait")
            return original_wait(*wait_args, **wait_kwargs)

        process.wait = final_reap
        owned.append(process)
        return process

    def signal_owned(group, sig):
        process = owned[0]
        assert group == process.pid and process.returncode is None
        # WNOWAIT still addresses our unreaped child immediately before each
        # signal, including when it has exited: its PID has not been recycled.
        observed = os.waitid(os.P_PID, group, os.WEXITED | os.WNOHANG | os.WNOWAIT)
        assert observed is None or observed.si_pid == group
        events.append(sig)
        original_killpg(group, sig)

    def failed_observation(group):
        raise PermissionError("synthetic unreadable proc entry")

    monkeypatch.setattr(job, "_active_group", failed_observation)
    monkeypatch.setattr(job.subprocess, "Popen", start_owned)
    monkeypatch.setattr(job.os, "killpg", signal_owned)
    try:
        started = time.monotonic()
        result = job.supervise([sys.executable, "-c", worker], environment=dict(os.environ),
            timeout_seconds=1, grace_seconds=0.05)
        assert result.timed_out and result.active_owned_processes == -1
        assert result.exit_code == -job.signal.SIGKILL and time.monotonic() - started < 4
        assert events == [job.signal.SIGTERM, job.signal.SIGKILL, "wait"]
        with pytest.raises(ChildProcessError):
            os.waitid(os.P_PID, owned[0].pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
        assert bystander.poll() is None
        assert not (Path("/proc") / pidfile.read_text()).exists()
    finally:
        bystander.terminate()
        bystander.wait(timeout=5)

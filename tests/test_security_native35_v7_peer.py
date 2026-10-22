"""Finite native35 V7 admission, truthful stop and immutable oracle controls."""
import ast
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.e2e import native35_guard_v7 as guard

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 22, tzinfo=UTC)


def ack_pair():
    expected = {"scope": "native35-v7-sql", "source_head": "a" * 40,
                "selection": "current35", "expected_groups": [15, 18, 2], "UUIDs": 1}
    return expected, {**expected, "granted": True, "expires_at_UTC": (NOW + timedelta(hours=1)).isoformat()}


@pytest.mark.parametrize("fault", ["expired", "exact-expiry", "too-long", "naive", "missing", "wrong-type",
                                  "boolean-budget", "boolean-group", "not-granted", "source", "extra"])
def test_typed_finite_ACK_boundaries(fault):
    expected, value = ack_pair()
    if fault == "expired":
        value["expires_at_UTC"] = (NOW - timedelta(seconds=1)).isoformat()
    elif fault == "exact-expiry":
        value["expires_at_UTC"] = NOW.isoformat()
    elif fault == "too-long":
        value["expires_at_UTC"] = (NOW + timedelta(hours=4, seconds=1)).isoformat()
    elif fault == "naive":
        value["expires_at_UTC"] = "2026-10-22T01:00:00"
    elif fault == "missing":
        value.pop("expires_at_UTC")
    elif fault == "wrong-type":
        value["expires_at_UTC"] = True
    elif fault == "boolean-budget":
        value["UUIDs"] = True
    elif fault == "boolean-group":
        value["expected_groups"] = [True, 18, 2]
    elif fault == "not-granted":
        value["granted"] = False
    elif fault == "source":
        value["source_head"] = "b" * 40
    else:
        value["unbound"] = True
    starts = []
    with pytest.raises((ValueError, TypeError)):
        guard.admitted_phase(lambda: guard.validate_ack(value, expected, NOW), lambda: starts.append("SQL/child"))
    assert starts == []


def test_valid_control_admits_only_injected_marker():
    expected, value = ack_pair()
    starts = []
    guard.admitted_phase(lambda: guard.validate_ack(value, expected, NOW), lambda: starts.append("fake child"))
    assert starts == ["fake child"]


def test_expiry_during_child_allows_own_finalizer_but_refuses_next_phase():
    expected, value = ack_pair()
    clock, events = [NOW], []
    check = lambda: guard.validate_ack(value, expected, clock[0])

    def child():
        events.append("first child started")
        clock[0] += timedelta(hours=2)
        events.append("first child finished")
        events.append("own finalizer finished after expiry")

    guard.admitted_phase(check, child)
    with pytest.raises(ValueError, match="expired"):
        guard.admitted_phase(check, lambda: events.append("forbidden second child"))
    assert events == ["first child started", "first child finished", "own finalizer finished after expiry"]


def test_browser_readmission_requires_SQL_then_Chrome_and_stops_on_expired_SQL(monkeypatch):
    seen = []
    monkeypatch.setattr(guard, "require_ack", lambda _task, phase: seen.append(phase) or phase)
    assert guard.require_chrome_phase("unused") == {"sql": "sql", "chrome": "chrome"}
    assert seen == ["sql", "chrome"]
    seen.clear()

    def expired(_task, phase):
        seen.append(phase)
        raise ValueError("Expired SQL")

    monkeypatch.setattr(guard, "require_ack", expired)
    with pytest.raises(ValueError):
        guard.require_chrome_phase("unused")
    assert seen == ["sql"]


@pytest.mark.parametrize("expired", [True, False])
def test_actual_new_launcher_refuses_expired_before_fake_SQL_fixture_and_has_valid_control(tmp_path, monkeypatch, expired):
    file = ROOT / "tests/e2e/run_native35_qa_v7.py"
    spec = importlib.util.spec_from_file_location("new_native35_admission", file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    task = tmp_path / "metodobase-account37-author-pg-new-v7-purecanary"
    (task / "private").mkdir(parents=True)
    (task / "leases").mkdir()
    head = "a" * 40
    monkeypatch.setattr(guard, "source_context", lambda: head)
    preflight = {"schema": "native35-v7", "product_source": guard.SOURCE, "source_head": head,
                 "selection": "current35", "expected_groups": [15, 18, 2],
                 "profile_path": str(guard.PROFILE), "profile_sha256": guard.PROFILE_SHA,
                 "source_RAW_sha256": {}, "packages": [], "installed_map_sha256": guard.digest(b"{}")}
    preflight_path = task / "native-preflight.json"
    preflight_path.write_text(json.dumps(preflight), encoding="utf8")
    expiry = datetime.now(UTC) + timedelta(hours=-1 if expired else 1)
    ack = {"scope": "native35-v7-sql", "source_head": head, "product_source": guard.SOURCE,
           "selection": "current35", "expected_groups": [15, 18, 2], "UUIDs": 1,
           "preflight_sha256": guard.digest(preflight_path.read_bytes()), "profile_sha256": guard.PROFILE_SHA,
           "launcher_sha256": guard.digest(file.read_bytes()),
           "fixture_sha256": guard.digest((ROOT / "tests/e2e/native35_postgres_server_v7.py").read_bytes()),
           "guard_sha256": guard.digest(Path(guard.__file__).read_bytes()),
           "granted": True, "expires_at_UTC": expiry.isoformat()}
    (task / "native-sql-ack.json").write_text(json.dumps(ack), encoding="utf8")
    attempts = []

    def fake_popen(*_args, **_kwargs):
        attempts.append("fixture marker only")
        raise RuntimeError("No actual child")

    class FakeSocket:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def bind(self, _address):
            return None

    library = SimpleNamespace(__file__=str(ROOT / "tests/e2e/native37_environment_qa.py"), pipcheck=lambda *_args: None)
    import tests.e2e
    monkeypatch.setitem(sys.modules, "tests.e2e.native37_environment_qa", library)
    monkeypatch.setattr(tests.e2e, "native37_environment_qa", library, raising=False)
    monkeypatch.setattr(module, "subprocess", SimpleNamespace(check_output=lambda *_args, **_kwargs: head, Popen=fake_popen))
    monkeypatch.setattr(module, "socket", SimpleNamespace(socket=FakeSocket))
    monkeypatch.setattr(module, "fingerprint_snapshot", lambda *_args: {"head": head, "source": {}, "packages": [], "installed": {}})
    monkeypatch.setattr(module, "inventory", lambda *_args: {"processes": [], "listeners": []})
    monkeypatch.setattr(module, "put", lambda *_args: None)
    monkeypatch.setattr(sys, "argv", [str(file), "--private-root", str(task), "--pg-config", str(guard.PROFILE), "--selection", "current35"])
    with pytest.raises(ValueError if expired else AssertionError):
        module.main()
    assert attempts == ([] if expired else ["fixture marker only"])


def fixture_controls(tmp_path, monkeypatch):
    local = tmp_path / "source"
    helpers = local / "tests/e2e"
    helpers.mkdir(parents=True)
    for name in ("run_native35_qa_v7.py", "native35_postgres_server_v7.py"):
        (helpers / name).write_bytes((ROOT / "tests/e2e" / name).read_bytes())
    monkeypatch.setattr(guard, "ROOT", local)
    task = tmp_path / "task"
    (task / "private").mkdir(parents=True)
    (task / "private/startup.json").write_bytes(b'{"synthetic":true}')
    preflight = {"schema": "native35-v7", "product_source": guard.SOURCE, "source_head": "a" * 40,
                 "profile_path": str(guard.PROFILE), "profile_sha256": guard.PROFILE_SHA}
    monkeypatch.setattr(guard, "source_context", lambda: preflight["source_head"])
    (task / "native-preflight.json").write_text(json.dumps(preflight), encoding="utf8")
    expected = {"scope": "native35-v7-sql", "source_head": preflight["source_head"], "product_source": guard.SOURCE,
                "selection": "current35", "expected_groups": [15, 18, 2], "UUIDs": 1,
                "preflight_sha256": guard.digest((task / "native-preflight.json").read_bytes()),
                "profile_sha256": guard.PROFILE_SHA,
                "launcher_sha256": guard.digest((helpers / "run_native35_qa_v7.py").read_bytes()),
                "fixture_sha256": guard.digest((helpers / "native35_postgres_server_v7.py").read_bytes()),
                "guard_sha256": guard.digest(Path(guard.__file__).read_bytes())}
    for phase in ("sql", "chrome"):
        value = {**expected, "scope": "native35-v7-" + phase, "granted": True,
                 "expires_at_UTC": (NOW + timedelta(hours=1)).isoformat()}
        if phase == "chrome":
            value["startup_sha256"] = guard.digest((task / "private/startup.json").read_bytes())
        (task / ("native-" + phase + "-ack.json")).write_text(json.dumps(value), encoding="utf8")
    return task, helpers


@pytest.mark.parametrize("phase", ["sql", "chrome"])
def test_actual_file_bound_ACK_reader_accepts_pinned_control(tmp_path, monkeypatch, phase):
    task, _helpers = fixture_controls(tmp_path, monkeypatch)
    result = guard.require_ack(task, phase, NOW)
    assert result == guard.digest((task / ("native-" + phase + "-ack.json")).read_bytes())


@pytest.mark.parametrize("fault", ["fixture", "launcher", "preflight", "startup", "profile-path", "expiry", "source-head"])
def test_actual_file_bound_ACK_reader_refuses_drift(tmp_path, monkeypatch, fault):
    task, helpers = fixture_controls(tmp_path, monkeypatch)
    if fault in {"fixture", "launcher"}:
        name = "native35_postgres_server_v7.py" if fault == "fixture" else "run_native35_qa_v7.py"
        with (helpers / name).open("ab") as output:
            output.write(b" ")
    elif fault == "preflight":
        with (task / "native-preflight.json").open("ab") as output:
            output.write(b" ")
    elif fault == "startup":
        with (task / "private/startup.json").open("ab") as output:
            output.write(b" ")
    elif fault == "profile-path":
        value = json.loads((task / "native-preflight.json").read_bytes())
        value["profile_path"] += ".unapproved"
        (task / "native-preflight.json").write_text(json.dumps(value), encoding="utf8")
    elif fault == "source-head":
        monkeypatch.setattr(guard, "source_context", lambda: "b" * 40)
    else:
        value = json.loads((task / "native-chrome-ack.json").read_bytes())
        value["expires_at_UTC"] = NOW.isoformat()
        (task / "native-chrome-ack.json").write_text(json.dumps(value), encoding="utf8")
    with pytest.raises(ValueError):
        guard.require_ack(task, "chrome", NOW)


@pytest.mark.parametrize("fault", ["PID", "boolean-PID", "generation", "source", "action", "extra", "birth", "duplicate", "oversize"])
def test_private_stop_rejects_stale_or_unbound_request(tmp_path, fault):
    packet = {"action": "stop", "pid": 123, "generation": "a" * 32, "source_commit": "b" * 40}
    identity = [123, 456]
    control = guard.PrivateStop(tmp_path, 123, "a" * 32, "b" * 40, 456, lambda: tuple(identity))
    if fault == "PID":
        packet["pid"] = 124
    elif fault == "boolean-PID":
        packet["pid"] = True
    elif fault == "generation":
        packet["generation"] = "c" * 32
    elif fault == "source":
        packet["source_commit"] = "d" * 40
    elif fault == "action":
        packet["action"] = "other"
    elif fault == "extra":
        packet["birth"] = 456
    elif fault == "birth":
        identity[1] += 1
    raw = json.dumps(packet).encode()
    if fault == "duplicate":
        raw = raw[:-1] + b',"pid":123}'
    elif fault == "oversize":
        raw += b" " * 4096
    (tmp_path / "stop-request.private.json").write_bytes(raw)
    assert control.inspect() is False and control.accepted is False and control.refusals == 1


def test_positive_stop_and_cleanup_do_not_revalidate_expired_start_ACK(tmp_path, monkeypatch):
    (tmp_path / "stop-request.private.json").write_text(json.dumps({"action": "stop", "pid": 123,
        "generation": "a" * 32, "source_commit": "b" * 40}), encoding="utf8")
    monkeypatch.setattr(guard, "require_ack", lambda *_args: pytest.fail("Cleanup must not readmit a new phase"))
    control = guard.PrivateStop(tmp_path, 123, "a" * 32, "b" * 40, 456, lambda: (123, 456))
    assert control.inspect() is True
    assert guard.stop_receipt(True, True, True, True, control, None)["normal_shutdown_accepted"] is True


@pytest.mark.parametrize("fault", ["not-closed", "not-started", "run-raised", "watcher-live", "no-request", "error"])
def test_receipt_never_labels_failed_or_unowned_close_normal(tmp_path, fault):
    control = guard.PrivateStop(tmp_path, 123, "a" * 32, "b" * 40, 456, lambda: (123, 456))
    control.accepted = fault != "no-request"
    values = [True, True, True, True]
    if fault in ("not-closed", "not-started", "run-raised", "watcher-live"):
        values[("not-closed", "not-started", "run-raised", "watcher-live").index(fault)] = False
    result = guard.stop_receipt(*values, control, "SyntheticError" if fault == "error" else None)
    assert result["normal_shutdown_accepted"] is False
    if fault == "run-raised":
        assert result["normal_return"] is False


@pytest.mark.parametrize("fault", ["stale-birth", "stale-fact", "metadata-PID", "metadata-birth", "metadata-generation", "metadata-source", "positive"])
def test_sender_retains_HANDLE_and_revalidates_identity_before_four_key_stop(tmp_path, monkeypatch, fault):
    startup = {"pid": 123, "process_birth": 456, "generation": "a" * 32, "source_commit": "b" * 40}
    executable = str(Path(sys.executable).resolve())
    fact = {"ProcessId": 123, "ParentProcessId": 77, "ExecutablePath": executable, "CommandLine": "synthetic"}
    clock, closed = [456], []
    monkeypatch.setattr(guard, "_api", lambda: SimpleNamespace(OpenProcess=lambda *_args: 333,
                                                            CloseHandle=lambda handle: closed.append(handle)))
    monkeypatch.setattr(guard, "_birth", lambda _handle: clock[0])
    monkeypatch.setattr(guard, "_fact", lambda _pid: dict(fact))
    monkeypatch.setattr(guard, "_argv", lambda _command: [executable, "-B", "synthetic.py"])
    monkeypatch.setattr(guard, "require_ack", lambda *_args: pytest.fail("Owned cleanup must remain valid after expiry"))
    worker = guard.OwnedWorker(startup, [executable, "-B", "synthetic.py"], 77, executable)
    assert worker.handle == 333 and closed == []
    metadata = dict(startup)
    if fault == "stale-birth":
        clock[0] += 1
    elif fault == "stale-fact":
        fact["CommandLine"] = "changed"
    elif fault == "metadata-PID":
        metadata["pid"] += 1
    elif fault == "metadata-birth":
        metadata["process_birth"] += 1
    elif fault == "metadata-generation":
        metadata["generation"] = "c" * 32
    elif fault == "metadata-source":
        metadata["source_commit"] = "d" * 40
    (tmp_path / "native35-instance.private.json").write_text(json.dumps(metadata), encoding="utf8")
    try:
        if fault == "positive":
            worker.request_stop(tmp_path)
            packet = json.loads((tmp_path / "stop-request.private.json").read_bytes())
            assert packet == {"action": "stop", "pid": 123, "generation": "a" * 32, "source_commit": "b" * 40}
            receiver = guard.PrivateStop(tmp_path, 123, "a" * 32, "b" * 40, 456, lambda: (123, 456))
            assert receiver.inspect() is True
        else:
            with pytest.raises(ValueError):
                worker.request_stop(tmp_path)
            assert not (tmp_path / "stop-request.private.json").exists()
    finally:
        worker.close()
    assert worker.handle is None and closed == [333]


@pytest.mark.parametrize("fault", ["PID", "address", "absent", "positive"])
def test_actual_listener_observation_requires_the_exact_worker_and_loopback(monkeypatch, fault):
    rows = [{"LocalAddress": "127.0.0.1", "LocalPort": 8802, "OwningProcess": 123}]
    if fault == "PID":
        rows[0]["OwningProcess"] = 124
    elif fault == "address":
        rows[0]["LocalAddress"] = "0.0.0.0"
    elif fault == "absent":
        rows.clear()
    fake = SimpleNamespace(stdout=json.dumps({"rows": rows}).encode(), stderr=b"")
    monkeypatch.setattr(guard.subprocess, "run", lambda *_args, **_kwargs: fake)
    if fault == "positive":
        assert guard.verify_listener(123) == rows
    else:
        with pytest.raises(ValueError):
            guard.verify_listener(123)


def test_derived_harness_has_exact_full_inverse_and_original22_RAW_are_unchanged():
    boundaries = json.loads((ROOT / "tests/e2e/native35_v7_boundaries.json").read_bytes())
    for record in boundaries["boundaries"]:
        current = (ROOT / record["companion"]).read_text(encoding="utf8")
        for change in reversed(record["changes"]):
            assert current.count(change["after"]) == 1
            current = current.replace(change["after"], change["before"])
        original = (ROOT / record["original"]).read_bytes()
        assert current.encode() == original
        assert ast.dump(ast.parse(current)) == ast.dump(ast.parse(original))
    original = json.loads((ROOT / "tests/e2e/native37_transitive_qa_v6.json").read_bytes())
    assert len(original["helper_union"]) == 22
    for name, record in original["helper_union"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == record["raw_sha256"]
    launcher = (ROOT / "tests/e2e/run_native35_qa_v7.py").read_text(encoding="utf8")
    fixture = (ROOT / "tests/e2e/native35_postgres_server_v7.py").read_text(encoding="utf8")
    assert "child=admitted_phase(lambda:require_chrome_phase(TASK)" in launcher
    assert "server=admitted_phase(lambda:require_ack(TASK,'sql')" in launcher
    assert fixture.index('require_ack(private.parent, "sql")', fixture.index('    try:\n        require_ack')) < fixture.index('with owned_database("postgresql"')
    assert "if stop_guard.inspect():" in fixture and '(private / "stop").exists()' not in fixture
    for name in ("native35_guard_v7.py", "native35_postgres_server_v7.py", "run_native35_qa_v7.py"):
        compile((ROOT / "tests/e2e" / name).read_bytes(), name, "exec")


@pytest.mark.parametrize("driver", ["mfa_ui_browser", "mfa_personal_browser"])
def test_original_MFA_compiler_only_preserves_business_oracles(driver):
    node = shutil.which("node")
    assert node is not None, "Node is required for the native compiler control"
    result = subprocess.run([node, "tests/e2e/native37_mfa_compat_qa_v6.cjs",
                             driver, "--compile-only"], cwd=ROOT, capture_output=True, check=True)
    value = json.loads(result.stdout)
    assert value["parsed"] is True
    assert value["browser_session_composition"]["assertion_calls_preserved_before_normative_changes"] > 0
    assert "--compile-only" in value["browser_session_composition"]["scope"]


@pytest.mark.parametrize("driver", ["native37_account_notifications_qa_v4.cjs", "native37_onboarding_r22_qa_v5.cjs"])
def test_original18_and2_syntax_only_not_an_unsupported_compile_flag(driver):
    # These two scripts have no --compile-only branch. --check never executes them.
    node = shutil.which("node")
    assert node is not None, "Node is required for the native syntax control"
    result = subprocess.run([node, "--check", "tests/e2e/" + driver],
                            cwd=ROOT, capture_output=True, check=True)
    assert result.stdout == result.stderr == b""

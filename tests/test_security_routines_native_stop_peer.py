"""Private lifecycle-control tests; fake server/engine, no SQL or listener."""
import importlib.util
import json
import threading
from pathlib import Path

import pytest

FIXTURE = Path(__file__).resolve().parents[1] / "tests/e2e/security_routines37_server_peer.py"
IDENTITY = {"pid": 12345, "generation": "a" * 32,
            "source_commit": "50325b464169fc750d9f39e339d874a716030797"}


@pytest.fixture
def helper():
    spec = importlib.util.spec_from_file_location("own_routine_stop_fixture", FIXTURE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("change", [
    {"pid": 54321}, {"generation": "b" * 32}, {"source_commit": "0" * 40},
    {"pid": True}, {"action": "terminate"}, {"extra": True},
])
def test_foreign_or_malformed_stop_never_admits_an_instance(helper, change):
    with pytest.raises(ValueError):
        helper.validate_stop_request({"action": "stop", **IDENTITY, **change}, IDENTITY)


class FakeEngine:
    disposed = False

    def dispose(self):
        self.disposed = True


def test_exact_private_stop_runs_finalizer_without_rechecking_expired_ACK(helper, tmp_path, monkeypatch):
    class FakeServer:
        started = False
        should_exit = False

        def run(self):
            self.started = True
            helper.write(tmp_path / "stop-request.private.json", {"action": "stop", **IDENTITY})
            for _ in range(200):
                if self.should_exit:
                    return
                threading.Event().wait(0.01)
            raise AssertionError("Private fake server stop timed out")

    def expired(*_args):
        raise AssertionError("An expired start ACK must not block normal cleanup")

    monkeypatch.setattr(helper, "require_lease", expired)
    server, engine = FakeServer(), FakeEngine()
    receipt = helper.run_owned_server(server, engine, tmp_path, IDENTITY)
    assert server.should_exit is True and engine.disposed is True
    assert receipt["normal_shutdown_accepted"] is True
    assert receipt["server_started"] is receipt["stop_request_accepted"] is receipt["normal_return"] is True
    assert receipt["watcher_stopped_joined"] is True and receipt["error_class"] is None
    assert receipt["stop_request_sha256"] == helper.digest((tmp_path / "stop-request.private.json").read_bytes())
    assert json.loads((tmp_path / "fixture-closed.private.json").read_bytes()) == receipt
    assert not any(thread.name == "routine-own-stop" for thread in threading.enumerate())


def test_run_exception_is_not_labelled_normal_and_still_disposes_and_joins(helper, tmp_path):
    class BrokenServer:
        started = False
        should_exit = False

        def run(self):
            raise RuntimeError("Synthetic private error text must not enter the receipt")

    engine = FakeEngine()
    with pytest.raises(RuntimeError):
        helper.run_owned_server(BrokenServer(), engine, tmp_path, IDENTITY)
    raw = (tmp_path / "fixture-closed.private.json").read_text(encoding="utf8")
    receipt = json.loads(raw)
    assert receipt["normal_return"] is receipt["normal_shutdown_accepted"] is False
    assert receipt["server_started"] is receipt["stop_request_accepted"] is False
    assert receipt["owned_engine_disposed"] is receipt["watcher_stopped_joined"] is True
    assert receipt["error_class"] == "RuntimeError" and "Synthetic private error" not in raw
    assert engine.disposed is True


def test_plain_server_return_does_not_prove_an_owned_stop(helper, tmp_path):
    class ReturnedServer:
        started = True
        should_exit = False

        def run(self):
            return

    receipt = helper.run_owned_server(ReturnedServer(), FakeEngine(), tmp_path, IDENTITY)
    assert receipt["normal_return"] is receipt["server_started"] is True
    assert receipt["stop_request_accepted"] is receipt["normal_shutdown_accepted"] is False
    assert receipt["watcher_stopped_joined"] is True


def test_disposal_error_keeps_normal_run_fact_but_refuses_complete_shutdown(helper, tmp_path):
    class ReturnedServer:
        started = True
        should_exit = False

        def run(self):
            return

    class BrokenEngine:
        def dispose(self):
            raise ValueError("Synthetic disposal text is private")

    with pytest.raises(ValueError):
        helper.run_owned_server(ReturnedServer(), BrokenEngine(), tmp_path, IDENTITY)
    raw = (tmp_path / "fixture-closed.private.json").read_text(encoding="utf8")
    receipt = json.loads(raw)
    assert receipt["normal_return"] is True
    assert receipt["normal_shutdown_accepted"] is receipt["owned_engine_disposed"] is False
    assert receipt["watcher_stopped_joined"] is True
    assert receipt["error_class"] == "ValueError" and "Synthetic disposal" not in raw

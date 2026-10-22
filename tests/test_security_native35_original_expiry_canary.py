"""Immutable original V6 admission canary; fake Popen and socket, no SQL/process."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "tests/e2e/run_native37_qa_v6.py"


def original_admission(tmp_path, monkeypatch, expiry):
    spec = importlib.util.spec_from_file_location("literal_original_native35", ORIGINAL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    task = tmp_path / "metodobase-account37-author-pg-purecanary"
    (task / "private").mkdir(parents=True)
    (task / "leases").mkdir()
    profile = task / "profile.private.json"
    profile.write_bytes(b"{}")
    head = "a" * 40
    photo = {"head": head, "source": {}, "packages": {}, "installed": {}}
    preflight = {"selection": "current35", "expected_groups": [15, 18, 2],
                 "source_head": head, "profile_sha256": hashlib.sha256(b"{}").hexdigest(),
                 "source_RAW_sha256": {}, "packages": {},
                 "installed_map_sha256": hashlib.sha256(b"{}").hexdigest()}
    ack = {"selection": "current35", "expected_groups": [15, 18, 2], "granted": True,
           "UUIDs": 1, "source_head": head, "expires_at_UTC": expiry,
           "launcher_sha256": hashlib.sha256(ORIGINAL.read_bytes()).hexdigest()}
    for name, value in (("native-preflight.json", preflight), ("native-sql-ack.json", ack)):
        (task / name).write_text(json.dumps(value), encoding="utf8")
    attempts = []

    def fake_popen(*args, **kwargs):
        attempts.append("fixture admitted before SQL")
        raise RuntimeError("Pure admission marker; no child exists")

    class FakeSocket:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def bind(self, _address):
            return None

    fake_library = SimpleNamespace(__file__=str(ROOT / "tests/e2e/native37_environment_qa.py"),
                                   pipcheck=lambda *_args: None)
    monkeypatch.setitem(sys.modules, "tests.e2e.native37_environment_qa", fake_library)
    import tests.e2e
    monkeypatch.setattr(tests.e2e, "native37_environment_qa", fake_library, raising=False)
    monkeypatch.setattr(module, "subprocess", SimpleNamespace(check_output=lambda *_args, **_kwargs: head,
                                                            Popen=fake_popen))
    monkeypatch.setattr(module, "socket", SimpleNamespace(socket=FakeSocket))
    monkeypatch.setattr(module, "fingerprint_snapshot", lambda *_args: photo)
    monkeypatch.setattr(module, "inventory", lambda *_args: {"processes": [], "listeners": []})
    monkeypatch.setattr(module, "put", lambda *_args: None)
    monkeypatch.setattr(sys, "argv", [str(ORIGINAL), "--private-root", str(task), "--pg-config", str(profile),
                                     "--selection", "current35"])
    with pytest.raises(AssertionError, match="Fixture must exit zero"):
        module.main()
    return attempts


def test_original_expired_sql_ack_must_refuse_before_first_fixture_admission(tmp_path, monkeypatch):
    assert original_admission(tmp_path, monkeypatch, "2000-01-01T00:00:00+00:00") == []


def test_original_unexpired_control_reaches_only_fake_fixture_marker(tmp_path, monkeypatch):
    assert original_admission(tmp_path, monkeypatch, "2099-01-01T00:00:00+00:00") == ["fixture admitted before SQL"]

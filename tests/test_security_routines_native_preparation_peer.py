"""Pure admission/compile checks only; never starts the native fixture."""
import importlib.util
import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/e2e/security_routines37_server_peer.py"
DRIVER = ROOT / "tests/e2e/security_routines_browser37_peer.cjs"
NODE = "C:/Program Files/nodejs/node.exe"
SOURCE = "50325b464169fc750d9f39e339d874a716030797"


@pytest.fixture
def helper():
    spec = importlib.util.spec_from_file_location("own_routine_native_fixture", FIXTURE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ack(helper, private):
    return {"approved": True, "scope": "routines37-saas-sqlite-native-exclusive-v1",
            "source_commit": SOURCE, "private_directory": str(private),
            "fixture_sha256": helper.digest(FIXTURE.read_bytes()), "port": 8812,
            "expires_at_UTC": (datetime.now(UTC) + timedelta(hours=1)).isoformat()}


def test_exact_unexpired_ack_admits_only_its_contract(helper, tmp_path):
    value = ack(helper, tmp_path)
    path = tmp_path / "synthetic-only-not-a-Root-runtime-ACK.json"
    path.write_text(json.dumps(value), encoding="utf8")
    helper.require_lease(path, SOURCE, tmp_path)


@pytest.mark.parametrize("field,value", [
    ("approved", 1), ("scope", "legacy-native-PG"), ("source_commit", "0" * 40),
    ("private_directory", "another-private-path"), ("fixture_sha256", "0" * 64),
    ("port", 8812.0), ("port", 8802),
    ("expires_at_UTC", "2000-01-01T00:00:00+00:00"),
    ("expires_at_UTC", "2099-01-01T00:00:00+00:00"),
    ("expires_at_UTC", "2099-01-01T00:00:00"),
])
def test_wrong_scope_source_bytes_or_expiry_refuses_without_side_effects(helper, tmp_path, field, value):
    entry = ack(helper, tmp_path)
    entry[field] = value
    path = tmp_path / "synthetic-invalid-ACK.json"
    path.write_text(json.dumps(entry), encoding="utf8")
    with pytest.raises(ValueError):
        helper.require_lease(path, SOURCE, tmp_path)


def test_wrong_frozen_product_refuses_before_environment_or_SQL(helper, tmp_path, monkeypatch):
    from tests import isolation

    touched = []
    monkeypatch.setattr(isolation, "prepare_environment", lambda **_kw: touched.append("environment"))

    def reject(argv, **_kw):
        assert argv[:4] == ["git", "--no-replace-objects", "diff", "--quiet"]
        raise subprocess.CalledProcessError(1, argv)

    monkeypatch.setattr(helper.subprocess, "run", reject)
    with pytest.raises(subprocess.CalledProcessError):
        helper.serve(tmp_path, SOURCE)
    assert touched == []


@pytest.mark.parametrize("actor,database", [("foreign", "unused"), ("owner", "outside-private")])
def test_retirement_never_selects_an_unowned_actor_or_database(helper, tmp_path, monkeypatch, actor, database):
    entry = {"actors": {"owner": {"id": "synthetic-only"}}, "sqlite_database": str(tmp_path.parent / database)}
    (tmp_path / "metadata.private.json").write_text(json.dumps(entry), encoding="utf8")
    called = []
    monkeypatch.setattr(helper.sqlite3, "connect", lambda *_args, **_kwargs: called.append("SQL"))
    with pytest.raises(ValueError):
        helper.retire(tmp_path, actor)
    assert called == []


def test_actual_driver_compiles_without_Playwright_or_metadata(tmp_path):
    result = subprocess.run([NODE, str(DRIVER), "--compile-only"], cwd=ROOT, capture_output=True, timeout=15, check=False)
    assert result.returncode == 0
    value = json.loads(result.stdout)
    assert value["actual_browser_started"] is False
    assert value["widths"] == [320, 390, 768, 1440]
    assert value["scenarios"] == 4 and value["planned_scoped_captures"] == 16
    assert result.stderr == b""


def test_driver_has_no_default_execution_path():
    result = subprocess.run([NODE, str(DRIVER)], cwd=ROOT, capture_output=True, timeout=15, check=False)
    assert result.returncode == 1
    assert result.stdout == b"" and result.stderr.strip() == b"AssertionError"

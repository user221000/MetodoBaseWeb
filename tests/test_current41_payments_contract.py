"""No SQL: exact new payments identities/budget and fail-closed Root authority."""
import ast
import json
import os
import stat
import tempfile
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from scripts.scan_secrets import _private_evidence
from tests.ci_web41 import payments_contract as contract


@pytest.fixture(scope="module", autouse=True)
def database_schema():
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


@pytest.fixture
def ack_environment(monkeypatch):
    """Use this unit campaign's actual private TEMP with the real validator.

    The serial runner deliberately makes a private child directory its TEMP.
    Only this test's process environment is aligned to that actual directory;
    private_workspace, ACL checks, UID and ACK validation remain unmodified.
    """
    if os.name == "posix":
        if (os.environ.get("GITHUB_ACTIONS") != "true"
                or Path(os.environ["GITHUB_WORKSPACE"]).resolve(strict=True) != contract.ROOT):
            raise ValueError("The ACK unit context requires the existing genuine CI checkout")
        temporary = Path(tempfile.gettempdir()).resolve(strict=True)
        for name in ("TEMP", "TMP", "TMPDIR", "RUNNER_TEMP"):
            monkeypatch.setenv(name, str(temporary))
    from tests.billing13_legacy_apply37_pg_contract import private_workspace
    return private_workspace()


def _write_private_ack(path, data):
    def private_opener(name, flags):
        return os.open(name, flags, 0o600)
    with open(path, "x", encoding="utf8", opener=private_opener) as output:
        json.dump(data, output)


def test_separate_five_identities_and_two_backend_budget_leave_privacy_phases_literal():
    body = ast.parse((contract.ROOT / contract.MODULE).read_bytes())
    names = [node.name for node in body.body if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")]
    assert names == list(contract.CURRENT_CASES) and len(names) == len(set(names)) == 5
    assert contract.CASES == (*contract.CURRENT_CASES, *contract.PEER_CASES)
    assert len(contract.PEER_CASES) == 7 and len(set(contract.CASES)) == 12
    assert contract.PLAN == {"cases": 12, "UUIDs": 1, "concurrent_UUIDs": 1, "application_pool": 2,
        "application_workers": 2, "max_overflow": 0, "database_admin_pool": 1,
        "control_observer_connections": 1, "historical_core_restore_budgets_unchanged": True}
    historical = json.loads((contract.ROOT / "tests/ci_web39/pg-plan.json").read_bytes())
    current = json.loads((contract.ROOT / "tests/ci_web41/pg-plan.json").read_bytes())
    assert set(historical["phases"]) == set(current["phases"]) == {"core", "restore"}
    for name in historical["phases"]:
        for field in ("UUIDs", "concurrent_UUIDs", "application_pool", "max_overflow"):
            assert current["phases"][name][field] == historical["phases"][name][field]


@pytest.mark.parametrize("fault", [None, "bool", "scope", "digest", "extra", "expired", "long", "naive", "source-changed"])
def test_root_ack_needs_exact_source_budget_identity_boolean_and_bounded_fresh_time(tmp_path, fault, ack_environment):
    private = _private_evidence(tmp_path / "payments41-authority")
    target = private / "ack.private.json"
    value = {"schema": contract.SCOPE, "plan": deepcopy(contract.PLAN), "FileSetDigest": "a" * 64}
    data = {"approved": True, "scope": contract.SCOPE, "contract_sha256": contract.digest(value),
            "expires_at_UTC": (datetime.now(UTC) + timedelta(hours=1)).isoformat()}
    if fault == "bool":
        data["approved"] = 1
    elif fault == "scope":
        data["scope"] = "privacy41-pg-exclusive-v1"
    elif fault == "digest":
        data["contract_sha256"] = "0" * 64
    elif fault == "extra":
        data["fallback"] = True
    elif fault == "expired":
        data["expires_at_UTC"] = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    elif fault == "long":
        data["expires_at_UTC"] = (datetime.now(UTC) + timedelta(hours=9)).isoformat()
    elif fault == "naive":
        data["expires_at_UTC"] = datetime.now().isoformat()
    elif fault == "source-changed":
        value["FileSetDigest"] = "b" * 64
    _write_private_ack(target, data)
    if fault is None:
        assert len(contract.require_ack(target, value)) == 64
    else:
        with pytest.raises(ValueError):
            contract.require_ack(target, value)


@pytest.mark.parametrize("mask", [0o022, 0o077])
def test_ack_file_is_private_from_its_first_byte_under_the_real_process_mask(tmp_path, monkeypatch, mask):
    from web.services.legacy_object_apply_boundary import verify
    private = _private_evidence(tmp_path / "private-ack-writer")
    path = private / "ack.private.json"
    actual_open = os.open
    observations = []
    def observe(name, flags, mode):
        descriptor = actual_open(name, flags, mode)
        observations.append((flags, mode, os.fstat(descriptor).st_size,
                             stat.S_IMODE(os.fstat(descriptor).st_mode)))
        return descriptor
    monkeypatch.setattr(os, "open", observe)
    old = os.umask(mask)
    try:
        _write_private_ack(path, {"synthetic": True})
    finally:
        os.umask(old)
    assert len(observations) == 1 and observations[0][1:3] == (0o600, 0)
    assert observations[0][0] & os.O_EXCL and observations[0][0] & os.O_CREAT
    if os.name == "posix":
        assert observations[0][3] == 0o600
    verify(path)


def test_private_ack_writer_refuses_to_replace_an_existing_authority(tmp_path):
    path = tmp_path / "existing"
    path.write_bytes(b"retained synthetic authority")
    with pytest.raises(FileExistsError):
        _write_private_ack(path, {"replacement": True})
    assert path.read_bytes() == b"retained synthetic authority"

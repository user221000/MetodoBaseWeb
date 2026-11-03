"""Fail closed on stale databases, incomplete scans and threshold mismatches."""
import ast
import hashlib
import json
import re
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from tests.ci_image57 import security_scan as scan


@pytest.fixture(scope="module", autouse=True)
def database_schema():
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


def test_accepts_only_fresh_valid_database():
    now = datetime.now(timezone.utc)
    assert scan.validate_db({"built": (now - timedelta(hours=1)).isoformat(), "valid": True}, now) == 3600
    for age, valid in ((86400, True), (86401, True), (-1, True), (3600, False), (3600, 1)):
        with pytest.raises(ValueError):
            scan.validate_db({"built": (now - timedelta(seconds=age)).isoformat(), "valid": valid}, now)


def finding(severity):
    return {"vulnerability": {"id": "CVE-2026-0001", "severity": severity}, "artifact": {"name": "synthetic"}}


def test_threshold_findings_and_ignored_matches_are_never_accepted():
    assert scan.summary({"matches": [], "ignoredMatches": []}, 0)["accepted"] is True
    for severity in ("High", "Critical"):
        value = {"matches": [finding(severity)], "ignoredMatches": []}
        assert scan.summary(value, 2)["accepted"] is False
        with pytest.raises(ValueError):
            scan.summary(value, 0)
    assert scan.summary({"matches": [], "ignoredMatches": [finding("Critical")]}, 0)["accepted"] is False
    for value, exitcode in (({}, 0), ({"matches": []}, 1), ({"matches": []}, 2)):
        with pytest.raises(ValueError):
            scan.summary(value, exitcode)


def test_actual_probe_version_parser_accepts_openssl_versions_without_guessing():
    tree = ast.parse(scan.NATIVE_PROBE)
    call = next(node for node in ast.walk(tree) if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute) and node.func.attr == "fullmatch")
    pattern = ast.literal_eval(call.args[0])
    assert re.fullmatch(pattern, "OpenSSL 4.0.3 3 Oct 2026").group(1) == "4.0.3"
    assert re.fullmatch(pattern, "LibreSSL 4.0.3") is None
    compile(scan.NATIVE_PROBE, "native-SCA-runtime-witness", "exec")


@pytest.mark.parametrize("profile", [None, 1, True, "", "WEB", " backup", "root", "10001:0"])
def test_unknown_image_profiles_cannot_choose_a_runtime_identity(profile):
    with pytest.raises(ValueError, match="Unreviewed"):
        scan.profile_user(profile)


def test_closed_image_profiles_retain_web_identity_and_separate_backup_identity():
    assert scan.profile_user("web") == "999:999"
    assert scan.profile_user("backup") == "10001:10001"
    for profile in ("web", "backup"):
        assert all(int(value) > 0 for value in scan.profile_user(profile).split(":"))


@pytest.fixture
def backup_inventory():
    repository = Path(__file__).resolve().parents[1]
    contract_raw = (repository / "deploy/backup-service.contract.json").read_bytes()
    contract = json.loads(contract_raw)
    sources = {name: (repository / name).read_bytes() for name in scan.BACKUP_SOURCES}
    measured = {"python_distributions": contract["build"]["runtime_distributions"],
        "source_sha256": {name: hashlib.sha256(raw).hexdigest() for name, raw in sources.items()},
        "pg_clients": {name: {"version": "18.6", "sha256": "a" * 64} for name in ("pg_dump", "pg_restore")},
        "libpq_version": 180006, "contract_sha256": hashlib.sha256(contract_raw).hexdigest(),
        "missing_arguments_rejected": True}
    return {"backup_runtime": measured}, contract_raw, sources


def test_backup_inventory_authenticates_each_original_source_and_tool_contract(backup_inventory):
    native, contract_raw, sources = backup_inventory
    assert scan.validate_backup_runtime(native, contract_raw, sources)
    for name in sources:
        changed = dict(sources, **{name: sources[name] + b"# changed"})
        with pytest.raises(ValueError):
            scan.validate_backup_runtime(native, contract_raw, changed)


@pytest.mark.parametrize("fault", ["missing-file", "extra-file", "dist-version", "extra-dist", "contract", "libpq", "bool", "client-version", "client-hash", "missing-client", "extra-client-field", "argument-result", "extra-field"])
def test_backup_runtime_drift_cannot_enter_image_acceptance(backup_inventory, fault):
    native, contract_raw, sources = backup_inventory
    native = deepcopy(native)
    value = native["backup_runtime"]
    if fault == "missing-file":
        value["source_sha256"].pop(next(iter(value["source_sha256"])))
    elif fault == "extra-file":
        value["source_sha256"]["private.py"] = "a" * 64
    elif fault == "dist-version":
        value["python_distributions"]["boto3"] = "0"
    elif fault == "extra-dist":
        value["python_distributions"]["pip"] = "26.2.1"
    elif fault == "contract":
        value["contract_sha256"] = "0" * 64
    elif fault in {"libpq", "bool"}:
        value["libpq_version"] = True if fault == "bool" else 170011
    elif fault == "client-version":
        value["pg_clients"]["pg_dump"]["version"] = "17.11"
    elif fault == "client-hash":
        value["pg_clients"]["pg_restore"]["sha256"] = "not-a-digest"
    elif fault == "missing-client":
        value["pg_clients"].pop("pg_restore")
    elif fault == "extra-client-field":
        value["pg_clients"]["pg_restore"]["secret"] = "private"
    elif fault == "argument-result":
        value["missing_arguments_rejected"] = 1
    else:
        value["secret"] = "private"
    with pytest.raises(ValueError):
        scan.validate_backup_runtime(native, contract_raw, sources)

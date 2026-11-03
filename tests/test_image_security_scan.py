"""Fail closed on stale databases, incomplete scans and threshold mismatches."""
import ast
from datetime import datetime, timedelta, timezone
import re

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

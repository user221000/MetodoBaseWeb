"""Current V7 exact one-location union and actual fail-closed loader boundaries."""
import ast
import hashlib
import io
import json
import subprocess
import zipfile
from functools import cache
from pathlib import Path

import pytest

from scripts import reviewed_scan_locations as review

ROOT = Path(__file__).resolve().parents[1]
BASE = "45eba8f1d50efebd7106106f8aa20bfda3c7b440"
SCAN = "b0fa556346a0097cd8a4372d586184a100758737"
V6 = "scripts/data/reviewed_scan_locations_v6.zip"
V7 = "scripts/data/reviewed_scan_locations_v7.zip"
OLD_SHA = "6b10c621dca9e76b3bee4867caae5a33b70f2e81f3700807ebb9f9fb7731f092"
NEW_SHA = "907501744833ca5c1ec1e8acaeff58659311f93ab56d7d8b184814dcf14ccb06"
PROPOSAL = "docs/implementation/20261018-evolution/evidence/security-r05-last1-independent-20261020/finite-proposal.zip"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


@cache
def git(revision, name):
    return subprocess.check_output(["git", "--no-replace-objects", "show", revision + ":" + name], cwd=ROOT)


def data(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        assert archive.namelist() == ["reviewed-locations.json"]
        return json.loads(archive.read("reviewed-locations.json"))


@cache
def proposal():
    raw = (ROOT / PROPOSAL).read_bytes()
    assert sha(raw) == "86d060f518ba6daec844b3273d9a2650d75b70571a2d6b59d13fd185485884aa"
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        assert archive.namelist() == ["proposal.json"]
        return json.loads(archive.read("proposal.json"))


def test_exact_one_record_union_retains_all903_records_and57261_pins():
    old_raw, new_raw = (ROOT / V6).read_bytes(), (ROOT / V7).read_bytes()
    assert sha(old_raw) == OLD_SHA and sha(new_raw) == NEW_SHA
    old, new = data(old_raw), data(new_raw)
    canonical = lambda row: json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    assert len(old["files"]) == 903 and len(new["files"]) == 904
    assert list(map(canonical, new["files"][:903])) == list(map(canonical, old["files"]))
    assert new["files"][903:] == proposal()["files"] and len(proposal()["files"]) == 1
    assert len({row["path"] for row in new["files"]}) == 904
    assert sum(len(line["rules"]) for row in old["files"] for line in row["lines"]) == 57261
    assert sum(len(line["rules"]) for row in new["files"] for line in row["lines"]) == 57262
    assert {k: v for k, v in old.items() if k != "files"} == {k: v for k, v in new.items() if k != "files"}
    assert review._REVIEW_DATA_PATH == V7 and review._REVIEW_DATA_DIGEST == NEW_SHA
    row = proposal()["witnesses"][0]
    record = new["files"][-1]
    assert record == {"path": row["file"], "source_digest": row["file_sha256"], "scanner_digest": row["file_sha256"],
        "lines": [{"number": row["line"], "digest": row["physical_line_sha256"], "rules": [row["rule"]]}]}
    assert len(proposal()["witnesses"]) == 1 and row["rule"] == "generic-api-key"


def test_only_three_loader_literals_change_with_exact_inverse_and_old_data_config_tests_unchanged():
    name = "scripts/reviewed_scan_locations.py"
    current = git("HEAD", name)
    inverse = current
    for before, after in [(V7, V6), (NEW_SHA, OLD_SHA), ("registry v7", "registry v6")]:
        assert inverse.count(before.encode()) == 1
        inverse = inverse.replace(before.encode(), after.encode())
    assert inverse == git(BASE, name)
    assert ast.dump(ast.parse((ROOT / name).read_bytes())) == ast.dump(ast.parse(current))
    for name in [".gitleaks.toml", "scripts/scan_secrets.py", "tests/test_secret_scan_finite_v6.py",
                 "tests/test_security_r05_v5_current_peer.py", *[f"scripts/data/reviewed_scan_locations_v{i}.zip" for i in range(1, 7)]]:
        assert git("HEAD", name) == git(BASE, name)


def snapshot(tmp_path):
    row = proposal()["witnesses"][0]
    raw = git(SCAN, row["file"])
    assert sha(raw) == row["file_sha256"]
    hashes = {}
    for name, payload in [(row["file"], raw), (".gitleaks.toml", (ROOT / ".gitleaks.toml").read_bytes()),
                          (V7, (ROOT / V7).read_bytes())]:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        hashes[name] = sha(payload)
    return row, hashes


def finding(row):
    return {"StartLine": row["line"], "EndLine": row["line"], "RuleID": row["rule"],
        "File": object(), "Match": {"untrusted": True}, "Secret": object(), "Line": False}


def test_actual_v7_loader_accepts_only_the_named_physical_location_ignoring_untrusted_payload(tmp_path):
    row, hashes = snapshot(tmp_path)
    assert review.load_reviewed_locations(tmp_path, hashes, "8.30.1").classify(finding(row), row["file"]) == {
        "file": row["file"], "line": row["line"], "rule": row["rule"], "file_sha256": row["file_sha256"],
        "physical_line_sha256": row["physical_line_sha256"],
        "reason": "finite independently reviewed non-credential evidence; registry v7"}


@pytest.mark.parametrize("fault", ["neighbor-byte", "physical-line", "wrong-rule", "wrong-path", "inventory", "boolean-line", "multiline", "CRLF-added"])
def test_added_location_source_line_rule_and_inventory_boundaries_fail_closed(tmp_path, fault):
    row, hashes = snapshot(tmp_path)
    item, name = finding(row), row["file"]
    path = tmp_path / name
    if fault == "neighbor-byte":
        path.write_bytes(path.read_bytes() + b" ")
    elif fault == "physical-line":
        lines = path.read_bytes().split(b"\n")
        lines[row["line"] - 1] += b" "
        path.write_bytes(b"\n".join(lines))
    elif fault == "wrong-rule":
        item["RuleID"] = "new-unreviewed-rule"
    elif fault == "wrong-path":
        name += ".unreviewed"
    elif fault == "inventory":
        hashes[name] = "0" * 64
    elif fault == "boolean-line":
        item.update(StartLine=True, EndLine=True)
    elif fault == "multiline":
        item["EndLine"] += 1
    else:
        raw = path.read_bytes()
        assert b"\r" not in raw
        path.write_bytes(raw.replace(b"\n", b"\r\n"))
        hashes[name] = sha(path.read_bytes())
    assert review.load_reviewed_locations(tmp_path, hashes, "8.30.1").classify(item, name) is None


@pytest.mark.parametrize("fault", ["archive-byte", "config-byte", "version", "repacked-identical-payload"])
def test_active_zip_configuration_and_tool_version_are_exact(tmp_path, fault):
    snapshot(tmp_path)
    hashes = {row["path"]: row["source_digest"] for row in proposal()["files"]}
    hashes[".gitleaks.toml"] = sha((tmp_path / ".gitleaks.toml").read_bytes())
    version = "8.30.1"
    if fault == "archive-byte":
        (tmp_path / V7).write_bytes((tmp_path / V7).read_bytes() + b" ")
    elif fault == "config-byte":
        (tmp_path / ".gitleaks.toml").write_bytes(b"changed=true\n")
    elif fault == "version":
        version = "8.30.2"
    else:
        with zipfile.ZipFile(tmp_path / V7, "w", zipfile.ZIP_STORED) as archive:
            archive.writestr("reviewed-locations.json", json.dumps(data((ROOT / V7).read_bytes())))
    with pytest.raises(RuntimeError):
        review.load_reviewed_locations(tmp_path, hashes, version)

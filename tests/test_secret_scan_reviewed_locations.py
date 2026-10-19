"""Adversarial boundaries of the finite, anchored reviewed-location registry."""
import codecs
import hashlib
import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from scripts import reviewed_scan_locations as review


def _sha(content):
    return hashlib.sha256(content).hexdigest()


def _zip(raw, *, member="reviewed-locations.json", second=False):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(member, raw)
        if second:
            archive.writestr("second.json", b"{}")
    return buffer.getvalue()


def _setup(tmp_path, monkeypatch, *, original=None, copied=None, raw=None, change=None):
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    config = b"[extend]\nuseDefault=true\n"
    original = b"public_digest = 'reviewed fixture only'\r\n" if original is None else original
    copied = original if copied is None else copied
    (snapshot / ".gitleaks.toml").write_bytes(config)
    (snapshot / "source.txt").write_bytes(copied)
    digest = _sha(copied.split(b"\n")[0])
    data = {"schema": 1, "version": "8.30.1", "config_digest": _sha(config), "files": [
        {"path": "source.txt", "source_digest": _sha(original), "scanner_digest": _sha(copied),
         "lines": [{"number": 1, "digest": digest, "rules": ["synthetic-rule"]}]}]}
    if change:
        change(data)
    payload = _zip(raw if raw is not None else json.dumps(data).encode())
    destination = snapshot / review._REVIEW_DATA_PATH
    destination.parent.mkdir(parents=True)
    destination.write_bytes(payload)
    monkeypatch.setattr(review, "_REVIEW_DATA_DIGEST", _sha(payload))
    source_hashes = {"source.txt": _sha(original), ".gitleaks.toml": _sha(config)}
    finding = {"StartLine": 1, "EndLine": 1, "RuleID": "synthetic-rule",
        "Match": "UNTRUSTED_VALUE", "Secret": "UNTRUSTED_VALUE", "Line": "UNTRUSTED_VALUE"}
    return snapshot, source_hashes, finding, destination, data


def test_exact_raw_file_and_physical_line_are_required(tmp_path, monkeypatch):
    snapshot, hashes, finding, _, _ = _setup(tmp_path, monkeypatch)
    registry = review.load_reviewed_locations(snapshot, hashes, "8.30.1")
    result = registry.classify(finding, "source.txt")
    assert result["physical_line_sha256"] == _sha((snapshot / "source.txt").read_bytes().split(b"\n")[0])
    assert result["file_sha256"] == hashes["source.txt"]
    assert "UNTRUSTED_VALUE" not in json.dumps(result)
    assert not {"Match", "Secret", "Line"} & result.keys()


@pytest.mark.parametrize("change", ["source", "snapshot", "line", "path", "rule", "start", "end",
    "boolean_start", "boolean_end", "multiline", "cr_removed", "bom_added", "new_adjacent_credential"])
def test_every_unreviewed_change_remains_blocking(tmp_path, monkeypatch, change):
    snapshot, hashes, finding, _, _ = _setup(tmp_path, monkeypatch)
    target = snapshot / "source.txt"
    name = "source.txt"
    if change == "source":
        hashes[name] = _sha(b"different original")
    elif change == "snapshot":
        target.write_bytes(target.read_bytes() + b" ")
    elif change == "line":
        target.write_bytes(b"\n" + target.read_bytes())
    elif change == "path":
        name = "copy.txt"
        (snapshot / name).write_bytes(target.read_bytes())
        hashes[name] = hashes["source.txt"]
    elif change == "rule":
        finding["RuleID"] = "different-rule"
    elif change in {"start", "end"}:
        finding["StartLine" if change == "start" else "EndLine"] = 2
    elif change in {"boolean_start", "boolean_end"}:
        finding["StartLine" if change == "boolean_start" else "EndLine"] = True
    elif change == "multiline":
        finding["EndLine"] = 2
    elif change == "cr_removed":
        target.write_bytes(target.read_bytes().replace(b"\r\n", b"\n"))
        hashes[name] = _sha(target.read_bytes())
    elif change == "bom_added":
        target.write_bytes(codecs.BOM_UTF8 + target.read_bytes())
        hashes[name] = _sha(target.read_bytes())
    else:
        target.write_bytes(target.read_bytes() + b"api_key = 'new synthetic unreviewed credential'\n")
        hashes[name] = _sha(target.read_bytes())
    registry = review.load_reviewed_locations(snapshot, hashes, "8.30.1")
    assert registry.classify(finding, name) is None


def test_original_utf16_and_exact_transcoded_snapshot_both_must_match(tmp_path, monkeypatch):
    text = "public fixture á\r\n"
    original = codecs.BOM_UTF16_LE + text.encode("utf-16-le")
    snapshot, hashes, finding, _, _ = _setup(tmp_path, monkeypatch,
        original=original, copied=text.encode("utf-8"))
    registry = review.load_reviewed_locations(snapshot, hashes, "8.30.1")
    assert registry.classify(finding, "source.txt") is not None
    hashes["source.txt"] = _sha(text.encode("utf-8"))
    assert registry.classify(finding, "source.txt") is None


def test_absent_data_cannot_classify_a_finding(tmp_path):
    registry = review.load_reviewed_locations(tmp_path, {}, "8.30.1")
    assert registry.classify({"StartLine": 1, "EndLine": 1, "RuleID": "synthetic-rule"}, "source.txt") is None


@pytest.mark.parametrize("change", [
    "anchor", "config_source", "config_snapshot", "version", "member", "second_member",
    "invalid_zip", "duplicate_json_key", "invalid_json", "nan", "nested_json",
])
def test_present_invalid_data_aborts_without_exposing_payload(tmp_path, monkeypatch, change):
    snapshot, hashes, _, destination, data = _setup(tmp_path, monkeypatch)
    version = "8.30.1"
    if change == "anchor":
        destination.write_bytes(destination.read_bytes() + b"changed")
    elif change == "config_source":
        hashes[".gitleaks.toml"] = _sha(b"new config")
    elif change == "config_snapshot":
        (snapshot / ".gitleaks.toml").write_bytes(b"new config")
    elif change == "version":
        version = "8.30.2"
    else:
        raw = json.dumps(data).encode()
        if change == "duplicate_json_key":
            raw = b'{"UNTRUSTED_VALUE":1,"UNTRUSTED_VALUE":2}'
        elif change == "invalid_json":
            raw = b'{"UNTRUSTED_VALUE":'
        elif change == "nan":
            raw = b'{"UNTRUSTED_VALUE":NaN}'
        elif change == "nested_json":
            raw = b"[" * 2000 + b"0" + b"]" * 2000
        payload = (b"UNTRUSTED_VALUE" if change == "invalid_zip" else _zip(raw,
            member="wrong.json" if change == "member" else "reviewed-locations.json",
            second=change == "second_member"))
        destination.write_bytes(payload)
        monkeypatch.setattr(review, "_REVIEW_DATA_DIGEST", _sha(payload))
    with pytest.raises(RuntimeError, match="registry is invalid; output withheld") as failure:
        review.load_reviewed_locations(snapshot, hashes, version)
    assert "UNTRUSTED_VALUE" not in str(failure.value)
    assert failure.value.__suppress_context__


def _change(data, name):
    row = data["files"][0]
    line = row["lines"][0]
    if name == "schema_bool":
        data["schema"] = True
    elif name == "extra":
        data["unexpected"] = True
    elif name == "empty_rules":
        line["rules"] = []
    elif name == "duplicate_rule":
        line["rules"].append(line["rules"][0])
    elif name == "duplicate_file":
        data["files"].append(row)
    elif name == "line_bool":
        line["number"] = True
    elif name == "line_zero":
        line["number"] = 0
    elif name == "line_digest":
        line["digest"] = "invalid"
    elif name == "rule_type":
        line["rules"] = [False]
    elif name == "rule_text":
        line["rules"] = ["invalid rule"]
    elif name == "source_digest":
        row["source_digest"] = "invalid"
    elif name == "scanner_digest":
        row["scanner_digest"] = "invalid"
    else:
        row["path"] = {"parent": "../outside", "backslash": "a\\b", "absolute": "/outside",
            "drive": "C:/outside", "empty_part": "a//b", "dot": "./source.txt", "control": "a\nb"}[name]


@pytest.mark.parametrize("name", ["schema_bool", "extra", "empty_rules", "duplicate_rule", "duplicate_file",
    "line_bool", "line_zero", "line_digest", "rule_type", "rule_text", "source_digest", "scanner_digest",
    "parent", "backslash", "absolute", "drive", "empty_part", "dot", "control"])
def test_strict_schema_and_canonical_paths_fail_closed(tmp_path, monkeypatch, name):
    snapshot, hashes, _, _, _ = _setup(tmp_path, monkeypatch, change=lambda data: _change(data, name))
    with pytest.raises(RuntimeError, match="registry is invalid; output withheld"):
        review.load_reviewed_locations(snapshot, hashes, "8.30.1")


@pytest.mark.parametrize("case,expected", [("classified", 0), ("changed_byte", 1), ("different_rule", 1)])
def test_wrapper_preserves_raw_exit_and_reports_effective_exit(tmp_path, monkeypatch, case, expected):
    from scripts import scan_secrets as scanner

    root, _, item, _, _ = _setup(tmp_path, monkeypatch)
    if case == "changed_byte":
        source = root / "source.txt"
        source.write_bytes(source.read_bytes() + b" ")
    elif case == "different_rule":
        item["RuleID"] = "different-rule"
    tool = tmp_path / "gitleaks.exe"
    tool.write_bytes(b"synthetic boundary only; never executed")
    report = tmp_path / "result.json"
    monkeypatch.setattr(scanner, "ROOT", root)
    monkeypatch.setattr(sys, "argv", ["scan_secrets.py", "--gitleaks", str(tool), "--report", str(report)])

    def run(command, **options):
        if command[0] == "git":
            names = [".gitleaks.toml", "source.txt", review._REVIEW_DATA_PATH]
            return subprocess.CompletedProcess(command, 0, stdout="\0".join(names).encode() + b"\0")
        if command[1] == "version":
            return subprocess.CompletedProcess(command, 0, stdout="8.30.1\n")
        snapshot = Path(command[2])
        raw = Path(command[command.index("--report-path") + 1])
        raw.write_text(json.dumps([dict(item, File=str(snapshot / "source.txt"))]), encoding="utf-8")
        return subprocess.CompletedProcess(command, 1)

    monkeypatch.setattr(scanner.subprocess, "run", run)
    assert scanner.main() == expected
    result = json.loads(report.read_bytes())
    assert result["exit_code"] == 1
    assert result["effective_exit_code"] == expected
    assert result["raw_finding_count"] == 1
    assert result["classified_finding_count"] == (1 if expected == 0 else 0)
    assert result["remaining_finding_count"] == expected
    assert "UNTRUSTED_VALUE" not in report.read_text(encoding="utf-8")

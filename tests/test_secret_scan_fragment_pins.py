"""Real immutable manifests and adversarial boundaries of the finite classifier."""
import codecs
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts import scan_secrets as scanner
from tests.ci_web37.serial_security_transport import historical_source


PINS = tuple(scanner._FRAGMENT_FINGERPRINT_PINS)
ROOT = Path(__file__).resolve().parents[1]


def _copy(tmp_path, name, *, crlf=False):
    original = historical_source(ROOT, name).replace(b"\r\n", b"\n")
    content = original.replace(b"\n", b"\r\n") if crlf else original
    target = tmp_path / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    item = {"StartLine": 3081, "EndLine": 3081, "RuleID": "generic-api-key",
            "Match": "untrusted truncated match", "Secret": "untrusted truncated secret",
            "Line": "untrusted fragment"}
    return item, target, {name: hashlib.sha256(content).hexdigest()}


@pytest.mark.parametrize("name", PINS)
@pytest.mark.parametrize("crlf", [False, True])
def test_only_exact_reviewed_lf_or_crlf_manifest_is_classified(tmp_path, name, crlf):
    item, _, hashes = _copy(tmp_path, name, crlf=crlf)
    result = scanner._classify_fragment_fingerprint(item, name, tmp_path, hashes)
    assert result is not None
    assert result["file_sha256"] == hashes[name]
    assert result["physical_line_sha256"] == scanner._FRAGMENT_FINGERPRINT_PINS[name][1]
    assert not {"Match", "Secret", "Line"} & result.keys()


@pytest.mark.parametrize("name", PINS)
@pytest.mark.parametrize("mutation", [
    "hash_suffix", "field_prefix", "adjacent_key", "line_position", "utf8_bom",
    "utf16", "snapshot_only", "path", "rule", "start", "end", "bool_start", "bool_end",
])
def test_every_changed_boundary_remains_blocking(tmp_path, name, mutation):
    item, target, hashes = _copy(tmp_path, name)
    original = target.read_bytes()
    lines = original.split(b"\n")
    if mutation == "hash_suffix":
        # Mutate beyond the partial scanner Match/Secret, retaining its length.
        line = lines[3080]
        index = line.rfind(b'"') - 1
        lines[3080] = line[:index] + (b"0" if line[index:index + 1] != b"0" else b"1") + line[index + 1:]
        target.write_bytes(b"\n".join(lines))
    elif mutation == "field_prefix":
        lines[3080] = lines[3080].replace(b"tests/", b"xests/", 1)
        assert lines[3080] != original.split(b"\n")[3080]
        target.write_bytes(b"\n".join(lines))
    elif mutation == "adjacent_key":
        lines.insert(3081, b'    "api_key": "synthetic_new_adjacent_credential_123456789",')
        target.write_bytes(b"\n".join(lines))
    elif mutation == "line_position":
        target.write_bytes(b"\n" + original)
    elif mutation == "utf8_bom":
        target.write_bytes(codecs.BOM_UTF8 + original)
    elif mutation == "utf16":
        target.write_bytes(codecs.BOM_UTF16_LE + original.decode("utf-8").encode("utf-16-le"))
    elif mutation == "snapshot_only":
        target.write_bytes(original + b" ")
    elif mutation == "path":
        name = name.replace("desktop-real-build", "copied-build")
    elif mutation == "rule":
        item["RuleID"] = "sentry-access-token"
    elif mutation in {"start", "end"}:
        item["StartLine" if mutation == "start" else "EndLine"] = 1391
    elif mutation in {"bool_start", "bool_end"}:
        item["StartLine" if mutation == "bool_start" else "EndLine"] = True
    if mutation != "snapshot_only":
        hashes = {name: hashlib.sha256(target.read_bytes()).hexdigest()}
    assert scanner._classify_fragment_fingerprint(item, name, tmp_path, hashes) is None


@pytest.mark.parametrize("name", PINS)
def test_other_finding_in_same_file_is_not_classified(tmp_path, name):
    item, _, hashes = _copy(tmp_path, name)
    item["StartLine"] = item["EndLine"] = 1391
    assert scanner._classify_fragment_fingerprint(item, name, tmp_path, hashes) is None


@pytest.mark.parametrize("value", ["../outside.json", "nested/../../outside.json", "", None])
def test_noncanonical_or_outside_scanner_path_is_rejected(tmp_path, value):
    with pytest.raises(ValueError):
        scanner._finding_name(value, tmp_path)


@pytest.mark.parametrize("case,expected", [
    ("classified", 0), ("other_finding", 1), ("source_changed", 2),
    ("snapshot_changed", 1), ("empty_exit1", None), ("findings_exit0", None),
])
def test_wrapper_classification_counts_and_failure_status(tmp_path, monkeypatch, case, expected):
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    name = PINS[0]
    _, source, _ = _copy(candidate, name)
    (candidate / ".gitleaks.toml").write_text("[extend]\nuseDefault=true\n", encoding="utf-8")
    tool = tmp_path / "gitleaks.exe"
    tool.write_bytes(b"synthetic boundary only; never executed")
    report = tmp_path / "report.json"
    files = [name, ".gitleaks.toml"]
    monkeypatch.setattr(scanner, "ROOT", candidate)
    monkeypatch.setattr(sys, "argv", ["scan_secrets.py", "--gitleaks", str(tool), "--report", str(report)])

    actual_boundary_run = subprocess.run

    def run(command, **options):
        if command[0] in {"whoami", "icacls"}:
            return actual_boundary_run(command, **options)
        if command[0] == "git":
            return subprocess.CompletedProcess(command, 0, stdout="\0".join(files).encode() + b"\0")
        if command[1] == "version":
            return subprocess.CompletedProcess(command, 0, stdout="8.30.1\n")
        snapshot = Path(command[2])
        item = {"File": str(snapshot / name), "StartLine": 3081, "EndLine": 3081,
                "RuleID": "generic-api-key", "Secret": "must never be emitted"}
        findings = [] if case == "empty_exit1" else [item]
        if case == "other_finding":
            findings.append(dict(item, StartLine=1391, EndLine=1391))
        if case == "source_changed":
            source.write_bytes(source.read_bytes() + b" ")
        if case == "snapshot_changed":
            copied = snapshot / name
            copied.write_bytes(copied.read_bytes() + b" ")
        Path(command[command.index("--report-path") + 1]).write_text(json.dumps(findings), encoding="utf-8")
        count = len(findings)
        final = f"WRN leaks found: {count}" if count else "INF no leaks found"
        complete = "6:47PM INF scanned ~37 bytes (37 bytes) in 1ms\n6:47PM " + final + "\n"
        return subprocess.CompletedProcess(command, 0 if case == "findings_exit0" else 1,
                                           stdout=b"", stderr=complete)

    monkeypatch.setattr(scanner.subprocess, "run", run)
    if expected is None:
        with pytest.raises(RuntimeError, match="inconsistent findings; output withheld"):
            scanner.main()
        assert not report.exists()
        return
    assert scanner.main() == expected
    result = json.loads(report.read_text(encoding="utf-8"))
    assert result["raw_finding_count"] == (2 if case == "other_finding" else 1)
    assert result["classified_finding_count"] == (0 if case == "snapshot_changed" else 1)
    assert result["remaining_finding_count"] == (1 if case in {"snapshot_changed", "other_finding"} else 0)
    assert result["source_stable"] == (case != "source_changed")
    assert "must never be emitted" not in report.read_text(encoding="utf-8")


@pytest.mark.parametrize("payload", [{}, False, 0, "", None, "unexpected", {"unexpected": True}, 1])
def test_malformed_scanner_json_cannot_become_a_successful_empty_list(tmp_path, monkeypatch, payload):
    from tests.ci_web37.serial_security_transport import completed_safety_scenario as _scenario

    boundary, report, _ = _scenario(tmp_path, monkeypatch)
    original_run = boundary.subprocess.run

    def run(command, **options):
        result = original_run(command, **options)
        if len(command) > 1 and command[1] == "dir":
            raw = Path(command[command.index("--report-path") + 1])
            raw.write_text(json.dumps(payload), encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, stdout=result.stdout, stderr=result.stderr)
        return result

    monkeypatch.setattr(boundary.subprocess, "run", run)
    with pytest.raises(RuntimeError, match="inconsistent findings; output withheld"):
        boundary.main()
    assert not report.exists()

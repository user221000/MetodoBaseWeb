"""A list/report and exit1 never establish complete Gitleaks execution."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts import reviewed_scan_locations as reviewed
from scripts import scan_secrets as scanner

CANARY = "SYNTHETIC_PRIVATE_DIAGNOSTIC_DO_NOT_PUBLISH"
FULL = "6:47PM INF scanned ~37 bytes (37 bytes) in 1ms\n"


def scenario(tmp_path, monkeypatch, *, stderr, finding=True, classified=True, timeout=False):
    root = tmp_path / "candidate"
    root.mkdir()
    source = b"safe_metadata = 1\n"
    (root / "source.py").write_bytes(source)
    (root / ".gitleaks.toml").write_bytes(b"[extend]\nuseDefault = true\n")
    tool = tmp_path / "gitleaks.exe"
    tool.write_bytes(b"inert mock executable")
    report = tmp_path / "sanitized.json"
    monkeypatch.setattr(scanner, "ROOT", root)
    monkeypatch.setattr(sys, "argv", ["scan_secrets.py", "--gitleaks", str(tool), "--report", str(report)])
    mapping = {"source.py": {"source_digest": hashlib.sha256(source).hexdigest(),
                "scanner_digest": hashlib.sha256(source).hexdigest(),
                "lines": {(1, "generic-api-key"): hashlib.sha256(source.splitlines()[0]).hexdigest()}}} if classified else {}
    monkeypatch.setattr(scanner, "load_reviewed_locations", lambda snapshot, hashes, version:
                        reviewed.ReviewedLocations(snapshot, hashes, mapping))
    private = tmp_path / "private-evidence"
    private.mkdir()
    monkeypatch.setattr(scanner, "_private_evidence", lambda requested: private, raising=False)
    seen = {}

    def run(command, **options):
        if command[0] == "git":
            return subprocess.CompletedProcess(command, 0, stdout=b".gitleaks.toml\0source.py\0")
        if command[1] == "version":
            return subprocess.CompletedProcess(command, 0, stdout="8.30.1\n")
        seen.update(command=command, options=options)
        if timeout:
            raise subprocess.TimeoutExpired(command, 600, output=CANARY.encode(), stderr=CANARY.encode())
        snapshot = Path(command[2])
        raw = [{"File": str(snapshot / "source.py"), "StartLine": 1, "EndLine": 1,
                "RuleID": "generic-api-key", "Secret": CANARY, "Match": CANARY,
                "Fingerprint": "source.py:generic-api-key:1"}] if finding else []
        Path(command[command.index("--report-path") + 1]).write_text(json.dumps(raw), encoding="utf8")
        return subprocess.CompletedProcess(command, 1 if finding else 0, stdout=b"", stderr=stderr.encode())

    monkeypatch.setattr(scanner.subprocess, "run", run)
    return report, seen


@pytest.mark.parametrize("stderr", [
    "6:47PM ERR failed scan error=\"" + CANARY + "\"\n6:47PM WRN scanned ~37 bytes (37 bytes)\n6:47PM WRN partial scan completed in 1s\n6:47PM WRN 1 leaks found in partial scan\n",
    "",
    FULL,
    FULL + "6:47PM WRN leaks found: 2\n",
    FULL + "6:47PM WRN leaks found: 1\n6:47PM ERR " + CANARY + "\n",
    "6:47PM WRN skipping file: permission denied\n" + FULL + "6:47PM WRN leaks found: 1\n",
    FULL + FULL + "6:47PM WRN leaks found: 1\n",
    FULL + "6:47PM WRN unknown scanner warning\n6:47PM WRN leaks found: 1\n",
    "6:47PM INF scanned ~0 bytes (0) in 1ms\n6:47PM WRN leaks found: 1\n",
])
def test_partial_missing_inconsistent_or_warned_scan_never_becomes_PASS(tmp_path, monkeypatch, capsys, stderr):
    report, _ = scenario(tmp_path, monkeypatch, stderr=stderr)
    with pytest.raises(RuntimeError, match="output withheld") as failure:
        scanner.main()
    captured = capsys.readouterr()
    assert CANARY not in str(failure.value) + captured.out + captured.err
    assert not report.exists()


def test_complete_classified_scan_is_accepted_and_uses_only_external_timeout(tmp_path, monkeypatch, capsys):
    report, seen = scenario(tmp_path, monkeypatch, stderr=FULL + "6:47PM WRN leaks found: 1\n")
    assert scanner.main() == 0
    assert "--timeout=0" in seen["command"] and seen["options"]["timeout"] == 600
    assert "--log-level=info" in seen["command"] and "--redact=100" in seen["command"]
    result = json.loads(report.read_bytes())
    assert result["raw_finding_count"] == result["classified_finding_count"] == 1
    assert result["scan_complete"] is True
    assert CANARY not in report.read_text(encoding="utf8") + capsys.readouterr().out


def test_complete_zero_findings_is_distinct_from_incomplete_zero_findings(tmp_path, monkeypatch):
    report, _ = scenario(tmp_path, monkeypatch, stderr=FULL + "6:47PM INF no leaks found\n", finding=False)
    assert scanner.main() == 0
    assert json.loads(report.read_bytes())["scan_complete"] is True


def test_complete_unclassified_finding_still_blocks(tmp_path, monkeypatch):
    report, _ = scenario(tmp_path, monkeypatch, stderr=FULL + "6:47PM WRN leaks found: 1\n", classified=False)
    assert scanner.main() == 1
    assert json.loads(report.read_bytes())["remaining_finding_count"] == 1


def test_external_timeout_is_a_private_refusal_without_publishing_payload(tmp_path, monkeypatch, capsys):
    report, _ = scenario(tmp_path, monkeypatch, stderr="", timeout=True)
    with pytest.raises(RuntimeError, match="output withheld") as failure:
        scanner.main()
    captured = capsys.readouterr()
    assert CANARY not in str(failure.value) + captured.out + captured.err
    assert not report.exists()

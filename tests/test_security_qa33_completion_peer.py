"""Independent finite QA33 boundaries; no scanner binary or service executes."""
import csv
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import scan_secrets as scanner

PRIVATE_MARKER = "INERT_PEER_DIAGNOSTIC_NOT_A_PROVIDER_VALUE"
SUMMARY = "7:13PM INF scanned ~67 bytes (67 bytes) in 46.8ms\n"


def exercise(tmp_path, monkeypatch, *, count=1, returncode=None, summary=None,
             stdout=b"", timeout=False, malformed=False, classify=False, drift=False):
    """Mock only Git/scanner I/O; the real Windows private boundary executes."""
    root = tmp_path / "source"
    root.mkdir()
    (root / ".gitleaks.toml").write_bytes(b"[extend]\nuseDefault=true\n")
    (root / "sample.txt").write_bytes(b"inert fixture\n")
    tool = tmp_path / "never-executed.exe"
    tool.write_bytes(b"inert fake process identity")
    public = tmp_path / "sanitized.json"
    private = tmp_path / "private"
    monkeypatch.setattr(scanner, "ROOT", root)
    monkeypatch.setattr(sys, "argv", ["scan_secrets.py", "--gitleaks", str(tool),
        "--report", str(public), "--private-evidence", str(private)])

    class Reviewed:
        def classify(self, item, name):
            return {"file": name, "line": 1, "reason": "finite synthetic peer control"} if classify else None

    monkeypatch.setattr(scanner, "load_reviewed_locations", lambda *args: Reviewed())
    actual_run = subprocess.run
    observation = {"native_scanner_calls": 0, "fake_calls": 0}

    def run(command, **options):
        if command[0] in {"whoami", "icacls"}:
            # Real pre-payload privacy setup/readback, not a test-only ACL answer.
            return actual_run(command, **options)
        if command[0] == "git":
            names = b".gitleaks.toml\0sample.txt\0"
            if (root / "added.txt").exists():
                names += b"added.txt\0"
            return subprocess.CompletedProcess(command, 0, stdout=names)
        if command[0] != str(tool.resolve()):
            raise AssertionError("An unapproved process was requested")
        if command[1] == "version":
            return subprocess.CompletedProcess(command, 0, stdout="8.30.1\n")
        observation["fake_calls"] += 1
        assert command[1] == "dir" and options["timeout"] == 600
        assert "--timeout=0" in command and "--redact=100" in command
        assert "--log-level=info" in command and "--no-color" in command
        sid = None
        if os.name == "nt":
            sid = next(csv.reader(io.StringIO(actual_run(
                ["whoami", "/user", "/fo", "csv", "/nh"], capture_output=True,
                check=True, text=True).stdout)))[1]
        scanner._verify_private_boundary(private, sid)
        assert (private / "boundary-before-payload.private.txt").is_file() == (os.name == "nt")
        assert not (private / "scan.stdout.private.log").exists()
        snapshot = Path(command[2])
        row = {"File": str(snapshot / "sample.txt"), "StartLine": 1, "EndLine": 1,
               "RuleID": "generic-api-key", "Match": PRIVATE_MARKER,
               "Secret": PRIVATE_MARKER, "Fingerprint": "sample.txt:generic-api-key:1"}
        raw = b"{" if malformed else json.dumps([row] * count).encode()
        Path(command[command.index("--report-path") + 1]).write_bytes(raw)
        observation["raw"] = raw
        if drift:
            (root / "sample.txt").write_bytes(b"changed fixture\n")
            (root / "added.txt").write_bytes(b"new candidate\n")
        if timeout:
            raise subprocess.TimeoutExpired(command, 600, output=PRIVATE_MARKER.encode(),
                                            stderr=PRIVATE_MARKER.encode())
        final = f"WRN leaks found: {count}" if count else "INF no leaks found"
        stderr = SUMMARY + "7:13PM " + final + "\n" if summary is None else summary
        return subprocess.CompletedProcess(command, int(bool(count)) if returncode is None else returncode,
                                           stdout=stdout, stderr=stderr.encode())

    monkeypatch.setattr(scanner.subprocess, "run", run)
    return public, private, observation


@pytest.mark.parametrize("count,classify,expected", [(0, False, 0), (2, False, 1), (2, True, 0)])
def test_real_private_boundary_and_complete_counts_preserve_multiplicity(
        tmp_path, monkeypatch, count, classify, expected, capsys):
    public, private, seen = exercise(tmp_path, monkeypatch, count=count, classify=classify)
    assert scanner.main() == expected
    data = json.loads(public.read_bytes())
    assert data["scan_complete"] is True and data["scanned_bytes"] == 67
    assert data["raw_finding_count"] == count
    assert data["classified_finding_count"] == (count if classify else 0)
    assert data["remaining_finding_count"] == (0 if classify else count)
    assert seen["fake_calls"] == 1 and seen["native_scanner_calls"] == 0
    assert (private / "raw-redacted.private.json").read_bytes() == seen["raw"]
    assert PRIVATE_MARKER not in public.read_text(encoding="utf8") + capsys.readouterr().out


@pytest.mark.parametrize("fault", ["partial", "missing-final", "wrong-counter", "duplicate-summary",
    "extra-warning", "extra-error", "extra-stdout", "zero-exit-with-finding", "error-exit",
    "truncated-json", "timeout-with-partial-raw", "oversize-stderr"])
def test_current_main_refuses_partial_or_inconsistent_process_without_public_report(
        tmp_path, monkeypatch, capsys, fault):
    final = "7:13PM WRN leaks found: 1\n"
    changes = {
        "partial": {"summary": "7:13PM ERR scan failed " + PRIVATE_MARKER + "\n"},
        "missing-final": {"summary": SUMMARY},
        "wrong-counter": {"summary": SUMMARY + "7:13PM WRN leaks found: 2\n"},
        "duplicate-summary": {"summary": SUMMARY + SUMMARY + final},
        "extra-warning": {"summary": "7:13PM WRN skipped unreadable file\n" + SUMMARY + final},
        "extra-error": {"summary": SUMMARY + final + "7:13PM ERR " + PRIVATE_MARKER + "\n"},
        "extra-stdout": {"stdout": PRIVATE_MARKER.encode()},
        "zero-exit-with-finding": {"returncode": 0},
        "error-exit": {"returncode": 2},
        "truncated-json": {"malformed": True},
        "timeout-with-partial-raw": {"timeout": True},
        "oversize-stderr": {"summary": SUMMARY + final + "z" * (scanner._CAPTURE_LIMIT + 1)},
    }[fault]
    public, private, seen = exercise(tmp_path, monkeypatch, classify=True, **changes)
    with pytest.raises((RuntimeError, json.JSONDecodeError)) as failure:
        scanner.main()
    assert not public.exists() and seen["fake_calls"] == 1
    assert (private / "raw-redacted.private.json").read_bytes() == seen["raw"]
    assert (private / "scan.stderr.private.log").stat().st_size <= scanner._CAPTURE_LIMIT
    captured = capsys.readouterr()
    assert PRIVATE_MARKER not in str(failure.value) + captured.out + captured.err


def test_complete_summary_cannot_mask_source_or_candidate_set_changes(tmp_path, monkeypatch):
    public, _, _ = exercise(tmp_path, monkeypatch, classify=True, drift=True)
    assert scanner.main() == 2
    data = json.loads(public.read_bytes())
    assert data["scan_complete"] is True and data["source_stable"] is False
    assert set(data["changed_files"]) == {"sample.txt", "added:added.txt"}
    assert data["effective_exit_code"] == 2


@pytest.mark.parametrize("unit", ["ns", "µs", "ms", "s", "m", "h"])
def test_exact_complete_duration_units_are_accepted_without_a_binary_call(unit):
    line = "7:13PM INF scanned ~67 bytes (67 bytes) in 1.25" + unit + "\n"
    assert scanner._require_complete(line + "7:13PM INF no leaks found\n", 0) == 67


@pytest.mark.parametrize("tail", ["WRN leaks found: 01", "WRN leaks found: 1 trailing",
    "INF no leaks found", "WRN leaks found: 0", "WRN leaks found: True"])
def test_counter_text_cannot_authorize_nonmatching_raw_length(tail):
    with pytest.raises(RuntimeError, match="complete execution; output withheld"):
        scanner._require_complete(SUMMARY + "7:13PM " + tail + "\n", 1)

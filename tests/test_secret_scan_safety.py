"""Independent scanner boundary tests; real rule probes have separate evidence."""
import json
from pathlib import Path
import subprocess
import sys

import pytest


def _scenario(tmp_path, monkeypatch, *, failure=False, mutation=None, version="8.30.1"):
    from scripts import scan_secrets as scanner

    root = tmp_path / "candidate"
    root.mkdir()
    (root / ".gitleaks.toml").write_text("[extend]\nuseDefault = true\n", encoding="utf-8")
    (root / "source.py").write_text("safe = 1\n", encoding="utf-8")
    tool = tmp_path / "gitleaks.exe"
    tool.write_bytes(b"synthetic executable boundary; never executed")
    report = tmp_path / "sanitized.json"
    files = [".gitleaks.toml", "source.py"]
    canary = "SYNTHETIC_CANARY_DO_NOT_RETAIN"
    monkeypatch.setattr(scanner, "ROOT", root)
    monkeypatch.setattr(sys, "argv", ["scan_secrets.py", "--gitleaks", str(tool), "--report", str(report)])
    monkeypatch.setenv("GITLEAKS_CONFIG_TOML", "untrusted inherited override")

    def run(command, **options):
        if command[0] == "git":
            return subprocess.CompletedProcess(command, 0, stdout="\0".join(files).encode() + b"\0")
        assert not any(key.upper().startswith("GITLEAKS_") for key in options["env"])
        if command[1] == "version":
            return subprocess.CompletedProcess(command, 0, stdout=version + "\n")
        snapshot = Path(command[2])
        configuration = Path(command[command.index("--config") + 1])
        assert configuration == snapshot / ".gitleaks.toml"
        assert configuration.read_bytes() == (root / ".gitleaks.toml").read_bytes()
        assert options["cwd"] != root
        assert "--redact=100" in command and "--ignore-gitleaks-allow" in command
        ignore = Path(command[command.index("--gitleaks-ignore-path") + 1])
        assert ignore.read_text() == ""
        raw = Path(command[command.index("--report-path") + 1])
        raw.write_text(json.dumps([{"File": str(snapshot / "source.py"), "StartLine": 1,
            "RuleID": "synthetic-rule", "Fingerprint": "source.py:synthetic-rule:1",
            "Secret": canary, "Match": canary, "Author": canary, "Email": canary}]
            if not mutation else []), encoding="utf-8")
        if mutation == "changed":
            (root / "source.py").write_text("safe = 2\n", encoding="utf-8")
        elif mutation == "added":
            (root / "new.py").write_text("new = 1\n", encoding="utf-8")
            files.append("new.py")
        return subprocess.CompletedProcess(command, 2 if failure else (0 if mutation else 1),
            stdout=canary, stderr=canary)

    monkeypatch.setattr(scanner.subprocess, "run", run)
    return scanner, report, canary


def test_report_drops_matches_secrets_and_author_metadata(tmp_path, monkeypatch, capsys):
    scanner, report, canary = _scenario(tmp_path, monkeypatch)
    assert scanner.main() == 1
    text = report.read_text(encoding="utf-8")
    assert canary not in text + capsys.readouterr().out
    finding = json.loads(text)["findings"][0]
    assert set(finding) == {"file", "line", "rule", "fingerprint", "file_sha256"}
    assert finding["file"] == "source.py" and len(finding["file_sha256"]) == 64


def test_scanner_failure_withholds_captured_output(tmp_path, monkeypatch, capsys):
    scanner, report, canary = _scenario(tmp_path, monkeypatch, failure=True)
    with pytest.raises(RuntimeError, match="output withheld") as failure:
        scanner.main()
    captured = capsys.readouterr()
    assert canary not in str(failure.value) + captured.out + captured.err
    assert not report.exists()


@pytest.mark.parametrize("mutation", ["changed", "added"])
def test_files_changed_or_added_during_scan_invalidate_gate(tmp_path, monkeypatch, mutation):
    scanner, report, _ = _scenario(tmp_path, monkeypatch, mutation=mutation)
    assert scanner.main() == 2
    evidence = json.loads(report.read_text(encoding="utf-8"))
    assert not evidence["source_stable"]
    assert evidence["changed_files"] == (["source.py"] if mutation == "changed" else ["added:new.py"])


def test_unreviewed_binary_version_is_rejected(tmp_path, monkeypatch):
    scanner, report, _ = _scenario(tmp_path, monkeypatch, version="0.0.0")
    with pytest.raises(RuntimeError, match="version must be 8.30.1"):
        scanner.main()
    assert not report.exists()

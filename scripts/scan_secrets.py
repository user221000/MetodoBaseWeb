"""Scan a reproducible deliverable snapshot without printing secret values.

Gitleaks must be installed externally and verified against its release checksum.
Only tracked and unignored candidate files are copied. The sanitized report
contains locations/rules and source hashes, never matches, secrets or author
metadata. An exit of 1 means findings; other scanner errors remain failures.
Historical Git objects and ignored local files are outside this tree scan.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gitleaks", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    tool = args.gitleaks.resolve(strict=True)
    report = args.report.resolve()
    environment = {key: value for key, value in os.environ.items()
        if not key.upper().startswith("GITLEAKS_")}
    version = subprocess.run([str(tool), "version"], check=True, capture_output=True,
        text=True, env=environment, timeout=15).stdout.strip()
    if version != "8.30.1":
        raise RuntimeError("Reviewed secret scanner version must be 8.30.1")
    result = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT, check=True, capture_output=True)
    paths = sorted(set(value.decode("utf-8") for value in result.stdout.split(b"\0") if value))
    source_hashes = {}
    encoding_transforms = {}
    with tempfile.TemporaryDirectory(prefix="metodobase-secrets-") as temporary:
        workspace = Path(temporary)
        snapshot = workspace / "snapshot"
        snapshot.mkdir()
        for name in paths:
            source = ROOT / name
            if not source.is_file() or source.resolve() == report:
                continue  # Deleted files and this run's generated report.
            if source.is_symlink() or not source.resolve().is_relative_to(ROOT):
                raise ValueError("Deliverable contains a symlink/outside file: " + name)
            destination = snapshot / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            content = source.read_bytes()
            source_hashes[name] = hashlib.sha256(content).hexdigest()
            # Gitleaks treats BOM UTF16 as binary and misses ASCII secrets in
            # it. Transcode only the private snapshot; retain original hashes.
            encoding = None
            if content.startswith((b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff")):
                encoding = "utf-32"
            elif content.startswith((b"\xff\xfe", b"\xfe\xff")):
                encoding = "utf-16"
            elif content.startswith(b"\xef\xbb\xbf"):
                encoding = "utf-8-sig"
            if encoding:
                content = content.decode(encoding).encode("utf-8")
                encoding_transforms[name] = {"source_encoding": encoding,
                    "scanner_encoding": "utf-8", "scanner_sha256": hashlib.sha256(content).hexdigest()}
            destination.write_bytes(content)
        raw_report = workspace / "raw-redacted.json"
        empty_ignore = workspace / "empty.gitleaksignore"
        empty_ignore.write_text("", encoding="utf-8")
        scan = subprocess.run([str(tool), "dir", str(snapshot), "--config", str(snapshot / ".gitleaks.toml"),
            "--redact=100", "--no-banner", "--no-color", "--log-level=error",
            "--ignore-gitleaks-allow", "--gitleaks-ignore-path", str(empty_ignore),
            "--max-decode-depth=5", "--max-archive-depth=0",
            "--report-format=json", "--report-path", str(raw_report), "--timeout=120"],
            capture_output=True, cwd=workspace, env=environment, timeout=135)
        if scan.returncode not in {0, 1} or not raw_report.is_file():
            raise RuntimeError(f"Secret scanner failed; exit={scan.returncode}; output withheld")
        raw = json.loads(raw_report.read_text(encoding="utf-8")) or []
        findings = []
        for item in raw:
            path = Path(item["File"])
            name = path.relative_to(snapshot).as_posix() if path.is_absolute() else path.as_posix()
            findings.append({"file": name, "line": item["StartLine"], "rule": item["RuleID"],
                "fingerprint": item.get("Fingerprint"), "file_sha256": source_hashes.get(name)})
    changed = [name for name, digest in source_hashes.items()
        if not (ROOT / name).is_file() or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
    after_paths = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT, check=True, capture_output=True)
    current = {value.decode("utf-8") for value in after_paths.stdout.split(b"\0") if value
        and (ROOT / value.decode("utf-8")).is_file()
        and (ROOT / value.decode("utf-8")).resolve() != report}
    changed.extend("added:" + name for name in sorted(current - source_hashes.keys()))
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps({"tool": "gitleaks", "version": version,
        "binary_sha256": hashlib.sha256(tool.read_bytes()).hexdigest(),
        "scope": "tracked and unignored deliverable tree; no git history or ignored files",
        "exit_code": scan.returncode, "source_stable": not changed, "changed_files": changed,
        "files": source_hashes, "encoding_transforms": encoding_transforms, "findings": findings},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Gitleaks {version}: {len(source_hashes)} files, {len(findings)} findings; values withheld")
    return 2 if changed else (1 if findings else scan.returncode)


if __name__ == "__main__":
    raise SystemExit(main())

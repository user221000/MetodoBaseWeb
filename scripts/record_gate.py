"""Run an isolated acceptance command while proving the source stayed fixed.

The interpreter invoking this script is the candidate interpreter used for the
child. Output is UTF-8. No credentials or inherited environment are recorded.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/implementation/20261018-evolution/evidence"


def source_hashes() -> dict[str, str]:
    """Hash maintained code, tests and dependency/config inputs, excluding data."""
    paths = []
    for folder in ("api", "core", "config", "src", "utils", "web", "tests", "ui_desktop", "design_system", "scripts"):
        paths.extend(path for path in (ROOT / folder).rglob("*")
            if path.is_file() and path.suffix in {".py", ".js", ".css", ".html"} and "__pycache__" not in path.parts)
    for pattern in ("requirements*.txt", "requirements*.lock", "*.ini", ".coveragerc", "Dockerfile", "conftest.py", "entrypoint.sh", "railway.toml"):
        paths.extend(ROOT.glob(pattern))
    return {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(set(paths))}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("label")
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    options = parser.parse_args()
    if not options.label.replace("-", "").replace("_", "").isalnum():
        parser.error("Gate label must be an identifier")
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    before = source_hashes()
    start = datetime.now(timezone.utc).isoformat()
    log = EVIDENCE / (options.label + ".log")
    arguments = options.arguments[1:] if options.arguments[:1] == ["--"] else options.arguments
    command = [sys.executable, "-X", "utf8", "tests/run_isolated.py", *arguments]
    with log.open("w", encoding="utf-8") as output:
        result = subprocess.run(command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT, check=False)
    after = source_hashes()
    changed = [name for name in sorted(before.keys() | after.keys()) if before.get(name) != after.get(name)]
    report = {"started_at": start, "ended_at": datetime.now(timezone.utc).isoformat(),
        "python": sys.version, "interpreter": sys.executable, "command": command,
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "tests_exit_code": result.returncode, "changedDuringCheck": bool(changed), "changed": changed,
        "source_hashes": before, "log": log.name}
    (EVIDENCE / (options.label + "-source.json")).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"gate": options.label, "tests_exit_code": result.returncode,
        "changedDuringCheck": bool(changed), "files": len(before)}))
    return result.returncode or (2 if changed else 0)


if __name__ == "__main__":
    raise SystemExit(main())

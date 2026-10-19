"""Blocking syntax/security checks with narrowly reviewed historical noise."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ("api", "core", "web", "src", "utils", "config", "ui_desktop", "design_system", "scripts")


def maintained_targets():
    """Include runtime/build/operational entrypoints, excluding test fixtures."""
    return [*SOURCES, *(path.name for path in sorted(ROOT.glob("*.py"))
                        if path.name != "conftest.py")]


def fingerprint(finding):
    """Bind an exception to source text, path and rule, independent of line shifts."""
    code = "\n".join(re.sub(r"^\d+\s", "", line).strip() for line in finding["code"].splitlines()).strip()
    path = finding["filename"].replace("\\", "/").removeprefix("./")
    return f"{path}:{finding['test_id']}:{hashlib.sha256(code.encode()).hexdigest()}"


def main():
    if sys.argv[1:] == ["lint"]:
        return subprocess.run([sys.executable, "-m", "ruff", "check", *maintained_targets(),
                               "--select", "F821"], cwd=ROOT, check=False).returncode
    if sys.argv[1:] == ["syntax"]:
        paths = set(ROOT.glob("*.py"))
        for source in (*SOURCES, "tests"):
            paths.update((ROOT / source).rglob("*.py"))
        for path in sorted(paths):
            ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        print(f"Parsed {len(paths)} maintained Python files")
        return 0
    if sys.argv[1:] != ["security"]:
        raise SystemExit("usage: python tests/check_quality.py lint|syntax|security")
    result = subprocess.run([sys.executable, "-X", "utf8", "-m", "bandit", "-q", "-r", *maintained_targets(),
                             "-ll", "--skip", "B101", "-f", "json"],
                            cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if result.returncode not in {0, 1}:
        print(result.stderr)
        return result.returncode
    if not result.stdout.strip():
        print(result.stderr)
        return 1
    report = json.loads(result.stdout)
    if report["errors"]:
        print(json.dumps(report["errors"]))
        return 1
    baseline = json.loads((ROOT / "tests/bandit-reviewed-baseline.json").read_text(encoding="utf-8"))
    today = datetime.now(timezone.utc).date().isoformat()
    approved = {item["fingerprint"] for item in baseline["exceptions"] if item["expires"] >= today}
    new = [finding for finding in report["results"] if fingerprint(finding) not in approved]
    for finding in new:
        print(f"Unreviewed {finding['test_id']} {finding['filename']}:{finding['line_number']}: {finding['issue_text']}")
    print(f"Bandit: {len(report['results'])} findings; {len(new)} require review")
    return int(bool(new))


if __name__ == "__main__":
    raise SystemExit(main())

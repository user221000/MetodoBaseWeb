"""Web deliverable quality using the original reviewed finding fingerprints."""
from __future__ import annotations

import ast
import importlib.metadata
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tests.check_quality import fingerprint

RUNTIME = ("api", "core", "web", "src", "utils", "config", "runtime-source")
OPERATIONAL = (
    "api_server.py", "db_bootstrap.py", "scripts/scan_secrets.py",
    "scripts/reviewed_scan_locations.py", "scripts/record_gate.py",
    "scripts/migrate_rbac.py", "scripts/inventory_legacy_objects.py",
    "scripts/implementation_registry.py", "scripts/cleanup_expired_tokens.py",
    "scripts/check_frontend_report.py", "scripts/check_followup_fixture.py",
    "scripts/check_browser_fixture_startup.py", "scripts/backup_restore.py",
    "scripts/backup_daily.py", "scripts/apply_legacy_objects.py",
)


def maintained_targets():
    return [*RUNTIME, *OPERATIONAL]


def syntax_paths():
    paths = {ROOT / name for name in OPERATIONAL}
    for source in (*RUNTIME, "tests"):
        paths.update((ROOT / source).rglob("*.py"))
    return sorted(path for path in paths
                  if path.name not in {"test_login_desktop.py", "test_license_offline_security.py"}
                  and not path.name.startswith("test_desktop"))


def main():
    if sys.argv[1:] == ["lint"]:
        return subprocess.run([sys.executable, "-m", "ruff", "check", *maintained_targets(),
                               "--select", "F821"], cwd=ROOT, check=False).returncode
    if sys.argv[1:] == ["syntax"]:
        paths = syntax_paths()
        for path in paths:
            ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        print(f"Parsed {len(paths)} maintained web and test Python files")
        return 0
    report_target = None
    if len(sys.argv[1:]) == 3 and sys.argv[1:3] == ["security", "--report"]:
        report_target = Path(sys.argv[3])
        if not report_target.is_absolute() or report_target.exists() or not report_target.parent.is_dir():
            raise ValueError("Bandit RAW requires a fresh absolute file inside an existing private boundary")
    elif sys.argv[1:] != ["security"]:
        raise SystemExit("usage: python tests/ci_web37/quality.py lint|syntax|security [--report <private-absolute-file>]")
    result = subprocess.run([sys.executable, "-X", "utf8", "-m", "bandit", "-q", "-r", *maintained_targets(),
                             "-ll", "--skip", "B101", "-f", "json"],
                            cwd=ROOT, capture_output=True, check=False)
    if report_target is not None:
        with report_target.open("xb") as raw:
            raw.write(result.stdout)
    if result.returncode not in {0, 1} or not result.stdout.strip():
        print(result.stderr.decode("utf8", errors="replace"))
        return result.returncode or 1
    report = json.loads(result.stdout)
    if report["errors"]:
        print(json.dumps(report["errors"]))
        return 1
    baseline = json.loads((ROOT / "tests/bandit-reviewed-baseline.json").read_text(encoding="utf-8"))
    today = datetime.now(UTC).date().isoformat()
    approved = {item["fingerprint"] for item in baseline["exceptions"] if item["expires"] >= today}
    new = [finding for finding in report["results"] if fingerprint(finding) not in approved]
    if len(new) == 22:
        from tests.ci_web37.bandit_registry import REGISTRY, apply_registry
        from tests.ci_web37.container_inputs import verify

        registry = json.loads(REGISTRY.read_bytes())
        try:
            inputs = verify()
            if inputs["container_inputs"] != 12 or inputs["runtime_distribution_count"] != 57:
                raise ValueError("The current isolated Docker entry source contract differs")
            matched = apply_registry({"errors": [], "results": new}, ROOT, registry,
                context="isolated-docker-expat-build-verified12-and-reviewed-static-SQL",
                bandit_version=importlib.metadata.version("bandit"))
        except (ValueError, KeyError, TypeError) as error:
            print(f"Finite current review refused: {error}")
        else:
            print(f"Finite current review: {matched['approved_occurrences']} exact occurrences; {matched['source_variant']}")
            new = []
    for finding in new:
        print(f"Unreviewed {finding['test_id']} {finding['filename']}:{finding['line_number']}: {finding['issue_text']}")
    print(f"Bandit: {len(report['results'])} findings; {len(new)} require review")
    return int(bool(new))


if __name__ == "__main__":
    raise SystemExit(main())

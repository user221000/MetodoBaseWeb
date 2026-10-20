"""Exercise real web quality tools with inert root/operation/runtime regressions."""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tests.ci_web37.quality import OPERATIONAL, RUNTIME


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    if args.evidence is not None and (not args.evidence.is_absolute() or not args.evidence.is_dir()):
        parser.error("Existing absolute private evidence directory required")
    with tempfile.TemporaryDirectory(prefix="metodobase-quality-web37-") as temporary:
        target = Path(temporary)
        for directory in (*RUNTIME, "tests/ci_web37"):
            (target / directory).mkdir(parents=True, exist_ok=True)
        for name in OPERATIONAL:
            source = target / name
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text("safe = 1\n", encoding="utf8")
        (target / "tests/__init__.py").touch()
        for name in ("tests/ci_web37/quality.py", "tests/check_quality.py", "tests/bandit-reviewed-baseline.json"):
            shutil.copyfile(ROOT / name, target / name)
        command = [sys.executable, "-B", "-X", "utf8", str(target / "tests/ci_web37/quality.py")]

        observations = []

        def run(mode):
            result = subprocess.run([*command, mode], capture_output=True, timeout=30, check=False)
            observations.append({"mode": mode, "exit": result.returncode})
            if args.evidence is not None:
                prefix = args.evidence / ("tool-" + str(len(observations)))
                prefix.with_suffix(".stdout.private.log").write_bytes(result.stdout)
                prefix.with_suffix(".stderr.private.log").write_bytes(result.stderr)
            result.stdout = result.stdout.decode("utf8")
            result.stderr = result.stderr.decode("utf8")
            return result

        for filename in ("api_server.py", "scripts/backup_daily.py", "web/synthetic_quality_probe.py"):
            source = target / filename
            source.write_text("safe = 1\n", encoding="utf8")
            assert run("lint").returncode == run("syntax").returncode == 0
            source.write_text("def probe():\n    return undefined_web_quality_canary\n", encoding="utf8")
            result = run("lint")
            assert result.returncode != 0 and "F821" in result.stdout, "Real web undefined-name guard did not reject"
            source.write_text("def broken(:\n", encoding="utf8")
            result = run("syntax")
            assert result.returncode != 0 and "SyntaxError" in result.stderr, "Real web parse guard did not reject"
            source.write_text("import subprocess\ndef dangerous(command):\n    subprocess.run(command, shell=True)\n", encoding="utf8")
            result = run("security")
            assert result.returncode != 0 and "B602" in result.stdout, "Real web Bandit guard did not reject"
            source.write_text("safe = 1\n", encoding="utf8")
        if args.evidence is not None:
            (args.evidence / "nine-probes.json").write_text(json.dumps({
                "failure_probes": 9, "positive_controls": 6, "observations": observations,
                "synthetic_code_imported_or_executed": False}, indent=2) + "\n", encoding="utf8")
    print("Verified web root, operation and runtime F821/syntax/Bandit guards; synthetic code never imported")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

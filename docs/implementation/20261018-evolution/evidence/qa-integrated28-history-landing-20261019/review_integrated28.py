"""Independent broad web gate on the integrated revision28/history/landing candidate."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

ROOT = Path(r"F:\MetodoBaseWeb-execution-20261018")
OUT = Path(__file__).resolve().parent
PYTHON = Path(r"C:\Users\Consu\AppData\Local\Temp\metodobase-candidate-web-20261018\Scripts\python.exe")
HEAD = "dd9877350aad3f483299c990a1e97aab63c83f5d"
DIRS = {".github", "api", "core", "web", "src", "utils", "config", "ui_desktop", "design_system", "scripts", "tests", "assets", "fonts", "static", "infra"}
EXTENSIONS = {".py", ".js", ".cjs", ".ts", ".tsx", ".json", ".html", ".css", ".sql", ".lock", ".txt", ".ini", ".yml", ".yaml", ".bat", ".cmd", ".ps1", ".sh", ".spec", ".csv", ".svg", ".png", ".jpg", ".jpeg", ".ico", ".woff", ".woff2", ".ttf", ".otf"}
EXCLUDED = {"node_modules", "__pycache__", ".pytest_cache", ".venv", "venv", "dist", "build"}
KNOWN_SKIP = "tests.test_object_storage::test_symlink_cannot_redirect_a_private_document"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    with (OUT / name).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def git_head():
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def paths():
    files = set()
    for dirname in DIRS:
        folder = ROOT / dirname
        if not folder.is_dir():
            continue
        for path in folder.rglob("*"):
            if path.is_file() and path.suffix.lower() in EXTENSIONS and not any(part in EXCLUDED for part in path.relative_to(ROOT).parts):
                files.add(path.relative_to(ROOT).as_posix())
    for path in ROOT.iterdir():
        if path.is_file() and (path.suffix.lower() in EXTENSIONS or path.name in {".coveragerc", ".gitattributes", "Dockerfile", ".dockerignore", ".gitignore"}):
            files.add(path.name)
    files.add(".github/workflows/ci.yml")
    return sorted(files)


def capture(label):
    files = paths()
    snapshot = {name: sha(ROOT / name) for name in files}
    packages = sorted(({"name": entry.metadata["Name"], "version": entry.version}
                       for entry in importlib.metadata.distributions()), key=lambda row: row["name"].lower())
    assert len(packages) == 89, "Candidate package count changed"
    result = subprocess.run([str(PYTHON), "-m", "pip", "check"], cwd=ROOT, capture_output=True, encoding="utf-8")
    with (OUT / (label + "-pip-check.log")).open("x", encoding="utf-8") as stream:
        stream.write(result.stdout + result.stderr)
    assert result.returncode == 0
    value = {"utc": datetime.now(timezone.utc).isoformat(), "head": git_head(), "source_count": len(snapshot), "sources": snapshot,
             "python": sys.version, "packages": packages, "package_count": len(packages), "pip_check_exit": result.returncode}
    save(label + "-source.json", value)
    assert value["head"] == HEAD
    return value


def junit(path):
    root = ET.parse(path).getroot()
    cases = root.findall(".//testcase")
    skips = [{"node": case.attrib.get("classname", "") + "::" + case.attrib["name"],
              "message": case.find("skipped").attrib.get("message", "")} for case in cases if case.find("skipped") is not None]
    return {"collected": len(cases), "passed": sum(not any(case.find(tag) is not None for tag in ("skipped", "failure", "error")) for case in cases),
            "failures": len(root.findall(".//failure")), "errors": len(root.findall(".//error")), "skipped": skips}


assert Path(sys.executable).resolve() == PYTHON.resolve()
assert git_head() == HEAD
assert not subprocess.run(["git", "diff", "--name-only"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
baseline = capture("before-serial")
print("Frozen " + str(baseline["source_count"]) + " runtime/test/dependency files;89 packages;pip check0;HEADdd98773", flush=True)
runs = []
accepted = False
error = None
try:
    for label in ("serial", "shuffle"):
        before = baseline if label == "serial" else capture("before-shuffle")
        assert before["sources"] == baseline["sources"] and before["packages"] == baseline["packages"]
        temporary_root = Path(tempfile.mkdtemp(prefix="metodobase-test-qa-integrated28-" + label + "-"))
        environment = os.environ.copy()
        for name in ("_METODOBASE_TEST_ROOT", "PYTEST_XDIST_WORKER", "METODOBASE_TEST_DATABASE_URL", "METODOBASE_TEST_REDIS_URL",
                     "METODOBASE_TEST_MIGRATOR_URL", "METODOBASE_TEST_POSTGRES_URL", "METODOBASE_TEST_PG_BIN", "METODOBASE_HISTORY_EXPLAIN_OUTPUT"):
            environment.pop(name, None)
        environment.update({"_METODOBASE_TEST_ROOT": str(temporary_root), "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1",
                            "COVERAGE_FILE": str(OUT / "qa-integrated28-history-landing.coverage")})
        xml = OUT / ("qa-integrated28-history-landing-" + label + ".xml")
        command = [str(PYTHON), "-X", "utf8", "tests/run_isolated.py", "tests", "--ignore=tests/test_login_desktop.py", "--ignore=tests/test_desktop_entrypoints.py"]
        if label == "serial":
            command += ["-q", "--tb=short", "--cov", "--cov-report=xml:" + str(OUT / "qa-integrated28-history-landing-coverage.xml"),
                        "--cov-report=json:" + str(OUT / "qa-integrated28-history-landing-coverage.json")]
        else:
            command += ["--shuffle-seed=20261018", "-q", "-n", "2", "--tb=short"]
        command.append("--junitxml=" + str(xml))
        print("Starting " + label + " broad gate with fresh isolated SQLite data", flush=True)
        started = time.monotonic()
        with (OUT / ("qa-integrated28-history-landing-" + label + ".log")).open("xb") as output:
            result = subprocess.run(command, cwd=ROOT, env=environment, stdout=output, stderr=subprocess.STDOUT)
        after = capture("after-" + label)
        counts = junit(xml)
        run = {"label": label, "command": command, "temporary_test_root": str(temporary_root),
               "seconds": round(time.monotonic() - started, 3), "exit": result.returncode, "junit": counts,
               "source_stable": after["sources"] == before["sources"], "packages_stable": after["packages"] == before["packages"]}
        runs.append(run)
        save("qa-integrated28-history-landing-" + label + "-result.json", run)
        print(json.dumps({"finished": label, "seconds": run["seconds"], "exit": result.returncode, "junit": counts,
                          "sources_stable": run["source_stable"], "packages_stable": run["packages_stable"]}), flush=True)
        assert result.returncode == 0 and counts["failures"] == counts["errors"] == 0
        assert len(counts["skipped"]) <= 1
        assert all(row["node"] == KNOWN_SKIP and "Host does not grant symlink creation" in row["message"] for row in counts["skipped"])
        assert run["source_stable"] and run["packages_stable"]
        if label == "serial":
            coverage = subprocess.run([str(PYTHON), "tests/check_coverage.py", str(OUT / "qa-integrated28-history-landing-coverage.json")], cwd=ROOT, env=environment, capture_output=True, encoding="utf-8")
            with (OUT / "qa-integrated28-history-landing-coverage-guard.log").open("x", encoding="utf-8") as output:
                output.write(coverage.stdout + coverage.stderr)
            save("qa-integrated28-history-landing-coverage-guard.json", {"exit": coverage.returncode})
            assert coverage.returncode == 0
    assert runs[0]["junit"]["passed"] == runs[1]["junit"]["passed"]
    def outcomes(path):
        cases = ET.parse(path).getroot().findall('.//testcase')
        result = {}
        for case in cases:
            node = case.attrib.get('classname', '') + '::' + case.attrib['name']
            assert node not in result, 'Duplicate JUnit node: ' + node
            tags = tuple(tag for tag in ('skipped', 'failure', 'error') if case.find(tag) is not None)
            result[node] = tags
        return result
    serial_outcomes = outcomes(OUT / 'qa-integrated28-history-landing-serial.xml')
    shuffle_outcomes = outcomes(OUT / 'qa-integrated28-history-landing-shuffle.xml')
    assert serial_outcomes == shuffle_outcomes, 'Collected case identities/outcomes differ between serial and shuffled runs'
    save('case-outcomes.json', {'identical': True, 'cases': serial_outcomes})
    accepted = True
except BaseException as exc:
    error = {"class": type(exc).__name__, "detail": str(exc)}
finally:
    proof = {"accepted": accepted, "head": HEAD, "source_count": baseline["source_count"], "package_count": 89,
             "runs": runs, "error": error,
             "scope": "Current integrated web suite with source/locks/installed packages frozen. Serial coverage and two isolated shuffled workers. Fresh metadata-only SQLite and Python socket guard; no PG integrations/provider/image/Linux/desktopGUI/Actions execution.",
             "only_allowed_skip": KNOWN_SKIP,
             "all_prior_acceptance_evidence": "preserved; no earlier case totals reused or summed"}
    save("qa-integrated28-history-landing-source.json", proof)
if not accepted:
    raise AssertionError(error)
print(json.dumps({"accepted": True, "serial_passed": runs[0]["junit"]["passed"], "shuffle_passed": runs[1]["junit"]["passed"],
                  "summary_sha256": sha(OUT / "qa-integrated28-history-landing-source.json")}))

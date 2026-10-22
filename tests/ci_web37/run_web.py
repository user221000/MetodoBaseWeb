"""Current web SQLite/Node gates with private originals and honest RED results.

PostgreSQL, Redis, Docker and native browsers are separate leased gates. This
runner never launches them. Physical35 criteria use their own source/models35.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tests.ci_google33.environment_photo import interpreter, packages
from tests.ci_google33.publish import scan
from scripts.scan_secrets import _private_evidence as private_directory
from tests.ci_web37.prepare_collection import source_photo
from tests.ci_web37.recipes import (
    CONTROL_SELECTORS,
    CURRENT_RUNTIME_SELECTORS,
    HISTORICAL35_SELECTORS,
    NODE_MAP,
    R05_FROZEN_PHASES,
    SHUFFLE_SEED,
    SMOKE_SELECTORS,
    require_native_expiry_replacement,
    require_scanner_safety_companion,
)
from tests.ci_web37.reports import junit_identities, node_cases, require_exact_junit


def write(path, value):
    with path.open("x", encoding="utf8") as out:
        json.dump(value, out, indent=2)
        out.write("\n")


def node_directory():
    candidates = [ROOT / "tests/e2e/node_modules"]
    if os.name == "nt":
        candidates += [Path("F:/MetodoBaseWeb-execution-20261018/tests/e2e/node_modules"),
                       Path("F:/MetodoBaseWeb-main/tests/e2e/node_modules")]
    return next((path for path in candidates if path.is_dir()), None)


def environment_photo():
    node = shutil.which("node")
    directory = node_directory()
    files = {str(path.relative_to(directory)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
             for path in sorted(directory.rglob("*")) if path.is_file()} if directory else {}
    return {"source": source_photo(), "Python": interpreter(), "packages": packages(),
            "Node_binary_sha256": hashlib.sha256(Path(node).read_bytes()).hexdigest() if node else None,
            "Node_installed_files": files}


def execute(argv, source, environment, raw_path, *, timeout=None):
    with raw_path.open("xb") as raw:
        child = subprocess.Popen(argv, cwd=source, env=environment, stdout=raw, stderr=subprocess.STDOUT)
        # Never force-kill a Python redirector or its unattributed descendants.
        # Application fixtures own their cleanup. Node offline gates prohibit
        # child processes and have a separate bounded timeout.
        try:
            return child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            if argv[0] == shutil.which("node"):
                child.kill()
                child.wait()
            raise


def observe_junit(path, expected):
    raw = path.read_bytes()
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValueError("Unexpected required XML declaration")
    root = ET.fromstring(raw)
    cases = list(root.iter("testcase"))
    identities = [(row.get("classname"), row.get("name")) for row in cases]
    exact = len(identities) == len(set(identities)) and set(identities) == set(map(tuple, expected))
    counts = {name: sum(bool(row.find(name) is not None) for row in cases)
              for name in ("failure", "error", "skipped")}
    return {"reported_cases": len(cases), "collected_cases": len(expected), "identities_exact": exact,
            "failed": counts["failure"], "errors": counts["error"], "skipped": counts["skipped"],
            "passed": len(cases) - sum(counts.values())}


def pytest_gate(private, environment, suite):
    source = ROOT
    selectors = list(CURRENT_RUNTIME_SELECTORS)
    if suite == "smoke":
        selectors = list(SMOKE_SELECTORS)
    if suite == "control":
        selectors = [SMOKE_SELECTORS[5], "-p", "tests.ci_web37.composition", "--web37-current-fixtures"]
    if suite == "controls":
        selectors = list(CONTROL_SELECTORS)
    if suite == "node-controls":
        selectors = ["tests/test_ci_web37_node_current.py", "-p", "tests.ci_web37.composition",
                     "--web37-current-fixtures", "-p", "tests.ci_web37.scope"]
    if suite == "pg-controls":
        selectors = ["tests/test_ci_web37_pg_legacy.py", "tests/test_ci_web37_pg_expansion.py", "-p", "tests.ci_web37.composition",
                     "--web37-current-fixtures", "-p", "tests.ci_web37.scope"]
    if suite == "pg-lease-controls":
        selectors = ["tests/test_ci_web37_pg_lease.py", "-p", "tests.ci_web37.composition",
                     "--web37-current-fixtures", "-p", "tests.ci_web37.scope"]
    if suite == "r05-history-controls":
        selectors = ["tests/test_ci_web37_git_history.py", "tests/test_ci_web37_r05_phase_selection.py",
                     "tests/test_ci_web37_r05_v7_history.py", "-p", "tests.ci_web37.composition",
                     "--web37-current-fixtures", "-p", "tests.ci_web37.scope"]
    if suite == "r31-current":
        selectors = ["tests/test_current37_r31_primary_boundaries.py", "-p", "tests.ci_web37.composition",
                     "--web37-current-fixtures", "-p", "tests.ci_web37.scope"]
    if suite == "image-controls":
        selectors = ["tests/test_ci_web37_image_context.py", "tests/test_ci_web37_image_preflight.py", "-p", "tests.ci_web37.composition",
                     "--web37-current-fixtures", "-p", "tests.ci_web37.scope"]
    if suite == "legacy-current":
        selectors = ["tests/test_current37_primary_privacy.py", "tests/test_current37_retention.py",
                     "-p", "tests.ci_web37.composition", "--web37-current-fixtures", "-p", "tests.ci_web37.scope"]
    if suite == "registry-controls":
        selectors = ["tests/test_ci_web37_bandit_registry.py", "-p", "tests.ci_web37.composition",
                     "--web37-current-fixtures", "-p", "tests.ci_web37.scope"]
    if suite == "release-controls":
        selectors = ["tests/test_ci_web37_image_context.py", "tests/test_ci_web37_image_preflight.py",
                     "tests/test_ci_web37_bandit_registry.py", "-p", "tests.ci_web37.composition",
                     "--web37-current-fixtures", "-p", "tests.ci_web37.scope"]
    if suite == "history35":
        from tests.ci_web37.history import materialize
        source = private / "historical35-source"
        receipt = materialize(source)
        write(private / "historical35-materialization.json", receipt)
        selectors = list(HISTORICAL35_SELECTORS)
    evidence = private / "companion-bindings"
    evidence.mkdir()
    collection_selectors = list(selectors)
    runtime_selectors = list(selectors)
    if suite != "history35":
        for label, target in (("collection", collection_selectors), ("runtime", runtime_selectors)):
            directory = evidence / label
            directory.mkdir()
            target += ["--web37-companion-evidence", str(directory)]
        if "tests.ci_web37.scope" not in runtime_selectors:
            runtime_selectors += ["-p", "tests.ci_web37.scope"]
        journal = private / "execution-journal"
        journal.mkdir()
        runtime_selectors += ["--web37-execution-journal", str(journal)]
    oracle = private / "oracle.json"
    collector = source / "tests/ci_google33/collect.py" if suite == "history35" else ROOT / "tests/ci_web37/collect.py"
    collect = [sys.executable, "-X", "utf8", str(collector), "--output", str(oracle), *collection_selectors]
    collected = execute(collect, source, environment, private / "collection.private.log")
    if collected:
        return {"collection_exit": collected, "runtime_started": False, "accepted": False}
    expected = json.loads(oracle.read_bytes())
    if suite in {"serial", "parallel"}:
        require_scanner_safety_companion(expected)
        require_native_expiry_replacement(expected)
    argv = [sys.executable, "-X", "utf8", "tests/run_isolated.py", *runtime_selectors, "-q", "--tb=short",
            "--basetemp=" + str(private / "pytest-data"), "--junitxml=" + str(private / "pytest.xml")]
    if suite == "serial":
        argv += ["--cov", "--cov-config=" + str(ROOT / "tests/ci_web37/coverage.ini"),
                 "--cov-report=json:" + str(private / "coverage.json"), "--cov-report=xml:" + str(private / "coverage.xml")]
    if suite == "parallel":
        argv += ["--shuffle-seed=" + str(SHUFFLE_SEED), "-n", "2"]
    write(private / "command.private.json", {"argv": argv, "source": str(source)})
    code = execute(argv, source, environment, private / "pytest.private.log")
    result = {"collection_exit": collected, "runtime_started": True, "pytest_exit": code,
              "physical35_source_separate": suite == "history35", "shuffle_seed": SHUFFLE_SEED if suite == "parallel" else None}
    if suite == "history35":
        result["historical_source_quiet"] = all(hashlib.sha256((source / row["path"]).read_bytes()).hexdigest()
                                                == row["raw_sha256"] for row in receipt["files"])
    if (private / "pytest.xml").is_file():
        result.update(observe_junit(private / "pytest.xml", expected))
    accepted = code == 0 and result.get("identities_exact") is True and result.get("historical_source_quiet", True)
    if accepted:
        require_exact_junit((private / "pytest.xml").read_bytes(), expected)
    if suite == "serial" and code == 0:
        result["risk_coverage_exit"] = execute([sys.executable, "tests/check_coverage.py", str(private / "coverage.json")],
            ROOT, environment, private / "coverage.private.log")
        accepted = accepted and result["risk_coverage_exit"] == 0
    result["accepted"] = accepted
    return result


def r05_history_gate(private, environment):
    """Require both original registry-specific phases outside current runtime."""
    from tests.ci_web37.git_history import load
    proof = load()
    results = []
    for phase, required in R05_FROZEN_PHASES:
        script = "tests/ci_web37/run_r05_history.py"
        selected_proof = proof
        if phase == "frozen-v7-author15":
            from tests.ci_web37.r05_v7_history import load as load_v7
            selected_proof = load_v7()
            script = "tests/ci_web37/run_r05_v7_history.py"
        if selected_proof.manifest["phases"][phase]["required_cases"] != required:
            raise ValueError("The original R05 phase criteria differ from the finite recipe")
        directory = private / phase
        argv = [sys.executable, "-B", "-X", "utf8", script,
                "--phase", phase, "--private", str(directory)]
        code = execute(argv, ROOT, environment, private / (phase + ".private.log"))
        if code:
            raise ValueError("An original frozen R05 phase failed; its RAW result remains private")
        row = json.loads((directory / "result.json").read_bytes())
        files = selected_proof.manifest["phases"][phase]["files"]
        quiet = all(hashlib.sha256((directory / "source" / name).read_bytes()).hexdigest()
                    == value["materialized_sha256"] for name, value in files.items())
        if (row.get("accepted") is not True or row.get("phase") != phase
                or row.get("required_cases") != required or row.get("passed_exact_unique_cases") != required
                or row.get("process_or_network_attempts") != 0 or row.get("Git_repository_present") is not False
                or row.get("current_runtime_claim") is not False or not quiet
                or len(junit_identities((directory / "pytest.xml").read_bytes())) != required):
            raise ValueError("The source-bound frozen R05 result or literal assertions differ")
        results.append({"phase": phase, "passed": required, "literal_sources_quiet": quiet,
                        "process_or_network_attempts": 0, "current_runtime_claim": False})
    write(private / "r05-history-observation.json", results)
    return {"accepted": True, "frozen_R05_phases": results, "passed": sum(row["passed"] for row in results),
            "scope": "frozen_v5_peer60_v6_author48_v7_author15_separate_from_current_runtime",
            "current_runtime_claim": False}


def node_gate(private, environment):
    mapping = json.loads((ROOT / NODE_MAP).read_bytes())
    commands = mapping["current_commands"]
    if len(commands) != 51 or len(mapping["case_obligations"]) != 865:
        raise ValueError("Current frontend normative command/obligation inventory differs")
    results = []
    for index, entry in enumerate(commands):
        argv = [shutil.which("node"), "--require", str(ROOT / "tests/e2e/browser_offline31.cjs"), *entry["argv"][1:]]
        module = ROOT / entry["argv"][1]
        if hashlib.sha256(module.read_bytes().replace(b"\r\n", b"\n")).hexdigest() != entry["source_sha256"]:
            raise ValueError("A reviewed current frontend companion source differs")
        path = private / ("node-" + str(index + 1) + ".private.json")
        code = execute(argv, ROOT, environment, path, timeout=300)
        passed = 0
        valid = False
        if code == 0:
            try:
                passed = node_cases(json.loads(path.read_bytes()), [row["name"] for row in entry["expected_cases"]])
                valid = True
            except (ValueError, TypeError):
                valid = False
        results.append({"command": entry["key"], "exit": code, "cases": passed, "exact_normative_labels": valid})
    write(private / "node-observation.json", results)
    return {"commands": len(results), "executions": sum(row["cases"] for row in results),
            "normative_obligations": len(mapping["case_obligations"]),
            "accepted": all(row["exit"] == 0 and row["exact_normative_labels"] for row in results),
            "native_browser_executed": False}


def current_node_gate(private, environment):
    from tests.ci_web37.node_current import require_sources, validate
    mapping = json.loads((ROOT / "tests/ci_web37/node-current37.json").read_bytes())
    commands = require_sources(ROOT, mapping)
    results = []
    for index, entry in enumerate(commands):
        path = private / ("node-current-" + str(index + 1) + ".private.json")
        argv = [shutil.which("node"), "--require", str(ROOT / "tests/e2e/ci_web37_offline.cjs"), entry["script"]]
        code = execute(argv, ROOT, environment, path, timeout=300)
        passed = 0
        valid = False
        if code == 0:
            try:
                passed = validate(path.read_bytes(), entry)
                valid = True
            except (ValueError, TypeError):
                valid = False
        results.append({"command": entry["script"], "exit": code, "cases": passed,
                        "exact_normative_labels": valid})
    require_sources(ROOT, mapping)
    write(private / "node-current-observation.json", results)
    return {"commands": len(results), "executions": sum(row["cases"] for row in results),
            "legacy51_cases_repeated": 0, "bound_direct_transitive_files": len(mapping["input_files"]),
            "accepted": all(row["exit"] == 0 and row["exact_normative_labels"] for row in results),
            "native_browser_executed": False, "read_Git_transports": "finite_RAW_fixtures_no_child_process"}


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--suite", choices=("serial", "parallel", "node", "node-current", "node-controls", "pg-controls", "pg-lease-controls", "r05-history-controls", "r05-history", "r31-current", "image-controls", "legacy-current", "registry-controls", "release-controls",
                                          "history35", "smoke", "control", "controls"), required=True)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--replay-manifest", type=Path)
    args = parser.parse_args()
    from web.database.schema_control import expected_head
    if expected_head() != "20261020_account_security":
        parser.error("This current runner requires the actual37 product")
    if not args.private.is_absolute() or not args.output.is_absolute() or args.output.exists():
        parser.error("Fresh absolute private/public paths are required")
    private = private_directory(args.private)
    if os.name == "nt":
        acl = subprocess.check_output(["icacls", str(private)])
        (private / "dacl-before-payload.private.txt").write_bytes(acl)
    else:
        assert private.stat().st_mode & 0o777 == 0o700
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHON_DOTENV_DISABLED="1",
                       COVERAGE_FILE=str(private / ".coverage"))
    # VM test author knobs cannot silently select an earlier API source.
    environment.pop("BROWSER31_SOURCE", None)
    environment.pop("SEC_BROWSER_SOURCE", None)
    environment.pop("_METODOBASE_TEST_ROOT", None)
    environment.update(_METODOBASE_TEST_ROOT=str(private / "metodobase-test-data"),
                       METODOBASE_TEST_DATABASE_URL="", METODOBASE_TEST_REDIS_URL="")
    if node_directory():
        environment["NODE_PATH"] = str(node_directory())
    before = environment_photo()
    replay = json.loads(args.replay_manifest.read_bytes()) if args.replay_manifest else None
    if replay is not None:
        from tests.ci_web37.replay import verify_manifest
        verify_manifest(ROOT, replay)
    write(private / "before.json", before)
    pip_before = execute([sys.executable, "-m", "pip", "check"], ROOT, environment, private / "pip-before.private.log")
    result = {"accepted": False, "suite": args.suite}
    try:
        if pip_before != 0:
            raise ValueError("Dependency consistency failed before execution")
        if args.suite == "r05-history":
            observation = r05_history_gate(private, environment)
        elif args.suite == "node-current":
            observation = current_node_gate(private, environment)
        elif args.suite == "node":
            observation = node_gate(private, environment)
        else:
            observation = pytest_gate(private, environment, args.suite)
        result.update(observation)
    except Exception as error:  # noqa: BLE001 -- seal every failed gate before rejecting it
        import traceback
        (private / "runner-error.private.log").write_text(traceback.format_exc(), encoding="utf8")
        result.update(accepted=False, runner_error_class=type(error).__name__)
    finally:
        after = environment_photo()
        write(private / "after.json", after)
        pip_after = execute([sys.executable, "-m", "pip", "check"], ROOT, environment, private / "pip-after.private.log")
    quiet = before == after
    if replay is not None:
        result["frozen_replay_files_verified_before_and_after"] = verify_manifest(ROOT, replay)
    result.update(source_commit=before["source"]["HEAD"], source_packages_binaries_quiet=quiet,
                  pip_before=pip_before, pip_after=pip_after, packages=len(before["packages"]),
                  accepted=result["accepted"] and quiet and pip_before == pip_after == 0,
                  PostgreSQL=False, Redis=False, Docker=False, Chrome=False, Desktop_runtime=False)
    write(private / "observation.json", result)
    archive = private / "originals.private.zip"
    manifest = []
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as output:
        for path in sorted(private.rglob("*")):
            if path.is_file() and path != archive:
                raw = path.read_bytes()
                name = path.relative_to(private).as_posix()
                output.writestr(name, raw)
                manifest.append({"path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    with zipfile.ZipFile(archive) as closed:
        if closed.namelist() != [row["path"] for row in manifest]:
            raise ValueError("Closed private archive membership differs")
        for row in manifest:
            if hashlib.sha256(closed.read(row["path"])).hexdigest() != row["sha256"]:
                raise ValueError("Closed private archive readback differs")
    write(private / "closed-manifest.json", {"members": manifest, "all_members_readback": True})
    if os.name == "nt":
        final_acl = subprocess.check_output(["icacls", str(private)])
        (private / "dacl-after-readback.private.txt").write_bytes(final_acl)
        if final_acl != acl:
            raise ValueError("Private boundary changed")
    result.update(private_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                  private_archive_members=len(manifest), private_boundary_before_payload=True,
                  all_members_readback=True, raw_private=True)
    public = (json.dumps(result, indent=2) + "\n").encode()
    scan(public)
    args.output.mkdir(mode=0o700)
    (args.output / "summary.json").write_bytes(public)
    print(json.dumps(result))
    return int(not result["accepted"])


if __name__ == "__main__":
    raise SystemExit(main())

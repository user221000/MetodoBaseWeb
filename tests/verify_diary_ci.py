"""Focused local CI wiring checks; no services, provider, browser or backend suite."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]
BASE = "7bde30b1877f3b4471ef5a75c47839ceaec209a9"


def command(args, **kwargs):
    return subprocess.run(args, capture_output=True, text=True, timeout=30, **kwargs)


def save(out, name, value):
    (out / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    bash = os.environ.get("METODOBASE_CI_BASH") or (
        "C:/Program Files/Git/bin/bash.exe" if os.name == "nt" else shutil.which("bash"))
    assert bash
    raw = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf8")
    old_raw = subprocess.check_output(["git", "show", BASE + ":.github/workflows/ci.yml"], cwd=ROOT).decode()
    workflow, old = yaml.safe_load(raw), yaml.safe_load(old_raw)
    assert {k: v for k, v in workflow.items() if k != "jobs"} == {k: v for k, v in old.items() if k != "jobs"}
    for name in old["jobs"]:
        if name not in ("frontend-contracts", "image"):
            assert workflow["jobs"][name] == old["jobs"][name], name
    previous_calls = [line for line in old_raw.splitlines() if line.strip().startswith("run_browser_fixture tests/")]
    calls = [line for line in raw.splitlines() if line.strip().startswith("run_browser_fixture tests/")]
    assert len(previous_calls) == 6 and calls[:6] == previous_calls and len(calls) == 7
    assert "personal_diary_server.py 8776 tests/e2e/personal_diary.cjs" in calls[-1]
    assert "17 named 8 tests/e2e/personal_export_context_browser.cjs" in calls[-1]
    assert calls[-1].endswith("4 strings 4 personal-diary-ui")
    assert "context_replay" not in raw and "personal_export_context_server" not in raw
    node_guard = lambda text: next(line for line in text.splitlines() if "Number.isSafeInteger" in line)
    assert node_guard(raw) == node_guard(old_raw)
    for name in ("scripts/check_frontend_report.py", "tests/test_frontend_report_guard.py"):
        historical = subprocess.check_output(["git", "show", BASE + ":" + name], cwd=ROOT)
        assert (ROOT / name).read_bytes().replace(b"\r\n", b"\n") == historical.replace(b"\r\n", b"\n")
    old_export = subprocess.check_output(["git", "show", BASE + ":tests/e2e/personal_export_context_browser.cjs"], cwd=ROOT).decode()
    export = (ROOT / "tests/e2e/personal_export_context_browser.cjs").read_text(encoding="utf8")
    assert export[export.index("const report="):] == old_export[old_export.index("const report="):]
    image_runs = [step for step in workflow["jobs"]["image"]["steps"] if not step.get("name", "").startswith("Generation, private branding")]
    old_image_runs = [step for step in old["jobs"]["image"]["steps"] if not step.get("name", "").startswith("Generation, private branding")]
    assert image_runs == old_image_runs
    blocks = []
    for job in workflow["jobs"].values():
        for step in job.get("steps", []):
            if "run" in step:
                result = subprocess.run([bash, "-n"], input=step["run"], capture_output=True, text=True)
                assert result.returncode == 0, result.stderr
                blocks.append(step["run"])
    refs = sorted(set(re.findall(r"(?:scripts|tests)/[A-Za-z0-9_./-]+\.(?:py|cjs)", raw)))
    assert all((ROOT / name).is_file() for name in refs)
    # Execute only the Node contracts and real report guard, never another workflow job.
    node_results = []
    steps = workflow["jobs"]["frontend-contracts"]["steps"]
    for step in steps:
        for line in step.get("run", "").splitlines():
            if line.startswith("node tests/e2e/"):
                parts = shlex.split(line)
                result = command(parts[:2], cwd=ROOT)
                assert result.returncode == 0, result.stderr
                (out / parts[3]).write_text(result.stdout, encoding="utf8")
                report = json.loads(result.stdout)
                count = report["total"] if "total" in report else len(report["report"])
                node_results.append({"driver": parts[1], "count": count})
            elif line.startswith("python scripts/check_frontend_report.py"):
                parts = shlex.split(line)
                result = command([sys.executable, str(ROOT / parts[1]), str(out / parts[2]), *parts[3:]], cwd=ROOT)
                assert result.returncode == 0, result.stderr
            elif line.startswith("node -e "):
                result = command(shlex.split(line), cwd=out)
                assert result.returncode == 0, result.stderr
    assert sum(row["count"] for row in node_results) == 162 and len(node_results) == 11
    assert not any(row["driver"].endswith("personal_export_context.cjs") for row in node_results)
    url_result = command(["node", "tests/e2e/personal_export_url_contract.cjs"], cwd=ROOT)
    assert url_result.returncode == 0, url_result.stderr
    save(out, "url-harness.json", json.loads(url_result.stdout))
    # Reuse the real CLI for each new format/minimum combination, not the91 old generic probes.
    cli_results = []
    for kind, minimum, screens in [("counts", n, 0) for n in (7, 18, 10, 12, 21)] + [("named", 17, 8), ("strings", 4, 4)]:
        rows = [{"case": str(n), "passed": True} for n in range(minimum)]
        positive = {"total": minimum, "passed": minimum, "results": rows} if kind == "counts" else {
            "checks": [{"name": str(n)} for n in range(minimum)] if kind == "named" else [str(n) for n in range(minimum)],
            "pageErrors": [], "screens": [str(n) for n in range(screens)]}
        for phase in ("positive", "short", "failed"):
            sample = json.loads(json.dumps(positive))
            if phase == "short":
                if kind == "counts":
                    sample["total"] -= 1; sample["passed"] -= 1; sample["results"].pop()
                else:
                    sample["checks"].pop()
            elif phase == "failed":
                if kind == "counts": sample["results"][0]["passed"] = False
                else: sample["pageErrors"] = ["synthetic"]
            path = out / f"cli-{kind}-{minimum}-{phase}.json"
            save(out, path.name, sample)
            result = command([sys.executable, str(ROOT / "scripts/check_frontend_report.py"), str(path), "--format", kind, "--minimum", str(minimum), "--minimum-screens", str(screens)])
            assert (result.returncode == 0) == (phase == "positive")
            cli_results.append({"format": kind, "minimum": minimum, "screens": screens, "case": phase, "exit": result.returncode})
    marker = {"fixture": "personal-diary-ui", "tables": 26, "model_target_revision": "20261019_personal_diary"}
    startup_results = []
    for name, text, success in [
        ("valid", json.dumps(marker), True), ("missing", "", False),
        ("malformed", '{"fixture":"personal-diary-ui",', False),
        ("wrong-tables", json.dumps({**marker, "tables": 25}), False),
        ("boolean-tables", json.dumps({**marker, "tables": True}), False),
        ("wrong-head", json.dumps({**marker, "model_target_revision": "20261018_individual_publication"}), False),
        ("wrong-fixture", json.dumps({**marker, "fixture": "other"}), False),
        ("duplicate", json.dumps(marker) + "\n" + json.dumps(marker), False),
    ]:
        path = out / ("startup-" + name + ".log"); path.write_text(text, encoding="utf8")
        result = command([sys.executable, str(ROOT / "scripts/check_browser_fixture_startup.py"), str(path), "--fixture", "personal-diary-ui", "--tables", "26", "--revision", "20261019_personal_diary"])
        assert (result.returncode == 0) == success
        startup_results.append({"case": name, "exit": result.returncode})
    block = next(value for value in blocks if "run_browser_fixture() {" in value)
    function = block[block.index("run_browser_fixture() {"):block.index("\nbrowser_evidence=")]
    (out / "exact-fixture-function.sh").write_text(function + "\n", encoding="utf8")
    inert = inert_cases(function, bash, out)
    report = {"scope": "Windows-local YAML/Bash syntax, actual Node162 and CLI report guards, inert fixture processes only; no Actions/Linux/browser/backend execution",
              "base": BASE, "six_calls_unchanged": True, "prior_guards_unchanged": True,
              "postgres_and_desktop_jobs_unchanged": True, "export_assertions_unchanged": True,
              "bash_blocks": len(blocks), "references": refs, "node_contracts": node_results,
              "node_unique_total": 162, "new_cli_cases": cli_results, "inert_cases": inert}
    report["startup_cli_cases"] = startup_results
    save(out, "review.json", report)
    print(json.dumps({"node": 162, "cli": len(cli_results), "inert": len(inert), "bash_blocks": len(blocks), "references": len(refs)}))


def inert_cases(function, bash, out):
    writer = out / "inert_writer.py"
    writer.write_text("import json,sys\nfrom pathlib import Path\np,kind,n,screens,bad=sys.argv[1:]\nn=int(n);screens=int(screens)\nr={'checks':[{'name':str(i)} if kind=='named' else str(i) for i in range(n)],'pageErrors':[],'screens':[str(i) for i in range(screens)]}\nif bad=='malformed':Path(p).write_text('{');raise SystemExit(0)\nif bad=='checks':r['checks'].pop()\nif bad=='screens':r['screens'].pop()\nPath(p).write_text(json.dumps(r))\n", encoding="utf8")
    prefix = r'''set -euo pipefail
browser_fixture_pid=''
seen_drivers=0
kill() { if [[ "$1" != '-0' ]]; then printf 'cleanup %s\n' "$1" >> "$CI_EVENTS"; fi; builtin kill "$@"; }
trap 'if [ -n "${browser_fixture_pid:-}" ]; then kill "$browser_fixture_pid" 2>/dev/null || true; fi' EXIT
python() {
 if [[ "$1" == '-X' ]]; then
  printf 'start %s\n' "$BASHPID" >> "$CI_EVENTS"
  case "$CI_MARKER" in
   valid) printf '%s\n' '{"fixture":"personal-diary-ui","tables":26,"model_target_revision":"20261019_personal_diary"}' ;;
   malformed) printf '%s\n' '{"fixture":"personal-diary-ui",' ;;
   wrong) printf '%s\n' '{"fixture":"personal-diary-ui","tables":25,"model_target_revision":"20261019_personal_diary"}' ;;
  esac
  exec /usr/bin/sleep 30
 elif [[ "$1" == 'scripts/check_browser_fixture_startup.py' ]]; then
  "$CI_PYTHON" "$CI_STARTUP" "${@:2}"
 else
  "$CI_PYTHON" "$CI_GUARD" "${@:2}"
 fi
}
node() {
 seen_drivers=$((seen_drivers+1))
 printf 'driver%s %s\n' "$seen_drivers" "$browser_fixture_pid" >> "$CI_EVENTS"
 if [[ "$CI_FAIL" == "$seen_drivers" ]]; then return 7; fi
 if [[ "$CI_MISSING" == "$seen_drivers" ]]; then return 0; fi
 if [[ "$seen_drivers" == 1 ]]; then
  "$CI_PYTHON" "$CI_WRITER" "$expected_report" "$report_format" "$minimum_checks" "$minimum_screens" good
  if [[ "$CI_DEAD" == 1 ]]; then builtin kill "$browser_fixture_pid"; wait "$browser_fixture_pid" || true; fi
 else
  "$CI_PYTHON" "$CI_WRITER" "$second_report" "$second_format" "$second_minimum" "$second_screens" "$CI_BAD"
 fi
}
curl() { [[ "$CI_NOT_READY" != 1 ]]; }
sleep() { /usr/bin/sleep 0.01; }
'''
    cases = [("old-default", {}, 0, False), ("two-drivers", {}, 0, True),
             ("missing-marker", {"CI_MARKER": "none"}, 1, True),
             ("malformed-marker", {"CI_MARKER": "malformed"}, 1, True),
             ("wrong-target", {"CI_MARKER": "wrong"}, 1, True),
             ("not-ready", {"CI_NOT_READY": "1"}, 1, True),
             ("first-driver-fails", {"CI_FAIL": "1"}, 7, True),
             ("second-driver-fails", {"CI_FAIL": "2"}, 7, True),
             ("second-report-missing", {"CI_MISSING": "2"}, 1, True),
             ("second-report-malformed", {"CI_BAD": "malformed"}, 1, True),
             ("second-checks-short", {"CI_BAD": "checks"}, 1, True),
             ("second-screens-short", {"CI_BAD": "screens"}, 1, True),
             ("fixture-exits-between-drivers", {"CI_DEAD": "1"}, 1, True)]
    results = []
    for name, changes, expected, paired in cases:
        directory = out / ("inert-" + name); directory.mkdir()
        (directory / "docs/implementation/20261018-evolution/evidence/ux").mkdir(parents=True)
        call = 'run_browser_fixture fixture.py 9999 first.cjs first.json 17 named 8 second.cjs second.json 4 strings 4 personal-diary-ui\n' if paired else 'run_browser_fixture fixture.py 9999 first.cjs first.json 9\n'
        script = directory / "probe.sh"; script.write_text(prefix + function + "\n" + call, encoding="utf8")
        env = dict(os.environ, CI_PYTHON=Path(sys.executable).as_posix(), CI_GUARD=(ROOT / "scripts/check_frontend_report.py").as_posix(), CI_STARTUP=(ROOT / "scripts/check_browser_fixture_startup.py").as_posix(), CI_WRITER=writer.as_posix(), CI_EVENTS=(directory / "events.txt").as_posix(), CI_MARKER="valid", CI_FAIL="0", CI_MISSING="0", CI_BAD="good", CI_NOT_READY="0", CI_DEAD="0")
        env.update(changes)
        run = command([bash, script.as_posix()], cwd=directory, env=env)
        assert run.returncode == expected, (name, run.returncode, run.stderr)
        events = (directory / "events.txt").read_text().splitlines()
        starts = [line for line in events if line.startswith("start ")]
        cleanup = [line for line in events if line.startswith("cleanup ")]
        assert len(starts) == len(cleanup) == 1 and starts[0].split()[1] == cleanup[0].split()[1], (name, events)
        if name == "two-drivers":
            drivers = [line for line in events if line.startswith("driver")]
            assert len(drivers) == 2 and all(line.split()[1] == starts[0].split()[1] for line in drivers)
        results.append({"case": name, "exit": run.returncode, "cleanup_count": len(cleanup), "events": events})
    return results


if __name__ == "__main__":
    main()

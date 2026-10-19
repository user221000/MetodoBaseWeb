"""Independent bounded CI diary wiring review; no product edits or services."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import yaml

ROOT = Path(r"F:\MetodoBaseWeb-diary-ci-20261019")
OUT = Path(__file__).resolve().parent
BASH = "C:/Program Files/Git/bin/bash.exe"
HEAD = "8435bd079ef5a48c081043ebe8efe542278143c4"
BASE = "7bde30b1877f3b4471ef5a75c47839ceaec209a9"
MANIFEST = ROOT / "docs/implementation/20261018-evolution/evidence/ci-diary-author-source.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    with (OUT / name).open("x", encoding="utf8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def run(command, **kwargs):
    return subprocess.run(command, capture_output=True, encoding="utf8", errors="strict", timeout=120, **kwargs)


def write_log(name, result):
    with (OUT / name).open("x", encoding="utf8") as stream:
        stream.write(result.stdout + result.stderr)


def packages(label):
    values = sorted(({"name": row.metadata["Name"], "version": row.version} for row in importlib.metadata.distributions()), key=lambda row: row["name"].lower())
    assert len(values) == 89
    check = run([sys.executable, "-m", "pip", "check"], cwd=ROOT)
    write_log(label + "-pip-check.log", check)
    assert check.returncode == 0
    save(label + "-packages.json", values)
    return values


assert run(["git", "rev-parse", "HEAD"], cwd=ROOT).stdout.strip() == HEAD
assert sha(MANIFEST) == "2cd1eb45b9e67736d1ac897993772761eb9a459ee226df37cac1c8aaf1040d46"
manifest = json.loads(MANIFEST.read_text(encoding="utf8"))
assert len(manifest["sources"]) == 6 and len(manifest["readonly_dependencies"]) == 81
expected = {**manifest["sources"], **manifest["readonly_dependencies"]}
assert all(sha(ROOT / name) == digest for name, digest in expected.items())
changes = run(["git", "diff", "--name-only", BASE, HEAD], cwd=ROOT).stdout.splitlines()
assert not any(name.split("/")[0] in {"web", "api", "core"} for name in changes)
inventory = sorted(set(changes + list(expected) + [str(MANIFEST.relative_to(ROOT)).replace("\\", "/")]))
before = {name: sha(ROOT / name) for name in inventory}
save("source-before.json", before)
package_before = packages("before")
temp = Path(tempfile.mkdtemp(prefix="metodobase-ci-diary-independent-"))
replayed = run([sys.executable, "-X", "utf8", "tests/verify_diary_ci.py", "--output", str(temp / "verifier")], cwd=ROOT)
write_log("author-verifier-replay.log", replayed)
assert replayed.returncode == 0, replayed.stderr
replay = json.loads((temp / "verifier/review.json").read_text())
assert replay["node_unique_total"] == 162 and len(replay["new_cli_cases"]) == 21 and len(replay["startup_cli_cases"]) == 8 and len(replay["inert_cases"]) == 13
shutil.copytree(temp / "verifier", OUT / "author-verifier-replay")
print("Author verifier repeated:162 Node;21 report CLI;8 startup;13 inert scenarios", flush=True)
startup = {"fixture": "personal-diary-ui", "tables": 26, "model_target_revision": "20261019_personal_diary"}
own_startup = [
    ("file-missing", None, False),
    ("utf8-invalid", b"\xff\xfe", False),
    ("health-only", b"HTTP health is ready 200\n", False),
    ("noise-plus-marker", ("ordinary log\n" + json.dumps(startup) + "\nordinary tail\n").encode(), True),
    ("embedded-marker-not-standalone", ("INFO " + json.dumps(startup)).encode(), False),
    ("nested-marker", json.dumps({"nested": startup}).encode(), False),
    ("array-marker", json.dumps([startup]).encode(), False),
    ("float-table-count", json.dumps({**startup, "tables": 26.0}).encode(), False),
    ("string-table-count", json.dumps({**startup, "tables": "26"}).encode(), False),
    ("missing-revision", json.dumps({"fixture": "personal-diary-ui", "tables": 26}).encode(), False),
    ("valid-and-conflicting-duplicate", (json.dumps(startup) + "\n" + json.dumps({**startup, "tables": 25})).encode(), False),
    ("foreign-marker-and-valid", (json.dumps({**startup, "fixture": "foreign"}) + "\n" + json.dumps(startup)).encode(), True),
]
startup_results = []
own = OUT / "own"
own.mkdir()
for name, payload, success in own_startup:
    path = own / (name + ".log")
    if payload is not None:
        path.write_bytes(payload)
    result = run([sys.executable, str(ROOT / "scripts/check_browser_fixture_startup.py"), str(path), "--fixture", "personal-diary-ui", "--tables", "26", "--revision", "20261019_personal_diary"])
    assert (result.returncode == 0) is success, name
    startup_results.append({"case": name, "expected_success": success, "exit": result.returncode})
save("own-startup-results.json", startup_results)
origin = run(["node", str(OUT / "own_origins.cjs")], cwd=ROOT, env=dict(os.environ, QA_CI_REPO=str(ROOT)))
write_log("own-origins.json", origin)
assert origin.returncode == 0
assert json.loads(origin.stdout)["passed"] == 21
workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf8"))
block = next(step["run"] for step in workflow["jobs"]["image"]["steps"] if "run_browser_fixture() {" in step.get("run", ""))
function = block[block.index("run_browser_fixture() {"):block.index("\nbrowser_evidence=")]
assert function.strip() == (temp / "verifier/exact-fixture-function.sh").read_text().strip()
writer = own / "writer.py"
writer.write_text("import json,sys\nfrom pathlib import Path\np,kind,n,screens,fault=sys.argv[1:]\nr={'checks':[{'name':'own-'+str(i)} if kind=='named' else 'own-'+str(i) for i in range(int(n))],'pageErrors':['synthetic'] if fault=='errors' else [],'screens':['own-'+str(i) for i in range(int(screens))]}\nPath(p).write_text(json.dumps(r))\n", encoding="utf8")
inert_cases = [("no-marker", 1, 0), ("delayed-marker", 0, 2), ("wrong-fixture", 1, 0), ("wrong-head", 1, 0), ("wrong-tables", 1, 0),
               ("second-exit23", 23, 2), ("second-missing", 1, 2), ("second-empty", 1, 2), ("second-page-errors", 1, 2), ("dead-after-first", 1, 1)]
inert_results = []
for name, expected_exit, expected_drivers in inert_cases:
    case = own / name
    case.mkdir()
    (case / "docs/implementation/20261018-evolution/evidence/ux").mkdir(parents=True)
    script = case / "probe.sh"
    script.write_text((OUT / "own_inert_prefix.sh").read_text() + "\n" + function + "\nrun_browser_fixture own-fixture.py 9998 first.cjs first.json 17 named 8 second.cjs second.json 4 strings 4 personal-diary-ui\n", encoding="utf8")
    env = dict(os.environ, QA_MODE=name, QA_EVENTS=(case / "events.txt").as_posix(), QA_PYTHON=Path(sys.executable).as_posix(),
               QA_STARTUP=(ROOT / "scripts/check_browser_fixture_startup.py").as_posix(), QA_GUARD=(ROOT / "scripts/check_frontend_report.py").as_posix(), QA_WRITER=writer.as_posix())
    result = run([BASH, script.as_posix()], cwd=case, env=env)
    with (case / "stdout.log").open("x", encoding="utf8") as stream:
        stream.write(result.stdout + result.stderr)
    events = (case / "events.txt").read_text().splitlines()
    starts = [line for line in events if line.startswith("start ")]
    cleanup = [line for line in events if line.startswith("cleanup ")]
    drivers = [line for line in events if line.startswith("driver")]
    assert result.returncode == expected_exit, (name, result.returncode, result.stderr)
    assert len(starts) == len(cleanup) == 1 and starts[0].split()[1] == cleanup[0].split()[1]
    assert len(drivers) == expected_drivers
    assert all(line.split()[1] == starts[0].split()[1] for line in drivers)
    if name == "delayed-marker":
        assert events.index("health3") < events.index("marker") < events.index(drivers[0])
    closed = run([BASH, "-c", 'for attempt in $(seq 1 10); do if ! kill -0 "$1" 2>/dev/null; then exit 0; fi; /usr/bin/sleep 0.02; done; exit 1', "qa-check", starts[0].split()[1]], cwd=case)
    assert closed.returncode == 0, (name, "Own inert sleep PID remained alive")
    inert_results.append({"case": name, "exit": result.returncode, "driver_count": len(drivers), "cleanup_count": len(cleanup), "own_pid_closed": True, "events": events})
save("own-inert-results.json", inert_results)
package_after = packages("after")
after = {name: sha(ROOT / name) for name in inventory}
save("source-after.json", after)
assert after == before and package_after == package_before
assert run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT).stdout.strip() == ""
report = {"accepted": True, "head": HEAD, "author_manifest_sha256": sha(MANIFEST), "sources": len(before), "sources_stable": True,
          "author_dependency_count": 81, "packages": 89, "packages_stable": True, "pip_check_before_after": 0,
          "repeated_author": {"node": 162, "report_cli": 21, "startup_cli": 8, "inert": 13, "origins": 15, "bash_blocks": 61, "references": len(replay["references"])},
          "own": {"startup_cli": len(startup_results), "origins": 21, "inert": len(inert_results), "closed_each_own_inert_pid": True},
          "temporary_verifier_output": str(temp / "verifier"), "product_diff_empty": True,
          "limits": ["Actual CLI/Node and inert Git Bash processes on Windows; no app, TCP listener, browser, PG, backend suite, native Linux or Actions execution.",
                     "Existing browser25 acceptance remains separate; the unchanged assertion body was not repeated.",
                     "Origin prelude tests validate allowed parameter strings, not operating-system network isolation."]}
save("ci-diary-independent-source.json", report)
print(json.dumps({"accepted": True, "stable_sources": len(before), "own_cli": len(startup_results), "own_origins": 21, "own_inert": len(inert_results), "summary_sha256": sha(OUT / "ci-diary-independent-source.json")}))

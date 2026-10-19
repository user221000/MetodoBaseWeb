"""Replay the focused CI27 routing review without services or provider I/O."""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import yaml

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(os.environ.get("CI27_REVIEW_OUTPUT", str(Path(__file__).resolve().parent)))
OUT.mkdir(parents=True, exist_ok=True)
WORKFLOW = ROOT / ".github/workflows/ci.yml"
NEW_REPORTS = ["pytest-postgres-diary-migrations.xml", "pytest-postgres-diary.xml"]
BASH = Path(r"C:\Program Files\Git\bin\bash.exe")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_json(name, data):
    with (OUT / name).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def save_text(name, value):
    with (OUT / name).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(value)


raw = WORKFLOW.read_text(encoding="utf-8")
workflow = yaml.safe_load(raw)
references = sorted(set(re.findall(r"(?:scripts|tests)/[A-Za-z0-9_./-]+\.(?:py|cjs)", raw)))
assert all((ROOT / name).is_file() for name in references)
sources = sorted(set(references + [
    ".github/workflows/ci.yml", "scripts/check_frontend_report.py", "tests/test_frontend_report_guard.py",
    "docs/implementation/20261018-evolution/evidence/ci27-author-source.json",
    "docs/implementation/20261018-evolution/evidence/ci27-desktop-windows-author.xml",
    "docs/implementation/20261018-evolution/evidence/ci27-desktop-windows-author.log",
    "docs/implementation/20261018-evolution/evidence/ci-desktop-routing-independent/ci-desktop-routing-independent-source.json",
    "docs/implementation/20261018-evolution/evidence/ci27-independent/review_ci27.py",
]))
before = {name: sha(ROOT / name) for name in sources}
save_json("ci27-independent-before-source.json", before)
historical = "tests/integration_backup_restore_postgres.py"
historical_git = subprocess.run(["git", "show", "HEAD:" + historical], cwd=ROOT, capture_output=True, check=True).stdout
assert (ROOT / historical).read_bytes().replace(b"\r\n", b"\n") == historical_git.replace(b"\r\n", b"\n")
head_workflow = yaml.safe_load(subprocess.run(["git", "show", "HEAD:.github/workflows/ci.yml"], cwd=ROOT, capture_output=True, check=True).stdout)
pg_steps = workflow["jobs"]["postgres"]["steps"]
pg_commands = [step["run"] for step in pg_steps if "--junitxml=pytest-postgres-" in step.get("run", "")]
pg_reports = [re.search(r"--junitxml=(\S+)", command).group(1) for command in pg_commands]
guard_command = next(step["run"] for step in pg_steps if step.get("name", "").startswith("Required PostgreSQL"))
guard_args = shlex.split(guard_command)
assert guard_args[:2] == ["python", "-c"]
assert len(pg_reports) == len(set(pg_reports)) == 19
assert guard_args[3:] == pg_reports
old_reports = [re.search(r"--junitxml=(\S+)", step["run"]).group(1)
               for step in head_workflow["jobs"]["postgres"]["steps"]
               if "--junitxml=pytest-postgres-" in step.get("run", "")]
assert len(old_reports) == 17
assert [name for name in pg_reports if name not in NEW_REPORTS] == old_reports
save_text("ci27-independent-postgres-guard.py", guard_args[2] + "\n")
guard_cases = []
positive_xml = '<testsuites><testsuite tests="1"><testcase classname="synthetic" name="required"/></testsuite></testsuites>'
bad_payloads = {
    "missing": None,
    "empty_report": '<testsuites><testsuite tests="0"/></testsuites>',
    "zero_bytes": "",
    "skipped": '<testsuites><testsuite><testcase name="required"><skipped/></testcase></testsuite></testsuites>',
    "failure": '<testsuites><testsuite><testcase name="required"><failure/></testcase></testsuite></testsuites>',
    "error": '<testsuites><testsuite><testcase name="required"><error/></testcase></testsuite></testsuites>',
    "malformed": '<testsuites><testsuite>',
}
with tempfile.TemporaryDirectory(prefix="metodobase-ci27-guard-") as directory:
    temp = Path(directory)
    for report in pg_reports:
        (temp / report).write_text(positive_xml, encoding="utf-8")
    cases = [("all_19_positive", None, None)] + [(kind, target, payload) for target in NEW_REPORTS for kind, payload in bad_payloads.items()]
    for kind, target, payload in cases:
        if target:
            if payload is None:
                (temp / target).unlink()
            else:
                (temp / target).write_text(payload, encoding="utf-8")
        result = subprocess.run([sys.executable, *guard_args[1:]], cwd=temp, capture_output=True, encoding="utf-8")
        expected_success = target is None
        assert (result.returncode == 0) is expected_success, (kind, target, result.returncode)
        guard_cases.append({"case": kind, "report": target, "exit": result.returncode,
                            "expected_success": expected_success, "matched": True,
                            "payload_sha256": None if payload is None else hashlib.sha256(payload.encode()).hexdigest()})
        if target:
            (temp / target).write_text(positive_xml, encoding="utf-8")
save_json("ci27-independent-guard-canaries.json", guard_cases)
bash_blocks = []
with tempfile.TemporaryDirectory(prefix="metodobase-ci27-syntax-") as directory:
    for job, config in workflow["jobs"].items():
        for index, step in enumerate(config.get("steps", [])):
            if "run" not in step:
                continue
            path = Path(directory) / (str(len(bash_blocks)) + ".sh")
            path.write_text(step["run"], encoding="utf-8")
            result = subprocess.run([str(BASH), "-n", path.as_posix()], capture_output=True, encoding="utf-8")
            assert result.returncode == 0, (job, index, result.stderr)
            bash_blocks.append({"job": job, "step": index, "exit": result.returncode})
assert len(bash_blocks) == 60
desktop = [step for step in workflow["jobs"]["test-desktop"]["steps"] if "--junitxml=pytest-desktop-packaging.xml" in step.get("run", "")]
assert len(desktop) == 2
assert {step["if"] for step in desktop} == {"runner.os == 'Windows'", "runner.os != 'Windows'"}
assert all("tests/test_desktop_packaging_ops10.py" in step["run"] for step in desktop)
for step in workflow["jobs"]["test-web"]["steps"]:
    if "--junitxml=pytest-web" in step.get("run", ""):
        assert "--ignore=tests/test_desktop_entrypoints.py" in step["run"]
restore = next(command for command in pg_commands if "--junitxml=pytest-postgres-restore.xml" in command)
restore_probe = "tests/integration_backup_restore_postgres.py::test_encrypted_pg_restore_preserves_rows_constraints_and_private_objects"
assert restore_probe in restore and "tests/integration_diary_restore_review.py" in restore
assert "test_release_schema_restore_preserves_migrations_rows_relationships_and_objects" not in restore
probe_module, probe_name = restore_probe.split("::")
assert any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == probe_name
           for node in ast.parse((ROOT / probe_module).read_text(encoding="utf-8")).body)
collections = {}
collect_commands = {"windows": next(step["run"] for step in desktop if step["if"] == "runner.os == 'Windows'"),
                    "linux_selection_on_windows": next(step["run"] for step in desktop if step["if"] != "runner.os == 'Windows'")}
for report in NEW_REPORTS + ["pytest-postgres-restore.xml"]:
    collect_commands[report.removesuffix(".xml")] = next(command for command in pg_commands if "--junitxml=" + report in command)
for label, command in collect_commands.items():
    args = [part for part in shlex.split(command) if not part.startswith("--junitxml=")]
    args[0] = sys.executable
    result = subprocess.run([*args, "--collect-only"], cwd=ROOT, capture_output=True, encoding="utf-8", errors="strict")
    save_text("ci27-independent-" + label + "-collection.log", result.stdout + result.stderr)
    assert result.returncode == 0, (label, result.stdout, result.stderr)
    nodes = [line for line in result.stdout.splitlines() if line.startswith("tests/") and "::" in line]
    assert nodes, label
    collections[label] = nodes
assert len(collections["windows"]) == 97
assert len(collections["linux_selection_on_windows"]) == 95
deselected = sorted(set(collections["windows"]) - set(collections["linux_selection_on_windows"]))
assert deselected == [
    "tests/test_desktop_entrypoints.py::test_new_batch_wrong_commit_from_other_cwd_preserves_files",
    "tests/test_desktop_entrypoints.py::test_new_portable_launcher_missing_package_never_installs",
]
assert all(sum("test_desktop_packaging_ops10.py::" in node for node in collections[label]) == 12
           for label in ("windows", "linux_selection_on_windows"))
assert len(collections["pytest-postgres-restore"]) == 2
author_xml = ET.parse(ROOT / "docs/implementation/20261018-evolution/evidence/ci27-desktop-windows-author.xml")
assert len(author_xml.findall(".//testcase")) == 97
assert not any(author_xml.findall(".//" + kind) for kind in ("failure", "error", "skipped"))
previous_review = json.loads((ROOT / "docs/implementation/20261018-evolution/evidence/ci-desktop-routing-independent/ci-desktop-routing-independent-source.json").read_text())
frontend_names = ["scripts/check_frontend_report.py", "tests/test_frontend_report_guard.py"]
assert all(before[name] == previous_review["after"][name] for name in frontend_names)
after = {name: sha(ROOT / name) for name in sources}
assert before == after, "Reviewed sources changed during execution"
save_json("ci27-independent-source.json", {
    "accepted": True, "before": before, "after": after, "stable": True,
    "source_references": references, "postgres_reports": pg_reports,
    "previous_17_report_order_preserved": True, "guard_canaries": len(guard_cases),
    "bash_blocks": bash_blocks, "collections": {name: len(nodes) for name, nodes in collections.items()},
    "windows_only_deselected": deselected, "ops10_on_both_targets": 12,
    "historical26_source_matches_head_blob": True,
    "frontend_guard_sources_unchanged_from_accepted_review": True,
    "reused_author_windows_execution": {"passed": 97, "skipped": 0},
    "limits": ["Collection ran locally on Windows; it does not demonstrate Linux execution.",
               "No PostgreSQL, browser, provider, image or Actions execution in this focused CI review.",
               "Previously accepted PostgreSQL27 and desktop execution remain separate evidence."]})
print(json.dumps({"accepted": True, "guard_canaries": len(guard_cases), "bash_blocks": len(bash_blocks),
                  "references": len(references), "stable_sources": len(sources),
                  "collections": {name: len(nodes) for name, nodes in collections.items()},
                  "source_sha256": sha(OUT / "ci27-independent-source.json")}))

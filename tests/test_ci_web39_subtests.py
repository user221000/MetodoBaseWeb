"""Real native pytest serial/n2 reports and adversarial current39 evidence."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import xml.etree.ElementTree as ET

import pytest
from _pytest.reports import TestReport as MainReport
from _pytest.subtests import SubtestContext, SubtestReport

from scripts.scan_secrets import _private_evidence
from tests.ci_web38.reports import require_exact_junit
from tests.ci_web39 import subtest_reports as reports
from tests.ci_web39.subtest_evidence import Observer

ROOT = Path(__file__).resolve().parents[1]
INERT = '''import unittest
import pytest
class TestNative(unittest.TestCase):
    def test_unit(self):
        for i in range(3):
            with self.subTest("unit", i=i): self.assertEqual(i, i)
    def test_repeated_context(self):
        for _ in range(2):
            with self.subTest("same", key="same"): self.assertTrue(True)
    def test_failure(self):
        for i in range(2):
            with self.subTest("failure", i=i): self.assertEqual(i, 0)
def test_fixture(subtests):
    for i in range(2):
        with subtests.test("fixture", i=i): assert i == i
def test_skip(subtests):
    with subtests.test("skip", marker="synthetic"): pytest.skip("synthetic skip")
'''
CHILD_DRIVER = r'''from pathlib import Path
import json, subprocess, sys
root, repository = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(repository))
from tests.isolation import prepare_environment, block_external_sockets
prepare_environment(discard_inherited=True)
block_external_sockets()
from tests.ci_web39 import subtest_reports as reports
import pytest
source = root / "test_child.py"
source.write_text('def test_child(subtests):\n    for i in range(2):\n        with subtests.test(i=i): assert i == i\n', encoding="utf8")
ini = root / "pytest.ini"
ini.write_text("[pytest]\n", encoding="utf8")
options = [str(source), "-c", str(ini), "--rootdir", str(root), "--noconftest", "-o", "cache_dir=" + str(root / "cache")]
oracle = root / "oracle.json"
with (root / "collection.private.log").open("xb") as output:
    code = subprocess.run([sys.executable, "-B", "-X", "utf8", str(repository / "tests/ci_web38/collect.py"),
        "--output", str(oracle), *options], cwd=repository, stdout=output, stderr=subprocess.STDOUT, check=False).returncode
assert code == 0
expected = json.loads(oracle.read_bytes())
assert len(expected) == 1
path, sha256 = reports.create_contract(root / "witness", expected, ["controller"])
code = pytest.main([*options, "-p", "tests.ci_web39.subtest_evidence", "--web39-subtest-contract", str(path),
    "--web39-subtest-contract-sha256", sha256, "--basetemp=" + str(root / "pytest-data"),
    "--junitxml=" + str(root / "pytest.xml"), "-q", "--tb=short"])
value = reports.require_exact_junit39((root / "pytest.xml").read_bytes(), expected, path, sha256, ["controller"], pytest_exit=int(code))
contract = reports.read_contract(path, sha256)
assert value["subtest_main_owners"] == 1 and value["subtests_passed"] == 2
value.update(run_id=contract["run_id"], output=contract["output"])
(root / "result.json").write_text(json.dumps(value), encoding="utf8")
raise SystemExit(int(code))
'''
OUTER_DRIVER = r'''from pathlib import Path
import json, os, subprocess, sys
import pytest
from scripts.scan_secrets import _private_evidence
from tests.ci_web39 import subtest_evidence
from tests.test_ci_web39_subtests import ROOT, environment
@pytest.mark.parametrize("ordinal", [1, 2])
def test_outer_after_owned_child(tmp_path, subtests, ordinal):
    original = subtest_evidence.observer
    assert original is not None
    with subtests.test(stage="before-child", ordinal=ordinal):
        assert subtest_evidence.observer is original
    before = dict(os.environ)
    child = _private_evidence(tmp_path / "owned-child")
    with (child / "runtime.private.log").open("xb") as output:
        code = subprocess.run([sys.executable, "-B", "-X", "utf8", str(Path(__file__).with_name("child_driver.py")),
            str(child), str(ROOT)], cwd=ROOT, env=environment(child), stdout=output, stderr=subprocess.STDOUT, check=False).returncode
    assert code == 0
    value = json.loads((child / "result.json").read_bytes())
    assert value["subtest_main_owners"] == 1 and value["subtests_passed"] == 2
    assert value["run_id"] != original.value["run_id"] and value["output"] != original.value["output"]
    assert dict(os.environ) == before and subtest_evidence.observer is original
    with subtests.test(stage="after-child", ordinal=ordinal):
        assert original.value["run_id"] != value["run_id"]
'''


@pytest.fixture(scope="module", autouse=True)
def database_schema():
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


def environment(directory, inherited=None):
    value = dict(os.environ if inherited is None else inherited,
                 PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1", PYTHONUTF8="1",
                 PYTHON_DOTENV_DISABLED="1", PYTHONPATH=str(ROOT))
    for name in list(value):
        if name.startswith("PYTEST_XDIST_") or name in {
            "PYTEST_CURRENT_TEST", "PYTEST_ADDOPTS", "PYTEST_PLUGINS", "METODOBASE_TEST_NATIVE35_V7_PROFILE",
        }:
            value.pop(name)
    value["_METODOBASE_TEST_ROOT"] = str(directory / "metodobase-test-child")
    value.update({name: str(directory) for name in ("TEMP", "TMP", "TMPDIR")})
    return value


def run(argv, directory):
    with (directory / "command.private.log").open("xb") as output:
        return subprocess.run(argv, cwd=ROOT, env=environment(directory), stdout=output,
                              stderr=subprocess.STDOUT, check=False).returncode


@pytest.fixture(scope="module")
def traces(tmp_path_factory):
    directory = _private_evidence(tmp_path_factory.mktemp("subtests39-inert") / "private")
    source = directory / "test_inert_subtests.py"
    source.write_text(INERT, encoding="utf8")
    ini = directory / "pytest.ini"
    ini.write_text("[pytest]\n", encoding="utf8")
    config = ["-c", str(ini), "--rootdir", str(directory), "--noconftest",
              "-o", "cache_dir=" + str(directory / "cache")]
    result = {}
    for label, names, actors in (
        ("serial", ["TestNative::test_unit", "TestNative::test_repeated_context", "test_fixture"], ["controller"]),
        ("parallel", ["TestNative::test_unit", "TestNative::test_repeated_context", "test_fixture"], ["gw0", "gw1"]),
        ("failed", ["TestNative::test_failure", "test_skip"], ["controller"]),
    ):
        phase = _private_evidence(directory / label)
        selected = [str(source) + "::" + name for name in names]
        collection = _private_evidence(phase / "collection")
        oracle = collection / "oracle.json"
        code = run([sys.executable, "-B", "-X", "utf8", str(ROOT / "tests/ci_web38/collect.py"),
                    "--output", str(oracle), *selected, *config], collection)
        assert code == 0
        expected = json.loads(oracle.read_bytes())
        contract, sha256 = reports.create_contract(phase / "witness", expected, actors)
        runtime = _private_evidence(phase / "runtime")
        argv = [sys.executable, "-B", "-X", "utf8", "-m", "pytest", *selected, *config,
                "-p", "tests.ci_web39.subtest_evidence", "--web39-subtest-contract", str(contract),
                "--web39-subtest-contract-sha256", sha256, "-q", "--tb=short",
                "--basetemp=" + str(runtime / "pytest-data"), "--junitxml=" + str(runtime / "pytest.xml")]
        if len(actors) == 2:
            argv += ["-n", "2"]
        code = run(argv, runtime)
        value = reports.read_contract(contract, sha256)
        streams = {actor: reports.read_actor(Path(value["output"]) / (actor + ".jsonl")) for actor in actors}
        result[label] = SimpleNamespace(path=contract, sha256=sha256, expected=expected,
            actors=actors, streams=streams, raw=(runtime / "pytest.xml").read_bytes(), exit=code)
    return result


def test_original_twenty_five_image_unittests_retain_all_eighty_real_subtests(tmp_path):
    directory = _private_evidence(tmp_path / "original-image-controls")
    selected = ["tests/test_ci_image57_offline.py", "tests/test_ci_image57_preflight_offline.py"]
    source_before = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in selected}
    ini = directory / "pytest.ini"
    ini.write_text("[pytest]\n", encoding="utf8")
    config = ["-c", str(ini), "--rootdir", str(ROOT), "--noconftest", "-o", "cache_dir=" + str(directory / "cache")]
    collection = _private_evidence(directory / "collection")
    oracle = collection / "oracle.json"
    assert run([sys.executable, "-B", "-X", "utf8", "tests/ci_web38/collect.py", "--output", str(oracle),
                *selected, *config], collection) == 0
    expected = json.loads(oracle.read_bytes())
    assert len(expected) == 25
    path, sha256 = reports.create_contract(directory / "witness", expected, ["controller"])
    runtime = _private_evidence(directory / "runtime")
    code = run([sys.executable, "-B", "-X", "utf8", "-m", "pytest", *selected, *config,
                "-p", "tests.ci_web39.subtest_evidence", "--web39-subtest-contract", str(path),
                "--web39-subtest-contract-sha256", sha256, "--basetemp=" + str(runtime / "pytest-data"),
                "--junitxml=" + str(runtime / "pytest.xml"), "-q", "--tb=short"], runtime)
    raw = (runtime / "pytest.xml").read_bytes()
    result = reports.require_exact_junit39(raw, expected, path, sha256, ["controller"], pytest_exit=code)
    assert code == 0 and result["subtest_main_owners"] == 25 and result["subtests_passed"] == 80
    assert result["junit_declared_total"] == 105 and len(list(ET.fromstring(raw).iter("testcase"))) == 25
    assert source_before == {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in selected}


@pytest.mark.parametrize("parallel", [False, True], ids=["serial", "n2"])
def test_real_nested_suites_keep_both_outer_subtests_and_separate_child_contracts(tmp_path, parallel):
    directory = _private_evidence(tmp_path / "nested-suite")
    for name, code in (("child_driver.py", CHILD_DRIVER), ("test_outer.py", OUTER_DRIVER)):
        compile(code, name, "exec")
        (directory / name).write_text(code, encoding="utf8")
    ini = directory / "pytest.ini"
    ini.write_text("[pytest]\n", encoding="utf8")
    selected = [str(directory / "test_outer.py"), "-c", str(ini), "--rootdir", str(directory), "--noconftest",
                "-o", "cache_dir=" + str(directory / "cache")]
    collection = _private_evidence(directory / "collection")
    oracle = collection / "oracle.json"
    assert run([sys.executable, "-B", "-X", "utf8", "tests/ci_web38/collect.py", "--output", str(oracle),
                *selected], collection) == 0
    expected = json.loads(oracle.read_bytes())
    assert len(expected) == 2
    actors = ["gw0", "gw1"] if parallel else ["controller"]
    path, sha256 = reports.create_contract(directory / "witness", expected, actors)
    runtime = _private_evidence(directory / "runtime")
    argv = [sys.executable, "-B", "-X", "utf8", "-m", "pytest", *selected,
            "-p", "tests.ci_web39.subtest_evidence", "--web39-subtest-contract", str(path),
            "--web39-subtest-contract-sha256", sha256, "--basetemp=" + str(runtime / "pytest-data"),
            "--junitxml=" + str(runtime / "pytest.xml"), "-q", "--tb=short"]
    if parallel:
        argv += ["-n", "2"]
    code = run(argv, runtime)
    result = reports.require_exact_junit39((runtime / "pytest.xml").read_bytes(), expected, path, sha256,
                                         actors, pytest_exit=code)
    assert result["subtest_main_owners"] == 2 and result["subtests_passed"] == 4
    assert result["junit_declared_total"] == 6


@pytest.mark.parametrize("label", ["serial", "parallel"])
def test_actual_native_serial_and_n2_preserve_three_main_ids_and_seven_subtests(traces, label):
    trace = traces[label]
    assert trace.exit == 0 and len(trace.expected) == 3
    result = reports.require_exact_junit39(trace.raw, trace.expected, trace.path, trace.sha256,
                                         trace.actors, pytest_exit=trace.exit)
    assert result == {"subtests_passed": 7, "subtest_main_owners": 3,
                      "junit_declared_total": 10, "subtest_evidence_complete": True}
    assert len(list(ET.fromstring(trace.raw).iter("testcase"))) == 3
    # The old contract remains strict and unchanged; no XML is repaired.
    with pytest.raises(ValueError, match="declared total"):
        require_exact_junit(trace.raw, trace.expected)
    repeated = [row for rows in trace.streams.values() for row in rows
                if row["event"] == "subtest" and "test_repeated_context" in row["nodeid"]]
    assert len(repeated) == 2 and repeated[0]["context_sha256"] == repeated[1]["context_sha256"]
    assert [row["ordinal"] for row in repeated] == [1, 2]


def fork_trace(trace, tmp_path):
    path, sha256 = reports.create_contract(tmp_path / "fork", trace.expected, trace.actors)
    contract = reports.read_contract(path, sha256)
    streams = copy.deepcopy(trace.streams)
    for rows in streams.values():
        rows[0].update(run_id=contract["run_id"], contract_sha256=sha256, binding=contract["binding"])
    return path, sha256, contract, streams


def save_streams(contract, streams, *, repair_sequences=True):
    for actor, rows in streams.items():
        if repair_sequences:
            for sequence, row in enumerate(rows, 1):
                row["sequence"] = sequence
            if rows and rows[-1]["event"] == "footer":
                rows[-1]["prior_events"] = len(rows) - 1
        with reports.exclusive_output(Path(contract["output"]) / (actor + ".jsonl")) as output:
            output.write(b"".join(reports.canonical(row) + b"\n" for row in rows))


@pytest.mark.parametrize("fault", [
    "missing-subtest", "duplicate-subtest", "failed-subtest", "skipped-subtest", "boolean-ordinal",
    "wrong-report-type", "foreign-node", "foreign-identity", "missing-owner", "duplicate-owner",
    "missing-footer", "false-footer-counter", "foreign-worker", "tool-binding", "truncated", "duplicate-JSON", "UTF16-JSON",
])
def test_observed_evidence_cannot_hide_omitted_failed_or_fabricated_children(traces, tmp_path, fault):
    trace = traces["serial"]
    path, sha256, contract, streams = fork_trace(trace, tmp_path)
    rows = streams["controller"]
    sub = next(row for row in rows if row["event"] == "subtest")
    closed = next(row for row in rows if row["event"] == "owner_closed")
    if fault == "missing-subtest":
        rows.remove([row for row in rows if row["event"] == "subtest" and row["nodeid"] == sub["nodeid"]][-1])
    elif fault == "duplicate-subtest":
        rows.insert(rows.index(sub) + 1, copy.deepcopy(sub))
    elif fault in {"failed-subtest", "skipped-subtest"}:
        sub["outcome"] = "failed" if fault == "failed-subtest" else "skipped"
    elif fault == "boolean-ordinal":
        sub["ordinal"] = True
    elif fault == "wrong-report-type":
        sub["report_class"] = reports.MAIN_CLASS
    elif fault == "foreign-node":
        sub["nodeid"] = "uncollected.py::test_counterfeit"
    elif fault == "foreign-identity":
        sub["identity"] = ["uncollected", "test_counterfeit"]
    elif fault == "missing-owner":
        rows.remove(closed)
    elif fault == "duplicate-owner":
        rows.insert(rows.index(closed) + 1, copy.deepcopy(closed))
    elif fault == "missing-footer":
        rows.pop()
    elif fault == "false-footer-counter":
        rows[-1]["subtests"] = 6
    elif fault == "foreign-worker":
        streams["gw9"] = copy.deepcopy(rows)
    elif fault == "tool-binding":
        rows[0]["binding"]["pytest"] = "unreviewed"
    save_streams(contract, streams)
    if fault == "truncated":
        actor = Path(contract["output"]) / "controller.jsonl"
        actor.write_bytes(actor.read_bytes()[:-1])
    elif fault in {"duplicate-JSON", "UTF16-JSON"}:
        actor = Path(contract["output"]) / "controller.jsonl"
        raw = actor.read_bytes()
        if fault == "duplicate-JSON":
            raw = raw.replace(b'{"binding":', b'{"sequence":1,"binding":', 1)
        else:
            raw = raw.decode("utf8").encode("utf-16-be")
        actor.write_bytes(raw)
    reasons = {
        "missing-subtest": "owner lifecycle or subtest count", "duplicate-subtest": "subtest ordinal",
        "failed-subtest": "subtest type, failure or skip", "skipped-subtest": "subtest type, failure or skip",
        "boolean-ordinal": "subtest ordinal", "wrong-report-type": "subtest type, failure or skip",
        "foreign-node": "owner cannot be mapped", "foreign-identity": "foreign owner identity",
        "missing-owner": "subtest owner never closed", "duplicate-owner": "duplicate or late owner event",
        "missing-footer": "complete successful closure", "false-footer-counter": "footer counters",
        "foreign-worker": "missing or foreign actor file", "tool-binding": "header or binding",
        "truncated": "truncated or noncanonical",
        "duplicate-JSON": "duplicate JSON field", "UTF16-JSON": "UTF-8 JSON required",
    }
    with pytest.raises(ValueError, match=reasons[fault]):
        reports.require_exact_junit39(trace.raw, trace.expected, path, sha256, trace.actors, pytest_exit=0)


@pytest.mark.parametrize("fault", ["hide-subtests", "duplicate-case", "missing-case", "failed-case", "skipped-case",
                                 "DTD", "UTF16-DTD", "UTF32-DTD", "non-UTF8-declaration"])
def test_real_junit_raw_cannot_be_relabelled_or_reduced(traces, fault):
    trace = traces["serial"]
    tree = ET.fromstring(trace.raw)
    suite = next(tree.iter("testsuite"))
    case = next(tree.iter("testcase"))
    if fault == "hide-subtests":
        suite.set("tests", "3")
    elif fault == "duplicate-case":
        suite.append(copy.deepcopy(case))
    elif fault == "missing-case":
        suite.remove(case)
    elif fault == "failed-case":
        ET.SubElement(case, "failure")
    elif fault == "skipped-case":
        ET.SubElement(case, "skipped")
    raw = ET.tostring(tree)
    if fault == "DTD":
        raw = b"<!DOCTYPE testsuites>" + raw
    elif fault in {"UTF16-DTD", "UTF32-DTD"}:
        raw = ('<!DOCTYPE testsuites [<!ENTITY probe "synthetic">]>' + raw.decode("utf8")).encode(
            "utf-16" if fault == "UTF16-DTD" else "utf-32")
    elif fault == "non-UTF8-declaration":
        raw = b'<?xml version="1.0" encoding="utf-16"?>' + raw
    with pytest.raises(ValueError):
        reports.require_exact_junit39(raw, trace.expected, trace.path, trace.sha256, trace.actors, pytest_exit=0)


def test_real_subtest_failure_and_skip_refuse_even_if_parent_exit_is_forged(traces, tmp_path):
    trace = traces["failed"]
    assert trace.exit != 0
    events = [row for rows in trace.streams.values() for row in rows if row["event"] == "subtest"]
    assert {row["outcome"] for row in events} == {"passed", "failed", "skipped"}
    with pytest.raises(ValueError, match="runtime exit"):
        reports.require_exact_junit39(trace.raw, trace.expected, trace.path, trace.sha256, trace.actors,
                                     pytest_exit=trace.exit)
    path, sha256, contract, streams = fork_trace(trace, tmp_path)
    for rows in streams.values():
        rows[-1]["exitstatus"] = 0
    save_streams(contract, streams)
    with pytest.raises(ValueError, match="subtest type, failure or skip"):
        reports.require_exact_junit39(trace.raw, trace.expected, path, sha256, trace.actors, pytest_exit=0)


def test_same_actual_subtest_report_object_cannot_be_reemitted(tmp_path):
    expected = [["inert.TestNative", "test_unit"]]
    path, sha256 = reports.create_contract(tmp_path / "repeat-report", expected, ["controller"])
    value = reports.read_contract(path, sha256)
    observer = Observer(value, sha256, "controller")
    item = SimpleNamespace(nodeid="inert.py::TestNative::test_unit", name="test_unit")
    observer.collection([item])
    observer.start(item)

    def report(phase):
        return MainReport(item.nodeid, ("inert.py", 0, "TestNative.test_unit"), {}, "passed", None, phase)

    observer.report(report("setup"))
    child = SubtestReport._new(report("call"), SubtestContext(msg="same", kwargs={"i": 1}), None, None)
    observer.report(child)
    observer.report(child)
    observer.report(report("call"))
    observer.report(report("teardown"))
    observer.finish(0)
    rows = reports.read_actor(Path(value["output"]) / "controller.jsonl")
    assert rows[-1]["issues"] == ["duplicate_subtest_report_object"]
    raw = b'<testsuite tests="2" errors="0" failures="0" skipped="0"><testcase classname="inert.TestNative" name="test_unit"/></testsuite>'
    with pytest.raises(ValueError, match="complete successful closure"):
        reports.require_exact_junit39(raw, expected, path, sha256, ["controller"], pytest_exit=0)


def test_contract_and_actor_are_exclusive_private_files_without_changing_umask(tmp_path):
    import stat

    expected = [["inert", "test_control"]]
    path, sha256 = reports.create_contract(tmp_path / "private-files", expected, ["controller"])
    value = reports.read_contract(path, sha256)
    actor = Path(value["output"]) / "controller.jsonl"
    with reports.exclusive_output(actor) as output:
        output.write(b"synthetic\n")
    with pytest.raises(FileExistsError):
        reports.exclusive_output(actor)
    if os.name == "posix":
        assert stat.S_IMODE(path.stat().st_mode) == stat.S_IMODE(actor.stat().st_mode) == 0o600
        actor.chmod(0o644)
        with pytest.raises(OSError, match="private_boundary_unavailable"):
            reports.read_actor(actor)
        actor.chmod(0o600)
    # File privacy is also revalidated on Windows, including nlink identity.
    alias = tmp_path / "second-link"
    os.link(actor, alias)
    with pytest.raises(OSError, match="private_boundary_unavailable"):
        reports.read_actor(actor)


def test_child_environment_clears_only_inherited_test_producer_state_without_global_changes(tmp_path):
    inherited = dict(os.environ, PYTEST_XDIST_WORKER="gw0", PYTEST_XDIST_WORKER_COUNT="2",
        PYTEST_XDIST_TESTRUNUID="outer-run", PYTEST_CURRENT_TEST="outer::case (call)",
        PYTEST_ADDOPTS="--web39-subtest-contract outer", PYTEST_PLUGINS="outer", KEEP_SYNTHETIC="preserved",
        _METODOBASE_TEST_ROOT="outer-test-root", TEMP="outer-temp", TMP="outer-temp", TMPDIR="outer-temp")
    before = dict(inherited)
    actual_environment = dict(os.environ)
    child = environment(tmp_path, inherited)
    assert inherited == before and dict(os.environ) == actual_environment
    assert not any(key.startswith("PYTEST_XDIST_") for key in child)
    assert not {"PYTEST_CURRENT_TEST", "PYTEST_ADDOPTS", "PYTEST_PLUGINS"} & child.keys()
    assert child["_METODOBASE_TEST_ROOT"] == str(tmp_path / "metodobase-test-child")
    assert all(child[name] == str(tmp_path) for name in ("TEMP", "TMP", "TMPDIR"))
    assert child["KEEP_SYNTHETIC"] == "preserved"


def test_real_child_isolation_requires_its_root_below_its_effective_private_temp(tmp_path):
    private = _private_evidence(tmp_path / "effective-child-temp")
    other = _private_evidence(tmp_path / "other-temp")
    before = dict(os.environ)
    child = environment(private)
    code = ("from pathlib import Path; import os,tempfile; "
            "from tests.isolation import prepare_environment; "
            "root=prepare_environment(discard_inherited=True); "
            "assert root.parent==Path(os.environ['_METODOBASE_TEST_ROOT']); "
            "assert root.is_relative_to(Path(tempfile.gettempdir()).resolve())")
    argv = [sys.executable, "-B", "-X", "utf8", "-c", code]
    accepted = subprocess.run(argv, cwd=ROOT, env=child, capture_output=True, check=False)
    assert accepted.returncode == 0, accepted.stderr
    refused = subprocess.run(argv, cwd=ROOT, env=dict(child, TEMP=str(other), TMP=str(other), TMPDIR=str(other)),
                             capture_output=True, check=False)
    assert refused.returncode != 0
    assert b"Test data root must be a dedicated temporary directory" in refused.stderr
    assert dict(os.environ) == before


@pytest.mark.parametrize("name", ["name::inside[param::value]", "name[back\\slash::parameter]"])
def test_owner_identity_uses_literal_item_name_instead_of_splitting_parameter_bytes(name):
    item = SimpleNamespace(nodeid="tests/inert.py::TestNative::" + name, name=name)
    assert reports.item_identity(item) == ["tests.inert.TestNative", name]


@pytest.mark.parametrize("suite,actors", [("serial", ["controller"]), ("parallel", ["gw0", "gw1"])])
def test_actual_current_runner_requires_bound_evidence_and_never_accepts_a_false_zero_exit(tmp_path, monkeypatch, traces, suite, actors):
    from tests.ci_web39 import run_web

    trace = traces["serial"]
    private = _private_evidence(tmp_path / "runner")
    calls = []

    def fake_process(argv, source, environment, log):
        calls.append(argv)
        if "--output" in argv:
            Path(argv[argv.index("--output") + 1]).write_text(json.dumps(trace.expected), encoding="utf8")
        else:
            assert "tests.ci_web39.subtest_evidence" in argv
            path = Path(argv[argv.index("--web39-subtest-contract") + 1])
            sha256 = argv[argv.index("--web39-subtest-contract-sha256") + 1]
            assert reports.read_contract(path, sha256)["workers"] == actors
            # A fabricated zero exit/XML cannot replace missing actual actors.
            tree = ET.fromstring(trace.raw)
            next(tree.iter("testsuite")).set("tests", "3")
            (private / "pytest.xml").write_bytes(ET.tostring(tree))
        return 0

    monkeypatch.setattr(run_web, "execute", fake_process)
    monkeypatch.setattr(run_web, "python_source_archive", lambda environment: None)
    for name in ("require_scanner_safety_companion", "require_native_expiry_replacement", "require_parent_companions"):
        monkeypatch.setattr(run_web, name, lambda rows: None)
    with pytest.raises(ValueError, match="missing or foreign actor file"):
        run_web.pytest_gate(private, {}, suite)
    assert len(calls) == 2

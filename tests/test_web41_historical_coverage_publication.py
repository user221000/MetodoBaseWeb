"""Measured coverage preservation, privacy and source-bound negative controls."""
import copy
import importlib.util
import io
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("typed_coverage_publication", ROOT / "tests/ci_web41/historical_coverage_publication.py")
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.PIPE)


def counters():
    return {"covered_lines": 2, "num_statements": 2, "percent_covered": 100.0,
            "percent_covered_display": "100.00", "missing_lines": 0, "excluded_lines": 0,
            "percent_statements_covered": 100.0, "percent_statements_covered_display": "100.00",
            "num_branches": 0, "num_partial_branches": 0, "covered_branches": 0, "missing_branches": 0,
            "percent_branches_covered": 100.0, "percent_branches_covered_display": "100.00"}


@pytest.fixture
def measured(tmp_path):
    root = tmp_path / "measured-source"
    root.mkdir()
    git(root, "init", "--initial-branch=measured-test")
    for name in ("tests/run_reviewed_ci30.py", "tests/ci_mfa31/publish.py"):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(git(ROOT, "show", "de506b6077ba055587f02e7d839387e7f5c56f84:" + name))
    (root / "requirements-test.lock").write_bytes(b"coverage==7.16.2 \\\n")
    (root / "core").mkdir()
    (root / "core/metric_fixture.py").write_bytes(b"def secret():\n    return 1\n")
    git(root, "-c", "core.autocrlf=false", "add", "--", ".")
    git(root, "-c", "user.name=Owned QA", "-c", "user.email=qa@example.invalid", "commit", "-m", "Measured fixture")
    commit = git(root, "rev-parse", "HEAD").decode().strip()
    directory = tmp_path / "private-measurements"
    directory.mkdir()
    row = {"executed_lines": [1, 2], "summary": counters(), "missing_lines": [], "excluded_lines": [],
           "executed_branches": [], "missing_branches": [], "functions": {"secret": {"SYNTHETIC_PRIVATE": "DO_NOT_PUBLISH"}}, "classes": {}}
    data = {"meta": {"format": 3, "version": "7.16.2", "timestamp": "2026-11-03T09:00:00",
                     "branch_coverage": True, "show_contexts": False},
            "files": {"core/metric_fixture.py": row}, "totals": counters()}
    xml = ET.Element("coverage", version="7.16.2", timestamp="1793696400000", **{
        "lines-valid": "2", "lines-covered": "2", "line-rate": "1", "branches-valid": "0", "branches-covered": "0", "branch-rate": "1", "complexity": "0"})
    ET.SubElement(ET.SubElement(xml, "sources"), "source").text = str(root / "core")
    package = ET.SubElement(ET.SubElement(xml, "packages"), "package", name=".", **{"line-rate": "1", "branch-rate": "1"})
    cls = ET.SubElement(ET.SubElement(package, "classes"), "class", name="metric_fixture.py", filename="metric_fixture.py", **{"line-rate": "1", "branch-rate": "1"})
    ET.SubElement(cls, "methods")
    lines = ET.SubElement(cls, "lines")
    for number in (1, 2):
        ET.SubElement(lines, "line", number=str(number), hits="1")
    (directory / "coverage.json").write_text(json.dumps(data), encoding="utf8")
    (directory / "coverage.xml").write_bytes(ET.tostring(xml, encoding="utf8"))
    (directory / "pytest-web.xml").write_bytes(b'<testsuite tests="1" failures="1"><testcase classname="tests.test_demo" name="test_visible"><failure message="PRIVATE_CANARY">PRIVATE_BODY</failure></testcase></testsuite>')
    return root, commit, directory, data


def test_original_scanner_stays_closed_and_projection_preserves_every_measurement(measured, tmp_path):
    root, commit, directory, data = measured
    scanner = gate.Sources(root, commit).scanner()
    with pytest.raises(ValueError):
        scanner["scan"]((directory / "coverage.json").read_bytes())
    before = {p.name: p.read_bytes() for p in directory.iterdir()}
    result = gate.publish(root, commit, directory, tmp_path / "public", ["coverage.json", "coverage.xml", "pytest-web.xml"])
    public = json.loads((tmp_path / "public/coverage.json").read_bytes())
    expected = copy.deepcopy(data)
    for row in expected["files"].values():
        row.pop("functions")
        row.pop("classes")
    assert public == expected and result["all_other_JSON_measurements_unchanged"]
    assert result["runtime_execution_attested"] is False and result["test_acceptance_inferred"] is False
    assert before == {p.name: p.read_bytes() for p in directory.iterdir()}
    for path in (tmp_path / "public").iterdir():
        scanner["scan"](path.read_bytes())
        assert b"PRIVATE_CANARY" not in path.read_bytes() and b"PRIVATE_BODY" not in path.read_bytes()
        assert b"SYNTHETIC_PRIVATE" not in path.read_bytes()
    junit = ET.fromstring((tmp_path / "public/pytest-web.xml").read_bytes())
    assert len(list(junit.iter("failure"))) == 1


@pytest.mark.parametrize("fault", ["counter", "bool-counter", "percentage", "display", "extra-field", "source-path", "line", "duplicate-line", "overlap", "arc", "format", "version", "timestamp", "no-execution", "false-excluded-eof"])
def test_fabricated_or_unbound_coverage_rejected_before_output(measured, tmp_path, fault):
    root, commit, directory, data = measured
    row = data["files"]["core/metric_fixture.py"]
    if fault == "counter":
        row["summary"]["covered_lines"] = 1
    elif fault == "bool-counter":
        row["summary"]["covered_lines"] = True
    elif fault == "percentage":
        row["summary"]["percent_covered"] = 99.0
    elif fault == "display":
        row["summary"]["percent_covered_display"] = "95.00"
    elif fault == "extra-field":
        row["extra_private"] = "NEVER_PUBLISH"
    elif fault == "source-path":
        data["files"]["../outside.py"] = data["files"].pop("core/metric_fixture.py")
    elif fault == "line":
        row["executed_lines"] = [1, 99999]
    elif fault == "duplicate-line":
        row["executed_lines"] = [1, 1]
    elif fault == "overlap":
        row["missing_lines"] = [1]
    elif fault == "arc":
        row["executed_branches"] = [[1, "PRIVATE_BRANCH"]]
    elif fault in {"format", "version", "timestamp"}:
        data["meta"][fault] = "PRIVATE_METADATA"
    elif fault == "false-excluded-eof":
        row["excluded_lines"] = [3]
    else:
        row["executed_lines"] = []
    (directory / "coverage.json").write_text(json.dumps(data), encoding="utf8")
    with pytest.raises(ValueError):
        gate.publish(root, commit, directory, tmp_path / "rejected", ["coverage.json", "coverage.xml"])
    assert not (tmp_path / "rejected").exists()


@pytest.mark.parametrize("fault", ["totals", "source", "filename", "hits", "private-attribute", "entity", "rate", "false-branch"])
def test_xml_substitution_never_publishes_unverified_measurements(measured, tmp_path, fault):
    root, commit, directory, _ = measured
    path = directory / "coverage.xml"
    xml = ET.fromstring(path.read_bytes())
    if fault == "totals":
        xml.set("lines-covered", "1")
    elif fault == "source":
        next(xml.iter("source")).text = str(tmp_path)
    elif fault == "filename":
        next(xml.iter("class")).set("filename", "unbound.py")
    elif fault == "hits":
        next(xml.iter("line")).set("hits", "0")
    elif fault == "private-attribute":
        xml.set("secret", "SYNTHETIC_PRIVATE")
    elif fault == "rate":
        next(xml.iter("class")).set("line-rate", "0.5")
    elif fault == "false-branch":
        first = next(xml.iter("line"))
        first.set("branch", "true")
        first.set("condition-coverage", "100% (1/1)")
    else:
        path.write_bytes(b'<!DOCTYPE coverage [<!ENTITY a "PRIVATE">]><coverage/>')
    if fault != "entity":
        path.write_bytes(ET.tostring(xml, encoding="utf8"))
    with pytest.raises(ValueError):
        gate.publish(root, commit, directory, tmp_path / "rejected", ["coverage.json", "coverage.xml"])
    assert not (tmp_path / "rejected").exists()


def test_physical_source_drift_is_not_hidden_by_git(measured, tmp_path):
    root, commit, directory, _ = measured
    (root / "core/metric_fixture.py").write_bytes(b"def forged():\n    return 1\n")
    with pytest.raises(ValueError, match="source bytes differ"):
        gate.publish(root, commit, directory, tmp_path / "rejected", ["coverage.json", "coverage.xml"])


def test_wrong_head_missing_pair_existing_output_and_hardlinked_inputs_reject(measured, tmp_path):
    root, commit, directory, _ = measured
    with pytest.raises(ValueError):
        gate.Sources(root, "0" * 40)
    with pytest.raises(ValueError):
        gate.publish(root, commit, directory, tmp_path / "missing-pair", ["coverage.json"])
    output = tmp_path / "exists"
    output.mkdir()
    with pytest.raises(ValueError):
        gate.publish(root, commit, directory, output, ["coverage.json", "coverage.xml"])
    (tmp_path / "alias.json").hardlink_to(directory / "coverage.json")
    with pytest.raises(ValueError):
        gate.publish(root, commit, directory, tmp_path / "hardlinked", ["coverage.json", "coverage.xml"])


def test_duplicate_json_keys_and_nonfinite_numbers_are_not_measurements():
    for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}'):
        with pytest.raises(ValueError):
            gate.unique_json(raw)


def test_excluded_terminal_ellipsis_eof_preserves_real_producer_semantics(measured):
    _, _, _, data = measured
    row = data["files"]["core/metric_fixture.py"]
    row["executed_lines"] = [1]
    row["excluded_lines"] = [2, 3]
    row["summary"].update(covered_lines=1, num_statements=1, excluded_lines=2)
    data["totals"] = dict(row["summary"])
    class SourceFixture:
        def code(self, name):
            if name == "requirements-test.lock":
                return b"coverage==7.16.2 \\\n"
            return b"class Store(Protocol):\n    def read(self): ...\n"
    raw, _ = gate.coverage_json(json.dumps(data).encode(), SourceFixture())
    public = json.loads(raw)
    assert public["files"]["core/metric_fixture.py"]["excluded_lines"] == [2, 3]
    assert public["totals"] == data["totals"]


def test_growing_input_read_is_bounded_before_rejecting(tmp_path, monkeypatch):
    path = tmp_path / "growing-input.json"
    path.write_bytes(b"x")
    monkeypatch.setattr(gate, "MAX_BYTES", 32)
    requested = []
    class GrowingStream(io.BytesIO):
        def read(self, size=-1):
            requested.append(size)
            assert size == 33
            return b"x" * 33
    original_open = Path.open
    def bounded_open(self, *args, **kwargs):
        return GrowingStream() if self == path else original_open(self, *args, **kwargs)
    monkeypatch.setattr(Path, "open", bounded_open)
    with pytest.raises(ValueError, match="input changed"):
        gate.plain(path)
    assert requested == [33]


def test_excessive_git_blob_rejects_before_capture(measured, monkeypatch):
    root, commit, _, _ = measured
    sources = gate.Sources(root, commit)
    original_git = sources.git
    requests = []
    def excessive(*args):
        requests.append(args)
        if args[:2] == ("cat-file", "-s"):
            return str(gate.MAX_BYTES + 1).encode() + b"\n"
        assert args[0] != "show", "oversized blob must not be captured"
        return original_git(*args)
    monkeypatch.setattr(sources, "git", excessive)
    with pytest.raises(ValueError, match="blob exceeds"):
        sources.code("core/metric_fixture.py")
    assert any(args[:2] == ("cat-file", "-s") for args in requests)

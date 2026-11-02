"""Adversarial diagnostic privacy and original-result preservation controls."""
import ast
import hashlib
import importlib.util
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from types import CodeType, FunctionType

import pytest

PAYLOAD = Path(__file__).resolve().parent
SOURCE = PAYLOAD / "ci_web41/web_failure_projection.py"
SPEC = importlib.util.spec_from_file_location("external_web_failure_projection", SOURCE)
projection = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(projection)


def _git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=True, timeout=15).stdout


@pytest.fixture
def repository(tmp_path):
    root = tmp_path / "owned-git"
    root.mkdir()
    _git(root, "init", "--initial-branch=owned-test")
    (root / "tests").mkdir()
    content = (
        b"raise RuntimeError('SYNTHETIC_IMPORT_CANARY_NEVER_EXECUTE')\n"
        b"def test_one(): pass\n"
        b"def test_two(): pass\n"
        b"class TestVisible:\n    def test_method(self): pass\n"
        b"class Hidden:\n    def test_method(self): pass\n"
        b"def helper():\n    def test_nested(): pass\n"
    )
    (root / "tests/test_case.py").write_bytes(content)
    (root / "tests/test_dynamic.py").write_bytes(b"from somewhere import test_dynamic\n")
    (root / ".gitattributes").write_bytes(b"*.py text eol=lf\n")
    _git(root, "-c", "core.autocrlf=false", "add", "--", ".")
    _git(root, "-c", "user.name=Owned QA", "-c", "user.email=qa@example.invalid", "commit", "-m", "Owned static fixture")
    source = _git(root, "rev-parse", "HEAD").decode().strip()
    photo = {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
             for name in ("tests/test_case.py", "tests/test_dynamic.py")}
    return root, source, photo


def _junit(rows):
    root = ET.Element("testsuite")
    for classname, name, outcome in rows:
        case = ET.SubElement(root, "testcase", classname=classname, name=name)
        if outcome != "passed":
            child = ET.SubElement(case, outcome, message="SYNTHETIC_MESSAGE_DO_NOT_PUBLISH")
            child.text = "SYNTHETIC_ASSERTION_BODY_DO_NOT_PUBLISH"
    return ET.tostring(root, encoding="utf8")


def _project(repository, rows, manifest=None):
    root, source, photo = repository
    if manifest is None:
        manifest = [[classname, name] for classname, name, _ in rows]
    return projection.project(_junit(rows), json.dumps(manifest).encode(), projection.GitSources(root, source, photo))


def test_parameters_and_assertions_never_escape_static_symbols(repository):
    marker = "SYNTHETIC_PARAMETER_DO_NOT_PUBLISH"
    rows = [("tests.test_case", "test_one[" + marker + "]", "failure"),
            ("tests.test_case.TestVisible", "test_method", "error"),
            ("tests.test_case", "test_two", "skipped"),
            ("tests.test_case", "test_one", "passed")]
    value = _project(repository, rows)
    public = json.dumps(value)
    assert all(item not in public for item in (marker, "SYNTHETIC_MESSAGE", "SYNTHETIC_ASSERTION", "SYNTHETIC_IMPORT"))
    assert value["counters"] == {"error": 1, "failure": 1, "passed": 1, "skipped": 1}
    assert value["runtime_code_attestation"] is False
    assert value["manifest_entries"] == value["reported_entries"] == 4
    symbols = value["locations"][0]["symbols"]
    assert {row["function"] for row in symbols} == {"test_one", "test_two", "test_method"}
    assert next(row for row in symbols if row["function"] == "test_method")["classes"] == ["TestVisible"]


def test_dynamic_nested_and_non_test_classes_only_get_module_counts(repository):
    rows = [("tests.test_dynamic", "test_dynamic", "failure"),
            ("tests.test_case.Hidden", "test_method", "error"),
            ("tests.test_case", "test_nested", "failure")]
    value = _project(repository, rows)
    assert len(value["locations"]) == 2
    assert sum(row["unresolved_symbol_count"] for row in value["locations"]) == 3
    assert all(row["symbols"] == [] for row in value["locations"])


def test_duplicate_report_entries_count_without_fabricating_unique_execution(repository):
    rows = [("tests.test_case", "test_one", "error")] * 2
    value = _project(repository, rows, [["tests.test_case", "test_one"]])
    assert value["reported_entries"] == 2 and value["manifest_entries"] == 1
    assert value["counters"]["duplicate_report_identity"] == 1
    assert value["counters"]["error"] == 2
    assert value["counters"]["ambiguous_report_identity"] == 2
    assert value["locations"] == []


def test_unknown_identity_cannot_publish_its_candidate_module(repository):
    rows = [("tests.test_case", "test_two[SYNTHETIC_FOREIGN_VALUE]", "failure")]
    value = _project(repository, rows, [["tests.test_case", "test_one"]])
    assert value["locations"] == [] and value["counters"]["unresolved_report_identity"] == 1
    assert "SYNTHETIC_FOREIGN_VALUE" not in json.dumps(value)


@pytest.mark.parametrize("classname,name", [
    ("/tests/test_case.py", "test_one"), ("tests..test_case", "test_one"),
    ("tests.test_case", "test_one[\\SYNTHETIC_CANARY]"),
    ("tests.test_case", "test_one[\nSYNTHETIC_CANARY]"),
    ("tests.test_case", "test_one[bad[nested]]"),
])
def test_untrusted_identity_cannot_escape_or_claim_a_symbol(repository, classname, name):
    value = _project(repository, [(classname, name, "failure")])
    assert not any(row["symbols"] for row in value["locations"])
    assert "SYNTHETIC_CANARY" not in json.dumps(value)


def test_ambiguous_module_mapping_is_unresolved(repository):
    root, _, _ = repository
    (root / "tests/test_case").mkdir()
    (root / "tests/test_case/test_shadow.py").write_bytes(b"def test_method(): pass\n")
    _git(root, "add", "--", "tests/test_case/test_shadow.py")
    _git(root, "-c", "user.name=Owned QA", "-c", "user.email=qa@example.invalid", "commit", "-m", "Ambiguous static module")
    source = _git(root, "rev-parse", "HEAD").decode().strip()
    photo = dict(repository[2], **{"tests/test_case/test_shadow.py": hashlib.sha256((root / "tests/test_case/test_shadow.py").read_bytes()).hexdigest()})
    value = _project((root, source, photo), [("tests.test_case.test_shadow", "test_method", "failure")])
    assert value["locations"] == [] and value["counters"]["unresolved_location"] == 1


@pytest.mark.parametrize("payload", [b'<!DOCTYPE testsuite [<!ENTITY item "CANARY">]><testsuite/>',
    '<!DOCTYPE testsuite [<!ENTITY item "CANARY">]><testsuite/>'.encode('utf16'), b'<other/>'])
def test_xml_rejects_entities_encodings_and_unknown_root(repository, payload):
    root, source, photo = repository
    with pytest.raises((ValueError, UnicodeError)):
        projection.project(payload, b'[["tests.test_case","test_one"]]', projection.GitSources(root, source, photo))


def test_duplicate_manifest_rejected(repository):
    with pytest.raises(ValueError):
        _project(repository, [("tests.test_case", "test_one", "failure")], [["tests.test_case", "test_one"]] * 2)


def test_repeated_outcome_markers_are_ambiguous(repository):
    root, source, photo = repository
    raw = b'<testsuite><testcase classname="tests.test_case" name="test_one"><failure/><failure/></testcase></testsuite>'
    value = projection.project(raw, b'[["tests.test_case","test_one"]]', projection.GitSources(root, source, photo))
    assert value["counters"] == {"ambiguous_outcome": 1}
    assert value["locations"] == []


def test_hostile_git_environment_and_replace_refs_cannot_change_authority(repository, monkeypatch, tmp_path):
    root, source, _photo = repository
    old_blob = _git(root, "rev-parse", source + ":tests/test_case.py").decode().strip()
    forged = subprocess.run(["git", "-C", str(root), "hash-object", "-w", "--stdin"],
                            input=b"def test_bogus(): pass\n", capture_output=True, check=True).stdout.decode().strip()
    _git(root, "replace", old_blob, forged)
    trace = tmp_path / "forbidden-trace.json"
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "wrong-repository"))
    monkeypatch.setenv("GIT_WORK_TREE", str(tmp_path))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.bare")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "true")
    monkeypatch.setenv("GIT_TRACE2_EVENT", str(trace))
    value = _project(repository, [("tests.test_case", "test_one", "failure")])
    assert value["locations"][0]["blob_sha1"] == old_blob
    assert value["locations"][0]["symbols"][0]["function"] == "test_one"
    assert not trace.exists()


def test_uncommitted_info_attributes_cannot_override_git_source_transport(repository):
    root, source, photo = repository
    info = root / ".git/info/attributes"
    info.write_bytes(b"*.py text eol=crlf\n")
    with pytest.raises(ValueError):
        projection.GitSources(root, source, photo)


def test_mutated_info_attributes_after_source_construction_are_rejected(repository):
    root, source, photo = repository
    sources = projection.GitSources(root, source, photo)
    (root / ".git/info/attributes").write_bytes(b"*.py -text\n")
    with pytest.raises(ValueError):
        projection.project(_junit([("tests.test_case", "test_one", "failure")]),
                           b'[["tests.test_case","test_one"]]', sources)


def test_source_changed_or_photograph_drift_cannot_authenticate(repository):
    root, source, photo = repository
    with pytest.raises(ValueError):
        projection.GitSources(root, "0" * 40, photo)
    value = _project((root, source, {**photo, "tests/test_case.py": "0" * 64}), [("tests.test_case", "test_one", "failure")])
    assert value["locations"] == []


def test_honest_whole_crlf_transport_only(repository):
    root, source, photo = repository
    altered = dict(photo)
    altered["tests/test_case.py"] = hashlib.sha256((root / "tests/test_case.py").read_bytes().replace(b"\n", b"\r\n")).hexdigest()
    value = _project((root, source, altered), [("tests.test_case", "test_one", "failure")])
    assert value["locations"][0]["symbols"][0]["function"] == "test_one"
    (root / ".gitattributes").write_bytes(b"*.py -text\n")
    _git(root, "add", "--", ".gitattributes")
    _git(root, "-c", "user.name=Owned QA", "-c", "user.email=qa@example.invalid", "commit", "-m", "Explicit raw transport")
    new_source = _git(root, "rev-parse", "HEAD").decode().strip()
    rejected = _project((root, new_source, altered), [("tests.test_case", "test_one", "failure")])
    assert rejected["locations"] == []


def test_size_row_and_ast_limits_reject(repository, monkeypatch):
    root, source, photo = repository
    sources = projection.GitSources(root, source, photo)
    raw = _junit([("tests.test_case", "test_one", "failure")])
    monkeypatch.setattr(projection, "MAX_REPORT", 1)
    with pytest.raises(ValueError):
        projection.project(raw, b'[["tests.test_case","test_one"]]', sources)
    monkeypatch.setattr(projection, "MAX_REPORT", 10000)
    monkeypatch.setattr(projection, "MAX_ROWS", 1)
    with pytest.raises(ValueError):
        projection.project(raw, b'[["tests.test_case","test_one"],["tests.test_case","test_two"]]', sources)


def test_real_private_files_require_matching_manifest_and_reject_hardlinks(repository, tmp_path):
    root, source, photo = repository
    private = tmp_path / "private"
    private.mkdir()
    report = private / "pytest.xml"
    report.write_bytes(_junit([("tests.test_case", "test_one", "failure")]))
    expected = [["tests.test_case", "test_one"]]
    (private / "oracle.json").write_text(json.dumps(expected), encoding="utf8")
    (private / "before.json").write_text(json.dumps({"source": {"HEAD": source, "files": photo}}), encoding="utf8")
    value = projection.project_files(root, report, expected)
    assert value["diagnostic_available"] is True
    with pytest.raises(ValueError):
        projection.project_files(root, report, [["tests.test_case", "test_two"]])
    alias = private / "alias.xml"
    alias.hardlink_to(report)
    with pytest.raises(ValueError):
        projection.plain_bytes(report, 10000)


def _wrapper(original, projector):
    tree = ast.parse((PAYLOAD / "ci_web41/run_web.py").read_bytes())
    node, = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "observe_junit"]
    namespace = {"_original_observe_junit": original, "_project_files": projector, "_runner_root": None}
    module_code = compile(ast.Module(body=[node], type_ignores=[]), "<reviewed-wrapper-function>", "exec")
    function_code, = [code for code in module_code.co_consts if isinstance(code, CodeType) and code.co_name == "observe_junit"]
    return FunctionType(function_code, namespace)


def test_wrapper_preserves_rejection_and_never_turns_diagnostic_error_into_acceptance():
    original = {"identities_exact": False, "failed": 2, "errors": 1, "skipped": 0, "passed": 5}
    def reject(*args):
        raise RuntimeError("SYNTHETIC_EXCEPTION_DO_NOT_PUBLISH")
    value = _wrapper(lambda *args: dict(original), reject)(None, [])
    assert {key: value[key] for key in original} == original
    assert value["failure_locations"] == {"diagnostic_available": False, "reason": "projection_rejected"}
    assert "SYNTHETIC_EXCEPTION" not in json.dumps(value)


def test_wrapper_keeps_success_free_of_diagnostic_dependency():
    original = {"identities_exact": True, "failed": 0, "errors": 0, "skipped": 0, "passed": 1}
    def forbidden(*args):
        pytest.fail("Successful original gate must not invoke diagnostics")
    assert _wrapper(lambda *args: dict(original), forbidden)(None, []) == original


def test_original_parser_error_is_preserved():
    def reject(*args):
        raise ValueError("SYNTHETIC_ORIGINAL_REJECTION")
    with pytest.raises(ValueError):
        _wrapper(reject, lambda *args: {})(None, [])

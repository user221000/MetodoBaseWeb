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


def _long_case(kind):
    if kind == "nutrition":
        function = "test_corrupt_stored_declarations_fail_instead_of_becoming_unknown"
        return "tests.test_nutrition35_profile_contract", function + "[" + " " * 16385 + "]"
    function = "test_documented_transport_rejections_do_not_reach_provider"
    factory = {"api": "api.app", "web": "web.main_web"}[kind]
    return "tests.test_web_api_contract_audit", function + "[" + factory + "-request-" + " " * 4097 + "-application/json-413]"


@pytest.fixture
def long_repository(tmp_path):
    """Use exact reviewed test blobs, never importing their data or fixtures."""
    root = tmp_path / "owned-long-git"
    root.mkdir()
    (root / "tests").mkdir()
    _git(root, "init", "--initial-branch=owned-long-test")
    photo = {}
    for name in ("tests/test_nutrition35_profile_contract.py", "tests/test_web_api_contract_audit.py"):
        raw = _git(PAYLOAD.parent, "show", "HEAD:" + name)
        (root / name).write_bytes(raw)
        photo[name] = hashlib.sha256(raw).hexdigest()
    (root / ".gitattributes").write_bytes(b"*.py text eol=lf\n")
    _git(root, "-c", "core.autocrlf=false", "add", "--", ".")
    _git(root, "-c", "user.name=Owned QA", "-c", "user.email=qa@example.invalid", "commit", "-m", "Reviewed long-identity source")
    return root, _git(root, "rev-parse", "HEAD").decode().strip(), photo


@pytest.mark.parametrize("kind", ["nutrition", "api", "web"])
def test_reviewed_long_identity_uses_only_authenticated_short_symbol(long_repository, kind):
    classname, name = _long_case(kind)
    root, source, photo = long_repository
    sources = projection.GitSources(root, source, photo)
    # The ordinary4096 lookup remains closed even for a registered full ID.
    assert sources.location(classname, name) is None
    value = _project(long_repository, [(classname, name, "failure")])
    assert value["counters"] == {"failure": 1}
    assert value["locations"][0]["path"] == classname.replace(".", "/") + ".py"
    assert value["locations"][0]["symbols"] == [{"classes": [], "function": name.split("[", 1)[0], "outcome": "failure", "count": 1}]
    public = json.dumps(value)
    assert name not in public and " " * 4097 not in public
    assert "SYNTHETIC_MESSAGE" not in public and "SYNTHETIC_ASSERTION" not in public
    assert value["runtime_code_attestation"] is False


@pytest.mark.parametrize("kinds", [("api", "web"), ("nutrition", "api", "web")], ids=["audit-subset", "all-three"])
def test_passed_long_oracle_members_do_not_hide_an_ordinary_failure(long_repository, kinds):
    rows = [(*_long_case(kind), "passed") for kind in kinds]
    rows.append(("tests.test_web_api_contract_audit", "test_each_method_path_has_one_effective_handler_and_openapi_matches[api.app]", "failure"))
    value = _project(long_repository, rows)
    assert value["counters"] == {"failure": 1, "passed": len(kinds)}
    assert value["manifest_entries"] == value["reported_entries"] == len(rows)
    assert value["locations"][0]["symbols"][0]["function"] == "test_each_method_path_has_one_effective_handler_and_openapi_matches"


@pytest.mark.parametrize("kind", ["nutrition", "api", "web"])
@pytest.mark.parametrize("fault", ["same-length-parameter", "length", "classname", "symbol"])
def test_long_identity_mutation_never_inherits_the_finite_admission(long_repository, kind, fault):
    classname, name = _long_case(kind)
    if fault == "same-length-parameter":
        name = name[:-2] + "X" + name[-1]
    elif fault == "length":
        name += "X"
    elif fault == "classname":
        classname += "X"
    else:
        name = name.replace("test_", "fake_", 1)
    with pytest.raises(ValueError, match="Unsupported long diagnostic identity") as rejected:
        _project(long_repository, [(classname, name, "passed")])
    assert name not in str(rejected.value)


def test_fourth_long_identity_rejects_even_if_all_reported_tests_pass(long_repository):
    rows = [(*_long_case(kind), "passed") for kind in ("nutrition", "api", "web")]
    classname, name = _long_case("api")
    rows.append((classname, name[:-2] + "X]", "passed"))
    with pytest.raises(ValueError, match="Unsupported long diagnostic identity"):
        _project(long_repository, rows)


def test_duplicate_long_manifest_still_rejects_and_report_duplicates_keep_counts(long_repository):
    classname, name = _long_case("api")
    with pytest.raises(ValueError, match="Ambiguous diagnostic manifest"):
        _project(long_repository, [(classname, name, "passed")], [[classname, name]] * 2)
    value = _project(long_repository, [(classname, name, "error")] * 2, [[classname, name]])
    assert value["counters"] == {"ambiguous_report_identity": 2, "duplicate_report_identity": 1, "error": 2}
    assert value["locations"] == []


def test_foreign_long_report_identity_is_unresolved_without_publishing_parameters(long_repository):
    classname, name = _long_case("api")
    foreign = name[:-2] + "X]"
    value = _project(long_repository, [(classname, foreign, "failure")], [[classname, name]])
    assert value["counters"] == {"failure": 1, "unresolved_report_identity": 1}
    assert value["locations"] == [] and foreign not in json.dumps(value)


@pytest.mark.parametrize("kind", ["nutrition", "api"])
def test_new_git_and_photo_cannot_reapprove_changed_long_source(long_repository, kind):
    root, _, photo = long_repository
    classname, name = _long_case(kind)
    path = classname.replace(".", "/") + ".py"
    raw = (root / path).read_bytes() + b"\n# Synthetic unauthenticated comment\n"
    (root / path).write_bytes(raw)
    _git(root, "add", "--", path)
    _git(root, "-c", "user.name=Owned QA", "-c", "user.email=qa@example.invalid", "commit", "-m", "Unreviewed source")
    new_source = _git(root, "rev-parse", "HEAD").decode().strip()
    with pytest.raises(ValueError, match="Unreviewed long diagnostic source"):
        _project((root, new_source, {**photo, path: hashlib.sha256(raw).hexdigest()}), [(classname, name, "passed")])


def test_long_source_photo_and_symbol_must_be_authenticated(long_repository, monkeypatch):
    root, source, photo = long_repository
    classname, name = _long_case("api")
    path = "tests/test_web_api_contract_audit.py"
    with pytest.raises(ValueError, match="Photographed source differs"):
        _project((root, source, {**photo, path: "0" * 64}), [(classname, name, "passed")])
    original = projection.GitSources.location
    def unresolved(self, *args):
        value = original(self, *args)
        if value is not None:
            value = {**value, "symbol": None}
        return value
    monkeypatch.setattr(projection.GitSources, "location", unresolved)
    with pytest.raises(ValueError, match="Unresolved long diagnostic symbol"):
        _project(long_repository, [(classname, name, "passed")])


def test_real_private_file_projection_accepts_known_long_subset_without_changing_bytes(long_repository, tmp_path):
    root, source, photo = long_repository
    private = tmp_path / "long-private"
    private.mkdir()
    rows = [(*_long_case(kind), "passed") for kind in ("api", "web")]
    expected = [[classname, name] for classname, name, _ in rows]
    (private / "pytest.xml").write_bytes(_junit(rows))
    (private / "oracle.json").write_text(json.dumps(expected), encoding="utf8")
    (private / "before.json").write_text(json.dumps({"source": {"HEAD": source, "files": photo}}), encoding="utf8")
    before = {path.name: path.read_bytes() for path in private.iterdir()}
    value = projection.project_files(root, private / "pytest.xml", expected)
    assert value["diagnostic_available"] is True and value["counters"] == {"passed": 2}
    assert value["locations"] == [] and value["manifest_entries"] == value["reported_entries"] == 2
    assert before == {path.name: path.read_bytes() for path in private.iterdir()}


def test_general_long_boundary_and_all_global_limits_remain_closed(repository):
    assert (projection.MAX_REPORT, projection.MAX_MANIFEST, projection.MAX_PHOTO,
            projection.MAX_ROWS, projection.MAX_XML_NODES) == (64 * 1024**2, 8 * 1024**2, 16 * 1024**2, 20000, 200000)
    assert len(projection.LONG_IDENTITIES) == 3
    with pytest.raises(ValueError, match="Unsupported long diagnostic identity"):
        _project(repository, [("tests.test_case", "test_one[" + "X" * 4097 + "]", "passed")])

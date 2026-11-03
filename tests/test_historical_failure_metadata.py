"""Offline privacy/provenance and unchanged-finalizer controls; no SQL/browser."""
from __future__ import annotations

import ast
import builtins
import hashlib
import json
import os
import re
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path
from types import FunctionType, SimpleNamespace

import pytest

from tests.ci_web41 import historical_failure_metadata as meta
from tests.ci_web41 import historical_image_runtime as runtime
from tests.ci_web41 import historical_member_diagnostic as member

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module", autouse=True)
def database_schema():
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


@pytest.fixture(scope="module")
def sources():
    result = {}
    for schema, spec in meta.SOURCES.items():
        result[schema] = {name: subprocess.check_output(
            ["git", "--no-replace-objects", "show", spec["commit"] + ":" + name], cwd=ROOT)
            for name in spec["files"]}
    result["cjs31"] = {name: subprocess.check_output(
        ["git", "--no-replace-objects", "show", meta.SOURCES["31"]["commit"] + ":" + name], cwd=ROOT)
        for name in meta.CJS_SOURCES["31"]}
    return result


def source_tree(root, schema, sources):
    root.mkdir(mode=0o700)
    for name, raw in sources[schema].items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    if schema == "31":
        for name, raw in sources["cjs31"].items():
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
    return root


@pytest.fixture
def quota(tmp_path, sources):
    return meta.SourceRegistry(source_tree(tmp_path / "source30", "30", sources), "30")


def quota_xml(registry, secret="synthetic-private-value"):
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite", tests="3", failures="3", errors="0", skipped="0")
    for name in meta.QUOTA_CASES:
        case = ET.SubElement(suite, "testcase", classname="tests.integration_quota_postgres", name=name)
        function = next(node for node in registry.trees["tests/integration_quota_postgres.py"].body
                        if isinstance(node, ast.FunctionDef) and node.name == name.split("[")[0])
        line = next(node.lineno for node in ast.walk(function) if isinstance(node, ast.Assert))
        ET.SubElement(case, "failure", message=secret).text = (
            f"tests/integration_quota_postgres.py:{line}: in {function.name}\nE   AssertionError: " + secret)
        ET.SubElement(case, "system-out").text = secret
    return ET.tostring(root)


def test_exact17_original_sources_and_closed_three_historical_commits(sources, tmp_path):
    assert {schema: len(spec["files"]) for schema, spec in meta.SOURCES.items()} == {"30": 1, "31": 8, "33": 8}
    for schema, spec in meta.SOURCES.items():
        registry = meta.SourceRegistry(source_tree(tmp_path / ("source" + schema), schema, sources), schema)
        assert registry.quiet()
        for name, raw in sources[schema].items():
            assert hashlib.sha256(raw).hexdigest() == spec["files"][name]["sha256"]
            assert raw == registry.raw[name]


@pytest.mark.parametrize("schema", ["30", "31", "33"])
def test_each_source_byte_drift_is_rejected_before_observation(tmp_path, sources, schema):
    root = source_tree(tmp_path / "source", schema, sources)
    for name in sources[schema]:
        path = root / name
        original = path.read_bytes()
        path.write_bytes(bytes([original[0] ^ 1]) + original[1:])
        with pytest.raises(ValueError, match="source differs"):
            meta.SourceRegistry(root, schema)
        path.write_bytes(original)


@pytest.mark.parametrize("schema", [None, 31, "32", " 31", "31 ", ""])
def test_unreviewed_schema_never_enters_registry(tmp_path, schema):
    with pytest.raises(ValueError):
        meta.SourceRegistry(tmp_path, schema)


def test_quota_preserves_three_exact_identities_but_no_private_values(quota, tmp_path):
    secret = "synthetic-private-" + uuid.uuid4().hex
    raw = quota_xml(quota, secret)
    log = ("SQL https://example.invalid/" + secret + "\naccess_token=" + secret).encode()
    value = meta.quota_bytes(quota, raw, log)
    assert value["diagnostic_accepted"] and value["source_unchanged"]
    assert [row["name"] for row in value["cases"]] == list(meta.QUOTA_CASES)
    assert {row["outcome"] for row in value["cases"]} == {"failure"}
    assert {row["exception_type"] for row in value["cases"]} == {"AssertionError"}
    assert value["origin"] == "private_xml_projection"
    assert {row["origin"] for row in value["private_artifacts"]} == {"private_text_projection"}
    output = tmp_path / "sanitized.json"
    meta.write_metadata(output, quota, value)
    published = output.read_text()
    assert secret not in published and "https://" not in published and "access_token" not in published
    assert value["private_artifacts"][0]["sha256"] == hashlib.sha256(raw).hexdigest()
    if os.name == "posix":
        assert output.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("fault", ["duplicate", "missing", "foreign", "outcome", "DTD", "entity", "oversize"])
def test_quota_unknown_duplicate_incomplete_or_executable_xml_is_rejected(quota, fault):
    raw = quota_xml(quota)
    tree = ET.fromstring(raw)
    suite = tree.find("testsuite")
    if fault == "duplicate":
        suite.append(deepcopy(suite[0]))
    elif fault == "missing":
        suite.remove(suite[0])
    elif fault == "foreign":
        suite[0].set("name", "unreviewed-private-identity")
    elif fault == "outcome":
        ET.SubElement(suite[0], "error")
    elif fault in {"DTD", "entity"}:
        raw = (b'<!DOCTYPE testsuites>' if fault == "DTD" else b'<!ENTITY forbidden "private">') + raw
    else:
        raw = b"x" * (meta.MAX_PRIVATE + 1)
    if fault not in {"DTD", "entity", "oversize"}:
        raw = ET.tostring(tree)
    with pytest.raises(ValueError):
        meta.quota_bytes(quota, raw, b"")


def test_redacted_xml_cannot_claim_observed_locations(quota):
    tree = ET.fromstring(quota_xml(quota))
    for node in tree.iter("failure"):
        node.text = "redacted"
    result = meta.quota_bytes(quota, ET.tostring(tree), b"")
    assert not result["diagnostic_accepted"] and result["issues"] == ["unmapped_failure"]


@pytest.mark.parametrize("fault", ["line-zero", "line-huge", "foreign-root", "foreign-path", "synthetic"])
def test_text_frame_needs_exact_source_membership_and_real_ast_line(quota, fault):
    name = "tests/integration_quota_postgres.py"
    line = 125
    if fault == "line-zero":
        line = 0
    elif fault == "line-huge":
        line = 999999
    elif fault == "foreign-root":
        name = "/unreviewed/private/" + name
    elif fault == "foreign-path":
        name = "tests/unreviewed.py"
    else:
        name = "<synthetic>"
    result = quota.project_text(f'  File "{name}", line {line}, in test_control\nValueError: private'.encode())
    assert result["frames"] == []
    assert result["exception_types"] == ["ValueError"]


def test_builtin_identity_and_text_projection_cannot_publish_custom_class_names():
    counterfeit = type("ValueError", (Exception,), {})
    assert meta.exception_kind(counterfeit("private")) == "OTHER"
    assert meta.exception_kind(ValueError("private")) == "ValueError"


@pytest.mark.parametrize("fault", ["message", "frame", "span", "kind", "identities", "role", "accepted-empty"])
def test_output_schema_refuses_arbitrary_payloads_before_creating_output(quota, tmp_path, fault):
    value = meta.quota_bytes(quota, quota_xml(quota), b"")
    if fault == "message":
        value["message"] = "private"
    elif fault == "frame":
        value["cases"][0]["frames"][0]["path"] = "private"
    elif fault == "span":
        value["cases"][0]["frames"][0]["AST_span"]["sha256"] = "0" * 64
    elif fault == "kind":
        value["exception_type"] = "PrivateCustomerClass"
    elif fault == "identities":
        value["cases"] = value["cases"][:-1]
    elif fault == "role":
        value["private_artifacts"][0]["role"] = "driver_log"
    else:
        value["cases"], value["private_artifacts"] = [], []
    path = tmp_path / "refused.json"
    with pytest.raises(ValueError):
        meta.write_metadata(path, quota, value)
    assert not path.exists()


def test_source_change_after_read_is_not_quiet_or_publishable(quota, tmp_path):
    value = meta.quota_bytes(quota, quota_xml(quota), b"")
    path = quota.root / "tests/integration_quota_postgres.py"
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError):
        quota.quiet()
    with pytest.raises(ValueError):
        meta.write_metadata(tmp_path / "refused.json", quota, value)


def test_alias_and_oversize_inputs_fail_closed(tmp_path):
    path = tmp_path / "private.log"
    path.write_bytes(b"bounded")
    with pytest.raises(ValueError, match="size"):
        meta.read_bounded(path, 3)
    (tmp_path / "second.log").hardlink_to(path)
    with pytest.raises(ValueError, match="alias"):
        meta.read_bounded(path, 20)


def test_input_modified_during_read_is_rejected(tmp_path, monkeypatch):
    path = tmp_path / "private.log"
    path.write_bytes(b"bounded")
    original = Path.open
    class ChangingStream:
        def __init__(self, stream):
            self.stream = stream
        def __enter__(self):
            self.stream.__enter__()
            return self
        def __exit__(self, *args):
            return self.stream.__exit__(*args)
        def fileno(self):
            return self.stream.fileno()
        def read(self, limit):
            raw = self.stream.read(limit)
            path.write_bytes(raw + b"\n")
            return raw
    def changed(self, mode="r", *args, **kwargs):
        stream = original(self, mode, *args, **kwargs)
        return ChangingStream(stream) if self == path and mode == "rb" else stream
    monkeypatch.setattr(Path, "open", changed)
    with pytest.raises(ValueError, match="changed"):
        meta.read_bounded(path, 20)


@pytest.mark.parametrize("field", ["st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns"])
def test_every_open_handle_identity_field_remains_required(tmp_path, monkeypatch, field):
    path = tmp_path / "private.log"
    path.write_bytes(b"bounded")
    original = os.fstat
    calls = []
    def changed(descriptor):
        value = original(descriptor)
        calls.append(None)
        if len(calls) == 2:
            fields = {name: getattr(value, name) for name in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")}
            fields[field] += 1
            return SimpleNamespace(**fields)
        return value
    monkeypatch.setattr(meta.os, "fstat", changed)
    with pytest.raises(ValueError, match="changed"):
        meta.read_bounded(path, 20)


@pytest.mark.parametrize("schema", ["31", "33"])
def test_dispatch_has_complete_inverse_and_unchanged_default_salt(schema, sources):
    original = sources[schema][runtime.SOURCES[schema]["runner"]]
    salt = runtime.adapted_bytes(original, schema)
    observed = runtime.diagnostic_bytes(salt, schema)
    old, new = runtime.member_dispatch(schema)
    assert observed.replace(new, old) == salt
    assert salt.replace(runtime.ADDITION, b"") == original
    assert runtime.digest(observed) == runtime.DIAGNOSTIC_COMPILED[schema]["sha256"]
    assert salt == runtime.adapted_bytes(original, schema)
    with pytest.raises(ValueError):
        runtime.diagnostic_bytes(salt + b"\n", schema)


def test_support_pins_reject_changed_or_hardlinked_helpers(tmp_path, monkeypatch):
    for name in runtime.DIAGNOSTIC_SUPPORT:
        (tmp_path / name).write_bytes((ROOT / "tests/ci_web41" / name).read_bytes())
    monkeypatch.setattr(runtime, "__file__", str(tmp_path / "historical_image_runtime.py"))
    assert runtime.diagnostic_support() == tmp_path / "historical_member_diagnostic.py"
    target = tmp_path / "historical_failure_metadata.py"
    raw = target.read_bytes()
    target.write_bytes(raw + b"\n")
    with pytest.raises(ValueError):
        runtime.diagnostic_support()
    target.write_bytes(raw)
    (tmp_path / "alias.py").hardlink_to(target)
    with pytest.raises(ValueError):
        runtime.diagnostic_support()


def sandbox_run(registry, tmp_path, error, *, before_try=False):
    """Execute the real original run CodeType with inert transport boundaries."""
    events = []
    phase = tmp_path / "metodobase-member31-browser-synthetic"
    phase.mkdir()
    (phase / "database-closure.json").write_text("{}")
    chrome = tmp_path / "chrome"
    chrome.write_bytes(b"inert")
    modules = tmp_path / "modules"
    for name in ("playwright-core/package.json", "axe-core/axe.min.js"):
        path = modules / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"inert")
    class Process:
        returncode = 0
        polls = 0
        def poll(self):
            self.polls += 1
            events.append("poll")
            if self.polls == 1:
                raise error
        def wait(self, **_kwargs):
            events.append("wait")
            return 0
    def validate(_url):
        if before_try:
            raise error
    def imports(name, *args, **kwargs):
        if name == "tests.isolation":
            return SimpleNamespace(validate_postgres_test_url=validate)
        return builtins.__import__(name, *args, **kwargs)
    def check_output(argv, **_kwargs):
        return registry.spec["commit"] if "rev-parse" in argv else b""
    def popen(*_args, **_kwargs):
        events.append("popen")
        return Process()
    namespace = {"__builtins__": dict(vars(builtins), __import__=imports), "__name__": "inert_original_run",
        "ROOT": registry.root, "Path": Path, "re": re, "json": json, "uuid": uuid,
        "REVISION": ast.literal_eval(next(node.value for node in registry.trees[member.DRIVERS[registry.schema]].body
            if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "REVISION" for target in node.targets))),
        "sys": SimpleNamespace(path=[], executable="inert-python"),
        "os": SimpleNamespace(name=os.name, environ={"METODOBASE_TEST_MIGRATOR_URL": "inert",
            "METODOBASE_TEST_POSTGRES_URL": "inert", "METODOBASE_TEST_PG_BIN": str(tmp_path),
            "QA_CHROME": str(chrome), "QA_NODE_MODULES": str(modules)}),
        "shutil": SimpleNamespace(which=lambda _name: "inert-node"),
        "tempfile": SimpleNamespace(mkdtemp=lambda **_kwargs: str(phase)),
        "time": SimpleNamespace(monotonic=lambda: 1),
        "subprocess": SimpleNamespace(check_output=check_output, Popen=popen, STDOUT=-2),
        "listener_closed": lambda _port: events.append("closed") or True,
        "validate_closure": lambda _value: events.append("closure")}
    driver = member.DRIVERS[registry.schema]
    code = next(code for code in registry.codes[driver] if code.co_name == "run")
    function = FunctionType(code, namespace)
    return function, namespace, events


def untraced_canary(request, tmp_path):
    """Coverage keeps its tracer; the standalone observer gets its own process."""
    if sys.gettrace() is None:
        return False
    assert os.environ.get("METODOBASE_OBSERVER_UNIT_CHILD") != "1", "Standalone canary unexpectedly has a tracer"
    private = tmp_path / "observer-child"
    private.mkdir(mode=0o700)
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(("COVERAGE_", "PYTEST_XDIST_"))
                   and key not in {"PYTEST_CURRENT_TEST", "PYTEST_ADDOPTS", "PYTEST_PLUGINS"}}
    environment.update(PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", METODOBASE_OBSERVER_UNIT_CHILD="1",
                       _METODOBASE_TEST_ROOT=str(private / "metodobase-test-child"))
    environment.update({key: str(private) for key in ("TEMP", "TMP", "TMPDIR")})
    bootstrap = ("import sys; from tests.isolation import prepare_environment,block_external_sockets; "
                 "prepare_environment(); block_external_sockets(); import pytest; "
                 "raise SystemExit(int(pytest.main(sys.argv[1:])))")
    argv = [sys.executable, "-B", "-X", "utf8", "-c", bootstrap, "--noconftest", "-q", "--tb=short",
            "-p", "no:cacheprovider", request.node.nodeid, "--basetemp=" + str(private / "pytest-data"),
            "--junitxml=" + str(private / "pytest.xml")]
    with (private / "pytest.private.log").open("xb") as stream:
        code = subprocess.run(argv, cwd=ROOT, env=environment, stdout=stream, stderr=subprocess.STDOUT,
                              timeout=60, check=False).returncode
    assert code == 0, "Owned standalone observer canary failed; payload retained privately"
    cases = list(ET.parse(private / "pytest.xml").iter("testcase"))
    assert len(cases) == 1 and cases[0].get("name") == request.node.name
    assert not any(cases[0].find(kind) is not None for kind in ("failure", "error", "skipped"))
    return True


@pytest.mark.parametrize("schema", ["31", "33"])
@pytest.mark.parametrize("kind", [ValueError, SystemExit, KeyboardInterrupt])
def test_observation_preserves_real_original_finalizer_and_generic_error(tmp_path, sources, schema, kind, request):
    if untraced_canary(request, tmp_path):
        return
    registry = meta.SourceRegistry(source_tree(tmp_path / "source", schema, sources), schema)
    base_dir, watched_dir = tmp_path / "baseline", tmp_path / "observed"
    base_dir.mkdir()
    watched_dir.mkdir()
    secret = "synthetic-private-" + uuid.uuid4().hex
    baseline, _namespace, baseline_events = sandbox_run(registry, base_dir, kind(secret))
    with pytest.raises(RuntimeError) as original:
        baseline(base_dir / "output", 8794)
    watched, namespace, observed_events = sandbox_run(registry, watched_dir, kind(secret))
    prior = sys.gettrace()
    observer = member.MemberObserver(meta, registry, namespace)
    with pytest.raises(RuntimeError) as actual, observer:
        watched(watched_dir / "output", 8794)
    assert sys.gettrace() is prior
    assert observed_events == baseline_events and "wait" in observed_events and "closure" in observed_events
    assert type(actual.value) is type(original.value) and actual.value.args == original.value.args
    assert observer.kind == kind.__name__ and observer.frames
    value = observer.payload(True)
    meta.validate(registry, value)
    assert secret not in json.dumps(value) and "inert" not in json.dumps(value)


@pytest.mark.parametrize("schema", ["31", "33"])
def test_before_try_systemexit_is_the_same_object_and_previous_trace_is_restored(tmp_path, sources, schema, request):
    if untraced_canary(request, tmp_path):
        return
    registry = meta.SourceRegistry(source_tree(tmp_path / "source", schema, sources), schema)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    error = SystemExit(7)
    function, namespace, events = sandbox_run(registry, run_dir, error, before_try=True)
    previous = sys.gettrace()
    observer = member.MemberObserver(meta, registry, namespace)
    with pytest.raises(SystemExit) as caught, observer:
        function(run_dir / "output", 8794)
    assert caught.value is error and sys.gettrace() is previous
    assert "popen" not in events and observer.kind == "SystemExit"


def test_previous_trace_is_not_replaced_or_admitted(tmp_path, sources):
    registry = meta.SourceRegistry(source_tree(tmp_path / "source", "31", sources), "31")
    observer = member.MemberObserver(meta, registry, {})
    previous = sys.gettrace()
    def existing(_frame, _event, _argument):
        return None
    try:
        sys.settrace(existing)
        with pytest.raises(ValueError, match="existing trace"), observer:
            pytest.fail("Incompatible observer entered")
        assert sys.gettrace() is existing
    finally:
        sys.settrace(previous)


def test_counterfeit_namespace_or_code_never_observed(tmp_path, sources, request):
    if untraced_canary(request, tmp_path):
        return
    registry = meta.SourceRegistry(source_tree(tmp_path / "source", "31", sources), "31")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    function, namespace, _events = sandbox_run(registry, run_dir, ValueError("private"), before_try=True)
    observer = member.MemberObserver(meta, registry, dict(namespace))
    with pytest.raises(ValueError), observer:
        function(run_dir / "output", 8794)
    assert not observer.observed and observer.frames == []
    altered = function.__code__.replace(co_filename="<counterfeit>")
    assert registry.code_location(altered, altered.co_firstlineno) is None


@pytest.mark.parametrize("script", ["historical_failure_metadata.py", "historical_member_diagnostic.py"])
def test_cli_never_echoes_unknown_private_arguments(script):
    secret = "synthetic-private-" + uuid.uuid4().hex
    result = subprocess.run([sys.executable, "-B", "-X", "utf8", str(ROOT / "tests/ci_web41" / script),
                             "--unreviewed", "https://invalid.example/" + secret], capture_output=True, check=False)
    assert result.returncode != 0
    assert secret.encode() not in result.stdout + result.stderr and b"https://" not in result.stdout + result.stderr


def test_wrapper_standalone_boundary_precedes_business_execution(tmp_path):
    with pytest.raises(ValueError, match="standalone"):
        member.execute_member(tmp_path, "31", tmp_path / "public", 8794, tmp_path / "metadata.json")
    assert not (tmp_path / "metadata.json").exists()


@pytest.mark.parametrize("direct_root", [False, True])
def test_quota_explicit_leaf_grammar_preserves_outcomes_and_pytest_properties(quota, direct_root):
    tree = ET.fromstring(quota_xml(quota))
    suite = tree[0]
    for parent in (suite, suite[0]):
        properties = ET.SubElement(parent, "properties")
        ET.SubElement(properties, "property", name="synthetic", value="private")
        ET.SubElement(parent, "system-err").text = "synthetic private stderr"
    suite[1].remove(suite[1].find("failure"))
    suite[2].find("failure").tag = "error"
    value = meta.quota_bytes(quota, ET.tostring(suite if direct_root else tree), b"")
    assert value["diagnostic_accepted"]
    assert [row["outcome"] for row in value["cases"]] == ["failure", "passed", "error"]
    assert "synthetic private stderr" not in json.dumps(meta.validate(quota, value))


@pytest.mark.parametrize("fault", ["nested-failure", "nested-error", "nested-skipped", "property-outcome",
    "outcome-child", "output-child", "suite-output-child", "property-child", "property-unknown-attribute",
    "property-without-name", "duplicate-properties", "duplicate-output", "unknown-case-child",
    "unknown-suite-child", "testcase-outside-suite", "nested-suite", "case-text", "case-tail"])
def test_quota_malformed_descendants_can_never_be_reported_as_passed(quota, tmp_path, fault):
    tree = ET.fromstring(quota_xml(quota))
    suite, case = tree[0], tree[0][0]
    if fault in {"nested-failure", "nested-error", "nested-skipped", "property-outcome"}:
        failure = case.find("failure")
        case.remove(failure)
        failure.tag = fault.removeprefix("nested-") if fault != "property-outcome" else "failure"
        parent = ET.SubElement(case, "properties")
        if fault == "property-outcome":
            parent = ET.SubElement(parent, "property", name="synthetic")
        parent.append(failure)
    elif fault in {"outcome-child", "output-child", "suite-output-child"}:
        parent = case.find("failure") if fault == "outcome-child" else case.find("system-out")
        if fault == "suite-output-child":
            parent = ET.SubElement(suite, "system-out")
        ET.SubElement(parent, "failure")
    elif fault.startswith("property-"):
        child = ET.SubElement(ET.SubElement(case, "properties"), "property", name="synthetic", value="private")
        if fault == "property-child":
            ET.SubElement(child, "unreviewed")
        elif fault == "property-unknown-attribute":
            child.set("unreviewed", "private")
        else:
            del child.attrib["name"]
    elif fault == "duplicate-properties":
        ET.SubElement(case, "properties")
        ET.SubElement(case, "properties")
    elif fault == "duplicate-output":
        ET.SubElement(case, "system-out")
    elif fault == "unknown-case-child":
        ET.SubElement(case, "unreviewed")
    elif fault == "unknown-suite-child":
        ET.SubElement(suite, "unreviewed")
    elif fault == "testcase-outside-suite":
        suite.remove(case)
        tree.append(case)
    elif fault == "nested-suite":
        tree.remove(suite)
        ET.SubElement(tree, "testsuite").append(suite)
    elif fault == "case-text":
        case.text = "unreviewed private text"
    else:
        case[0].tail = "unreviewed private text"
    output = tmp_path / "malformed.json"
    with pytest.raises(ValueError, match="Quota|quota"):
        value = meta.quota_bytes(quota, ET.tostring(tree), b"")
        meta.write_metadata(output, quota, value)
    assert not output.exists()


def support_copy(tmp_path, monkeypatch, loader):
    for name in runtime.DIAGNOSTIC_SUPPORT:
        (tmp_path / name).write_bytes((ROOT / "tests/ci_web41" / name).read_bytes())
    module = member if loader == "member" else runtime
    monkeypatch.setattr(module, "__file__", str(tmp_path / ("historical_" + loader + ".py")))
    return module.load_support if loader == "member" else module.diagnostic_support


@pytest.mark.parametrize("loader", ["member", "runtime"])
def test_support_reads_use_exact_pinned_bounds_and_execute_authenticated_bytes(tmp_path, monkeypatch, loader):
    invoke = support_copy(tmp_path, monkeypatch, loader)
    original = Path.open
    calls = []
    class Stream:
        def __init__(self, stream, path):
            self.stream, self.path = stream, path
        def __enter__(self):
            self.stream.__enter__()
            return self
        def __exit__(self, *args):
            return self.stream.__exit__(*args)
        def fileno(self):
            return self.stream.fileno()
        def read(self, bound):
            calls.append((self.path.name, bound))
            return self.stream.read(bound)
    def opened(path, mode="r", *args, **kwargs):
        stream = original(path, mode, *args, **kwargs)
        return Stream(stream, path) if path.parent == tmp_path and mode == "rb" else stream
    def unbounded(*_args, **_kwargs):
        pytest.fail("Support used an unbounded or implicit import-loader source read")
    monkeypatch.setattr(Path, "open", opened)
    monkeypatch.setattr(Path, "read_bytes", unbounded)
    monkeypatch.setattr(member.importlib.machinery.SourceFileLoader, "exec_module", unbounded)
    value = invoke()
    names = ["historical_failure_metadata.py"] if loader == "member" else list(runtime.DIAGNOSTIC_SUPPORT)
    assert calls == [(name, runtime.DIAGNOSTIC_SUPPORT[name]["bytes"] + 1) for name in names]
    if loader == "member":
        assert value.SOURCES == meta.SOURCES and value.__file__ == str(tmp_path / names[0])


@pytest.mark.parametrize("loader", ["member", "runtime"])
@pytest.mark.parametrize("field", ["st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns"])
def test_support_open_handle_drift_is_rejected_in_each_identity_field(tmp_path, monkeypatch, loader, field):
    invoke = support_copy(tmp_path, monkeypatch, loader)
    original, calls = os.fstat, []
    def changed(descriptor):
        value = original(descriptor)
        calls.append(None)
        if len(calls) == 2:
            fields = {name: getattr(value, name) for name in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")}
            fields[field] += 1
            return SimpleNamespace(**fields)
        return value
    monkeypatch.setattr(os, "fstat", changed)
    with pytest.raises(ValueError, match="opened support changed"):
        invoke()


@pytest.mark.parametrize("loader", ["member", "runtime"])
@pytest.mark.parametrize("fault", ["foreign-handle", "growth", "same-size-source"])
def test_support_foreign_handle_growth_and_source_drift_are_rejected(tmp_path, monkeypatch, loader, fault):
    invoke = support_copy(tmp_path, monkeypatch, loader)
    path = tmp_path / "historical_failure_metadata.py"
    if fault == "same-size-source":
        raw = path.read_bytes()
        path.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
    elif fault == "foreign-handle":
        original = os.fstat
        def foreign(descriptor):
            value = original(descriptor)
            fields = {name: getattr(value, name) for name in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns",
                                                            "st_mode", "st_nlink")}
            fields["st_ino"] += 1
            return SimpleNamespace(**fields)
        monkeypatch.setattr(os, "fstat", foreign)
    else:
        original, bounds = Path.open, []
        class GrowingStream:
            def __init__(self, stream):
                self.stream = stream
            def __enter__(self):
                self.stream.__enter__()
                return self
            def __exit__(self, *args):
                return self.stream.__exit__(*args)
            def fileno(self):
                return self.stream.fileno()
            def read(self, bound):
                bounds.append(bound)
                with original(path, "ab") as writer:
                    writer.write(b"x" * 8)
                raw = self.stream.read(bound)
                assert len(raw) <= bound
                return raw
        def growing(target, mode="r", *args, **kwargs):
            stream = original(target, mode, *args, **kwargs)
            return GrowingStream(stream) if target == path and mode == "rb" else stream
        monkeypatch.setattr(Path, "open", growing)
    with pytest.raises(ValueError):
        invoke()
    if fault == "growth":
        assert bounds == [runtime.DIAGNOSTIC_SUPPORT[path.name]["bytes"] + 1]


@pytest.mark.parametrize("schema", ["31", "33"])
def test_observer_rejects_equivalent_code_with_foreign_filename_and_real_namespace(tmp_path, sources, schema):
    registry = meta.SourceRegistry(source_tree(tmp_path / "source", schema, sources), schema)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    function, namespace, _events = sandbox_run(registry, run_dir, ValueError("private"), before_try=True)
    observer = member.MemberObserver(meta, registry, namespace)
    altered = function.__code__.replace(co_filename="<foreign-filename>")
    assert altered == observer.code and altered.co_filename != observer.code.co_filename
    frame = SimpleNamespace(f_code=altered, f_globals=namespace, f_locals={"failure": ValueError("private")})
    assert observer(frame, "exception", (ValueError, ValueError("private"), None)) is None
    assert not observer.observed and observer.frames == [] and not observer.payload(True)["diagnostic_accepted"]


def member_value(registry, raw, role="browser_error_log"):
    value = meta.empty(registry, "runtime_observer")
    driver = member.DRIVERS[registry.schema]
    value["exception_type"], value["frames"] = "AssertionError", [registry.location(driver, 163)]
    value["private_artifacts"] = [meta.artifact(registry, role, raw)]
    value["source_unchanged"], value["diagnostic_accepted"] = registry.quiet(), True
    return value


def semlock_trace(terminal="FileNotFoundError: private payload"):
    return ("Traceback (most recent call last):\n"
            '  File "/private/stdlib/multiprocessing/synchronize.py", line 115, in __setstate__\n'
            "    self._semlock = _multiprocessing.SemLock._rebuild(*state)\n"
            "                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n" + terminal + "\n").encode()


def missing_node_trace(registry):
    path = registry.root / meta.MISSING_ENTRY["33"]["path"]
    return ("Error: Cannot find module '" + str(path) + "'\n"
            "    at Function._resolveFilename (node:internal/modules/cjs/loader:1:2)\n"
            "    at node:internal/main/run_main_module:1:2 {\n"
            "  code: 'MODULE_NOT_FOUND',\n  requireStack: []\n}\n").encode()


def test_cjs_is_a_separate_authenticated_Git_source_without_python_AST_or_CodeType(tmp_path, sources):
    registry = meta.SourceRegistry(source_tree(tmp_path / "source", "31", sources), "31")
    name, pin = next(iter(meta.CJS_SOURCES["31"].items()))
    raw = sources["cjs31"][name]
    assert len(raw) == pin["bytes"] == 18150 and len(raw.splitlines()) == pin["lines"] == 83
    assert meta.digest(raw) == pin["sha256"] == "ce49258340e40f1800aa1405d1460e9cc59cf4f6a05171257282bc0479b009b4"
    assert hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw, usedforsecurity=False).hexdigest() == pin["Git_blob"]
    assert len(registry.raw) == len(registry.codes) == len(registry.trees) == 8
    assert name not in registry.raw and registry.cjs_raw == {name: raw}
    assert registry.entrypoint()["expected_absent"] is False


@pytest.mark.parametrize("style", ["bare", "function", "async"])
@pytest.mark.parametrize("absolute", [False, True])
def test_cjs_frames_publish_only_exact_source_line_column_and_hashes(tmp_path, sources, style, absolute):
    registry = meta.SourceRegistry(source_tree(tmp_path / "source", "31", sources), "31")
    name = next(iter(meta.CJS_SOURCES["31"]))
    reported = str(registry.root / name) if absolute else name
    location = reported + ":75:1"
    secret = "privateFunction" + uuid.uuid4().hex
    if style != "bare":
        location = ("async " if style == "async" else "") + secret + " (" + location + ")"
    value = member_value(registry, ("Error: " + secret + "\n    at " + location + "\n").encode())
    frame = value["private_artifacts"][0]["frames"][0]
    assert frame == registry.cjs_location(name, 75, 1)
    assert frame["line_sha256"] == meta.digest(registry.cjs_raw[name].splitlines()[74])
    assert frame["origin"] == "private_cjs_text_projection" and "AST_span" not in frame
    assert meta.validate(registry, value) is value
    assert secret not in json.dumps(value) and str(registry.root) not in json.dumps(value)
    driver = meta.artifact(registry, "driver_log", ("    at " + location + "\n").encode())
    assert driver["frames"] == [frame]


@pytest.mark.parametrize("fault", ["byte", "append", "missing", "hardlink"])
def test_cjs_source_admission_refuses_drift_missing_and_aliases(tmp_path, sources, fault):
    root = source_tree(tmp_path / "source", "31", sources)
    path = root / next(iter(meta.CJS_SOURCES["31"]))
    raw = path.read_bytes()
    if fault == "missing":
        path.unlink()
    elif fault == "hardlink":
        (tmp_path / "alias.cjs").hardlink_to(path)
    else:
        path.write_bytes(raw + b"\n" if fault == "append" else bytes([raw[0] ^ 1]) + raw[1:])
    with pytest.raises((OSError, ValueError)):
        meta.SourceRegistry(root, "31")


def test_cjs_late_source_drift_prevents_metadata_publication(tmp_path, sources):
    registry = meta.SourceRegistry(source_tree(tmp_path / "source", "31", sources), "31")
    value = member_value(registry, b"")
    path = registry.root / next(iter(meta.CJS_SOURCES["31"]))
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError):
        registry.quiet()
    output = tmp_path / "refused.json"
    with pytest.raises(ValueError):
        meta.write_metadata(output, registry, value)
    assert not output.exists()


@pytest.mark.parametrize("fault", ["zero-line", "past-last-line", "zero-column", "past-line-column",
    "bool-line", "bool-column", "wrong-path", "foreign-root", "case", "suffix", "prefix", "function-name-only"])
def test_cjs_nearby_paths_prefixes_and_out_of_range_locations_are_unmapped(tmp_path, sources, fault):
    registry = meta.SourceRegistry(source_tree(tmp_path / "source", "31", sources), "31")
    name = next(iter(meta.CJS_SOURCES["31"]))
    line, column, reported, prefix = 75, 1, name, "    at "
    if fault == "zero-line":
        line = 0
    elif fault == "past-last-line":
        line = 84
    elif fault == "zero-column":
        column = 0
    elif fault == "past-line-column":
        column = len(registry.cjs_raw[name].splitlines()[74]) + 100
    elif fault == "bool-line":
        line = True
    elif fault == "bool-column":
        column = True
    elif fault == "wrong-path":
        reported = name.replace("31", "33")
    elif fault == "foreign-root":
        reported = "/private/foreign/" + name
    elif fault == "case":
        reported = name.replace("member_link", "Member_Link")
    elif fault == "suffix":
        reported += "/extra.cjs"
    elif fault == "prefix":
        prefix = "PRIVATE "
    else:
        reported = "privateFunction"
    assert registry.project_cjs_text((prefix + reported + f":{line}:{column}\n").encode()) == []
    if fault in {"zero-line", "past-last-line", "zero-column", "past-line-column", "bool-line", "bool-column"}:
        assert registry.cjs_location(name, line, column) is None


@pytest.mark.parametrize("fault", ["AST", "message", "line-hash", "source-hash", "blob", "column",
    "origin", "top-level", "fixture-role", "signal-private"])
def test_cjs_schema_refuses_fictitious_AST_private_fields_and_wrong_roles(tmp_path, sources, fault):
    registry = meta.SourceRegistry(source_tree(tmp_path / "source", "31", sources), "31")
    name = next(iter(meta.CJS_SOURCES["31"]))
    value = member_value(registry, ("    at " + name + ":75:1\n").encode())
    artifact = value["private_artifacts"][0]
    frame = artifact["frames"][0]
    if fault == "AST":
        frame["AST_span"] = {"kind": "Call", "first": 75, "last": 75, "sha256": "0" * 64}
    elif fault == "message":
        frame["message"] = "private"
    elif fault == "line-hash":
        frame["line_sha256"] = "0" * 64
    elif fault == "source-hash":
        frame["source_sha256"] = "0" * 64
    elif fault == "blob":
        frame["source_Git_blob"] = "0" * 40
    elif fault == "column":
        frame["column"] = True
    elif fault == "origin":
        frame["origin"] = "runtime_observer"
    elif fault == "top-level":
        value["frames"] = [frame]
    elif fault == "fixture-role":
        artifact["role"] = "fixture_log"
    else:
        artifact["signals"] = [{"kind": "private", "origin": "private_text_signature"}]
    output = tmp_path / "refused.json"
    with pytest.raises(ValueError):
        meta.write_metadata(output, registry, value)
    assert not output.exists()


@pytest.mark.parametrize("schema", ["31", "33"])
def test_member_reads_browser_error_only_for31_and_no_other_private_filename(tmp_path, sources, monkeypatch, schema):
    """Unit-test role selection with a directory capability, never fake POSIX/UID."""
    registry = meta.SourceRegistry(source_tree(tmp_path / "source", schema, sources), schema)
    phase = tmp_path / "phase"
    phase.mkdir(mode=0o700)
    for name in ("fixture.private.log", "driver.private.log", "browser-error.private.log", "not-readable.log"):
        (phase / name).write_bytes(b"private text must not appear")
    observer = member.MemberObserver(meta, registry, {})
    observer.phase, observer.observed = phase, True
    observer.frames = [registry.location(member.DRIVERS[schema], 163)]
    # The real POSIX private boundary remains unchanged; only this unit's role
    # selection uses an ordinary canonical directory capability on Windows.
    monkeypatch.setattr(meta, "private_directory", meta.directory)
    original, opened = meta.read_bounded, []
    def measured(path, limit):
        if path.parent == phase:
            opened.append(path.name)
            assert path.name != "not-readable.log"
        return original(path, limit)
    monkeypatch.setattr(meta, "read_bounded", measured)
    value = observer.payload(True)
    expected = ["fixture.private.log", "driver.private.log"]
    if schema == "31":
        expected.append("browser-error.private.log")
    assert opened == expected
    assert len(value["private_artifacts"]) == (3 if schema == "31" else 2)
    assert "private text" not in json.dumps(meta.validate(registry, value))


@pytest.mark.parametrize("fault", ["hardlink", "oversize", "changed-during-read"])
def test_browser_error_input_alias_bounds_and_handle_quiet_are_still_required(tmp_path, sources, monkeypatch, fault):
    registry = meta.SourceRegistry(source_tree(tmp_path / "source", "31", sources), "31")
    phase = tmp_path / "phase"
    phase.mkdir(mode=0o700)
    path = phase / "browser-error.private.log"
    path.write_bytes(b"private browser payload")
    if fault == "hardlink":
        (tmp_path / "alias.log").hardlink_to(path)
    elif fault == "oversize":
        with path.open("wb") as stream:
            stream.truncate(meta.MAX_PRIVATE + 1)
    else:
        original = Path.open
        class ChangedStream:
            def __init__(self, stream):
                self.stream = stream
            def __enter__(self):
                self.stream.__enter__()
                return self
            def __exit__(self, *arguments):
                return self.stream.__exit__(*arguments)
            def fileno(self):
                return self.stream.fileno()
            def read(self, bound):
                raw = self.stream.read(bound)
                with original(path, "r+b") as writer:
                    writer.write(bytes([raw[0] ^ 1]))
                return raw
        def changed(target, mode="r", *arguments, **keywords):
            stream = original(target, mode, *arguments, **keywords)
            return ChangedStream(stream) if target == path and mode == "rb" else stream
        monkeypatch.setattr(Path, "open", changed)
    monkeypatch.setattr(meta, "private_directory", meta.directory)
    observer = member.MemberObserver(meta, registry, {})
    observer.phase, observer.observed = phase, True
    observer.frames = [registry.location(member.DRIVERS["31"], 163)]
    value = observer.payload(True)
    assert value["diagnostic_accepted"] is False and value["issues"] == ["private_log_unavailable"]
    assert value["private_artifacts"] == []
    assert "private browser payload" not in json.dumps(meta.validate(registry, value))


@pytest.mark.parametrize("schema", ["30", "33"])
def test_browser_error_role_cannot_be_admitted_for_another_schema(tmp_path, sources, schema):
    registry = meta.SourceRegistry(source_tree(tmp_path / "source", schema, sources), schema)
    value = (meta.quota_bytes(registry, quota_xml(registry), b"") if schema == "30"
             else member_value(registry, b"", "driver_log"))
    value["private_artifacts"].append(meta.artifact(registry, "browser_error_log", b""))
    with pytest.raises(ValueError):
        meta.validate(registry, value)


@pytest.mark.parametrize("schema", ["30", "31", "33"])
@pytest.mark.parametrize("fault", ["wrong-kind", "private-field", "wrong-origin", "duplicate"])
def test_signal_schema_is_closed_and_cannot_publish_arbitrary_details(tmp_path, sources, schema, fault):
    registry = meta.SourceRegistry(source_tree(tmp_path / "source", schema, sources), schema)
    if schema == "30":
        value = meta.quota_bytes(registry, quota_xml(registry), semlock_trace())
        row = value["private_artifacts"][1]
    else:
        value = member_value(registry, missing_node_trace(registry) if schema == "33" else b"", "driver_log")
        row = value["private_artifacts"][0]
    signal = {"kind": "node_entrypoint_module_not_found" if schema == "33" else "spawn_semlock_rebuild_file_not_found",
              "origin": "private_text_signature"}
    if fault == "wrong-kind":
        signal["kind"] = "private-value"
    elif fault == "private-field":
        signal["message"] = "private-value"
    elif fault == "wrong-origin":
        signal["origin"] = "authenticated_stdlib_runtime_cause"
    row["signals"] = [signal, signal] if fault == "duplicate" else [signal]
    with pytest.raises(ValueError):
        meta.validate(registry, value)


def test_schema33_absence_descriptor_is_bound_to_real_invoker_and_refuses_an_invented_entry(tmp_path, sources):
    registry = meta.SourceRegistry(source_tree(tmp_path / "source", "33", sources), "33")
    entry = registry.entrypoint()
    assert entry["expected_absent"] is True and entry["historical_tree"] == "65dc275f8056b3712de8f8ff0ec28135fd300429"
    assert entry["invoker"] == registry.location(member.DRIVERS["33"], 162)
    assert b"tests/e2e/member_link33_browser.cjs" in registry.raw[member.DRIVERS["33"]].splitlines()[161]
    assert registry.cjs_raw == {} and "source_sha256" not in entry
    path = registry.root / entry["path"]
    path.write_bytes(sources["cjs31"][next(iter(meta.CJS_SOURCES["31"]))])
    with pytest.raises(ValueError, match="must remain absent"):
        registry.quiet()
    with pytest.raises(ValueError, match="must remain absent"):
        meta.SourceRegistry(registry.root, "33")


@pytest.mark.parametrize("fault", ["boolean", "tree", "invoker", "extra-private", "invented-pin"])
def test_schema33_absence_descriptor_cannot_be_forged_or_coerced(tmp_path, sources, fault):
    registry = meta.SourceRegistry(source_tree(tmp_path / "source", "33", sources), "33")
    value = member_value(registry, b"", "driver_log")
    entry = value["entrypoint"]
    if fault == "boolean":
        entry["expected_absent"] = 1
    elif fault == "tree":
        entry["historical_tree"] = "0" * 40
    elif fault == "invoker":
        entry["invoker"]["line"] = 161
    elif fault == "extra-private":
        entry["message"] = "private"
    else:
        entry["source_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        meta.validate(registry, value)


def test_quota_semlock_signal_is_only_private_structural_text_not_a_stdlib_frame(quota):
    raw = semlock_trace()
    value = meta.quota_bytes(quota, quota_xml(quota), raw)
    row = value["private_artifacts"][1]
    assert row["signals"] == [{"kind": "spawn_semlock_rebuild_file_not_found", "origin": "private_text_signature"}]
    assert row["frames"] == [] and row["exception_types"] == ["FileNotFoundError"]
    assert meta.validate(quota, value) is value
    assert "private payload" not in json.dumps(value) and "synchronize.py" not in json.dumps(value)
    assert meta.artifact(quota, "quota_xml", raw)["signals"] == []


@pytest.mark.parametrize("fault", ["no-header", "other-frame", "message", "custom", "qualified-custom",
    "separate-block", "wrong-terminal", "terminal-first", "quoted-source", "no-frame", "prefixed", "altered-call"])
def test_semlock_nearby_messages_classes_or_other_tracebacks_do_not_signal(quota, fault):
    raw = semlock_trace()
    if fault == "no-header":
        raw = raw.split(b"\n", 1)[1]
    elif fault == "other-frame":
        raw = raw.replace(b"in __setstate__", b"in private_function")
    elif fault == "message":
        raw = b"ValueError: " + raw.replace(b"\n", b" ")
    elif fault == "custom":
        raw = raw.replace(b"FileNotFoundError:", b"PrivateFileNotFoundError:")
    elif fault == "qualified-custom":
        raw = raw.replace(b"FileNotFoundError:", b"private.FileNotFoundError:")
    elif fault == "separate-block":
        raw = raw.replace(b"FileNotFoundError:", b"Traceback (most recent call last):\nFileNotFoundError:")
    elif fault == "wrong-terminal":
        raw = raw.replace(b"FileNotFoundError:", b"ValueError:")
    elif fault == "terminal-first":
        raw = b"FileNotFoundError: private\n" + raw.replace(b"FileNotFoundError: private payload\n", b"")
    elif fault == "quoted-source":
        raw = raw.replace(b"    self._semlock =", b"    message = 'self._semlock =")
    elif fault == "no-frame":
        raw = b"\n".join(line for line in raw.split(b"\n") if not line.startswith(b"  File"))
    elif fault == "prefixed":
        raw = b"\n".join(b"PRIVATE> " + line for line in raw.split(b"\n"))
    else:
        raw = raw.replace(b"_rebuild(*state)", b"_rebuild(private)")
    assert not meta.semlock_signature(raw)
    assert meta.artifact(quota, "quota_log", raw)["signals"] == []


def test_schema33_module_not_found_signal_requires_exact_missing_entry_and_one_Node_block(tmp_path, sources):
    registry = meta.SourceRegistry(source_tree(tmp_path / "source", "33", sources), "33")
    raw = missing_node_trace(registry)
    value = member_value(registry, raw, "driver_log")
    row = value["private_artifacts"][0]
    assert row["signals"] == [{"kind": "node_entrypoint_module_not_found", "origin": "private_text_signature"}]
    assert row["frames"] == [] and meta.validate(registry, value) is value
    assert str(registry.root) not in json.dumps(value) and "Cannot find module" not in json.dumps(value)
    assert meta.artifact(registry, "fixture_log", raw)["signals"] == []


@pytest.mark.parametrize("fault", ["wrong-path", "foreign-root", "suffix", "custom-class", "message",
    "separate-block", "other-code", "no-code", "no-stack", "no-brace", "nonempty-require-stack"])
def test_schema33_nearby_paths_custom_errors_and_unrelated_module_not_found_blocks_do_not_signal(tmp_path, sources, fault):
    registry = meta.SourceRegistry(source_tree(tmp_path / "source", "33", sources), "33")
    raw = missing_node_trace(registry)
    if fault == "wrong-path":
        raw = raw.replace(b"member_link33_browser.cjs", b"member_link31_browser.cjs")
    elif fault == "foreign-root":
        raw = raw.replace(str(registry.root).encode(), b"/private/foreign")
    elif fault == "suffix":
        raw = raw.replace(b"member_link33_browser.cjs'", b"member_link33_browser.cjs/extra'")
    elif fault == "custom-class":
        raw = raw.replace(b"Error:", b"PrivateError:")
    elif fault == "message":
        raw = b"private argument: " + raw
    elif fault == "separate-block":
        raw = raw.replace(b"  code:", b"Error: private other block\n  code:")
    elif fault == "other-code":
        raw = raw.replace(b"MODULE_NOT_FOUND", b"OTHER")
    elif fault == "no-code":
        raw = raw.replace(b"  code: 'MODULE_NOT_FOUND',\n", b"")
    elif fault == "no-stack":
        raw = b"\n".join(line for line in raw.split(b"\n") if not line.startswith(b"    at"))
    elif fault == "no-brace":
        raw = raw.replace(b" {\n", b"\n")
    else:
        raw = raw.replace(b"requireStack: []", b"requireStack: ['private']")
    assert not meta.missing_entry_signature(registry, raw)
    assert meta.artifact(registry, "driver_log", raw)["signals"] == []

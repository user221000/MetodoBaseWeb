"""Actual historical phase inputs, original code and adversarial lifecycle checks."""
from __future__ import annotations

import ast
import builtins
import hashlib
import importlib
import json
import os
import shutil
import subprocess
import sys
import textwrap
from copy import copy, deepcopy
from dataclasses import replace
from pathlib import Path
from types import FunctionType, ModuleType, SimpleNamespace

import pytest
from _pytest.stash import Stash

from tests.ci_web41 import legacy_pg_unit_capsule as capsule
from tests.ci_web41 import pg_legacy_consumer_inputs as inputs

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module", autouse=True)
def database_schema():
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


@pytest.fixture(scope="module")
def real_snapshot(tmp_path_factory):
    return capsule.snapshot(ROOT, tmp_path_factory.mktemp("legacy-phases-real") / "capsule")


@pytest.fixture(scope="module")
def clones(real_snapshot):
    originals = [importlib.import_module(name[:-3].replace("/", ".")) for name in inputs.CONSUMERS]
    names = {module.__name__: (module, dict(vars(module))) for module in originals}
    lease = importlib.import_module("tests.ci_web37.pg_lease")
    names[lease.__name__] = lease, dict(vars(lease))
    modules = [inputs.clone_inputs(module, snapshot=real_snapshot)[0] for module in originals]
    for name, (module, namespace) in names.items():
        assert sys.modules[name] is module and vars(module).keys() == namespace.keys()
        assert all(vars(module)[key] is value for key, value in namespace.items())
    return modules


def test_child_derives_separate_bounded_complete_phase_artifact(real_snapshot):
    value = real_snapshot.checked(ROOT, capsule.manifest(ROOT))
    assert value["schema"] == "legacy-pg-unit-child-v3"
    assert len(capsule.read_bounded(real_snapshot._private / "snapshot.json", 65536)) < 65536
    raw = capsule.read_bounded(real_snapshot._private / "phases.json", 63169)
    assert len(raw) == 63169 and hashlib.sha256(raw).hexdigest() == capsule.PHASE_ARTIFACT["sha256"]
    rows = capsule.historical_phase_rows(ROOT, None, snapshot=real_snapshot)
    assert len(rows) == 29 and sum(row["cases"] for row in rows) == 429
    assert len({tuple(identity) for row in rows for identity in row["expected"]}) == 429
    assert len(value["cases"]) == 19 and all(set(case["phases"].values()) == {"passed"} for case in value["cases"])
    assert len(value["budgets"]) == 29 and sum(row["UUIDs"] for row in value["budgets"]) == 69
    rows[0]["expected"].clear()
    assert capsule.historical_phase_rows(ROOT, None, snapshot=real_snapshot)[0]["expected"]


@pytest.mark.parametrize("index", range(3))
def test_original_CodeTypes_markers_asserts_and_fixture_objects_are_retained(clones, index):
    clone = clones[index]
    original = sys.modules[clone.__name__]
    assert clone is not original and clone.__file__ == original.__file__
    tree = ast.parse((ROOT / inputs.CONSUMERS[index]).read_bytes())
    assert sum(isinstance(node, ast.Assert) for node in ast.walk(tree)) == (7, 21, 4)[index]
    for name, value in vars(original).items():
        if isinstance(value, FunctionType) and value.__module__ == original.__name__:
            current = vars(clone)[name]
            assert current is not value and current.__code__ is value.__code__
            assert current.__globals__ is vars(clone) and value.__globals__ is vars(original)
            assert current.__defaults__ == value.__defaults__ and current.__kwdefaults__ == value.__kwdefaults__
            assert current.__dict__ == value.__dict__ and current.__qualname__ == value.__qualname__
    if index == 2:
        assert clone.trace is original.trace and clone.require_witnesses is original.require_witnesses
    if hasattr(clone, "pg_lease"):
        for name, value in vars(original.pg_lease).items():
            if isinstance(value, FunctionType) and value.__module__ == original.pg_lease.__name__:
                current = vars(clone.pg_lease)[name]
                assert current.__code__ is value.__code__ and current.__globals__ is vars(clone.pg_lease)


@pytest.mark.parametrize("name", inputs.PINS)
def test_all_ten_consumer_inputs_reject_a_changed_payload_before_import(tmp_path, name):
    for relative in inputs.PINS:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    target = tmp_path / name
    raw = target.read_bytes()
    target.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
    with pytest.raises(ValueError, match="source differs"):
        inputs.source_payloads(tmp_path)


@pytest.mark.parametrize("fault", ["schema-v2", "missing-descriptor", "extra-descriptor", "file", "role", "bytes",
                                  "float-bytes", "sha256"])
def test_snapshot_descriptor_is_closed_and_cannot_select_a_file(real_snapshot, fault):
    value = real_snapshot.checked(ROOT, capsule.manifest(ROOT))
    if fault == "schema-v2":
        value["schema"] = "legacy-pg-unit-child-v2"
    elif fault == "missing-descriptor":
        del value["phase_artifact"]
    elif fault == "extra-descriptor":
        value["phase_artifact"]["private"] = "synthetic-private-marker"
    else:
        key = "bytes" if fault == "float-bytes" else fault
        value["phase_artifact"][key] = 63169.0 if fault == "float-bytes" else "unreviewed"
    with pytest.raises((ValueError, TypeError)):
        capsule.validate_snapshot(value, capsule.manifest(ROOT), real_snapshot._helper_sha)


@pytest.mark.parametrize("fault", ["missing", "extra-byte", "truncated", "mutated", "hardlink", "duplicate-key",
                                  "duplicate-row", "unknown-row", "extra-field", "missing-identity"])
def test_phase_artifact_cannot_expand_or_fabricate_original_inputs(tmp_path, real_snapshot, fault):
    raw = capsule.read_bounded(real_snapshot._private / "phases.json", 63169)
    target = tmp_path / "phases.json"
    if fault == "missing":
        pass
    elif fault == "extra-byte":
        target.write_bytes(raw + b" ")
    elif fault == "truncated":
        target.write_bytes(raw[:-1])
    elif fault == "mutated":
        target.write_bytes(b" " + raw[1:])
    elif fault == "hardlink":
        target.write_bytes(raw)
        (tmp_path / "alias").hardlink_to(target)
    elif fault == "duplicate-key":
        target.write_bytes(raw.replace(b'"key":', b'"key":"forged","key":', 1))
    else:
        rows = capsule.decode(raw)
        if fault == "duplicate-row":
            rows[-1] = rows[0]
        elif fault == "unknown-row":
            rows[0]["key"] = "unreviewed"
        elif fault == "extra-field":
            rows[0]["private"] = "synthetic-private-marker"
        else:
            rows[0]["expected"].pop()
        target.write_bytes(capsule.canonical(rows) + b"\n")
    with pytest.raises((ValueError, OSError)):
        capsule.phase_rows(tmp_path, dict(capsule.PHASE_ARTIFACT))


def test_artifact_reader_is_bounded_and_never_uses_an_unbounded_reader(real_snapshot, monkeypatch):
    reads = []
    original = Path.open
    class Stream:
        def __init__(self, stream):
            self.stream = stream
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            self.stream.close()
        def fileno(self):
            return self.stream.fileno()
        def read(self, size):
            reads.append(size)
            return self.stream.read(size)
    def opened(path, *args, **kwargs):
        return Stream(original(path, *args, **kwargs))
    def refused(*_args, **_kwargs):
        pytest.fail("An unbounded payload reader ran")
    monkeypatch.setattr(Path, "read_bytes", refused)
    monkeypatch.setattr(Path, "open", opened)
    assert len(capsule.phase_rows(real_snapshot._private, dict(capsule.PHASE_ARTIFACT))) == 29
    assert reads == [63170]


@pytest.mark.parametrize("fault", ["code", "filename", "nested-filename", "namespace", "defaults", "kwdefaults", "annotations", "attributes",
                                  "marks", "module", "qualname", "global-alias", "constant", "fixture"])
def test_loaded_original_objects_cannot_be_replaced_by_source_lookalikes(real_snapshot, monkeypatch, fault):
    original = importlib.import_module("tests.test_ci_web37_pg_lease")
    function = original.test_all_twenty_nine_phases_have_their_source_bound_finite_budget
    if fault == "code":
        monkeypatch.setattr(function, "__code__", (lambda: None).__code__)
    elif fault == "filename":
        monkeypatch.setattr(function, "__code__", function.__code__.replace(co_filename="synthetic-untrusted.py"))
    elif fault == "nested-filename":
        constants = tuple(value.replace(co_filename="synthetic-untrusted.py") if isinstance(value, type(function.__code__))
                          else value for value in function.__code__.co_consts)
        monkeypatch.setattr(function, "__code__", function.__code__.replace(co_consts=constants))
    elif fault == "namespace":
        monkeypatch.setattr(original, function.__name__, FunctionType(function.__code__, dict(vars(original))))
    elif fault == "defaults":
        monkeypatch.setattr(function, "__defaults__", (None,))
    elif fault == "kwdefaults":
        monkeypatch.setattr(function, "__kwdefaults__", {"extra": None})
    elif fault == "annotations":
        monkeypatch.setattr(function, "__annotations__", {"return": "forged"})
    elif fault == "attributes":
        monkeypatch.setattr(function, "forged", True, raising=False)
    elif fault == "marks":
        marked = original.test_a_child_cannot_exceed_or_fabricate_its_UUID_budget
        monkeypatch.setattr(marked, "pytestmark", [pytest.mark.parametrize("value", [0])])
    elif fault == "module":
        monkeypatch.setattr(function, "__module__", "unreviewed")
    elif fault == "qualname":
        monkeypatch.setattr(function, "__qualname__", "unreviewed")
    elif fault == "global-alias":
        monkeypatch.setattr(original, "pg_lease", SimpleNamespace())
    elif fault == "constant":
        monkeypatch.setattr(original, "NOW", None)
    else:
        original = importlib.import_module("tests.test_ci_web37_pg_r24_witness")
        marker = replace(original.trace._fixture_function_marker, scope="session")
        monkeypatch.setattr(original.trace, "_fixture_function_marker", marker)
    with pytest.raises(ValueError, match="original consumer"):
        inputs.clone_inputs(original, snapshot=real_snapshot)


@pytest.mark.parametrize("value", [-1, 2, True, 1.0, "1"])
def test_uuid_negatives_reach_original_phase_budget_after_historical_source_validation(clones, value):
    lease = clones[0].pg_lease
    with pytest.raises(ValueError, match="UUID budget") as caught:
        lease.phase_budget("account", value, succeeded=False)
    frames = []
    trace = caught.value.__traceback__
    while trace:
        frames.append(trace.tb_frame.f_code)
        trace = trace.tb_next
    assert lease.phase_budget.__code__ in frames
    assert all(frame.co_name != "specification" for frame in frames)


@pytest.mark.parametrize("fault", ["missing", "extra", "pool", "boolean-pool", "role", "identity", "stage", "kind"])
def test_R24_negatives_reach_original_witness_validator(clones, tmp_path, fault):
    clone = clones[2]
    rows = [json.loads(line) for line in clone.RAW.read_bytes().splitlines()]
    assert clone.require_witnesses(clone.RAW, clone.race()) == 6
    if fault == "missing":
        rows.pop()
    elif fault == "extra":
        rows.append(deepcopy(rows[-1]))
    elif fault == "pool":
        rows[1]["value"]["pool_size"] = 1
    elif fault == "boolean-pool":
        rows[0]["value"]["pool_size"] = True
    elif fault == "role":
        rows[0]["value"]["role_flags4"][0] = True
    elif fault == "identity":
        rows[0]["test"] = "unreviewed"
    elif fault == "stage":
        rows[0]["test"] = rows[0]["test"].replace("setup", "teardown")
    else:
        rows[0]["kind"] = "unreviewed"
    target = clone.write_trace(tmp_path, rows)
    phase = clone.race()
    with pytest.raises(ValueError) as caught:
        clone.require_witnesses(target, phase)
    frames = []
    trace = caught.value.__traceback__
    while trace:
        frames.append(trace.tb_frame.f_code)
        trace = trace.tb_next
    assert clone.require_witnesses.__code__ in frames
    assert all(frame.co_name != "specification" for frame in frames)


def test_fixture_lifecycle_revalidates_and_copies_each_consumer_without_caching_mutable_rows(real_snapshot, tmp_path_factory, monkeypatch):
    original = importlib.import_module("tests.test_ci_web37_pg_lease")
    clone, _receipt = inputs.clone_inputs(original)
    request = SimpleNamespace(config=SimpleNamespace(stash=Stash()))
    issued, reads = [], []
    actual_reader = capsule.historical_phase_rows
    def issue(*_args):
        issued.append(True)
        return real_snapshot
    def read(*args, **kwargs):
        reads.append(True)
        return actual_reader(*args, **kwargs)
    monkeypatch.setattr(capsule, "snapshot", issue)
    monkeypatch.setattr(capsule, "historical_phase_rows", read)
    fixture = clone._web41_historical_pg_input._get_wrapped_function()
    with pytest.raises(ValueError, match="fixture has not run"):
        clone.pg_lease.budgets()
    for _ in range(2):
        lifecycle = fixture(request, tmp_path_factory)
        next(lifecycle)
        rows = clone.pg_lease.budgets()
        rows[0]["cases"] = -1
        assert clone.pg_lease.budgets()[0]["cases"] > 0
        with pytest.raises(StopIteration):
            next(lifecycle)
        with pytest.raises(ValueError, match="fixture has not run"):
            clone.pg_lease.budgets()
    assert len(issued) == 1 and len(reads) == 6
    assert type(request.config.stash[inputs._SNAPSHOT]) is capsule.Snapshot


def test_second_fixture_consumer_rejects_changed_artifact_even_with_cached_Snapshot(real_snapshot, tmp_path, tmp_path_factory):
    altered = copy(real_snapshot)
    altered._private = tmp_path / "private"
    shutil.copytree(real_snapshot._private, altered._private)
    clone, _receipt = inputs.clone_inputs(importlib.import_module("tests.test_ci_web37_pg_lease"))
    request = SimpleNamespace(config=SimpleNamespace(stash=Stash()))
    request.config.stash[inputs._SNAPSHOT] = altered
    fixture = clone._web41_historical_pg_input._get_wrapped_function()
    first = fixture(request, tmp_path_factory)
    next(first)
    assert len(clone.pg_lease.budgets()) == 29
    with pytest.raises(StopIteration):
        next(first)
    (altered._private / "phases.json").write_bytes(b"[]\n")
    with pytest.raises(ValueError, match="phase artifact differs"):
        next(fixture(request, tmp_path_factory))
    with pytest.raises(ValueError, match="fixture has not run"):
        clone.pg_lease.budgets()


def test_real_pytest_fixture_cycle_revalidates_both_consumers_from_one_child(tmp_path):
    """Exercise actual scheduling as well as the direct fixture-body negatives."""
    (tmp_path / "test_lifecycle.py").write_text(textwrap.dedent('''\
        import importlib
        from tests.ci_web41 import pg_legacy_consumer_inputs as source
        original = importlib.import_module("tests.test_ci_web37_pg_lease")
        private, _receipt = source.clone_inputs(original)
        historical_pg_input = private._web41_historical_pg_input
        seen = {}
        def test_01_mutates_only_own_rows(request):
            rows = private.pg_lease.budgets()
            assert len(rows) == 29 and sum(row["cases"] for row in rows) == 429
            seen["rows"] = rows
            seen["snapshot"] = request.config.stash[source._SNAPSHOT]
            rows[0]["cases"] = -1
            rows.append({"cases": -1})
        def test_02_gets_a_revalidated_independent_copy(request):
            rows = private.pg_lease.budgets()
            assert len(rows) == 29 and sum(row["cases"] for row in rows) == 429
            assert sum(row["UUIDs"] for row in rows) == 69
            assert rows is not seen["rows"]
            assert all(new is not old for new, old in zip(rows, seen["rows"]))
            assert request.config.stash[source._SNAPSHOT] is seen["snapshot"]
    '''), encoding="utf8")
    runner = textwrap.dedent('''\
        import json, pathlib, sys, xml.etree.ElementTree as ET
        repository, private = map(pathlib.Path, sys.argv[1:])
        sys.path.insert(0, str(repository))
        from tests.isolation import prepare_environment, block_external_sockets
        prepare_environment(discard_inherited=True)
        block_external_sockets()
        import sqlite3, psycopg2
        def denied(*args, **kwargs):
            raise AssertionError("SQL is forbidden in this source-only fixture check")
        sqlite3.connect = psycopg2.connect = denied
        import pytest
        from tests.ci_web41 import legacy_pg_unit_capsule as capsule
        counts = {"snapshot_calls": 0, "phase_api_calls": 0, "checked_calls": 0}
        codes = {capsule.snapshot.__code__: "snapshot_calls",
                 capsule.historical_phase_rows.__code__: "phase_api_calls",
                 capsule.Snapshot.checked.__code__: "checked_calls"}
        def observe(frame, event, argument):
            if event == "call" and frame.f_code in codes:
                original = next(code for code in codes if code == frame.f_code)
                if frame.f_code.co_filename == original.co_filename:
                    counts[codes[original]] += 1
        sys.setprofile(observe)
        try:
            code = pytest.main([str(private / "test_lifecycle.py"), "--noconftest",
                "-o", "addopts=", "-p", "no:cacheprovider", "--rootdir", str(private),
                "--basetemp", str(private / "pytest-base"),
                "--junitxml", str(private / "lifecycle.private.xml"), "-q"])
        finally:
            sys.setprofile(None)
        cases = list(ET.parse(private / "lifecycle.private.xml").getroot().iter("testcase"))
        snapshots = list((private / "pytest-base").rglob("snapshot.json"))
        counts.update(pytest_exit=int(code), cases=len(cases),
            failed=sum(any(item.tag in ("failure", "error", "skipped") for item in row) for row in cases),
            snapshot_files=len(snapshots))
        if len(snapshots) == 1:
            actual = json.loads(snapshots[0].read_bytes())
            counts.update(child_exit=actual["child_exit"], blocked_attempts=actual["blocked_attempts"],
                          child_cases=len(actual["cases"]), phase_artifact=actual["phase_artifact"])
        (private / "lifecycle.json").write_text(json.dumps(counts), encoding="utf8")
        raise SystemExit(code)
    ''')
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(("PYTEST_", "COVERAGE_"))
                   and key not in {"PYTHONPATH", "PYTHONSTARTUP", "_METODOBASE_TEST_ROOT"}}
    temporary = tmp_path / "temporary"
    temporary.mkdir()
    environment.update(PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1",
                       **{key: str(temporary) for key in ("TEMP", "TMP", "TMPDIR")})
    with (tmp_path / "lifecycle.private.log").open("xb") as stream:
        process = subprocess.run([sys.executable, "-I", "-B", "-X", "utf8", "-c", runner, str(ROOT), str(tmp_path)],
            cwd=tmp_path, env=environment, stdout=stream, stderr=subprocess.STDOUT, timeout=150, check=False)
    value = json.loads((tmp_path / "lifecycle.json").read_bytes())
    assert process.returncode == value["pytest_exit"] == 0
    assert value["cases"] == 2 and value["failed"] == 0
    assert value["snapshot_calls"] == value["snapshot_files"] == 1
    assert value["phase_api_calls"] == value["checked_calls"] == 4
    assert value["child_cases"] == 19 and value["child_exit"] == value["blocked_attempts"] == 0
    assert value["phase_artifact"] == capsule.PHASE_ARTIFACT


def test_reuse_detects_phase_mutation_before_next_consumer(real_snapshot, tmp_path):
    altered = copy(real_snapshot)
    altered._private = tmp_path / "private"
    shutil.copytree(real_snapshot._private, altered._private)
    (altered._private / "phases.json").write_bytes(b"[]\n")
    for reader in (capsule.historical_phase_rows, capsule.historical_budget_rows):
        with pytest.raises(ValueError, match="phase artifact differs"):
            reader(ROOT, None, snapshot=altered)


def test_only_a_real_snapshot_and_three_explicit_consumers_can_bind(real_snapshot):
    original = importlib.import_module("tests.test_ci_web37_pg_lease")
    with pytest.raises(ValueError, match="actual isolated child Snapshot"):
        inputs.clone_inputs(original, snapshot={})
    with pytest.raises(ValueError, match="process snapshot"):
        capsule.historical_phase_rows(ROOT, None, snapshot={})
    with pytest.raises(ValueError, match="explicit original"):
        inputs.clone_inputs(SimpleNamespace(__file__=str(ROOT / "tests/unreviewed.py")), snapshot=real_snapshot)


def test_fixed_expression_language_cannot_execute_other_calls():
    for source in ("unreviewed()", "NOW.replace(year=2000)", "range(100000)", "'private' * 100000"):
        with pytest.raises(ValueError):
            inputs._expression(ast.parse(source, mode="eval").body)


@pytest.mark.parametrize("values", [[-1, 2, 1, 1], [-1, 2, 1.0, 1.0], [-1, 2, True, 1]])
def test_equal_numeric_mark_values_cannot_replace_original_boolean_or_float_oracles(monkeypatch, values):
    original = importlib.import_module("tests.test_ci_web37_pg_lease")
    function = original.test_a_child_cannot_exceed_or_fabricate_its_UUID_budget
    prior = function.pytestmark
    changed = [pytest.mark.parametrize("value", values).mark]
    assert changed == prior  # The historical Python-equality trap is real.
    monkeypatch.setattr(function, "pytestmark", changed)
    with pytest.raises(ValueError, match="marker or function attributes"):
        inputs.clone_inputs(original)


def _typed_function_contract():
    """Finite function fixture for the metadata checker, not a source admission."""
    source = "def sample(a=True, *, flag=False):\n return a, flag\n"
    path = Path(__file__).absolute()
    node = ast.parse(source).body[0]
    reference = next(item for item in compile(source, str(path), "exec", dont_inherit=True).co_consts
                     if isinstance(item, type(_typed_function_contract.__code__)))
    module = ModuleType("typed_contract_control")
    function = FunctionType(reference, vars(module), "sample", (True,))
    function.__kwdefaults__ = {"flag": False}
    function.__qualname__, function.__module__ = "sample", module.__name__
    return function, reference, node, module, path


@pytest.mark.parametrize("field,value", [("defaults", 1), ("defaults", 1.0), ("kwdefaults", 0), ("kwdefaults", 0.0)])
def test_function_metadata_keeps_recursive_exact_default_types(field, value):
    function, reference, node, module, path = _typed_function_contract()
    assert inputs._function(function, [reference], node, module, path) is function
    if field == "defaults":
        function.__defaults__ = (value,)
    else:
        function.__kwdefaults__ = {"flag": value}
    with pytest.raises(ValueError, match="defaults differs"):
        inputs._function(function, [reference], node, module, path)


@pytest.mark.parametrize("fault", ["autouse-int", "autouse-float", "params-int", "params-float", "params-bool"])
def test_fixture_metadata_cannot_exchange_boolean_integer_or_float_parameters(fault):
    function, reference, _node, module, path = _typed_function_contract()
    source = "@pytest.fixture(params=(True, 1, 1.0), autouse=False)\ndef sample(a=True, *, flag=False):\n return a, flag\n"
    node = ast.parse(source).body[0]
    fixture = pytest.fixture(params=(True, 1, 1.0), autouse=False)(function)
    assert inputs._function(fixture, [reference], node, module, path) is function
    options = {"params": (True, 1, 1.0), "autouse": False}
    if fault == "autouse-int":
        options["autouse"] = 0
    elif fault == "autouse-float":
        options["autouse"] = 0.0
    elif fault == "params-int":
        options["params"] = (1, 1, 1)
    elif fault == "params-float":
        options["params"] = (1.0, 1.0, 1.0)
    else:
        options["params"] = (True, True, True)
    changed = pytest.fixture(**options)(function)
    assert vars(changed._fixture_function_marker) == vars(fixture._fixture_function_marker)
    with pytest.raises(ValueError, match="fixture scope or parameters"):
        inputs._function(changed, [reference], node, module, path)


@pytest.mark.parametrize("actual,expected", [
    (True, 1), (1, 1.0), ([True], [1]), ((1.0,), (1,)), ({"params": [True]}, {"params": [1]}),
    ({True: "value"}, {1: "value"}), ({1.0: "value"}, {1: "value"}), ({True}, {1}),
    (frozenset({1.0}), frozenset({1})), (range(0, 6, 2), range(0, 5, 2)),
])
def test_nested_equal_values_do_not_destroy_typed_oracles(actual, expected):
    assert actual == expected
    assert not inputs.same_typed(actual, expected)


def test_legitimate_mark_values_and_original_parameter_types_remain_accepted():
    value = {"rows": [-1, 2, True, 1.0], "tuple": (False, None, "text"), "range": range(6),
             "set": {"a", "b"}, "frozen": frozenset({"b", "a"}), "path": ROOT}
    assert inputs.same_typed(value, deepcopy(value))
    original = importlib.import_module("tests.test_ci_web37_pg_lease")
    clone, _receipt = inputs.clone_inputs(original)
    function = clone.test_a_child_cannot_exceed_or_fabricate_its_UUID_budget
    assert [type(item) for item in function.pytestmark[0].args[1]] == [int, int, bool, float]
    assert inputs.same_typed(function.__dict__, original.test_a_child_cannot_exceed_or_fabricate_its_UUID_budget.__dict__)


IMPORT_BINDINGS = {
    "consumer": ("ast", "importlib", "json", "deepcopy", "UTC", "datetime", "timedelta", "Path",
                 "CodeType", "FunctionType", "ModuleType", "pytest", "rewrite_asserts", "capsule"),
    "capsule": ("argparse", "csv", "hashlib", "importlib", "io", "json", "os", "re", "stat",
                "subprocess", "sys", "tempfile", "deepcopy", "Path", "CodeType", "FunctionType"),
}


@pytest.mark.parametrize("provider,binding", [(name, key) for name, keys in IMPORT_BINDINGS.items() for key in keys])
def test_every_provider_import_binding_rejects_substitution_before_dispatch(monkeypatch, provider, binding):
    from tests.ci_web41 import collection

    original = importlib.import_module("tests.test_ci_web37_pg_lease")
    target = inputs if provider == "consumer" else capsule
    monkeypatch.setattr(target, binding, object())
    with pytest.raises(pytest.UsageError, match="canonical import binding"):
        collection.clone_pg_consumer(original)
    with pytest.raises(ValueError, match="canonical import binding"):
        inputs.clone_inputs(original)


@pytest.mark.parametrize("provider", ["consumer", "capsule"])
def test_provider_builtins_must_be_the_canonical_object(monkeypatch, provider):
    from tests.ci_web41 import collection

    original = importlib.import_module("tests.test_ci_web37_pg_lease")
    target = inputs if provider == "consumer" else capsule
    monkeypatch.setitem(vars(target), "__builtins__", dict(vars(builtins)))
    with pytest.raises(pytest.UsageError, match="builtins binding"):
        collection.clone_pg_consumer(original)
    with pytest.raises(ValueError, match="builtins binding"):
        inputs.clone_inputs(original)


@pytest.mark.parametrize("binding", ["importlib", "deepcopy", "pytest", "rewrite_asserts"])
def test_unbound_import_callbacks_do_not_execute_in_direct_or_collection_entry(monkeypatch, binding):
    from tests.ci_web41 import collection

    original = importlib.import_module("tests.test_ci_web37_pg_lease")
    calls = []
    def unbound(*args, **_kwargs):
        calls.append(True)
        return args[0] if args else None
    bad = {"importlib": SimpleNamespace(import_module=unbound), "deepcopy": unbound,
           "pytest": SimpleNamespace(mark=SimpleNamespace(parametrize=unbound)), "rewrite_asserts": unbound}[binding]
    monkeypatch.setattr(inputs, binding, bad)
    for exception, action in ((ValueError, lambda: inputs.clone_inputs(original)),
                              (pytest.UsageError, lambda: collection.clone_pg_consumer(original))):
        with pytest.raises(exception, match="binding"):
            action()
    assert not calls


@pytest.mark.parametrize("fault", ["entry-code", "entry-filename", "entry-namespace", "run-code", "run-filename", "class-new"])
def test_official_entry_identity_is_insufficient_for_a_modified_compiler(monkeypatch, fault):
    official = importlib.import_module("_pytest.assertion.rewrite")
    calls = []
    def unbound(*_args, **_kwargs):
        calls.append(True)
    entry, method = official.rewrite_asserts, official.AssertionRewriter.run
    if fault == "entry-code":
        monkeypatch.setattr(entry, "__code__", (lambda *_args, **_kwargs: None).__code__)
    elif fault == "entry-filename":
        monkeypatch.setattr(entry, "__code__", entry.__code__.replace(co_filename="unbound-compiler.py"))
    elif fault == "entry-namespace":
        fake = FunctionType(entry.__code__, dict(vars(official)), entry.__name__, entry.__defaults__)
        monkeypatch.setattr(official, "rewrite_asserts", fake)
        monkeypatch.setattr(inputs, "rewrite_asserts", fake)
    elif fault == "run-code":
        # Same official entry remains installed, matching the V2 bypass.
        monkeypatch.setattr(official.AssertionRewriter, "run", unbound)
    elif fault == "run-filename":
        monkeypatch.setattr(method, "__code__", method.__code__.replace(co_filename="unbound-compiler.py"))
    else:
        # Replacing __new__ and deleting it on the real class can leave a
        # CPython slot changed. Substitute a private class and restore identity.
        namespace = {key: value for key, value in vars(official.AssertionRewriter).items()
                     if key not in {"__dict__", "__weakref__"}}
        namespace["__new__"] = staticmethod(unbound)
        substitute = type("AssertionRewriter", official.AssertionRewriter.__bases__, namespace)
        monkeypatch.setattr(official, "AssertionRewriter", substitute)
    assert inputs.rewrite_asserts is official.rewrite_asserts
    with pytest.raises(ValueError, match="official pytest compiler"):
        inputs.compiler_reference()
    assert not calls


def test_compiler_whole_source_hash_precedes_reference_generation(monkeypatch):
    original = inputs.trusted_source
    def changed(path, limit):
        raw = original(path, limit)
        return b"#" + raw[1:] if path.name == "rewrite.py" else raw
    monkeypatch.setattr(inputs, "trusted_source", changed)
    with pytest.raises(ValueError, match="compiler source differs"):
        inputs.compiler_reference()


def test_mark_reference_does_not_execute_a_replaced_pytest_factory(monkeypatch):
    original = importlib.import_module("tests.test_ci_web37_pg_lease")
    def forbidden(*_args, **_kwargs):
        pytest.fail("A mutable mark factory generated the trusted reference")
    monkeypatch.setattr(pytest.mark, "parametrize", forbidden)
    clone, _receipt = inputs.clone_inputs(original)
    marks = clone.test_a_child_cannot_exceed_or_fabricate_its_UUID_budget.pytestmark
    assert [type(value) for value in marks[0].args[1]] == [int, int, bool, float]


def _foreign_builtin_function(function, namespace):
    prior = namespace["__builtins__"]
    namespace["__builtins__"] = dict(vars(builtins))
    try:
        result = FunctionType(function.__code__, namespace, function.__name__, function.__defaults__, function.__closure__)
    finally:
        namespace["__builtins__"] = prior
    result.__kwdefaults__, result.__annotations__ = function.__kwdefaults__, function.__annotations__
    result.__module__, result.__qualname__ = function.__module__, function.__qualname__
    result.__dict__.update(function.__dict__)
    assert result.__builtins__ is not vars(builtins)
    return result


@pytest.mark.parametrize("target", ["provider", "consumer", "compiler"])
def test_function_cached_builtins_cannot_disagree_with_canonical_namespace(monkeypatch, target):
    from tests.ci_web41 import collection

    original = importlib.import_module("tests.test_ci_web37_pg_lease")
    if target == "provider":
        fake = _foreign_builtin_function(inputs.clone_function, vars(inputs))
        monkeypatch.setattr(inputs, "clone_function", fake)
        with pytest.raises(pytest.UsageError, match="provider function differs"):
            collection.clone_pg_consumer(original)
    elif target == "consumer":
        name = "test_an_exact_finite_lease_is_accepted_without_SQL"
        fake = _foreign_builtin_function(getattr(original, name), vars(original))
        monkeypatch.setattr(original, name, fake)
        with pytest.raises(ValueError, match="namespace or defaults"):
            inputs.clone_inputs(original)
    else:
        official = importlib.import_module("_pytest.assertion.rewrite")
        fake = _foreign_builtin_function(official.rewrite_asserts, vars(official))
        monkeypatch.setattr(official, "rewrite_asserts", fake)
        monkeypatch.setattr(inputs, "rewrite_asserts", fake)
        with pytest.raises(ValueError, match="compiler CodeType or namespace"):
            inputs.compiler_reference()

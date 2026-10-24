"""Finite matching negatives and actual SQL/native control-flow probes only.

No PostgreSQL, real provider/network, compiler, package, image or desktop runs.
The native CLI executes with explicit filesystem/transport/build doubles.
"""
import ast
import copy
import importlib
import importlib.util
import json
import shutil
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.security_bandit22_contract_peer import descriptor, digest, validate_candidate
from tests.ci_web37.serial_security_transport import historical_source

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = json.loads((ROOT/"tests/data/security_bandit22_contract_candidate.json").read_bytes())
LEDGER_RAW = (ROOT/"tests/data/security_bandit22_original_ledger.RAW.json").read_bytes()


def report():
    return {"errors": [], "results": [{"filename": row["path"], "test_id": row["rule"],
        "line_number": row["line"], "col_offset": row["column"], "end_col_offset": row["end_column"],
        "line_range": row["bandit_line_range"], "code": "Untrusted scanner payload",
        "issue_text": "Untrusted scanner payload"} for row in PROPOSAL["occurrences"]]}


@pytest.fixture
def source_copy(tmp_path):
    for name in {**PROPOSAL["dependency_bindings"], **PROPOSAL["source_bindings"]}:
        target = tmp_path/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(historical_source(ROOT, name))
    return tmp_path


def test_original28_and22_unique_source_occurrences_are_preserved_without_baseline_approval(source_copy):
    assert digest(LEDGER_RAW) == PROPOSAL["original_ledger_raw_sha256"]
    ledger = json.loads(LEDGER_RAW)
    assert ledger["total"] == len(ledger["findings"]) == 28 and ledger["requires_review"] == 22
    assert sum(row["existing_unexpired_exception"] for row in ledger["findings"]) == 6
    actual = report()
    actual["results"].reverse()
    assert len(Counter(map(descriptor, actual["results"]))) == 22
    assert validate_candidate(actual, source_copy, PROPOSAL, context=PROPOSAL["context_required"]) == {
        "reviewed_occurrences": 22, "approved": False, "exceptions_applied": 0, "status": "source_match_proposal_only"}


@pytest.mark.parametrize("fault", ["missing", "extra", "duplicate-fragment", "coarse-fingerprint-collapse",
                                  "wrong-column", "wrong-rule", "wrong-line-range", "boolean-line", "float-column",
                                  "untrusted-path", "raw-errors"])
def test_each_multiset_and_span_fault_remains_blocking(source_copy, fault):
    actual = report()
    if fault == "missing":
        actual["results"].pop()
    elif fault == "extra":
        actual["results"].append(copy.deepcopy(actual["results"][0]))
    elif fault == "duplicate-fragment":
        actual["results"][-1] = copy.deepcopy(actual["results"][-2])
    elif fault == "coarse-fingerprint-collapse":
        seen = set()
        actual["results"] = [item for row, item in zip(PROPOSAL["occurrences"], actual["results"]) if row["legacy_fingerprint"] not in seen and not seen.add(row["legacy_fingerprint"])]
    elif fault == "wrong-column":
        actual["results"][-1]["col_offset"] += 1
    elif fault == "wrong-rule":
        actual["results"][-1]["test_id"] = "B310"
    elif fault == "wrong-line-range":
        actual["results"][-1]["line_range"] = [1]
    elif fault == "boolean-line":
        actual["results"][-1]["line_number"] = True
    elif fault == "float-column":
        actual["results"][-1]["col_offset"] = float(actual["results"][-1]["col_offset"])
    elif fault == "untrusted-path":
        actual["results"][-1]["filename"] = "../"+actual["results"][-1]["filename"]
    else:
        actual["errors"] = [{"reason": "Source was not scanned"}]
    with pytest.raises(ValueError):
        validate_candidate(actual, source_copy, PROPOSAL, context=PROPOSAL["context_required"])


@pytest.mark.parametrize("fault", ["source-byte", "new-operator-caller", "new-import-caller", "native-url",
                                  "native-build-stage", "schema-column", "ast-fragment-pin"])
def test_frozen_source_and_dataflow_context_cannot_be_generalized(source_copy, fault):
    candidate = copy.deepcopy(PROPOSAL)
    if fault in {"source-byte", "new-operator-caller"}:
        target = source_copy/"web/database/followup_policy.py"
        target.write_bytes(target.read_bytes()+(b"\n# changed\n" if fault == "source-byte" else b"\ndef unreviewed(request_value):\n    return _source(request_value)\n"))
    elif fault == "new-import-caller":
        (source_copy/"web/unreviewed.py").write_bytes(b"from web.database.followup_policy import _source\n")
    elif fault == "native-url":
        target = source_copy/"runtime-source/expat-sec10/source-pins.json"
        data = json.loads(target.read_bytes())
        data["psf_source_url"] = "file:///synthetic-unreviewed-source"
        target.write_text(json.dumps(data))
    elif fault == "native-build-stage":
        target = source_copy/"Dockerfile"
        target.write_bytes(target.read_bytes().replace(b"FROM psycopg-build AS expat-build", b"FROM unreviewed AS expat-build"))
    elif fault == "schema-column":
        target = source_copy/"web/database/followup_schema_v1.py"
        target.write_bytes(target.read_bytes()+b"\nSNAPSHOT=(*SNAPSHOT,'unreviewed')\n")
    else:
        candidate["occurrences"][0]["ast_sha256"] = "0"*64
    with pytest.raises(ValueError):
        validate_candidate(report(), source_copy, candidate, context=candidate["context_required"])


@pytest.mark.parametrize("context", [None, "shared-host", "web-runtime", "unverified-docker-build"])
def test_native_exceptions_are_not_approved_outside_the_named_isolated_source_context(source_copy, context):
    with pytest.raises(ValueError):
        validate_candidate(report(), source_copy, PROPOSAL, context=context)


@pytest.mark.parametrize("module", ["followup_policy", "notification_policy"])
@pytest.mark.parametrize("dialect", ["sqlite", "postgresql"])
def test_actual_policy_compilers_consume_only_a_connection_and_emit_closed_sql(module, dialect):
    subject = importlib.import_module("web.database."+module)
    statements = []
    connection = SimpleNamespace(dialect=SimpleNamespace(name=dialect),
                                 exec_driver_sql=lambda statement: statements.append(statement))
    subject.install(connection)
    assert statements and all(type(statement) is str and len(statement) < 100000 for statement in statements)
    assert not any("SYNTHETIC-UNTRUSTED-INPUT" in statement for statement in statements)
    if dialect == "postgresql":
        assert any("FORCE ROW LEVEL SECURITY" in statement for statement in statements)
        assert all("SECURITY DEFINER" not in statement for statement in statements)
    else:
        assert any("RAISE(ABORT" in statement for statement in statements)


def test_followup_interpolated_operator_arguments_are_exact_local_literals():
    tree = ast.parse((ROOT/"web/database/followup_policy.py").read_bytes())
    expected = {"_source": {"IS", "IS NOT DISTINCT FROM"}, "_projection": {"IS", "IS NOT DISTINCT FROM"},
                "_immutable": {"IS", "IS NOT DISTINCT FROM"}, "_transition": {"IS NOT", "IS DISTINCT FROM"}}
    for function, values in expected.items():
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == function]
        assert len(calls) == (3 if function == "_projection" else 2)
        assert all(len(node.args) == 1 and isinstance(node.args[0], ast.Constant) for node in calls)
        assert {node.args[0].value for node in calls} == values


@pytest.mark.parametrize("revision", ["20261020_notifications", "20261020_account_security"])
def test_actual_downgrade_queries_expand_only_frozen_identifiers_without_running_ddl(monkeypatch, revision):
    subject = importlib.import_module("web.database.alembic.versions."+revision)
    queries, dropped = [], []
    connection = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"),
        scalar=lambda query: queries.append(str(query)) or False, exec_driver_sql=lambda query: dropped.append(query))
    fake_op = SimpleNamespace(get_bind=lambda: connection, drop_table=lambda name: dropped.append(name),
        drop_column=lambda table, name: dropped.append(name), drop_index=lambda *args, **kwargs: None)
    monkeypatch.setattr(subject, "op", fake_op)
    monkeypatch.setattr(subject, "verify", lambda *args: None)
    subject.downgrade()
    if revision.endswith("notifications"):
        assert queries == ["SELECT EXISTS(SELECT 1 FROM "+name+")" for name in subject.TABLES]
    else:
        assert queries == ["SELECT EXISTS(SELECT 1 FROM usuarios WHERE "+" OR ".join(name+" IS NOT NULL" for name in subject.NAMES)+")"]


@pytest.fixture
def native():
    path = ROOT/"runtime-source/expat-sec10/rebuild_pyexpat.py"
    spec = importlib.util.spec_from_file_location("bandit22_native_peer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def native_main(native, monkeypatch, *, mode="valid", platform="linux", output="/expat-output", build=True):
    lock = native.pins()
    archive = Path("F:/MetodoBaseWeb-linux-lab-20261019/evidence/sca-native-triage31-20261019/primary/Python-3.12.15.tar.xz").read_bytes()
    assert digest(archive) == lock["psf_source_sha256"]
    if mode == "short":
        archive = archive[:-1]
    elif mode == "extra":
        archive += b"X"
    elif mode == "tampered":
        archive = bytes([archive[0]^1])+archive[1:]
    trace = []

    class DeclaredPath:
        def __init__(self, value):
            self.value = str(value)

        def __eq__(self, other):
            return isinstance(other, DeclaredPath) and self.value == other.value

        def exists(self):
            trace.append(("exists", self.value))
            return mode == "existing"

        def write_bytes(self, raw):
            trace.append(("write", self.value, len(raw), digest(raw)))

    class DeclaredResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self, bound):
            trace.append(("read", bound))
            return archive[:bound]

    def urlopen(url, timeout):
        trace.append(("urlopen", url, timeout))
        return DeclaredResponse()

    monkeypatch.setattr(native, "Path", DeclaredPath)
    monkeypatch.setattr(native, "sys", SimpleNamespace(platform=platform))
    monkeypatch.setattr(native, "os", SimpleNamespace(environ={}))
    monkeypatch.setattr(native, "pins", lambda: lock)
    monkeypatch.setattr(native, "urllib", SimpleNamespace(request=SimpleNamespace(urlopen=urlopen)))
    monkeypatch.setattr(native, "prepare", lambda *args: trace.append(("prepare",)) or {})
    monkeypatch.setattr(native, "build", lambda *args: trace.append(("build-double",)))
    monkeypatch.setattr(sys, "argv", ["review", "--output", output, *(["--build"] if build else [])])
    return native.main, trace, lock


@pytest.mark.parametrize("mode", ["short", "extra", "tampered", "existing"])
def test_native_fetch_rejects_unconfirmed_archive_before_any_write_or_prepare(native, monkeypatch, mode):
    run, trace, _ = native_main(native, monkeypatch, mode=mode)
    with pytest.raises(AssertionError):
        run()
    assert not any(row[0] in {"write", "prepare", "build-double"} for row in trace)


@pytest.mark.parametrize("platform,output,build", [("win32", "/expat-output", True),
                                                  ("linux", "/unreviewed", True),
                                                  ("linux", "/expat-output", False)])
def test_native_cli_rejects_host_or_output_or_implicit_preparation_before_fetch(native, monkeypatch, platform, output, build):
    run, trace, _ = native_main(native, monkeypatch, platform=platform, output=output, build=build)
    with pytest.raises(AssertionError):
        run()
    assert trace == []


def test_valid_native_source_uses_exact_https_pin_and_bounded_read_then_authenticates_before_write(native, monkeypatch):
    run, trace, lock = native_main(native, monkeypatch)
    run()
    assert trace == [("exists", "/tmp/psf-expat-sec10.tar.xz"),
                     ("urlopen", "https://www.python.org/ftp/python/3.12.15/Python-3.12.15.tar.xz", 60),
                     ("read", 20829825), ("write", "/tmp/psf-expat-sec10.tar.xz", 20829824, lock["psf_source_sha256"]),
                     ("prepare",), ("build-double",)]


def test_docker_invocation_is_builder_only_and_does_not_copy_the_helper_to_runtime():
    docker = (ROOT/"Dockerfile").read_text(encoding="utf8")
    stage = docker.split("FROM psycopg-build AS expat-build", 1)[1].split("\nFROM ", 1)[0]
    assert stage.count("RUN ") == 1
    assert "RUN /opt/psycopg-build-tools/bin/python -I /tmp/metodobase-expat-sec10/rebuild_pyexpat.py --build --output /expat-output" in stage
    runtime = docker.split("FROM native-runtime AS runtime", 1)[1]
    assert "rebuild_pyexpat.py" not in runtime and "/tmp/metodobase-expat-sec10" not in runtime

"""Finite metadata, isolation and privacy controls; no real backup/SQL job."""
import json
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest

from tests.ci_web41 import backup_validation as subject


def xml_bytes(mode="postgres", outcome=None):
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite", tests=str(len(subject.expected(mode))),
                          failures=str(int(outcome == "failure")), errors=str(int(outcome == "error")),
                          skipped=str(int(outcome == "skipped")))
    for index, (module, name) in enumerate(subject.expected(mode)):
        row = ET.SubElement(suite, "testcase", classname=module, name=name)
        if index == 0 and outcome:
            ET.SubElement(row, outcome, message="PRIVATE-URL-MUST-STAY-PRIVATE").text = "PRIVATE-TRACEBACK"
        ET.SubElement(row, "system-out").text = "PRIVATE-CUSTOMER-PAYLOAD"
    return ET.tostring(root)


def test_exact_two_modes_have_finite_identity_sets():
    assert len(subject.expected("job")) == len(set(subject.expected("job"))) == 46
    assert len(subject.expected("postgres")) == len(set(subject.expected("postgres"))) == 4
    assert {module for module, _ in subject.expected("postgres")} == {
        "tests.integration_backup_capture_s3_postgres", "tests.integration_backup_capture_full_postgres"}
    assert subject.CHILD_TIMEOUT <= 900 and subject.JUNIT_LIMIT == 2 * 1024 * 1024
    with pytest.raises(subject.ValidationError):
        subject.expected("unknown")


@pytest.mark.parametrize("mode", ["job", "postgres"])
def test_complete_unique_xml_returns_only_fixed_counts(mode):
    counts = subject.parse_junit(xml_bytes(mode), mode)
    assert counts == {"tests": len(subject.expected(mode)), "failures": 0, "errors": 0, "skips": 0}
    assert "PRIVATE" not in json.dumps(counts)


@pytest.mark.parametrize("kind", ["empty", "malformed", "oversized", "DTD", "direct-suite", "two-suites",
                                  "missing", "duplicate", "foreign", "wrong-class", "forged-count", "bool-count",
                                  "unknown-node", "multiple-outcomes", "nested-case", "UTF16-DTD"])
def test_partial_foreign_or_malformed_xml_cannot_seal_success(kind):
    root = ET.fromstring(xml_bytes())
    suite = root[0]
    if kind == "empty": raw = b""
    elif kind == "malformed": raw = b"<testsuites>"
    elif kind == "oversized": raw = b" " * (subject.JUNIT_LIMIT + 1)
    elif kind == "DTD": raw = b'<!DOCTYPE a [<!ENTITY x "canary">]>' + xml_bytes()
    elif kind == "UTF16-DTD": raw = ('<!DOCTYPE a [<!ENTITY x "canary">]>' + xml_bytes().decode()).encode('utf16')
    elif kind == "direct-suite": raw = ET.tostring(suite)
    else:
        if kind == "two-suites": root.append(deepcopy(suite))
        elif kind == "missing": suite.remove(suite[0])
        elif kind == "duplicate": suite[1].set("name", suite[0].get("name"))
        elif kind == "foreign": suite[0].set("name", "test_unreviewed")
        elif kind == "wrong-class": suite[0].set("classname", "foreign.module")
        elif kind == "forged-count": suite.set("tests", "0")
        elif kind == "bool-count": suite.set("tests", "True")
        elif kind == "unknown-node": ET.SubElement(suite, "private-extra")
        elif kind == "multiple-outcomes": ET.SubElement(suite[0], "failure"); ET.SubElement(suite[0], "error")
        elif kind == "nested-case": ET.SubElement(suite[0], "testcase", name="unreviewed")
        raw = ET.tostring(root)
    with pytest.raises((subject.ValidationError, ET.ParseError, UnicodeError)):
        subject.parse_junit(raw, "postgres")


@pytest.mark.parametrize("outcome,key", [("failure", "failures"), ("error", "errors"), ("skipped", "skips")])
def test_xml_outcome_counts_are_real_and_private_messages_are_not_returned(outcome, key):
    result = subject.parse_junit(xml_bytes(outcome=outcome), "postgres")
    assert result[key] == 1 and "PRIVATE" not in json.dumps(result)


@pytest.mark.parametrize("container", ["properties", "property", "system-out", "system-err"])
@pytest.mark.parametrize("outcome", ["failure", "error", "skipped"])
def test_nested_outcome_cannot_be_hidden_by_zero_suite_counters(container, outcome):
    root = ET.fromstring(xml_bytes())
    row = root[0][0]
    if container == "property":
        parent = ET.SubElement(ET.SubElement(row, "properties"), "property", name="canary", value="PRIVATE")
    elif container == "system-out":
        parent = row.find("system-out")
    else:
        parent = ET.SubElement(row, container)
    ET.SubElement(parent, outcome).text = "PRIVATE-NESTED-FAILURE"
    with pytest.raises(subject.ValidationError, match="Backup validation failed"):
        subject.parse_junit(ET.tostring(root), "postgres")


@pytest.mark.parametrize("container", ["properties", "system-out", "system-err"])
def test_duplicate_metadata_container_is_rejected(container):
    root = ET.fromstring(xml_bytes())
    row = root[0][0]
    if container != "system-out":
        ET.SubElement(row, container)
    ET.SubElement(row, container)
    with pytest.raises(subject.ValidationError):
        subject.parse_junit(ET.tostring(root), "postgres")


def test_regular_pytest_properties_and_text_output_remain_private_and_valid():
    root = ET.fromstring(xml_bytes())
    properties = ET.SubElement(root[0][0], "properties")
    ET.SubElement(properties, "property", name="canary", value="PRIVATE-PROPERTY")
    counts = subject.parse_junit(ET.tostring(root), "postgres")
    assert counts == {"tests": 4, "failures": 0, "errors": 0, "skips": 0}
    assert "PRIVATE" not in json.dumps(counts)


@pytest.fixture
def pg_values(tmp_path):
    binary = tmp_path / "18" / "bin"
    binary.mkdir(parents=True)
    for name in ("pg_dump", "pg_restore"):
        (binary / (name + (".exe" if os.name == "nt" else ""))).write_bytes(b"not executed")
    return dict(zip(subject.PG_ENV, ("isolated-pg18", "postgresql://metodobase_test_admin:PRIVATE@127.0.0.1:55491/metodobase_test_control", str(binary))))


@pytest.mark.parametrize("field,value", [
    (0, ""), (0, "production"), (1, "postgresql://metodobase_test_admin:p@outside.example/metodobase_test_x"),
    (1, "postgresql://admin:p@127.0.0.1/metodobase_test_x"), (1, "postgresql://metodobase_test_admin:p@127.0.0.1/production"),
    (1, "postgresql://metodobase_test_admin:p@127.0.0.1/metodobase_test_x?host=outside.example"), (2, "relative/bin"),
])
def test_pg_explicit_inputs_reject_remote_or_overridden_authorities(pg_values, field, value):
    pg_values[subject.PG_ENV[field]] = value
    with pytest.raises((subject.ValidationError, ValueError)):
        subject._pg_values(pg_values)


def test_child_environment_restores_only_three_pg_inputs_and_clears_inherited_secrets(tmp_path, pg_values):
    inherited = {**pg_values, "PATH": os.environ.get("PATH", ""), "AWS_SECRET_ACCESS_KEY": "PRIVATE",
                 "STRIPE_SECRET_KEY": "PRIVATE", "DATABASE_URL": "PRIVATE", "PYTHONPATH": "PRIVATE",
                 "PYTEST_ADDOPTS": "PRIVATE", "LD_PRELOAD": "PRIVATE", "GITHUB_TOKEN": "PRIVATE"}
    private = tmp_path / "private"
    private.mkdir()
    actual = subject.child_environment("postgres", private, inherited)
    assert {name: actual[name] for name in subject.PG_ENV} == pg_values
    assert all(name not in actual for name in inherited if name not in {*subject.PG_ENV, "PATH"})
    assert actual["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1" and actual["PYTHON_DOTENV_DISABLED"] == "1"
    assert {actual[name] for name in ("TEMP", "TMP", "TMPDIR")} == {str(private / "temp")}


def test_job_child_never_inherits_pg_authority(tmp_path, pg_values):
    private = tmp_path / "private"
    private.mkdir()
    actual = subject.child_environment("job", private, pg_values)
    assert not set(subject.PG_ENV) & actual.keys()


def test_child_bootstrap_calls_original_sanitizer_then_restores_only_valid_pg_values(tmp_path, monkeypatch, pg_values):
    from tests import isolation
    calls = []
    monkeypatch.setattr(subject.os, "environ", dict(pg_values))
    def prepare(**kwargs):
        calls.append(("prepare", kwargs, dict(subject.os.environ)))
        subject.os.environ["DATABASE_URL"] = "sqlite:///synthetic"
    monkeypatch.setattr(isolation, "prepare_environment", prepare)
    monkeypatch.setattr(isolation, "block_external_sockets", lambda: calls.append(("blocked",)))
    def pytest_main(args):
        calls.append(("pytest", args, dict(subject.os.environ)))
        return 0
    monkeypatch.setattr(pytest, "main", pytest_main)
    assert subject.child_main("postgres", str(tmp_path)) == 0
    assert calls[0] == ("prepare", {"discard_inherited": True}, {})
    assert calls[1] == ("blocked",)
    assert {name: calls[2][2][name] for name in subject.PG_ENV} == pg_values
    args = calls[2][1]
    assert args[:2] == list(subject.MODULES["postgres"])
    assert "--noconftest" in args and args[args.index("-o") + 1] == "addopts="
    assert "no:cacheprovider" in args and "--junitxml=" + str(tmp_path / "junit.private.xml") in args


@pytest.fixture
def fake_execution(tmp_path, monkeypatch):
    photo = {"tests/ci_web41/backup_validation.py": {"bytes": 1, "sha256": "a" * 64}}
    monkeypatch.setattr(subject, "source_photo", lambda: deepcopy(photo))
    def boundary(path):
        path.mkdir()
        return (path.stat().st_dev, path.stat().st_ino), None
    monkeypatch.setattr(subject, "_private_boundary", boundary)
    monkeypatch.setattr(subject, "_require_private", lambda *args: None)
    monkeypatch.setattr(subject, "child_environment", lambda *args: {})
    def run(mode, private, environment):
        (private / "pytest.private.log").write_bytes(b"PRIVATE postgres://secret/url")
        (private / "junit.private.xml").write_bytes(xml_bytes(mode))
        return 0, False
    monkeypatch.setattr(subject, "run_child", run)
    return photo, run


def test_only_new_public_summary_is_written_and_no_raw_canary_is_published(tmp_path, capsys, fake_execution):
    output = tmp_path / "public.json"
    assert subject.main(["--mode", "postgres", "--private", str(tmp_path / "private"), "--output", str(output)]) == 0
    value = json.loads(output.read_bytes())
    public = capsys.readouterr()
    assert value["accepted"] and value["observed_cases"] == value["passed"] == 4 and value["source_quiet"]
    assert "PRIVATE" not in output.read_text() + public.out + public.err
    assert str(tmp_path) not in output.read_text() and "test_pg18_" not in output.read_text()


@pytest.mark.parametrize("fault", ["exit", "skip", "failure", "source", "missing_xml", "timeout", "private_boundary"])
def test_forged_child_success_never_overrides_a_failed_guard(tmp_path, capsys, monkeypatch, fake_execution, fault):
    photo, original = fake_execution
    def run(mode, private, environment):
        result = original(mode, private, environment)
        if fault == "exit": return 3, False
        if fault in {"skip", "failure"}:
            (private / "junit.private.xml").write_bytes(xml_bytes(mode, "skipped" if fault == "skip" else "failure"))
        if fault == "source": photo["tests/ci_web41/backup_validation.py"]["sha256"] = "b" * 64
        if fault == "missing_xml": (private / "junit.private.xml").unlink()
        if fault == "timeout": return None, True
        return result
    monkeypatch.setattr(subject, "run_child", run)
    if fault == "private_boundary":
        monkeypatch.setattr(subject, "_require_private", lambda *args: (_ for _ in ()).throw(subject.ValidationError("private_boundary")))
    output = tmp_path / "public.json"
    assert subject.main(["--mode", "postgres", "--private", str(tmp_path / "private"), "--output", str(output)]) == 1
    value = json.loads(output.read_bytes())
    assert not value["accepted"] and value["gate_exit"] == 1
    assert value["cleanup_required"] is (fault == "timeout")
    assert "PRIVATE" not in output.read_text() + capsys.readouterr().out


@pytest.mark.parametrize("kind", ["relative", "existing", "repository"])
def test_private_and_output_paths_must_be_new_absolute_outside_source(tmp_path, kind):
    value = "relative" if kind == "relative" else str(tmp_path if kind == "existing" else subject.ROOT / "uncreated-QA-only")
    with pytest.raises(subject.ValidationError):
        subject._new_path(value)


def test_existing_output_is_never_overwritten(tmp_path, capsys, fake_execution):
    target = tmp_path / "out.json"
    target.write_bytes(b"existing-private-canary")
    assert subject.main(["--mode", "postgres", "--private", str(tmp_path / "private"), "--output", str(target)]) == 1
    assert target.read_bytes() == b"existing-private-canary" and not (tmp_path / "private").exists()
    assert "canary" not in capsys.readouterr().out


def test_invalid_arguments_and_exception_messages_are_not_echoed(tmp_path, capsys, monkeypatch):
    assert subject.main(["--mode", "PRIVATE-URL", "--private", "PRIVATE", "--output", "PRIVATE"]) == 1
    assert "PRIVATE" not in capsys.readouterr().out
    monkeypatch.setattr(subject, "validate", lambda *args: (_ for _ in ()).throw(subject.ValidationError("PRIVATE-URL")))
    assert subject.main(["--mode", "postgres", "--private", str(tmp_path / "private2"), "--output", str(tmp_path / "out2")]) == 1
    assert "PRIVATE" not in capsys.readouterr().out
    monkeypatch.setattr(subject, "validate", lambda *args: (_ for _ in ()).throw(RuntimeError("PRIVATE-URL")))
    assert subject.main(["--mode", "postgres", "--private", str(tmp_path / "private"), "--output", str(tmp_path / "out")]) == 1
    assert "PRIVATE" not in capsys.readouterr().out


def test_timeout_stops_only_the_child_pid_and_does_not_execute_cluster_cleanup(tmp_path, monkeypatch):
    events = []
    class Child:
        def wait(self, timeout):
            events.append(("wait", timeout))
            if len(events) == 1: raise subprocess.TimeoutExpired("private", timeout)
            return 0
        def terminate(self): events.append(("terminate-own-child",))
        def kill(self): events.append(("kill-own-child",))
    def popen(command, **kwargs):
        assert "PRIVATE-PASSWORD" not in " ".join(command)
        assert kwargs["env"] == {"METODOBASE_TEST_MIGRATOR_URL": "PRIVATE-PASSWORD"}
        return Child()
    monkeypatch.setattr(subject.subprocess, "Popen", popen)
    assert subject.run_child("postgres", tmp_path, {"METODOBASE_TEST_MIGRATOR_URL": "PRIVATE-PASSWORD"}) == (None, True)
    assert events == [("wait", subject.CHILD_TIMEOUT), ("terminate-own-child",), ("wait", 5)]


def test_source_photo_contains_graph_and_detects_real_file_or_membership_change(tmp_path):
    names = subject.source_photo()
    assert set(subject.SOURCE_BASE) <= names.keys()
    assert "web/database/models.py" in names and "web/storage/objects.py" in names
    for name in names:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(subject.ROOT / name, target)
    before = subject.source_photo(tmp_path)
    path = tmp_path / "web/storage/objects.py"
    path.write_bytes(path.read_bytes() + b"\n# PRIVATE local drift\n")
    assert subject.source_digest(subject.source_photo(tmp_path)) != subject.source_digest(before)
    path.write_bytes((subject.ROOT / "web/storage/objects.py").read_bytes())
    (tmp_path / "web/database/unreviewed_source.py").write_bytes(b"# private local addition\n")
    assert set(subject.source_photo(tmp_path)) == set(before) | {"web/database/unreviewed_source.py"}


def test_plain_reader_rejects_links_and_bounds_before_allocation(tmp_path):
    path = tmp_path / "sample"
    path.write_bytes(b"x" * 33)
    with pytest.raises(subject.ValidationError): subject._plain(path, 32)
    path.write_bytes(b"small")
    os.link(path, tmp_path / "alias")
    with pytest.raises(subject.ValidationError): subject._plain(path, 32)


def test_real_private_boundary_precedes_payload_and_rejects_replacement(tmp_path):
    private = tmp_path / 'owned-boundary'
    identity, sid = subject._private_boundary(private)
    subject._require_private(private, identity, sid)
    assert not (private / 'pytest.private.log').exists()
    replacement = tmp_path / 'retained-owned-boundary'
    private.rename(replacement)
    private.mkdir()
    with pytest.raises(subject.ValidationError):
        subject._require_private(private, identity, sid)


def test_pg_client_bin_is_sufficient_without_a_host_server_binary(pg_values):
    assert subject._pg_values(pg_values) == pg_values

"""Finite historical53 fixture admission controls; no SQL or provider calls."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from tests.ci_web37 import pg53, pg_lease
from tests.ci_web41 import pg53_source_fixture as fixture

ROOT = Path(__file__).resolve().parents[1]
FOUR = tuple(fixture.CURRENT_FOUR)
CURRENT = ("tests/integration_r30_ppl37_postgres.py", "tests/ci_web37/pg_close.py")
original_legacy_budgets = fixture.original_legacy_budgets


@pytest.fixture(scope="module")
def admitted():
    return fixture.source_payloads(ROOT)


def write_payloads(root, payloads):
    root.mkdir()
    for name, raw in payloads.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return root


@pytest.fixture
def actual_copy(tmp_path, monkeypatch, admitted):
    payloads = {name: (ROOT / name).read_bytes() for name in admitted}
    value = json.loads(admitted[fixture.DESCRIPTOR])
    by_oid = {value["source_bindings"][name]["Git_blob"]: admitted[name] for name in FOUR}
    monkeypatch.setattr(fixture, "git_blob", lambda root, oid, size: by_oid[oid])
    return write_payloads(tmp_path / "current", payloads)


def test_exact_four_git_objects_all_bindings_and_no_current_source_acceptance(admitted, tmp_path, original_legacy_budgets):
    value = fixture.validate_payloads(admitted)
    assert len(value["source_bindings"]) == 8 and len(value["current_fixture_bindings"]) == 2
    assert len(admitted) == 10 and set(FOUR) < set(value["source_bindings"])
    for name in FOUR:
        pin = value["source_bindings"][name]
        raw = admitted[name]
        assert raw != (ROOT / name).read_bytes()
        assert fixture.record(raw) == (pin["git_raw_bytes"], pin["git_raw_sha256"])
        assert hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw,
                            usedforsecurity=False).hexdigest() == pin["Git_blob"]
    root = write_payloads(tmp_path / "historical", admitted)
    phase = fixture.validate_fixture(root)
    assert phase == pg53.phase(root) == value
    assert len(phase["expected"]) == len({tuple(row) for row in phase["expected"]}) == 53
    assert phase["UUIDs"] == phase["concurrent_UUIDs"] == 1
    assert phase["restricted_application_pool_size"] == 5 and phase["max_overflow"] == 0
    legacy = original_legacy_budgets
    assert len(legacy) == 29 and sum(row["cases"] for row in legacy) == 429
    assert sum(row["UUIDs"] for row in legacy) == 69
    with pytest.raises(ValueError, match="original53 direct assertion or fixture source"):
        pg53.phase(ROOT)


@pytest.mark.parametrize("name", FOUR)
@pytest.mark.parametrize("mutation", ("byte", "append", "missing"))
def test_each_current_four_drift_rejects_before_git_or_creation(actual_copy, tmp_path, monkeypatch, name, mutation):
    path = actual_copy / name
    raw = path.read_bytes()
    if mutation == "missing":
        path.unlink()
    else:
        path.write_bytes(bytes([raw[0] ^ 1]) + raw[1:] if mutation == "byte" else raw + b"\n")
    calls = []
    monkeypatch.setattr(fixture, "git_blob", lambda *args: calls.append(args))
    output = tmp_path / "refused"
    with pytest.raises((ValueError, OSError)):
        fixture.materialize(actual_copy, output)
    assert calls == [] and not output.exists()


@pytest.mark.parametrize("name", CURRENT)
@pytest.mark.parametrize("mutation", ("byte", "missing"))
def test_both_current_bindings_are_required_before_restore(actual_copy, tmp_path, monkeypatch, name, mutation):
    path = actual_copy / name
    if mutation == "missing":
        path.unlink()
    else:
        raw = path.read_bytes()
        path.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
    monkeypatch.setattr(fixture, "git_blob", lambda *args: pytest.fail("Git must not run before admission"))
    with pytest.raises((ValueError, OSError)):
        fixture.materialize(actual_copy, tmp_path / "refused")
    assert not (tmp_path / "refused").exists()


@pytest.mark.parametrize("name", FOUR)
@pytest.mark.parametrize("mutation", ("byte", "missing", "current"))
def test_four_recovered_payloads_reject_mutation_or_current_code(admitted, name, mutation):
    changed = dict(admitted)
    if mutation == "missing":
        del changed[name]
    elif mutation == "current":
        changed[name] = (ROOT / name).read_bytes()
    else:
        raw = changed[name]
        changed[name] = bytes([raw[0] ^ 1]) + raw[1:]
    with pytest.raises(ValueError):
        fixture.validate_payloads(changed)


@pytest.mark.parametrize("name", FOUR)
def test_wrong_git_payload_cannot_create_fixture(actual_copy, tmp_path, monkeypatch, admitted, name):
    value = json.loads(admitted[fixture.DESCRIPTOR])
    by_oid = {value["source_bindings"][key]["Git_blob"]: admitted[key] for key in FOUR}
    by_oid[value["source_bindings"][name]["Git_blob"]] = admitted[name] + b"\n"
    monkeypatch.setattr(fixture, "git_blob", lambda root, oid, size: by_oid[oid])
    with pytest.raises(ValueError):
        fixture.materialize(actual_copy, tmp_path / "refused")
    assert not (tmp_path / "refused").exists()


@pytest.mark.parametrize("mutation", ("descriptor", "extra", "missing_descriptor", "duplicate_identity"))
def test_descriptor_and_exact_namespace_cannot_be_extended(admitted, mutation):
    changed = dict(admitted)
    if mutation == "extra":
        changed["tests/extra.py"] = b"pass\n"
    elif mutation == "missing_descriptor":
        del changed[fixture.DESCRIPTOR]
    elif mutation == "descriptor":
        changed[fixture.DESCRIPTOR] += b"\n"
    else:
        value = json.loads(changed[fixture.DESCRIPTOR])
        value["expected"][1] = value["expected"][0]
        changed[fixture.DESCRIPTOR] = json.dumps(value).encode()
    with pytest.raises(ValueError):
        fixture.validate_payloads(changed)


@pytest.mark.parametrize("name", ("tests/followup34_http.py", "tests/account_security37_owned.py",
                                  "tests/integration_schema_migrations.py"))
def test_every_other_original_source_is_authenticated(actual_copy, tmp_path, name):
    path = actual_copy / name
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError):
        fixture.materialize(actual_copy, tmp_path / "refused")
    assert not (tmp_path / "refused").exists()


def test_materialization_is_explicit_new_bounded_and_source_quiet(actual_copy, tmp_path, admitted):
    before = {name: (actual_copy / name).read_bytes() for name in admitted}
    root = fixture.materialize(actual_copy, tmp_path / "fixture")
    assert {name: (actual_copy / name).read_bytes() for name in admitted} == before
    assert {name: (root / name).read_bytes() for name in admitted} == admitted
    assert fixture.validate_fixture(root)["cases"] == 53
    with pytest.raises(ValueError, match="new canonical"):
        fixture.materialize(actual_copy, root)
    with pytest.raises(ValueError, match="new canonical"):
        fixture.materialize(actual_copy, Path("relative"))


def test_late_current_source_change_rejects_before_creation(actual_copy, tmp_path, monkeypatch, admitted):
    original = fixture.git_blob
    name = FOUR[0]
    calls = []

    def changed(root, oid, size):
        calls.append(oid)
        result = original(root, oid, size)
        if len(calls) == 1:
            path = root / name
            path.write_bytes(path.read_bytes() + b"\n")
        return result

    monkeypatch.setattr(fixture, "git_blob", changed)
    with pytest.raises(ValueError, match="changed during"):
        fixture.materialize(actual_copy, tmp_path / "refused")
    assert len(calls) == 4 and not (tmp_path / "refused").exists()


@pytest.mark.parametrize("mutation", ("extra", "changed", "missing"))
def test_materialized_fixture_remains_strict(admitted, tmp_path, mutation):
    root = write_payloads(tmp_path / "fixture", admitted)
    path = root / CURRENT[1]
    if mutation == "extra":
        (root / "unexpected.py").write_bytes(b"pass\n")
    elif mutation == "changed":
        path.write_bytes(path.read_bytes() + b"\n")
    else:
        path.unlink()
    with pytest.raises(ValueError):
        fixture.validate_fixture(root)


def test_hardlink_source_is_rejected(actual_copy, tmp_path):
    path = actual_copy / FOUR[0]
    os.link(path, tmp_path / "second-link")
    with pytest.raises(ValueError, match="single-link"):
        fixture.source_payloads(actual_copy)


def test_actual_wrong_git_object_size_and_invalid_identity_reject(admitted):
    value = json.loads(admitted[fixture.DESCRIPTOR])
    pin = value["source_bindings"][FOUR[0]]
    with pytest.raises(ValueError, match="size differs"):
        fixture.git_blob(ROOT, pin["Git_blob"], pin["git_raw_bytes"] + 1)
    with pytest.raises(ValueError, match="bounded original"):
        fixture.git_blob(ROOT, "not-an-oid", 1)
    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        fixture.git_blob(ROOT, "0" * 40, pin["git_raw_bytes"])


def test_pinned_registry_cannot_authorize_different_git_blob(admitted):
    value = json.loads(admitted[fixture.DESCRIPTOR])
    pin = copy.deepcopy(value["source_bindings"][FOUR[0]])
    pin["Git_blob"] = "0" * 40
    with pytest.raises(ValueError, match="Git object differs"):
        fixture._original(admitted[FOUR[0]], pin)


@pytest.mark.parametrize("frame", ("LF", "CRLF", "mixed"))
def test_current_four_only_accept_complete_declared_frames(frame):
    raw = (ROOT / FOUR[1]).read_bytes().replace(b"\r\n", b"\n")
    if frame == "CRLF":
        raw = raw.replace(b"\n", b"\r\n")
    if frame == "mixed":
        raw = raw.replace(b"\n", b"\r\n", 1)
        with pytest.raises(ValueError):
            fixture._current(raw, fixture.CURRENT_FOUR[FOUR[1]])
    else:
        fixture._current(raw, fixture.CURRENT_FOUR[FOUR[1]])


def test_budget_fixture_reuses_only_verified_snapshot_and_preserves_parent_globals(
        request, tmp_path_factory, monkeypatch, original_legacy_budgets):
    from tests.ci_web41 import legacy_pg_unit_capsule

    parent_budget_function = pg_lease.budgets
    cached = request.config.stash[fixture._LEGACY_SNAPSHOT]
    assert type(cached) is legacy_pg_unit_capsule.Snapshot
    body = fixture.original_legacy_budgets._get_wrapped_function()
    monkeypatch.setattr(legacy_pg_unit_capsule, "snapshot",
                        lambda *args: pytest.fail("A verified snapshot must not restart the child"))
    rows = body(request, tmp_path_factory)
    assert rows == original_legacy_budgets and rows is not original_legacy_budgets
    assert rows[0] is not original_legacy_budgets[0]
    rows[0]["cases"] = -1
    assert body(request, tmp_path_factory) == original_legacy_budgets
    assert pg_lease.budgets is parent_budget_function
    assert request.config.stash[fixture._LEGACY_SNAPSHOT] is cached


def test_forged_budget_cache_is_rejected_without_restarting_the_child(
        request, tmp_path_factory, monkeypatch, original_legacy_budgets):
    from tests.ci_web41 import legacy_pg_unit_capsule

    cached = request.config.stash[fixture._LEGACY_SNAPSHOT]
    body = fixture.original_legacy_budgets._get_wrapped_function()
    monkeypatch.setattr(legacy_pg_unit_capsule, "snapshot",
                        lambda *args: pytest.fail("A forged snapshot must refuse without a retry"))
    request.config.stash[fixture._LEGACY_SNAPSHOT] = {"budgets": original_legacy_budgets}
    try:
        with pytest.raises(ValueError, match="original child process snapshot"):
            body(request, tmp_path_factory)
    finally:
        request.config.stash[fixture._LEGACY_SNAPSHOT] = cached
    assert body(request, tmp_path_factory) == original_legacy_budgets


def test_real_pytest_consumers_receive_separate_revalidated_rows_from_one_snapshot(tmp_path):
    """Exercise fixture scheduling, rather than calling its wrapped body directly."""
    consumer = tmp_path / "test_consumer_lifecycle.py"
    consumer.write_text(textwrap.dedent('''\
        from tests.ci_web41 import pg53_source_fixture as source

        original_legacy_budgets = source.original_legacy_budgets
        seen = {}

        def test_01_mutates_only_its_own_rows(original_legacy_budgets, request):
            rows = original_legacy_budgets
            assert len(rows) == 29 and sum(row["cases"] for row in rows) == 429
            assert sum(row["UUIDs"] for row in rows) == 69
            seen["rows"] = rows
            seen["snapshot"] = request.config.stash[source._LEGACY_SNAPSHOT]
            rows[0]["cases"] = -1
            rows.append({"cases": 0, "UUIDs": 0})

        def test_02_receives_an_unmodified_independent_copy(original_legacy_budgets, request):
            rows = original_legacy_budgets
            assert len(rows) == 29 and sum(row["cases"] for row in rows) == 429
            assert sum(row["UUIDs"] for row in rows) == 69
            assert rows is not seen["rows"]
            assert all(new is not old for new, old in zip(rows, seen["rows"]))
            assert request.config.stash[source._LEGACY_SNAPSHOT] is seen["snapshot"]
    '''), encoding="utf8")
    runner = textwrap.dedent('''\
        import json, os, pathlib, sys, xml.etree.ElementTree as ET
        repository, private = map(pathlib.Path, sys.argv[1:])
        sys.path.insert(0, str(repository))
        from tests.isolation import prepare_environment, block_external_sockets
        prepare_environment(discard_inherited=True)
        block_external_sockets()
        import sqlite3, psycopg2
        def denied(*args, **kwargs):
            raise AssertionError("SQL is forbidden in a source fixture lifecycle")
        sqlite3.connect = psycopg2.connect = denied
        import pytest
        from tests.ci_web41 import legacy_pg_unit_capsule as capsule
        counts = {"snapshot_calls": 0, "api_calls": 0, "checked_calls": 0}
        codes = {capsule.snapshot.__code__: "snapshot_calls",
                 capsule.historical_budget_rows.__code__: "api_calls",
                 capsule.Snapshot.checked.__code__: "checked_calls"}
        def observe(frame, event, argument):
            if event == "call" and frame.f_code in codes:
                counts[codes[frame.f_code]] += 1
        sys.setprofile(observe)
        try:
            code = pytest.main([str(private / "test_consumer_lifecycle.py"),
                "--noconftest", "-o", "addopts=", "-p", "no:cacheprovider",
                "--rootdir", str(private), "--basetemp", str(private / "pytest-base"),
                "--junitxml", str(private / "lifecycle.private.xml"), "-q"])
        finally:
            sys.setprofile(None)
        cases = list(ET.parse(private / "lifecycle.private.xml").getroot().iter("testcase"))
        snapshots = list((private / "pytest-base").rglob("snapshot.json"))
        counts.update(pytest_exit=int(code), cases=len(cases),
                      failed=sum(any(item.tag in ("failure", "error", "skipped")
                                     for item in row) for row in cases),
                      snapshot_files=len(snapshots))
        if len(snapshots) == 1:
            actual = json.loads(snapshots[0].read_bytes())
            counts.update(child_exit=actual["child_exit"],
                          blocked_attempts=actual["blocked_attempts"],
                          child_cases=len(actual["cases"]),
                          original_rows=len(actual["budgets"]),
                          original_cases=sum(row["cases"] for row in actual["budgets"]),
                          original_UUIDs=sum(row["UUIDs"] for row in actual["budgets"]))
        (private / "lifecycle.json").write_text(json.dumps(counts), encoding="utf8")
        raise SystemExit(code)
    ''')
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(("PYTEST_", "COVERAGE_"))
                   and key not in {"PYTHONPATH", "PYTHONSTARTUP", "_METODOBASE_TEST_ROOT"}}
    temporary = tmp_path / "temporary"
    temporary.mkdir()
    environment.update(PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONDONTWRITEBYTECODE="1",
                       PYTHONUTF8="1", **{key: str(temporary) for key in ("TEMP", "TMP", "TMPDIR")})
    with (tmp_path / "lifecycle.private.log").open("xb") as stream:
        process = subprocess.run([sys.executable, "-I", "-B", "-X", "utf8", "-c", runner,
                                  str(ROOT), str(tmp_path)], cwd=tmp_path, env=environment,
                                 stdout=stream, stderr=subprocess.STDOUT, timeout=180, check=False)
    result = json.loads((tmp_path / "lifecycle.json").read_bytes())
    assert process.returncode == result["pytest_exit"] == 0
    assert result["cases"] == 2 and result["failed"] == 0
    assert result["snapshot_calls"] == result["snapshot_files"] == 1
    assert result["api_calls"] == result["checked_calls"] == 2
    assert result["child_exit"] == result["blocked_attempts"] == 0
    assert result["child_cases"] == 19
    assert (result["original_rows"], result["original_cases"], result["original_UUIDs"]) == (29, 429, 69)

"""Real isolated original19 plus finite refusal controls, without SQL or PG234."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from copy import copy, deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.ci_web41 import legacy_pg_unit_capsule as capsule

ROOT = Path(__file__).resolve().parents[1]
SPEC = capsule.manifest(ROOT)


@pytest.fixture(scope="module", autouse=True)
def database_schema():
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


@pytest.fixture(scope="module")
def real_snapshot(tmp_path_factory):
    names = ("tests.test_google33_http", "tests.test_google33_headers", "tests.test_google33_conflict_window",
             "tests.ci_web37.pg_legacy", "web.database.models")
    before = {name: (sys.modules.get(name), dict(vars(sys.modules[name])) if name in sys.modules else None) for name in names}
    original_path, original_environment = list(sys.path), dict(os.environ)
    value = capsule.snapshot(ROOT, tmp_path_factory.mktemp("legacy-original19") / "capsule")
    assert sys.path == original_path and dict(os.environ) == original_environment
    for name, (module, namespace) in before.items():
        assert sys.modules.get(name) is module
        if namespace is not None:
            assert vars(module).keys() == namespace.keys()
            assert all(vars(module)[key] is item for key, item in namespace.items())
    return value


def test_original_unit_nineteen_and_complete_budget_validators_really_execute(real_snapshot):
    value = real_snapshot.checked(ROOT, SPEC)
    assert value["child_exit"] == 0 and value["blocked_attempts"] == 0 and value["inputs_quiet"]
    assert [case["identity"] for case in value["cases"]] == SPEC["identities"]
    assert all(set(case["phases"].values()) == {"passed"} for case in value["cases"])
    assert len(value["imported_current"]) == 46
    rows = capsule.historical_budget_rows(ROOT, None, snapshot=real_snapshot)
    assert len(rows) == 29 and sum(row["cases"] for row in rows) == 429
    assert sum(row["UUIDs"] for row in rows) == 69
    assert [row["group"] for row in rows if row["pool"] != 1] == ["legacy-r24-race"]
    assert [row["group"] for row in rows if row["concurrent_UUIDs"] == 2] == ["independent-qa", "restore"]
    rows[0]["cases"] = -1
    assert capsule.historical_budget_rows(ROOT, None, snapshot=real_snapshot)[0]["cases"] > 0


def test_original_whole_validator_registry_and_unit_are_unchanged(real_snapshot):
    source = real_snapshot._private / "source"
    registry = json.loads((source / "tests/ci_web37/pg-legacy37.json").read_bytes())
    assert len(registry["groups"]) == 18
    assert sum(len(row["original_cases"]) for row in registry["groups"].values()) == 234
    assert len(registry["original_source_sha256_LF"]) == 36
    for name, pin in SPEC["historical"].items():
        raw = (source / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == pin["sha256"]
    for name in ("tests/ci_web37/pg_legacy.py", "tests/ci_web37/pg-legacy37.json", SPEC["unit"]):
        assert (ROOT / name).read_bytes().replace(b"\r\n", b"\n") == (source / name).read_bytes()


@pytest.mark.parametrize("role,name", [(role, name) for role in ("historical", "current") for name in SPEC[role]])
def test_every_source_is_authenticated_before_any_child_or_reuse(tmp_path, real_snapshot, role, name):
    original_root = real_snapshot._private / "source" if role == "historical" else ROOT
    target = tmp_path / name
    target.parent.mkdir(parents=True)
    raw = (original_root / name).read_bytes()
    target.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
    with pytest.raises(ValueError, match="source differs"):
        capsule.pinned(target, SPEC[role][name], eol=role == "current")


@pytest.mark.parametrize("fault", ["extra-file", "extra-directory", "missing", "hardlink", "mixed-eol"])
def test_source_scope_aliases_and_frames_cannot_expand(tmp_path, real_snapshot, fault):
    source = tmp_path / "source"
    shutil.copytree(real_snapshot._private / "source", source)
    name = SPEC["unit"]
    if fault == "extra-file":
        (source / "unreviewed.py").write_bytes(b"pass\n")
    elif fault == "extra-directory":
        (source / "unreviewed").mkdir()
    elif fault == "missing":
        (source / name).unlink()
    elif fault == "hardlink":
        (tmp_path / "alias.py").hardlink_to(source / name)
    else:
        path = source / name
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n", 1))
    with pytest.raises((ValueError, OSError)):
        capsule.source_photo(ROOT, source, SPEC)


@pytest.mark.parametrize("fault", ["outcomes", "missing-case", "duplicate-case", "foreign-case", "missing-phase",
    "false-exit", "false-pass", "budget-row", "budget-extra-field", "source-photo", "unknown-field", "imports",
    "blocked", "quiet", "manifest", "helper", "commit"])
def test_child_protocol_rejects_incomplete_or_fabricated_success(real_snapshot, fault):
    value = real_snapshot.checked(ROOT, SPEC)
    if fault == "outcomes":
        value["cases"][0]["phases"]["call"] = {"passed": True}
    elif fault == "missing-case":
        value["cases"].pop()
    elif fault == "duplicate-case":
        value["cases"][-1] = deepcopy(value["cases"][0])
    elif fault == "foreign-case":
        value["cases"][0]["identity"] = "unreviewed"
    elif fault == "missing-phase":
        del value["cases"][0]["phases"]["call"]
    elif fault == "false-exit":
        value["child_exit"] = 1
    elif fault == "false-pass":
        value["cases"][0]["phases"]["call"] = "failed"
    elif fault == "budget-row":
        value["budgets"][0]["UUIDs"] += 1
    elif fault == "budget-extra-field":
        value["budgets"][0]["secret"] = "synthetic-private"
    elif fault == "source-photo":
        value["source_photo_sha256"] = "not hexadecimal".ljust(64)
    elif fault == "unknown-field":
        value["private_url"] = "https://synthetic.invalid/private"
    elif fault == "imports":
        value["imported_current"] = value["imported_current"][:-1]
    elif fault == "blocked":
        value["blocked_attempts"] = True
    elif fault == "quiet":
        value["inputs_quiet"] = False
    else:
        value[{"manifest": "manifest_sha256", "helper": "helper_sha256", "commit": "parent_commit"}[fault]] = "0" * 64
    with pytest.raises((ValueError, TypeError)):
        capsule.validate_snapshot(value, SPEC, real_snapshot._helper_sha)


def test_failed_and_skipped_original_phases_are_retained_as_non_success(real_snapshot):
    for outcome in ("failed", "skipped"):
        value = real_snapshot.checked(ROOT, SPEC)
        value["cases"][0]["phases"]["call"] = outcome
        value["child_exit"] = 1
        assert capsule.validate_snapshot(value, SPEC, real_snapshot._helper_sha)["cases"][0]["phases"]["call"] == outcome


def test_snapshot_reuse_does_not_accept_fabricated_dict_or_changed_private_payload(tmp_path, real_snapshot):
    with pytest.raises(ValueError, match="process snapshot"):
        capsule.historical_budget_rows(ROOT, None, snapshot=real_snapshot.checked(ROOT, SPEC))
    with pytest.raises(ValueError, match="actual child"):
        capsule.Snapshot({}, tmp_path, "0" * 64, issued=object())
    altered = copy(real_snapshot)
    altered._private = tmp_path
    (tmp_path / "snapshot.json").write_bytes(b"{}\n")
    with pytest.raises(ValueError, match="snapshot changed"):
        capsule.historical_budget_rows(ROOT, None, snapshot=altered)


@pytest.mark.parametrize("name", ["tests.unreviewed", "tests.ci_web37.unreviewed", "web.unreviewed", "config.paths"])
def test_project_import_outside_closed_catalog_fails_before_resolution(real_snapshot, name):
    finder = capsule.ClosedSources(ROOT, real_snapshot._private / "source", SPEC)
    with pytest.raises(ImportError, match="outside finite"):
        finder.find_spec(name)


def test_loader_executes_verified_source_without_implicit_pyc_reader(tmp_path, real_snapshot, monkeypatch):
    source = tmp_path / "source"
    path = source / "tests/__init__.py"
    path.parent.mkdir(parents=True)
    path.write_bytes((real_snapshot._private / "source/tests/__init__.py").read_bytes())
    cache = path.parent / "__pycache__"
    cache.mkdir()
    (cache / "__init__.cpython-312.pyc").write_bytes(b"untrusted-pyc")
    def refused(*_args, **_kwargs):
        pytest.fail("An implicit/unbounded source or pyc reader ran")
    monkeypatch.setattr(Path, "read_bytes", refused)
    monkeypatch.setattr(importlib.machinery.SourceFileLoader, "get_code", refused)
    finder = capsule.ClosedSources(ROOT, source, SPEC)
    spec = finder.find_spec("tests")
    module = importlib.util.module_from_spec(spec)
    finder.exec_module(module)
    assert module.__doc__ == "MetodoBase regression tests and isolated execution helpers."


@pytest.mark.parametrize("field", ["st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns"])
def test_open_handle_identity_cannot_drift_during_bounded_read(tmp_path, monkeypatch, field):
    target = tmp_path / "bounded"
    target.write_bytes(b"bounded")
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
    with pytest.raises(ValueError, match="opened file changed"):
        capsule.read_bounded(target, 7)


def test_size_and_hardlink_refusals_precede_open(tmp_path, monkeypatch):
    target = tmp_path / "bounded"
    target.write_bytes(b"bounded")
    def refused(*_args, **_kwargs):
        pytest.fail("Invalid input was opened")
    monkeypatch.setattr(Path, "open", refused)
    with pytest.raises(ValueError):
        capsule.read_bounded(target, 6)
    (tmp_path / "alias").hardlink_to(target)
    with pytest.raises(ValueError):
        capsule.read_bounded(target, 7)


def test_private_output_requires_new_canonical_external_directory(tmp_path):
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(ValueError):
        capsule.fresh(existing, ROOT)
    with pytest.raises(ValueError):
        capsule.fresh(ROOT / "unreviewed-capsule", ROOT)
    with pytest.raises(ValueError):
        capsule.fresh(Path("relative"), ROOT)


def test_child_actually_denies_database_socket_and_process_transport(tmp_path):
    script = ('import importlib.util,pathlib,sys; '
        f'p=pathlib.Path({str(ROOT / "tests/ci_web41/legacy_pg_unit_capsule.py")!r}); '
        's=importlib.util.spec_from_file_location("child_transport",p); '
        'm=importlib.util.module_from_spec(s);s.loader.exec_module(m); '
        'b=m.deny_transports(); import sqlite3,socket,subprocess,psycopg2; '
        'calls=[lambda:sqlite3.connect(":memory:"),lambda:socket.socket().bind(("127.0.0.1",0)), '
        'lambda:subprocess.Popen(["unreviewed-process"]),lambda:psycopg2.connect("synthetic")]; '
        '\nfor f in calls:\n try:f()\n except RuntimeError:pass\n else:raise AssertionError("Transport admitted")\n'
        'assert len(b)==4\n')
    result = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", script],
                            cwd=tmp_path, capture_output=True, timeout=30, check=False)
    assert result.returncode == 0


def test_normal_validator_still_rejects_current_three_and_cli_does_not_echo_private_args():
    result = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c",
        "from tests.ci_web37.pg_legacy import specification; specification()"],
        cwd=ROOT, capture_output=True, timeout=30, check=False)
    assert result.returncode != 0 and b"ValueError" in result.stderr
    secret = "https://synthetic.invalid/private-marker"
    result = subprocess.run([sys.executable, "-B", "-X", "utf8", str(ROOT / "tests/ci_web41/legacy_pg_unit_capsule.py"),
        "--unreviewed", secret], capture_output=True, check=False, timeout=30)
    assert result.returncode != 0 and secret.encode() not in result.stdout + result.stderr


@pytest.mark.parametrize("raw", [b'{"child_exit":1,"child_exit":0}',
    b'{"phases":{"call":"failed","call":"passed"}}'])
def test_duplicate_json_cannot_replace_failed_outcome_with_passed(raw):
    with pytest.raises(ValueError, match="Duplicate"):
        capsule.decode(raw)


def test_failed_capsule_is_not_retried_once_per_delegated_identity(monkeypatch, request):
    calls = []
    def failed(*_args, **_kwargs):
        calls.append(None)
        raise ValueError("Synthetic child failed")
    monkeypatch.setattr(capsule, "snapshot", failed)
    collector = capsule.collector(ROOT / SPEC["unit"], request.session)
    for _ in range(2):
        with pytest.raises(ValueError, match="verified receipt"):
            collector.result()
    assert len(calls) == 1


@pytest.mark.parametrize("name", capsule.CURRENT_REFERENCES)
def test_dispatch_does_not_hide_a_changed_current_original_unit_or_guard(tmp_path, name):
    target = tmp_path / capsule.MANIFEST
    target.parent.mkdir(parents=True)
    target.write_bytes((ROOT / capsule.MANIFEST).read_bytes())
    for reference in capsule.CURRENT_REFERENCES:
        target = tmp_path / reference
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / reference).read_bytes())
    target = tmp_path / name
    raw = target.read_bytes()
    target.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
    with pytest.raises(ValueError, match="source differs"):
        capsule.manifest(tmp_path)


@pytest.mark.parametrize("shadow", ["repository-pytest", "cwd-pytest", "bootstrap-csv", "bootstrap-json"])
def test_real_isolated_child_never_executes_untracked_external_or_bootstrap_shadow(tmp_path, real_snapshot, shadow):
    repository = tmp_path / "repository"
    for name in {*SPEC["current"], *capsule.CURRENT_REFERENCES, capsule.MANIFEST}:
        target = repository / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    private = tmp_path / "private"
    private.mkdir()
    source = private / "source"
    shutil.copytree(real_snapshot._private / "source", source)
    bootstrap = tmp_path / "bootstrap"
    bootstrap.mkdir()
    helper = bootstrap / "legacy_pg_unit_capsule.py"
    raw = (ROOT / "tests/ci_web41/legacy_pg_unit_capsule.py").read_bytes()
    helper.write_bytes(raw)
    hostile_cwd = tmp_path / "hostile-cwd"
    hostile_cwd.mkdir()
    marker = private / "SHADOW_EXECUTED"
    if shadow == "repository-pytest":
        target = repository / "pytest.py"
    elif shadow == "cwd-pytest":
        target = hostile_cwd / "pytest.py"
    else:
        target = bootstrap / (shadow.removeprefix("bootstrap-") + ".py")
    target.write_text(f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n"
                      "raise RuntimeError('Untracked shadow executed')\n", encoding="utf8")
    before = capsule.source_photo(repository, source, SPEC)
    environment = {key: value for key, value in os.environ.items() if not key.startswith(("PYTEST_", "COVERAGE_"))}
    environment.update(PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONPATH=str(bootstrap),
        _METODOBASE_TEST_ROOT=str(private / "metodobase-test-data"))
    environment.update({key: str(private) for key in ("TEMP", "TMP", "TMPDIR")})
    helper_sha = hashlib.sha256(raw).hexdigest()
    result = subprocess.run(capsule.child_command(helper, repository, source, private, helper_sha),
        cwd=hostile_cwd, env=environment, capture_output=True, timeout=90, check=False)
    assert not marker.exists()
    assert result.returncode == 0
    value = capsule.validate_snapshot(capsule.decode((private / "snapshot.json").read_bytes()), SPEC, helper_sha)
    assert value["isolated_bootstrap"] and not value["external_project_search_paths"]
    assert len(value["cases"]) == 19 and value["child_exit"] == 0
    assert len(value["budgets"]) == 29 and value["blocked_attempts"] == 0
    assert capsule.source_photo(repository, source, SPEC) == before


@pytest.mark.parametrize("fault", ["isolated_bootstrap", "external_project_search_paths"])
def test_protocol_cannot_claim_success_with_unsafe_import_boundary(real_snapshot, fault):
    value = real_snapshot.checked(ROOT, SPEC)
    value[fault] = not value[fault]
    with pytest.raises(ValueError, match="authority"):
        capsule.validate_snapshot(value, SPEC, real_snapshot._helper_sha)


@pytest.mark.parametrize("location", ["repository", "source", "cwd", "relative"])
def test_external_resolution_excludes_every_project_search_location(real_snapshot, location):
    source = real_snapshot._private / "source"
    finder = capsule.TrustedExternal(ROOT, source)
    path = {"repository": ROOT, "source": source, "cwd": Path.cwd(), "relative": Path("relative")}[location]
    assert not finder.allowed(path)
    with pytest.raises(ImportError, match="outside trusted"):
        finder.find_spec("unreviewed_external", path=[str(path)])


def test_child_rejects_nonisolated_direct_entry_before_project_import():
    assert not sys.flags.isolated
    with pytest.raises(ValueError, match="isolated interpreter"):
        capsule.child(ROOT, ROOT, ROOT, "0" * 64)

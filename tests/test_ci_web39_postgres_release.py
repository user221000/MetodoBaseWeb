"""Release wiring and Linux child-identity negatives; no SQL or service starts."""
import ast
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.ci_web39 import pg_admission, pg_contract, pg_tools_linux
from tests.ci_web39 import run_postgres as runner


@pytest.fixture(scope="session", autouse=True)
def database_schema():
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


@pytest.mark.parametrize("name", ["core", "restore"])
def test_current39_catalog_matches_every_original_function_without_import_or_omission(name):
    selected = pg_contract.phase(name)
    nodes = ast.parse((pg_contract.ROOT / selected["module"]).read_bytes())
    names = [node.name for node in nodes.body if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")]
    assert names == list(runner.CASES[name])
    assert len(runner.identities(name)) == (4 if name == "core" else 1)
    assert selected["UUIDs"] == (1 if name == "core" else 2)
    assert selected["concurrent_UUIDs"] == selected["application_pool"] == 1


def core_evidence(directory):
    value = {"FileSetDigest": "a" * 64}
    runtime = {"phase": "core", "contract_sha256": pg_contract.digest(value),
               "FileSetDigest": value["FileSetDigest"], "created_UUIDs": 1,
               "normally_closed_UUIDs": 1, "max_concurrent_UUIDs": 1}
    physical = {"revision": "20261023_privacy_disposition", "ORM_tables_observed": 44,
                "physical_tables_observed": 45, "FORCE_RLS_observed": 35,
                "role_five_flags": [False] * 5, "application_pool": 1, "overflow": 0,
                "protected_tables_FORCE_RLS": ["privacy_requests", "privacy_disposition_items", "product_analytics_facts"]}
    (directory / "pg39-core-runtime.json").write_text(json.dumps(runtime), encoding="utf8")
    (directory / "pg39-core-physical.json").write_text(json.dumps(physical), encoding="utf8")
    return value, runtime, physical


def test_actual39_runtime_and_physical_witnesses_are_both_required(tmp_path):
    value, _, _ = core_evidence(tmp_path)
    assert runner.require_runtime_evidence(tmp_path, "core", value) == 1
    (tmp_path / "pg39-core-physical.json").unlink()
    with pytest.raises(FileNotFoundError):
        runner.require_runtime_evidence(tmp_path, "core", value)


@pytest.mark.parametrize("field,bad", [("created_UUIDs", 0), ("normally_closed_UUIDs", 0),
                                     ("created_UUIDs", True), ("max_concurrent_UUIDs", 2),
                                     ("FileSetDigest", "b" * 64), ("contract_sha256", "b" * 64)])
def test_runtime_missing_closure_budget_or_source_refuses(tmp_path, field, bad):
    value, runtime, _ = core_evidence(tmp_path)
    runtime[field] = bad
    (tmp_path / "pg39-core-runtime.json").write_text(json.dumps(runtime), encoding="utf8")
    with pytest.raises(ValueError):
        runner.require_runtime_evidence(tmp_path, "core", value)


@pytest.mark.parametrize("field,bad", [("revision", "20261020_account_security"), ("ORM_tables_observed", 41),
                                     ("physical_tables_observed", 42), ("FORCE_RLS_observed", 34),
                                     ("role_five_flags", [True, False, False, False, False]),
                                     ("application_pool", 2), ("overflow", 1),
                                     ("protected_tables_FORCE_RLS", ["privacy_requests"])])
def test_historical_or_privileged_physical_witness_never_accepts39(tmp_path, field, bad):
    value, _, physical = core_evidence(tmp_path)
    physical[field] = bad
    (tmp_path / "pg39-core-physical.json").write_text(json.dumps(physical), encoding="utf8")
    with pytest.raises(ValueError):
        runner.require_runtime_evidence(tmp_path, "core", value)


def test_incomplete_or_relative_pytest_authority_refuses_before_contract(monkeypatch):
    observed = []
    monkeypatch.setattr(pg_contract, "checked_runtime", lambda *_: observed.append("contract"))
    values = {"pg39_phase": "core", "pg39_profile": None, "pg39_generation": Path("relative"), "pg39_ack": Path("relative")}
    config = SimpleNamespace(getoption=lambda name: values[name])
    with pytest.raises(pytest.UsageError):
        pg_admission.pytest_configure(config)
    values["pg39_profile"] = Path("relative")
    with pytest.raises(pytest.UsageError):
        pg_admission.pytest_configure(config)
    assert observed == []


def test_explicit_admission_restores_only_its_four_values_after_test_isolation(monkeypatch, tmp_path):
    observed = []
    monkeypatch.setattr(pg_contract, "checked_runtime", lambda phase: observed.append(phase))
    values = {"pg39_phase": "restore", "pg39_profile": tmp_path / "profile.json",
              "pg39_generation": tmp_path / "generation.json", "pg39_ack": tmp_path / "ack.json"}
    for key in pg_admission.OPTIONS:
        monkeypatch.setenv(key, "")
    monkeypatch.setenv("PGPASSWORD", "")
    pg_admission.pytest_configure(SimpleNamespace(getoption=lambda name: values[name]))
    import os
    assert observed == ["restore"] and os.environ["PGPASSWORD"] == ""
    assert {key: os.environ[key] for key in pg_admission.OPTIONS} == {
        key: str(values[option]) for key, option in pg_admission.OPTIONS.items()}


@pytest.mark.parametrize("bad", ["missing_target", "missing_tool", "not_waited", "active_backend", "nonzero_exit", "boolean_exit"])
def test_restore_needs_both_tool_phases_exact_tools_and_ordinary_drain(tmp_path, bad):
    value = {"FileSetDigest": "c" * 64}
    runtime = {"phase": "restore", "contract_sha256": pg_contract.digest(value), "FileSetDigest": value["FileSetDigest"],
               "created_UUIDs": 2, "normally_closed_UUIDs": 2, "max_concurrent_UUIDs": 1}
    (tmp_path / "pg39-restore-runtime.json").write_text(json.dumps(runtime), encoding="utf8")
    for phase, count in (("source", 2), ("target", 1)):
        rows = [{"normally_waited": True, "exit_code": 0, "fresh_absent_after_wait": True} for _ in range(count)]
        if phase == "target":
            if bad == "missing_target": continue
            if bad == "missing_tool": rows = []
            if bad == "not_waited": rows[0]["normally_waited"] = False
            if bad == "active_backend": rows[0]["fresh_absent_after_wait"] = False
            if bad == "nonzero_exit": rows[0]["exit_code"] = 1
            if bad == "boolean_exit": rows[0]["exit_code"] = False
        report = {"phase": phase, "FileSetDigest": value["FileSetDigest"], "tools": rows,
                  "no_process_or_backend_termination_by_observer": True}
        (tmp_path / ("pg39-restore-" + phase + "-tools.json")).write_text(json.dumps(report), encoding="utf8")
    with pytest.raises((ValueError, FileNotFoundError)):
        runner.require_runtime_evidence(tmp_path, "restore", value)


def linux_child(monkeypatch, tmp_path, *, zombie=False, wrong_executable=False, absent_live_executable=False):
    executable = tmp_path / "pg_restore"
    executable.write_bytes(b"synthetic executable identity")
    events = []
    class ProcPath:
        def __init__(self, value): self.value = value
        def __truediv__(self, value): return ProcPath(self.value + "/" + value)
        def read_text(self, **_):
            events.append(self.value)
            if self.value.endswith("/stat"):
                return "71 (pg_restore) " + ("Z" if zombie else "S") + " " + " ".join(["0"] * 18 + ["711"])
            assert self.value == "/proc/sys/kernel/random/boot_id"
            return "fake-boot-id"
        def resolve(self, **_):
            assert self.value == "/proc/71/exe"
            if zombie or absent_live_executable: raise FileNotFoundError
            return tmp_path / "foreign" if wrong_executable else executable
    def path(*parts):
        value = "/".join(str(item).rstrip("/") for item in parts)
        return ProcPath(value) if value.startswith("/proc") else Path(*parts)
    monkeypatch.setattr(pg_tools_linux, "Path", path)
    monkeypatch.setattr(pg_tools_linux, "sys", SimpleNamespace(platform="linux"))
    monkeypatch.setattr(pg_tools_linux, "os", SimpleNamespace(
        pidfd_open=lambda pid, flags: (events.append(("pidfd", pid, flags)) or 91),
        close=lambda fd: events.append(("close", fd))))
    process = SimpleNamespace(pid=71, returncode=None, args=[str(executable), "--list"])
    return process, events


@pytest.mark.parametrize("zombie", [False, True])
def test_pidfd_precedes_birth_and_fast_zombie_does_not_invent_live_executable(monkeypatch, tmp_path, zombie):
    process, events = linux_child(monkeypatch, tmp_path, zombie=zombie)
    identity = pg_tools_linux.native(process)
    assert events[0] == ("pidfd", 71, 0)
    assert identity["start_ticks"] == 711 and identity["pid"] == 71
    assert identity["executable_observed_while_alive"] is (not zombie)
    assert identity["executable_authority"] == "absolute_hash_bound_direct_Popen_no_shell"
    assert process._pg39_pidfd == 91 and process._pg39_identity == identity


@pytest.mark.parametrize("bad", ["wrong_executable", "absent_live_executable"])
def test_foreign_or_unobservable_live_exec_releases_pidfd_and_refuses(monkeypatch, tmp_path, bad):
    process, events = linux_child(monkeypatch, tmp_path, **{bad: True})
    with pytest.raises(ValueError):
        pg_tools_linux.native(process)
    assert events[-1] == ("close", 91)
    assert not hasattr(process, "_pg39_pidfd")


@pytest.mark.parametrize("bad", ["unwaited", "unsignalled", "identity_changed", "pid_changed"])
def test_closure_needs_same_identity_ordinary_wait_and_original_signalled_pidfd(monkeypatch, tmp_path, bad):
    process, _ = linux_child(monkeypatch, tmp_path)
    identity = pg_tools_linux.native(process)
    process.returncode = None if bad == "unwaited" else 0
    monkeypatch.setattr(pg_tools_linux, "signalled", lambda _: bad != "unsignalled")
    if bad == "identity_changed": process._pg39_identity = {**identity, "start_ticks": 712}
    if bad == "pid_changed": process.pid = 72
    with pytest.raises(ValueError):
        pg_tools_linux.confirm_closed(process, identity)


def test_signalled_waited_original_pidfd_accepts_without_post_exit_proc_query(monkeypatch, tmp_path):
    process, events = linux_child(monkeypatch, tmp_path)
    identity = pg_tools_linux.native(process)
    initial = list(events)
    process.returncode = 0
    monkeypatch.setattr(pg_tools_linux, "signalled", lambda _: True)
    value = pg_tools_linux.confirm_closed(process, identity)
    assert value["original_pidfd_signalled"] is True and value["exit_code"] == 0
    assert value["post_exit_process_identity_query_performed"] is False and events == initial
    pg_tools_linux.release(process)
    assert events[-1] == ("close", 91) and process._pg39_pidfd is None


def test_live_original_pidfd_cannot_be_released(monkeypatch, tmp_path):
    process, events = linux_child(monkeypatch, tmp_path)
    pg_tools_linux.native(process)
    monkeypatch.setattr(pg_tools_linux, "signalled", lambda _: False)
    with pytest.raises(ValueError): pg_tools_linux.release(process)
    assert ("close", 91) not in events


@pytest.mark.parametrize("kwargs", [{"shell": True}, {"executable": "/foreign/tool"},
                                  {"preexec_fn": lambda: None}, {"creationflags": 1}])
def test_fast_zombie_cannot_hide_executable_override_shell_or_preexec(kwargs):
    with pytest.raises(ValueError):
        pg_tools_linux.require_direct_spawn(kwargs)


def test_ordinary_product_linux_spawn_stays_direct():
    pg_tools_linux.require_direct_spawn({"creationflags": 0, "stdin": -3, "stdout": -3, "stderr": -3})


def test_workflow_separates_historical37_and_requires_both_actual39_phases():
    import yaml
    jobs = yaml.safe_load((pg_contract.ROOT / ".github/workflows/ci.yml").read_bytes())["jobs"]
    historical = jobs["historical37-postgres"]
    checkout = next(row for row in historical["steps"] if row.get("uses") == "actions/checkout@v4")
    assert checkout["with"]["ref"] == "878082b242cdfa23e1e4c134f675c12b535a2cd7"
    current = jobs["current-postgres"]
    commands = "\n".join(row.get("run", "") for row in current["steps"])
    assert "tests/ci_web39/run_postgres.py --phase core" in commands
    assert "tests/ci_web39/run_postgres.py --phase restore" in commands
    assert "tests/ci_web37/run_postgres.py" not in commands
    assert "current-postgres" in jobs["ci-success"]["needs"]
    assert "historical37-postgres" in jobs["ci-success"]["needs"]
    stop = next(row for row in current["steps"] if "ci_cluster stop" in row.get("run", ""))
    assert stop["if"] == "always()"


def test_workflow_keeps_browser33_historical_and_binds_startup39_to_built_image57():
    import yaml
    jobs = yaml.safe_load((pg_contract.ROOT / ".github/workflows/ci.yml").read_bytes())["jobs"]
    historical = jobs["historical33-image"]
    checkout = next(row for row in historical["steps"] if row.get("uses") == "actions/checkout@v4")
    assert checkout["with"]["ref"] == "c86d1a25fcd0b0befcb4b473c4144917122109fb"
    commands = "\n".join(row.get("run", "") for row in jobs["current-image"]["steps"])
    assert "tests/run_current_image57.py" in commands and "--source" in commands and "--build-probe" in commands
    assert "tests.ci_image57.current39_startup" in commands
    assert "runtime-input-contract.json" in commands and "--contract-sha256" in commands
    assert "'--image-id',value['image_id']" in commands
    assert "tests/ci_google33/run_current_browser.py" not in commands
    assert "historical33-image" in jobs["ci-success"]["needs"]


def test_source_bound_contract_includes_admission_runner_and_linux_observer():
    for name in ("pg_admission.py", "run_postgres.py", "pg_tools_linux.py"):
        assert "tests/ci_web39/" + name in pg_contract.BOUND


@pytest.mark.parametrize("name,target", [("privacy39current", "privacy390"),
                                        ("test_pg39_restores_current", "test_pg39_restores_10")])
def test_closed_pytest_alias_recognizes_only_numbered_sibling(tmp_path, name, target):
    base = tmp_path / "pytest-data"
    assert runner.pytest_alias_target(base / name, str(base / target), base) == base / target


@pytest.mark.parametrize("name,target", [("privacy39current", "../outside0"),
                                        ("privacy39current", "other0"),
                                        ("privacy39current", "privacy39payload"),
                                        ("privacy39current", "child/privacy390"),
                                        ("privacy39payload", "privacy390"),
                                        ("current", "0")])
def test_unknown_pytest_alias_never_authorizes_unlink(tmp_path, name, target):
    base = tmp_path / "pytest-data"
    with pytest.raises(ValueError):
        runner.pytest_alias_target(base / name, str(base / target), base)


def test_relative_target_and_alias_outside_private_pytest_root_are_rejected(tmp_path):
    base = tmp_path / "pytest-data"
    with pytest.raises(ValueError):
        runner.pytest_alias_target(base / "privacy39current", "privacy390", base)
    with pytest.raises(ValueError):
        runner.pytest_alias_target(tmp_path / "privacy39current", str(tmp_path / "privacy390"), base)


def test_phase_evidence_has_its_own_real_private_boundary_before_fixture_payload(monkeypatch, tmp_path):
    from web.services import legacy_object_apply_boundary as boundary
    events = []
    create, verify = runner._private_evidence, boundary.verify
    def constructor(path):
        events.append("create")
        result = create(path)
        events.append("boundary_created")
        return result
    def strict(path, *, directory=False):
        assert path == tmp_path / "evidence" and directory is True
        verify(path, directory=directory)
        events.append("fixture_verifier_passed")
    monkeypatch.setattr(runner, "_private_evidence", constructor)
    monkeypatch.setattr(boundary, "verify", strict)
    directory = runner.phase_evidence(tmp_path)
    assert directory == tmp_path / "evidence"
    assert events == ["create", "boundary_created", "fixture_verifier_passed"]
    # Re-run the untouched native/0700 verifier independently. This is a real
    # filesystem boundary check, with no database or subprocess doubles.
    verify(directory, directory=True)
    assert not list(directory.glob("pg39-*.json"))


def test_phase_evidence_cannot_admit_an_unverified_directory(monkeypatch, tmp_path):
    requested = []
    def absent(path):
        requested.append(path)
        return path
    monkeypatch.setattr(runner, "_private_evidence", absent)
    with pytest.raises(OSError, match="private_boundary_unavailable"):
        runner.phase_evidence(tmp_path)
    assert requested == [tmp_path / "evidence"]
    assert not (tmp_path / "evidence").exists()

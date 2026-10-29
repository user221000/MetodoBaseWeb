"""Compile actual CI publisher guards; refuse before tools, SQL or payload."""
import builtins
import re
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
HISTORICAL37 = "878082b242cdfa23e1e4c134f675c12b535a2cd7"


class BeforeTool(Exception):
    pass


def publisher():
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_bytes())
    historical = workflow["jobs"]["historical37-postgres"]
    checkout = next(row for row in historical["steps"] if row.get("uses") == "actions/checkout@v4")
    assert checkout["with"]["ref"] == HISTORICAL37
    step = next(row for row in historical["steps"]
                if row.get("name", "").startswith("CI-only fresh loopback cluster"))
    matches = re.findall(r"<<'PY'\n(.*?)\nPY(?:\n|$)", step["run"], re.S)
    assert len(matches) == 1
    return compile(matches[0], "actual_historical37_postgres_workflow_publisher", "exec")


def execute_guard(environment, *, head=HISTORICAL37, uid=1001, ancestor=True):
    calls = []

    def forbidden(*args, **kwargs):
        pytest.fail("The CI context must be rejected before SQL, socket or private payload")

    def version_check(*args, **kwargs):
        calls.append(args[0])
        raise BeforeTool

    def ancestry_check(argv, **kwargs):
        assert argv == ["git", "--no-replace-objects", "merge-base", "--is-ancestor", HISTORICAL37, environment["GITHUB_SHA"]]
        assert kwargs == {"check": True}
        calls.append(argv)
        if not ancestor:
            raise subprocess.CalledProcessError(1, argv)
        return SimpleNamespace(returncode=0)

    def umask(mask):
        if type(mask) is not int or mask != 0o077:
            raise AssertionError("The real publisher must request its exact private umask")
        return 0o022  # Declared previous mask only; never change the process umask.

    fake = {
        "os": SimpleNamespace(environ=environment, name="posix", geteuid=lambda: uid, umask=umask),
        "subprocess": SimpleNamespace(check_output=version_check, run=ancestry_check),
        "socket": SimpleNamespace(socket=forbidden),
        "scripts.scan_secrets": SimpleNamespace(_private_evidence=forbidden),
        "tests.ci_web37.prepare_collection": SimpleNamespace(source_photo=lambda: {"HEAD": head, "files": {}}),
        "tests.ci_web37.pg_lease": SimpleNamespace(contract=forbidden, digest=forbidden),
        "tests.ci_web37.pg53": SimpleNamespace(contract=forbidden),
        "tests.billing13_legacy_apply37_pg_contract": SimpleNamespace(build_contract=forbidden, ci_generation=forbidden),
        "tests.ci_web37.pg_plan": SimpleNamespace(phases=forbidden),
    }

    def importer(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "psycopg2":
            forbidden()
        return fake[name] if name in fake else builtins.__import__(name, globals, locals, fromlist, level)

    namespace = {"__builtins__": {**vars(builtins), "__import__": importer}}
    try:
        exec(publisher(), namespace)
    finally:
        environment["observed_version_tool_calls"] = calls


def test_local_mismatched_or_privileged_context_is_rejected_before_any_tool_or_SQL():
    valid = {"GITHUB_ACTIONS": "true", "GITHUB_WORKSPACE": str(ROOT), "GITHUB_SHA": "a" * 40}
    variants = [(dict(valid, GITHUB_ACTIONS="false"), HISTORICAL37, 1001),
                (dict(valid, GITHUB_WORKSPACE=str(ROOT.parent)), HISTORICAL37, 1001),
                (dict(valid, GITHUB_SHA="not-a-commit"), HISTORICAL37, 1001),
                (dict(valid), "b" * 40, 1001), (dict(valid), HISTORICAL37, 0)]
    for environment, head, uid in variants:
        with pytest.raises(AssertionError):
            execute_guard(environment, head=head, uid=uid)
        assert environment["observed_version_tool_calls"] == []


def test_exact_CI_context_reaches_only_the_fake_pinned_version_check():
    environment = {"GITHUB_ACTIONS": "true", "GITHUB_WORKSPACE": str(ROOT), "GITHUB_SHA": "a" * 40}
    with pytest.raises(BeforeTool):
        execute_guard(environment)
    calls = environment["observed_version_tool_calls"]
    assert len(calls) == 2
    assert calls[0] == ["git", "--no-replace-objects", "merge-base", "--is-ancestor", HISTORICAL37, "a" * 40]
    assert calls[1][1] == "--version"
    assert Path(calls[1][0]).as_posix() == "/usr/lib/postgresql/17/bin/postgres"


def test_historical_source_outside_requested_ancestry_refuses_before_PG_SQL_or_payload():
    environment = {"GITHUB_ACTIONS": "true", "GITHUB_WORKSPACE": str(ROOT), "GITHUB_SHA": "a" * 40}
    with pytest.raises(subprocess.CalledProcessError):
        execute_guard(environment, ancestor=False)
    assert environment["observed_version_tool_calls"] == [
        ["git", "--no-replace-objects", "merge-base", "--is-ancestor", HISTORICAL37, "a" * 40]]


@pytest.mark.parametrize("fault", ["local", "workspace", "privileged", "platform"])
def test_actual39_cluster_rejects_wrong_context_before_tools_SQL_or_private_workspace(monkeypatch, fault):
    from scripts import scan_secrets
    from tests import billing13_legacy_apply37_pg_contract as contract
    from tests.ci_web39 import ci_cluster
    def forbidden(*args, **kwargs):
        pytest.fail("A rejected current39 context reached a tool, socket, SQL or private payload")
    environment = {"GITHUB_ACTIONS": "true", "GITHUB_WORKSPACE": str(ROOT), "GITHUB_SHA": "a" * 40}
    if fault == "local": environment["GITHUB_ACTIONS"] = "false"
    if fault == "workspace": environment["GITHUB_WORKSPACE"] = str(ROOT.parent)
    monkeypatch.setattr(ci_cluster, "os", SimpleNamespace(name="nt" if fault == "platform" else "posix",
        environ=environment, geteuid=lambda: 0 if fault == "privileged" else 1001))
    monkeypatch.setattr(ci_cluster, "subprocess", SimpleNamespace(check_output=forbidden, run=forbidden))
    monkeypatch.setattr(ci_cluster, "socket", SimpleNamespace(socket=forbidden))
    monkeypatch.setattr(contract, "private_workspace", forbidden)
    monkeypatch.setattr(scan_secrets, "_private_evidence", forbidden)
    with pytest.raises(ValueError, match="exact non-root GitHub Actions checkout"):
        ci_cluster.start()

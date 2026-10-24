"""Compile actual CI publisher guards; refuse before tools, SQL or payload."""
import builtins
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


class BeforeTool(Exception):
    pass


def publisher():
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_bytes())
    step = next(row for row in workflow["jobs"]["current-postgres"]["steps"]
                if row.get("name", "").startswith("CI-only fresh loopback cluster"))
    matches = re.findall(r"<<'PY'\n(.*?)\nPY(?:\n|$)", step["run"], re.S)
    assert len(matches) == 1
    return compile(matches[0], "actual_current_postgres_workflow_publisher", "exec")


def execute_guard(environment, *, head="a" * 40, uid=1001):
    calls = []

    def forbidden(*args, **kwargs):
        pytest.fail("The CI context must be rejected before SQL, socket or private payload")

    def version_check(*args, **kwargs):
        calls.append(args[0])
        raise BeforeTool

    def umask(mask):
        if type(mask) is not int or mask != 0o077:
            raise AssertionError("The real publisher must request its exact private umask")
        return 0o022  # Declared previous mask only; never change the process umask.

    fake = {
        "os": SimpleNamespace(environ=environment, name="posix", geteuid=lambda: uid, umask=umask),
        "subprocess": SimpleNamespace(check_output=version_check),
        "socket": SimpleNamespace(socket=forbidden),
        "scripts.scan_secrets": SimpleNamespace(_private_evidence=forbidden),
        "tests.ci_web37.prepare_collection": SimpleNamespace(source_photo=lambda: {"HEAD": head, "files": {}}),
        "tests.ci_web37.pg_lease": SimpleNamespace(contract=forbidden, digest=forbidden),
        "tests.ci_web37.pg53": SimpleNamespace(contract=forbidden),
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
    variants = [(dict(valid, GITHUB_ACTIONS="false"), "a" * 40, 1001),
                (dict(valid, GITHUB_WORKSPACE=str(ROOT.parent)), "a" * 40, 1001),
                (dict(valid, GITHUB_SHA="not-a-commit"), "a" * 40, 1001),
                (dict(valid), "b" * 40, 1001), (dict(valid), "a" * 40, 0)]
    for environment, head, uid in variants:
        with pytest.raises(AssertionError):
            execute_guard(environment, head=head, uid=uid)
        assert environment["observed_version_tool_calls"] == []


def test_exact_CI_context_reaches_only_the_fake_pinned_version_check():
    environment = {"GITHUB_ACTIONS": "true", "GITHUB_WORKSPACE": str(ROOT), "GITHUB_SHA": "a" * 40}
    with pytest.raises(BeforeTool):
        execute_guard(environment)
    calls = environment["observed_version_tool_calls"]
    assert len(calls) == 1 and calls[0][1] == "--version"
    assert Path(calls[0][0]).as_posix() == "/usr/lib/postgresql/17/bin/postgres"

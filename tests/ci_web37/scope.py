"""Reject Desktop product validation and journal private web execution starts."""
from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath

import pytest


def require_web_selection(nodeids):
    """Web Free catalog criteria and wide web viewports remain web scope."""
    for nodeid in nodeids:
        path, _, case = nodeid.replace("\\", "/").partition("::")
        module = PurePosixPath(path).name
        desktop_catalog = (module == "test_catalog_contract.py" and
            case == "test_catalog_copies_keep_personal_monthly_limits_separate_from_gym_daily_limits")
        if (module in {"test_login_desktop.py", "test_license_offline_security.py"}
                or module.startswith("test_desktop") or desktop_catalog):
            raise ValueError("Desktop product validation is outside the authorized web scope")


def pytest_addoption(parser):
    parser.addoption("--web37-execution-journal", type=Path, default=None,
                     help="Existing private directory for append-only per-worker case journals")


def pytest_configure(config):
    directory = config.getoption("web37_execution_journal")
    config._web37_journal = None
    if directory is not None:
        if not directory.is_absolute() or not directory.is_dir():
            raise pytest.UsageError("Execution journals require an existing absolute private directory")
        worker = getattr(config, "workerinput", {}).get("workerid", "controller")
        config._web37_journal = (directory / ("execution-" + worker + ".jsonl")).open("xb")


def record(config, value):
    output = config._web37_journal
    if output is not None:
        output.write((json.dumps(value, separators=(",", ":")) + "\n").encode())
        output.flush()
        os.fsync(output.fileno())


def pytest_collection_finish(session):
    try:
        require_web_selection(item.nodeid for item in session.items)
    except ValueError as error:
        raise pytest.UsageError(str(error)) from error


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_protocol(item, nextitem):
    # This durable start precedes setup, fixture creation and the test body.
    record(item.config, {"event": "start_before_setup", "nodeid": item.nodeid})


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    result = yield
    report = result.get_result()
    record(item.config, {"event": "phase", "nodeid": item.nodeid,
                         "phase": report.when, "outcome": report.outcome})


def pytest_unconfigure(config):
    output = getattr(config, "_web37_journal", None)
    if output is not None:
        output.close()

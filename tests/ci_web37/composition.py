"""Explicit in-memory current37 companions preserving original test objects.

Only the finite reviewed module namespace is cloned. The original sys.modules
entry, source file, function objects, assertions and helper globals stay intact.
Without the explicit flag this plugin changes no fixture or collection.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import re
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
MAP = ROOT / "tests/ci_web37/current-fixture-map.json"


def specification():
    value = json.loads(MAP.read_bytes())
    if value.get("schema") != "20261020_account_security" or len(value.get("modules", {})) != 43:
        raise pytest.UsageError("Current37 fixture composition specification differs")
    return value


def pytest_addoption(parser):
    group = parser.getgroup("current37")
    group.addoption("--web37-current-fixtures", action="store_true", default=False)
    group.addoption("--web37-companion-evidence", type=Path)


def pytest_configure(config):
    if config.getoption("--web37-current-fixtures"):
        from web.database.schema_control import expected_head
        if expected_head() != "20261020_account_security":
            raise pytest.UsageError("Current37 companions require the actual37 product; no fallback")
        config._web37_bindings = []


def fixture_function(value):
    if hasattr(value, "_get_wrapped_function"):
        return value._get_wrapped_function()
    return inspect.unwrap(value)


def clone_namespace(original, entry):
    from tests.ci_web37 import sqlite_fixtures

    path = Path(original.__file__)
    normalized = path.read_bytes().replace(b"\r\n", b"\n")
    if hashlib.sha256(normalized).hexdigest() != entry["source_sha256_LF"]:
        raise pytest.UsageError("An original current37 companion test module differs")
    companion = ModuleType(original.__name__)
    companion.__dict__.update(original.__dict__)
    bindings = []
    for name, expected in entry["replacements"].items():
        value = fixture_function(getattr(original, name))
        if (value.__module__, value.__name__) != (expected["module"], expected["function"]):
            raise pytest.UsageError("A selected historical fixture binding differs")
        companion.__dict__[name] = getattr(sqlite_fixtures, name)
        bindings.append({"name": name, "original_provider": value.__module__ + "." + value.__name__,
                         "current_provider": "tests.ci_web37.sqlite_fixtures." + name})
    tests = {name: value for name, value in original.__dict__.items()
             if name.startswith(("test_", "Test"))}
    if not tests or any(companion.__dict__[name] is not value for name, value in tests.items()):
        raise pytest.UsageError("An original business test object was changed or omitted")
    return companion, {"module": original.__name__, "test_objects_identical": len(tests),
                       "original_module_unmodified": True, "fixture_bindings": bindings}


class Current37Module(pytest.Module):
    def _getobj(self):
        original = super()._getobj()
        relative = self.path.relative_to(ROOT).as_posix()
        entry = specification()["modules"][relative]
        companion, receipt = clone_namespace(original, entry)
        self.config._web37_bindings.append(receipt)
        return companion


def pytest_pycollect_makemodule(module_path, parent):
    if not parent.config.getoption("--web37-current-fixtures"):
        return None
    try:
        relative = module_path.relative_to(ROOT).as_posix()
    except ValueError:
        return None
    if relative in specification()["modules"]:
        return Current37Module.from_parent(parent, path=module_path)
    return None


def pytest_sessionfinish(session, exitstatus):
    config = session.config
    if not config.getoption("--web37-current-fixtures"):
        return
    directory = config.getoption("--web37-companion-evidence")
    if directory is None:
        return
    if not directory.is_absolute() or not directory.is_dir() or directory.is_symlink():
        raise pytest.UsageError("Current37 companion evidence needs an existing private absolute directory")
    worker = getattr(config, "workerinput", {}).get("workerid", "controller")
    if not re.fullmatch(r"[a-z0-9]+", worker):
        raise pytest.UsageError("Current37 worker identity differs")
    value = {"scope": "explicit_current37_companions", "exitstatus": int(exitstatus),
             "worker": worker, "bindings": config._web37_bindings}
    with (directory / ("companions-" + worker + ".json")).open("x", encoding="utf8") as out:
        json.dump(value, out, indent=2)
        out.write("\n")

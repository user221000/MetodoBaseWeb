"""Explicit in-memory current39 companions preserving original test objects.

Only the finite reviewed module namespace is cloned. The original sys.modules
entry, source file, function objects, assertions and helper globals stay intact.
Without the explicit flag this plugin changes no fixture or collection.

The catalogue has72 current39 runtime fixture consumers and two operator-tool
consumers whose INPUT contract is an actual37 database. Those two keep their
authenticated37 fixture and are reported separately; no operator is approved
for a39 inventory by fixture substitution.
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
MAP = ROOT / "tests/ci_web39/current-fixture-map.json"
HISTORICAL37_SCOPE = "operator_toolkit_source37_not_current39_runtime"
HISTORICAL37_MODULES = {
    "tests/test_legacy_object_apply.py": "f8a2151c5d682eb6269bb20fba6eba3bae97d9f875d14fdaf1d7578ff7dbd2d1",
    "tests/test_legacy_object_apply_peer.py": "6c256bb9aade2950169b63a97b7c432ae6f6eb38e8fbeeb8b15a49527ba7b322",
}
HISTORICAL37_PROVIDER_SHA256_LF = "4a887ad23a46de5473d019c2aace2d541bd4ef7d04f29e2f301824e1178baf8d"


def historical37_entry(name):
    return {"source_sha256_LF": HISTORICAL37_MODULES[name], "replacements": {},
            "scope": HISTORICAL37_SCOPE, "preserved_fixtures": {"account37_engine": {
                "module": "tests.account_security37_fixtures", "function": "account37_engine",
                "historical_target": ["20261020_account_security"]}}}


def validate_specification(value):
    if value.get("schema") != "20261023_privacy_disposition" or len(value.get("modules", {})) != 74:
        raise pytest.UsageError("Current39 fixture composition specification differs")
    modules = value["modules"]
    historical = {name for name, entry in modules.items()
                  if not entry.get("replacements") or "scope" in entry or "preserved_fixtures" in entry}
    if (historical != set(HISTORICAL37_MODULES)
            or any(modules[name] != historical37_entry(name) for name in historical)
            or value.get("composition_scopes") != {"current39_runtime_modules": 72, "historical37_operator_modules": 2}):
        raise pytest.UsageError("Only the two pinned operator37 input exceptions may preserve historical fixtures")
    return value


def specification():
    value = json.loads(MAP.read_bytes())
    return validate_specification(value)


def pytest_addoption(parser):
    group = parser.getgroup("current39")
    group.addoption("--web39-current-fixtures", action="store_true", default=False)
    group.addoption("--web39-companion-evidence", type=Path)


def pytest_configure(config):
    if config.getoption("--web39-current-fixtures"):
        from web.database.schema_control import expected_head
        if expected_head() != "20261023_privacy_disposition":
            raise pytest.UsageError("Current39 companions require the actual39 product; no fallback")
        config._web39_bindings = []


def fixture_function(value):
    if hasattr(value, "_get_wrapped_function"):
        return value._get_wrapped_function()
    return inspect.unwrap(value)


def clone_namespace(original, entry):
    from tests.ci_web39 import sqlite_fixtures

    path = Path(original.__file__)
    normalized = path.read_bytes().replace(b"\r\n", b"\n")
    if hashlib.sha256(normalized).hexdigest() != entry["source_sha256_LF"]:
        raise pytest.UsageError("An original current39 companion test module differs")
    companion = ModuleType(original.__name__)
    companion.__dict__.update(original.__dict__)
    bindings = []
    historical = entry.get("scope") == HISTORICAL37_SCOPE
    if historical:
        try:
            relative = path.relative_to(ROOT).as_posix()
        except ValueError:
            raise pytest.UsageError("An operator37 exception must be the actual pinned source module") from None
        if (relative not in HISTORICAL37_MODULES or entry != historical37_entry(relative)
                or original.__name__ != relative.removesuffix(".py").replace("/", ".")):
            raise pytest.UsageError("An unreviewed operator37 exception cannot preserve a fixture")
        from tests import account_security37_fixtures
        provider = account_security37_fixtures.account37_engine
        value = fixture_function(getattr(original, "account37_engine"))
        provider_path = ROOT / "tests/account_security37_fixtures.py"
        if ((value.__module__, value.__name__) != ("tests.account_security37_fixtures", "account37_engine")
                or value is not fixture_function(provider)
                or hashlib.sha256(provider_path.read_bytes().replace(b"\r\n", b"\n")).hexdigest() != HISTORICAL37_PROVIDER_SHA256_LF):
            raise pytest.UsageError("The preserved operator37 fixture provider differs")
        bindings.append({"name": "account37_engine", "original_provider": value.__module__ + "." + value.__name__,
                         "current_provider": value.__module__ + "." + value.__name__,
                         "preserved_operator_input_revision": "20261020_account_security"})
    elif not entry.get("replacements") or "scope" in entry or "preserved_fixtures" in entry:
        raise pytest.UsageError("An empty or implicit historical fixture replacement is forbidden")
    for name, expected in entry["replacements"].items():
        value = fixture_function(getattr(original, name))
        if (value.__module__, value.__name__) != (expected["module"], expected["function"]):
            raise pytest.UsageError("A selected historical fixture binding differs")
        companion.__dict__[name] = getattr(sqlite_fixtures, name)
        bindings.append({"name": name, "original_provider": value.__module__ + "." + value.__name__,
                         "current_provider": "tests.ci_web39.sqlite_fixtures." + name})
    tests = {name: value for name, value in original.__dict__.items()
             if name.startswith(("test_", "Test"))}
    if not tests or any(companion.__dict__[name] is not value for name, value in tests.items()):
        raise pytest.UsageError("An original business test object was changed or omitted")
    return companion, {"module": original.__name__, "test_objects_identical": len(tests),
                       "original_module_unmodified": True, "fixture_bindings": bindings,
                       "validation_scope": HISTORICAL37_SCOPE if historical else "current39_runtime"}


class Current39Module(pytest.Module):
    def _getobj(self):
        original = super()._getobj()
        relative = self.path.relative_to(ROOT).as_posix()
        entry = specification()["modules"][relative]
        companion, receipt = clone_namespace(original, entry)
        self.config._web39_bindings.append(receipt)
        return companion


def pytest_pycollect_makemodule(module_path, parent):
    if not parent.config.getoption("--web39-current-fixtures"):
        return None
    try:
        relative = module_path.relative_to(ROOT).as_posix()
    except ValueError:
        return None
    if relative in specification()["modules"]:
        return Current39Module.from_parent(parent, path=module_path)
    return None


def pytest_sessionfinish(session, exitstatus):
    config = session.config
    if not config.getoption("--web39-current-fixtures"):
        return
    directory = config.getoption("--web39-companion-evidence")
    if directory is None:
        return
    if not directory.is_absolute() or not directory.is_dir() or directory.is_symlink():
        raise pytest.UsageError("Current39 companion evidence needs an existing private absolute directory")
    worker = getattr(config, "workerinput", {}).get("workerid", "controller")
    if not re.fullmatch(r"[a-z0-9]+", worker):
        raise pytest.UsageError("Current39 worker identity differs")
    value = {"scope": "explicit_72_current39_and_2_operator37_fixture_contracts", "exitstatus": int(exitstatus),
             "catalogue_scopes": {"current39_runtime_modules": 72, "historical37_operator_modules": 2},
             "worker": worker, "bindings": config._web39_bindings}
    with (directory / ("companions-" + worker + ".json")).open("x", encoding="utf8") as out:
        json.dump(value, out, indent=2)
        out.write("\n")

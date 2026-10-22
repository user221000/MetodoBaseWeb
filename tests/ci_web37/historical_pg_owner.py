"""External pytest transport for five physical33 criteria on authentic source33.

Load this as top-level `historical_pg_owner` with its directory on PYTHONPATH.
Do not put the current product root on PYTHONPATH: every web/model/schema import
must resolve to the unchanged historical checkout. Only the UUID owner is new.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
from types import ModuleType

import pytest

CONTROL = Path(__file__).resolve().parents[2]
OWNER_SHA256_LF = "a6548646a61c916dc9543720061df21765df15b0de49ae781ecbd8fff992ebf4"
HISTORICAL_MODULE_SHA256 = "9fa7d884722c5febf5c2700d7a5e78967c3a434ce3055501586421b7df7f8b30"
HISTORICAL_REVISION = "20261019_google_subjects"


def owner_module():
    path = CONTROL / "tests/account_security37_owned.py"
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    if hashlib.sha256(raw).hexdigest() != OWNER_SHA256_LF:
        raise pytest.UsageError("Historical33 transport current37 owner source differs")
    spec = importlib.util.spec_from_file_location("external_current37_uuid_owner", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(params=["postgresql"])
def google_database(request, tmp_path):
    if request.param != "postgresql":
        raise pytest.UsageError("Historical33 physical PG transport cannot choose another dialect")
    with owner_module().owned_database("postgresql", tmp_path) as value:
        yield value


def pytest_addoption(parser):
    parser.addoption("--historical33-owner37", action="store_true", default=False)


def pytest_configure(config):
    if config.getoption("historical33_owner37"):
        from web.database.models import Base
        from web.database.schema_control import expected_head

        if expected_head() != HISTORICAL_REVISION or len(Base.metadata.tables) != 35:
            raise pytest.UsageError("Physical33 criteria require authentic ORM35/head33, never current37 imports")


class Historical33Module(pytest.Module):
    def _getobj(self):
        original = super()._getobj()
        raw = Path(original.__file__).read_bytes()
        if hashlib.sha256(raw).hexdigest() != HISTORICAL_MODULE_SHA256:
            raise pytest.UsageError("An original physical33 assertion source differs")
        companion = ModuleType(original.__name__)
        companion.__dict__.update(original.__dict__)
        companion.google_database = google_database
        names = [name for name in vars(original) if name.startswith("test_")]
        if len(names) != 4 or any(getattr(companion, name) is not getattr(original, name) for name in names):
            raise pytest.UsageError("An original physical33 assertion object changed")
        output = os.environ.get("CI_WEB37_HISTORICAL33_BINDING")
        if output:
            path = Path(output)
            if not path.is_absolute() or not path.parent.is_dir() or path.is_symlink():
                raise pytest.UsageError("Historical33 binding requires an existing private output directory")
            with path.open("x", encoding="utf8") as receipt:
                json.dump({"scope": "physical33_only_not_runtime37", "revision": HISTORICAL_REVISION,
                           "model_tables": 35, "original_test_objects": len(names),
                           "source_sha256": HISTORICAL_MODULE_SHA256,
                           "UUID_owner37_source_sha256_LF": OWNER_SHA256_LF,
                           "original_assertions_unchanged": True}, receipt)
        return companion


def pytest_pycollect_makemodule(module_path, parent):
    if (parent.config.getoption("historical33_owner37")
            and module_path.resolve() == (Path.cwd() / "tests/integration_google33_migrations.py").resolve()):
        return Historical33Module.from_parent(parent, path=module_path)
    return None

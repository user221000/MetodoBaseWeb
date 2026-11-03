"""Exercise the actual startup validator with the authenticated CI runtime.

These checks do not start Docker, PostgreSQL, application workers or providers.
"""
from __future__ import annotations

import ast
import base64
import hashlib
import os

import pytest

from config.env_validator import validate_env_vars
from tests.ci_web41.source_companion import source_bytes


@pytest.fixture(scope="module", autouse=True)
def database_schema():
    """Configuration-only controls do not use SQL."""
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


def runtime_configuration():
    source = source_bytes("tests/ci_image57/current41_startup.py")
    tree = ast.parse(source)
    run = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run")
    statements = [node for node in run.body if isinstance(node, ast.Assign)
                  and any(isinstance(target, ast.Name) and target.id == "runtime" for target in node.targets)]
    assert len(statements) == 1 and isinstance(statements[0].value, ast.Dict)
    return eval(compile(ast.Expression(statements[0].value), "authenticated41-runtime-literal", "eval"),
                {"base64": base64, "os": os, "configuration": {
                    "METODOBASE_TEST_POSTGRES_URL":
                        "postgresql+psycopg2://metodobase_test_app:synthetic-only@127.0.0.1:55483/metodobase_test_image"}})


def test_only_one_runtime_salt_assignment_changed_in_complete_compiled_source():
    source = source_bytes("tests/ci_image57/current41_startup.py")
    addition = b"        'METODO_BASE_SALT': base64.urlsafe_b64encode(os.urandom(32)).decode(),\n"
    assert source.count(addition) == 1
    # This proves every other byte, require(), assertion, cleanup, command and
    # runtime resource limit remains the reviewed source41 program.
    assert hashlib.sha256(source.replace(addition, b"", 1)).hexdigest() == (
        "b02cb6249eb914f800297c3c43277721dbe1cbb96345768a33e2863f9f1898ed")


def test_exact_ci_runtime_passes_unchanged_product_environment_validator(monkeypatch):
    runtime = runtime_configuration()
    for key in tuple(os.environ):
        monkeypatch.delenv(key)
    for key, value in runtime.items():
        monkeypatch.setenv(key, value)
    assert validate_env_vars() is None


def test_historical_unsalted_runtime_still_rejects_before_worker_start(monkeypatch):
    runtime = runtime_configuration()
    del runtime["METODO_BASE_SALT"]
    for key in tuple(os.environ):
        monkeypatch.delenv(key)
    for key, value in runtime.items():
        monkeypatch.setenv(key, value)
    with pytest.raises(SystemExit) as failure:
        validate_env_vars()
    assert failure.value.code == 1


def test_each_runtime_gets_fresh_bounded_synthetic_salt_without_inherited_secrets(monkeypatch):
    monkeypatch.setenv("METODO_BASE_SALT", "inherited-salt-must-not-be-used")
    monkeypatch.setenv("LICENSE_SALT", "inherited-license-must-not-be-used")
    first, second = runtime_configuration(), runtime_configuration()
    a, b = first["METODO_BASE_SALT"], second["METODO_BASE_SALT"]
    assert len(a) == len(b) == 44 and len(base64.urlsafe_b64decode(a)) == 32
    assert a != b and a != os.environ["METODO_BASE_SALT"]
    assert "LICENSE_SALT" not in first and "MIGRATOR_DATABASE_URL" not in first
    assert first["METODOBASE_ENV"] == "testing" and first["RAILWAY_ENVIRONMENT"] == "ci41-synthetic"
    assert not any("STRIPE" in key for key in first)

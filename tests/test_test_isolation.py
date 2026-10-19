"""Behavior checks for the safeguards protecting developer/production data."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

import pytest

from tests.isolation import validate_postgres_test_url


@pytest.mark.parametrize("url", [
    "postgresql://metodobase_test_app@remote.invalid/metodobase_test",
    "postgresql://postgres@127.0.0.1/metodobase_test",
    "postgresql://metodobase_test_app@127.0.0.1/production",
    "postgresql://metodobase_test_app@127.0.0.1/metodobase_test?host=remote.invalid",
    "sqlite:///production.db",
])
def test_unapproved_database_targets_are_rejected(url):
    with pytest.raises(ValueError):
        validate_postgres_test_url(url)


def test_dedicated_loopback_database_is_accepted():
    url = "postgresql://metodobase_test_app@127.0.0.1:55482/metodobase_test_integration"
    assert validate_postgres_test_url(url) == url


@pytest.mark.parametrize("method", ["connect", "connect_ex"])
def test_outbound_tcp_is_blocked_before_connecting(method):
    with socket.socket() as connection, pytest.raises(RuntimeError, match="blocked"):
        getattr(connection, method)(("outside.invalid", 443))


def test_direct_pytest_rejects_an_inherited_database():
    env = dict(os.environ)
    env.pop("_METODOBASE_TEST_ROOT", None)
    env["DATABASE_URL"] = "postgresql://fake:do-not-log@outside.invalid/production"
    result = subprocess.run([sys.executable, "-X", "utf8", "-c",
                             "from tests.isolation import prepare_environment; prepare_environment()"],
                            env=env, capture_output=True, text=True, encoding="utf-8")
    assert result.returncode != 0
    assert "Inherited DATABASE_URL rejected" in result.stderr
    assert "do-not-log" not in result.stderr


def test_xdist_worker_uses_a_different_database_file():
    env = dict(os.environ)
    env["PYTEST_XDIST_WORKER"] = "gw987"
    code = "import os,json; from tests.isolation import prepare_environment; prepare_environment(); print(json.dumps({'db':os.environ['DATABASE_URL'],'data':os.environ['METODOBASE_DATA_DIR']}))"
    result = subprocess.run([sys.executable, "-X", "utf8", "-c", code], env=env,
                            capture_output=True, text=True, encoding="utf-8", check=True)
    child = json.loads(result.stdout)
    assert child["db"] != os.environ["DATABASE_URL"]
    assert Path(child["data"]).name == "gw987"
    assert child["db"].endswith("gw987/suite.db")


def test_backup_sources_keys_and_libpq_inheritance_are_disabled():
    env = dict(os.environ)
    names = ("BACKUP_DATABASE_URL", "RESTORE_DATABASE_URL", "CUSTOM_DATABASE_URL", "BACKUP_ENCRYPTION_KEY", "PGHOST", "PGPASSWORD", "PGSERVICE")
    env.update({name: "synthetic-inherited-marker" for name in names})
    code = "import os,json; from tests.isolation import prepare_environment; prepare_environment(); print(json.dumps({name:os.environ.get(name) for name in " + repr(names) + "}))"
    result = subprocess.run([sys.executable, "-X", "utf8", "-c", code], env=env,
                            capture_output=True, text=True, encoding="utf-8", check=True)
    assert all(value == "" for value in json.loads(result.stdout).values())

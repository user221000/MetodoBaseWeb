"""Real CLI/embedded SQLite migrations preserve the caller's logging authority."""
from contextlib import contextmanager
import hashlib
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import uuid

import pytest
from sqlalchemy import create_engine

from scripts.scan_secrets import _private_evidence

ROOT = Path(__file__).resolve().parents[1]
DRIVER = r'''from pathlib import Path
import json, os, runpy, sys
directory, repository, mode = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
sys.path.insert(0, str(repository))
from tests.isolation import prepare_environment, block_external_sockets
prepare_environment(discard_inherited=True)
block_external_sockets()
database = directory / "actual-cli.db"
os.environ["DATABASE_URL"] = "sqlite:///" + database.as_posix()
from sqlalchemy import create_engine
from web.database.schema_control import expected_head, verify_runtime_schema
calls = []
def observe(frame, event, arg):
    if (event == "call" and frame.f_code.co_name == "fileConfig"
            and frame.f_code.co_filename.replace("\\", "/").endswith("/logging/config.py")):
        calls.append(str(frame.f_locals["fname"]))
prior = sys.getprofile()
try:
    sys.setprofile(observe)
    if mode == "CLI":
        sys.argv = ["alembic", "upgrade", "head"]
        runpy.run_module("alembic", run_name="__main__")
    else:
        from alembic import command
        from alembic.config import Config
        config = Config()
        config.set_main_option("script_location", str(repository / "web/database/alembic"))
        assert config.config_file_name is None and "connection" not in config.attributes
        command.upgrade(config, "head")
finally:
    sys.setprofile(prior)
engine = create_engine("sqlite:///" + database.as_posix())
try:
    verify_runtime_schema(engine)
    with engine.connect() as connection:
        revision = connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one()
        assert revision == expected_head()
finally:
    engine.dispose()
(directory / "result.json").write_text(json.dumps({"fileConfig_calls": calls, "revision": revision,
    "database": str(database), "mode": mode}), encoding="utf8")
'''


@pytest.fixture(scope="module", autouse=True)
def database_schema():
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


def bootstrap(directory, mode="CLI"):
    private = _private_evidence(directory)
    environment = dict(os.environ, TEMP=str(private), TMP=str(private), TMPDIR=str(private),
        _METODOBASE_TEST_ROOT=str(private / "metodobase-test-child"), PYTHONDONTWRITEBYTECODE="1",
        PYTHONNOUSERSITE="1", PYTHONUTF8="1", PYTHON_DOTENV_DISABLED="1", PYTHONPATH=str(ROOT))
    for name in list(environment):
        if name.startswith("PYTEST_XDIST_") or name in {"PYTEST_CURRENT_TEST", "PYTEST_ADDOPTS", "PYTEST_PLUGINS"}:
            environment.pop(name)
    compile(DRIVER, "real-cli-driver", "exec")
    with (private / "command.private.log").open("xb") as output:
        code = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", DRIVER, str(private), str(ROOT), mode],
            cwd=ROOT, env=environment, stdout=output, stderr=subprocess.STDOUT, check=False).returncode
    assert code == 0, (private / "command.private.log").read_text(encoding="utf8")
    return json.loads((private / "result.json").read_bytes())


@contextmanager
def real_file_config_calls():
    """Observe the original Python function; never replace logging or Alembic."""
    prior, calls = sys.getprofile(), []

    def observe(frame, event, arg):
        if callable(prior):
            prior(frame, event, arg)
        if (event == "call" and frame.f_code.co_name == "fileConfig"
                and frame.f_code.co_filename.replace("\\", "/").endswith("/logging/config.py")):
            calls.append(str(frame.f_locals["fname"]))

    try:
        sys.setprofile(observe)
        yield calls
    finally:
        sys.setprofile(prior)


@pytest.mark.parametrize("mode,expected_calls", [("CLI", 1), ("no-config-file", 0)])
def test_real_default_cli_logging_and_absent_config_file_keep_exact_migration(mode, expected_calls, tmp_path):
    from web.database.schema_control import expected_head

    result = bootstrap(tmp_path / "actual-command", mode)
    assert result["revision"] == expected_head() == "20261023_privacy_disposition"
    assert len(result["fileConfig_calls"]) == expected_calls
    if expected_calls:
        assert Path(result["fileConfig_calls"][0]).resolve() == ROOT / "alembic.ini"


def test_real_bound_migration_preserves_existing_logger_state_and_root_handlers(tmp_path):
    from web.database.schema_control import verify_runtime_schema
    from web.services.privacy_restore_binding import destination, migrate_bound, restored_binding
    from web.routes import usuario

    result = bootstrap(tmp_path / "source-database")
    path = Path(result["database"])
    options = {"sqlite_destination": path}
    binding = restored_binding(destination(options), options)
    engine = create_engine("sqlite:///" + path.as_posix())
    # Creating a normal named logger exercises fileConfig's existing-logger
    # behavior without changing disabled, levels, propagation or capture rules.
    canary = logging.getLogger(__name__ + ".embedded." + uuid.uuid4().hex)
    assert canary.disabled is False
    loggers = [canary, usuario.logger, logging.root]
    def state():
        return [(logger, logger.disabled, logger.level, logger.propagate, tuple(logger.handlers)) for logger in loggers]
    before = state()
    try:
        with real_file_config_calls() as calls:
            migrate_bound(engine, binding)
        assert calls == []
        assert state() == before
        verify_runtime_schema(engine)
        assert restored_binding(destination(options), options) == binding
    finally:
        engine.dispose()


def test_wrong_destination_is_still_refused_before_real_migration_or_logging_config(tmp_path):
    from web.database.schema_control import verify_runtime_schema
    from web.services.privacy_restore_binding import destination, migrate_bound, restored_binding

    result = bootstrap(tmp_path / "source-database")
    path = Path(result["database"])
    options = {"sqlite_destination": path}
    binding = restored_binding(destination(options), options)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    engine = create_engine("sqlite:///" + path.as_posix())
    try:
        with real_file_config_calls() as calls, pytest.raises(ValueError, match="effective SQLite file"):
            migrate_bound(engine, {**binding, "sqlite_path": str((tmp_path / "other.db").resolve())})
        assert calls == []
        verify_runtime_schema(engine)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == before
        assert not (tmp_path / "other.db").exists()
    finally:
        engine.dispose()

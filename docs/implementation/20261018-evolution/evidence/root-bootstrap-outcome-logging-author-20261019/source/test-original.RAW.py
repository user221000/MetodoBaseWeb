"""The migration CLI reports confirmed outcomes without exposing error details."""
import os
from pathlib import Path
import sqlite3
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
PREVIOUS = "20261019_client_account_links"


def run_cli(tmp_path, database, *arguments):
    environment = os.environ.copy()
    for key in ("DATABASE_URL", "MIGRATOR_DATABASE_URL", "METODOBASE_TEST_DATABASE_URL",
                "METODOBASE_TEST_MIGRATOR_URL", "METODOBASE_TEST_POSTGRES_URL",
                "METODOBASE_TEST_REDIS_URL"):
        environment.pop(key, None)
    environment.update(DATABASE_URL="sqlite:///" + database.as_posix(),
        METODOBASE_ENV="testing", ENV="testing", PYTHONUTF8="1",
        PYTHONDONTWRITEBYTECODE="1", PYTHON_DOTENV_DISABLED="1")
    result = subprocess.run([sys.executable, "-X", "utf8", "-B", "db_bootstrap.py", *arguments],
        cwd=ROOT, env=environment, capture_output=True, timeout=60)
    number = len(list(tmp_path.glob("launch-*.stdout.raw.log"))) + 1
    for suffix, raw in (("stdout", result.stdout), ("stderr", result.stderr)):
        with (tmp_path / f"launch-{number}.{suffix}.raw.log").open("xb") as stream:
            stream.write(raw)
    return result, (result.stdout + result.stderr).decode("utf-8", errors="strict")


def test_cli_reports_post_alembic_failure_without_private_exception_details(tmp_path):
    database = tmp_path / "private-destination-marker.db"
    prepare, _ = run_cli(tmp_path, database, "--revision", PREVIOUS)
    assert prepare.returncode == 0
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE INDEX private_exception_marker ON usuarios(nombre)")
    failed, output = run_cli(tmp_path, database)
    assert failed.returncode == 1
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == (PREVIOUS,)
        assert connection.execute("SELECT count(*) FROM sqlite_master WHERE type='index' AND name='private_exception_marker'").fetchone() == (1,)
    assert "Migration aborted class=RuntimeError; database not accepted for release" in output
    assert "Migration completed and verified" not in output
    assert "private_exception_marker" not in output
    assert "private-destination-marker" not in output
    assert str(tmp_path) not in output
    assert "Traceback" not in output


def test_cli_reports_success_only_after_schema_verification(tmp_path):
    database = tmp_path / "private-success-marker.db"
    result, output = run_cli(tmp_path, database, "--revision", PREVIOUS)
    assert result.returncode == 0
    assert "Migration completed and verified at revision " + PREVIOUS in output
    assert "Migration aborted" not in output
    assert "private-success-marker" not in output
    assert str(tmp_path) not in output

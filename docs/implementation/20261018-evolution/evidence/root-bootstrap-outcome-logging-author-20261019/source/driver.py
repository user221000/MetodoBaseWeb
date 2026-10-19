"""Create an isolated source and real CLI regressions for migration outcome logs."""
from pathlib import Path
import ast
import hashlib
import json
import subprocess

repo = Path(r'F:\mb-mfa31-compose-20261019')
root = Path(r'F:\mb-bootstrap-log-20261019')
out = Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-bootstrap-log-source-20261019')
head = '6a75d096ea3d63d9e78c76d33b7e243160b23364'
assert not root.exists() and not out.exists()
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo).decode().strip() == head
assert not subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=repo)
out.mkdir()
(out / 'driver.py').write_bytes(Path(__file__).read_bytes())
result = subprocess.run(['git', '-c', 'core.autocrlf=false', 'worktree', 'add', '-b',
    'implementation/bootstrap-log-20261019', str(root), head], cwd=repo, capture_output=True)
(out / 'worktree.stdout.raw.log').write_bytes(result.stdout)
(out / 'worktree.stderr.raw.log').write_bytes(result.stderr)
assert result.returncode == 0
for name in ['alembic.ini', 'db_bootstrap.py', 'web/database/alembic/env.py']:
    raw = (root / name).read_bytes()
    safe = name.replace('/', '__')
    (out / (safe + '.before.RAW')).write_bytes(raw)
    blob = subprocess.check_output(['git', 'show', head + ':' + name], cwd=repo)
    (out / (safe + '.before.GitLF')).write_bytes(blob)

test = '''"""The migration CLI reports confirmed outcomes without exposing error details."""
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
'''
ast.parse(test)
target = root / 'tests/test_bootstrap_outcome_logging.py'
with target.open('xb') as stream:
    stream.write(test.encode('utf-8'))
(out / 'test-original.RAW.py').write_bytes(target.read_bytes())
print(json.dumps({'root': str(root), 'head': head,
    'test_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
    'product_changed': False, 'scope': 'Preparation only, real CLI red reproduction pending.'}))

"""Independent rollback/uncertain-commit and actual synthetic CLI exit checks."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import logging
import os
from pathlib import Path
import subprocess
import sys

import pytest
from sqlalchemy import create_engine, event, select

from scripts import cleanup_expired_tokens as cleanup
from tests.test_cleanup_tokens import cleanup_database, seed_retention_rows


def row_counts(engine):
    from web.database.models import AuthAuditLog, RefreshToken
    with engine.connect() as connection:
        return (len(connection.scalars(select(RefreshToken.jti)).all()),
                len(connection.scalars(select(AuthAuditLog.id)).all()))


@pytest.mark.parametrize('operation', ['cleanup_expired_tokens', 'cleanup_old_audit_logs'])
def test_failed_commit_does_not_confirm_cleanup_and_rolls_back_rows(cleanup_database, caplog, operation):
    seed_retention_rows(cleanup_database)
    def before_commit(connection):
        raise RuntimeError('synthetic-private-commit-parameter-marker')
    event.listen(cleanup_database, 'commit', before_commit)
    try:
        with caplog.at_level(logging.INFO, logger=cleanup.__name__), pytest.raises(cleanup.CleanupFailure) as failed:
            getattr(cleanup, operation)()
    finally:
        event.remove(cleanup_database, 'commit', before_commit)
    assert str(failed.value) == 'cleanup_not_confirmed'
    assert row_counts(cleanup_database) == (6, 4)
    assert 'Cleanup confirmed' not in caplog.text
    assert 'synthetic-private-commit-parameter-marker' not in caplog.text


@pytest.mark.parametrize('operation,remaining', [
    ('cleanup_expired_tokens', (4, 4)), ('cleanup_old_audit_logs', (6, 3)),
])
def test_committed_but_unacknowledged_cleanup_never_reports_zero_or_success(
        cleanup_database, monkeypatch, caplog, operation, remaining):
    seed_retention_rows(cleanup_database)
    original = cleanup_database
    class UncertainEngine:
        @contextmanager
        def begin(self):
            with original.begin() as connection:
                yield connection
            # The physical transaction committed; its confirmation was lost.
            raise RuntimeError('synthetic-private-after-commit-marker')
    monkeypatch.setattr(cleanup, 'get_engine', lambda: UncertainEngine())
    with caplog.at_level(logging.INFO, logger=cleanup.__name__), pytest.raises(cleanup.CleanupFailure) as failed:
        getattr(cleanup, operation)()
    assert str(failed.value) == 'cleanup_not_confirmed'
    assert row_counts(original) == remaining
    assert 'Cleanup confirmed' not in caplog.text
    assert 'synthetic-private-after-commit-marker' not in caplog.text
    monkeypatch.setattr(cleanup, 'get_engine', lambda: original)
    assert getattr(cleanup, operation)() == 0


@pytest.mark.parametrize('operation', ['cleanup_expired_tokens', 'cleanup_old_audit_logs'])
def test_unknown_driver_rowcount_rolls_back_instead_of_claiming_success(cleanup_database, monkeypatch, operation):
    seed_retention_rows(cleanup_database)
    original = cleanup_database
    class UnknownCount:
        rowcount = -1
    class UnknownCountEngine:
        @contextmanager
        def begin(self):
            with original.begin() as connection:
                class DriverBoundary:
                    def execute(self, statement):
                        connection.execute(statement)
                        return UnknownCount()
                yield DriverBoundary()
    monkeypatch.setattr(cleanup, 'get_engine', lambda: UnknownCountEngine())
    with pytest.raises(cleanup.CleanupFailure, match='cleanup_not_confirmed'):
        getattr(cleanup, operation)()
    assert row_counts(original) == (6, 4)


@pytest.mark.parametrize('prepared', [True, False], ids=['success', 'missing-tables-fails'])
def test_actual_cli_exit_code_with_explicit_owned_sqlite_only(tmp_path, prepared):
    from web.database.models import AuthAuditLog, Base, RefreshToken, Usuario
    root = Path(__file__).resolve().parents[1]
    database = (tmp_path / 'synthetic-cli-cleanup.db').resolve()
    assert database.is_relative_to(tmp_path.resolve())
    url = 'sqlite:///' + database.as_posix()
    engine = create_engine(url)
    if prepared:
        Base.metadata.create_all(engine)
        now = datetime.now(timezone.utc)
        with engine.begin() as connection:
            connection.execute(Usuario.__table__.insert().values(id='cli-cleanup-owner',
                email='cli-cleanup@example.invalid', nombre='Synthetic', password_hash='unused'))
            connection.execute(RefreshToken.__table__.insert().values(jti='synthetic-cli-expired',
                user_id='cli-cleanup-owner', expires_at=(now-timedelta(days=31)).timestamp(),
                created_at=(now-timedelta(days=40)).timestamp(), revoked=False))
            connection.execute(AuthAuditLog.__table__.insert().values(id='synthetic-cli-old-audit',
                event_type='synthetic', created_at=now-timedelta(days=91)))
    environment = dict(os.environ, DATABASE_URL=url, METODOBASE_TEST_DATABASE_URL='',
                       PYTHON_DOTENV_DISABLED='1', METODOBASE_ENV='testing')
    try:
        result = subprocess.run([sys.executable, '-X', 'utf8', 'scripts/cleanup_expired_tokens.py'],
            cwd=root, env=environment, capture_output=True, text=True, encoding='utf-8', timeout=20)
        output = result.stdout + result.stderr
        assert result.returncode == (0 if prepared else 1)
        assert 'DELETE FROM' not in output and url not in output and str(database) not in output
        assert ('CLEANUP JOB COMPLETED' in output) is prepared
        if prepared:
            assert row_counts(engine) == (0, 0)
            assert 'tokens=1 audit=1' in output
        else:
            assert 'CLEANUP JOB FAILED' in output
    finally:
        engine.dispose()

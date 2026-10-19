"""Retention units and failure visibility for the existing manual cleanup job."""
from datetime import datetime, timedelta, timezone
import json
import logging

import pytest
from sqlalchemy import create_engine, event, select

from scripts import cleanup_expired_tokens as cleanup

NOW = datetime(2032, 11, 1, 12, 30, 17, 123456, tzinfo=timezone.utc)


class FixedClock(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW.astimezone(tz) if tz else NOW.replace(tzinfo=None)


@pytest.fixture
def cleanup_database(tmp_path, monkeypatch):
    from web.database.models import Base
    engine = create_engine('sqlite:///' + (tmp_path / 'cleanup.db').as_posix())
    Base.metadata.create_all(engine)
    monkeypatch.setattr(cleanup, 'get_engine', lambda: engine)
    monkeypatch.setattr(cleanup, 'datetime', FixedClock)
    yield engine
    engine.dispose()


def seed_retention_rows(engine):
    from web.database.models import AuthAuditLog, RefreshToken, Usuario
    cutoff = NOW - timedelta(days=30)
    rows = [
        ('old-active', cutoff - timedelta(seconds=1), False),
        ('old-revoked', cutoff - timedelta(seconds=1), True),
        ('at-cutoff', cutoff, True),
        ('recent-expired', NOW - timedelta(days=1), False),
        ('at-now', NOW, False),
        ('future', NOW + timedelta(days=1), True),
    ]
    audit_cutoff = NOW - timedelta(days=90)
    with engine.begin() as connection:
        connection.execute(Usuario.__table__.insert().values(id='cleanup-owner',
            email='cleanup@example.invalid', nombre='Synthetic', password_hash='unused'))
        connection.execute(RefreshToken.__table__.insert(), [dict(jti=key, user_id='cleanup-owner',
            expires_at=expiry.timestamp(), revoked=revoked, created_at=(NOW-timedelta(days=100)).timestamp())
            for key, expiry, revoked in rows])
        connection.execute(AuthAuditLog.__table__.insert(), [dict(id=key, gym_id=None, user_id=None,
            event_type='synthetic', created_at=created) for key, created in [
                ('old-audit', audit_cutoff-timedelta(seconds=1)), ('audit-cutoff', audit_cutoff),
                ('recent-audit', audit_cutoff+timedelta(seconds=1)), ('now-audit', NOW)]])


def assert_cleanup_boundaries(engine):
    from web.database.models import AuthAuditLog, RefreshToken
    seed_retention_rows(engine)
    assert cleanup.cleanup_expired_tokens() == 2
    with engine.connect() as connection:
        assert set(connection.scalars(select(RefreshToken.jti))) == {
            'at-cutoff', 'recent-expired', 'at-now', 'future'}
    assert cleanup.cleanup_expired_tokens() == 0
    assert cleanup.cleanup_old_audit_logs() == 1
    with engine.connect() as connection:
        assert set(connection.scalars(select(AuthAuditLog.id))) == {
            'audit-cutoff', 'recent-audit', 'now-audit'}
    assert cleanup.cleanup_old_audit_logs() == 0


def test_epoch_and_utc_boundaries_do_not_delete_recent_rows(cleanup_database):
    assert_cleanup_boundaries(cleanup_database)


@pytest.mark.parametrize('operation', ['cleanup_expired_tokens', 'cleanup_old_audit_logs'])
def test_database_failure_rolls_back_and_exposes_only_a_stable_failure(cleanup_database, caplog, operation):
    from web.database.models import AuthAuditLog, RefreshToken
    seed_retention_rows(cleanup_database)
    marker = 'private-cleanup-sql-parameter-marker'
    def interrupt(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith('DELETE'):
            raise RuntimeError(marker)
    event.listen(cleanup_database, 'before_cursor_execute', interrupt)
    try:
        with caplog.at_level(logging.ERROR, logger=cleanup.__name__), pytest.raises(RuntimeError) as failure:
            getattr(cleanup, operation)()
    finally:
        event.remove(cleanup_database, 'before_cursor_execute', interrupt)
    assert marker not in str(failure.value)
    assert failure.value.__cause__ is None and failure.value.__suppress_context__
    assert marker not in json.dumps([r.__dict__ for r in caplog.records], default=str)
    with cleanup_database.connect() as connection:
        assert len(connection.scalars(select(RefreshToken.jti)).all()) == 6
        assert len(connection.scalars(select(AuthAuditLog.id)).all()) == 4


@pytest.mark.parametrize('days', [-1, True, 1.5, '30', None])
@pytest.mark.parametrize('operation', ['cleanup_expired_tokens', 'cleanup_old_audit_logs'])
def test_invalid_retention_never_opens_database(monkeypatch, operation, days):
    def forbidden():
        pytest.fail('Invalid retention must be rejected before connecting')
    monkeypatch.setattr(cleanup, 'get_engine', forbidden)
    with pytest.raises(ValueError):
        getattr(cleanup, operation)(days_to_keep=days)


def test_main_reports_failure_without_running_next_destructive_step(monkeypatch, caplog):
    def fail(**kwargs):
        raise RuntimeError('private-cleanup-main-marker')
    def forbidden(**kwargs):
        pytest.fail('Do not continue the job after a failure')
    monkeypatch.setattr(cleanup, 'cleanup_expired_tokens', fail)
    monkeypatch.setattr(cleanup, 'cleanup_old_audit_logs', forbidden)
    with caplog.at_level(logging.INFO, logger=cleanup.__name__):
        assert cleanup.main() == 1
    assert 'private-cleanup-main-marker' not in caplog.text
    assert 'CLEANUP JOB COMPLETED' not in caplog.text


def test_main_returns_zero_only_when_both_steps_succeed(monkeypatch):
    monkeypatch.setattr(cleanup, 'cleanup_expired_tokens', lambda **kwargs: 2)
    monkeypatch.setattr(cleanup, 'cleanup_old_audit_logs', lambda **kwargs: 1)
    assert cleanup.main() == 0

"""Independent SQLite controls; no PostgreSQL or real provider authority."""
import uuid
from datetime import timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import insert
from sqlalchemy.orm import Session

from tests import product_analytics_fixtures as fixtures
from web.database import engine as global_database
from web.database.models import GymGenerationReservation, UserRole
from web.database.tenant_context import current_tenant
from web.services import product_analytics as service

account37_engine = fixtures.account37_engine
analytics_engine = fixtures.analytics_engine
analytics_case = fixtures.analytics_case


@pytest.mark.parametrize('scope', ['gym', 'personal'])
def test_owned_factory_starts_neutral_and_cleanup_finishes_before_return(analytics_case, scope):
    case = analytics_case
    owner = case.user()
    actor = case.user(tipo='gym', role=UserRole.ADMIN, parent=owner['id'])
    case.saved(owner, fixtures.NOW - timedelta(days=1))
    case.saved(actor, fixtures.NOW - timedelta(days=2), context='personal')
    events = []
    sessions = []
    original_factory = global_database._SessionLocal

    class Observed(Session):
        def rollback(self):
            events.append(('rollback', current_tenant.get(), self.info.get('tenant_id')))
            return super().rollback()

        def close(self):
            result = super().close()
            events.append(('closed', current_tenant.get(), self.info.get('tenant_id')))
            return result

    def owned():
        events.append(('factory', current_tenant.get(), None))
        value = Observed(case.engine, autoflush=False)
        assert not value.in_transaction() and not value.info
        sessions.append(value)
        return value

    previous = current_tenant.set(str(uuid.uuid4()))
    inherited = current_tenant.get()
    try:
        value = service.read_report(actor, scope, factory=owned, now=fixtures.NOW)
        expected = owner['id'] if scope == 'gym' else actor['id']
        assert events == [('factory', '', None), ('rollback', '', expected), ('closed', '', expected)]
        assert current_tenant.get() == inherited
        assert len(sessions) == 1 and not sessions[0].in_transaction()
        assert global_database._SessionLocal is original_factory
        assert sum(week['saved_publications'] for week in value['weekly']) == 1
        assert owner['id'] not in str(value) and actor['id'] not in str(value)
        assert case.engine.pool.checkedout() == 0
    finally:
        current_tenant.reset(previous)


def test_factory_failure_cannot_be_an_empty_success_or_expose_private_detail(caplog):
    calls = []
    previous = current_tenant.set('inherited-foreign-context')
    try:
        def failed():
            calls.append(current_tenant.get())
            raise RuntimeError('PRIVATE_QA_R30_DATABASE_LOCATION')

        with pytest.raises(HTTPException) as caught:
            service.read_report({}, 'personal', factory=failed, now=fixtures.NOW)
        assert caught.value.status_code == 503
        assert caught.value.detail['code'] == 'analytics_unavailable'
        assert calls == [''] and current_tenant.get() == 'inherited-foreign-context'
        assert 'PRIVATE_QA_R30_DATABASE_LOCATION' not in caplog.text + str(caught.value.detail)
    finally:
        current_tenant.reset(previous)


@pytest.mark.parametrize('version_rows', [[], ['unrecognized_schema'], ['20261020_account_security', 'extra_head']])
def test_schema_uncertainty_fails_closed_and_releases_owned_session(analytics_case, version_rows):
    case = analytics_case
    actor = case.user()
    sessions = []

    class Versions:
        def all(self):
            return version_rows

    class Owned(Session):
        def scalars(self, statement, *args, **kwargs):
            if str(statement) == 'SELECT version_num FROM alembic_version':
                return Versions()
            return super().scalars(statement, *args, **kwargs)

    def owned():
        value = Owned(case.engine, autoflush=False)
        sessions.append(value)
        return value

    previous = current_tenant.set('unrelated-ambient-account')
    try:
        with pytest.raises(HTTPException) as caught:
            service.read_report(actor, 'gym', factory=owned, now=fixtures.NOW)
        assert caught.value.status_code == 503 and len(sessions) == 1
        assert current_tenant.get() == 'unrelated-ambient-account'
        assert case.engine.pool.checkedout() == 0 and not sessions[0].in_transaction()
    finally:
        current_tenant.reset(previous)
    assert service.read_report(actor, 'gym', factory=case.factory, now=fixtures.NOW)['scope'] == 'gym'


def test_fact_budget_applies_after_own_scope_and_accepts_exactly_10000(analytics_case):
    case = analytics_case
    owner, foreign = case.user(), case.user()
    rows = []
    for subject, count in ((owner, 10000), (foreign, 10001)):
        rows.extend({'id': str(uuid.uuid4()), 'gym_id': subject['id'], 'request_key': str(index),
            'request_hash': 'a' * 64, 'period': '2026-10', 'local_date': fixtures.NOW.date(),
            'timezone': 'America/Mexico_City', 'catalog_plan': 'free', 'status': 'reserved',
            'persisted_at': fixtures.NOW - timedelta(days=1)} for index in range(count))
    with case.factory() as db:
        db.execute(insert(GymGenerationReservation), rows)
        db.commit()
    value = service.read_report(owner, 'gym', start='2026-07-27', through='2026-10-21',
                                factory=case.factory, now=fixtures.NOW)
    assert len(value['weekly']) == 13
    assert sum(week['saved_publications'] for week in value['weekly']) == 10000
    with pytest.raises(HTTPException) as caught:
        service.read_report(foreign, 'gym', factory=case.factory, now=fixtures.NOW)
    assert caught.value.status_code == 413
    assert case.engine.pool.checkedout() == 0


def test_invalid_period_rejected_before_owned_factory():
    calls = []

    def forbidden():
        calls.append(True)
        raise AssertionError('Invalid period must not allocate a reader')

    with pytest.raises(HTTPException) as caught:
        service.read_report({}, 'personal', start='2026-07-20', through='2026-10-21',
                            factory=forbidden, now=fixtures.NOW)
    assert caught.value.status_code == 422 and calls == []

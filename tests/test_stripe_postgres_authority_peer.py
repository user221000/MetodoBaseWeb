"""Current migrated PostgreSQL, restricted-role RLS and Stripe invoice retry.

Provider messages are synthetic; PostgreSQL ownership is supplied by an owned
loopback cluster runner, never inferred from an arbitrary DATABASE_URL.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from tests.integration_schema_migrations import migration_database, run_migration
from tests.integration_provider_subjects import application_engine
from tests.test_stripe_invoice_authority_peer import invoice_case, event_from, deliver, client_for, SURFACES


@pytest.fixture
def pg_invoice(migration_database, monkeypatch):
    url, admin = migration_database
    if admin.dialect.name != 'postgresql':
        pytest.fail('This gate requires explicit PostgreSQL selection; SQLite is not a substitute')
    run_migration(url, 'db_bootstrap.py', '--revision', 'head')
    from web.database.models import Usuario, UserRole, UserSubscription
    from web.database.tenant_context import tenant_scope
    from web.database import engine as database
    actors = [{'id': 'pg-peer-a', 'email': 'pg-peer-a@example.invalid', 'nombre': 'Synthetic A',
               'tipo': 'usuario', 'role': 'owner'},
              {'id': 'pg-peer-b', 'email': 'pg-peer-b@example.invalid', 'nombre': 'Synthetic B',
               'tipo': 'usuario', 'role': 'owner'}]
    with Session(admin) as db:
        for actor in actors:
            db.add(Usuario(id=actor['id'], email=actor['email'], nombre=actor['nombre'],
                password_hash='unused-synthetic', apellido='', tipo='usuario', role=UserRole.OWNER,
                activo=True, session_version=0, fecha_registro=datetime.now(timezone.utc)))
        db.flush()
        db.add(UserSubscription(user_id='pg-peer-b', plan='starter', max_planes_mes=1,
                               planes_usados_mes=1, mes_actual=datetime.now(timezone.utc).strftime('%Y-%m')))
        db.commit()
    app = application_engine(url, admin)
    # Two physical restricted-role connections are required for the race;
    # the historical helper's single-connection pool would serialize callers.
    from web.database.tenant_context import configure_tenant_engine
    application_url = app.url
    app.dispose()
    app = configure_tenant_engine(create_engine(application_url, pool_size=2, max_overflow=0))
    sessions = sessionmaker(bind=app, expire_on_commit=False)
    monkeypatch.setattr(database, '_engine', app)
    monkeypatch.setattr(database, '_SessionLocal', sessions)
    try:
        with app.connect() as db:
            flags = db.execute(text('SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole,rolreplication FROM pg_roles WHERE rolname=current_user')).one()
            assert tuple(flags) == (False,)*5
            assert db.scalar(text("SELECT count(*) FROM pg_class WHERE relnamespace=current_schema()::regnamespace AND relkind='r' AND relrowsecurity AND relforcerowsecurity")) >= 35
        with tenant_scope('pg-peer-a'):
            case = invoice_case.__wrapped__((None, sessions, actors[0]), monkeypatch)
        yield case, app, admin
    finally:
        app.dispose()


def assert_facts(case, admin):
    _, actor, _ = case
    from web.database.models import Payment, StripeWebhookEvent, UserSubscription
    with Session(admin) as db:
        assert db.query(Payment).filter_by(gym_id=actor['id'], status='succeeded').count() == 1
        assert db.query(StripeWebhookEvent).count() == 1
        a = db.query(UserSubscription).filter_by(user_id=actor['id']).one()
        b = db.query(UserSubscription).filter_by(user_id='pg-peer-b').one()
        assert (a.plan, a.max_planes_mes) == ('pro', 5)
        assert (b.plan, b.max_planes_mes, b.planes_usados_mes) == ('starter', 1, 1)


@pytest.mark.parametrize('surface', SURFACES)
def test_pg_invoice_signed_retry_replay_preserves_other_tenant_and_quota(pg_invoice, surface):
    case, app, admin = pg_invoice
    factory, _, state = case
    from web.database.models import Payment, StripeWebhookEvent, UserSubscription
    from web.database.tenant_context import tenant_scope
    event = event_from(state)
    state['fail'] = True
    client = client_for(surface)
    failure = deliver(client, surface[1], event)
    assert failure.status_code == 503, failure.text
    with Session(admin) as db:
        assert db.query(Payment).count() == db.query(StripeWebhookEvent).count() == 0
    state['fail'] = False
    success = deliver(client, surface[1], event)
    assert success.status_code == 200, success.text
    assert success.json()['result'] == 'paid:7900'
    replay = deliver(client, surface[1], event)
    assert replay.status_code == 200 and replay.json()['result'] == 'duplicate:invoice.paid'
    assert_facts(case, admin)
    with tenant_scope('pg-peer-b'), Session(app) as db:
        assert db.query(Payment).count() == 0
        assert [row.user_id for row in db.query(UserSubscription).all()] == ['pg-peer-b']
    with tenant_scope('pg-peer-a'), Session(app) as db:
        assert [row.user_id for row in db.query(UserSubscription).all()] == ['pg-peer-a']


def test_pg_concurrent_same_invoice_has_one_ledger_and_retryable_inbox_collision(pg_invoice, record_property):
    case, _, admin = pg_invoice
    factory, _, state = case
    from web.services.stripe_service import handle_webhook_event
    from sqlalchemy.exc import IntegrityError
    gate = Barrier(2)
    backend_pids = []
    event = event_from(state)
    def attempt():
        with factory() as db:
            backend_pids.append(db.scalar(text('SELECT pg_backend_pid()')))
            gate.wait(timeout=10)
            try:
                result = handle_webhook_event(db, event)
                db.commit()
                return result
            except IntegrityError:
                db.rollback()
                return 'retryable_inbox_collision'
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert len(set(backend_pids)) == 2
    record_property('observed_distinct_postgres_backends', str(sorted(backend_pids)))
    assert 'paid:7900' in results
    assert set(results) <= {'paid:7900', 'duplicate:invoice.paid', 'retryable_inbox_collision'}
    with factory() as db:
        assert handle_webhook_event(db, event) == 'duplicate:invoice.paid'
        db.commit()
    assert_facts(case, admin)

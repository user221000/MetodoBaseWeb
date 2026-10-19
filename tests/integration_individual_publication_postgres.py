"""Serialize publication and compensation on actual restricted-role PG sessions."""
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from threading import Event
import time

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from tests.integration_schema_migrations import migration_database, run_migration
from tests.integration_provider_subjects import application_engine

pytestmark = pytest.mark.parametrize('migration_database', ['postgresql'], indirect=True)
SUBJECT = 'publication-race-owner'


@pytest.fixture
def publication_pg(migration_database):
    from web.database.models import Usuario, UserRole, Cliente
    from web.database.tenant_context import configure_tenant_engine
    url, admin = migration_database
    run_migration(url, 'db_bootstrap.py', '--revision', 'head')
    with Session(admin) as db:
        db.add(Usuario(id=SUBJECT, email=SUBJECT+'@example.invalid', nombre='Synthetic',
            tipo='usuario', role=UserRole.VIEWER, password_hash='synthetic'))
        db.flush()
        db.add(Cliente(id_cliente='publication-race-client', gym_id=SUBJECT, nombre='Synthetic'))
        db.commit()
    granted = application_engine(url, admin)
    target = granted.url
    granted.dispose()
    app = configure_tenant_engine(create_engine(target, pool_size=3, max_overflow=0))
    try:
        yield admin, app
    finally:
        app.dispose()


@pytest.mark.parametrize('first', ['publication', 'compensation'])
def test_account_lock_serializes_publication_against_compensation(publication_pg, first):
    from web.database import repository
    from web.database.models import GenerationReservation, PlanGenerado, UserSubscription
    from web.database.tenant_context import tenant_scope
    from web.services.generation_quota import _lock_account, reserve_generation, finish_generation
    admin, app = publication_pg
    with tenant_scope(SUBJECT), Session(app) as db:
        reservation = reserve_generation(db, SUBJECT, 'same-reservation').id
    held, release = Event(), Event()
    second_pid = Queue()

    def operation(kind, *, leading):
        with tenant_scope(SUBJECT), Session(app) as db:
            if leading:
                _lock_account(db, SUBJECT)
                held.set()
                assert release.wait(10), 'test coordinator did not release leading transaction'
            else:
                second_pid.put(db.scalar(text('SELECT pg_backend_pid()')))
            if kind == 'publication':
                try:
                    plan = repository.registrar_plan(db, SUBJECT, 'publication-race-client', {'plan_json':'{}'},
                        return_id=True, individual_reservation_id=reservation)
                    db.commit()
                    return ('published', plan)
                except ValueError:
                    db.rollback()
                    return ('rejected', None)
            finish_generation(db, reservation, SUBJECT, None, success=False)
            return ('compensated', None)

    with ThreadPoolExecutor(max_workers=2) as executor:
        leading = executor.submit(operation, first, leading=True)
        assert held.wait(5)
        trailing = executor.submit(operation, 'compensation' if first == 'publication' else 'publication', leading=False)
        pid = second_pid.get(timeout=5)
        waiting = False
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                with admin.connect() as db:
                    waiting = db.scalar(text('SELECT cardinality(pg_blocking_pids(:pid)) > 0'), {'pid':pid})
                if waiting:
                    break
                time.sleep(0.02)
            assert waiting and not trailing.done(), 'second transaction must wait on the actual account lock'
        finally:
            release.set()
        results = [leading.result(timeout=10), trailing.result(timeout=10)]
    with Session(admin) as db:
        row = db.get(GenerationReservation, reservation)
        used = db.query(UserSubscription).one().planes_usados_mes
        count = db.query(PlanGenerado).count()
        if first == 'publication':
            assert (row.status, used, count) == ('completed', 1, 1)
            assert row.persisted_at is not None and row.plan_id == results[0][1]
        else:
            assert (row.status, row.persisted_at, used, count) == ('released', None, 0, 0)
            assert results[1] == ('rejected', None)


def test_commit_acknowledgement_loss_is_resolved_from_published_state(publication_pg, monkeypatch):
    from web.database import repository
    from web.database.models import GenerationReservation, PlanGenerado, UserSubscription
    from web.database.tenant_context import tenant_scope
    from web.services.generation_quota import reserve_generation, compensate_individual_generation_failure
    admin, app = publication_pg
    with tenant_scope(SUBJECT), Session(app) as db:
        reservation = reserve_generation(db, SUBJECT, 'commit-acknowledgement').id
    with tenant_scope(SUBJECT), Session(app) as db:
        repository.registrar_plan(db, SUBJECT, 'publication-race-client', {},
            return_id=True, individual_reservation_id=reservation)
        commit = db.commit
        def committed_then_lost():
            commit()
            raise RuntimeError('Synthetic acknowledgement loss after actual COMMIT')
        monkeypatch.setattr(db, 'commit', committed_then_lost)
        with pytest.raises(RuntimeError):
            db.commit()
    with tenant_scope(SUBJECT), Session(app) as db:
        compensate_individual_generation_failure(db, reservation, SUBJECT)
    with Session(admin) as db:
        row = db.get(GenerationReservation, reservation)
        assert row.status == 'completed' and row.persisted_at is not None
        assert db.query(PlanGenerado).count() == 1
        assert db.query(UserSubscription).one().planes_usados_mes == 1

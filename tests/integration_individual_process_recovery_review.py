"""A controlled child dies after real personal publication; no HTTP compensation."""
import hashlib
import multiprocessing
import os

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session, sessionmaker

from tests.integration_individual_generation_recovery_review import (
    SUBJECT, evidence, individual_pg, state,
)
from tests.integration_schema_migrations import migration_database  # noqa: F401

pytestmark = pytest.mark.parametrize('migration_database', ['postgresql'], indirect=True)
CRASH_KEY = 'individual-real-process-commit-crash'


def _publish_then_die(url, objects_root, report_channel):
    """Only the validated UUID app database and parent's synthetic object root."""
    from tests.isolation import prepare_environment, block_external_sockets, validate_postgres_test_url

    validate_postgres_test_url(url)
    os.environ.pop('_METODOBASE_TEST_ROOT', None)
    os.environ['METODOBASE_TEST_DATABASE_URL'] = url
    prepare_environment(discard_inherited=True)
    os.environ['OBJECT_STORAGE_BACKEND'] = 'local'
    os.environ['OBJECT_STORAGE_LOCAL_ROOT'] = objects_root
    block_external_sockets()
    from web.database.engine import get_engine
    from web.database.models import GenerationReservation, PlanGenerado, StoredObject, UserSubscription
    from web.database.tenant_context import tenant_scope
    from web.database.tenant_policy import verify_application_database_role
    from web.routes.planes import _generar_plan_sync
    from web.services.generation_quota import reserve_generation
    from web.services.plan_documents import read_plan_pdf

    engine = get_engine()
    verify_application_database_role(engine)
    with tenant_scope(SUBJECT), Session(engine) as db:
        identity = reserve_generation(db, SUBJECT, CRASH_KEY).id
    # The actual worker runs nutrition/PDF/private PUT and atomic publication.
    # No route or finish/compensation handler runs after it returns.
    result = _generar_plan_sync('individual-recovery-client', 1, SUBJECT, 'opciones',
        individual_reservation_id=identity)
    with tenant_scope(SUBJECT), Session(engine) as db:
        row = db.get(GenerationReservation, identity)
        plan = db.get(PlanGenerado, row.plan_id)
        obj = db.get(StoredObject, plan.pdf_object_id)
        content = read_plan_pdf(db, SUBJECT, plan.id)
        assert row.status == 'completed' and row.persisted_at is not None
        assert row.plan_id == result['plan_id'] and obj.status == 'ready'
        assert db.query(UserSubscription).filter_by(user_id=SUBJECT).one().planes_usados_mes == 1
        assert content.startswith(b'%PDF-')
        report_channel.send({'reservation_id': identity, 'plan_id': plan.id,
            'status': row.status, 'publication_protocol': row.publication_protocol,
            'persisted_at': row.persisted_at.isoformat(), 'object_id': obj.id,
            'pdf_sha256': hashlib.sha256(content).hexdigest(), 'pdf_bytes': len(content)})
    report_channel.close()
    os._exit(23)  # Own synthetic child: bypass all ordinary Python finalizers.


def test_actual_process_death_after_real_worker_commit_cannot_refund_or_generate_twice(
        individual_pg, monkeypatch, tmp_path):
    from web.database import engine as database
    from web.database.models import GenerationReservation, PlanGenerado, UserSubscription
    from web.database.tenant_context import configure_tenant_engine, tenant_scope
    from web.main_web import create_app
    from web.routes import planes
    from web.services.generation_quota import compensate_individual_generation_failure
    from web.settings import get_settings

    admin, old_engine, _, headers = individual_pg
    assert state(admin)['used_credits'] == 0
    context = multiprocessing.get_context('spawn')
    receive, send = context.Pipe(duplex=False)
    child = context.Process(target=_publish_then_die,
        args=(old_engine.url.render_as_string(hide_password=False),
              get_settings().OBJECT_STORAGE_LOCAL_ROOT, send))
    child.start()
    send.close()
    try:
        child.join(50)
        assert not child.is_alive() and child.exitcode == 23, 'Child must die only after verified real publication'
        assert receive.poll(1), 'Child did not verify the durable Plan/ready/marker before death'
        committed = receive.recv()
    finally:
        if child.is_alive():
            child.terminate()
            child.join(5)
        receive.close()

    # Discard the original pool and build a fresh real application/Session
    # adapter. Its HTTP requests still use persisted auth and tenant middleware.
    target = old_engine.url
    old_engine.dispose()
    fresh = configure_tenant_engine(create_engine(target, pool_size=3, max_overflow=0))
    monkeypatch.setattr(database, '_engine', fresh)
    monkeypatch.setattr(database, '_SessionLocal', sessionmaker(bind=fresh, autocommit=False, autoflush=False))
    monkeypatch.setattr(planes, '_generar_plan_sync',
        lambda *args, **kwargs: pytest.fail('Durable replay or exhausted credit must never enter CPU worker'))
    report = {'scope': 'Actual controlled process death after real PostgreSQL restricted-role worker commit; no container-death claim',
        'child_exit_code': child.exitcode, 'child_committed': committed, 'after_child_death': state(admin)}
    try:
        with TestClient(create_app(), raise_server_exceptions=False) as client:
            assert client.get('/api/auth/me', headers=headers).status_code == 200
            replay = client.post('/api/usuario/generar-plan', headers={**headers, 'Idempotency-Key': CRASH_KEY})
            assert replay.status_code == 200, replay.text
            pdf = client.get('/api/usuario/descargar-pdf', params={'plan_id': committed['plan_id']}, headers=headers)
            assert pdf.status_code == 200 and hashlib.sha256(pdf.content).hexdigest() == committed['pdf_sha256']
            with tenant_scope(SUBJECT), Session(fresh) as db:
                compensate_individual_generation_failure(db, committed['reservation_id'], SUBJECT)
                assert db.execute(delete(PlanGenerado).where(PlanGenerado.id == committed['plan_id'],
                    PlanGenerado.gym_id == SUBJECT)).rowcount == 1
                db.commit()
                reservation = db.get(GenerationReservation, committed['reservation_id'])
                assert reservation.plan_id is None and reservation.persisted_at is not None
                compensate_individual_generation_failure(db, reservation.id, SUBJECT)
                compensate_individual_generation_failure(db, reservation.id, SUBJECT)
                assert db.query(UserSubscription).filter_by(user_id=SUBJECT).one().planes_usados_mes == 1
                assert db.query(PlanGenerado).count() == 0
            unavailable = client.post('/api/usuario/generar-plan', headers={**headers, 'Idempotency-Key': CRASH_KEY})
            new_key = client.post('/api/usuario/generar-plan', headers={**headers,
                'Idempotency-Key': 'individual-other-key-after-real-process-death'})
            assert unavailable.status_code == 409 and unavailable.json()['detail']['code'] == 'generation_result_unavailable'
            assert new_key.status_code == 403 and new_key.json()['detail']['code'] == 'monthly_plan_limit'
            report['replay_http_status'] = replay.status_code
            report['deleted_result_http_status'] = unavailable.status_code
            report['new_key_http_status'] = new_key.status_code
        with tenant_scope(SUBJECT), Session(fresh) as db:
            row = db.get(GenerationReservation, committed['reservation_id'])
            assert row.status == 'completed' and row.publication_protocol == 1
            assert row.persisted_at.isoformat() == committed['persisted_at']
            report['final_marker'] = row.persisted_at.isoformat()
        report['final_state'] = state(admin)
        evidence(tmp_path, 'individual-real-process-death-review', report)
    finally:
        fresh.dispose()

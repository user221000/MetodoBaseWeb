"""Independent PostgreSQL checks at the real worker COMMIT and FK boundary."""
import hashlib

from fastapi import HTTPException
import pytest
from sqlalchemy import delete
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import Session

from tests.integration_individual_generation_recovery_review import (
    SUBJECT, evidence, individual_pg, state,
)

pytestmark = pytest.mark.parametrize('migration_database', ['postgresql'], indirect=True)
# Register the fixture dependency imported indirectly through individual_pg.
from tests.integration_schema_migrations import migration_database  # noqa: E402,F401


def durable_reservation(engine):
    from web.database.models import GenerationReservation
    with Session(engine) as db:
        row = db.query(GenerationReservation).filter_by(user_id=SUBJECT).one()
        return {'id': row.id, 'status': row.status, 'plan_id': row.plan_id,
                'publication_protocol': row.publication_protocol,
                'persisted_at': row.persisted_at.isoformat() if row.persisted_at else None}


def test_real_worker_commit_acknowledgement_loss_preserves_plan_credit_and_safe_replay(
        individual_pg, monkeypatch, caplog, tmp_path):
    from web.database import repository
    from web.database.tenant_context import tenant_scope
    from web.services.plan_documents import read_plan_pdf

    admin, application_engine, client, headers = individual_pg
    original_register, original_commit = repository.registrar_plan, Session.commit
    private_marker = 'synthetic-review-private-commit-parameter'
    report = {'scope': 'Real authenticated PostgreSQL/core/PDF; only final worker COMMIT acknowledgement is lost',
              'before': state(admin), 'injected_commits': 0}

    def register_and_mark(db, *args, **kwargs):
        result = original_register(db, *args, **kwargs)
        if kwargs.get('individual_reservation_id') is not None:
            db.info['qa_lose_publication_commit_ack'] = True
        return result

    def commit_and_lose_acknowledgement(db):
        lose_ack = db.info.pop('qa_lose_publication_commit_ack', False)
        original_commit(db)
        if lose_ack:
            # A separate real connection must see Plan+ready+completed before
            # injecting the transport-level failure back into the worker.
            report['injected_commits'] += 1
            report['after_physical_commit'] = state(admin)
            report['committed_reservation'] = durable_reservation(admin)
            raise StatementError('Synthetic COMMIT acknowledgement loss',
                'COMMIT synthetic_private=:value', {'value': private_marker}, RuntimeError(private_marker))

    monkeypatch.setattr(repository, 'registrar_plan', register_and_mark)
    monkeypatch.setattr(Session, 'commit', commit_and_lose_acknowledgement)
    key = 'individual-actual-commit-ack-lost'
    response = client.post('/api/usuario/generar-plan', headers={**headers, 'Idempotency-Key': key})
    report['failed_http_status'] = response.status_code
    report['after_http_failure'] = state(admin)
    report['final_reservation'] = durable_reservation(admin)
    committed = report['after_physical_commit']
    plan_id = committed['plans'][0]['id']
    with tenant_scope(SUBJECT), Session(application_engine) as db:
        content = read_plan_pdf(db, SUBJECT, plan_id)
    report['real_pdf_sha256'] = hashlib.sha256(content).hexdigest()
    replay = client.post('/api/usuario/generar-plan', headers={**headers, 'Idempotency-Key': key})
    denied = client.post('/api/usuario/generar-plan', headers={**headers,
        'Idempotency-Key': 'individual-new-key-after-ack-loss'})
    report['replay_http_status'], report['new_key_http_status'] = replay.status_code, denied.status_code
    evidence(tmp_path, 'individual-commit-ack-loss-review', report)

    assert response.status_code in {500, 503}
    assert report['injected_commits'] == 1
    assert content.startswith(b'%PDF-')
    assert committed == report['after_http_failure']
    assert committed['used_credits'] == 1 and len(committed['plans']) == 1
    assert committed['objects'][0]['status'] == 'ready'
    assert report['committed_reservation'] == report['final_reservation']
    assert report['final_reservation']['status'] == 'completed'
    assert report['final_reservation']['publication_protocol'] == 1
    assert report['final_reservation']['persisted_at'] is not None
    assert replay.status_code == 200 and denied.status_code == 403
    assert denied.json()['detail']['code'] == 'monthly_plan_limit'
    assert private_marker not in response.text + caplog.text
    assert 'COMMIT synthetic_private' not in response.text + caplog.text


def test_real_completed_plan_fk_set_null_keeps_marker_and_never_restores_credit(individual_pg, tmp_path):
    from web.database.models import GenerationReservation, PlanGenerado
    from web.database.tenant_context import tenant_scope
    from web.services.generation_quota import compensate_individual_generation_failure, finish_generation

    admin, application_engine, client, headers = individual_pg
    key = 'individual-worker-before-fk-set-null'
    generated = client.post('/api/usuario/generar-plan', headers={**headers, 'Idempotency-Key': key})
    assert generated.status_code == 200, generated.text
    before = durable_reservation(admin)
    assert before['status'] == 'completed' and before['persisted_at'] is not None
    with tenant_scope(SUBJECT), Session(application_engine) as db:
        assert db.execute(delete(PlanGenerado).where(PlanGenerado.id == before['plan_id'],
            PlanGenerado.gym_id == SUBJECT)).rowcount == 1
        db.commit()
        after_delete = db.get(GenerationReservation, before['id'])
        assert after_delete.plan_id is None
        compensate_individual_generation_failure(db, before['id'], SUBJECT)
        compensate_individual_generation_failure(db, before['id'], SUBJECT)
        with pytest.raises(HTTPException) as unavailable:
            finish_generation(db, before['id'], SUBJECT, before['plan_id'], success=True)
        assert unavailable.value.status_code == 503
        db.rollback()
    replay = client.post('/api/usuario/generar-plan', headers={**headers, 'Idempotency-Key': key})
    denied = client.post('/api/usuario/generar-plan', headers={**headers,
        'Idempotency-Key': 'individual-new-key-after-plan-delete'})
    after = durable_reservation(admin)
    observed = state(admin)
    evidence(tmp_path, 'individual-real-plan-fk-set-null-review', {
        'scope': 'Real worker PDF committed before actual restricted-role DELETE/FK SET NULL and repeated compensation',
        'before': before, 'after': after, 'state': observed,
        'replay_http_status': replay.status_code, 'new_key_http_status': denied.status_code})
    assert after == {**before, 'plan_id': None}
    assert observed['used_credits'] == 1 and observed['plans'] == []
    assert len(observed['objects']) == 1 and observed['objects'][0]['status'] == 'ready'
    assert replay.status_code == 409 and replay.json()['detail']['code'] == 'generation_result_unavailable'
    assert denied.status_code == 403 and denied.json()['detail']['code'] == 'monthly_plan_limit'

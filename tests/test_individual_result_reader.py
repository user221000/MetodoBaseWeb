"""Owner/client consistency and soft-delete defense for individual JSON results."""
from datetime import datetime, timezone
import logging

from fastapi import HTTPException
import pytest

from tests.test_billing_integrity import billing_case  # noqa: F401


@pytest.mark.parametrize('association', ['owned', 'inactive', 'plan_deleted', 'client_deleted', 'mixed', 'foreign_plan'])
def test_reader_replay_and_success_verifier_share_the_same_boundary(billing_case, monkeypatch, association):
    from web.database.models import Cliente, GenerationReservation, PlanGenerado, Usuario, UserSubscription
    from web.routes import planes
    from web.services.billing_integrity import current_quota_period
    from web.services.generation_quota import finish_generation, read_individual_plan_result
    client, factory, subject = billing_case
    with factory() as db:
        db.add(Usuario(id='other-history-owner', email='other-history@example.invalid',
            nombre='Synthetic', tipo='usuario', password_hash='synthetic'))
        db.flush()
        db.add(Cliente(id_cliente='other-history-client', gym_id='other-history-owner', nombre='Synthetic'))
        profile = db.query(Cliente).filter_by(id_cliente='billing-profile').one()
        if association == 'inactive':
            profile.activo = False
        if association == 'client_deleted':
            profile.deleted_at = datetime.now(timezone.utc)
        plan = PlanGenerado(gym_id='other-history-owner' if association == 'foreign_plan' else subject['id'],
            id_cliente='other-history-client' if association == 'mixed' else 'billing-profile',
            plan_json='{"synthetic_private_result":{"review_marker":"owned-history"}}',
            deleted_at=datetime.now(timezone.utc) if association == 'plan_deleted' else None)
        db.add(plan)
        db.flush()
        plan_id = plan.id
        reservation = GenerationReservation(user_id=subject['id'], request_key='history-reader',
            period=current_quota_period(), status='completed', plan_id=plan.id, publication_protocol=0)
        db.add(reservation)
        db.add(UserSubscription(user_id=subject['id'], plan='starter', status='active',
            max_planes_mes=1, planes_usados_mes=1, mes_actual=current_quota_period()))
        db.commit()
        identity = reservation.id
    valid = association in {'owned', 'inactive'}
    with factory() as db:
        assert (read_individual_plan_result(db, subject['id'], plan_id) is not None) is valid
        if valid:
            finish_generation(db, identity, subject['id'], plan_id, success=True)
        else:
            with pytest.raises(HTTPException) as refused:
                finish_generation(db, identity, subject['id'], plan_id, success=True)
            assert refused.value.status_code == 503
        db.rollback()
    monkeypatch.setattr(planes, '_generar_plan_sync', lambda *args, **kwargs: pytest.fail('Replay cannot generate'))
    response = client.post('/api/usuario/generar-plan', headers={'Idempotency-Key':'history-reader'})
    if valid:
        assert response.status_code == 200, response.text
        assert 'owned-history' in response.text
    else:
        assert response.status_code == 409
        assert 'synthetic_private_result' not in response.text
    with factory() as db:
        assert db.get(GenerationReservation, identity).status == 'completed'
        assert db.query(UserSubscription).filter_by(user_id=subject['id']).one().planes_usados_mes == 1


@pytest.mark.parametrize('change', ['plan_deleted', 'client_deleted', 'mixed'])
def test_response_rechecks_association_after_success_verification(billing_case, monkeypatch, change):
    from web.database.models import Cliente, GenerationReservation, PlanGenerado, Usuario, UserSubscription
    from web.database.repository import registrar_plan
    from web.routes import planes
    from web.services import generation_quota
    client, factory, subject = billing_case
    plan_ids = []
    def committed_plan(*args, individual_reservation_id=None):
        with factory() as db:
            plan_id = registrar_plan(db, subject['id'], 'billing-profile',
                {'plan_json':'{"synthetic_private_result":{"review_marker":"final-read-secret"}}'},
                return_id=True, individual_reservation_id=individual_reservation_id)
            db.commit()
            plan_ids.append(plan_id)
            return {'plan_id':plan_id}
    real_finish = generation_quota.finish_generation
    def verified_then_changed(*args, **kwargs):
        real_finish(*args, **kwargs)
        with factory() as db:
            if change == 'plan_deleted':
                db.get(PlanGenerado, plan_ids[0]).deleted_at = datetime.now(timezone.utc)
            elif change == 'client_deleted':
                db.query(Cliente).filter_by(id_cliente='billing-profile').one().deleted_at = datetime.now(timezone.utc)
            else:
                db.add(Usuario(id='other-final-owner', email='other-final@example.invalid',
                    nombre='Synthetic', tipo='usuario', password_hash='synthetic'))
                db.flush()
                db.add(Cliente(id_cliente='other-final-client', gym_id='other-final-owner', nombre='Synthetic'))
                db.flush()
                db.get(PlanGenerado, plan_ids[0]).id_cliente = 'other-final-client'
            db.commit()
    monkeypatch.setattr(planes, '_generar_plan_sync', committed_plan)
    monkeypatch.setattr(generation_quota, 'finish_generation', verified_then_changed)
    response = client.post('/api/usuario/generar-plan', headers={'Idempotency-Key':'final-read'})
    assert response.status_code == 409
    assert 'final-read-secret' not in response.text
    with factory() as db:
        assert db.query(GenerationReservation).one().status == 'completed'
        assert db.query(UserSubscription).one().planes_usados_mes == 1


def test_generation_error_logs_only_technical_class(billing_case, monkeypatch, caplog):
    from web.routes import planes
    client, _, subject = billing_case
    private = 'synthetic-private-error-value'
    def failed_worker(*args, **kwargs):
        raise RuntimeError(private)
    monkeypatch.setattr(planes, '_generar_plan_sync', failed_worker)
    caplog.clear()
    with caplog.at_level(logging.ERROR):
        response = client.post('/api/usuario/generar-plan', headers={'Idempotency-Key':'class-only-log'})
    assert response.status_code == 500
    assert 'class=RuntimeError' in caplog.text
    assert private not in caplog.text + response.text
    assert subject['id'] not in caplog.text and subject['email'] not in caplog.text

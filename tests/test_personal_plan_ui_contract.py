"""Additive personal plan IDs and shared authorized query; no authority doubles claim."""
from datetime import datetime, timedelta, timezone

import pytest

from tests.test_billing_integrity import billing_case  # noqa: F401


def stored(db, subject, profile='billing-profile', **values):
    from web.database.models import PlanGenerado
    row = PlanGenerado(gym_id=subject, id_cliente=profile,
        plan_json='{"synthetic_result": {"marker": "owned-result"}}', **values)
    db.add(row)
    db.flush()
    return row.id


def test_current_and_replay_return_the_same_persisted_id_and_personal_pdf_url(billing_case):
    from web.database.models import GenerationReservation
    from web.services.billing_integrity import current_quota_period
    client, factory, principal = billing_case
    with factory() as db:
        identity = stored(db, principal['id'])
        db.add(GenerationReservation(user_id=principal['id'], request_key='ui-replay',
            status='completed', plan_id=identity, period=current_quota_period(), publication_protocol=0))
        db.commit()
    current = client.get('/api/usuario/mi-plan')
    replay = client.post('/api/usuario/generar-plan', headers={'Idempotency-Key':'ui-replay'})
    assert current.status_code == replay.status_code == 200
    for response in (current, replay):
        assert response.json()['plan_id'] == identity
        assert response.json()['pdf_url'] == f'/api/usuario/descargar-pdf?plan_id={identity}'
        assert 'ruta_pdf' not in response.json()


@pytest.mark.parametrize('association', ['owned', 'inactive', 'plan_deleted', 'client_deleted', 'mixed', 'foreign_plan'])
def test_current_and_history_share_the_result_reader_boundary(billing_case, association):
    from web.database.models import Cliente, PlanGenerado, Usuario
    from web.services.generation_quota import individual_plan_results_query, read_individual_plan_result
    client, factory, principal = billing_case
    with factory() as db:
        db.add(Usuario(id='ui-other', email='ui-other@example.invalid', nombre='Synthetic', tipo='usuario', password_hash='unused'))
        db.flush()
        db.add(Cliente(id_cliente='ui-other-client', gym_id='ui-other', nombre='Synthetic'))
        profile = db.query(Cliente).filter_by(id_cliente='billing-profile').one()
        if association == 'inactive': profile.activo = False
        if association == 'client_deleted': profile.deleted_at = datetime.now(timezone.utc)
        identity = stored(db, 'ui-other' if association == 'foreign_plan' else principal['id'],
            'ui-other-client' if association == 'mixed' else 'billing-profile',
            deleted_at=datetime.now(timezone.utc) if association == 'plan_deleted' else None)
        db.commit()
        expected = association in {'owned', 'inactive'}
        assert (read_individual_plan_result(db, principal['id'], identity) is not None) is expected
        assert [p.id for p in individual_plan_results_query(db, principal['id']).all()] == ([identity] if expected else [])
    current = client.get('/api/usuario/mi-plan').json()
    history = client.get('/api/usuario/historial').json()
    assert current['plan_id'] == (identity if expected else None)
    assert [p['id'] for p in history['planes']] == ([identity] if expected else [])
    if not expected:
        assert current['plan'] is None and current['pdf_url'] is None
        assert 'owned-result' not in str(current) + str(history)


def test_deleted_newer_plan_does_not_hide_older_live_plan(billing_case):
    client, factory, principal = billing_case
    with factory() as db:
        older = stored(db, principal['id'], fecha_generacion=datetime.now(timezone.utc)-timedelta(days=1))
        stored(db, principal['id'], deleted_at=datetime.now(timezone.utc))
        db.commit()
    assert client.get('/api/usuario/mi-plan').json()['plan_id'] == older
    assert [p['id'] for p in client.get('/api/usuario/historial').json()['planes']] == [older]


def test_deleted_existing_personal_profile_is_not_replaced_by_another_profile(billing_case):
    from web.database.models import Cliente
    client, factory, principal = billing_case
    with factory() as db:
        db.query(Cliente).filter_by(id_cliente='billing-profile').one().deleted_at = datetime.now(timezone.utc)
        db.add(Cliente(id_cliente='ui-later-profile', gym_id=principal['id'], nombre='Synthetic'))
        stored(db, principal['id'], 'ui-later-profile')
        db.commit()
    assert client.get('/api/usuario/mi-plan').json()['plan_id'] is None
    assert client.get('/api/usuario/historial').json()['planes'] == []

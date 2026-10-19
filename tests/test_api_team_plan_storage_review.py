"""API adapter: persisted team RBAC, owner ledger and private documents.

Only the CPU/PDF renderer is substituted. Auth, tenant middleware, reservation,
object publication, transactional plan linkage and exact downloads are real.
"""
from datetime import datetime, timedelta, timezone
import importlib

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session


PDF = b'%PDF-1.4\nSynthetic API team boundary review\n%%EOF'


def _persist_private_pdf(owner, client, *, reservation_id=None):
    from web.database.engine import get_engine
    from web.database import repository
    from web.services.private_objects import publish_pending_object, mark_object_ready

    descriptor = publish_pending_object(owner, 'plan_pdf', PDF, 'application/pdf')
    with Session(get_engine()) as db:
        object_id = mark_object_ready(db, owner, descriptor, 'plan_pdf')
        plan_id = repository.registrar_plan(db, owner, client,
            {'pdf_object_id': object_id, 'plan_json': '{"synthetic":true}'},
            return_id=True, reservation_id=reservation_id)
        db.commit()
    return plan_id


@pytest.fixture
def api_team(test_gym_user):
    from web.auth import crear_access_token
    from web.database.engine import get_engine
    from web.database.models import Cliente, Subscription, Usuario, UserRole

    owner = test_gym_user['id']
    identities = {}
    with Session(get_engine()) as db:
        db.add(Usuario(id='api-review-foreign-owner', email='api-foreign@example.invalid',
            nombre='Synthetic Foreign', password_hash='synthetic', tipo='gym',
            role=UserRole.OWNER, activo=True, session_version=0))
        for label, role in [('nutri', UserRole.NUTRIOLOGO), ('viewer', UserRole.VIEWER)]:
            identity = dict(id='api-storage-review-' + label, email='api-' + label + '@example.invalid',
                nombre='Synthetic ' + label, tipo='usuario', role=role.value, team_gym_id=owner)
            db.add(Usuario(**{key: value for key, value in identity.items() if key != 'role'},
                role=role, password_hash='synthetic', activo=True, session_version=0))
            identities[label] = identity
        db.flush()
        db.add(Subscription(gym_id=owner, plan='clinica', status='active', max_clientes=0,
            current_period_start=datetime.now(timezone.utc) - timedelta(days=1),
            current_period_end=datetime.now(timezone.utc) + timedelta(days=1)))
        db.add(Cliente(id_cliente='api-storage-owner-client', gym_id=owner, nombre='Synthetic owner client',
            edad=30, peso_kg=75, estatura_cm=175, sexo='M', nivel_actividad='moderada', objetivo='mantenimiento'))
        db.add(Cliente(id_cliente='api-storage-foreign-client', gym_id='api-review-foreign-owner',
            nombre='Synthetic foreign client', edad=30, peso_kg=75, estatura_cm=175))
        db.commit()
    owned_plan = _persist_private_pdf(owner, 'api-storage-owner-client')
    foreign_plan = _persist_private_pdf('api-review-foreign-owner', 'api-storage-foreign-client')
    headers = {label: {'Authorization': 'Bearer ' + crear_access_token(identity)}
        for label, identity in identities.items()}
    with TestClient(importlib.import_module('api.app').create_app(), raise_server_exceptions=False) as client:
        yield client, owner, headers, owned_plan, foreign_plan


def test_api_nutritionist_generation_uses_parent_clinic_and_transactional_owner_ledger(api_team, monkeypatch):
    from web.database.engine import get_engine
    from web.database.models import GymGenerationReservation, PlanGenerado
    from web.database.tenant_context import current_tenant
    from api.routes import planes

    client, owner, headers, _, _ = api_team
    calls = []
    def cpu(gym_id, id_cliente, plan_numero, tipo_plan='menu_fijo', *, reservation_id=None):
        assert gym_id == owner and current_tenant.get() == owner
        calls.append(reservation_id)
        plan_id = _persist_private_pdf(gym_id, id_cliente, reservation_id=reservation_id)
        return {'success': True, 'plan_id': plan_id, 'id_cliente': id_cliente, 'tipo_plan': tipo_plan,
                'pdf_url': '/api/planes/' + str(plan_id) + '/pdf'}
    monkeypatch.setattr(planes, '_generar_plan_sync', cpu)
    request_headers = {**headers['nutri'], 'Idempotency-Key': 'synthetic-api-team-review-key'}
    payload = {'id_cliente': 'api-storage-owner-client', 'plan_numero': 2, 'tipo_plan': 'menu_fijo'}
    response = client.post('/api/generar-plan', headers=request_headers, json=payload)
    assert response.status_code == 200, response.text
    replay = client.post('/api/generar-plan', headers=request_headers, json=payload)
    assert replay.status_code == 200 and replay.json() == response.json()
    assert len(calls) == 1
    with Session(get_engine()) as db:
        reservation = db.query(GymGenerationReservation).one()
        assert reservation.gym_id == owner and reservation.catalog_plan == 'clinica'
        assert reservation.status == 'completed' and reservation.persisted_at is not None
        assert db.get(PlanGenerado, reservation.plan_id).gym_id == owner
    assert client.get(response.json()['pdf_url'], headers=headers['nutri']).content == PDF
    foreign = client.post('/api/generar-plan', headers={**headers['nutri'], 'Idempotency-Key': 'synthetic-foreign-review'},
        json={**payload, 'id_cliente': 'api-storage-foreign-client'})
    assert foreign.status_code == 404 and len(calls) == 1


@pytest.mark.parametrize('role', ['nutri', 'viewer'])
def test_api_team_exact_and_legacy_downloads_preserve_owner_scope(api_team, role):
    client, _, headers, owned, foreign = api_team
    exact = client.get('/api/planes/' + str(owned) + '/pdf', headers=headers[role])
    assert exact.status_code == 200 and exact.content == PDF
    assert client.get('/api/planes/' + str(foreign) + '/pdf', headers=headers[role]).status_code == 404
    legacy = client.get('/api/descargar-pdf/api-storage-owner-client', headers=headers[role])
    assert legacy.status_code == 200 and legacy.content == PDF
    assert client.get('/api/descargar-pdf/api-storage-foreign-client', headers=headers[role]).status_code == 404
    if role == 'viewer':
        denied = client.post('/api/generar-plan', headers=headers[role], json={'id_cliente': 'api-storage-owner-client'})
        assert denied.status_code == 403
        from web.database.engine import get_engine
        from web.database.models import GymGenerationReservation
        with Session(get_engine()) as db:
            assert db.query(GymGenerationReservation).count() == 0

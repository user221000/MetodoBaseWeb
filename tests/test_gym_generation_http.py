"""Real nutrition/PDF/publication and exact replay through both HTTP adapters."""
import importlib
import json
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session


@pytest.mark.parametrize('factory', ['web.main_web', 'api.app'])
@pytest.mark.parametrize('plan_type', ['menu_fijo', 'opciones'])
def test_shared_worker_publishes_one_owned_pdf_and_replays_exact_response(test_gym_user, factory, plan_type):
    from web.database.engine import get_engine
    from web.database.models import Cliente, GymGenerationReservation, PlanGenerado, StoredObject
    client_id = str(uuid.uuid4())
    with Session(get_engine()) as db:
        db.add(Cliente(id_cliente=client_id, gym_id=test_gym_user['id'], nombre='Synthetic Nutrition',
            edad=30, sexo='M', peso_kg=75, estatura_cm=175, grasa_corporal_pct=20,
            nivel_actividad='moderada', objetivo='mantenimiento'))
        db.commit()
    body = {'id_cliente':client_id,'plan_numero':1,'tipo_plan':plan_type}
    headers = {**test_gym_user['auth_headers'], 'Idempotency-Key':'real-worker-' + plan_type}
    with TestClient(importlib.import_module(factory).create_app(), raise_server_exceptions=False) as client:
        generated = client.post('/api/generar-plan', json=body, headers=headers)
        assert generated.status_code == 200, generated.text
        result = generated.json()
        assert result['tipo_plan'] == plan_type and result['id_cliente'] == client_id
        assert result['pdf_url'] == '/api/planes/' + str(result['plan_id']) + '/pdf'
        assert 'ruta_pdf' not in result
        repeated = client.post('/api/generar-plan', json=body, headers=headers)
        assert repeated.status_code == 200 and repeated.json() == result
        conflict = client.post('/api/generar-plan', json={**body,'plan_numero':2}, headers=headers)
        assert conflict.status_code == 409
        downloaded = client.get('/api/descargar-pdf/' + client_id, headers=test_gym_user['auth_headers'])
        assert downloaded.status_code == 200 and downloaded.content.startswith(b'%PDF')
    with Session(get_engine()) as db:
        plan = db.query(PlanGenerado).filter_by(gym_id=test_gym_user['id']).one()
        reservation = db.query(GymGenerationReservation).filter_by(gym_id=test_gym_user['id']).one()
        assert reservation.status == 'completed' and reservation.plan_id == plan.id == result['plan_id']
        assert reservation.persisted_at is not None and json.loads(reservation.result_json) == result
        assert json.loads(plan.plan_json) == result['plan']
        obj = db.get(StoredObject, plan.pdf_object_id)
        assert obj.status == 'ready' and obj.gym_id == test_gym_user['id'] and obj.kind == 'plan_pdf'
        assert not plan.ruta_pdf
        assert db.query(Cliente).filter_by(id_cliente=client_id).one().total_planes_generados == 1


def test_same_display_name_and_second_cannot_overwrite_another_gym_pdf(test_gym_user, monkeypatch):
    from datetime import datetime, timezone
    from web.auth import crear_access_token
    from web.database.engine import get_engine
    from web.database.models import Cliente, Usuario, UserRole
    from web.main_web import create_app
    from web.services import plan_generation
    class SameSecond(datetime):
        @classmethod
        def now(cls, tz=None):
            value = datetime(2026,10,18,18,tzinfo=timezone.utc)
            return value.astimezone(tz) if tz else value.replace(tzinfo=None)
    monkeypatch.setattr(plan_generation, 'datetime', SameSecond, raising=False)
    other = {'id':str(uuid.uuid4()),'email':'other-pdf-owner@example.test','nombre':'Synthetic',
        'tipo':'gym','role':'owner','session_version':0}
    with Session(get_engine()) as db:
        db.add(Usuario(id=other['id'],email=other['email'],nombre=other['nombre'],tipo='gym',
            role=UserRole.OWNER,password_hash='unused-synthetic',activo=True))
        db.commit()
        for index, owner in enumerate((test_gym_user, other)):
            db.add(Cliente(id_cliente='same-name-client-' + str(index),gym_id=owner['id'],nombre='Same Synthetic Name',
                edad=30,sexo='M',peso_kg=75 + index*10,estatura_cm=175,grasa_corporal_pct=20,
                nivel_actividad='moderada',objetivo='mantenimiento'))
        db.commit()
    urls = []
    first_pdf = None
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        for index, owner in enumerate((test_gym_user, other)):
            response = client.post('/api/generar-plan', json={'id_cliente':'same-name-client-' + str(index)},
                headers={'Authorization':'Bearer ' + crear_access_token(owner),'Idempotency-Key':'same-name-' + str(index)})
            assert response.status_code == 200, response.text
            urls.append(response.json()['pdf_url'])
            if index == 0:
                first_pdf = client.get(urls[0], headers=test_gym_user['auth_headers']).content
        assert urls[0] != urls[1]
        assert client.get(urls[0], headers=test_gym_user['auth_headers']).content == first_pdf
        assert client.get(urls[1], headers=test_gym_user['auth_headers']).status_code == 404

"""A persisted team member keeps a separate personal profile, including legacy tipo."""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


@pytest.mark.parametrize('member_type', ['usuario', 'gym'])
def test_member_personal_profile_is_separate_from_professional_team(test_gym_user, member_type):
    from web.auth import crear_access_token
    from web.database.engine import get_engine
    from web.database.models import Usuario, UserRole, Cliente
    from web.main_web import create_app
    member_id = str(uuid.uuid4())
    with Session(get_engine()) as db:
        db.add(Usuario(id=member_id, email=member_id + '@example.test', password_hash='unused-synthetic',
            nombre='Synthetic Member', tipo=member_type, role=UserRole.VIEWER, team_gym_id=test_gym_user['id']))
        db.commit()
        db.add(Cliente(id_cliente='personal-client', gym_id=member_id, nombre='Personal', edad=32, peso_kg=78))
        db.add(Cliente(id_cliente='professional-client', gym_id=test_gym_user['id'], nombre='Professional', edad=55, peso_kg=110))
        db.commit()
    token = crear_access_token({'id': member_id, 'email': member_id + '@example.test', 'nombre': 'Synthetic Member',
        'apellido': '', 'tipo': member_type, 'role': 'viewer', 'team_gym_id': test_gym_user['id']})
    with TestClient(create_app(), headers={'Authorization': 'Bearer ' + token}) as client:
        personal = client.get('/api/usuario/perfil')
        assert personal.status_code == 200
        assert personal.json()['edad'] == 32 and personal.json()['peso_kg'] == 78
        professional = client.get('/api/clientes')
        assert professional.status_code == 200
        assert 'professional-client' in professional.text
        assert 'personal-client' not in professional.text


def test_owner_gym_without_membership_does_not_enter_individual_routes(web_auth_client):
    assert web_auth_client.get('/api/usuario/perfil').status_code == 403

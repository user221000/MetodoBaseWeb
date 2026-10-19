"""Missing-route baseline and future regression; real auth, synthetic local data."""
from contextlib import contextmanager
import importlib
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session


@pytest.fixture(params=['web.main_web','api.app'])
def link_http(request,monkeypatch):
    from web import auth
    from web.database.engine import get_engine
    from web.database.models import Usuario,UserRole,Cliente
    from web.settings import get_settings
    from web.services import email_service
    assert get_engine().dialect.name=='sqlite'
    settings=get_settings()
    monkeypatch.setattr(settings,'BASE_URL','https://member.example.invalid')
    monkeypatch.setattr(settings,'RESEND_API_KEY','re_synthetic_offline_only')
    mail=[]
    monkeypatch.setattr(email_service,'_send',lambda recipient,subject,html,**kwargs:mail.append((recipient,subject,html)) or True)
    app=importlib.import_module(request.param).create_app()
    owner,person,client_id=(str(uuid.uuid4()) for _ in range(3))
    with Session(get_engine()) as db:
        db.add_all([Usuario(id=owner,email='link-owner@example.invalid',nombre='Synthetic gym',password_hash='synthetic',tipo='gym',role=UserRole.OWNER),
            Usuario(id=person,email='link-person@example.invalid',nombre='Synthetic person',password_hash='synthetic',tipo='usuario',role=UserRole.VIEWER)])
        db.flush();db.add(Cliente(id_cliente=client_id,gym_id=owner,nombre='Synthetic client',activo=True));db.commit()
        headers={identity:{'Authorization':'Bearer '+auth.crear_access_token(auth.identity_from_user(db.get(Usuario,identity),db))} for identity in (owner,person)}
    with TestClient(app,raise_server_exceptions=False) as client:
        assert client.get('/api/auth/me',headers=headers[person]).status_code==200
        yield {'client':client,'engine':get_engine(),'owner':owner,'person':person,'client_id':client_id,'headers':headers,'mail':mail}


def test_professional_can_issue_specific_invitation_without_a_recipient_account_lookup(link_http):
    case=link_http
    response=case['client'].post('/api/clientes/'+case['client_id']+'/vinculacion/invitaciones',
        headers=case['headers'][case['owner']],json={'recipient_email':'not-yet-registered@example.invalid','request_key':'before-contract'})
    assert response.status_code==202,response.text
    result=response.json()
    assert result['status']=='pending' and result['delivery_status']=='not_confirmed'
    assert len(result['link_id'])==len(result['invitation_id'])==36
    assert all(key not in result for key in ('token','token_hash','url','recipient_user_id'))


def test_registered_person_can_read_empty_explicit_memberships(link_http):
    case=link_http
    response=case['client'].get('/api/usuario/vinculos',headers=case['headers'][case['person']])
    assert response.status_code==200,response.text
    assert response.json()['items']==[]

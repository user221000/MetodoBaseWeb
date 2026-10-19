"""Invitation bearer -> professional membership -> independent personal scope.

HTTP, canonical JWT identity, database role and RLS policies are real. Only
outbound email transport is disabled, consistently with the isolated runner.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from tests.integration_onboarding_postgres import onboarding_application
from tests.integration_schema_migrations import migration_database


@pytest.mark.parametrize('migration_database', ['postgresql'], indirect=True)
@pytest.mark.parametrize('persisted_type', ['usuario', 'gym'])
def test_invitation_and_revocation_preserve_personal_subject_under_rls(onboarding_application, monkeypatch, persisted_type):
    from web.database.models import Usuario, Cliente, Subscription
    from web.auth import crear_access_token, identity_from_user

    client, admin = onboarding_application
    monkeypatch.setattr('web.services.email_service.send_team_invitation', lambda *args, **kwargs: False)
    password = 'Synthetic-invitation-password-2026'
    registered = client.post('/api/auth/registro', json={'email': 'inviting-owner@example.test',
        'password': password, 'nombre': 'Invitation Owner', 'tipo': 'gym'})
    assert registered.status_code == 200, registered.text
    owner_headers = {'Authorization': 'Bearer ' + registered.json()['token']}
    with Session(admin) as db:
        owner = db.query(Usuario).filter_by(email='inviting-owner@example.test').one()
        owner_id = owner.id
        db.add(Subscription(gym_id=owner_id, plan='clinica', status='active',
            current_period_end=datetime.now(timezone.utc) + timedelta(days=30)))
        db.add(Cliente(id_cliente='owner-professional-client', gym_id=owner_id, nombre='Professional', edad=51))
        db.commit()
    issued = client.post('/api/gym/team/invite', headers=owner_headers,
        json={'email': 'pg-invited-professional@example.test', 'nombre': 'Professional', 'role': 'viewer'})
    assert issued.status_code == 200, issued.text
    token = issued.json()['invitation_token']
    info = client.post('/api/auth/invite-info', json={'token': token})
    assert info.status_code == 200 and info.json()['can_accept'] is True, info.text
    accepted = client.post('/api/auth/accept-invite', json={'token': token, 'password': password})
    assert accepted.status_code == 200, accepted.text
    member_id = accepted.json()['user']['id']
    assert accepted.json()['user']['team_gym_id'] == owner_id
    assert client.post('/api/auth/accept-invite', json={'token': token, 'password': password}).status_code in (400, 409)
    with Session(admin) as db:
        member = db.get(Usuario, member_id)
        member.tipo = persisted_type
        db.add(Cliente(id_cliente='independent-personal-client', gym_id=member_id, nombre='Personal', edad=32))
        db.commit()
        # Legacy persisted tipo is intentionally tested through canonical auth.
        identity = identity_from_user(member, db)
    member_headers = {'Authorization': 'Bearer ' + crear_access_token(identity)}
    personal = client.get('/api/usuario/perfil', headers=member_headers)
    assert personal.status_code == 200 and personal.json()['edad'] == 32, personal.text
    professional = client.get('/api/clientes', headers=member_headers)
    assert professional.status_code == 200, professional.text
    assert 'owner-professional-client' in professional.text and 'independent-personal-client' not in professional.text
    removed = client.delete('/api/gym/team/' + member_id, headers=owner_headers)
    assert removed.status_code == 200, removed.text
    assert client.get('/api/usuario/perfil', headers=member_headers).status_code == 401
    with Session(admin) as db:
        member = db.get(Usuario, member_id)
        assert member.activo and member.team_gym_id is None and member.tipo == 'usuario'
        assert db.query(Cliente).filter_by(gym_id=member_id).one().edad == 32
        personal_identity = identity_from_user(member, db)
    detached_headers = {'Authorization': 'Bearer ' + crear_access_token(personal_identity)}
    own_after = client.get('/api/usuario/perfil', headers=detached_headers)
    assert own_after.status_code == 200 and own_after.json()['edad'] == 32
    forbidden_professional = client.get('/api/clientes', headers=detached_headers)
    assert forbidden_professional.status_code in (200, 403)
    assert 'owner-professional-client' not in forbidden_professional.text

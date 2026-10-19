"""Current31 nondelegation/opacity matrix; original current30 assertions remain.

The old404 expectation is investigated, never weakened. Actual authenticated
owner/MFA, exact issue and real team route execute; no MFA/business monkeypatch.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from tests.test_team_invitation_contract import team_case


@pytest.mark.parametrize('action', ['role', 'remove', 'resend'])
@pytest.mark.parametrize('mode', ['own-grant-to-foreign', 'denied-issue-then-business', 'no-grant'])
def test_current31_foreign_mutation_is_opaque_and_never_inherits_a_grant(team_case, action, mode):
    from web.database.models import Usuario, UserRole, MfaAuthorization
    from web.services.mfa_crypto import opaque_digest

    client, factory, principal, captured = team_case
    with factory() as db:
        db.add(Usuario(id='matrix-other-owner', email='matrix-owner@example.invalid', nombre='Foreign owner',
            password_hash='unused', tipo='gym', role=UserRole.OWNER, activo=True))
        db.commit()
        db.add_all([
            Usuario(id='matrix-own-member', email='matrix-own@example.invalid', nombre='Own pending',
                password_hash='PENDING_INVITATION', tipo='usuario', role=UserRole.VIEWER,
                team_gym_id=principal['id'], activo=False, invitation_token='x'*64,
                invitation_expires=datetime.now(timezone.utc)+timedelta(hours=1), invitation_role=UserRole.VIEWER),
            Usuario(id='matrix-foreign-member', email='matrix-private@example.invalid', nombre='Foreign private name',
                password_hash='PENDING_INVITATION', tipo='usuario', role=UserRole.VIEWER,
                team_gym_id='matrix-other-owner', activo=False, invitation_token='y'*64,
                invitation_expires=datetime.now(timezone.utc)+timedelta(hours=1), invitation_role=UserRole.VIEWER),
        ])
        db.commit()

    method, suffix, body = ('PATCH', '/role', {'role':'admin'}) if action=='role' else (
        ('DELETE', '', {}) if action=='remove' else ('POST', '/resend-invite', {}))
    own_path='/api/gym/team/matrix-own-member'+suffix
    foreign_path='/api/gym/team/matrix-foreign-member'+suffix
    missing_path='/api/gym/team/matrix-absent-member'+suffix
    headers={}
    grant_hash=None
    if mode=='own-grant-to-foreign':
        issued=client.issue(method,own_path,body)
        assert issued.status_code==200
        headers['X-MFA-Grant']=issued.json()['grant']
        grant_hash=opaque_digest('action',issued.json()['grant'])
    elif mode=='denied-issue-then-business':
        issued=client.issue(method,foreign_path,body)
        assert issued.status_code==403 and 'grant' not in issued.json()
    response=client.raw.request(method,foreign_path,json=body,headers=headers)
    nonexistent=client.raw.request(method,missing_path,json=body,headers=headers)
    assert response.status_code==nonexistent.status_code==403
    assert response.json()==nonexistent.json()
    assert response.json()['detail']['code']=='mfa_action_forbidden'
    for value in ('matrix-private@example.invalid','Foreign private name','matrix-other-owner'):
        assert value not in response.text
    with factory() as db:
        foreign=db.get(Usuario,'matrix-foreign-member')
        assert foreign.team_gym_id=='matrix-other-owner' and foreign.role==UserRole.VIEWER
        assert foreign.activo is False and foreign.invitation_token=='y'*64
        assert foreign.session_version==0
        own=db.get(Usuario,'matrix-own-member')
        assert own.team_gym_id==principal['id'] and own.role==UserRole.VIEWER
        assert own.activo is False and own.invitation_token=='x'*64 and own.session_version==0
        if grant_hash is not None:
            assert db.get(MfaAuthorization,grant_hash).consumed_at is None
        assert db.scalars(select(Usuario).where(Usuario.team_gym_id=='matrix-other-owner')).all()==[foreign]
    assert captured==[]


def test_helper_adoption_does_not_change_the_global_primary_only_fixture(web_auth_client):
    response=web_auth_client.post('/api/billing/portal',json={'return_url':'/dashboard'})
    assert response.status_code==403
    assert response.json()['detail']['code']=='mfa_enrollment_required'

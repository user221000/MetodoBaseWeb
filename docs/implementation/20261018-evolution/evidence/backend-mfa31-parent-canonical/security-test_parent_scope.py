"""Persisted parent canonicality must survive after factor enrolment, before grants."""
import uuid
from datetime import datetime,timezone
import pytest
from sqlalchemy.orm import Session
from conftest import database_schema,isolated_database,test_gym_user
from tests.test_mfa31_http import mfa_client,enroll,authenticate

@pytest.mark.parametrize('mutation',['pending-invitation','parent-team','soft-deleted'])
def test_admin_parent_noncanonical_never_issues_new_professional_grant(mfa_client,mutation):
    from web.database.engine import get_engine
    from web.database.models import Usuario,UserRole
    from web.auth import crear_access_token,identity_from_user
    from web.services.client_link_context import canonical_gym
    client,owner,clock=mfa_client
    uid=str(uuid.uuid4());other=str(uuid.uuid4())
    with Session(get_engine()) as db:
        parent=db.get(Usuario,owner['id'])
        admin=Usuario(id=uid,email=uid+'@example.invalid',nombre='Synthetic admin',password_hash=parent.password_hash,tipo='usuario',role=UserRole.ADMIN,team_gym_id=parent.id,activo=True,session_version=0)
        peer=Usuario(id=other,email=other+'@example.invalid',nombre='Synthetic owner',password_hash=parent.password_hash,tipo='gym',role=UserRole.OWNER,activo=True,session_version=0)
        db.add_all([admin,peer]);db.commit();token=crear_access_token(identity_from_user(admin,db));actor={'id':uid,'email':admin.email}
        assert canonical_gym(parent)
    client.headers['Authorization']='Bearer '+token
    _,kit=enroll(client,clock);authenticate(client,actor,clock,recovery=kit['recovery_codes'][0])
    action={'method':'POST','path':'/api/gym/team/invite','body':{'email':'synthetic-new@example.invalid','nombre':'Synthetic invite','role':'viewer'}}
    allowed=client.post('/api/auth/mfa/step-up',json=action);assert allowed.status_code==200
    with Session(get_engine()) as db:
        parent=db.get(Usuario,owner['id'])
        if mutation=='pending-invitation':parent.invitation_token='A'*64
        elif mutation=='parent-team':parent.team_gym_id=other
        else:parent.deleted_at=datetime.now(timezone.utc)
        db.commit();assert not canonical_gym(parent)
    denied=client.post('/api/auth/mfa/step-up',json=action)
    assert denied.status_code in {401,403},'A pending/ambiguous source OWNER cannot authorize an admin grant'
    assert 'grant'not in denied.json()

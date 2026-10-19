"""Restricted application-role tests for33 trigger-only integrity, not RPCs."""
from datetime import datetime,timedelta,timezone
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.integration_google33_postgres import google_db
from web.database.schema_control import verify_runtime_schema


def test_trigger_only_functions_are_invoker_owned_and_not_directly_callable(google_db):
    admin,app=google_db
    from web.database.google_identity_policy import signature
    with admin.connect() as db:
        value=signature(db)
        assert len(value['functions'])==2 and len(value['triggers'])==2
        assert all(row[2]=='trigger' and row[3] is False and row[-1] is True for row in value['functions'])
        assert all(row[4]==['search_path=pg_catalog, public'] for row in value['functions'])
        assert value['control_plane']==[['auth_external_identities',False,False],['google_link_intents',False,False]]
    for name in ('r33_identity_immutable','r33_intent_immutable'):
        with app.connect() as db,pytest.raises(DBAPIError) as caught:
            db.execute(text('SELECT '+name+'()'))
        assert caught.value.orig.pgcode=='0A000'
        with app.connect() as db,pytest.raises(DBAPIError) as caught:
            db.execute(text('ALTER FUNCTION '+name+'() OWNER TO CURRENT_USER'))
        assert caught.value.orig.pgcode=='42501'
    verify_runtime_schema(admin)


def test_app_cannot_reassign_binding_identity_or_rewrite_proof(google_db):
    admin,app=google_db
    actor,other,binding=str(uuid.uuid4()),str(uuid.uuid4()),str(uuid.uuid4())
    subject=str(uuid.uuid4().int);now=datetime.now(timezone.utc).replace(tzinfo=None)
    token=uuid.uuid4().hex*2
    with admin.begin() as db:
        for who in (actor,other):
            db.execute(text("INSERT INTO usuarios(id,email,password_hash,nombre,apellido,tipo,role,activo,session_version,fecha_registro) VALUES (:who,:email,'synthetic','Synthetic','','usuario','VIEWER',true,0,:now)"),{'who':who,'email':who+'@example.invalid','now':now})
        db.execute(text("INSERT INTO auth_external_identities(id,user_id,issuer,subject,created_at,version) VALUES (:id,:actor,'https://accounts.google.com',:subject,:now,1)"),{'id':binding,'actor':actor,'subject':subject,'now':now})
        db.execute(text("INSERT INTO google_link_intents(token_hash,user_id,issuer,subject,purpose,access_hash,session_version,generation,created_at,expires_at) VALUES (:token,:actor,'https://accounts.google.com',:subject,'google_link',:access,0,0,:now,:expiry)"),{'token':token,'actor':actor,'subject':subject,'access':'a'*64,'now':now,'expiry':now+timedelta(minutes=5)})
    for sql,params in [
        ("UPDATE auth_external_identities SET user_id=:other WHERE id=:id",{'other':other,'id':binding}),
        ("UPDATE auth_external_identities SET issuer='https://other.example.invalid',version=2,revoked_at=:now WHERE id=:id",{'now':now,'id':binding}),
        ("UPDATE auth_external_identities SET subject='another',version=2,revoked_at=:now WHERE id=:id",{'now':now,'id':binding}),
        ("UPDATE auth_external_identities SET id=:other WHERE id=:id",{'other':str(uuid.uuid4()),'id':binding}),
        ("DELETE FROM auth_external_identities WHERE id=:id",{'id':binding}),
        ("UPDATE google_link_intents SET user_id=:other,consumed_at=:now WHERE token_hash=:token",{'other':other,'now':now,'token':token}),
        ("DELETE FROM google_link_intents WHERE token_hash=:token",{'token':token}),
    ]:
        with app.connect() as db,pytest.raises(DBAPIError) as caught:db.execute(text(sql),params)
        assert caught.value.orig.pgcode=='42501'
    with app.begin() as db:
        assert db.execute(text('UPDATE auth_external_identities SET revoked_at=:now,version=2 WHERE id=:id'),{'now':now,'id':binding}).rowcount==1
        assert db.execute(text('UPDATE google_link_intents SET consumed_at=:now WHERE token_hash=:token'),{'now':now,'token':token}).rowcount==1
    with app.connect() as db,pytest.raises(DBAPIError) as caught:
        db.execute(text('UPDATE google_link_intents SET consumed_at=:now WHERE token_hash=:token'),{'now':now,'token':token})
    assert caught.value.orig.pgcode=='42501'
    verify_runtime_schema(admin)


def test_runtime_attests_trigger_search_path_and_recovers_after_exact_restore(google_db):
    admin,_app=google_db
    try:
        with admin.begin() as db:db.exec_driver_sql('ALTER FUNCTION r33_identity_immutable() SET search_path = public, pg_catalog')
        with pytest.raises(RuntimeError,match='Google authentication binding'):verify_runtime_schema(admin)
    finally:
        with admin.begin() as db:db.exec_driver_sql('ALTER FUNCTION r33_identity_immutable() SET search_path = pg_catalog, public')
    verify_runtime_schema(admin)

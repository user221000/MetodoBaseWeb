"""Own UUID33, real factories/password/factor/JWKS, restricted pool1 and races."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import os
import uuid

import pytest
from sqlalchemy import create_engine,event,select,text
from sqlalchemy.orm import Session,sessionmaker

from tests.google33_fixtures import owned_database,REVISION
from tests.integration_schema_migrations import run_migration
from tests.integration_provider_subjects import application_engine
from tests.test_google33_http import (google_http,start,PASSWORD,
    test_real_binding_changes_session_not_contacts_or_personal_space,
    test_active_mfa_cannot_be_removed_by_google_or_link,
    test_commit_uncertainty_never_returns_proof_or_session,
    test_explicit_unlink_retains_owner_history_and_only_same_owner_can_relink)
from tests.test_google33_headers import test_new_google_login_discards_only_its_resolution_session_before_any_pair


@pytest.fixture(scope="module")
def google_db(tmp_path_factory):
    if not os.environ.get("METODOBASE_TEST_MIGRATOR_URL"):
        pytest.skip("Explicit owned synthetic PostgreSQL required")
    with owned_database("postgresql",tmp_path_factory.mktemp("google33-pg")) as (url,admin):
        run_migration(url,"db_bootstrap.py","--revision",REVISION)
        application=application_engine(url,admin)
        try:
            with application.connect() as db:
                assert tuple(db.execute(text("SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole,pg_has_role(current_user,(SELECT relowner FROM pg_class WHERE oid='usuarios'::regclass),'MEMBER') FROM pg_roles WHERE rolname=current_user")).one())==(False,False,False,False,False)
                assert db.scalar(text("SELECT count(*) FROM pg_class WHERE relnamespace=current_schema()::regnamespace AND relkind='r' AND relrowsecurity AND relforcerowsecurity"))==26
            yield admin,application
        finally:application.dispose()


def blank_pool(engine):
    with engine.connect() as db:
        assert tuple(db.execute(text("SELECT current_setting('app.current_tenant',true),current_setting('app.mfa_actor',true),current_setting('app.client_invitation_digest',true)")).one())==("","","")


def test_provider_await_has_no_transaction_or_account_lock_and_pool1_is_clean(google_http):
    c=google_http;provider=c["credential"].__self__;observed=[]
    def probe():
        assert c["engine"].pool.checkedout()==0
        with c["engine"].connect() as db:
            assert db.scalar(text("SELECT id FROM usuarios WHERE id=:actor FOR UPDATE NOWAIT"),{"actor":c["user"]})==c["user"]
            assert db.scalar(text("SELECT current_setting('app.mfa_actor',true)"))==""
        observed.append(True)
    provider.on_request=probe
    result=start(c);assert result.status_code==200 and observed==[True]
    blank_pool(c["engine"])


def test_confirm_respects_real_account_lock_without_consuming_or_publishing(google_http):
    from web.database.models import AuthExternalIdentity,GoogleLinkIntent,Usuario
    c=google_http;issued=start(c);assert issued.status_code==200
    with c["admin"].connect() as blocker:
        blocker.execute(text("SELECT id FROM usuarios WHERE id=:actor FOR UPDATE"),{"actor":c["user"]})
        failed=c["client"].post("/api/auth/google/link/confirm",headers=c["headers"],json={"intent":issued.json()["intent"],"confirm":True})
        assert failed.status_code==409 and failed.json()["detail"]["code"]=="mfa_busy"
    with Session(c["admin"]) as db:
        assert db.scalar(select(AuthExternalIdentity.id).where(AuthExternalIdentity.user_id==c["user"])) is None
        assert db.scalar(select(GoogleLinkIntent.consumed_at).where(GoogleLinkIntent.user_id==c["user"])) is None
        assert db.get(Usuario,c["user"]).session_version==0
    blank_pool(c["engine"])


def test_two_accounts_cannot_publish_the_same_verified_subject(google_http,monkeypatch):
    from web.database import engine as database
    from web.database.models import AuthExternalIdentity,GoogleLinkIntent,Usuario
    from web.database.tenant_context import configure_tenant_engine
    c=google_http;client=c["client"]
    first=start(c);assert first.status_code==200
    email=uuid.uuid4().hex+"@example.invalid"
    registered=client.post("/api/auth/registro",json={"email":email,"password":PASSWORD,"nombre":"Second actor"});assert registered.status_code==200
    password=client.post("/api/auth/login",json={"email":email,"password":PASSWORD});assert password.status_code==200
    other_headers={"Authorization":"Bearer "+password.json()["token"]}
    other=client.get("/api/auth/me",headers=other_headers);assert other.status_code==200
    second=client.post("/api/auth/google/link/start",headers=other_headers,json={"password":PASSWORD,"google_credential":c["credential"]()})
    assert second.status_code==200
    parallel=configure_tenant_engine(create_engine(c["engine"].url,pool_size=4,max_overflow=0,pool_timeout=5))
    collision=Barrier(2)
    arrivals=[]
    @event.listens_for(parallel,"before_cursor_execute")
    def both_insert(connection,cursor,statement,parameters,context,many):
        if statement.startswith("INSERT INTO auth_external_identities"):
            from threading import get_ident
            from time import monotonic
            arrivals.append({"thread":get_ident(),"time":monotonic()})
            collision.wait(timeout=10)
    try:
        with monkeypatch.context() as patch:
            patch.setattr(database,"_engine",parallel)
            patch.setattr(database,"_SessionLocal",sessionmaker(bind=parallel,expire_on_commit=True,autoflush=False))
            from fastapi.testclient import TestClient
            import importlib
            # Independent ASGI event loops are the functional equivalent of
            # distinct workers. A blocking SQL barrier cannot share one portal.
            application=importlib.import_module(c["factory"]).create_app()
            with TestClient(application,raise_server_exceptions=False,client=("192.4.1.1",50001)) as independent:
                def confirm(pair):
                    http,headers,intent=pair
                    return http.post("/api/auth/google/link/confirm",headers=headers,json={"intent":intent,"confirm":True}).status_code
                with ThreadPoolExecutor(max_workers=2) as pool:
                    statuses=list(pool.map(confirm,[(client,c["headers"],first.json()["intent"]),(independent,other_headers,second.json()["intent"])]))
        assert sorted(statuses)==[200,409], str(arrivals)
        assert len({entry["thread"] for entry in arrivals})==2
    finally:parallel.dispose()
    with Session(c["admin"]) as db:
        bindings=db.scalars(select(AuthExternalIdentity).where(AuthExternalIdentity.subject==c["google"]["sub"])).all()
        assert len(bindings)==1 and bindings[0].user_id in {c["user"],other.json()["id"]}
        versions=[db.get(Usuario,actor).session_version for actor in (c["user"],other.json()["id"])]
        assert sorted(versions)==[0,1]
        intents=db.scalars(select(GoogleLinkIntent).where(GoogleLinkIntent.user_id.in_([c["user"],other.json()["id"]]))).all()
        assert len(intents)==2 and sum(row.consumed_at is not None for row in intents)==1
    blank_pool(c["engine"])


def test_exact_expiry_is_not_authorized_and_metadata_stays_inert(google_http):
    from web.database.models import AuthExternalIdentity,GoogleLinkIntent
    c=google_http;issued=start(c);assert issued.status_code==200
    from datetime import datetime
    c["clock"][0]=datetime.fromisoformat(issued.json()["expires_at"].replace("Z","+00:00"))
    failed=c["client"].post("/api/auth/google/link/confirm",headers=c["headers"],json={"intent":issued.json()["intent"],"confirm":True})
    assert failed.status_code==409
    with Session(c["admin"]) as db:
        assert db.scalar(select(AuthExternalIdentity.id).where(AuthExternalIdentity.user_id==c["user"])) is None
        assert db.scalar(select(GoogleLinkIntent.consumed_at).where(GoogleLinkIntent.user_id==c["user"])) is None
    blank_pool(c["engine"])


@pytest.mark.parametrize('different_email',[False,True])
def test_new_google_signup_subject_collision_rolls_back_entire_losing_container(google_http,monkeypatch,different_email):
    from fastapi.testclient import TestClient
    from web.database import engine as database
    from web.database.models import AuthExternalIdentity,Usuario
    from web.database.tenant_context import configure_tenant_engine
    import importlib
    from threading import get_ident
    c=google_http;c['google']['sub']=str(uuid.uuid4().int)
    c['google']['email']=uuid.uuid4().hex+'@thirdparty.example.invalid'
    tokens=[c['credential'](),c['credential'](claims={**c['google'],**({'email':uuid.uuid4().hex+'@thirdparty.example.invalid'} if different_email else {})})]
    with Session(c['admin']) as db:before=set(db.scalars(select(Usuario.id)))
    parallel=configure_tenant_engine(create_engine(c['engine'].url,pool_size=4,max_overflow=0,pool_timeout=5))
    barrier=Barrier(2);arrivals=[]
    @event.listens_for(parallel,'before_cursor_execute')
    def both_users(connection,cursor,statement,parameters,context,many):
        # Meet before the UNIQUE email insert, not after one transaction has
        # already won that index lock. Each worker really starts a new account.
        if statement.startswith('INSERT INTO usuarios'):
            arrivals.append(get_ident());barrier.wait(timeout=10)
    try:
        with monkeypatch.context() as scope:
            scope.setattr(database,'_engine',parallel)
            scope.setattr(database,'_SessionLocal',sessionmaker(bind=parallel,expire_on_commit=True,autoflush=False))
            with TestClient(importlib.import_module(c['factory']).create_app(),raise_server_exceptions=False,
                    client=('192.4.33.1',50002)) as other:
                def signup(pair):return pair[0].post('/api/auth/google',json={'credential':pair[1]})
                with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(signup,[(c['client'],tokens[0]),(other,tokens[1])]))
        assert sorted(response.status_code for response in results)==[200,409]
        assert len(arrivals)==2 and len(set(arrivals))==2
        loser=next(response for response in results if response.status_code==409)
        assert 'token' not in loser.json() and 'refresh_token' not in loser.json()
    finally:parallel.dispose()
    with Session(c['admin']) as db:
        added=set(db.scalars(select(Usuario.id)))-before
        assert len(added)==1
        bindings=db.scalars(select(AuthExternalIdentity).where(AuthExternalIdentity.subject==c['google']['sub'])).all()
        assert len(bindings)==1 and bindings[0].user_id in added
    blank_pool(c['engine'])

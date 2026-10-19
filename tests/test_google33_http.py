"""Current33 real HTTP and migrations; provider transport only is synthetic."""
import base64
from datetime import datetime,timedelta,timezone
import importlib
import uuid

import httpx
import pytest
from sqlalchemy import event,select
from sqlalchemy.orm import Session,sessionmaker

from tests.google33_fixtures import owned_database,REVISION
from tests.integration_schema_migrations import run_migration

PASSWORD="Synthetic Google binding password 42!"
CLIENT_ID="000000000000-independent-review.apps.googleusercontent.com"
SUBJECT="104000000000000000001"

@pytest.fixture(scope="module")
def google_db(tmp_path_factory):
    with owned_database("sqlite",tmp_path_factory.mktemp("google-http33")) as (url,engine):
        run_migration(url,"db_bootstrap.py","--revision",REVISION)
        @event.listens_for(engine,"connect")
        def foreign_keys(connection,record):connection.execute("PRAGMA foreign_keys=ON")
        engine.dispose()
        yield engine

@pytest.fixture(params=["web.main_web","api.app"])
def google_http(google_db,request,monkeypatch):
    from web.database import engine as database
    from web.services import mfa_service
    from web.settings import get_settings
    settings=get_settings()
    monkeypatch.setattr(settings,"GOOGLE_CLIENT_ID",CLIENT_ID)
    monkeypatch.setattr(settings,"MFA_ENCRYPTION_KEY",base64.urlsafe_b64encode(b"G"*32).decode())
    admin,application=google_db if isinstance(google_db,tuple) else (google_db,google_db)
    monkeypatch.setattr(database,"_engine",application)
    monkeypatch.setattr(database,"_SessionLocal",sessionmaker(bind=application,expire_on_commit=True,autoflush=False))
    clock=[datetime.now(timezone.utc)]
    original=mfa_service.instant
    monkeypatch.setattr(mfa_service,"instant",lambda now=None:original(clock[0] if now is None else now))
    calls=[]
    info={"aud":CLIENT_ID,"iss":"https://accounts.google.com","sub":SUBJECT,
        "email":uuid.uuid4().hex+"@thirdparty.example.invalid","email_verified":"true",
        "exp":int((clock[0]+timedelta(hours=1)).timestamp()),"auth_time":int(clock[0].timestamp())}
    from tests.google33_signed_provider import SignedProvider
    provider=SignedProvider(monkeypatch,info)
    calls=provider.calls
    number=int(uuid.uuid4().hex[:4],16)
    with importlib.import_module("fastapi.testclient").TestClient(importlib.import_module(request.param).create_app(),
            raise_server_exceptions=False,client=(f"192.3.{number//256}.{number%256}",50000)) as client:
        email=uuid.uuid4().hex+"@example.invalid"
        made=client.post("/api/auth/registro",json={"email":email,"password":PASSWORD,"nombre":"Synthetic","tipo":"usuario"})
        assert made.status_code==200,"Real33 registration failed"
        response=client.post("/api/auth/login",json={"email":email,"password":PASSWORD})
        assert response.status_code==200,"Real33 password login failed"
        headers={"Authorization":"Bearer "+response.json()["token"]}
        me=client.get("/api/auth/me",headers=headers);assert me.status_code==200
        yield {"client":client,"headers":headers,"user":me.json()["id"],"email":email,"clock":clock,
            "google":info,"calls":calls,"engine":application,"admin":admin,"factory":request.param,
            "refresh":response.json()["refresh_token"],"credential":provider.credential}


def start(case,**changes):
    case["google"]["sub"]=str(int(SUBJECT)+int(uuid.uuid4().hex[:6],16))
    return case["client"].post("/api/auth/google/link/start",headers=case["headers"],
        json={"password":PASSWORD,"google_credential":case["credential"](),**changes})


def test_google_success_preserves_prior_audit_without_provider_or_session_secrets(google_http):
    import json
    from web.database.models import AuthAuditLog
    c=google_http;issued=start(c);assert issued.status_code==200
    confirmed=c['client'].post('/api/auth/google/link/confirm',headers=c['headers'],json={'intent':issued.json()['intent'],'confirm':True})
    assert confirmed.status_code==200
    credential=c['credential']()
    response=c['client'].post('/api/auth/google',json={'credential':credential})
    assert response.status_code==200
    with Session(c['admin']) as db:
        events=db.scalars(select(AuthAuditLog).where(AuthAuditLog.user_id==c['user'],AuthAuditLog.event_type=='login_success')).all()
        google=[row for row in events if row.event_metadata.get('source')=='google']
        assert len(google)==1 and google[0].event_metadata=={'tipo':'usuario','source':'google'}
        serialized=json.dumps([row.event_metadata for row in events])
        assert all(value not in serialized for value in (credential,response.json()['token'],response.json()['refresh_token'],issued.json()['intent']))


def test_real_binding_changes_session_not_contacts_or_personal_space(google_http):
    from web.database.models import Usuario,Cliente,AuthExternalIdentity,GoogleLinkIntent,RefreshToken
    c=google_http;client=c["client"]
    c["google"]["email"]=c["email"]
    unbound=client.post("/api/auth/google",json={"credential":c["credential"]()})
    assert unbound.status_code==409 and unbound.json()["detail"]["code"]=="google_link_required"
    issued=start(c);assert issued.status_code==200,issued.text
    intent=issued.json()["intent"];assert issued.json()["confirmation_required"] is True
    with Session(c["admin"]) as db:
        assert db.scalar(select(AuthExternalIdentity).where(AuthExternalIdentity.user_id==c["user"])) is None
        old=db.get(Usuario,c["user"]);before=(old.email,old.password_hash,old.nombre,old.tipo,old.role,old.team_gym_id)
    done=client.post("/api/auth/google/link/confirm",headers=c["headers"],json={"intent":intent,"confirm":True})
    assert done.status_code==200 and done.json()=={"success":True,"provider":"google","linked":True,"reauthenticate":True}
    assert "token" not in done.json() and client.get("/api/auth/me",headers=c["headers"]).status_code==401
    with Session(c["admin"]) as db:
        row=db.get(Usuario,c["user"])
        assert (row.email,row.password_hash,row.nombre,row.tipo,row.role,row.team_gym_id)==before
        assert row.session_version==1 and db.scalar(select(Cliente.id).where(Cliente.gym_id==row.id)) is None
        assert db.scalar(select(AuthExternalIdentity.user_id).where(AuthExternalIdentity.subject==c["google"]["sub"]))==row.id
        assert db.scalar(select(GoogleLinkIntent.consumed_at).where(GoogleLinkIntent.user_id==row.id)) is not None
        assert all(db.scalars(select(RefreshToken.revoked).where(RefreshToken.user_id==row.id)))
    c["google"]["email"]="changed-contact@thirdparty.example.invalid"
    login=client.post("/api/auth/google",json={"credential":c["credential"](),"tipo":"gym"})
    assert login.status_code==200 and login.json()["email"]==c["email"] and login.json()["tipo"]=="usuario"
    client.headers["Authorization"]="Bearer "+login.json()["token"]
    fresh={"Authorization":client.headers["Authorization"]}
    replay=client.post("/api/auth/google/link/confirm",headers=fresh,json={"intent":intent,"confirm":True})
    assert replay.status_code==409
    reauth=client.post("/api/auth/mfa/reauth",headers=fresh,json={"google_credential":c["credential"]()})
    assert reauth.status_code==200


def test_wrong_password_and_exact_access_binding(google_http):
    c=google_http
    assert start(c,password="not-the-password").status_code==401
    issued=start(c);assert issued.status_code==200
    second=c["client"].post("/api/auth/refresh",json={"refresh_token":c["refresh"]})
    assert second.status_code==200 and second.json()["token"]!=c["headers"]["Authorization"][7:]
    changed=c["client"].post("/api/auth/google/link/confirm",headers={"Authorization":"Bearer "+second.json()["token"]},
        json={"intent":issued.json()["intent"],"confirm":True})
    assert changed.status_code==409


def test_commit_uncertainty_never_returns_proof_or_session(google_http,monkeypatch):
    from web.database import engine as database
    from web.database.models import AuthExternalIdentity,GoogleLinkIntent
    c=google_http;issued=start(c);assert issued.status_code==200
    real=Session.commit;once=True
    class LostAck(Session):
        def commit(self):
            nonlocal once
            # Admission is first; inject only the transaction publishing binding.
            publishing=self.info.get("observed_binding_insert",False) or any(isinstance(x,AuthExternalIdentity) for x in self.new)
            real(self)
            if publishing and once:once=False;raise RuntimeError("PRIVATE_LINK_SQL_SENTINEL")
    @event.listens_for(LostAck,"before_flush")
    def observed_binding(db,context,instances):
        if any(isinstance(x,AuthExternalIdentity) for x in db.new):db.info["observed_binding_insert"]=True
    monkeypatch.setattr(database,"_SessionLocal",sessionmaker(bind=c["engine"],class_=LostAck,expire_on_commit=True))
    result=c["client"].post("/api/auth/google/link/confirm",headers=c["headers"],json={"intent":issued.json()["intent"],"confirm":True})
    assert result.status_code==503 and result.json()["detail"]["code"]=="google_link_unconfirmed"
    assert "token" not in result.json() and "PRIVATE_LINK_SQL_SENTINEL" not in result.text
    with Session(c["admin"]) as db:
        assert db.scalar(select(AuthExternalIdentity.user_id).where(AuthExternalIdentity.user_id==c["user"]))==c["user"]
        assert db.scalar(select(GoogleLinkIntent.consumed_at).where(GoogleLinkIntent.user_id==c["user"])) is not None
    assert c["client"].get("/api/auth/me",headers=c["headers"]).status_code==401


def test_active_mfa_cannot_be_removed_by_google_or_link(google_http):
    from web.services.mfa_crypto import totp
    c=google_http;client=c["client"]
    proof=client.post("/api/auth/mfa/reauth",headers=c["headers"],json={"password":PASSWORD})
    assert proof.status_code==200
    enroll=client.post("/api/auth/mfa/enroll",headers=c["headers"],json={"reauthentication_token":proof.json()["reauthentication_token"]})
    assert enroll.status_code==200
    seed=base64.b32decode(enroll.json()["secret"])
    done=client.post("/api/auth/mfa/enroll/confirm",headers=c["headers"],json={"enrollment_id":enroll.json()["enrollment_id"],"code":totp(seed,int(c["clock"][0].timestamp())//30)})
    assert done.status_code==200
    primary=client.post("/api/auth/login",json={"email":c["email"],"password":PASSWORD});assert primary.status_code==202
    verified=client.post("/api/auth/mfa/login/verify",json={"challenge":primary.json()["challenge"],"recovery_code":done.json()["recovery_codes"][0]})
    assert verified.status_code==200
    c["headers"]={"Authorization":"Bearer "+verified.json()["token"]}
    missing=start(c);assert missing.status_code==422
    valid=start(c,recovery_code=done.json()["recovery_codes"][1]);assert valid.status_code==200
    confirmed=client.post("/api/auth/google/link/confirm",headers=c["headers"],json={"intent":valid.json()["intent"],"confirm":True})
    assert confirmed.status_code==200
    google=client.post("/api/auth/google",json={"credential":c["credential"]()})
    assert google.status_code==202 and "token" not in google.json() and "refresh_token" not in google.json()


def test_google_new_container_is_not_an_email_merge_and_cannot_unlink_without_local_primary(google_http):
    from web.database.models import AuthExternalIdentity,Usuario,Cliente,AuthAuditLog
    c=google_http;client=c["client"]
    c["google"]["sub"]=str(int(SUBJECT)+int(uuid.uuid4().hex[:8],16))
    c["google"]["email"]=uuid.uuid4().hex+"@thirdparty.example.invalid"
    registered=client.post("/api/auth/google",json={"credential":c["credential"]()})
    assert registered.status_code==200
    headers={"Authorization":"Bearer "+registered.json()["token"]}
    me=client.get("/api/auth/me",headers=headers);assert me.status_code==200
    owner=me.json()["id"];assert owner!=c["user"] and me.json()["role"]=="viewer" and me.json().get("team_gym_id") is None
    status=client.get("/api/auth/google/link/status",headers=headers);assert status.status_code==200
    binding=status.json()["items"][0]
    denied=client.post("/api/auth/google/link/unlink",headers=headers,json={"identity_id":binding["id"],"expected_version":1,"password":PASSWORD})
    assert denied.status_code==401
    with Session(c["admin"]) as db:
        assert db.scalar(select(AuthExternalIdentity.user_id).where(AuthExternalIdentity.subject==c["google"]["sub"]))==owner
        assert db.scalar(select(Cliente.id).where(Cliente.gym_id==owner)) is None
        assert db.get(Usuario,c["user"]).email==c["email"]
        assert db.scalar(select(AuthAuditLog.id).where(AuthAuditLog.user_id==owner,AuthAuditLog.event_type=="google_identity_registered")) is not None


def test_explicit_unlink_retains_owner_history_and_only_same_owner_can_relink(google_http):
    from web.database.models import AuthExternalIdentity,AuthAuditLog
    c=google_http;client=c["client"]
    issued=start(c);assert issued.status_code==200
    done=client.post("/api/auth/google/link/confirm",headers=c["headers"],json={"intent":issued.json()["intent"],"confirm":True});assert done.status_code==200
    fresh=client.post("/api/auth/login",json={"email":c["email"],"password":PASSWORD});assert fresh.status_code==200
    c["headers"]={"Authorization":"Bearer "+fresh.json()["token"]}
    state=client.get("/api/auth/google/link/status",headers=c["headers"]);assert state.status_code==200
    item=state.json()["items"][0]
    assert set(item)=={"id","version","active","created_at","revoked_at"} and item["active"] is True
    stale=client.post("/api/auth/google/link/unlink",headers=c["headers"],json={"identity_id":item["id"],"expected_version":2,"password":PASSWORD});assert stale.status_code==409
    removed=client.post("/api/auth/google/link/unlink",headers=c["headers"],json={"identity_id":item["id"],"expected_version":1,"password":PASSWORD})
    assert removed.status_code==200 and removed.json()["version"]==2 and removed.json()["reauthenticate"] is True
    assert client.get("/api/auth/me",headers=c["headers"]).status_code==401
    revoked=client.post("/api/auth/google",json={"credential":c["credential"]()});assert revoked.status_code==409 and "token" not in revoked.json()
    fresh=client.post("/api/auth/login",json={"email":c["email"],"password":PASSWORD});assert fresh.status_code==200
    c["headers"]={"Authorization":"Bearer "+fresh.json()["token"]}
    subject=c["google"]["sub"]
    issued=client.post("/api/auth/google/link/start",headers=c["headers"],json={"password":PASSWORD,"google_credential":c["credential"]()});assert issued.status_code==200
    relink=client.post("/api/auth/google/link/confirm",headers=c["headers"],json={"intent":issued.json()["intent"],"confirm":True});assert relink.status_code==200
    with Session(c["admin"]) as db:
        binding=db.scalar(select(AuthExternalIdentity).where(AuthExternalIdentity.subject==subject))
        assert binding.id==item["id"] and binding.user_id==c["user"] and binding.version==3 and binding.revoked_at is None
        assert len(db.scalars(select(AuthAuditLog.id).where(AuthAuditLog.user_id==c["user"],AuthAuditLog.event_type=="google_identity_unlinked")).all())==1


@pytest.mark.parametrize("kind",["signature","issuer","audience","expiry","subject","algorithm","kid"])
def test_real_library_rejects_bad_provider_assertions_without_local_side_effects(google_http,kind):
    from cryptography.hazmat.primitives.asymmetric import rsa
    import jwt
    from web.database.models import AuthExternalIdentity,Usuario
    c=google_http;claims=dict(c["google"]);kwargs={}
    if kind=="signature":kwargs["key"]=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    if kind=="issuer":claims["iss"]="https://not-google.example.invalid"
    if kind=="audience":claims["aud"]="other-client"
    if kind=="expiry":claims["exp"]=int(datetime.now(timezone.utc).timestamp())-1
    if kind=="subject":claims["sub"]=""
    if kind=="kid":kwargs["kid"]="unrecognized-key"
    if kind=="algorithm":
        credential=jwt.encode(claims,b"synthetic-wrong-algorithm-key",algorithm="HS256",headers={"kid":"synthetic33"})
    else:credential=c["credential"](claims=claims,**kwargs)
    response=c["client"].post("/api/auth/google",json={"credential":credential})
    assert response.status_code==401 and all(x not in response.json() for x in ("token","refresh_token","challenge"))
    assert response.headers["Cache-Control"]=="no-store" and response.headers["Referrer-Policy"]=="no-referrer"
    with Session(c["admin"]) as db:
        assert db.scalar(select(AuthExternalIdentity.id).where(AuthExternalIdentity.user_id==c["user"])) is None
        assert db.get(Usuario,c["user"]).session_version==0


def test_failed_proofs_have_durable_budget_without_factor_or_binding_changes(google_http):
    from web.database.models import MfaCredential,GoogleLinkIntent,AuthExternalIdentity
    c=google_http
    for _ in range(10):assert start(c,password="not-the-independent-primary").status_code==401
    limited=start(c);assert limited.status_code==429
    with Session(c["admin"]) as db:
        row=db.get(MfaCredential,c["user"])
        assert row.attempts["google_link:start"]["count"]==10
        assert db.scalar(select(GoogleLinkIntent.token_hash).where(GoogleLinkIntent.user_id==c["user"])) is None
        assert db.scalar(select(AuthExternalIdentity.id).where(AuthExternalIdentity.user_id==c["user"])) is None


def test_intent_expiry_and_factor_generation_are_not_recovered_from_a_new_access(google_http):
    from web.database.models import MfaCredential,GoogleLinkIntent,AuthExternalIdentity
    c=google_http;issued=start(c);assert issued.status_code==200
    with Session(c["admin"]) as db:
        row=db.get(MfaCredential,c["user"]);row.generation+=1;db.commit()
    failed=c["client"].post("/api/auth/google/link/confirm",headers=c["headers"],json={"intent":issued.json()["intent"],"confirm":True})
    assert failed.status_code==409
    with Session(c["admin"]) as db:
        assert db.scalar(select(GoogleLinkIntent.consumed_at).where(GoogleLinkIntent.user_id==c["user"])) is None
        assert db.scalar(select(AuthExternalIdentity.id).where(AuthExternalIdentity.user_id==c["user"])) is None

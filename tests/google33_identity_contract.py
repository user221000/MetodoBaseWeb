"""Current33 explicit HTTP associations preserve historical role/disable criteria."""
from datetime import datetime,timezone
import uuid
from tests.ci_google33.identity_fixtures import identity_db,principal,auth_client
from tests.google33_signed_provider import SignedProvider
from tests.ci_web41 import google_mail_http_fixture as mail_http

def linked(identity_db,monkeypatch):
    from web.settings import get_settings
    factory,owner,member,password=identity_db
    user=principal(factory,member);now=int(datetime.now(timezone.utc).timestamp())
    monkeypatch.setattr(get_settings(),"GOOGLE_CLIENT_ID","synthetic-client-id")
    provider=SignedProvider(monkeypatch,{"aud":"synthetic-client-id","iss":"https://accounts.google.com",
        "sub":uuid.uuid4().hex,"email":user["email"],"email_verified":True,"iat":now,"exp":now+3600,"auth_time":now})
    client=auth_client(monkeypatch)
    login=client.post("/api/auth/login",json={"email":user["email"],"password":password});assert login.status_code==200
    headers={"Authorization":"Bearer "+login.json()["token"]}
    intent=client.post("/api/auth/google/link/start",headers=headers,json={"password":password,"google_credential":provider.credential()});assert intent.status_code==200
    confirm=client.post("/api/auth/google/link/confirm",headers=headers,json={"intent":intent.json()["intent"],"confirm":True});assert confirm.status_code==200
    return provider

def verified_primary(identity_db, monkeypatch, provider, user, *, tipo="usuario"):
    """Keep the final identity checks behind a real synthetic mailbox proof."""
    from web.settings import get_settings
    factory, _, _, _ = identity_db
    case = {"client": auth_client(monkeypatch), "admin": factory.kw["bind"],
            "google": {"email": user["email"]},
            "mail_transport": mail_http.install(monkeypatch, get_settings())}
    pending = mail_http.begin(case, credential=provider.credential(), tipo=tipo)
    return mail_http.verify(case, pending)


def test_google_uses_same_member_identity(identity_db, monkeypatch):
    from web import auth
    factory, owner_id, member_id, _ = identity_db
    user = principal(factory, member_id)
    provider=linked(identity_db,monkeypatch)
    response = verified_primary(identity_db, monkeypatch, provider, user, tipo="gym")
    assert response.status_code == 200
    assert response.json()["role"] == "nutriologo"
    assert response.json()["team_gym_id"] == owner_id
    identity = auth.verificar_token(response.json()["token"])
    assert identity["role"] == "nutriologo"
    assert identity["team_gym_id"] == owner_id

def test_disabled_google_account_is_not_recreated(identity_db, monkeypatch):
    from web.database.models import Usuario
    from web.settings import get_settings
    factory, _, member_id, _ = identity_db
    user = principal(factory, member_id)
    provider=linked(identity_db,monkeypatch)
    with factory() as db:
        db.get(Usuario, member_id).activo = False
        db.commit()
    transport = mail_http.install(monkeypatch, get_settings())
    response = auth_client(monkeypatch).post("/api/auth/google", json={"credential": provider.credential()})
    assert response.status_code == 401
    assert transport.mail == [] and transport.cache.rows == {}
    with factory() as db:
        assert db.query(Usuario).filter(Usuario.email == user["email"]).count() == 1

"""New account data boundaries, actual hashing/router and browser transport."""
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from tests.test_google_email_login import (
    counts,
    database_schema,
    isolated_database,
    otp_case,
)

__all__ = ["database_schema", "isolated_database", "otp_case"]

INVALID=[
    pytest.param({"email":"bad@@example.invalid"},id="multiple-at"),
    pytest.param({"email":"@example.invalid"},id="empty-local"),
    pytest.param({"email":"member@"},id="empty-domain"),
    pytest.param({"email":"mem ber@example.invalid"},id="email-space"),
    pytest.param({"email":"member@exam\nple.invalid"},id="email-control"),
    pytest.param({"email":"member@example..invalid"},id="empty-domain-label"),
    pytest.param({"email":"member@-example.invalid"},id="bad-domain-label"),
    pytest.param({"email":"member@exa_mple.invalid"},id="domain-underscore"),
    pytest.param({"email":"m"*256+"@example.invalid"},id="email-too-long"),
    pytest.param({"email":"m"*65+"@example.invalid"},id="local-over-64-bytes"),
    pytest.param({"email":"é"*33+"@example.invalid"},id="unicode-local-over-64-bytes"),
    pytest.param({"email":"m"*64+"@"+"a"*63+"."+"b"*63+"."+"c"*62},id="mailbox-over-254-bytes"),
    pytest.param({"nombre":""},id="empty-name"),
    pytest.param({"nombre":" \t "},id="blank-name"),
    pytest.param({"nombre":"N"*151},id="name-too-long"),
    pytest.param({"nombre":"N\x00ame"},id="name-nul"),
    pytest.param({"apellido":"A"*151},id="surname-too-long"),
]
ORIGIN="https://registration.example.invalid"
HEADERS={"Origin":ORIGIN,"X-MetodoBase-Browser":"1"}

@pytest.fixture
def registration_http(otp_case,monkeypatch):
    from web.routes.auth import router
    monkeypatch.setattr(otp_case.settings,"BASE_URL",ORIGIN)
    monkeypatch.setattr("web.services.email_service.send_welcome",lambda *a,**k:False)
    app=FastAPI()
    app.include_router(router,prefix="/api")
    with TestClient(app,base_url=ORIGIN,raise_server_exceptions=False) as client:
        yield otp_case,client

@pytest.mark.parametrize("patch",INVALID)
def test_invalid_identity_stops_before_hashing_or_opening_a_session(monkeypatch,patch):
    from web import auth
    def forbidden(*a,**k):raise AssertionError("Invalid identity reached costly or persistent work")
    monkeypatch.setattr(auth,"hash_password",forbidden)
    monkeypatch.setattr(auth,"_get_session",forbidden)
    payload={"email":"member@example.invalid","password":"cedro nube luna","nombre":"Synthetic","apellido":"",**patch}
    with pytest.raises(ValueError):auth.crear_usuario(**payload)

@pytest.mark.parametrize("kind",["usuario","gym"])
@pytest.mark.parametrize("patch",INVALID)
def test_invalid_form_data_creates_no_account_session_or_business_profile(registration_http,kind,patch):
    from web.database.models import GymProfile, PlanSuscripcion
    case,client=registration_http
    payload={"email":uuid.uuid4().hex+"@example.invalid","password":"cedro nube luna","nombre":"Synthetic","tipo":kind,**patch}
    response=client.post("/api/auth/registro",headers=HEADERS,json=payload)
    assert response.status_code==400 and response.json()["detail"]["code"]=="registration_invalid"
    assert payload["password"] not in response.text
    assert counts(case)==(0,0,0) and client.cookies.get("__Host-mb_refresh") is None
    with case.sessions() as db:
        assert db.scalar(select(func.count()).select_from(GymProfile))==0
        assert db.scalar(select(func.count()).select_from(PlanSuscripcion))==0

@pytest.mark.parametrize("kind,role",[("usuario","viewer"),("gym","owner")])
@pytest.mark.parametrize("email",["  Member+alias@Example.Invalid  ","Persona+alias@café.mx"])
def test_aliases_idns_and_trimmed_names_register_and_login_without_changing_password(registration_http,kind,role,email):
    from web import auth
    from web.database.models import GymProfile, PlanSuscripcion, Usuario
    case,client=registration_http
    password=" cedro nube luna "
    payload={"email":email,"password":password,"nombre":"  Nombre Ñ  ","apellido":"  Apellido  ","tipo":kind}
    created=client.post("/api/auth/registro",headers=HEADERS,json=payload)
    assert created.status_code==200
    result=created.json()
    identity=auth.verificar_token(result["token"])
    assert identity["tipo"]==kind and identity["role"]==role
    assert result["session_mode"]=="browser" and "refresh_token" not in result
    assert client.cookies.get("__Host-mb_refresh")
    cookie=created.headers["set-cookie"].lower()
    assert "httponly" in cookie and "secure" in cookie and "samesite=strict" in cookie
    with case.sessions() as db:
        user=db.get(Usuario,identity["id"])
        assert (user.email,user.nombre,user.apellido)==(email.strip().lower(),"Nombre Ñ","Apellido")
        assert auth.verify_password(password,user.password_hash)
        assert not auth.verify_password(password.strip(),user.password_hash)
        assert db.scalar(select(func.count()).select_from(GymProfile))==int(kind=="gym")
        assert db.scalar(select(func.count()).select_from(PlanSuscripcion))==5*int(kind=="gym")
    duplicate=client.post("/api/auth/registro",headers=HEADERS,json=payload)
    assert duplicate.status_code==400 and duplicate.json()["detail"]["code"]=="registration_invalid"
    assert counts(case)==(1,0,1)
    login=client.post("/api/auth/login",headers=HEADERS,json={"email":email,"password":password})
    assert login.status_code==200
    assert auth.verificar_token(login.json()["token"])["id"]==identity["id"]

@pytest.mark.parametrize("email",[
    "m"*64+"@example.invalid",
    "é"*32+"@example.invalid",
    "m"*64+"@"+"a"*63+"."+"b"*63+"."+"c"*61,
    "١٢٣٤+alias@café.mx",
    "member@intranet",
])
def test_transport_boundary_addresses_keep_the_stored_identity(email):
    from web.account_values import validate_registration_email
    assert validate_registration_email(email)==email.lower()

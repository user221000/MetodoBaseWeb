"""Opt-in current33 provider contracts; historical31 fixtures are unchanged."""
import uuid
import pytest
from tests.test_google33_http import google_http,PASSWORD,start

@pytest.fixture
def mfa_client(google_http):
    c=google_http;client=c["client"]
    # Preserve the historical privileged owner context through real endpoints.
    email=uuid.uuid4().hex+"@example.invalid"
    registered=client.post("/api/auth/registro",json={"email":email,"password":PASSWORD,"nombre":"Synthetic owner","tipo":"gym"})
    assert registered.status_code==200
    password=client.post("/api/auth/login",json={"email":email,"password":PASSWORD});assert password.status_code==200
    c["headers"]={"Authorization":"Bearer "+password.json()["token"]};c["email"]=email
    me=client.get("/api/auth/me",headers=c["headers"]);assert me.status_code==200
    c["user"]=me.json()["id"]
    issued=start(c);assert issued.status_code==200
    linked=client.post("/api/auth/google/link/confirm",headers=c["headers"],json={"intent":issued.json()["intent"],"confirm":True})
    assert linked.status_code==200
    password=client.post("/api/auth/login",json={"email":email,"password":PASSWORD});assert password.status_code==200
    client.headers["Authorization"]="Bearer "+password.json()["token"]
    actor={"email":email,"id":c["user"],"google_subject":c["google"]["sub"]}
    yield client,actor,c["clock"]

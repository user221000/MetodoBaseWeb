import pytest
from tests.test_google33_http import google_db,google_http,PASSWORD
from sqlalchemy.orm import Session
from tests.mfa31_contract_client import MfaContractClient
import uuid

def test_authentic_full_mfa_current33_has_no_task_context(google_http):
    c=google_http;raw=c["client"];email=uuid.uuid4().hex+"@example.invalid"
    assert raw.post("/api/auth/registro",json={"email":email,"password":PASSWORD,"nombre":"Synthetic manager","tipo":"gym"}).status_code==200
    login=raw.post("/api/auth/login",json={"email":email,"password":PASSWORD});assert login.status_code==200
    raw.headers["Authorization"]="Bearer "+login.json()["token"]
    me=raw.get("/api/auth/me");assert me.status_code==200
    client=MfaContractClient(raw,{"id":me.json()["id"]},lambda:Session(c["engine"]),PASSWORD)
    client.authenticate()
    assert raw.get("/api/auth/me").status_code==200
    response=raw.get("/api/seguimiento/contexto")
    assert response.status_code==200, "current33 context HTTP "+str(response.status_code)

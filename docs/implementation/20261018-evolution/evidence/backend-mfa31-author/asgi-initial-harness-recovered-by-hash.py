"""Bounded stream admission and final MFA protection through both factories."""
import asyncio

from fastapi import HTTPException
import pytest
from starlette.requests import Request

from tests.test_mfa31_http import mfa_client


def test_parser_stops_stream_before_json_and_before_later_chunks():
    from web.routes.mfa import parse, Reauth
    seen = []
    messages = iter([{"type":"http.request", "body":b"x"*20000, "more_body":True},
        {"type":"http.request", "body":b"x"*20000, "more_body":True},
        {"type":"http.request", "body":b"must-never-be-read", "more_body":False}])
    async def receive():
        item = next(messages)
        seen.append(item)
        return item
    request = Request({"type":"http", "method":"POST", "path":"/api/auth/mfa/reauth", "headers":[]},receive)
    with pytest.raises(HTTPException) as caught:
        asyncio.run(parse(request,Reauth))
    assert caught.value.status_code == 413 and len(seen) == 2


@pytest.mark.parametrize("content,status", [(b'{"password":"one","password":"two"}',422),
    (b'{"password":NaN}',422), (b'{"password":true}',422),
    (b'{"password":"valid-shape","actor":"foreign"}',422), (b'x'*32769,413)])
def test_invalid_body_never_reflects_private_material(mfa_client, content, status):
    client, _, _ = mfa_client
    response = client.post("/api/auth/mfa/reauth",content=content,headers={"Content-Type":"application/json"})
    assert response.status_code == status
    assert "valid-shape" not in response.text and "foreign" not in response.text
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Referrer-Policy"] == "no-referrer"


@pytest.mark.parametrize("outcome", ["limited", "redis_unavailable", "unexpected"])
def test_mfa_final_headers_and_opaque_failures_even_if_general_limit_disabled(mfa_client, monkeypatch, caplog, outcome):
    client, _, _ = mfa_client
    from web.settings import get_settings
    from web.services import mfa_service
    import web.rate_limiter_redis as limiter
    monkeypatch.setattr(get_settings(),"RATE_LIMIT_ENABLED",False)
    calls = []
    async def admission(key, maximum, window, **options):
        calls.append((maximum,window,options))
        if outcome == "redis_unavailable":
            raise HTTPException(503,"Servicio temporalmente no disponible")
        return (False,{"retry_after":17},None) if outcome == "limited" else (True,{},None)
    monkeypatch.setattr(limiter,"check_rate_limit",admission)
    if outcome == "unexpected":
        def broken(*args,**kwargs):
            raise RuntimeError("synthetic-private-secret-must-never-be-reflected")
        monkeypatch.setattr(mfa_service,"status",broken)
    response = client.get("/api/auth/mfa/status")
    assert response.status_code == (429 if outcome == "limited" else 503)
    assert calls == [(30,300,{"use_redis":False,"sensitive":True})]
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "default-src 'none'" in response.headers["Content-Security-Policy"]
    assert "synthetic-private-secret" not in response.text + caplog.text

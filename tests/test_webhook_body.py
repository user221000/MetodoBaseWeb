"""Bounded ASGI receive tests; bytes remain opaque until the provider verifier."""
import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from web.services import webhook_body


def _request(chunks, headers=(), *, disconnect=False):
    sent = []
    queue = list(chunks)

    async def receive():
        if queue:
            chunk = queue.pop(0)
            sent.append(chunk)
            return {"type": "http.request", "body": chunk, "more_body": bool(queue) or disconnect}
        if disconnect:
            return {"type": "http.disconnect"}
        raise AssertionError("Reader consumed beyond the final request chunk")

    request = Request({"type": "http", "method": "POST", "path": "/api/billing/webhook",
        "headers": list(headers)}, receive)
    return request, sent


@pytest.fixture(autouse=True)
def body_limit(monkeypatch):
    monkeypatch.setattr(webhook_body, "get_settings", lambda: SimpleNamespace(WEBHOOK_MAX_BODY_BYTES=65536))


@pytest.mark.parametrize("headers", [(), ((b"transfer-encoding", b"chunked"),), ((b"content-length", b"65536"),)])
def test_exact_limit_preserves_opaque_bytes(headers):
    raw = bytes(range(256)) * 256
    request, sent = _request([raw[:127], raw[127:32768], raw[32768:]], headers)
    assert asyncio.run(webhook_body.read_webhook_body(request)) == raw
    assert b"".join(sent) == raw


@pytest.mark.parametrize("headers", [(), ((b"transfer-encoding", b"chunked"),), ((b"content-length", b"1"),)])
def test_limit_plus_one_stops_before_verifier_or_remaining_receive(headers):
    request, sent = _request([b"x" * 65536, b"x", b"must-not-be-read"], headers)
    with pytest.raises(HTTPException) as error:
        asyncio.run(webhook_body.read_webhook_body(request))
    assert error.value.status_code == 413
    assert error.value.detail["code"] == "webhook_body_too_large"
    assert len(sent) == 2


def test_declared_oversize_is_rejected_without_reading():
    request, sent = _request([b"unread"], ((b"content-length", b"65537"),))
    with pytest.raises(HTTPException) as error:
        asyncio.run(webhook_body.read_webhook_body(request))
    assert error.value.status_code == 413
    assert sent == []


@pytest.mark.parametrize("headers", [
    ((b"content-length", b"1"), (b"content-length", b"1")),
    ((b"content-length", b"1,1"),),
    ((b"content-length", b"-1"),),
    ((b"content-length", b"+1"),),
    ((b"content-length", b"1.0"),),
    ((b"content-length", b"9" * 32),),
    ((b"content-length", b"1"), (b"transfer-encoding", b"chunked")),
])
def test_ambiguous_framing_rejected_before_receive(headers):
    request, sent = _request([b"x"], headers)
    with pytest.raises(HTTPException) as error:
        asyncio.run(webhook_body.read_webhook_body(request))
    assert error.value.status_code == 400
    assert error.value.detail["code"] == "webhook_content_length_invalid"
    assert sent == []


@pytest.mark.parametrize("declared", ["0", "1", "3"])
def test_incorrect_content_length_rejected(declared):
    request, _ = _request([b"ab"], ((b"content-length", declared.encode()),))
    with pytest.raises(HTTPException) as error:
        asyncio.run(webhook_body.read_webhook_body(request))
    assert error.value.status_code == 400


def test_disconnect_remains_retryable_and_does_not_return_partial_body():
    request, _ = _request([b"partial"], disconnect=True)
    with pytest.raises(HTTPException) as error:
        asyncio.run(webhook_body.read_webhook_body(request))
    assert error.value.status_code == 400
    assert error.value.detail["code"] == "webhook_body_incomplete"


@pytest.mark.parametrize("value,expected", [(None, 2097152), ("65536", 65536), ("8388608", 8388608)])
def test_setting_accepts_documented_default_and_bounds(monkeypatch, value, expected):
    from config.settings import Settings
    if value is None:
        monkeypatch.delenv("WEBHOOK_MAX_BODY_BYTES", raising=False)
    else:
        monkeypatch.setenv("WEBHOOK_MAX_BODY_BYTES", value)
    assert Settings().WEBHOOK_MAX_BODY_BYTES == expected


@pytest.mark.parametrize("value", ["65535", "8388609", "0", "-1", "2MiB", ""])
def test_invalid_webhook_limit_fails_configuration(monkeypatch, value):
    from config.settings import Settings
    monkeypatch.setenv("WEBHOOK_MAX_BODY_BYTES", value)
    with pytest.raises(RuntimeError, match="WEBHOOK_MAX_BODY_BYTES"):
        Settings()

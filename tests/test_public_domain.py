"""Configured public links and sender do not trust incoming host headers."""
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from web.public_urls import public_origin


@pytest.fixture(scope="module")
def database_schema():
    yield


@pytest.fixture(autouse=True)
def isolated_database():
    yield


@pytest.mark.parametrize("base,production,expected", [
    ("https://metodobase.com.mx", True, "https://metodobase.com.mx"),
    ("https://metodobase.com.mx/", True, "https://metodobase.com.mx"),
    ("http://localhost:8000", False, "http://localhost:8000"),
    ("http://127.0.0.1:8000/", False, "http://127.0.0.1:8000"),
])
def test_origin_uses_explicit_configuration_and_preserves_local_development(base, production, expected):
    assert public_origin(SimpleNamespace(BASE_URL=base, is_production=production)) == expected


@pytest.mark.parametrize("base,production", [
    ("http://metodobase.com.mx", True), ("http://localhost:8000", True),
    ("http://external.example.invalid", False), ("//metodobase.com.mx", True),
    ("https://metodobase.com.mx/dashboard", True),
    ("https://metodobase.com.mx?next=evil", True),
    ("https://metodobase.com.mx#evil", True),
    ("https://user@metodobase.com.mx", True),
    ("https://metodobase.com.mx:invalid", True),
    ("https://metodobase.com.mx:99999", True),
    ("https://metodobase.com.mx\\evil", True),
    ("https://metodobase.com.mx%2fevil", True),
    ("https://metodobase.com.mx\r\nInjected: value", True),
    ("", True), (None, True),
])
def test_invalid_public_origin_is_rejected_without_fallback(base, production):
    with pytest.raises(ValueError, match="Public origin configuration is invalid"):
        public_origin(SimpleNamespace(BASE_URL=base, is_production=production))


EMAIL_CASES = [
    ("send_welcome", ("Synthetic",)),
    ("send_plan_generated", ("Synthetic",)),
    ("send_subscription_activated", ("Synthetic", "standard")),
    ("send_payment_failed", ("Synthetic",)),
]


@pytest.mark.parametrize("base", ["https://metodobase.com.mx/", "http://localhost:8000"])
@pytest.mark.parametrize("method,args", EMAIL_CASES)
def test_business_email_links_follow_the_configured_domain(monkeypatch, base, method, args):
    from web.services import email_service
    send = Mock(return_value=True)
    monkeypatch.setattr(email_service, "get_settings", lambda: SimpleNamespace(BASE_URL=base, is_production=False))
    monkeypatch.setattr(email_service, "_send", send)
    assert getattr(email_service, method)("synthetic@example.invalid", *args) is True
    html = send.call_args.args[2]
    assert f'href="{base.rstrip("/")}/dashboard"' in html
    assert "metodobase.app" not in html


@pytest.mark.parametrize("method,args", EMAIL_CASES)
def test_email_never_sends_a_link_from_invalid_configuration(monkeypatch, method, args):
    from web.services import email_service
    send = Mock()
    monkeypatch.setattr(email_service, "get_settings", lambda: SimpleNamespace(
        BASE_URL="https://metodobase.com.mx@attacker.invalid/path", is_production=True))
    monkeypatch.setattr(email_service, "_send", send)
    assert getattr(email_service, method)("synthetic@example.invalid", *args) is False
    send.assert_not_called()


@pytest.mark.parametrize("host", ["metodobase.com.mx", "attacker.example.invalid"])
def test_landing_canonical_ignores_incoming_host_and_origin(monkeypatch, host):
    from web.routes import pages
    from web.settings import get_settings
    monkeypatch.setattr(get_settings(), "BASE_URL", "https://metodobase.com.mx")
    app = FastAPI()

    @app.middleware("http")
    async def nonce(request, call_next):
        request.state.csp_nonce = "synthetic-domain-nonce"
        return await call_next(request)

    app.include_router(pages.router)
    with TestClient(app) as client:
        response = client.get("/", headers={"Host": host, "Origin": "https://attacker.example.invalid"})
    assert response.status_code == 200
    assert '<link rel="canonical" href="https://metodobase.com.mx/">' in response.text
    assert "attacker.example.invalid" not in response.text


def test_default_sender_matches_the_new_domain(monkeypatch):
    from config.settings import DEFAULT_EMAIL_FROM, Settings
    monkeypatch.delenv("RESEND_FROM_EMAIL", raising=False)
    monkeypatch.setenv("METODOBASE_ENV", "testing")
    assert Settings().RESEND_FROM_EMAIL == DEFAULT_EMAIL_FROM == "MetodoBase <no-reply@metodobase.com.mx>"


@pytest.mark.parametrize("transport", ["business", "reminder"])
def test_both_mail_transports_use_the_explicit_sender(monkeypatch, transport):
    import resend
    from web.services import email_service, notification_transports
    from web.settings import get_settings
    sender = "MetodoBase <acceso@metodobase.com.mx>"
    monkeypatch.setattr(get_settings(), "RESEND_API_KEY", "synthetic-no-real-provider-key")
    monkeypatch.setattr(get_settings(), "RESEND_FROM_EMAIL", sender)
    send = Mock(return_value={"id": "synthetic-provider-ack"})
    monkeypatch.setattr(resend.Emails, "send", send)
    if transport == "business":
        assert email_service._send("synthetic@example.invalid", "Synthetic", "<p>Synthetic</p>") is True
    else:
        message = notification_transports.ReminderMessage("synthetic@example.invalid", "account_period_end",
            "https://metodobase.com.mx/suscripciones", "https://metodobase.com.mx/excluir", "synthetic-idempotency")
        assert notification_transports.ResendReminderPort(enabled=True).send(message).kind == "accepted"
    assert send.call_args.args[0]["from"] == sender

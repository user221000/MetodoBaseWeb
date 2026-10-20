"""Installed Resend SDK wire and MP observation; transports never use sockets."""
from datetime import datetime,timedelta,timezone
import json
import pytest

from web.services.notification_transports import BillingReference,ProviderReadPort,ReminderMessage,ResendReminderPort


class Client:
    def __init__(self,response=None,error=None):self.calls=[];self.response=response;self.error=error
    def request(self,**kwargs):
        self.calls.append(kwargs)
        if self.error is not None:raise self.error
        return json.dumps(self.response).encode(),200,{"content-type":"application/json"}


def message():
    return ReminderMessage("synthetic-recipient@example.invalid","account_period_end","https://app.example.invalid/suscripciones",
        "https://app.example.invalid/notificaciones/excluir#token="+"x"*43,"notification36/synthetic-id")


def test_real_sdk_wire_literal_from_and_exact_message_idempotency(monkeypatch):
    import resend
    from web.settings import get_settings
    client=Client({"id":"synthetic-provider-id"})
    monkeypatch.setattr(resend,"default_http_client",client)
    monkeypatch.setattr(get_settings(),"RESEND_API_KEY","synthetic-not-live-r27-key")
    result=ResendReminderPort(enabled=True).send(message())
    assert result.kind=="accepted" and result.provider_id=="synthetic-provider-id"
    assert len(client.calls)==1
    call=client.calls[0]
    assert call["url"]=="https://api.resend.com/emails"
    assert "from" in call["json"] and "from_" not in call["json"]
    assert call["json"]["to"]==[message().destination]
    assert call["headers"]["Idempotency-Key"]==message().idempotency_key
    assert "fact_id" not in call["json"]["html"] and "amount" not in call["json"]["html"]


@pytest.mark.parametrize("response",[{},None,{"id":""},{"id":True},{"id":"x"*257}])
def test_empty_or_invalid_sdk_ack_is_uncertain_not_retryable(monkeypatch,response):
    import resend
    from web.settings import get_settings
    client=Client(response)
    monkeypatch.setattr(resend,"default_http_client",client)
    monkeypatch.setattr(get_settings(),"RESEND_API_KEY","synthetic-not-live-r27-key")
    assert ResendReminderPort(enabled=True).send(message()).kind=="uncertain"
    assert len(client.calls)==1


def test_sdk_timeout_is_single_attempt_and_does_not_log_recipient_link_or_error(monkeypatch,caplog):
    import resend
    from web.settings import get_settings
    client=Client(error=TimeoutError("PRIVATE_SYNTHETIC_TRANSPORT_SENTINEL"))
    monkeypatch.setattr(resend,"default_http_client",client)
    monkeypatch.setattr(get_settings(),"RESEND_API_KEY","synthetic-not-live-r27-key")
    assert ResendReminderPort(enabled=True).send(message()).kind=="uncertain"
    assert len(client.calls)==1
    assert "PRIVATE_SYNTHETIC_TRANSPORT_SENTINEL" not in caplog.text
    assert message().destination not in caplog.text
    assert message().exclusion_url not in caplog.text


def test_missing_configuration_and_default_closed_never_call_sdk(monkeypatch):
    import resend
    from web.settings import get_settings
    client=Client({"id":"must-not-send"})
    monkeypatch.setattr(resend,"default_http_client",client)
    monkeypatch.setattr(get_settings(),"RESEND_API_KEY","")
    with pytest.raises(RuntimeError):ResendReminderPort().send(message())
    assert ResendReminderPort(enabled=True).send(message()).kind=="not_sent_terminal"
    assert client.calls==[]


def test_mp_single_payment_never_becomes_invoice_arrears(monkeypatch):
    from web.services import mercadopago_service as mp
    now=datetime.now(timezone.utc)
    reference=BillingReference("synthetic-user","gym",1,"mercadopago","payment","12345",None,"standard",10000,
        "active",now-timedelta(days=1),now+timedelta(days=29),"synthetic-purchase")
    value={"id":12345,"currency_id":"MXN","external_reference":"synthetic-purchase","transaction_amount":100,
        "status":"approved","transaction_amount_refunded":0}
    class Payment:
        def get(self,identifier):
            assert identifier=="12345"
            return {"status":200,"response":dict(value)}
    class SDK:
        def payment(self):return Payment()
    monkeypatch.setattr(mp,"get_sdk",lambda:SDK())
    result=ProviderReadPort(enabled=True).read_billing(reference)
    assert result.paid and result.invoice_id is None and result.invoice_status=="paid" and result.due_at is None
    value["status"]="rejected"
    rejected=ProviderReadPort(enabled=True).read_billing(reference)
    assert not rejected.paid and rejected.invoice_status=="unknown" and rejected.due_at is None
    value["external_reference"]="another-purchase"
    with pytest.raises(ValueError):ProviderReadPort(enabled=True).read_billing(reference)

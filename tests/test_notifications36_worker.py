"""Real owned transactions/ports, no retry or contact after uncertain handoff."""
from datetime import datetime,timedelta,timezone
from urllib.parse import urlsplit,parse_qs
import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import select,func
from sqlalchemy.orm import Session

from tests.notifications36_http import followup_db as followup_db,notification_http as notification_http
from tests.test_notifications36_http import billing,preference,observe,queue,candidate
from web.database.models import (Usuario,Subscription,NotificationOutbox,NotificationPreference,NotificationAttempt)
from web.services import notification_worker as worker
from web.services.notification_domain import SendResult


class Port:
    enabled=True
    def __init__(self,outcome=SendResult("accepted","synthetic-reminder-ack")):
        self.messages=[];self.outcome=outcome
    def send(self,message):
        self.messages.append(message)
        if isinstance(self.outcome,Exception):raise self.outcome
        return self.outcome


def prepared(case,monkeypatch):
    billing(case,monkeypatch)
    assert preference(case).status_code==200
    assert observe(case).status_code==200
    result=queue(case,candidate(case))
    assert result.status_code==200
    return result.json()["outbox"]["id"]


def origin():
    from web.settings import get_settings
    from web.services.password_recovery import public_origin
    return public_origin(get_settings())


def test_exact_handoff_acceptance_one_use_and_disabled_default(notification_http,monkeypatch):
    c=notification_http;identifier=prepared(c,monkeypatch)
    with pytest.raises(HTTPException) as caught:
        worker.run_one(c["user"],"gym",identifier,origin(),factory=c["factory"])
    assert caught.value.status_code==503
    port=Port()
    result=worker.run_one(c["user"],"gym",identifier,origin(),port,factory=c["factory"])
    assert result["outbox"]["state"]=="accepted" and len(port.messages)==1
    assert port.messages[0].destination.endswith("@example.invalid")
    assert "/notificaciones/excluir#token=" in port.messages[0].exclusion_url
    with pytest.raises(HTTPException):worker.run_one(c["user"],"gym",identifier,origin(),port,factory=c["factory"])
    assert len(port.messages)==1


def test_timeout_is_uncertain_and_never_automatically_retried(notification_http,monkeypatch):
    c=notification_http;identifier=prepared(c,monkeypatch);port=Port(TimeoutError("Synthetic port timeout"))
    result=worker.run_one(c["user"],"gym",identifier,origin(),port,factory=c["factory"])
    assert result["outbox"]["state"]=="uncertain"
    with pytest.raises(HTTPException):worker.run_one(c["user"],"gym",identifier,origin(),port,factory=c["factory"])
    assert len(port.messages)==1


def test_expired_sending_lease_is_uncertain_and_stale_receipt_fenced(notification_http,monkeypatch):
    c=notification_http;identifier=prepared(c,monkeypatch);now=datetime.now(timezone.utc)
    claimed=worker.claim(c["user"],"gym",identifier,factory=c["factory"],now=now)
    sending,message=worker.prepare_handoff(claimed,origin(),factory=c["factory"],now=now)
    result=worker.recover_expired_sending(c["user"],"gym",identifier,factory=c["factory"],now=now+timedelta(seconds=61))
    assert result["outbox"]["state"]=="uncertain"
    with pytest.raises(HTTPException):worker.finish(sending,SendResult("accepted","late-ack"),factory=c["factory"],now=now+timedelta(seconds=61))
    with Session(c["admin"]) as db:
        assert db.get(NotificationOutbox,identifier).state=="uncertain"
        assert db.scalar(select(func.count()).select_from(NotificationAttempt).where(NotificationAttempt.outbox_id==identifier))==2


def test_changed_customer_mapping_invalidates_captured_facts(notification_http,monkeypatch):
    c=notification_http;billing(c,monkeypatch)
    assert observe(c).status_code==200
    assert candidate(c)["eligible"] is True
    from web.services.provider_subjects import record_provider_subject
    with Session(c["admin"]) as db:
        sub=db.scalar(select(Subscription).where(Subscription.gym_id==c["user"]))
        customer="cus_changed_"+uuid.uuid4().hex
        record_provider_subject(db,"stripe","customer",customer,c["user"],"synthetic-current-source-change")
        sub.stripe_customer_id=customer;db.commit()
    assert candidate(c)["eligible"] is False


def test_inactive_subject_can_exclude_then_reactivation_does_not_revive(notification_http,monkeypatch):
    c=notification_http;identifier=prepared(c,monkeypatch);port=Port()
    result=worker.run_one(c["user"],"gym",identifier,origin(),port,factory=c["factory"])
    assert result["outbox"]["state"]=="accepted"
    token=parse_qs(urlsplit(port.messages[0].exclusion_url).fragment)["token"][0]
    with Session(c["admin"]) as db:
        db.get(Usuario,c["user"]).activo=False;db.commit()
    response=c["raw"].post("/api/notificaciones/excluir",json={"token":token})
    assert response.status_code==200
    with Session(c["admin"]) as db:
        latest=db.scalar(select(NotificationPreference).where(NotificationPreference.user_id==c["user"]).order_by(NotificationPreference.version.desc()))
        assert latest.enabled is False
        db.get(Usuario,c["user"]).activo=True;db.commit()
    with pytest.raises(HTTPException):worker.run_one(c["user"],"gym",identifier,origin(),port,factory=c["factory"])
    assert len(port.messages)==1

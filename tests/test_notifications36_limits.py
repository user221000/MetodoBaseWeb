"""Real durable handoffs, exclusion boundaries and bounded own projections."""
from datetime import datetime,timedelta,timezone
from urllib.parse import parse_qs,urlsplit
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import select,func
from sqlalchemy.orm import Session

from tests.notifications36_http import followup_db as followup_db,notification_http as notification_http
from tests.test_notifications36_http import billing,preference
from tests.test_notifications36_worker import prepared,Port,origin
from web.database.models import Usuario,NotificationOutbox,NotificationPreference,NotificationAttempt
from web.services import notifications as service,notification_worker as worker
from web.services.notification_transports import ProviderReadPort
from web.services.notification_domain import SendResult,aware


def principal(case):
    with Session(case["admin"]) as db:
        return {"id":case["user"],"session_version":db.get(Usuario,case["user"]).session_version}


def refresh(case,at):
    return service.observe(principal(case),"gym",str(uuid.uuid4()),ProviderReadPort(enabled=True),factory=case["factory"],now=at)


def test_definite_rejections_have_three_attempt_limit_and_durable_frequency(notification_http,monkeypatch):
    c=notification_http;identifier=prepared(c,monkeypatch);start=datetime.now(timezone.utc)
    port=Port(SendResult("not_sent_retryable"))
    first=worker.run_one(c["user"],"gym",identifier,origin(),port,factory=c["factory"],now=start)
    assert first["outbox"]["state"]=="retry_wait"
    blocked=worker.run_one(c["user"],"gym",identifier,origin(),port,factory=c["factory"],now=start+timedelta(seconds=61))
    assert blocked["handed_off"] is False and len(port.messages)==1
    for day in (1,2):
        at=start+timedelta(days=day)
        assert refresh(c,at)["observed"] is True
        outcome=worker.run_one(c["user"],"gym",identifier,origin(),port,factory=c["factory"],now=at)
    assert outcome["outbox"]["state"]=="failed" and outcome["outbox"]["attempt_count"]==3
    assert len(port.messages)==3
    with Session(c["admin"]) as db:
        assert db.scalar(select(func.count()).select_from(NotificationAttempt).where(NotificationAttempt.outbox_id==identifier))==6
    # A distinct provider source/intention cannot bypass the per-person 7d cap.
    billing(c,monkeypatch)
    at=start+timedelta(days=3)
    refresh(c,at)
    source=service.candidates(principal(c),"gym",factory=c["factory"],now=at)["candidates"][1]
    from web.notification_schemas import QueueWrite
    command=QueueWrite(purpose=source["purpose"],preference_id=source["preference"]["id"],
        expected_preference_version=source["preference"]["version"],fact_id=source["fact_id"],source_hash=source["source_hash"],confirm=True)
    fourth=service.queue(principal(c),"gym",command,str(uuid.uuid4()),factory=c["factory"],now=at)["outbox"]["id"]
    blocked=worker.run_one(c["user"],"gym",fourth,origin(),port,factory=c["factory"],now=at)
    assert blocked["handed_off"] is False and len(port.messages)==3
    with Session(c["admin"]) as db:
        row=db.get(NotificationOutbox,fourth)
        assert row.state=="retry_wait" and aware(row.next_attempt_at)==start+timedelta(days=7)


@pytest.mark.parametrize("change",["contact","preference","source"])
def test_changes_after_claim_block_handoff_without_contact(notification_http,monkeypatch,change):
    c=notification_http;identifier=prepared(c,monkeypatch)
    claimed=worker.claim(c["user"],"gym",identifier,factory=c["factory"])
    if change=="preference":
        assert preference(c,enabled=False,version=1).status_code==200
        with pytest.raises(HTTPException):worker.prepare_handoff(claimed,origin(),factory=c["factory"])
    else:
        if change=="contact":
            with Session(c["admin"]) as db:
                db.get(Usuario,c["user"]).email="changed-"+uuid.uuid4().hex+"@example.invalid";db.commit()
        else:billing(c,monkeypatch,status="canceled")
        assert worker.prepare_handoff(claimed,origin(),factory=c["factory"]) is None
    with Session(c["admin"]) as db:
        row=db.get(NotificationOutbox,identifier)
        assert row.state=="suppressed" and row.attempt_count==0
        assert db.scalar(select(func.count()).select_from(NotificationAttempt).where(NotificationAttempt.outbox_id==identifier,NotificationAttempt.kind=="handoff"))==0


def test_exclusion_expiry_prefetch_and_old_contact_never_disable_new_consent(notification_http,monkeypatch):
    c=notification_http;identifier=prepared(c,monkeypatch);port=Port();start=datetime.now(timezone.utc)
    worker.run_one(c["user"],"gym",identifier,origin(),port,factory=c["factory"],now=start)
    token=parse_qs(urlsplit(port.messages[0].exclusion_url).fragment)["token"][0]
    before=c["raw"].get("/api/notificaciones/preferencias",params={"context":"gym"}).json()
    page=c["raw"].get("/notificaciones/excluir")
    assert page.status_code==200 and c["user"] not in page.text and "example.invalid" not in page.text
    assert service.exclude(token,factory=c["factory"],now=start+timedelta(days=30))=={"success":True}
    assert c["raw"].get("/api/notificaciones/preferencias",params={"context":"gym"}).json()==before
    assert preference(c,version=1).status_code==200
    assert c["raw"].post("/api/notificaciones/excluir",json={"token":token}).json()=={"success":True}
    with Session(c["admin"]) as db:
        current=db.scalar(select(NotificationPreference).where(NotificationPreference.user_id==c["user"]).order_by(NotificationPreference.version.desc()))
        assert current.version==2 and current.enabled is True


def test_strict_stream_and_civil_queries_reject_without_side_effects(notification_http):
    c=notification_http;path="/api/notificaciones/preferencias/account_period_end?context=gym"
    for content in (b'{"expected_version":0,"expected_version":0,"enabled":true,"confirm":true}',
                    b'{"expected_version":false,"enabled":true,"confirm":true}',b'{"x":"\xff"}'):
        response=c["raw"].put(path,content=content,headers={"Content-Type":"application/json","Idempotency-Key":str(uuid.uuid4())})
        assert response.status_code==422
    response=c["raw"].put(path,content=b' '*8193,headers={"Content-Type":"application/json","Idempotency-Key":str(uuid.uuid4())})
    assert response.status_code==413
    for params in ({"context":"gym","from":"0","through":"0"},{"context":"gym","from":"2026-01-01"},
                   {"context":"gym","from":"2026-01-01","through":"2026-03-04"}):
        assert c["raw"].get("/api/notificaciones/metricas",params=params).status_code==422
    for params in ({"context":"gym","limit":0},{"context":"gym","limit":51},{"context":"gym","after":"foreign"}):
        assert c["raw"].get("/api/notificaciones/outbox",params=params).status_code==422
    with Session(c["admin"]) as db:
        assert db.scalar(select(func.count()).select_from(NotificationPreference).where(NotificationPreference.user_id==c["user"]))==0

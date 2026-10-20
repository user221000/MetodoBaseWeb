"""Owned cleanup, commit uncertainty and parallel intent under real current auth."""
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit,parse_qs
import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import select,func,update,delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session,sessionmaker

from tests.notifications36_http import followup_db as followup_db,notification_http as notification_http
from tests.test_notifications36_http import billing,preference,observe,queue,candidate,key
from tests.test_notifications36_worker import prepared,origin,Port
from web.database.models import (Usuario,NotificationPreference,NotificationBillingFact,NotificationOutbox,NotificationAttempt)
from web.database.tenant_context import current_tenant
from web.notification_schemas import PreferenceWrite
from web.services import notifications as service,notification_worker as worker


def principal(case):
    with Session(case["admin"]) as db:return {"id":case["user"],"session_version":db.get(Usuario,case["user"]).session_version}


@pytest.mark.parametrize("when",["before","after"])
def test_commit_failure_never_acknowledges_and_exact_replay_is_explicit(notification_http,when):
    c=notification_http;request_key=str(uuid.uuid4())
    class Fault(Session):
        def commit(self):
            if when=="after":super().commit()
            raise RuntimeError("Synthetic commit confirmation lost")
    factory=sessionmaker(bind=c["engine"],class_=Fault,autoflush=False)
    command=PreferenceWrite(expected_version=0,enabled=True,confirm=True)
    with pytest.raises(HTTPException) as caught:
        service.set_preference(principal(c),"gym","account_period_end",command,request_key,factory=factory)
    assert caught.value.status_code==503 and caught.value.detail["code"]=="notification_unconfirmed"
    with Session(c["admin"]) as db:
        assert db.scalar(select(func.count()).select_from(NotificationPreference).where(NotificationPreference.user_id==c["user"]))==(1 if when=="after" else 0)
    replay=preference(c,purpose="account_period_end",headers={"Idempotency-Key":request_key})
    assert replay.status_code==200
    assert replay.json()["replayed"] is (when=="after")


@pytest.mark.parametrize("when",["before","after","invalidate_failure"])
def test_owned_close_failure_does_not_return_success_or_retag_ambient(notification_http,when):
    c=notification_http;instances=[]
    class Fault(Session):
        def __init__(self,*a,**k):super().__init__(*a,**k);instances.append(self)
        def close(self):
            if when=="after":super().close()
            raise RuntimeError("Synthetic close uncertainty")
        def invalidate(self):
            if when=="invalidate_failure":raise RuntimeError("Synthetic invalidation unavailable")
            return super().invalidate()
    factory=sessionmaker(bind=c["engine"],class_=Fault,autoflush=False)
    token=current_tenant.set("synthetic-ambient-tenant")
    try:
        with pytest.raises(HTTPException) as caught:
            service.set_preference(principal(c),"gym","account_period_end",PreferenceWrite(expected_version=0,enabled=True,confirm=True),
                str(uuid.uuid4()),factory=factory)
        assert caught.value.status_code==503
        assert current_tenant.get()=="synthetic-ambient-tenant"
    finally:
        current_tenant.reset(token)
        # Only this test-owned faulty Session can retain checkout when both
        # cleanup methods fail; no ambient Session/engine disposal is a repair.
        for instance in instances:Session.close(instance)
    with Session(c["admin"]) as db:
        assert db.scalar(select(func.count()).select_from(NotificationPreference).where(NotificationPreference.user_id==c["user"]))==1


def test_parallel_same_intent_records_one_event_and_replay_ack(notification_http):
    c=notification_http;headers=key()
    with ThreadPoolExecutor(max_workers=2) as threads:
        replies=list(threads.map(lambda _:preference(c,headers=headers),range(2)))
    assert [r.status_code for r in replies]==[200,200]
    assert sorted(r.json()["replayed"] for r in replies)==[False,True]
    with Session(c["admin"]) as db:
        assert db.scalar(select(func.count()).select_from(NotificationPreference).where(NotificationPreference.user_id==c["user"]))==1


def test_history_and_projection_cannot_be_rewritten_or_deleted(notification_http,monkeypatch):
    c=notification_http;identifier=prepared(c,monkeypatch)
    worker.run_one(c["user"],"gym",identifier,origin(),Port(),factory=c["factory"])
    for model in (NotificationPreference,NotificationBillingFact,NotificationAttempt,NotificationOutbox):
        with Session(c["admin"]) as db:
            with pytest.raises(IntegrityError):
                db.execute(update(model).where(model.user_id==c["user"]).values(id=model.id));db.commit()
            db.rollback()
            with pytest.raises(IntegrityError):
                db.execute(delete(model).where(model.user_id==c["user"]));db.commit()
            db.rollback()


def test_exclusion_while_off_suppresses_another_pending_and_never_revives(notification_http,monkeypatch):
    c=notification_http;identifier=prepared(c,monkeypatch);port=Port()
    worker.run_one(c["user"],"gym",identifier,origin(),port,factory=c["factory"])
    token=parse_qs(urlsplit(port.messages[0].exclusion_url).fragment)["token"][0]
    billing(c,monkeypatch)
    assert observe(c).status_code==200
    second=queue(c,candidate(c))
    assert second.status_code==200
    pending=second.json()["outbox"]["id"]
    with Session(c["admin"]) as db:db.get(Usuario,c["user"]).activo=False;db.commit()
    assert c["raw"].post("/api/notificaciones/excluir",json={"token":token}).status_code==200
    with Session(c["admin"]) as db:
        assert db.get(NotificationOutbox,pending).state=="suppressed"
        assert db.scalar(select(NotificationPreference).where(NotificationPreference.user_id==c["user"]).order_by(NotificationPreference.version.desc())).enabled is False
        db.get(Usuario,c["user"]).activo=True;db.commit()
    with pytest.raises(HTTPException):worker.run_one(c["user"],"gym",pending,origin(),port,factory=c["factory"])
    assert len(port.messages)==1


def test_both_cleanup_methods_failing_on_a_read_exposes_bounded_checkout_limit(notification_http):
    c=notification_http;instances=[];baseline=c["engine"].pool.checkedout()
    class Fault(Session):
        def __init__(self,*a,**k):super().__init__(*a,**k);instances.append(self)
        def close(self):raise RuntimeError("Synthetic read close failure")
        def invalidate(self):raise RuntimeError("Synthetic read invalidation failure")
    factory=sessionmaker(bind=c["engine"],class_=Fault,autoflush=False)
    try:
        with pytest.raises(HTTPException) as caught:service.context(principal(c),"gym",factory=factory)
        assert caught.value.status_code==503
        assert c["engine"].pool.checkedout()==baseline+1
    finally:
        for instance in instances:Session.close(instance)
    assert c["engine"].pool.checkedout()==baseline

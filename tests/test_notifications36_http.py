"""HTTP36 real auth/MFA; provider operations doubled only at their SDK boundary."""
from datetime import datetime,timedelta,timezone
import uuid
from sqlalchemy import select,func
from sqlalchemy.orm import Session

from tests.notifications36_http import followup_db as followup_db,notification_http as notification_http
from web.database.models import (NotificationPreference,NotificationOutbox,NotificationBillingFact,
    NotificationAttempt,Usuario)
from web.services.notification_transports import ProviderReadPort


def key():return {"Idempotency-Key":str(uuid.uuid4())}


def preference(case,*,enabled=True,version=0,purpose="confirmed_payment_issue",headers=None):
    return case["raw"].put("/api/notificaciones/preferencias/"+purpose,params={"context":"gym"},
        json={"expected_version":version,"enabled":enabled,"interval_hours":24,"confirm":True},headers=headers or key())


def billing(case,monkeypatch,*,status="past_due",paid=False,refunded=False,due=True):
    from web.services.subscription_service import activate_subscription,update_subscription_status
    from web.services.provider_subjects import record_provider_subject
    from web.services import stripe_service
    from web.services.billing_integrity import price_in_cents
    now=datetime.now(timezone.utc).replace(microsecond=0)
    sid="sub_"+uuid.uuid4().hex;cid="cus_"+uuid.uuid4().hex;iid="in_"+uuid.uuid4().hex
    amount=price_in_cents("standard")
    with Session(case["admin"]) as db:
        sub=activate_subscription(db,case["user"],"standard",stripe_customer_id=cid,stripe_subscription_id=sid,
            current_period_start=now-timedelta(days=29),current_period_end=now+timedelta(days=1))
        update_subscription_status(db,sub,status)
        record_provider_subject(db,"stripe","subscription",sid,case["user"],"synthetic-r27-purchase")
        record_provider_subject(db,"stripe","customer",cid,case["user"],"synthetic-r27-purchase")
        db.commit()
    subscription={"id":sid,"customer":cid,"status":status,"latest_invoice":iid,
        "current_period_start":int((now-timedelta(days=29)).timestamp()),"current_period_end":int((now+timedelta(days=1)).timestamp())}
    invoice={"id":iid,"subscription":sid,"customer":cid,"currency":"mxn","amount_due":amount,
        "amount_paid":amount if paid else 0,"amount_remaining":0 if paid else amount,
        "paid":paid,"status":"paid" if paid else "open","due_date":int((now-timedelta(days=1)).timestamp()) if due else None,
        "charge":{"id":"ch_synthetic","customer":cid,"currency":"mxn","paid":paid,"captured":paid,
            "amount":amount,"refunded":refunded,"amount_refunded":amount if refunded else 0}}
    monkeypatch.setattr(stripe_service,"_init_stripe",lambda:True)
    monkeypatch.setattr(stripe_service.stripe.Subscription,"retrieve",lambda *a,**k:dict(subscription))
    monkeypatch.setattr(stripe_service.stripe.Invoice,"retrieve",lambda *a,**k:dict(invoice))
    case["raw"].app.state.notification_billing_port=ProviderReadPort(enabled=True)
    return subscription,invoice


def observe(case):
    return case["raw"].post("/api/notificaciones/observar",params={"context":"gym"},json={},headers=key())


def queue(case,candidate):
    return case["raw"].post("/api/notificaciones/outbox",params={"context":"gym"},headers=key(),json={
        "purpose":candidate["purpose"],"preference_id":candidate["preference"]["id"],
        "expected_preference_version":candidate["preference"]["version"],"fact_id":candidate["fact_id"],
        "source_hash":candidate["source_hash"],"confirm":True})


def candidate(case,purpose="confirmed_payment_issue"):
    response=case["raw"].get("/api/notificaciones/candidatos",params={"context":"gym"})
    assert response.status_code==200
    return next(c for c in response.json()["candidates"] if c["purpose"]==purpose)


def test_context_and_virtual_preferences_are_readonly_and_transport_disabled(notification_http):
    c=notification_http
    response=c["raw"].get("/api/notificaciones/contexto",params={"context":"gym"})
    assert response.status_code==200
    assert response.json()["delivery_enabled"] is False
    response=c["raw"].get("/api/notificaciones/preferencias",params={"context":"gym"})
    assert response.status_code==200 and len(response.json()["items"])==2
    assert all(not p["enabled"] and p["version"]==0 for p in response.json()["items"])
    assert observe(c).status_code==503
    with Session(c["admin"]) as db:
        assert db.scalar(select(func.count()).select_from(NotificationPreference).where(NotificationPreference.user_id==c["user"]))==0
        assert db.scalar(select(func.count()).select_from(NotificationOutbox).where(NotificationOutbox.user_id==c["user"]))==0


def test_explicit_preference_cas_replay_and_unknown_never_queues(notification_http):
    c=notification_http;headers=key()
    response=preference(c,headers=headers)
    assert response.status_code==200 and response.json()["preference"]["version"]==1
    repeated=preference(c,headers=headers)
    assert repeated.status_code==200 and repeated.json()["replayed"] and repeated.json()["read_required"]
    assert preference(c).status_code==409
    changed=preference(c,enabled=False,version=1,headers=headers)
    assert changed.status_code==409
    assert not candidate(c)["eligible"]
    disabled=preference(c,enabled=False,version=1)
    assert disabled.status_code==200 and disabled.json()["preference"]["version"]==2


def test_verified_provider_observation_durable_queue_and_explicit_optout(notification_http,monkeypatch):
    c=notification_http;billing(c,monkeypatch)
    assert preference(c).status_code==200
    response=observe(c)
    assert response.status_code==200
    source=candidate(c)
    assert source["eligible"] is True
    response=queue(c,source)
    assert response.status_code==200 and response.json()["outbox"]["state"]=="pending"
    assert queue(c,source).status_code==409
    assert preference(c,enabled=False,version=1).status_code==200
    rows=c["raw"].get("/api/notificaciones/outbox",params={"context":"gym"}).json()["items"]
    assert len(rows)==1 and rows[0]["state"]=="suppressed"
    with Session(c["admin"]) as db:
        assert db.scalar(select(func.count()).select_from(NotificationBillingFact).where(NotificationBillingFact.user_id==c["user"]))==1
        assert db.scalar(select(func.count()).select_from(NotificationAttempt).where(NotificationAttempt.user_id==c["user"]))==1


def test_paid_cancelled_refunded_and_missing_due_are_not_arrears(notification_http,monkeypatch):
    c=notification_http
    for changes in ({"paid":True,"status":"active"},{"status":"canceled"},{"refunded":True},{"due":False}):
        billing(c,monkeypatch,**changes)
        assert observe(c).status_code==200
        assert candidate(c)["eligible"] is False


def test_body_and_authority_never_select_other_recipient_or_context(notification_http):
    c=notification_http
    payload={"expected_version":0,"enabled":True,"confirm":True,"user_id":c["member"]}
    response=c["raw"].put("/api/notificaciones/preferencias/confirmed_payment_issue",params={"context":"gym"},json=payload,headers=key())
    assert response.status_code==422
    assert "user_id" not in response.text
    with Session(c["admin"]) as db:
        user=db.get(Usuario,c["user"]);user.tipo="usuario";db.commit()
    assert preference(c).status_code==403
    # A historical ambiguous owner receives no personal account adoption.
    assert c["raw"].get("/api/notificaciones/contexto",params={"context":"personal"}).status_code==403

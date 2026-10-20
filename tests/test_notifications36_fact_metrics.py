"""Provider contradiction is unknown; paid period observations are not causality."""
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
import uuid

from sqlalchemy import select,func
from sqlalchemy.orm import Session

from tests.notifications36_http import followup_db as followup_db,notification_http as notification_http
from tests.test_notifications36_http import billing,observe,candidate,queue
from web.database.models import Usuario,Subscription,NotificationBillingFact
from web.services import notifications as service
from web.services.notification_transports import ProviderReadPort


def subject(case):
    with Session(case["admin"]) as db:
        return {"id":case["user"],"session_version":db.get(Usuario,case["user"]).session_version}


def test_conflicting_provider_period_supersedes_previous_fact_with_unknown(notification_http,monkeypatch):
    c=notification_http;subscription,invoice=billing(c,monkeypatch)
    assert observe(c).status_code==200 and candidate(c)["eligible"] is True
    subscription["current_period_end"]+=86400
    assert observe(c).status_code==200
    source=c["raw"].get("/api/notificaciones/candidatos",params={"context":"gym"})
    assert source.status_code==200 and source.json()["source_state"]=="unknown"
    assert all(not row["eligible"] and row["fact_id"] is None for row in source.json()["candidates"])
    with Session(c["admin"]) as db:
        assert db.scalar(select(func.count()).select_from(NotificationBillingFact).where(NotificationBillingFact.user_id==c["user"]))==2


def test_failed_reobservation_does_not_keep_previous_fresh_source_eligible(notification_http,monkeypatch):
    from tests.test_notifications36_http import preference
    from web.services import stripe_service
    c=notification_http;billing(c,monkeypatch)
    assert preference(c).status_code==200 and observe(c).status_code==200
    previous=candidate(c)
    assert previous["eligible"] is True
    def unavailable(*args,**kwargs):raise ValueError("Synthetic provider identity contradiction")
    monkeypatch.setattr(stripe_service.stripe.Subscription,"retrieve",unavailable)
    assert observe(c).status_code==503
    current=c["raw"].get("/api/notificaciones/candidatos",params={"context":"gym"})
    assert current.status_code==200 and current.json()["source_state"]=="unknown"
    assert queue(c,previous).status_code==409


def test_renewal_counts_distinct_verified_paid_periods_and_refund_correction(notification_http,monkeypatch):
    c=notification_http;subscription,invoice=billing(c,monkeypatch,status="active",paid=True)
    start=datetime.now(timezone.utc)-timedelta(minutes=1);expected=subject(c)
    def capture(at):
        return service.observe(expected,"gym",str(uuid.uuid4()),ProviderReadPort(enabled=True),factory=c["factory"],now=at)
    def metrics(at):
        day=at.astimezone(ZoneInfo("America/Mexico_City")).date()
        return service.metrics(expected,"gym",day-timedelta(days=1),day,factory=c["factory"],now=at)
    assert capture(start)["observed"] is True
    assert capture(start+timedelta(seconds=1))["observed"] is True
    assert metrics(start+timedelta(seconds=2))["verified_paid_period_advances"]==0
    subscription["current_period_start"]=subscription["current_period_end"]
    subscription["current_period_end"]+=30*86400
    invoice["id"]="in_renewed_"+uuid.uuid4().hex;subscription["latest_invoice"]=invoice["id"]
    with Session(c["admin"]) as db:
        sub=db.scalar(select(Subscription).where(Subscription.gym_id==c["user"]))
        sub.current_period_start=datetime.fromtimestamp(subscription["current_period_start"],timezone.utc)
        sub.current_period_end=datetime.fromtimestamp(subscription["current_period_end"],timezone.utc)
        db.commit()
    assert capture(start+timedelta(seconds=3))["observed"] is True
    report=metrics(start+timedelta(seconds=4))
    assert report["verified_paid_period_advances"]==1
    assert report["attribution"]=="observed_facts_only_no_email_causality" and report["outbox_states"]=={}
    assert capture(start+timedelta(seconds=5))["observed"] is True
    assert metrics(start+timedelta(seconds=6))["verified_paid_period_advances"]==1
    subscription["current_period_end"]+=86400
    assert capture(start+timedelta(seconds=7))["observed"] is True
    assert metrics(start+timedelta(seconds=8))["verified_paid_period_advances"]==0
    subscription["current_period_end"]-=86400
    invoice["charge"]["refunded"]=True;invoice["charge"]["amount_refunded"]=invoice["amount_paid"]
    assert capture(start+timedelta(seconds=9))["observed"] is True
    assert metrics(start+timedelta(seconds=10))["verified_paid_period_advances"]==0

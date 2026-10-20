"""Nonvacuous purpose/provenance/ACK/clock rules without provider I/O."""
from dataclasses import replace
from datetime import datetime,timedelta,timezone
from types import SimpleNamespace
import pytest
from web.services.notification_domain import BillingSnapshot,SendResult,instant,qualifies

NOW=datetime(2026,10,20,12,tzinfo=timezone.utc)


def source(**changes):
    base=BillingSnapshot("stripe","subscription","sub_synthetic","in_synthetic","past_due","open","mxn",
        10000,0,10000,False,False,NOW-timedelta(days=30),NOW+timedelta(days=1),NOW-timedelta(days=1))
    return replace(base,**changes).validate()


def fact(**changes):
    from dataclasses import asdict
    row=SimpleNamespace(**asdict(source()),created_at=NOW,fresh_until=NOW+timedelta(minutes=15))
    for key,value in changes.items():setattr(row,key,value)
    return row


def test_confirmed_arrears_requires_current_invoice_and_never_client_dates():
    assert qualifies(fact(),"confirmed_payment_issue",NOW)
    assert not qualifies(None,"confirmed_payment_issue",NOW)
    assert not qualifies(fact(provider="mercadopago",invoice_id=None),"confirmed_payment_issue",NOW)


@pytest.mark.parametrize("change",[{"paid":True},{"refunded":True},{"invoice_status":"unknown"},
    {"subscription_status":"canceled"},{"subscription_status":"active"},{"amount_remaining":0},
    {"due_at":None},{"due_at":NOW},{"fresh_until":NOW},{"created_at":NOW+timedelta(microseconds=1)}])
def test_uncertain_paid_cancelled_refunded_or_stale_never_qualifies(change):
    assert not qualifies(fact(**change),"confirmed_payment_issue",NOW)


def test_period_end_is_not_arrears_and_repeated_observation_has_stable_fingerprint():
    row=fact(subscription_status="active",invoice_status="paid",paid=True,amount_paid=10000,amount_remaining=0)
    assert qualifies(row,"account_period_end",NOW)
    assert not qualifies(row,"confirmed_payment_issue",NOW)
    assert source().fingerprint()==source().fingerprint()
    assert source().fingerprint()!=source(amount_paid=5000,amount_remaining=5000).fingerprint()


@pytest.mark.parametrize("change",[{"amount_due":True},{"amount_paid":-1},{"currency":"usd"},
    {"paid":True},{"period_end":None},{"period_end":NOW-timedelta(days=31)}])
def test_contradictory_or_untyped_provider_values_are_rejected(change):
    with pytest.raises(ValueError):source(**change)


def test_explicit_aware_clock_and_opaque_provider_ack():
    with pytest.raises(ValueError):instant(datetime(2026,10,20))
    assert instant(NOW)==NOW
    assert SendResult("accepted","synthetic-provider-id").validate().kind=="accepted"
    for value in (None,"",True,"x"*257):
        with pytest.raises(ValueError):SendResult("accepted",value).validate()

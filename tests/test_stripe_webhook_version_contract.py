"""Actual SQLAlchemy, synthetic Stripe boundary replies, no live payments."""
from copy import deepcopy
from unittest.mock import patch

import pytest

from tests.test_billing_integrity import billing_case, _paid_snapshot, _stored_plan


def _case(factory, principal):
    snapshot = _paid_snapshot(factory, principal)
    snapshot.update(object="subscription", livemode=False)
    invoice = snapshot["latest_invoice"]
    invoice.update(object="invoice", customer="cus_person", subscription="sub_person",
                   livemode=False, amount_due=7900, attempted=True, attempt_count=1,
                   paid_out_of_band=False, payment_intent="pi_current")
    invoice["charge"].update(object="charge", invoice=invoice["id"], livemode=False)
    return snapshot


def _event(invoice, event_type="invoice.paid", *, modern=True, event_id="evt_invoice_contract"):
    body = deepcopy(invoice)
    if modern:
        body["parent"] = {"type": "subscription_details", "subscription_details": {
            "subscription": body.pop("subscription")}}
        for key in ("paid", "paid_out_of_band", "charge", "payment_intent"):
            body.pop(key, None)
    return {"id": event_id, "type": event_type, "api_version": "2026-03-25.dahlia",
            "livemode": False, "data": {"object": body}}


@pytest.mark.parametrize("modern", [False, True])
@pytest.mark.parametrize("renewal", [False, True])
def test_live_config_invoice_paid_is_processed_and_idempotent(billing_case, modern, renewal):
    _, factory, principal = billing_case
    from web.services.stripe_service import handle_webhook_event, reconcile_subscription
    from web.database.models import Payment, StripeWebhookEvent, Subscription
    snapshot = _case(factory, principal)
    if renewal:
        with patch("stripe.Subscription.retrieve", return_value=snapshot):
            with factory() as db:
                reconcile_subscription(db, "sub_person", principal["id"])
                db.commit()
        snapshot["latest_invoice"]["id"] = "in_renewal"
        snapshot["latest_invoice"]["charge"].update(id="ch_renewal", invoice="in_renewal")
        snapshot["current_period_start"] += 86400 * 30
        snapshot["current_period_end"] += 86400 * 30
    event = _event(snapshot["latest_invoice"], modern=modern)
    with patch("web.services.stripe_service._init_stripe", return_value=True), \
            patch("stripe.Subscription.retrieve", return_value=snapshot), \
            patch("stripe.Invoice.retrieve", return_value=snapshot["latest_invoice"]) as invoice_get:
        with factory() as db:
            result = handle_webhook_event(db, event)
            db.commit()
            assert result == "paid:7900"
            assert db.query(Payment).one().stripe_invoice_id == snapshot["latest_invoice"]["id"]
            assert db.query(Subscription).one().status == "active"
        with factory() as db:
            assert handle_webhook_event(db, event) == "duplicate:invoice.paid"
            db.commit()
            assert db.query(Payment).count() == 1
            assert db.query(StripeWebhookEvent).count() == 1
        assert invoice_get.called
    assert _stored_plan(factory, principal["id"]) == "pro"


def test_stale_success_body_cannot_create_paid_ledger_from_open_provider_invoice(billing_case):
    _, factory, principal = billing_case
    from web.services.stripe_service import handle_webhook_event, reconcile_subscription
    from web.database.models import Payment
    snapshot = _case(factory, principal)
    event = _event(snapshot["latest_invoice"], "invoice.payment_succeeded", modern=False)
    with patch("stripe.Subscription.retrieve", return_value=snapshot):
        with factory() as db:
            reconcile_subscription(db, "sub_person", principal["id"])
            db.commit()
    snapshot["status"] = "past_due"
    snapshot["latest_invoice"].update(status="open", paid=False, amount_paid=0, charge=None)
    with patch("web.services.stripe_service._init_stripe", return_value=True), \
            patch("stripe.Subscription.retrieve", return_value=snapshot), \
            patch("stripe.Invoice.retrieve", return_value=snapshot["latest_invoice"]):
        with factory() as db:
            handle_webhook_event(db, event)
            db.commit()
            assert db.query(Payment).filter_by(status="succeeded").count() == 0


def test_stale_failed_body_records_actual_success_after_retry(billing_case):
    _, factory, principal = billing_case
    from web.services.stripe_service import handle_webhook_event
    from web.database.models import Payment
    snapshot = _case(factory, principal)
    event = _event(snapshot["latest_invoice"], "invoice.payment_failed", modern=False)
    event["data"]["object"].update(status="open", paid=False, amount_paid=0)
    with patch("web.services.stripe_service._init_stripe", return_value=True), \
            patch("stripe.Subscription.retrieve", return_value=snapshot), \
            patch("stripe.Invoice.retrieve", return_value=snapshot["latest_invoice"]):
        with factory() as db:
            result = handle_webhook_event(db, event)
            db.commit()
            assert result == "paid:7900"
            assert db.query(Payment).one().status == "succeeded"


def test_provider_invoice_identity_mismatch_is_retryable_not_paid(billing_case):
    _, factory, principal = billing_case
    from web.services.stripe_service import handle_webhook_event
    from web.database.models import Payment, StripeWebhookEvent
    snapshot = _case(factory, principal)
    current_invoice = deepcopy(snapshot["latest_invoice"])
    current_invoice["id"] = "in_wrong_resource"
    event = _event(snapshot["latest_invoice"], "invoice.payment_succeeded", modern=False)
    with patch("web.services.stripe_service._init_stripe", return_value=True), \
            patch("stripe.Subscription.retrieve", return_value=snapshot), \
            patch("stripe.Invoice.retrieve", return_value=current_invoice):
        with factory() as db:
            with pytest.raises(ValueError, match="[Ii]nvoice"):
                handle_webhook_event(db, event)
            db.rollback()
            assert db.query(Payment).count() == 0
            assert db.query(StripeWebhookEvent).count() == 0


@pytest.mark.parametrize("mutation", ["void", "unpaid", "refunded", "partial_refund",
    "offline", "missing_charge", "wrong_amount", "wrong_currency"])
def test_stale_paid_snapshot_cannot_override_current_unfunded_invoice(billing_case, mutation):
    _, factory, principal = billing_case
    from web.services.stripe_service import handle_webhook_event
    from web.database.models import Payment, Subscription
    snapshot = _case(factory, principal)
    event = _event(snapshot["latest_invoice"])
    actual = deepcopy(snapshot["latest_invoice"])
    if mutation in {"void", "unpaid"}:
        actual.update(status="void" if mutation == "void" else "open", paid=False, amount_paid=0, charge=None)
    elif mutation in {"refunded", "partial_refund"}:
        actual["charge"].update(refunded=mutation == "refunded", amount_refunded=7900 if mutation == "refunded" else 1)
    elif mutation == "offline":
        actual.update(paid_out_of_band=True, charge=None)
    elif mutation == "missing_charge":
        actual["charge"] = None
    elif mutation == "wrong_amount":
        actual["amount_paid"] = 1
    else:
        actual["currency"] = "usd"
    with patch("web.services.stripe_service._init_stripe", return_value=True), \
            patch("stripe.Subscription.retrieve", return_value=snapshot), \
            patch("stripe.Invoice.retrieve", return_value=actual):
        with factory() as db:
            handle_webhook_event(db, event)
            db.commit()
            assert db.query(Payment).filter_by(status="succeeded").count() == 0
            assert db.query(Subscription).filter_by(status="active").count() == 0
    assert _stored_plan(factory, principal["id"]) == "starter"


@pytest.mark.parametrize("mutation", ["customer", "subscription", "mode", "charge_invoice",
    "charge_mode", "event_mode"])
def test_cross_resource_or_mode_evidence_rolls_back_without_acknowledging(billing_case, mutation):
    _, factory, principal = billing_case
    from web.services.stripe_service import handle_webhook_event
    from web.database.models import Payment, StripeWebhookEvent, Subscription
    snapshot = _case(factory, principal)
    event = _event(snapshot["latest_invoice"])
    actual = deepcopy(snapshot["latest_invoice"])
    if mutation in {"customer", "subscription"}:
        actual[mutation] = "cus_other" if mutation == "customer" else "sub_other"
    elif mutation == "mode":
        actual["livemode"] = True
    elif mutation.startswith("charge_"):
        actual["charge"]["invoice" if mutation == "charge_invoice" else "livemode"] = "in_other" if mutation == "charge_invoice" else True
    else:
        event["livemode"] = True
    with patch("web.services.stripe_service._init_stripe", return_value=True), \
            patch("stripe.Subscription.retrieve", return_value=snapshot), \
            patch("stripe.Invoice.retrieve", return_value=actual):
        with factory() as db:
            with pytest.raises(ValueError):
                handle_webhook_event(db, event)
            db.rollback()
            assert db.query(Payment).count() == 0
            assert db.query(StripeWebhookEvent).count() == 0
            assert db.query(Subscription).count() == 0


@pytest.mark.parametrize("read_number", [1, 2, 3])
def test_invoice_read_failure_preserves_retry_and_later_exactly_one_payment(billing_case, read_number):
    _, factory, principal = billing_case
    from web.services.stripe_service import handle_webhook_event
    from web.database.models import Payment, StripeWebhookEvent, Subscription
    snapshot = _case(factory, principal)
    event = _event(snapshot["latest_invoice"])
    replies = [snapshot["latest_invoice"]] * (read_number - 1) + [TimeoutError("synthetic provider timeout")]
    with patch("web.services.stripe_service._init_stripe", return_value=True), \
            patch("stripe.Subscription.retrieve", return_value=snapshot), \
            patch("stripe.Invoice.retrieve", side_effect=replies):
        with factory() as db:
            with pytest.raises(TimeoutError):
                handle_webhook_event(db, event)
            db.rollback()
            assert db.query(Payment).count() == 0
            assert db.query(StripeWebhookEvent).count() == 0
            assert db.query(Subscription).count() == 0
    with patch("web.services.stripe_service._init_stripe", return_value=True), \
            patch("stripe.Subscription.retrieve", return_value=snapshot), \
            patch("stripe.Invoice.retrieve", return_value=snapshot["latest_invoice"]):
        with factory() as db:
            assert handle_webhook_event(db, event) == "paid:7900"
            db.commit()
        with factory() as db:
            assert handle_webhook_event(db, event) == "duplicate:invoice.paid"
            db.commit()
            assert db.query(Payment).count() == 1
            assert db.query(StripeWebhookEvent).count() == 1


def test_invoice_payment_object_is_not_an_invoice_alias(billing_case):
    _, factory, _ = billing_case
    from web.services.stripe_service import handle_webhook_event
    from web.database.models import Payment, Subscription
    event = {"id": "evt_invoice_payment", "type": "invoice_payment.paid", "livemode": False,
             "data": {"object": {"id": "inpay_test", "object": "invoice_payment", "invoice": "in_current"}}}
    with patch("web.services.stripe_service._init_stripe", return_value=True), \
            patch("stripe.Invoice.retrieve") as invoice_get:
        with factory() as db:
            assert handle_webhook_event(db, event) == "ignored:invoice_payment.paid"
            db.commit()
            assert db.query(Payment).count() == db.query(Subscription).count() == 0
        invoice_get.assert_not_called()


@pytest.mark.parametrize("path", ["/api/billing/webhook", "/api/pagos/stripe/webhook"])
def test_http_invoice_timeout_is_retryable_then_recovered_and_duplicate(billing_case, path):
    _, factory, principal = billing_case
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from web.routes.billing import router as billing_router
    from api.routes.pagos import router as legacy_router
    from web.database.models import Payment, StripeWebhookEvent, Subscription
    snapshot = _case(factory, principal)
    event = _event(snapshot["latest_invoice"])
    app = FastAPI()
    app.include_router(billing_router, prefix="/api")
    app.include_router(legacy_router, prefix="/api")
    with TestClient(app) as client, \
            patch("web.services.stripe_service.verify_webhook", return_value=event), \
            patch("web.services.stripe_service._init_stripe", return_value=True), \
            patch("stripe.Subscription.retrieve", return_value=snapshot):
        with patch("stripe.Invoice.retrieve", side_effect=TimeoutError("synthetic-private-provider-marker")):
            response = client.post(path, content=b'{"synthetic":"event"}')
        assert response.status_code == 503
        assert "synthetic-private-provider-marker" not in response.text
        with factory() as db:
            assert db.query(Payment).count() == db.query(StripeWebhookEvent).count() == db.query(Subscription).count() == 0
        with patch("stripe.Invoice.retrieve", return_value=snapshot["latest_invoice"]):
            assert client.post(path, content=b'{"synthetic":"event"}').json()["result"] == "paid:7900"
            response = client.post(path, content=b'{"synthetic":"event"}')
            assert response.status_code == 200
            assert response.json()["result"] == "duplicate:invoice.paid"
        with factory() as db:
            assert db.query(Payment).count() == db.query(StripeWebhookEvent).count() == 1


@pytest.mark.parametrize("event_type,current_status", [
    ("customer.subscription.updated", "past_due"),
    ("customer.subscription.deleted", "canceled"),
    ("charge.refunded", "unpaid"),
    ("charge.refunded", "active"),
])
def test_configured_lifecycle_events_use_current_provider_state(billing_case, event_type, current_status):
    _, factory, principal = billing_case
    from web.services.stripe_service import handle_webhook_event, reconcile_subscription
    from web.database.models import Subscription
    snapshot = _case(factory, principal)
    with patch("stripe.Subscription.retrieve", return_value=snapshot):
        with factory() as db:
            reconcile_subscription(db, "sub_person", principal["id"])
            db.commit()
    if event_type == "charge.refunded":
        body = {"id": "ch_old", "customer": "cus_person", "refunded": True}
        if current_status == "unpaid":
            snapshot["latest_invoice"]["charge"].update(refunded=True, amount_refunded=7900)
    else:
        body = {"id": "sub_person", "status": "active"}
        snapshot["status"] = current_status
    event = {"id": "evt_lifecycle", "type": event_type, "livemode": False, "data": {"object": body}}
    with patch("web.services.stripe_service._init_stripe", return_value=True), \
            patch("stripe.Subscription.retrieve", return_value=snapshot):
        with factory() as db:
            handle_webhook_event(db, event)
            db.commit()
            assert db.query(Subscription).one().status == current_status
    assert _stored_plan(factory, principal["id"]) == ("pro" if current_status == "active" else "starter")

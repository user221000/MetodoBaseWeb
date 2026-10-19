"""Billing regressions using persisted synthetic accounts and offline providers.

These tests exercise the SaaS routers and real SQLAlchemy persistence. Provider
replies are boundary doubles; they do not claim a completed sandbox purchase.
"""
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def billing_case(monkeypatch):
    """Own every connection and dependency; never use the configured database."""
    from web.auth_deps import get_usuario_actual
    from web.database import engine as engine_module
    from web.database.models import Base, Cliente, Usuario, UserRole
    from web.routes import usuario

    engine = create_engine("sqlite://", poolclass=StaticPool,
                           connect_args={"check_same_thread": False})
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(engine_module, "_engine", engine)
    monkeypatch.setattr(engine_module, "_SessionLocal", factory)
    Base.metadata.create_all(engine)
    principal = {"id": "billing-person", "email": "person@example.invalid",
                 "nombre": "Synthetic", "apellido": "Person", "tipo": "usuario",
                 "role": "owner", "team_gym_id": None}
    with factory() as db:
        db.add(Usuario(id=principal["id"], email=principal["email"],
                       password_hash="unused-offline", nombre="Synthetic",
                       tipo="usuario", role=UserRole.OWNER, activo=True))
        db.add(Cliente(id_cliente="billing-profile", gym_id=principal["id"],
                       nombre="Synthetic Person", edad=30, peso_kg=75,
                       estatura_cm=175, objetivo="mantenimiento",
                       nivel_actividad="moderada", sexo="M"))
        db.commit()
    app = FastAPI()
    app.include_router(usuario.router, prefix="/api")
    app.dependency_overrides[get_usuario_actual] = lambda: dict(principal)
    with TestClient(app) as client:
        yield client, factory, principal
    engine.dispose()


def _stored_plan(factory, subject):
    from web.database.models import UserSubscription
    with factory() as db:
        sub = db.query(UserSubscription).filter_by(user_id=subject).first()
        return sub.plan if sub else "starter"


def test_preferences_cannot_grant_pro(billing_case):
    client, factory, principal = billing_case
    response = client.post("/api/usuario/suscripcion", json={"plan": "pro"})
    assert response.status_code == 409
    assert _stored_plan(factory, principal["id"]) == "starter"


def test_incomplete_subscription_cannot_grant_pro(billing_case):
    client, factory, principal = billing_case
    with patch("web.services.stripe_service.create_subscription_with_payment_method",
               return_value={"subscription_id": "sub_unpaid", "status": "incomplete",
                             "client_secret": "test-only"}):
        response = client.post("/api/usuario/stripe-subscribe",
                               json={"plan": "pro", "payment_method_id": "pm_test"})
    assert response.status_code == 200
    assert _stored_plan(factory, principal["id"]) == "starter"


def test_unconfirmed_subscription_cannot_grant_pro(billing_case):
    client, factory, principal = billing_case
    with patch("web.services.stripe_service.confirm_subscription",
               return_value={"activated": False, "status": "incomplete"}):
        response = client.post("/api/usuario/confirm-subscription",
                               json={"subscription_id": "sub_unpaid"})
    assert response.status_code == 200
    assert _stored_plan(factory, principal["id"]) == "starter"


def test_paid_individual_subscription_fits_schema_and_updates_projection(billing_case):
    _, factory, principal = billing_case
    from web.database.models import UserSubscription
    from web.services.subscription_service import activate_subscription
    with factory() as db:
        activate_subscription(db, principal["id"], "pro_usuario",
                              stripe_customer_id="cus_person",
                              stripe_subscription_id="sub_person")
        db.commit()
        projection = db.query(UserSubscription).filter_by(user_id=principal["id"]).one()
        assert projection.plan == "pro"
        assert projection.max_planes_mes == 5


def test_independent_mercadopago_subscriptions_do_not_collide(billing_case):
    _, factory, principal = billing_case
    from web.database.models import Usuario, UserRole
    from web.services.subscription_service import activate_subscription
    with factory() as db:
        db.add(Usuario(id="second-gym", email="second@example.invalid",
                       password_hash="unused-offline", nombre="Second Gym",
                       tipo="gym", role=UserRole.OWNER, activo=True))
        db.commit()
        first = activate_subscription(db, principal["id"], "standard", provider="mercadopago")
        second = activate_subscription(db, "second-gym", "standard", provider="mercadopago")
        db.commit()
        assert first.stripe_subscription_id is None
        assert second.stripe_subscription_id is None


def test_exhausted_individual_quota_never_calls_generator(billing_case):
    client, factory, principal = billing_case
    from web.database.models import UserSubscription
    with factory() as db:
        db.add(UserSubscription(user_id=principal["id"], plan="starter",
                                max_planes_mes=1, planes_usados_mes=1,
                                mes_actual=datetime.now(timezone.utc).strftime("%Y-%m")))
        db.commit()
    with patch("web.routes.planes._generar_plan_sync", return_value={"plan": {}}) as generate:
        response = client.post("/api/usuario/generar-plan")
    assert response.status_code == 403
    generate.assert_not_called()


def test_unpaid_checkout_never_activates_rights(billing_case):
    _, factory, principal = billing_case
    from web.database.models import Subscription
    from web.services.stripe_service import _on_checkout_completed
    with factory() as db:
        result = _on_checkout_completed(db, {
            "id": "cs_unpaid", "payment_status": "unpaid", "status": "complete",
            "metadata": {"gym_id": principal["id"], "plan": "pro_usuario"},
            "customer": "cus_person", "subscription": "sub_person"})
        db.commit()
        assert db.query(Subscription).count() == 0
        assert "pending" in result


def test_unknown_paid_plan_is_rejected(billing_case):
    _, factory, principal = billing_case
    from web.services.subscription_service import activate_subscription
    with factory() as db, pytest.raises(ValueError):
        activate_subscription(db, principal["id"], "unknown_plan")


def _paid_snapshot(factory, principal):
    from web.services.billing_integrity import prepare_purchase
    with factory() as db:
        intent = prepare_purchase(db, principal["id"], "stripe", "elements", "pro_usuario", "purchase-one")
        intent_id = intent.id
    now = datetime.now(timezone.utc).timestamp()
    return {"id": "sub_person", "status": "active", "customer": "cus_person",
            "metadata": {"gym_id": principal["id"], "plan": "pro_usuario", "purchase_intent_id": intent_id},
            "current_period_start": int(now - 60), "current_period_end": int(now + 86400 * 30),
            "items": {"data": [{"quantity": 1, "price": {"unit_amount": 7900, "currency": "mxn",
                        "recurring": {"interval": "month", "interval_count": 1}}}]},
            "latest_invoice": {"id": "in_current", "status": "paid", "paid": True,
                               "amount_paid": 7900, "currency": "mxn",
                               "charge": {"id": "ch_current", "refunded": False, "paid": True,
                                          "captured": True, "amount_refunded": 0, "amount": 7900,
                                          "currency": "mxn", "customer": "cus_person"}}}


def test_confirm_paid_snapshot_then_cancellation_updates_both_tables(billing_case):
    _, factory, principal = billing_case
    from web.services.stripe_service import confirm_subscription, _on_subscription_deleted
    from web.database.models import Subscription
    snapshot = _paid_snapshot(factory, principal)
    with patch("web.services.stripe_service._init_stripe", return_value=True), \
            patch("stripe.Subscription.retrieve", return_value=snapshot):
        with factory() as db:
            assert confirm_subscription(db, principal["id"], "sub_person")["activated"] is True
            db.commit()
        assert _stored_plan(factory, principal["id"]) == "pro"
        snapshot["status"] = "canceled"
        with factory() as db:
            assert _on_subscription_deleted(db, {"id": "sub_person"}) == "canceled"
            db.commit()
            assert db.query(Subscription).one().status == "canceled"
        assert _stored_plan(factory, principal["id"]) == "starter"


@pytest.mark.parametrize("mutation", ["incomplete", "unpaid_invoice", "wrong_price", "wrong_currency", "refunded"])
def test_provider_evidence_never_grants_unpaid_or_wrong_product(billing_case, mutation):
    _, factory, principal = billing_case
    from web.services.stripe_service import confirm_subscription
    snapshot = _paid_snapshot(factory, principal)
    if mutation == "incomplete":
        snapshot["status"] = "incomplete"
    elif mutation == "unpaid_invoice":
        snapshot["latest_invoice"].update(paid=False, status="open")
    elif mutation == "wrong_price":
        snapshot["items"]["data"][0]["price"]["unit_amount"] = 1
    elif mutation == "wrong_currency":
        snapshot["items"]["data"][0]["price"]["currency"] = "usd"
    else:
        snapshot["latest_invoice"]["charge"]["refunded"] = True
    with patch("web.services.stripe_service._init_stripe", return_value=True), \
            patch("stripe.Subscription.retrieve", return_value=snapshot):
        with factory() as db:
            if mutation in ("wrong_price", "wrong_currency"):
                with pytest.raises(ValueError):
                    confirm_subscription(db, principal["id"], "sub_person")
            else:
                assert confirm_subscription(db, principal["id"], "sub_person")["activated"] is False
                db.commit()
    assert _stored_plan(factory, principal["id"]) == "starter"


def test_cannot_confirm_another_subject_purchase(billing_case):
    _, factory, principal = billing_case
    from web.services.stripe_service import reconcile_subscription
    snapshot = _paid_snapshot(factory, principal)
    with patch("stripe.Subscription.retrieve", return_value=snapshot):
        with factory() as db, pytest.raises(ValueError):
            reconcile_subscription(db, "sub_person", "other-person")
    assert _stored_plan(factory, principal["id"]) == "starter"


def test_old_active_event_after_cancellation_uses_current_provider_state(billing_case):
    _, factory, principal = billing_case
    from web.services.stripe_service import reconcile_subscription, handle_webhook_event
    snapshot = _paid_snapshot(factory, principal)
    with patch("stripe.Subscription.retrieve", return_value=snapshot):
        with factory() as db:
            reconcile_subscription(db, "sub_person", principal["id"])
            db.commit()
        snapshot["status"] = "canceled"
        event = {"id": "evt_old_active", "type": "customer.subscription.updated",
                 "data": {"object": {"id": "sub_person", "status": "active"}}}
        with factory() as db:
            assert handle_webhook_event(db, event) == "updated:canceled"
            db.commit()
            assert "duplicate" in handle_webhook_event(db, event)
    assert _stored_plan(factory, principal["id"]) == "starter"


def test_failed_generation_returns_credit_once(billing_case):
    client, factory, principal = billing_case
    from web.database.models import UserSubscription, GenerationReservation
    with patch("web.routes.planes._generar_plan_sync", side_effect=RuntimeError("offline PDF failure")):
        response = client.post("/api/usuario/generar-plan", headers={"Idempotency-Key": "generation-failure"})
    assert response.status_code == 500
    with factory() as db:
        assert db.query(UserSubscription).one().planes_usados_mes == 0
        assert db.query(GenerationReservation).one().status == "released"
    repeated = client.post("/api/usuario/generar-plan", headers={"Idempotency-Key": "generation-failure"})
    assert repeated.status_code == 409
    with factory() as db:
        assert db.query(UserSubscription).one().planes_usados_mes == 0


def test_completed_retry_returns_same_plan_without_generation(billing_case):
    client, factory, principal = billing_case
    from web.database.models import PlanGenerado, UserSubscription
    calls = []
    def generate(*args):
        with factory() as db:
            plan = PlanGenerado(gym_id=principal["id"], id_cliente="billing-profile",
                                plan_json='{"desayuno":{"kcal_objetivo":400}}', kcal_objetivo=1600)
            db.add(plan)
            db.commit()
            calls.append(plan.id)
            return {"plan_id": plan.id, "plan": {}}
    with patch("web.routes.planes._generar_plan_sync", side_effect=generate):
        first = client.post("/api/usuario/generar-plan", headers={"Idempotency-Key": "generation-success"})
        second = client.post("/api/usuario/generar-plan", headers={"Idempotency-Key": "generation-success"})
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert len(calls) == 1
    with factory() as db:
        assert db.query(UserSubscription).one().planes_usados_mes == 1
        assert db.query(PlanGenerado).count() == 1


def test_quota_month_is_mexico_city_not_utc():
    from web.services.billing_integrity import current_quota_period
    assert current_quota_period(datetime(2026, 11, 1, 2, tzinfo=timezone.utc)) == "2026-10"


@pytest.mark.parametrize("change", ["different_id", "expired", "signature"])
def test_mp_signature_binds_body_query_and_time(monkeypatch, change):
    import hashlib
    import hmac
    import json
    from starlette.requests import Request
    from types import SimpleNamespace
    from fastapi import HTTPException
    from web.services.mercadopago_service import verify_notification
    secret = "synthetic-webhook-secret"
    monkeypatch.setattr("web.services.mercadopago_service.get_settings", lambda: SimpleNamespace(MERCADOPAGO_WEBHOOK_SECRET=secret))
    stamp = "1700000000"
    manifest = f"id:123;request-id:request-test;ts:{stamp};"
    signature = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    if change == "signature":
        signature = "0" * 64
    request = Request({"type": "http", "method": "POST", "path": "/webhook", "query_string": b"data.id=123",
                       "headers": [(b"x-signature", f"ts={stamp},v1={signature}".encode()), (b"x-request-id", b"request-test")]})
    body = json.dumps({"id": "event-test", "type": "payment", "data": {"id": "456" if change == "different_id" else "123"}}).encode()
    with pytest.raises(HTTPException) as exc:
        verify_notification(request, body, now=1700000400 if change == "expired" else 1700000000)
    assert exc.value.status_code == 401


def test_mp_approved_payment_then_refund_reconciles_projection(billing_case):
    _, factory, principal = billing_case
    from unittest.mock import MagicMock
    from web.services.billing_integrity import prepare_purchase
    from web.services.mercadopago_service import reconcile_payment
    with factory() as db:
        intent = prepare_purchase(db, principal["id"], "mercadopago", "preference", "pro_usuario", "mp-purchase")
        intent_id = intent.id
    payment = {"id": "123", "external_reference": intent_id, "metadata": {"purchase_intent_id": intent_id},
               "status": "approved", "currency_id": "MXN", "transaction_amount": 79,
               "date_approved": datetime.now(timezone.utc).isoformat()}
    sdk = MagicMock()
    sdk.payment.return_value.get.return_value = {"status": 200, "response": payment}
    with factory() as db:
        assert reconcile_payment(db, "123", sdk) == "activated"
        db.commit()
        assert reconcile_payment(db, "123", sdk) == "already_processed"
    assert _stored_plan(factory, principal["id"]) == "pro"
    payment["status"] = "refunded"
    with factory() as db:
        assert reconcile_payment(db, "123", sdk) == "reversed"
        db.commit()
    assert _stored_plan(factory, principal["id"]) == "starter"


@pytest.mark.parametrize("evidence", [None, {}, {"id": "ch_current"}])
def test_invoice_without_verified_charge_does_not_grant_access(billing_case, evidence):
    _, factory, principal = billing_case
    from web.services.stripe_service import reconcile_subscription
    snapshot = _paid_snapshot(factory, principal)
    snapshot["latest_invoice"]["charge"] = evidence
    with patch("stripe.Subscription.retrieve", return_value=snapshot):
        with factory() as db:
            assert reconcile_subscription(db, "sub_person", principal["id"])["activated"] is False
            db.commit()
    assert _stored_plan(factory, principal["id"]) == "starter"


def test_unexpanded_charge_is_retrieved_and_refund_is_checked(billing_case):
    _, factory, principal = billing_case
    from web.services.stripe_service import reconcile_subscription
    snapshot = _paid_snapshot(factory, principal)
    evidence = dict(snapshot["latest_invoice"]["charge"])
    evidence["refunded"] = True
    evidence["amount_refunded"] = 7900
    snapshot["latest_invoice"]["charge"] = "ch_current"
    with patch("stripe.Subscription.retrieve", return_value=snapshot), \
            patch("stripe.Charge.retrieve", return_value=evidence) as retrieve:
        with factory() as db:
            assert reconcile_subscription(db, "sub_person", principal["id"])["activated"] is False
            db.commit()
        retrieve.assert_called_once_with("ch_current")
    assert _stored_plan(factory, principal["id"]) == "starter"


def test_old_refund_after_renewal_preserves_current_paid_access(billing_case):
    _, factory, principal = billing_case
    from web.services.stripe_service import reconcile_subscription, _on_charge_refunded
    snapshot = _paid_snapshot(factory, principal)
    with patch("stripe.Subscription.retrieve", return_value=snapshot):
        with factory() as db:
            reconcile_subscription(db, "sub_person", principal["id"])
            db.commit()
        with factory() as db:
            assert _on_charge_refunded(db, {"id": "ch_old", "customer": "cus_person", "refunded": True}) == "refund:reconciled"
            db.commit()
    assert _stored_plan(factory, principal["id"]) == "pro"


def test_old_mp_approval_after_new_purchase_preserves_new_period(billing_case):
    _, factory, principal = billing_case
    from unittest.mock import MagicMock
    from web.services.billing_integrity import prepare_purchase
    from web.services.mercadopago_service import reconcile_payment
    from web.database.models import Subscription, Payment
    with factory() as db:
        old = prepare_purchase(db, principal["id"], "mercadopago", "preference", "pro_usuario", "old-purchase")
        newer = prepare_purchase(db, principal["id"], "mercadopago", "preference", "pro_usuario", "new-purchase")
        old_id, new_id = old.id, newer.id
    payment = {"id": "222", "external_reference": new_id, "metadata": {"purchase_intent_id": new_id},
               "status": "approved", "currency_id": "MXN", "transaction_amount": 79,
               "date_approved": datetime.now(timezone.utc).isoformat()}
    sdk = MagicMock()
    sdk.payment.return_value.get.return_value = {"status": 200, "response": payment}
    with factory() as db:
        assert reconcile_payment(db, "222", sdk) == "activated"
        db.commit()
        current_end = db.query(Subscription).one().current_period_end
    payment.update(id="111", external_reference=old_id, metadata={"purchase_intent_id": old_id}, date_approved="2026-01-01T12:00:00+00:00")
    with factory() as db:
        assert reconcile_payment(db, "111", sdk) == "superseded"
        db.commit()
        sub = db.query(Subscription).one()
        assert sub.provider_payment_id == "222"
        assert sub.current_period_end == current_end
        assert db.query(Payment).count() == 2
    assert _stored_plan(factory, principal["id"]) == "pro"


def test_professional_keeps_separate_personal_profile(billing_case):
    client, _, principal = billing_case
    # The presentation principal has a professional context, while personal
    # profile queries continue to use its own user.id, never the team's gym.id.
    principal["team_gym_id"] = "professional-gym"
    response = client.get("/api/usuario/perfil")
    assert response.status_code == 200
    assert response.json()["peso_kg"] == 75
    response = client.put("/api/usuario/perfil", json={"peso_kg": 76})
    assert response.status_code == 200
    assert client.get("/api/usuario/perfil").json()["peso_kg"] == 76


def test_provider_error_is_redacted_from_public_response_and_logs(billing_case, caplog):
    client, _, _ = billing_case
    sentinel = "synthetic-sensitive-provider-error-token-and-health-note"
    with patch("web.services.stripe_service.create_subscription_with_payment_method",
               side_effect=Exception(sentinel)):
        response = client.post("/api/usuario/stripe-subscribe",
                               json={"plan": "pro", "payment_method_id": "pm_test"})
    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "payment_service_unavailable"
    assert response.json()["detail"]["request_id"]
    assert sentinel not in response.text
    assert sentinel not in caplog.text


@pytest.mark.parametrize("mp_configured", [False, True])
def test_missing_stripe_key_never_grants_unpaid_gym_premium(billing_case, monkeypatch, mp_configured):
    _, factory, principal = billing_case
    from types import SimpleNamespace
    from web.subscription_guard import require_active_subscription, _get_gym_plan
    monkeypatch.setattr("web.settings.get_settings", lambda: SimpleNamespace(
        STRIPE_SECRET_KEY="", MERCADOPAGO_ACCESS_TOKEN="synthetic-mp" if mp_configured else ""))
    with factory() as db:
        user = require_active_subscription(db, dict(principal))
        assert user["subscription"]["plan"] == "free"
        assert user["subscription"]["max_clientes"] == 10
        assert _get_gym_plan(db, principal["id"]) == "free"


def test_mercadopago_rights_use_persisted_period_without_stripe(billing_case, monkeypatch):
    _, factory, principal = billing_case
    from datetime import timedelta
    from types import SimpleNamespace
    from web.services.subscription_service import activate_subscription
    from web.subscription_guard import require_active_subscription, _get_gym_plan
    monkeypatch.setattr("web.settings.get_settings", lambda: SimpleNamespace(STRIPE_SECRET_KEY="", MERCADOPAGO_ACCESS_TOKEN="synthetic-mp"))
    with factory() as db:
        sub = activate_subscription(db, principal["id"], "standard", provider="mercadopago",
                                    current_period_end=datetime.now(timezone.utc) + timedelta(days=1))
        db.commit()
        assert require_active_subscription(db, dict(principal))["subscription"]["plan"] == "standard"
        sub.current_period_end = datetime.now(timezone.utc) - timedelta(days=1)
        db.commit()
        assert _get_gym_plan(db, principal["id"]) == "free"


def test_expired_individual_canonical_period_removes_pro_projection(billing_case):
    _, factory, principal = billing_case
    from datetime import timedelta
    from web.services.subscription_service import activate_subscription
    from web.services.billing_integrity import get_individual_subscription
    with factory() as db:
        activate_subscription(db, principal["id"], "pro_usuario", stripe_subscription_id="sub_person",
                              current_period_end=datetime.now(timezone.utc) - timedelta(seconds=1))
        db.commit()
        projection = get_individual_subscription(db, principal["id"])
        assert projection.plan == "starter"
        assert projection.max_planes_mes == 1


def test_resilience_never_logs_provider_exception_text(caplog):
    from web.services.resilience import retry_with_backoff, CircuitBreaker, CircuitBreakerConfig
    sentinel = "sensitive-provider-token-in-exception"
    @retry_with_backoff(max_retries=1, initial_delay=0, jitter=0)
    def failing_provider():
        raise ConnectionError(sentinel)
    with pytest.raises(ConnectionError):
        failing_provider()
    circuit = CircuitBreaker("synthetic-test", CircuitBreakerConfig(failure_threshold=1))
    with pytest.raises(ConnectionError):
        circuit.call(lambda: (_ for _ in ()).throw(ConnectionError(sentinel)))
    assert "ConnectionError" in caplog.text
    assert sentinel not in caplog.text


def test_purchase_identity_is_durable_and_request_key_scoped(billing_case):
    _, factory, principal = billing_case
    from web.services.billing_integrity import prepare_purchase
    from web.database.models import PurchaseIntent
    with factory() as db:
        first = prepare_purchase(db, principal["id"], "stripe", "elements", "pro_usuario", "client-purchase")
        first_id = first.id
    with factory() as db:
        second = prepare_purchase(db, principal["id"], "stripe", "elements", "pro_usuario", "client-purchase")
        assert second.id == first_id
        assert db.query(PurchaseIntent).count() == 1
        with pytest.raises(ValueError):
            prepare_purchase(db, principal["id"], "stripe", "elements", "standard", "client-purchase")


def test_stale_mapping_before_lock_cannot_cancel_new_purchase(billing_case, monkeypatch):
    _, factory, principal = billing_case
    from sqlalchemy import update
    from sqlalchemy.orm import Query
    from web.database.models import Subscription, PurchaseIntent, Usuario
    from web.services.stripe_service import reconcile_subscription
    snapshot = _paid_snapshot(factory, principal)
    with patch("stripe.Subscription.retrieve", return_value=snapshot):
        with factory() as db:
            reconcile_subscription(db, "sub_person", principal["id"])
            db.commit()
    snapshot["status"] = "canceled"
    original_update = Query.update
    interleaved = False
    def install_new_mapping_after_old_mapping_loaded(query, *args, **kwargs):
        nonlocal interleaved
        result = original_update(query, *args, **kwargs)
        if query.column_descriptions[0].get("entity") is Usuario and not interleaved:
            interleaved = True
            # Reproduce a changed DB row while the earlier loaded ORM object
            # remains stale, as when another process committed during lock wait.
            query.session.execute(update(Subscription).where(Subscription.gym_id == principal["id"]).values(
                stripe_subscription_id="sub_newer", status="active"), execution_options={"synchronize_session": False})
            query.session.add(PurchaseIntent(subject_id=principal["id"], provider="stripe", operation="elements",
                request_key="newer-purchase", plan="pro_usuario", amount_cents=7900, currency="mxn",
                status="confirmed", provider_reference_id="sub_newer"))
            query.session.flush()
        return result
    monkeypatch.setattr(Query, "update", install_new_mapping_after_old_mapping_loaded)
    with patch("stripe.Subscription.retrieve", return_value=snapshot):
        with factory() as db:
            result = reconcile_subscription(db, "sub_person", principal["id"])
            db.commit()
            current = db.query(Subscription).one()
            assert current.stripe_subscription_id == "sub_newer"
            assert current.status == "active"
            assert result["status"] == "superseded"
    assert interleaved
    assert _stored_plan(factory, principal["id"]) == "pro"


def test_old_stripe_cancellation_cannot_revoke_current_mp_purchase(billing_case):
    _, factory, principal = billing_case
    from web.database.models import Subscription
    from web.services.subscription_service import activate_subscription
    from web.services.stripe_service import reconcile_subscription
    snapshot = _paid_snapshot(factory, principal)
    with patch("stripe.Subscription.retrieve", return_value=snapshot):
        with factory() as db:
            reconcile_subscription(db, "sub_person", principal["id"])
            db.commit()
        with factory() as db:
            current = activate_subscription(db, principal["id"], "pro_usuario", provider="mercadopago")
            current.provider_payment_id = "mp-current"
            db.commit()
            assert current.stripe_subscription_id is None
            assert current.stripe_customer_id is None
        snapshot["status"] = "canceled"
        with factory() as db:
            result = reconcile_subscription(db, "sub_person", principal["id"])
            db.commit()
            current = db.query(Subscription).one()
            assert result["status"] == "superseded"
            assert current.provider == "mercadopago"
            assert current.status == "active"
            assert current.provider_payment_id == "mp-current"
    assert _stored_plan(factory, principal["id"]) == "pro"

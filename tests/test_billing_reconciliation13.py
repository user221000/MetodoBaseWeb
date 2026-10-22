"""Lost-callback repair and operator limits using current37 SQLite only."""
import json
import uuid
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import event, select
from sqlalchemy.orm import Session, sessionmaker

from tests import account_security37_fixtures
from web.database.models import (
    Payment,
    ProviderSubjectAssociation,
    PurchaseIntent,
    Subscription,
    UserRole,
    UserSubscription,
    Usuario,
)
from web.database.tenant_context import current_tenant
from web.services import billing_reconciliation as service
from web.services.billing_integrity import current_quota_period, price_in_cents
from web.services.billing_reconciliation_providers import (
    ReadBudget,
    ReadOnlyProviders,
    RetryableRead,
)

account37_engine = account_security37_fixtures.account37_engine


@pytest.fixture
def billing_case(account37_engine):
    subject, foreign, intent = (str(uuid.uuid4()) for _ in range(3))
    factory = sessionmaker(bind=account37_engine, expire_on_commit=True, autoflush=False)
    amount = price_in_cents("pro_usuario")
    with factory() as db:
        for identity in (subject, foreign):
            db.add(Usuario(id=identity, email=uuid.uuid4().hex + "@example.invalid", nombre="Synthetic B13",
                password_hash="synthetic-not-a-login", tipo="usuario", role=UserRole.VIEWER))
        db.flush()
        db.add(UserSubscription(user_id=subject, plan="starter", status="active", max_planes_mes=1,
            planes_usados_mes=1, mes_actual=current_quota_period()))
        purchase = PurchaseIntent(id=intent, subject_id=subject, provider="stripe", operation="elements", plan="pro_usuario",
            amount_cents=amount, currency="mxn", request_key=uuid.uuid4().hex, status="provider_created",
            provider_reference_id="sub_b13_" + uuid.uuid4().hex, provider_customer_id="cus_b13_" + uuid.uuid4().hex)
        db.add(purchase)
        subscription = Subscription(gym_id=subject, plan="pro_usuario", provider="stripe", status="incomplete",
            stripe_subscription_id=purchase.provider_reference_id, stripe_customer_id=purchase.provider_customer_id)
        db.add(subscription)
        db.flush()
        subscription_id, reference, customer = subscription.id, purchase.provider_reference_id, purchase.provider_customer_id
        db.commit()
    yield SimpleNamespace(engine=account37_engine, factory=factory, subject=subject, foreign=foreign,
        intent=intent, subscription=subscription_id, reference=reference, customer=customer, amount=amount,
        payment=str(int(uuid.uuid4().hex[:12], 16)))


def manifest(case, *, kind="subscription", provider="stripe", subject=None, resource_id=None):
    return json.dumps({"version": 1, "resources": [{"subject_id": subject or case.subject,
        "kind": kind, "provider": provider, "resource_id": resource_id or (case.subscription if kind == "subscription" else case.intent)}]}).encode()


def facts(case):
    with case.factory() as db:
        sub = db.get(Subscription, case.subscription)
        quota = db.scalar(select(UserSubscription).where(UserSubscription.user_id == case.subject))
        intent = db.get(PurchaseIntent, case.intent)
        user = db.get(Usuario, case.subject)
        return {
            "subscription": tuple(getattr(sub, field) for field in ("plan", "status", "provider", "max_clientes", "stripe_subscription_id",
                "stripe_customer_id", "provider_payment_id", "current_period_start", "current_period_end", "cancel_at_period_end")),
            "quota": (quota.plan, quota.status, quota.max_planes_mes, quota.planes_usados_mes, quota.mes_actual),
            "intent": (intent.status, intent.provider_reference_id, intent.provider_customer_id),
            "user": (user.activo, user.tipo, user.role, user.team_gym_id, user.password_hash, user.session_version),
            "payments": tuple(db.execute(select(Payment.id, Payment.amount_cents, Payment.currency, Payment.status,
                Payment.stripe_payment_intent_id).where(Payment.gym_id == case.subject).order_by(Payment.id)).all()),
            "links": tuple(db.execute(select(ProviderSubjectAssociation.provider, ProviderSubjectAssociation.resource_type,
                ProviderSubjectAssociation.resource_id, ProviderSubjectAssociation.subject_id, ProviderSubjectAssociation.provenance,
                ProviderSubjectAssociation.source_ref).where(ProviderSubjectAssociation.subject_id == case.subject)
                .order_by(ProviderSubjectAssociation.provider, ProviderSubjectAssociation.resource_type, ProviderSubjectAssociation.resource_id)).all()),
        }


class ProviderFacts:
    def __init__(self, case):
        from web.constants import PLANES_LICENCIA
        self.calls = []
        self.budget = None
        now = datetime.now(UTC)
        self.subscription_fact = {"id": case.reference, "customer": case.customer, "status": "active",
            "metadata": {"purchase_intent_id": case.intent, "gym_id": case.subject, "plan": "pro_usuario"},
            "items": {"data": [{"quantity": 1, "price": {"id": PLANES_LICENCIA["pro_usuario"].get("stripe_price_id") or "price_synthetic",
                "currency": "mxn", "unit_amount": case.amount, "recurring": {"interval": "month", "interval_count": 1}}}]},
            "latest_invoice": {"paid": True, "currency": "mxn", "amount_paid": case.amount, "charge": "ch_b13"},
            "current_period_start": int(now.timestamp()), "current_period_end": int((now + timedelta(days=30)).timestamp())}
        self.charge_fact = {"id": "ch_b13", "customer": case.customer, "paid": True, "captured": True,
            "refunded": False, "amount_refunded": 0, "currency": "mxn", "amount": case.amount}
        self.checkout_fact = {"id": "cs_b13", "object": "checkout.session", "mode": "subscription", "status": "complete",
            "customer": case.customer, "subscription": case.reference, "metadata": deepcopy(self.subscription_fact["metadata"])}
        self.payment_fact = {"id": int(case.payment), "external_reference": case.intent, "metadata": deepcopy(self.subscription_fact["metadata"]),
            "currency_id": "MXN", "transaction_amount": case.amount / 100, "status": "approved", "date_approved": now.isoformat()}
        self.search_fact = {"status": 200, "response": {"paging": {"total": 1, "offset": 0, "limit": 11},
            "results": [{"id": int(case.payment), "external_reference": case.intent}]}}
        self.failure = None

    def factory(self, budget):
        self.budget = budget
        return self

    def read(self, label, value):
        self.budget.admit_read()
        self.calls.append(label)
        if self.failure:
            raise self.failure
        return deepcopy(value)

    def subscription(self, reference, *, expand):
        return self.read(("subscription", reference), self.subscription_fact)

    def charge(self, reference):
        return self.read(("charge", reference), self.charge_fact)

    def checkout(self, reference):
        return self.read(("checkout", reference), self.checkout_fact)

    def payment(self):
        return self

    def get(self, reference):
        return self.read(("payment", reference), {"status": 200, "response": self.payment_fact})

    def search(self, reference):
        return self.read(("search", reference), self.search_fact)


def apply(case, provider, selection=None, **kwargs):
    return service.run(selection or manifest(case), apply=True, factory=case.factory, reader_factory=provider.factory, **kwargs)


@pytest.mark.parametrize("source", ["stripe_subscription", "stripe_checkout", "mp_subscription", "mp_preference"])
def test_lost_webhook_repairs_then_replay_preserves_business_facts_and_quota(billing_case, source):
    case = billing_case
    provider = ProviderFacts(case)
    is_mp = source.startswith("mp")
    purchase = source in {"stripe_checkout", "mp_preference"}
    with case.factory() as db:
        sub, intent = db.get(Subscription, case.subscription), db.get(PurchaseIntent, case.intent)
        if is_mp:
            sub.provider, sub.provider_payment_id = "mercadopago", case.payment
            sub.stripe_subscription_id = sub.stripe_customer_id = None
            intent.provider, intent.operation, intent.provider_reference_id = "mercadopago", "preference", "pref_b13"
        elif purchase:
            intent.operation, intent.provider_reference_id = "checkout", "cs_b13"
        db.commit()
    selected = manifest(case, provider="mercadopago" if is_mp else "stripe", kind="purchase_intent" if purchase else "subscription")
    before = facts(case)
    result = apply(case, provider, selected)
    assert result["reconciled"] == 1 and result["complete"] and result["next_cursor"] is None
    repaired = facts(case)
    assert repaired["subscription"][1] == "active" and repaired["quota"][:4] == ("pro", "active", 5, 1)
    assert repaired["user"] == before["user"]
    assert len(repaired["payments"]) == int(is_mp)
    assert apply(case, provider, selected)["reconciled"] == 1
    assert facts(case) == repaired  # Existing operational updated_at is deliberately outside business facts.


def test_plan_is_local_readonly_scoped_and_restores_caller_context(billing_case):
    case = billing_case
    observed, writes = [], []
    def witness(connection, cursor, statement, parameters, context, many):
        observed.append(current_tenant.get())
        if statement.lstrip().split()[0].upper() in {"UPDATE", "INSERT", "DELETE", "CREATE", "DROP", "ALTER"}:
            writes.append(True)
    constructed = []
    def factory():
        constructed.append(current_tenant.get())
        return case.factory()
    def forbidden(*args):
        raise AssertionError("Plan constructed an SDK")
    before = facts(case)
    event.listen(case.engine, "before_cursor_execute", witness)
    token = current_tenant.set(case.foreign)
    try:
        result = service.run(manifest(case), factory=factory, reader_factory=forbidden)
        assert current_tenant.get() == case.foreign
    finally:
        current_tenant.reset(token)
        event.remove(case.engine, "before_cursor_execute", witness)
    assert result["planned"] == 1 and result["provider_reads"] == 0 and writes == []
    assert observed and set(observed) == {case.subject}
    assert constructed == [""]
    assert facts(case) == before


@pytest.mark.parametrize("fault", ["foreign_resource", "provider_ref", "foreign_intent", "customer", "unpaid_charge"])
def test_foreign_or_mismatched_truth_cannot_grant_or_adopt(billing_case, fault):
    case = billing_case
    provider = ProviderFacts(case)
    selection = manifest(case)
    if fault == "foreign_resource":
        selection = manifest(case, subject=case.foreign)
    elif fault == "provider_ref":
        provider.subscription_fact["id"] = "sub_foreign"
    elif fault == "foreign_intent":
        provider.subscription_fact["metadata"]["gym_id"] = case.foreign
    elif fault == "customer":
        provider.subscription_fact["customer"] = "cus_foreign"
    else:
        provider.charge_fact["refunded"] = True
        provider.charge_fact["amount_refunded"] = case.amount
    before = facts(case)
    result = apply(case, provider, selection)
    if fault == "unpaid_charge":
        assert result["reconciled"] == 1
        assert facts(case)["subscription"][1] == "unpaid"
        assert facts(case)["quota"][0] == "starter" and facts(case)["quota"][3] == 1
    else:
        assert result["manual"] == 1 and result["reconciled"] == 0
        assert facts(case) == before
    if fault == "foreign_resource":
        assert provider.calls == []


def test_current_cancellation_revokes_projection_without_resetting_usage(billing_case):
    case = billing_case
    provider = ProviderFacts(case)
    assert apply(case, provider)["reconciled"] == 1
    provider.subscription_fact["status"] = "canceled"
    assert apply(case, provider)["reconciled"] == 1
    value = facts(case)
    assert value["subscription"][1] == "canceled" and value["quota"][:4] == ("starter", "canceled", 1, 1)
    assert apply(case, provider)["reconciled"] == 1 and facts(case) == value


@pytest.mark.parametrize("mode", ["provider", "read_budget", "deadline"])
def test_temporary_or_budget_failure_keeps_cursor_without_rights(billing_case, mode):
    case = billing_case
    provider = ProviderFacts(case)
    budget = ReadBudget(max_reads=1) if mode == "read_budget" else None
    if mode == "provider":
        provider.failure = RetryableRead("synthetic private provider failure")
    if mode == "deadline":
        clock = [0.0]
        budget = ReadBudget(seconds=1, clock=lambda: clock[0])
        clock[0] = 2.0
    before = facts(case)
    result = apply(case, provider, budget=budget)
    assert result["reconciled"] == 0 and not result["complete"] and result["next_cursor"]
    assert result["retryable"] + result["deferred"] == 1
    assert facts(case) == before


@pytest.mark.parametrize("fault", ["before_commit", "lost_commit_ack", "rollback", "close"])
def test_uncertain_database_finalization_never_acknowledges_or_advances(billing_case, fault):
    case = billing_case
    provider = ProviderFacts(case)
    class FaultSession(Session):
        def commit(self):
            if fault == "lost_commit_ack":
                super().commit()
                raise ValueError("synthetic lost ACK")
            if fault == "before_commit":
                raise RuntimeError("synthetic before commit")
            return super().commit()
        def rollback(self):
            if fault == "rollback":
                raise RuntimeError("synthetic rollback")
            return super().rollback()
        def close(self):
            if fault == "close":
                super().close()
                raise RuntimeError("synthetic close")
            return super().close()
    if fault == "rollback":
        provider.failure = RetryableRead()
    factory = sessionmaker(bind=case.engine, class_=FaultSession, expire_on_commit=True, autoflush=False)
    before = facts(case)
    result = service.run(manifest(case), apply=True, factory=factory, reader_factory=provider.factory)
    assert result["unconfirmed"] == 1 and result["reconciled"] == 0 and result["next_cursor"] and not result["complete"]
    if fault in {"before_commit", "rollback"}:
        assert facts(case) == before
    else:
        assert facts(case)["subscription"][1] == "active"
    assert current_tenant.get() == ""


@pytest.mark.parametrize("fault", ["many", "two", "wrong_reference", "missing_reference", "empty"])
def test_mp_discovery_is_bounded_strict_and_does_not_guess(billing_case, fault):
    case = billing_case
    provider = ProviderFacts(case)
    with case.factory() as db:
        row = db.get(PurchaseIntent, case.intent)
        row.provider, row.operation, row.provider_reference_id = "mercadopago", "preference", "pref_b13"
        if fault == "missing_reference":
            row.provider_reference_id = None
        db.commit()
    if fault == "many":
        provider.search_fact["response"]["paging"]["total"] = 11
    elif fault == "two":
        provider.search_fact["response"]["paging"]["total"] = 2
        provider.search_fact["response"]["results"].append({"id": int(case.payment) + 1, "external_reference": case.intent})
    elif fault == "wrong_reference":
        provider.search_fact["response"]["results"][0]["external_reference"] = case.foreign
    elif fault == "empty":
        provider.search_fact["response"] = {"paging": {"total": 0, "offset": 0}, "results": []}
    before = facts(case)
    result = apply(case, provider, manifest(case, kind="purchase_intent", provider="mercadopago"))
    assert result["pending"] == int(fault == "empty")
    assert result["manual"] == int(fault != "empty") and result["reconciled"] == 0
    assert facts(case) == before and not any(call[0] == "payment" for call in provider.calls)


def test_manifest_cursor_and_page_budget_do_not_expand_selection(billing_case):
    case = billing_case
    document = json.loads(manifest(case))
    second = {**document["resources"][0], "kind": "purchase_intent", "resource_id": case.intent}
    document["resources"].append(second)
    raw = json.dumps(document).encode()
    first = service.run(raw, factory=case.factory, max_items=1)
    assert first["visited"] == 1 and first["next_cursor"] and not first["complete"]
    second = service.run(raw, factory=case.factory, max_items=1, cursor=first["next_cursor"])
    assert second["visited"] == 1 and second["complete"]
    with pytest.raises(ValueError):
        service.run(manifest(case), factory=lambda: pytest.fail("Invalid cursor opened a Session"), cursor=first["next_cursor"])
    with pytest.raises(ValueError):
        service.run(raw, max_items=101, factory=lambda: pytest.fail("Invalid budget opened a Session"))


@pytest.mark.parametrize("raw", [b"[]", b'{"version":1,"version":1,"resources":[]}', b"x" * 65537,
    b'{"version":true,"resources":[]}', b'{"version":1,"resources":[null]}'],
    ids=["array", "duplicate", "oversized", "boolean-version", "null-resource"])
def test_closed_manifest_rejects_before_database_or_provider(raw):
    with pytest.raises(ValueError):
        service.run(raw, factory=lambda: pytest.fail("Invalid selection opened a Session"),
            reader_factory=lambda _: pytest.fail("Invalid selection constructed a provider"))


def test_sdk_capabilities_use_per_call_timeouts_zero_retries_and_leave_globals(monkeypatch):
    import mercadopago
    import stripe
    calls, transports, options = [], [], []
    globals_before = (stripe.api_key, stripe.max_network_retries, stripe.default_http_client)
    class Transport:
        def __init__(self, *, timeout):
            self.timeout, self.closed = timeout, False
            transports.append(self)
        def close(self):
            self.closed = True
    class StripeResource:
        def retrieve(self, reference, params, *, options):
            calls.append(("stripe", reference, params, options))
            return {"id": reference}
    def stripe_client(key, **kwargs):
        assert kwargs["max_network_retries"] == 0 and kwargs["stripe_version"] == "2024-06-20"
        return SimpleNamespace(subscriptions=StripeResource(), charges=StripeResource(),
            checkout=SimpleNamespace(sessions=StripeResource()))
    class MpPayment:
        def get(self, reference, *, request_options):
            options.append(request_options)
            return {"status": 200, "response": {"id": reference}}
        def search(self, filters, *, request_options):
            assert filters == {"external_reference": "synthetic-intent", "limit": 11, "offset": 0}
            options.append(request_options)
            return {"status": 200, "response": {"results": []}}
    def mp_client(key, *, request_options):
        assert request_options.max_retries == 0 and 0 < request_options.connection_timeout <= 5
        return SimpleNamespace(payment=lambda: MpPayment())
    monkeypatch.setattr(stripe.http_client, "RequestsClient", Transport)
    monkeypatch.setattr(stripe, "StripeClient", stripe_client)
    monkeypatch.setattr(mercadopago, "SDK", mp_client)
    reader = ReadOnlyProviders(ReadBudget(), SimpleNamespace(STRIPE_SECRET_KEY="synthetic-no-send", MERCADOPAGO_ACCESS_TOKEN="synthetic-no-send"))
    reader.subscription("sub_synthetic", expand=["latest_invoice.charge"])
    reader.charge("ch_synthetic")
    reader.checkout("cs_synthetic")
    reader.get("10001")
    reader.search("synthetic-intent")
    assert len(transports) == 3 and all(item.closed and 0 < item.timeout <= 5 for item in transports)
    assert len(options) == 2 and all(item.max_retries == 0 for item in options)
    assert reader.budget.reads == 5 and len(calls) == 3
    assert (stripe.api_key, stripe.max_network_retries, stripe.default_http_client) == globals_before


@pytest.mark.parametrize("provider", ["stripe", "mp"])
def test_sdk_timeout_is_sanitized_retryable_without_configuring_globals(monkeypatch, provider):
    import mercadopago
    import stripe
    def failure(*args, **kwargs):
        raise TimeoutError("private-provider-payload-not-for-output")
    monkeypatch.setattr(stripe, "StripeClient", failure)
    monkeypatch.setattr(mercadopago, "SDK", failure)
    reader = ReadOnlyProviders(ReadBudget(), SimpleNamespace(STRIPE_SECRET_KEY="synthetic-no-send", MERCADOPAGO_ACCESS_TOKEN="synthetic-no-send"))
    with pytest.raises(RetryableRead) as caught:
        reader.checkout("cs_synthetic") if provider == "stripe" else reader.get("10001")
    assert "private-provider" not in str(caught.value)


def test_existing_stripe_defaults_keep_two_sdk_fetches_and_charge_read(billing_case, monkeypatch):
    import stripe

    from web.services.stripe_service import reconcile_subscription
    case = billing_case
    provider = ProviderFacts(case)
    provider.factory(ReadBudget())
    monkeypatch.setattr(stripe.Subscription, "retrieve", provider.subscription)
    monkeypatch.setattr(stripe.Charge, "retrieve", provider.charge)
    token = current_tenant.set(case.subject)
    try:
        with case.factory() as db:
            result = reconcile_subscription(db, case.reference, case.subject)
            assert result["activated"] is True
            db.commit()
    finally:
        current_tenant.reset(token)
    assert [label for label, reference in provider.calls] == ["subscription", "subscription", "charge"]
    assert facts(case)["subscription"][1] == "active"


def test_cli_default_plan_prints_only_aggregate_result(billing_case, monkeypatch, tmp_path, capsys):
    from web import billing_reconciliation_cli as cli
    from web.database import engine as database
    case = billing_case
    path = tmp_path / "selection.private.json"
    path.write_bytes(manifest(case))
    monkeypatch.setattr(database, "SessionLocal", case.factory)
    before = facts(case)
    assert cli.main(["--manifest", str(path)]) == 0
    output = capsys.readouterr().out
    result = json.loads(output)
    assert result["mode"] == "plan" and result["planned"] == 1 and result["provider_reads"] == 0
    assert case.subject not in output and case.reference not in output and str(path) not in output
    assert facts(case) == before


def test_open_checkout_is_pending_without_fabricating_activation(billing_case):
    case = billing_case
    provider = ProviderFacts(case)
    with case.factory() as db:
        intent = db.get(PurchaseIntent, case.intent)
        intent.operation, intent.provider_reference_id = "checkout", "cs_b13"
        db.commit()
    provider.checkout_fact.update(status="open", subscription=None)
    before = facts(case)
    result = apply(case, provider, manifest(case, kind="purchase_intent"))
    assert result["pending"] == 1 and result["reconciled"] == 0 and result["complete"]
    assert facts(case) == before and len(provider.calls) == 1


def test_mp_get_cannot_adopt_another_persisted_intent_after_search(billing_case):
    case = billing_case
    provider = ProviderFacts(case)
    foreign_intent = str(uuid.uuid4())
    with case.factory() as db:
        own = db.get(PurchaseIntent, case.intent)
        own.provider, own.operation, own.provider_reference_id = "mercadopago", "preference", "pref_b13"
        db.add(PurchaseIntent(id=foreign_intent, subject_id=case.foreign, provider="mercadopago", operation="preference",
            request_key=uuid.uuid4().hex, plan="pro_usuario", amount_cents=case.amount, currency="mxn", status="provider_created"))
        db.commit()
    provider.payment_fact["metadata"]["purchase_intent_id"] = foreign_intent
    provider.payment_fact["external_reference"] = foreign_intent
    before = facts(case)
    result = apply(case, provider, manifest(case, kind="purchase_intent", provider="mercadopago"))
    assert result["manual"] == 1 and result["reconciled"] == 0 and facts(case) == before
    with case.factory() as db:
        assert db.get(PurchaseIntent, foreign_intent).status == "provider_created"
        assert db.scalar(select(Subscription.id).where(Subscription.gym_id == case.foreign)) is None


def test_provider_truth_does_not_reactivate_disabled_identity(billing_case):
    case = billing_case
    with case.factory() as db:
        db.get(Usuario, case.subject).activo = False
        db.commit()
    before = facts(case)["user"]
    assert apply(case, ProviderFacts(case))["reconciled"] == 1
    assert facts(case)["user"] == before and before[0] is False


def test_factory_valueerror_is_uncertain_and_does_not_advance_cursor(billing_case):
    case = billing_case
    def broken():
        raise ValueError("private database configuration detail")
    result = service.run(manifest(case), apply=True, factory=broken)
    assert result["unconfirmed"] == 1 and result["manual"] == 0
    assert result["next_cursor"] and not result["complete"] and result["provider_reads"] == 0
    assert current_tenant.get() == ""


def test_manifest_hundred_resource_bound_and_page_limit(billing_case):
    case = billing_case
    document = json.loads(manifest(case))
    original = document["resources"][0]
    document["resources"] = [{**original, "resource_id": case.subscription + index} for index in range(100)]
    raw = json.dumps(document).encode()
    assert len(service.parse_manifest(raw)[0]) == 100
    result = service.run(raw, factory=case.factory, max_items=3)
    assert result["visited"] == 3 and result["planned"] == 1 and result["manual"] == 2
    assert result["next_cursor"] and not result["complete"]
    document["resources"].append({**original, "resource_id": case.subscription + 100})
    with pytest.raises(ValueError):
        service.run(json.dumps(document).encode(), factory=lambda: pytest.fail("Over-budget selection opened DB"))


@pytest.mark.parametrize("source", ["stripe_checkout", "stripe_elements", "mp_preference"])
@pytest.mark.parametrize("changed_read", [1, 2], ids=["first-canonical-read", "locked-canonical-read"])
def test_selected_intent_cannot_drift_to_another_purchase_by_same_actor(billing_case, source, changed_read):
    case = billing_case
    reader = ProviderFacts(case)
    other = str(uuid.uuid4())
    is_mp = source == "mp_preference"
    provider = "mercadopago" if is_mp else "stripe"
    with case.factory() as db:
        intent = db.get(PurchaseIntent, case.intent)
        intent.provider = provider
        intent.operation = "preference" if is_mp else "checkout" if source == "stripe_checkout" else "elements"
        intent.provider_reference_id = "pref_b13" if is_mp else "cs_b13" if source == "stripe_checkout" else case.reference
        if is_mp:
            sub = db.get(Subscription, case.subscription)
            sub.provider, sub.provider_payment_id = provider, case.payment
            sub.stripe_subscription_id = sub.stripe_customer_id = None
        db.add(PurchaseIntent(id=other, subject_id=case.subject, provider=provider, operation="preference" if is_mp else "elements",
            plan="pro_usuario", amount_cents=case.amount, currency="mxn", request_key=uuid.uuid4().hex,
            status="provider_created", provider_reference_id="pref_other" if is_mp else case.reference,
            provider_customer_id=case.customer))
        db.commit()
    count = [0]
    original = reader.get if is_mp else reader.subscription
    def drift(reference, **kwargs):
        count[0] += 1
        response = original(reference, **kwargs)
        if count[0] == changed_read:
            snapshot = response["response"] if is_mp else response
            snapshot["metadata"]["purchase_intent_id"] = other
            if is_mp:
                snapshot["external_reference"] = other
        return response
    if is_mp:
        reader.get = drift
    else:
        reader.subscription = drift
    before = facts(case)
    result = apply(case, reader, manifest(case, kind="purchase_intent", provider=provider))
    assert result["manual"] == 1 and result["reconciled"] == 0 and facts(case) == before
    with case.factory() as db:
        assert db.get(PurchaseIntent, other).status == "provider_created"


def test_selected_elements_intent_accepts_its_own_resource(billing_case):
    case = billing_case
    result = apply(case, ProviderFacts(case), manifest(case, kind="purchase_intent"))
    assert result["reconciled"] == 1 and result["manual"] == 0
    assert facts(case)["subscription"][1] == "active"

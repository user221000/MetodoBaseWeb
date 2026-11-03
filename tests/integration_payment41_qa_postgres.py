"""Twelve current41 criteria on one owned PostgreSQL UUID and two real backends.

Provider reads are synthetic. The migrations, restricted SQLAlchemy sessions,
RLS, SDK signature verification and HTTP authentication are real.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import hmac
import json
import re
from threading import Barrier
import time

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, DBAPIError
from sqlalchemy.orm import Session

from tests.ci_web41.payments_fixtures import (database_schema, isolated_database,
    payments41_database, payments41_case)  # noqa: F401 -- explicit owned fixture contract
from tests.test_stripe_invoice_authority_peer import SECRET, client_for, deliver, event_from
from tests.test_stripe_postgres_authority_peer import (pg_invoice,
    test_pg_invoice_signed_retry_replay_preserves_other_tenant_and_quota,
    test_pg_concurrent_same_invoice_has_one_ledger_and_retryable_inbox_collision)  # noqa: F401 -- original seven PG identities
from tests.test_stripe_postgres_refund_peer import (
    test_pg_refund_updates_only_its_ledger_and_preserves_other_tenant_quota)  # noqa: F401 -- all three original HTTP surfaces


def _owned_peer_urls(fixture):
    from tests.isolation import validate_postgres_test_url
    if (not isinstance(fixture.name, str)
            or re.fullmatch(r"metodobase_test_payments41_[0-9a-f]{32}", fixture.name) is None
            or any(engine.dialect.name != "postgresql" or engine.url.database != fixture.name
                   for engine in (fixture.admin, fixture.app))
            or (fixture.admin.url.host, fixture.admin.url.port) != (fixture.app.url.host, fixture.app.url.port)):
        raise ValueError("Original PG peers require the already-owned payments41 UUID")
    urls = tuple(engine.url.render_as_string(hide_password=False) for engine in (fixture.admin, fixture.app))
    for url in urls:
        validate_postgres_test_url(url)
    return urls


@pytest.fixture
def migration_database(payments41_database, monkeypatch):
    """Route unchanged original PG peers to this campaign's owned UUID only.

    The legacy backend-parametrized generator is never entered. Its additional
    database creation and forced DROP are replaced by the existing OID-bound
    payments41 owner and normal closure, after all twelve criteria.
    """
    from web.database.models import Base
    fixture = payments41_database
    admin_url, app_url = _owned_peer_urls(fixture)
    # The owner may retain idle restricted connections after setup/current
    # cases. Release that idle pool before the unchanged peer opens its pool2.
    # A checked-out connection is a failure, never a worker to terminate.
    assert fixture.app.pool.checkedout() == 0
    fixture.app.dispose()
    with fixture.admin.begin() as db:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
    monkeypatch.setenv("METODOBASE_TEST_POSTGRES_URL", app_url)
    yield admin_url, fixture.admin
    assert fixture.app.pool.checkedout() == fixture.admin.pool.checkedout() == 0


def provider(case, monkeypatch):
    import stripe
    state = case[2]
    state["invoice"]["charge"]["payment_intent"] = state["invoice"]["payment_intent"]
    state["invoices"] = {state["invoice"]["id"]: state["invoice"]}
    monkeypatch.setattr(stripe.Invoice, "retrieve", lambda reference, **_: deepcopy(state["invoices"][reference]))
    monkeypatch.setattr(stripe.Charge, "retrieve", lambda reference, **_: deepcopy(next(
        invoice["charge"] for invoice in state["invoices"].values() if invoice["charge"]["id"] == reference)))
    return state


def signed_refund(invoice, amount, event_id):
    invoice["charge"].update(amount_refunded=amount, refunded=amount == 7900)
    return {"id": event_id, "type": "charge.refunded", "livemode": False,
            "data": {"object": deepcopy(invoice["charge"])}}


def paid(case, client, event_id="evt_payments41_paid"):
    event = event_from(case[2])
    event["id"] = event_id
    reply = deliver(client, "/api/billing/webhook", event)
    assert reply.status_code == 200 and reply.json()["result"] == "paid:7900", reply.text


def test_partial_full_replay_and_other_tenant_quota(payments41_case, monkeypatch):
    from web.database.models import Payment, StripeWebhookEvent, Subscription, UserSubscription
    from web.database.tenant_context import tenant_scope
    from web.services.stripe_service import get_payment_history
    case, fixture = payments41_case
    factory, actor, _ = case
    state = provider(case, monkeypatch)
    with client_for(("web", "")) as client:
        paid(case, client)
        with Session(fixture.admin) as db:
            quota = db.query(UserSubscription).filter_by(user_id=actor["id"]).one()
            quota.planes_usados_mes = 2
            paid_end = db.query(Subscription).filter_by(gym_id=actor["id"]).one().current_period_end
            db.commit()
        for index, amount in enumerate((1, 1000, 7900)):
            event = signed_refund(state["invoice"], amount, "evt_payments41_refund_" + str(index))
            reply = deliver(client, "/api/billing/webhook", event)
            assert reply.status_code == 200 and reply.json()["result"] == "refund:reconciled", reply.text
            replay = deliver(client, "/api/billing/webhook", event)
            assert replay.status_code == 200 and replay.json()["result"] == "duplicate:charge.refunded"
            with tenant_scope(actor["id"]), factory() as db:
                row = get_payment_history(db, actor["id"])[0]
                assert (row["amount_cents"], row["refund_amount_cents"], row["net_amount_cents"]) == (7900, amount, 7900 - amount)
                assert row["status"] == ("refunded" if amount == 7900 else "partially_refunded")
                assert datetime.fromisoformat(row["refund_observed_at"]).tzinfo is not None
            with Session(fixture.admin) as db:
                assert db.query(Subscription).filter_by(gym_id=actor["id"]).one().current_period_end == paid_end
                assert db.query(UserSubscription).filter_by(user_id=actor["id"]).one().planes_usados_mes == 2
                other = db.query(UserSubscription).filter_by(user_id="payments41-b").one()
                assert (other.plan, other.max_planes_mes, other.planes_usados_mes) == ("starter", 1, 1)
        with Session(fixture.admin) as db:
            assert db.query(Payment).count() == 1 and db.query(StripeWebhookEvent).count() == 4
            assert db.query(UserSubscription).filter_by(user_id=actor["id"]).one().plan == "starter"
        with tenant_scope("payments41-b"), factory() as db:
            assert get_payment_history(db, actor["id"]) == [] and db.query(Payment).count() == 0


def test_old_partial_and_full_keep_new_paid_renewal(payments41_case, monkeypatch):
    from web.database.models import Payment, Subscription, UserSubscription
    case, fixture = payments41_case
    state = provider(case, monkeypatch)
    with client_for(("api", "")) as client:
        paid(case, client)
        old = state["invoice"]
        renewal = deepcopy(old)
        renewal.update(id="in_renewal41", payment_intent="pi_renewal41")
        renewal["charge"].update(id="ch_renewal41", invoice="in_renewal41", payment_intent="pi_renewal41")
        state["invoices"][renewal["id"]] = renewal
        state["invoice"] = renewal
        state["subscription"]["latest_invoice"] = deepcopy(renewal)
        state["subscription"]["current_period_start"] += 30 * 86400
        state["subscription"]["current_period_end"] += 30 * 86400
        paid(case, client, "evt_renewal41_paid")
        with Session(fixture.admin) as db:
            paid_end = db.query(Subscription).one().current_period_end
        for index, amount in enumerate((500, 7900)):
            reply = deliver(client, "/api/billing/webhook", signed_refund(old, amount, "evt_old41_refund_" + str(index)))
            assert reply.status_code == 200, reply.text
            with Session(fixture.admin) as db:
                assert db.query(Subscription).one().current_period_end == paid_end
                assert db.query(Subscription).one().status == "active"
                assert db.query(UserSubscription).filter_by(user_id=case[1]["id"]).one().plan == "pro"
                assert db.query(Payment).filter_by(stripe_invoice_id="in_renewal41").one().status == "succeeded"
                assert db.query(Payment).filter_by(stripe_invoice_id="in_peer").one().refund_amount_cents == amount


def test_partial_never_extends_same_paid_invoice_or_resets_usage(payments41_case, monkeypatch):
    import stripe
    from web.database.models import Payment, StripeWebhookEvent, Subscription, UserSubscription
    case, fixture = payments41_case
    state = provider(case, monkeypatch)
    with client_for(("web", "")) as client:
        paid(case, client)
        with Session(fixture.admin) as db:
            paid_end = db.query(Subscription).one().current_period_end
            db.query(UserSubscription).filter_by(user_id=case[1]["id"]).one().planes_usados_mes = 3
            db.commit()
        state["subscription"]["current_period_start"] += 86400
        state["subscription"]["current_period_end"] += 86400
        reply = deliver(client, "/api/billing/webhook", signed_refund(state["invoice"], 25, "evt_shifted41_partial"))
        assert reply.status_code == 200, reply.text
        # A fresh paid event cannot erase the partial or slide the same invoice.
        paid(case, client, "evt_shifted41_paid_replay")
        with Session(fixture.admin) as db:
            assert db.query(Subscription).one().current_period_end <= paid_end
            projection = db.query(UserSubscription).filter_by(user_id=case[1]["id"]).one()
            assert (projection.plan, projection.planes_usados_mes, projection.max_planes_mes) == ("pro", 3, 5)

        def persisted_funding():
            # The privileged connection observes every synthetic A/B row,
            # while the webhook itself still uses the restricted role/RLS.
            with Session(fixture.admin) as db:
                return tuple(tuple(tuple(getattr(row, column.name) for column in model.__table__.columns)
                                   for row in db.query(model).order_by(*model.__table__.primary_key.columns))
                             for model in (Subscription, Payment, UserSubscription, StripeWebhookEvent))

        stable = deepcopy(state["invoice"])
        observations = []
        # The cumulative partial progresses first. A stable full refund is last
        # so no later case invents a regression from a known complete refund.
        for mutation in ("partial", "presence_null", "full"):
            changed = deepcopy(stable)
            if mutation == "partial":
                changed["charge"].update(amount_refunded=26, refunded=False)
            elif mutation == "presence_null":
                assert "amount_captured" not in changed["charge"]
                changed["charge"]["amount_captured"] = None
            else:
                changed["charge"].update(amount_refunded=7900, refunded=True)
            reads = []

            def changing_invoice(reference, **_):
                assert reference == stable["id"]
                reads.append(reference)
                return deepcopy(changed if len(reads) >= 3 else stable)

            monkeypatch.setattr(stripe.Invoice, "retrieve", changing_invoice)
            event = event_from(state)
            event["id"] = "evt_pg41_third_read_" + mutation
            before = persisted_funding()
            failed = deliver(client, "/api/billing/webhook", event)
            assert failed.status_code == 503, (mutation, failed.status_code, failed.text)
            assert len(reads) >= 3
            assert persisted_funding() == before, "Contradictory reads must roll back access, money, usage and inbox together"
            with Session(fixture.admin) as db:
                assert db.get(StripeWebhookEvent, event["id"]) is None

            # An invalid NULL observation recovers to the last valid provider
            # state. Partial/full observations then use their stable current
            # values on every provider read of the exact same signed attempt.
            if mutation != "presence_null":
                stable = deepcopy(changed)
            state["invoice"].clear()
            state["invoice"].update(deepcopy(stable))
            monkeypatch.setattr(stripe.Invoice, "retrieve", lambda reference, **_: deepcopy(stable))
            retry = deliver(client, "/api/billing/webhook", event)
            assert retry.status_code == 200, (mutation, retry.status_code, retry.text)
            expected = "pending:invoice_payment_not_verified" if mutation == "full" else "paid:7900"
            assert retry.json()["result"] == expected
            replay = deliver(client, "/api/billing/webhook", event)
            assert replay.status_code == 200 and replay.json()["result"] == "duplicate:invoice.paid"
            with Session(fixture.admin) as db:
                sub = db.query(Subscription).one()
                quota = db.query(UserSubscription).filter_by(user_id=case[1]["id"]).one()
                assert quota.planes_usados_mes == 3
                if mutation == "full":
                    # An unpaid provider period is metadata, not paid access.
                    # Preserve the pre-existing complete-refund policy while
                    # requiring both canonical and quota access to be closed.
                    assert (sub.status, quota.plan, quota.max_planes_mes, quota.status) == ("unpaid", "starter", 1, "canceled")
                else:
                    assert sub.current_period_end <= paid_end
                    assert (sub.status, quota.plan, quota.max_planes_mes) == ("active", "pro", 5)
                assert db.query(Payment).one().refund_amount_cents == 26
                assert db.query(StripeWebhookEvent).filter_by(event_id=event["id"]).count() == 1
            observations.append({"mutation": mutation, "changing_provider_reads": len(reads),
                                 "HTTP_rejection": 503, "all_four_persisted_planes_rolled_back": True,
                                 "retry_HTTP": 200, "retry_result": expected, "dedup_HTTP": 200})

        # A stable unfunded invoice revokes access. Its independently signed
        # charge.refunded event records the complete monetary refund through
        # the existing charge handler, preserving its distinct event purpose.
        final_refund = signed_refund(state["invoice"], 7900, "evt_pg41_third_read_full_charge")
        final = deliver(client, "/api/billing/webhook", final_refund)
        assert final.status_code == 200 and final.json()["result"] == "refund:reconciled", final.text
        final_replay = deliver(client, "/api/billing/webhook", final_refund)
        assert final_replay.status_code == 200 and final_replay.json()["result"] == "duplicate:charge.refunded"
        with Session(fixture.admin) as db:
            assert (db.query(Payment).one().status, db.query(Payment).one().refund_amount_cents) == ("refunded", 7900)
            assert db.query(UserSubscription).filter_by(user_id=case[1]["id"]).one().planes_usados_mes == 3
        fixture.record("third-read-HTTP-rollback-retry.json", {"variants": observations,
                       "stable_full_charge_refund_and_dedup": True, "separate_test_IDs_added": 0})


def test_concurrent_signed_refund_has_two_backends_and_one_cumulative_fact(payments41_case, monkeypatch, record_property):
    import stripe
    from web.database.models import Payment, StripeWebhookEvent
    from web.services.stripe_service import handle_webhook_event
    case, fixture = payments41_case
    factory = case[0]
    state = provider(case, monkeypatch)
    with client_for(("web", "")) as client:
        paid(case, client)
    event = signed_refund(state["invoice"], 1700, "evt_concurrent41_refund")
    raw = json.dumps(event).encode()
    stamp = str(int(time.time()))
    signature = "t=" + stamp + ",v1=" + hmac.new(SECRET.encode(), stamp.encode() + b"." + raw, hashlib.sha256).hexdigest()
    gate, backends = Barrier(2), []

    def attempt():
        with factory() as db:
            backends.append(db.scalar(text("SELECT pg_backend_pid()")))
            gate.wait(timeout=15)
            authenticated = stripe.Webhook.construct_event(raw, signature, SECRET)
            try:
                answer = handle_webhook_event(db, authenticated)
                db.commit()
                return answer
            except IntegrityError:
                db.rollback()
                return "retryable_inbox_collision"

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(lambda _: attempt(), range(2)))
    assert len(set(backends)) == 2 and "refund:reconciled" in results
    assert set(results) <= {"refund:reconciled", "duplicate:charge.refunded", "retryable_inbox_collision"}
    record_property("two_physical_restricted_postgres_backends", json.dumps(sorted(backends)))
    fixture.record("concurrent-backends.json", {"pids": sorted(backends), "distinct": 2, "results": results})
    with factory() as db:
        assert handle_webhook_event(db, event) == "duplicate:charge.refunded"
        db.commit()
    with Session(fixture.admin) as db:
        assert db.query(Payment).count() == 1
        row = db.query(Payment).one()
        assert (row.status, row.refund_amount_cents) == ("partially_refunded", 1700)
        assert db.query(StripeWebhookEvent).filter_by(event_id=event["id"]).count() == 1


def test_actual_personal_team_history_is_own_and_rls_protected(payments41_case):
    from fastapi.testclient import TestClient
    from web.auth import crear_access_token, init_auth
    from web.database.models import Usuario, UserRole, Payment
    from web.database.tenant_context import tenant_scope
    from web.services.stripe_service import get_payment_history
    case, fixture = payments41_case
    actors = {"gym": {"id": "payments41-gym", "tipo": "gym", "role": "owner", "team_gym_id": None},
              "team": {"id": "payments41-team", "tipo": "gym", "role": "viewer", "team_gym_id": "payments41-gym"}}
    with Session(fixture.admin) as db:
        for key, actor in actors.items():
            actor.update(email=key + "@example.invalid", nombre="Synthetic", session_version=0)
            db.add(Usuario(id=actor["id"], email=actor["email"], nombre=actor["nombre"], password_hash="unused-offline",
                           tipo=actor["tipo"], role=UserRole(actor["role"]), team_gym_id=actor["team_gym_id"], activo=True))
        db.flush()
        for actor in actors.values():
            db.add(Payment(gym_id=actor["id"], amount_cents=7900, currency="mxn", status="succeeded"))
        db.commit()
        expected = {row.gym_id: row.id for row in db.scalars(select(Payment))}
    init_auth(run_startup_writes=False)
    tokens = {key: crear_access_token(actor) for key, actor in actors.items()}
    from api.app import create_app as api_factory
    from web.main_web import create_app as web_factory
    for create_app in (api_factory, web_factory):
        with TestClient(create_app(), raise_server_exceptions=False) as client:
            reply = client.get("/api/usuario/payments", params={"gym_id": actors["gym"]["id"]},
                               headers={"Authorization": "Bearer " + tokens["team"]})
            assert reply.status_code == 200, reply.text
            assert [row["id"] for row in reply.json()["payments"]] == [expected[actors["team"]["id"]]]
            assert client.get("/api/usuario/payments", headers={"Authorization": "Bearer " + tokens["gym"]}).status_code == 403
            assert client.get("/api/usuario/payments").status_code == 401
    with tenant_scope(actors["team"]["id"]), case[0]() as db:
        assert get_payment_history(db, actors["gym"]["id"]) == []
        with pytest.raises(DBAPIError):
            db.add(Payment(gym_id=actors["gym"]["id"], amount_cents=7900, currency="mxn", status="succeeded"))
            db.commit()
        db.rollback()
    with case[0]() as db:
        assert db.query(Payment).count() == 0

"""Bounded operator-selected billing reconciliation, never a public endpoint.

An explicit manifest authorizes only existing subjects and persisted resource
PKs. Each item owns its Session and tenant context; finalization precedes ACK.
The default plan mode reads local facts only and never constructs an SDK.
"""
import base64
import hashlib
import hmac
import json
import logging
import re
from pathlib import Path
from uuid import UUID

from sqlalchemy import select, text

from web.database.models import PurchaseIntent, Subscription, Usuario
from web.database.tenant_context import bind_verified_subject, current_tenant
from web.services.billing_reconciliation_providers import (
    ReadBudget,
    ReadOnlyProviders,
    RetryableRead,
)

MAX_MANIFEST_BYTES = 65536
MAX_RESOURCES = 100
logger = logging.getLogger(__name__)


class ManualReconciliation(ValueError):
    """Persisted/provider facts do not authorize an automatic repair."""


def _uuid(value):
    if type(value) is not str or str(UUID(value)) != value:
        raise ValueError("Invalid reconciliation selection")
    return value


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("Invalid reconciliation selection")
        result[key] = value
    return result


def parse_manifest(raw):
    if type(raw) is not bytes or len(raw) > MAX_MANIFEST_BYTES:
        raise ValueError("Invalid reconciliation selection")
    try:
        document = json.loads(raw, object_pairs_hook=_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Invalid reconciliation selection")))
        if type(document) is not dict or set(document) != {"version", "resources"} or type(document["version"]) is not int or document["version"] != 1:
            raise ValueError
        resources = document["resources"]
        if type(resources) is not list or not 1 <= len(resources) <= MAX_RESOURCES:
            raise ValueError
        seen = set()
        for item in resources:
            if type(item) is not dict or set(item) != {"subject_id", "kind", "resource_id", "provider"}:
                raise ValueError
            _uuid(item["subject_id"])
            if item["provider"] not in {"stripe", "mercadopago"}:
                raise ValueError
            if item["kind"] == "subscription":
                if type(item["resource_id"]) is not int or not 1 <= item["resource_id"] <= 2147483647:
                    raise ValueError
            elif item["kind"] == "purchase_intent":
                _uuid(item["resource_id"])
            else:
                raise ValueError
            identity = (item["subject_id"], item["kind"], item["resource_id"])
            if identity in seen:
                raise ValueError
            seen.add(identity)
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        raise ValueError("Invalid reconciliation selection") from None
    canonical = json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return resources, hashlib.sha256(canonical).hexdigest()


def load_manifest(path):
    try:
        with Path(path).open("rb") as source:
            return parse_manifest(source.read(MAX_MANIFEST_BYTES + 1))
    except (OSError, ValueError):
        raise ValueError("Invalid reconciliation selection") from None


def _cursor(selection, offset):
    data = json.dumps({"version": 1, "selection": selection, "offset": offset}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _offset(cursor, selection, count):
    if cursor is None:
        return 0
    try:
        if type(cursor) is not str or len(cursor) > 512 or not re.fullmatch(r"[A-Za-z0-9_-]+", cursor):
            raise ValueError
        raw = base64.b64decode(cursor + "=" * (-len(cursor) % 4), altchars=b"-_", validate=True)
        data = json.loads(raw, object_pairs_hook=_pairs)
        if set(data) != {"version", "selection", "offset"} or type(data["version"]) is not int or data["version"] != 1:
            raise ValueError
        if type(data["selection"]) is not str or not hmac.compare_digest(data["selection"], selection):
            raise ValueError
        if type(data["offset"]) is not int or not 0 <= data["offset"] < count:
            raise ValueError
        return data["offset"]
    except (ValueError, TypeError, KeyError, UnicodeError):
        raise ValueError("Invalid reconciliation cursor") from None


def _reference(value):
    if type(value) is not str or not 1 <= len(value) <= 255 or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ManualReconciliation("Resource unavailable for automatic reconciliation")
    return value


def _payment_id(value):
    if type(value) not in {str, int} or not re.fullmatch(r"[0-9]{1,32}", str(value)):
        raise ManualReconciliation("Resource unavailable for automatic reconciliation")
    return str(value)


def _resource(db, item):
    subject = item["subject_id"]
    if db.scalar(select(Usuario.id).where(Usuario.id == subject)) is None:
        raise ManualReconciliation("Resource unavailable for automatic reconciliation")
    if item["kind"] == "subscription":
        row = db.scalar(select(Subscription).where(Subscription.id == item["resource_id"], Subscription.gym_id == subject))
        if row is None or row.provider not in {None, item["provider"]}:
            raise ManualReconciliation("Resource unavailable for automatic reconciliation")
        reference = row.stripe_subscription_id if item["provider"] == "stripe" else row.provider_payment_id
        return row, _reference(reference)
    row = db.scalar(select(PurchaseIntent).where(PurchaseIntent.id == item["resource_id"],
        PurchaseIntent.subject_id == subject, PurchaseIntent.provider == item["provider"]))
    if row is None:
        raise ManualReconciliation("Resource unavailable for automatic reconciliation")
    return row, _reference(row.provider_reference_id)


def _checkout(reader, intent):
    snapshot = reader.checkout(intent.provider_reference_id)
    metadata = snapshot.get("metadata") or {}
    if (snapshot.get("id") != intent.provider_reference_id or snapshot.get("object") != "checkout.session"
            or snapshot.get("mode") != "subscription" or metadata.get("purchase_intent_id") != intent.id
            or metadata.get("gym_id") != intent.subject_id or metadata.get("plan") != intent.plan
            or (intent.provider_customer_id and snapshot.get("customer") != intent.provider_customer_id)):
        raise ManualReconciliation("Resource unavailable for automatic reconciliation")
    if snapshot.get("subscription") is None and snapshot.get("status") in {"open", "expired"}:
        return None
    return _reference(snapshot.get("subscription"))


def _payment_search(reader, intent):
    result = reader.search(intent.id)
    if result.get("status") != 200:
        raise RetryableRead("Provider unavailable")
    body = result.get("response") or {}
    paging, values = body.get("paging") or {}, body.get("results")
    total = paging.get("total")
    if (type(values) is not list or type(total) is not int or not 0 <= total <= 10
            or len(values) != total or len(values) > 10 or paging.get("offset") != 0):
        raise ManualReconciliation("Resource unavailable for automatic reconciliation")
    if not values:
        return None
    # Several attempts can fund the same intent. Selecting one by order/status
    # would invent payment authority; leave this exact intent to manual review.
    if len(values) != 1 or type(values[0]) is not dict or values[0].get("external_reference") != intent.id:
        raise ManualReconciliation("Resource unavailable for automatic reconciliation")
    return _payment_id(values[0].get("id"))


class SelectedIntentReads:
    """Every canonical read must remain within the exact selected purchase.

    Matching only its actor would allow checkout/search for A to reconcile B
    belonging to that same actor. The guard is repeated on the fresh read
    under the existing reconciler's account lock, not just on discovery.
    """
    def __init__(self, reader, intent_id):
        self.reader = reader
        self.intent_id = intent_id

    def subscription(self, reference, *, expand):
        snapshot = self.reader.subscription(reference, expand=expand)
        metadata = snapshot.get("metadata") or {}
        if snapshot.get("id") != reference or metadata.get("purchase_intent_id") != self.intent_id:
            raise ManualReconciliation("Resource unavailable for automatic reconciliation")
        return snapshot

    def charge(self, reference):
        return self.reader.charge(reference)

    def payment(self):
        return self

    def get(self, reference):
        result = self.reader.payment().get(reference)
        if result.get("status") != 200:
            raise RetryableRead("Provider unavailable")
        snapshot = result.get("response") or {}
        metadata = snapshot.get("metadata") or {}
        if (str(snapshot.get("id")) != str(reference) or snapshot.get("external_reference") != self.intent_id
                or metadata.get("purchase_intent_id") not in {None, self.intent_id}):
            raise ManualReconciliation("Resource unavailable for automatic reconciliation")
        return result


def _apply(db, item, row, reference, reader):
    canonical = SelectedIntentReads(reader, row.id) if isinstance(row, PurchaseIntent) else reader
    if item["provider"] == "stripe":
        from web.services.stripe_service import reconcile_subscription
        if isinstance(row, PurchaseIntent) and row.operation == "checkout" and row.status in {"pending", "provider_created"}:
            reference = _checkout(reader, row)
            if reference is None:
                return "pending"
        elif isinstance(row, PurchaseIntent) and row.operation not in {"checkout", "elements"}:
            raise ManualReconciliation("Resource unavailable for automatic reconciliation")
        try:
            reconcile_subscription(db, reference, item["subject_id"], fetch_subscription=canonical.subscription, fetch_charge=canonical.charge)
        except ValueError:
            raise ManualReconciliation("Resource unavailable for automatic reconciliation") from None
        return "reconciled"
    from web.services.mercadopago_service import reconcile_payment
    if isinstance(row, PurchaseIntent):
        if row.operation != "preference":
            raise ManualReconciliation("Resource unavailable for automatic reconciliation")
        reference = _payment_search(reader, row)
        if reference is None:
            return "pending"
    try:
        reconcile_payment(db, _payment_id(reference), sdk=canonical)
    except ValueError:
        raise ManualReconciliation("Resource unavailable for automatic reconciliation") from None
    return "reconciled"


def _one(item, *, factory, apply, reader_factory, budget):
    token = current_tenant.set("")
    scope = None
    db, owned, committed, outcome = None, False, False, "unconfirmed"
    try:
        db = factory()
        if db.in_transaction():
            raise RuntimeError("Reconciliation requires an owned fresh Session")
        owned = True
        scope = current_tenant.set(item["subject_id"])
        bind_verified_subject(db, item["subject_id"])
        if db.get_bind().dialect.name == "postgresql":
            db.execute(text("SELECT set_config('statement_timeout', '5000', true), set_config('lock_timeout', '1000', true)"))
        row, reference = _resource(db, item)
        if apply:
            applied = _apply(db, item, row, reference, reader_factory(budget))
            try:
                db.commit()
            except Exception as error:  # noqa: BLE001 -- any COMMIT failure is uncertain; exception text is private.
                # Even ValueError after a successful server COMMIT is an
                # uncertain ACK, never a permanent/manual result to skip.
                logger.error("reconciliation_commit_unconfirmed class=%s", type(error).__name__)
                raise RuntimeError("Reconciliation commit unconfirmed") from None
            committed = True
            outcome = applied
        else:
            outcome = "planned"
    except ManualReconciliation:
        outcome = "manual"
    except RetryableRead:
        outcome = "retryable"
    except Exception as error:  # noqa: BLE001 -- an unknown owned transaction failure cannot produce ACK.
        logger.error("reconciliation_unconfirmed class=%s", type(error).__name__)
        outcome = "unconfirmed"
    finally:
        if owned:
            try:
                if not committed:
                    db.rollback()
            except Exception as error:  # noqa: BLE001 -- cleanup of the owned Session must fail closed for every class.
                logger.error("reconciliation_rollback_unconfirmed class=%s", type(error).__name__)
                outcome = "unconfirmed"
            try:
                db.close()
            except Exception as error:  # noqa: BLE001 -- close uncertainty must not become a successful result.
                logger.error("reconciliation_close_unconfirmed class=%s", type(error).__name__)
                outcome = "unconfirmed"
                try:
                    db.invalidate()
                except Exception as error:  # noqa: BLE001 -- final owned invalidation cannot expose private diagnostics.
                    logger.error("reconciliation_invalidate_unconfirmed class=%s", type(error).__name__)
        if scope is not None:
            current_tenant.reset(scope)
        current_tenant.reset(token)
    return outcome


def run(manifest, *, apply=False, cursor=None, max_items=25, seconds=60,
        factory=None, reader_factory=None, budget=None):
    """One finite page; a temporary/uncertain result retains its same cursor."""
    if type(apply) is not bool or type(max_items) is not int or not 1 <= max_items <= MAX_RESOURCES:
        raise ValueError("Invalid reconciliation options")
    resources, selection = parse_manifest(manifest)
    offset = _offset(cursor, selection, len(resources))
    budget = budget or ReadBudget(seconds=seconds)
    if factory is None:
        from web.database.engine import SessionLocal
        factory = SessionLocal
    if reader_factory is None:
        from web.settings import get_settings
        reader_factory = lambda limit: ReadOnlyProviders(limit, get_settings())
    result = {"version": 1, "mode": "apply" if apply else "plan", "visited": 0,
        "planned": 0, "reconciled": 0, "pending": 0, "manual": 0, "retryable": 0, "unconfirmed": 0, "deferred": 0}
    neutral = current_tenant.set("")
    index = offset
    try:
        while index < min(offset + max_items, len(resources)):
            try:
                budget.admit_item()
            except RetryableRead:
                result["deferred"] += 1
                break
            outcome = _one(resources[index], factory=factory, apply=apply, reader_factory=reader_factory, budget=budget)
            result["visited"] += 1
            result[outcome] += 1
            if outcome in {"retryable", "unconfirmed"}:
                break
            index += 1
    finally:
        current_tenant.reset(neutral)
    result.update(provider_reads=budget.reads, complete=index == len(resources),
        next_cursor=None if index == len(resources) else _cursor(selection, index))
    return result

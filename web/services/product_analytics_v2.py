"""Explicit origin declarations and aggregate v2 product facts; v1 stays frozen."""
from datetime import datetime, timezone

from sqlalchemy import select, text

from web import product_analytics_domain as v1
from web.database.models import Cliente, ProductAnalyticsFact as Fact, Usuario
from web.database.tenant_context import bind_verified_subject, current_tenant
from web.product_analytics_v2 import aggregate
from web.services import product_analytics as authority
from web.services import product_facts


def _origin_authority(db, principal, context, *, write=False):
    if context != 'gym':
        return authority._authority(db, principal, context)
    if (not isinstance(principal, dict) or not isinstance(principal.get('id'), str)
            or not 1 <= len(principal['id']) <= 36 or type(principal.get('session_version')) is not int):
        authority.fail(401, 'analytics_identity_unavailable')
    actor = db.execute(select(*authority._USER).where(Usuario.id == principal['id'])).first()
    if (not authority._live(actor) or actor.session_version != principal['session_version']
            or actor.tipo != principal.get('tipo') or actor.role.value != principal.get('role')
            or actor.team_gym_id != principal.get('team_gym_id')):
        authority.fail(401, 'analytics_identity_unavailable')
    owner = actor.team_gym_id or actor.id
    parent = db.execute(select(*authority._USER).where(Usuario.id == owner)).first()
    from web.services.permissions import has_permission
    if (not authority._owner(parent) or (actor.team_gym_id and actor.role.value == 'owner')
            or not has_permission(actor, 'read', 'cliente', owner)
            or write and not authority._owner(actor)):
        authority.fail(403, 'analytics_context_forbidden')
    bind_verified_subject(db, owner)
    return owner


def origin(db, principal, context, client, *, value=None, expected_version=None):
    if db.in_transaction() or db.in_nested_transaction():
        raise RuntimeError("Origin service requires an owned Session")
    try:
        owner = _origin_authority(db, principal, context, write=value is not None)
        if context == "gym":
            if not isinstance(client, str) or not 1 <= len(client) <= 36:
                authority.fail(422, "analytics_invalid_input")
            if value is not None:
                # R12 acceptance already locks this owner. Match that order
                # before the client lock, and revalidate a revoked identity
                # after any wait rather than trusting the initial projection.
                product_facts.lock_subject(db, owner, 'personal', None)
                _origin_authority(db, principal, context, write=True)
            subject = (product_facts.lock_subject(db, owner, context, client) if value is not None else
                db.scalar(select(Cliente).where(Cliente.gym_id == owner, Cliente.id_cliente == client)))
            if subject is None or subject.deleted_at is not None:
                authority.fail(404, "analytics_subject_unavailable")
        elif client is not None:
            authority.fail(422, "analytics_invalid_input")
        elif value is not None:
            subject = product_facts.lock_subject(db, owner, context, None)
            # Revalidate account authority after the serialization lock.
            _origin_authority(db, principal, context, write=True)
        current = product_facts.current_origin(db, owner, context, client)
        if value is not None:
            if value not in product_facts.ORIGINS or type(expected_version) is not int or expected_version != current["version"] or current["version"] >= product_facts.MAX_VERSION:
                authority.fail(409, "analytics_origin_conflict")
            product_facts.append(db, owner, context, client, "origin_declared", client or owner,
                current["version"] + 1, value)
            db.commit()
            return {"origin": value, "version": current["version"] + 1, "applies_to": "future_facts", "customer_is_payment": False}
        db.rollback()
        return {**current, "applies_to": "future_facts", "customer_is_payment": False}
    except Exception:
        db.rollback()
        raise


def read_report(principal, context, start=None, through=None, *, session_factory=None):
    if session_factory is None:
        from web.database.engine import SessionLocal
        session_factory = SessionLocal
    # Borrow no caller transaction or tenant, and restore it before returning.
    token = current_tenant.set("")
    db = None
    try:
        candidate = session_factory()
        if candidate.in_transaction() or candidate.in_nested_transaction():
            raise RuntimeError("Analytics v2 requires a new owned Session")
        db = candidate
        authority._snapshot(db)
        owner = authority._authority(db, principal, context)
        from web.database.schema_control import expected_head
        if db.scalars(text("SELECT version_num FROM alembic_version")).all() != [expected_head()]:
            raise RuntimeError("Analytics schema unavailable")
        period = v1.period(start, through)
        # Database reads are bounded before materialization; no global population.
        rows = db.execute(select(Fact.event_type, Fact.origin, Fact.occurred_at, Fact.client_id,
            Fact.source_id).where(Fact.owner_id == owner, Fact.context == context)
            .order_by(Fact.occurred_at, Fact.id).limit(v1.MAX_FACTS + 1)).all()
        if len(rows) > v1.MAX_FACTS:
            authority.fail(413, "analytics_volume_limit")
        result = aggregate(rows, period, now=datetime.now(timezone.utc), context=context)
        owned = db
        db = None
        authority._cleanup(owned)
        return result
    finally:
        if db is not None:
            authority._cleanup(db)
        current_tenant.reset(token)

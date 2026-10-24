"""Append typed facts in the business transaction, never a best-effort collector.

Only the post-ASGI observation has a separate transaction. A failure there is
reported as an observation gap, without changing an already served response.
"""
import logging
import uuid

from sqlalchemy import select, update

from web.database.models import Cliente, ProductAnalyticsFact as Fact, Usuario
from web.database.product_analytics_schema_v2 import EVENTS, ORIGINS

logger = logging.getLogger(__name__)
MAX_VERSION = 2147483647


def origin_query(owner, context, client=None):
    return select(Fact).where(Fact.owner_id == owner, Fact.context == context,
        Fact.client_id == client, Fact.event_type == "origin_declared").order_by(Fact.source_version.desc())


def current_origin(db, owner, context, client=None):
    fact = db.scalar(origin_query(owner, context, client).limit(1))
    return {"origin": fact.origin if fact else "unknown", "version": fact.source_version if fact else 0}


def inherited_origin(db, owner, context, event, source, client=None):
    fact = db.scalar(select(Fact.origin).where(Fact.owner_id == owner, Fact.context == context,
        Fact.client_id == client, Fact.event_type == event, Fact.source_id == str(source),
        Fact.source_version == 1))
    return fact or "unknown"


def append(db, owner, context, client, event, source, version, origin):
    """Exact source uniqueness makes retries no-ops; it never updates old facts."""
    if event not in EVENTS or origin not in ORIGINS or context not in ("gym", "personal"):
        raise ValueError("Invalid product fact")
    if type(version) is not int or not 1 <= version <= MAX_VERSION:
        raise ValueError("Invalid product source version")
    values = {"id": uuid.uuid4().hex, "owner_id": owner, "context": context,
        "client_id": client, "event_type": event, "source_id": str(source),
        "source_version": version, "origin": origin}
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    elif dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert
    else:
        raise RuntimeError("Unreviewed product fact dialect")
    statement = insert(Fact).values(**values)
    if dialect == "postgresql":
        from sqlalchemy.exc import IntegrityError
        # A targeted ON CONFLICT also checks SELECT RLS on the proposed row.
        # Preserve narrow recipient reads and accept only the exact source-key
        # duplicate. Begin outside try: errors from flushing prior business
        # state must propagate, even if they name this same constraint.
        savepoint = db.begin_nested()
        try:
            with savepoint:
                db.execute(statement)
        except IntegrityError as error:
            detail = getattr(error.orig, "diag", None)
            if (getattr(error.orig, "pgcode", None) != "23505"
                    or getattr(detail, "constraint_name", None) != "uq_product_fact_source"
                    or getattr(detail, "table_name", None) != "product_analytics_facts"
                    or getattr(detail, "schema_name", None) != "public"):
                raise
    else:
        db.execute(statement.on_conflict_do_nothing(index_elements=[
            "owner_id", "context", "event_type", "source_id", "source_version"]))


def lock_subject(db, owner, context, client):
    """One real subject lock orders declarations and new plan snapshots."""
    model, condition = ((Cliente, (Cliente.gym_id == owner, Cliente.id_cliente == client))
        if context == "gym" else (Usuario, (Usuario.id == owner,)))
    if db.get_bind().dialect.name == "sqlite":
        db.execute(update(model).where(*condition).values(id=model.id).execution_options(synchronize_session=False))
    return db.scalar(select(model).where(*condition).with_for_update().execution_options(populate_existing=True))


def plan_saved(db, plan, *, personal=False):
    context, client = ("personal", None) if personal else ("gym", plan.id_cliente)
    if lock_subject(db, plan.gym_id, context, client) is None:
        raise ValueError("Product fact source unavailable")
    append(db, plan.gym_id, context, client, "plan_saved", plan.id, 1,
           current_origin(db, plan.gym_id, context, client)["origin"])


def link_accepted(db, link):
    append(db, link.gym_id, "gym", link.client_id, "client_link_accepted", link.id, link.version,
           current_origin(db, link.gym_id, "gym", link.client_id)["origin"])


def assignment_published(db, publication):
    append(db, publication.gym_id, "gym", publication.client_id, "plan_assignment_published",
        publication.id, 1, inherited_origin(db, publication.gym_id, "gym", "plan_saved",
            publication.source_plan_id, publication.client_id))


def assignment_withdrawn(db, publication):
    append(db, publication.gym_id, "gym", publication.client_id, "plan_assignment_withdrawn",
        publication.id, publication.publication_version, inherited_origin(db, publication.gym_id,
            "gym", "plan_assignment_published", publication.id, publication.client_id))


def assigned_plan_served(principal, link_id, publication_id, publication_version):
    """Revalidate the served principal/source, then persist one first HTTP200 fact.

    Called after ASGI accepted the complete response body, not after TCP receipt
    or human reading. Revocation/races/crash/commit failure can lose observations.
    There is no retry, and no change to the already served business response.
    """
    try:
        from web.database.engine import SessionLocal
        from web.services.client_link_context import operation, commit
        from web.services.client_link_plans import _read_context, _publication
        with SessionLocal() as db, operation(db):
            _, link = _read_context(db, principal, link_id)
            publication = _publication(db, link, publication_id)
            if publication is None or publication.publication_version != publication_version:
                raise ValueError("Served source changed")
            append(db, publication.gym_id, "gym", publication.client_id, "assigned_plan_http200",
                publication.id, publication.publication_version, inherited_origin(db, publication.gym_id,
                    "gym", "plan_assignment_published", publication.id, publication.client_id))
            commit(db)
    except Exception as error:  # noqa: BLE001 -- response has already been served; never reflect source identifiers
        logger.error("Assigned-plan observation unconfirmed class=%s", type(error).__name__)

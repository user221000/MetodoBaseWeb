"""One authorised, consistent snapshot of minimal retained business facts.

No event collection, profile bootstrap, global report, health data, statistics
helper, new RLS policy or second connection. Scope is derived only after the
authenticated identity is revalidated in this reader's fresh owned Session.
"""
import logging

from fastapi import HTTPException
from sqlalchemy import and_, exists, or_, select, text
from sqlalchemy.orm import aliased

from web import product_analytics_domain as domain
from web.database.models import (
    ClientAccountLink as Link,
)
from web.database.models import (
    Cliente,
    UserRole,
    Usuario,
)
from web.database.models import (
    ClientLinkInvitation as Invitation,
)
from web.database.models import (
    ClientPlanPublication as Publication,
)
from web.database.models import (
    GenerationReservation as Personal,
)
from web.database.models import (
    GymGenerationReservation as Gym,
)
from web.database.models import (
    PlanGenerado as Plan,
)
from web.database.tenant_context import bind_verified_subject, current_tenant
from web.services.permissions import has_permission

logger = logging.getLogger(__name__)
_USER = (Usuario.id, Usuario.tipo, Usuario.role, Usuario.team_gym_id, Usuario.activo,
         Usuario.deleted_at, Usuario.invitation_token, Usuario.session_version)


def fail(status, code):
    raise HTTPException(status, {"code": code, "message": {
        "analytics_invalid_input": "Revisa el contexto y las fechas de la consulta.",
        "analytics_identity_unavailable": "Vuelve a iniciar sesión para consultar tu espacio.",
        "analytics_context_forbidden": "Esta cuenta no puede consultar ese espacio.",
        "analytics_volume_limit": "El resultado supera el volumen de esta consulta.",
    }.get(code, "No pudimos confirmar la consulta. Vuelve a consultarla desde tu cuenta.")})


def _live(row):
    return (row is not None and row.activo is True and row.deleted_at is None
        and row.invitation_token is None and row.role in set(UserRole)
        and type(row.session_version) is int and 0 <= row.session_version <= 2147483647)


def _owner(row):
    return _live(row) and row.tipo == "gym" and row.role == UserRole.OWNER and row.team_gym_id is None


def _authority(db, principal, context):
    if (not isinstance(principal, dict) or not isinstance(principal.get("id"), str)
            or not 1 <= len(principal["id"]) <= 36 or type(principal.get("session_version")) is not int):
        fail(401, "analytics_identity_unavailable")
    row = db.execute(select(*_USER).where(Usuario.id == principal["id"])).first()
    if (not _live(row) or row.session_version != principal["session_version"]
            or row.tipo != principal.get("tipo") or row.role.value != principal.get("role")
            or row.team_gym_id != principal.get("team_gym_id")):
        fail(401, "analytics_identity_unavailable")
    team = row.team_gym_id is not None
    if team:
        parent = db.execute(select(*_USER).where(Usuario.id == row.team_gym_id)).first()
        if not _owner(parent) or row.role == UserRole.OWNER:
            fail(403, "analytics_context_forbidden")
    if context == "gym":
        scope = row.team_gym_id if team else row.id
        if not (_owner(row) or team and row.role == UserRole.ADMIN) or not has_permission(row, "read", "analytics", scope):
            fail(403, "analytics_context_forbidden")
    elif context == "personal":
        if row.role == UserRole.OWNER or not (team or row.tipo == "usuario"):
            fail(403, "analytics_context_forbidden")
        scope = row.id
    else:
        fail(422, "analytics_invalid_input")
    bind_verified_subject(db, scope)
    return scope


def _snapshot(db):
    """Connection options precede BEGIN, including the existing GUC hooks."""
    if db.in_transaction() or db.in_nested_transaction():
        raise RuntimeError("Analytics requires a new owned Session")
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        connection = db.connection(execution_options={
            "isolation_level": "REPEATABLE READ", "postgresql_readonly": True})
        if (connection.get_isolation_level() != "REPEATABLE READ"
                or connection.exec_driver_sql("SHOW transaction_read_only").scalar_one() != "on"):
            raise RuntimeError("Analytics snapshot not available")
    elif dialect == "sqlite":
        connection = db.connection()
        if connection.connection.driver_connection.in_transaction:
            raise RuntimeError("Analytics SQLite transaction already active")
        connection.exec_driver_sql("BEGIN")
    else:
        raise RuntimeError("Unsupported analytics database")


def _rows(db, query):
    rows = db.execute(query.limit(domain.MAX_FACTS + 1)).all()
    if len(rows) > domain.MAX_FACTS:
        raise domain.AnalyticsVolume("Fact budget exceeded")
    return rows


def _saved(db, scope, context, cutoff, *, exclusive=False):
    cutoff = cutoff.replace(tzinfo=None)
    table = Gym if context == "gym" else Personal
    query = select(table.id, table.persisted_at).outerjoin(Plan, Plan.id == table.plan_id).outerjoin(
        Cliente, and_(Cliente.id_cliente == Plan.id_cliente, Cliente.gym_id == Plan.gym_id))
    coherent_plan = or_(table.plan_id.is_(None), and_(Plan.id.is_not(None),
        Plan.gym_id == scope, Cliente.id.is_not(None), Cliente.gym_id == scope))
    filters = [table.persisted_at.is_not(None),
               table.persisted_at < cutoff if exclusive else table.persisted_at <= cutoff, coherent_plan]
    if context == "gym":
        referenced_client = aliased(Cliente)
        query = query.outerjoin(referenced_client, and_(referenced_client.id_cliente == Gym.client_id,
            referenced_client.gym_id == Gym.gym_id))
        filters.extend([Gym.gym_id == scope, Gym.status.in_(("reserved", "completed")),
            or_(Gym.client_id.is_(None), referenced_client.id.is_not(None)),
            or_(Gym.plan_id.is_(None), Gym.client_id.is_(None), Gym.client_id == Plan.id_cliente)])
    else:
        filters.extend([Personal.user_id == scope, Personal.publication_protocol == 1, Personal.status == "completed"])
    return [domain.storage_instant(row.persisted_at) for row in _rows(db, query.where(*filters).distinct())]


def _preparation(db, scope, context):
    client = select(Cliente.id).where(Cliente.gym_id == scope, Cliente.activo.is_(True), Cliente.deleted_at.is_(None))
    plan = select(Plan.id).join(Cliente, and_(Cliente.id_cliente == Plan.id_cliente,
        Cliente.gym_id == Plan.gym_id)).where(Plan.gym_id == scope, Cliente.gym_id == scope,
        Plan.deleted_at.is_(None), Cliente.deleted_at.is_(None), Cliente.activo.is_(True))
    return dict(zip(("client_registered", "plan_saved") if context == "gym" else ("profile_present", "plan_present"),
                    (bool(db.scalar(select(exists(client)))), bool(db.scalar(select(exists(plan)))))))


def _link_source(scope):
    recipient = aliased(Usuario)
    source = Link.__table__.join(Cliente, and_(Cliente.gym_id == Link.gym_id, Cliente.id_cliente == Link.client_id))
    source = source.join(Invitation, and_(Invitation.gym_id == Link.gym_id,
        Invitation.client_id == Link.client_id, Invitation.link_id == Link.id))
    source = source.join(recipient, recipient.id == Link.user_id)
    conditions = [Link.gym_id == scope, Link.status.in_(("active", "revoked")), Link.accepted_at.is_not(None),
        Link.user_id.is_not(None), Invitation.status == "consumed", Invitation.consumed_by == Link.user_id,
        Invitation.consumed_at == Link.accepted_at, Invitation.consumed_at < Invitation.expires_at,
        or_(and_(Link.status == "active", Link.revoked_at.is_(None)),
            and_(Link.status == "revoked", Link.revoked_at >= Link.accepted_at))]
    return source, conditions


def _links(db, scope, cutoff, *, exclusive=False):
    source, conditions = _link_source(scope)
    cut = cutoff.replace(tzinfo=None)
    accepted = _rows(db, select(Link.id, Link.accepted_at).select_from(source).where(
        *conditions, Link.accepted_at < cut if exclusive else Link.accepted_at <= cut).distinct())
    source = source.join(Publication, and_(Publication.gym_id == Link.gym_id,
        Publication.client_id == Link.client_id, Publication.link_id == Link.id)).join(Plan, and_(
        Plan.id == Publication.source_plan_id, Plan.id_cliente == Publication.client_id, Plan.gym_id == Publication.gym_id))
    publications = _rows(db, select(Publication.id, Publication.published_at, Publication.status).select_from(source).where(
        *conditions, Publication.gym_id == scope,
        Publication.published_at < cut if exclusive else Publication.published_at <= cut,
        Publication.published_at >= Link.accepted_at,
        or_(and_(Publication.status == "withdrawn", Publication.withdrawn_at >= Publication.published_at),
            and_(Publication.status == "published", Publication.withdrawn_at.is_(None), Link.status == "active",
                Plan.deleted_at.is_(None), Cliente.deleted_at.is_(None), Cliente.activo.is_(True)))).distinct())
    return ([domain.storage_instant(row.accepted_at) for row in accepted],
        [(domain.storage_instant(row.published_at), row.status) for row in publications])


def _cleanup(db):
    failed = False
    for operation in (db.rollback, db.close):
        try:
            operation()
        except Exception as error:  # noqa: BLE001 -- cleanup uncertainty must deny a response
            failed = True
            logger.error("Analytics cleanup unavailable class=%s", type(error).__name__)
    if failed:
        try:
            db.invalidate()
        except Exception as error:  # noqa: BLE001 -- only this owned Session is invalidated
            logger.error("Analytics invalidation unavailable class=%s", type(error).__name__)
        fail(503, "analytics_unavailable")


def read_report(principal, context, start=None, through=None, *, factory=None, now=None, reported_build=None):
    """Return only after read-TX and owned connection cleanup is confirmed."""
    # Validate before creating a Session. R31 bearer verification is unchanged.
    try:
        stamp = domain.instant(now)
        first, last = domain.period(start, through, now=stamp)
        if context not in ("gym", "personal"):
            raise domain.AnalyticsInput("Unknown context")
    except domain.AnalyticsInput:
        fail(422, "analytics_invalid_input")
    token = current_tenant.set("")
    db = None
    try:
        try:
            if factory is None:
                from web.database.engine import SessionLocal
                factory = SessionLocal
            db = factory()
            _snapshot(db)
            scope = _authority(db, principal, context)
            from web.database.schema_control import expected_head
            revisions = db.scalars(text("SELECT version_num FROM alembic_version")).all()
            if revisions != [expected_head()]:
                raise RuntimeError("Analytics schema unavailable")
            _, upper, cutoff = domain.boundaries(first, last, stamp)
            saved = _saved(db, scope, context, cutoff, exclusive=upper <= stamp)
            accepted, assigned = _links(db, scope, cutoff, exclusive=upper <= stamp) if context == "gym" else ([], [])
            result = domain.build_report(context, _preparation(db, scope, context), saved, accepted, assigned,
                now=stamp, start=first.isoformat(), through=last.isoformat(), schema_revision=revisions[0],
                reported_build=reported_build)
        except domain.AnalyticsVolume:
            fail(413, "analytics_volume_limit")
        except HTTPException:
            raise
        except Exception as error:  # noqa: BLE001 -- unknown driver failures are opaque503
            logger.error("Analytics unavailable class=%s", type(error).__name__)
            fail(503, "analytics_unavailable")
        finally:
            if db is not None:
                _cleanup(db)
        return result
    finally:
        current_tenant.reset(token)

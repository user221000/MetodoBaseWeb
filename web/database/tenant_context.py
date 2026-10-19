"""Explicit tenant context for every application transaction and trusted job.

The application chooses this identity only after principal/provider validation.
It is not a user-controlled header, query parameter, role bypass or SQL filter.
PostgreSQL RLS still denies access when the selected identity is absent.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from inspect import signature

from sqlalchemy import event, text
from sqlalchemy.orm import Session

current_tenant: ContextVar[str] = ContextVar("current_tenant", default="")
_TENANT_SQL = text("SELECT set_config('app.current_tenant', :tenant, true)")


def _tenant(value) -> str:
    if value is None:
        return ""
    if not isinstance(value, str) or len(value) > 36:
        raise ValueError("Invalid tenant context")
    return value


@contextmanager
def tenant_scope(tenant_id: str):
    """Run already-authorized background work under one explicit identity."""
    identity = _tenant(tenant_id)
    if not identity:
        raise ValueError("Background work requires an explicit tenant")
    existing = _tenant(current_tenant.get())
    if existing and existing != identity:
        raise ValueError("Background tenant differs from the authorized request")
    token = current_tenant.set(identity)
    try:
        yield
    finally:
        current_tenant.reset(token)


def tenant_task(parameter: str):
    """Carry a caller-authorized tenant into a standalone synchronous worker."""
    def decorate(function):
        parameters = signature(function)
        @wraps(function)
        def run(*args, **kwargs):
            identity = parameters.bind(*args, **kwargs).arguments[parameter]
            with tenant_scope(identity):
                return function(*args, **kwargs)
        return run
    return decorate


def _on_engine_begin(connection):
    # An explicit empty LOCAL value also overrides any residual session value.
    # Failure propagates: no query proceeds after an uncertain context install.
    identity = _tenant(current_tenant.get())
    connection.execute(_TENANT_SQL, {"tenant": identity})
    # A prior session-level purpose setting must never survive pool reuse.
    # No capability is carried across commits or inferred from a tenant ID.
    connection.execute(text("SELECT set_config('app.client_invitation_digest', '', true)"))
    connection.info["_tenant_tx_identity"] = identity


def _on_session_begin(session, transaction, connection):
    if not getattr(connection.engine, "_metodobase_tenant_context", False):
        return
    requested = _tenant(current_tenant.get())
    identity = _tenant(session.info.setdefault("tenant_id", requested))
    if requested and identity and requested != identity:
        raise ValueError("Session cannot switch tenant identity")
    if connection.info.get("_tenant_tx_identity") != identity:
        connection.execute(_TENANT_SQL, {"tenant": identity})
        connection.info["_tenant_tx_identity"] = identity


def configure_tenant_engine(engine):
    """Install transaction hooks once, including direct Session(engine) users."""
    if engine.dialect.name != "postgresql":
        return engine
    if not event.contains(engine, "begin", _on_engine_begin):
        event.listen(engine, "begin", _on_engine_begin)
    engine._metodobase_tenant_context = True
    if not event.contains(Session, "after_begin", _on_session_begin):
        event.listen(Session, "after_begin", _on_session_begin)
    return engine


def bind_verified_subject(db: Session, subject_id: str) -> None:
    """Bind a verified subject to this session across internal commits.

    Callers first verify a durable provider identity, invitation token, or the
    newly persisted account created by the current registration flow. A request
    or session already scoped to another account cannot change identities.
    A fresh callback session may inspect control-plane purchase identities
    before binding, but cannot read tenant billing data until this succeeds.
    """
    identity = _tenant(subject_id)
    if not identity:
        raise ValueError("Verified subject is required")
    requested = _tenant(current_tenant.get())
    existing = _tenant(db.info.get("tenant_id"))
    if (requested and requested != identity) or (existing and existing != identity):
        raise ValueError("Tenant identity mismatch")
    db.info["tenant_id"] = identity
    bind = db.get_bind()
    if bind.dialect.name == "postgresql":
        configure_tenant_engine(getattr(bind, "engine", bind))
        db.execute(_TENANT_SQL, {"tenant": identity})
        db.connection().info["_tenant_tx_identity"] = identity

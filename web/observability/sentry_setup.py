"""Classified telemetry only: private payloads never leave through Sentry.

This is a closed projection, not a recursive secret-name blocklist. Unknown
fields are dropped, including future SDK fields. The authorized local security
audit remains separate. Profiles, attachments, session reports and independent
log/metric channels require their own review before they can be enabled.
"""
from datetime import datetime, timezone
import logging
import math
import re
import sys
from types import ModuleType
from typing import Any

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.logging import LoggingIntegration


logger = logging.getLogger("sentry_setup")
_LEVELS = frozenset({"debug", "info", "warning", "error", "fatal"})
_ROLES = frozenset({"owner", "admin", "nutriologo", "viewer"})
_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"})
_OPERATIONS = frozenset({"http.server", "http.client", "db", "db.sql.query", "function"})
_STATUSES = frozenset({"ok", "unknown_error", "internal_error", "cancelled", "deadline_exceeded",
                       "permission_denied", "resource_exhausted", "unavailable", "not_found"})
_ENVIRONMENTS = frozenset({"development", "staging", "production", "test"})
_EXCEPTION_TYPES = frozenset({
    "Exception", "RuntimeError", "ValueError", "TypeError", "KeyError", "IndexError",
    "AttributeError", "AssertionError", "ArithmeticError", "ZeroDivisionError", "OverflowError",
    "OSError", "IOError", "FileNotFoundError", "PermissionError", "TimeoutError", "ConnectionError",
    "MemoryError", "RecursionError", "NotImplementedError", "UnicodeError", "UnicodeDecodeError",
    "JSONDecodeError", "StatementError", "IntegrityError", "OperationalError", "DBAPIError",
    "DataError", "ProgrammingError", "InvalidRequestError", "PendingRollbackError",
    "ObjectUnavailable", "ObjectIntegrityError", "ObjectNotFound", "ObjectOwnershipError",
})
FILTERED_EXCEPTIONS = {
    "ValidationError", "RequestValidationError", "HTTPException", "StarletteHTTPException", "HTTPStatusError",
}


def init_sentry(dsn: str, environment: str, traces_rate: float, profiles_rate: float) -> None:
    """Initialize reviewed error/transaction channels; profiles_rate is legacy.

    Profiles and streaming channels bypass the event projection in SDK 2.72.0.
    Keep the argument for callers, but do not enable those channels implicitly.
    """
    if not dsn:
        logger.info("Sentry DSN no configurado, observabilidad deshabilitada")
        return
    safe_environment = _one_of(environment, _ENVIRONMENTS, "unknown")
    sentry_sdk.init(
        dsn=dsn, environment=safe_environment, traces_sample_rate=traces_rate,
        profiles_sample_rate=0.0, profile_session_sample_rate=0.0,
        trace_lifecycle="static", stream_gen_ai_spans=False,
        integrations=[FastApiIntegration(transaction_style="endpoint"), SqlalchemyIntegration(),
                      LoggingIntegration(level=logging.WARNING, event_level=logging.ERROR)],
        before_send=_filter_events, before_send_transaction=_filter_transactions,
        before_breadcrumb=_drop_breadcrumb,
        data_collection={
            "user_info": False, "cookies": {"mode": "off"},
            "http_headers": {"request": {"mode": "off"}}, "http_bodies": [],
            "url_query_params": {"mode": "off"},
            "graphql": {"document": False, "variables": False},
            "gen_ai": {"inputs": False, "outputs": False},
            "database_query_data": False, "queues": False,
            "stack_frame_variables": False, "frame_context_lines": 0,
        },
        include_local_variables=False, include_source_context=False,
        max_request_body_size="never", enable_db_query_source=False, enable_http_request_source=False,
        enable_logs=False, enable_metrics=False, auto_session_tracking=False,
        propagate_traces=False, debug=False,
    )
    logger.info("Sentry initialized environment=%s", safe_environment)


def _one_of(value: Any, allowed: frozenset[str], default: str) -> str:
    return value if isinstance(value, str) and value in allowed else default


def _hex(value: Any, length: int) -> str | None:
    if isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{" + str(length) + r"}", value):
        return value.lower()
    return None


def _timestamp(value: Any) -> float | None:
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return None
            value = parsed.astimezone(timezone.utc).timestamp()
        except (ValueError, OverflowError, OSError):
            return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if 0 <= value <= 4102444800 and math.isfinite(value):
            return float(value)
    return None


def _technical_context(context: Any) -> dict[str, Any]:
    if not isinstance(context, dict):
        return {}
    result = {}
    for name, length in (("trace_id", 32), ("span_id", 16), ("parent_span_id", 16)):
        identifier = _hex(context.get(name), length)
        if identifier is not None:
            result[name] = identifier
    result["op"] = _one_of(context.get("op"), _OPERATIONS, "function")
    if isinstance(context.get("status"), str) and context["status"] in _STATUSES:
        result["status"] = context["status"]
    return result


def _application_frames(value: Any) -> list[dict[str, Any]]:
    """Retain loaded application module + line, never paths, source or locals.

    Module names must be real loaded first-party Python modules. Deriving the
    filename from that name avoids copying an arbitrary filename from an event.
    """
    if not isinstance(value, dict) or not isinstance(value.get("frames"), list):
        return []
    frames = []
    for frame in value["frames"][-40:]:
        if not isinstance(frame, dict):
            continue
        name = frame.get("module")
        line = frame.get("lineno")
        if not isinstance(name, str) or not name.startswith(("web.", "api.", "core.")):
            continue
        if not re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+", name, flags=re.ASCII):
            continue
        if not isinstance(sys.modules.get(name), ModuleType):
            continue
        if not isinstance(line, int) or isinstance(line, bool) or not 1 <= line <= 1000000:
            continue
        frames.append({"module": name, "filename": name.replace(".", "/") + ".py",
                       "lineno": line, "in_app": True})
    return frames


def _project_event(event: dict[str, Any], transaction: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {"platform": "python"}
    identifier = _hex(event.get("event_id"), 32)
    if identifier is not None:
        result["event_id"] = identifier
    for name in ("timestamp", "start_timestamp"):
        timestamp = _timestamp(event.get(name))
        if timestamp is not None:
            result[name] = timestamp
    if "level" in event:
        result["level"] = _one_of(event["level"], _LEVELS, "error")
    if "environment" in event:
        result["environment"] = _one_of(event["environment"], _ENVIRONMENTS, "unknown")
    release = _hex(event.get("release"), 40) or _hex(event.get("release"), 64)
    if release is not None:
        result["release"] = release
    tags = event.get("tags")
    if isinstance(tags, dict) and isinstance(tags.get("role"), str) and tags["role"] in _ROLES:
        result["tags"] = {"role": tags["role"]}
    request = event.get("request")
    if isinstance(request, dict) and isinstance(request.get("method"), str) and request["method"] in _METHODS:
        result["request"] = {"method": request["method"]}
    contexts = event.get("contexts")
    if isinstance(contexts, dict) and isinstance(contexts.get("trace"), dict):
        result["contexts"] = {"trace": _technical_context(contexts["trace"])}
    if transaction:
        result.update(type="transaction", transaction="http.server", transaction_info={"source": "custom"})
        result["spans"] = []
        spans = event.get("spans")
        for span in spans[:200] if isinstance(spans, list) else []:
            if not isinstance(span, dict):
                continue
            projected = _technical_context(span)
            for name in ("timestamp", "start_timestamp"):
                timestamp = _timestamp(span.get(name))
                if timestamp is not None:
                    projected[name] = timestamp
            if "span_id" in projected and "trace_id" in projected:
                result["spans"].append(projected)
    else:
        exceptions = event.get("exception")
        values = exceptions.get("values") if isinstance(exceptions, dict) else None
        projected_values = []
        for value in values[-10:] if isinstance(values, list) else []:
            if not isinstance(value, dict):
                continue
            projected = {"type": _one_of(value.get("type"), _EXCEPTION_TYPES, "ApplicationError"),
                         "value": "Application error"}
            frames = _application_frames(value.get("stacktrace"))
            if frames:
                projected["stacktrace"] = {"frames": frames}
            projected_values.append(projected)
        if projected_values:
            result["exception"] = {"values": projected_values}
        else:
            result["message"] = "Application event"
    return result


def _filter_events(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    # SDK builds envelope attachments from hint after this callback, separately
    # from event serialization. Dropping event fields alone would leave bytes.
    hint["attachments"] = []
    exceptions = event.get("exception")
    values = exceptions.get("values") if isinstance(exceptions, dict) else None
    if isinstance(values, list) and values and isinstance(values[0], dict):
        if isinstance(values[0].get("type"), str) and values[0]["type"] in FILTERED_EXCEPTIONS:
            return None
    return _project_event(event)


def _filter_transactions(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    hint["attachments"] = []
    if event.get("transaction") in ("/health", "/health/ready", "/metrics", "/alerts"):
        return None
    return _project_event(event, transaction=True)


def _drop_breadcrumb(crumb: dict[str, Any], hint: dict[str, Any]) -> None:
    """Unstructured HTTP, SQL and logging breadcrumbs are not an approved sink."""
    return None


def set_user_context(user_id: str, gym_id: str, role: str) -> None:
    """Keep caller compatibility without forwarding personal/tenant identifiers."""
    sentry_sdk.set_user(None)
    sentry_sdk.set_tag("role", _one_of(role, _ROLES, "unknown"))


def capture_business_error(message: str, extra: dict[str, Any] | None = None) -> None:
    """Record a stable business error category; legacy free text is not copied."""
    sentry_sdk.capture_message("Business operation failed", level="error")

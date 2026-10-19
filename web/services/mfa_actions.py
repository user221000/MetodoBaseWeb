"""Closed action/body registry shared by issuing and consuming a step-up grant."""
import hashlib
import json
import re

from pydantic import ValidationError

from web.services.mfa_service import fail


def specification(method, path, body, idempotency_key=None):
    from web.routes import billing, team
    from api.routes.pagos import CrearSesionRequest
    registry = {
        ("POST", "/api/gym/team/invite"): ("team.invite", team.TeamInviteRequest),
        ("POST", "/api/billing/checkout"): ("billing.checkout", billing.CheckoutRequest),
        ("POST", "/api/billing/stripe/subscribe"): ("billing.subscribe", billing.StripeSubscribeRequest),
        ("POST", "/api/billing/confirm-subscription"): ("billing.confirm", billing.ConfirmSubscriptionRequest),
        ("POST", "/api/billing/portal"): ("billing.portal", billing.PortalRequest),
        ("POST", "/api/billing/mp/preference"): ("billing.mp", billing.MPPreferenceRequest),
        ("POST", "/api/pagos/stripe/session"): ("billing.checkout", CrearSesionRequest),
        ("POST", "/api/pagos/mp/preference"): ("billing.mp", CrearSesionRequest),
    }
    target = None
    entry = registry.get((method, path))
    if entry is None:
        match = re.fullmatch(r"/api/gym/team/([A-Za-z0-9_-]{1,36})(/role|/resend-invite)?", path)
        if match:
            target, suffix = match.groups()
            if (method, suffix) == ("PATCH", "/role"):
                entry = ("team.role", team.UpdateRoleRequest)
            elif (method, suffix) == ("POST", "/resend-invite"):
                entry = ("team.resend", None)
            elif (method, suffix) == ("DELETE", None):
                entry = ("team.remove", None)
    if entry is None or not isinstance(body, dict):
        fail(422, "mfa_action_invalid")
    action, schema = entry
    try:
        if schema is None:
            if body:
                fail(422, "mfa_action_invalid")
            normalized = {}
        else:
            # Historic endpoint DTOs may allow extra keys; a grant does not.
            if set(body) - set(schema.model_fields):
                fail(422, "mfa_action_invalid")
            normalized = schema.model_validate(body).model_dump(mode="json")
    except (ValidationError, ValueError):
        fail(422, "mfa_action_invalid")
    if action == "billing.portal":
        from web.services.return_paths import private_return_path
        try:
            private_return_path(normalized["return_url"])
        except ValueError:
            fail(400, "mfa_action_invalid")
    financial_key = action in {"billing.checkout", "billing.subscribe", "billing.mp"}
    if idempotency_key is not None and (not financial_key or not isinstance(idempotency_key, str)
            or not 1 <= len(idempotency_key) <= 128 or not idempotency_key.isascii()):
        fail(422, "mfa_action_invalid")
    return action, target, {"method": method, "path": path, "body": normalized,
                            "idempotency_key": idempotency_key}


def binding(spec, gym_id):
    encoded = json.dumps({"gym_id": gym_id, **spec}, sort_keys=True,
        ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode("ascii")
    if len(encoded) > 32768:
        fail(422, "mfa_action_invalid")
    return hashlib.sha256(encoded).hexdigest()


def authorize(db, identity, action, target_id):
    from sqlalchemy import select
    from web.database.models import Usuario, UserRole
    from web.services.permissions import verify_permission, can_manage_user
    gym_id = identity.get("team_gym_id") or identity["id"]
    role = identity["role"]
    if role not in {"owner", "admin"}:
        fail(403, "mfa_action_forbidden")
    owner = db.get(Usuario, gym_id, populate_existing=True)
    if (not owner or not owner.activo or owner.deleted_at is not None or owner.team_gym_id
            or owner.tipo != "gym" or owner.role != UserRole.OWNER):
        fail(403, "mfa_action_forbidden")
    if action.startswith("billing."):
        verify_permission(identity, "update", "subscription", gym_id)
        if identity["id"] != gym_id:
            fail(403, "mfa_action_forbidden")
    else:
        permission = {"team.invite": "invite", "team.resend": "invite",
            "team.role": "update_role", "team.remove": "remove"}[action]
        verify_permission(identity, permission, "team", gym_id)
        if target_id is not None:
            target = db.scalar(select(Usuario).where(Usuario.id == target_id,
                Usuario.team_gym_id == gym_id, Usuario.deleted_at.is_(None)))
            if (not target or target.role == UserRole.OWNER or
                    not can_manage_user(identity, {"id": target.id, "role": target.role.value})):
                fail(403, "mfa_action_forbidden")
    return gym_id

"""Explicit browser transport for existing revocable authentication tokens.

Only the refresh proof uses an HttpOnly cookie. Resource authorization continues
to require an access bearer; the cookie never becomes general API authority.
"""
import json
import logging
import math
import time
from urllib.parse import urlsplit, urlunsplit

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

logger = logging.getLogger(__name__)
HEADERS = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}
HEADER = "x-metodobase-browser"
PRIMARY = frozenset({"/api/auth/login", "/api/auth/google", "/api/auth/registro", "/api/auth/accept-invite"})
REVOKING = frozenset({"/api/auth/mfa/enroll/confirm", "/api/auth/mfa/recovery-codes/regenerate",
                     "/api/auth/mfa/revoke", "/api/auth/google/link/confirm", "/api/auth/google/link/unlink"})
COOKIE_POSTS = PRIMARY | REVOKING | frozenset({
    "/api/auth/refresh", "/api/auth/browser/migrate", "/api/auth/browser/logout",
    "/api/auth/mfa/login/verify", "/api/auth/mfa/reauth", "/api/auth/mfa/enroll",
    "/api/auth/mfa/step-up", "/api/auth/google/link/start",
})


def is_browser_session_private(path):
    return path in COOKIE_POSTS or (path.endswith("/") and path[:-1] in COOKIE_POSTS)


def failure(status, code):
    messages = {"browser_session_unavailable": "Inicia sesión para continuar.",
                "browser_session_unconfirmed": "No se pudo confirmar la sesión. Vuelve a iniciar sesión.",
                "browser_origin_invalid": "El origen de la solicitud no es válido.",
                "browser_input_invalid": "La solicitud de sesión no es válida."}
    raise HTTPException(status, {"code": code, "message": messages.get(code, messages["browser_input_invalid"])},
                        headers=HEADERS)


def browser_request(request):
    return HEADER in request.headers


def configuration():
    """An explicit canonical origin; HTTP is allowed only for local development."""
    from web.settings import get_settings
    settings = get_settings()
    try:
        parsed = urlsplit(settings.BASE_URL)
        if (not parsed.hostname or parsed.username or parsed.password or parsed.path not in {"", "/"}
                or parsed.query or parsed.fragment or any(ord(char) < 33 for char in settings.BASE_URL)
                or "\\" in parsed.netloc or "%" in parsed.netloc or parsed.scheme not in {"https", "http"}
                or (parsed.scheme == "http" and (settings.is_production or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}))):
            raise ValueError("Invalid browser origin configuration")
        _ = parsed.port
        origin = urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
        secure = parsed.scheme == "https"
        return origin, "__Host-mb_refresh" if secure else "mb_refresh_dev", secure
    except (ValueError, TypeError, AttributeError):
        failure(503, "browser_session_unconfirmed")


def admit(request):
    """Run before dependencies, credentials, provider calls or token mutations."""
    origin, _, _ = configuration()
    if (request.headers.getlist(HEADER) != ["1"] or request.headers.getlist("origin") != [origin]
            or request.method != "POST" or request.url.path not in COOKIE_POSTS
            or request.url.query):
        failure(403, "browser_origin_invalid")
    content_types = request.headers.getlist("content-type")
    if len(content_types) != 1 or content_types[0].lower().replace(" ", "") not in {
        "application/json", "application/json;charset=utf-8",
    }:
        failure(415, "browser_input_invalid")


def expire_cookie(response):
    _, name, secure = configuration()
    response.delete_cookie(name, path="/", secure=secure, httponly=True, samesite="strict")


def cookie_proof(request):
    """Reject ambiguous cookie duplicates instead of letting a parser pick one."""
    _, name, _ = configuration()
    pairs = [part.strip().split("=", 1) for header in request.headers.getlist("cookie") for part in header.split(";")]
    proofs = [pair[1] for pair in pairs if len(pair) == 2 and pair[0] == name]
    if len(proofs) != 1 or not proofs[0] or len(proofs[0]) > 8192:
        return None
    return proofs[0]


async def body(request, *, migration=False):
    """Small closed JSON object; duplicates and nonfinite values are rejected."""
    from pydantic import BaseModel, ConfigDict, Field

    from web.routes.mfa import parse

    class Empty(BaseModel):
        model_config = ConfigDict(extra="forbid", strict=True)

    class Migration(Empty):
        refresh_token: str = Field(min_length=1, max_length=8192)

    return await parse(request, Migration if migration else Empty)


def rotate(request, proof):
    from web.auth import rotar_refresh_token
    if not proof:
        failure(401, "browser_session_unavailable")
    result = rotar_refresh_token(proof)
    if not result:
        failure(401, "browser_session_unavailable")
    return {"token": result["access_token"], "refresh_token": result["refresh_token"]}


def _browser_response(response, request):
    """Adapt only a committed token pair. ACKs retain their existing schema."""
    data = json.loads(response.body) if response.body and response.media_type == "application/json" else None
    if isinstance(data, dict) and response.status_code == 200 and "refresh_token" in data:
        from web.auth import _decode_token, _valid_token_payload
        proof = data["refresh_token"]
        payload = _decode_token(proof)
        access = data.get("token") or data.get("access_token")
        if not _valid_token_payload(payload, "refresh") or not isinstance(access, str) or not access:
            failure(503, "browser_session_unconfirmed")
        remaining = math.floor(payload["exp"] - time.time())
        if remaining < 1:
            failure(503, "browser_session_unconfirmed")
        data = {key: value for key, value in data.items() if key != "refresh_token"}
        data.update(token=access, session_mode="browser")
        response.body = json.dumps(data, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
        response.headers["content-length"] = str(len(response.body))
        _, name, secure = configuration()
        response.set_cookie(name, proof, max_age=remaining, path="/", secure=secure, httponly=True, samesite="strict")
    elif request.url.path in PRIMARY or (request.url.path in REVOKING and response.status_code < 300):
        if isinstance(data, dict) and response.status_code == 202 and data.get("mfa_required") is True:
            data["session_mode"] = "browser"
            response.body = json.dumps(data, separators=(",", ":")).encode()
            response.headers["content-length"] = str(len(response.body))
        expire_cookie(response)
    response.headers.update(HEADERS)
    return response


class BrowserAuthRoute(APIRoute):
    """Opt-in transport; callers without the browser header keep legacy JSON."""
    def get_route_handler(self):
        original = super().get_route_handler()

        async def handle(request: Request):
            if not browser_request(request):
                return await original(request)
            # An invalid Origin cannot clear or replace a same-site cookie.
            admit(request)
            try:
                response = await original(request)
                return _browser_response(response, request)
            except HTTPException as error:
                response = JSONResponse({"detail": error.detail}, status_code=error.status_code,
                                        headers={**(error.headers or {}), **HEADERS})
            except RequestValidationError:
                response = JSONResponse({"detail": {"code": "browser_input_invalid", "message": "Solicitud no válida."}},
                                        status_code=422, headers=HEADERS)
            except Exception as error:
                logger.exception("Browser session unconfirmed class=%s", type(error).__name__, exc_info=None)
                response = JSONResponse({"detail": {"code": "browser_session_unconfirmed", "message": "No se pudo confirmar la sesión."}},
                                        status_code=503, headers=HEADERS)
            if request.url.path in PRIMARY or request.url.path in {"/api/auth/refresh", "/api/auth/browser/migrate", "/api/auth/browser/logout"}:
                expire_cookie(response)
            return response
        return handle

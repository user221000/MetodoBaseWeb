"""Google verified transport and stable identity, independent from contact email.

Official google-auth verifies provider JWTs against a fixed HTTPS JWKS port.
This repairs account association without treating provider email as authority.
No caller-supplied endpoint or custom JWT verification is used.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import re

from fastapi import HTTPException
import httpx
from web.account_values import normalize_account_email

ISSUER = "https://accounts.google.com"


def _invalid():
    raise HTTPException(401, {"code":"google_identity_invalid","message":"No se pudo verificar la identidad de Google."})


def _integer(value):
    if isinstance(value, str) and re.fullmatch(r"[0-9]{1,12}", value):
        return int(value)
    return value if type(value) is int else None


async def verified_google_info(credential):
    from web.settings import get_settings
    client_id = get_settings().GOOGLE_CLIENT_ID.strip()
    if not client_id:
        raise HTTPException(501, "Google login no esta configurado.")
    if not isinstance(credential, str) or not 1 <= len(credential) <= 16384:
        _invalid()
    try:
        from google.oauth2 import id_token
        from starlette.concurrency import run_in_threadpool
        # Keys come only from Google's fixed HTTPS JWKS endpoint. Bound reads
        # precede official library verification; no input token is put in a URL.
        endpoint="https://www.googleapis.com/oauth2/v3/certs"
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            async with client.stream("GET",endpoint) as response:
                if response.status_code!=200:
                    _invalid()
                payload=bytearray()
                async for chunk in response.aiter_bytes():
                    if len(payload)+len(chunk)>131072:
                        _invalid()
                    payload.extend(chunk)
        class CertificateResponse:
            status=200
            data=bytes(payload)
            headers={"content-type":"application/json"}
        def certificates(url,method="GET",**kwargs):
            if url!=endpoint or method!="GET":
                raise ValueError("Unapproved Google certificates request")
            return CertificateResponse()
        # google-auth and its existing PyJWT dependency implement signature,
        # algorithm, audience, issued-at and expiry checks. No custom crypto.
        info=await run_in_threadpool(id_token.verify_token,credential,certificates,
            audience=client_id,certs_url=endpoint,clock_skew_in_seconds=0)
    except HTTPException:
        raise
    except Exception:
        _invalid()
    if (not isinstance(info, dict) or info.get("aud") != client_id
            or not (info.get("email_verified") is True or info.get("email_verified")=="true") or not isinstance(info.get("email"), str)
            or info.get("iss") not in {ISSUER,"accounts.google.com"}
            or not isinstance(info.get("sub"), str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,255}", info["sub"])):
        _invalid()
    expiry = _integer(info.get("exp"))
    if expiry is None or expiry <= datetime.now(timezone.utc).timestamp():
        _invalid()
    try:
        email = normalize_account_email(info["email"])
    except (ValueError, TypeError):
        _invalid()
    return {**info,"email":email,"iss":ISSUER}


@dataclass(frozen=True)
class VerifiedGooglePrimary:
    issuer: str
    subject: str
    email: str
    authenticated_at: datetime


async def verified_google_reauthentication(credential, *, now=None):
    """Only verified fresh auth_time; token issuance never substitutes for it."""
    info = await verified_google_info(credential)
    value = _integer(info.get("auth_time"))
    clock = datetime.now(timezone.utc) if now is None else now
    if value is None or not 0 <= clock.timestamp()-value < 300:
        raise HTTPException(403, {"code":"mfa_primary_reauthentication_required",
            "message":"Vuelve a autenticarte con tu proveedor o con tu contrasena para cambiar la seguridad de la cuenta."})
    return VerifiedGooglePrimary(info["iss"],info["sub"],info["email"],datetime.fromtimestamp(value,timezone.utc))


def bound_user_id(db, issuer, subject):
    """One exact control-plane lookup; email never chooses an account."""
    from sqlalchemy import select
    from web.database.models import AuthExternalIdentity
    return db.scalar(select(AuthExternalIdentity.user_id).where(
        AuthExternalIdentity.issuer==issuer,AuthExternalIdentity.subject==subject,AuthExternalIdentity.revoked_at.is_(None)))


def primary_matches(db, user_id, primary):
    return (isinstance(primary, VerifiedGooglePrimary)
        and primary.issuer==ISSUER and bound_user_id(db,primary.issuer,primary.subject)==user_id)

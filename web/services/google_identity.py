"""One verified Google primary identity, shared by login and fresh reauth.

The fixed provider endpoint is transport authority. No body email or arbitrary
endpoint is accepted; tests substitute only its HTTP transport.
"""
from fastapi import HTTPException
import httpx
from dataclasses import dataclass
from datetime import datetime, timezone
import re
from web.account_values import normalize_account_email


async def verified_google_info(credential):
    from web.settings import get_settings
    client_id = get_settings().GOOGLE_CLIENT_ID.strip()
    if not client_id:
        raise HTTPException(501, "Google login no está configurado.")
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get("https://oauth2.googleapis.com/tokeninfo", params={"id_token": credential})
    if response.status_code != 200:
        raise HTTPException(401, "Token de Google inválido.")
    info = response.json()
    if (not isinstance(info, dict) or info.get("aud") != client_id
            or info.get("email_verified") != "true" or not isinstance(info.get("email"), str)):
        raise HTTPException(401, "Identidad de Google inválida.")
    return {**info, "email": normalize_account_email(info["email"])}


@dataclass(frozen=True)
class VerifiedGooglePrimary:
    email: str
    authenticated_at: datetime


async def verified_google_reauthentication(credential, *, now=None):
    """Google's verified auth_time is distinct from token issuance (iat).

    The MFA UI must request essential_claims='auth_time, amr' and an actual
    fresh Google authentication. Missing/old metadata never falls back to iat.
    """
    info = await verified_google_info(credential)
    value = info.get("auth_time")
    if isinstance(value, str) and re.fullmatch(r"[0-9]{1,12}", value):
        value = int(value)
    clock = datetime.now(timezone.utc) if now is None else now
    if type(value) is not int or not 0 <= clock.timestamp() - value < 300:
        raise HTTPException(403, {"code":"mfa_primary_reauthentication_required",
            "message":"Vuelve a autenticarte con tu proveedor o con tu contraseña para cambiar la seguridad de la cuenta."})
    return VerifiedGooglePrimary(info["email"], datetime.fromtimestamp(value,timezone.utc))

"""One verified Google primary identity, shared by login and fresh reauth.

The fixed provider endpoint is transport authority. No body email or arbitrary
endpoint is accepted; tests substitute only its HTTP transport.
"""
from fastapi import HTTPException
import httpx
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

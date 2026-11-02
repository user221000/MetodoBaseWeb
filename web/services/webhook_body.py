"""Bound payment webhook streams without changing the signed raw bytes."""
import logging

from fastapi import HTTPException, Request
from starlette.requests import ClientDisconnect

from web.settings import get_settings

logger = logging.getLogger(__name__)


async def read_webhook_body(request: Request) -> bytes:
    """Treat Content-Length as a hint; enforce the limit on received chunks."""
    limit = get_settings().WEBHOOK_MAX_BODY_BYTES
    lengths = request.headers.getlist("content-length")
    if len(lengths) > 1 or (lengths and (
            not lengths[0].isascii() or not lengths[0].isdigit()
            or len(lengths[0]) > 12 or request.headers.get("transfer-encoding"))):
        raise HTTPException(400, {"code": "webhook_content_length_invalid"})
    declared = int(lengths[0]) if lengths else None

    def too_large():
        # No payload, signature, query string or personal data in telemetry.
        logger.warning("Payment webhook body exceeds configured limit")
        raise HTTPException(413, {"code": "webhook_body_too_large"})

    if declared is not None and declared > limit:
        too_large()
    body = bytearray()
    try:
        async for chunk in request.stream():
            if len(body) + len(chunk) > limit:
                too_large()
            body.extend(chunk)
    except ClientDisconnect:
        raise HTTPException(400, {"code": "webhook_body_incomplete"}) from None
    if declared is not None and declared != len(body):
        raise HTTPException(400, {"code": "webhook_content_length_invalid"})
    return bytes(body)

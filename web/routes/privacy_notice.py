"""Public privacy information; no account reads, consent writes or tracking."""

import hashlib
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from web.services.privacy_notice import public_privacy_notice
from web.template_compat import template_response

_WEB = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(_WEB / "templates"))
router = APIRouter(include_in_schema=False)


@router.get("/privacidad", response_class=HTMLResponse)
async def privacy_information(request: Request):
    response = template_response(templates, request, "privacy_notice.html", {
        "request": request,
        "notice": public_privacy_notice(),
        "privacy_style_version": hashlib.sha256(
            (_WEB / "static" / "css" / "privacy-notice.css").read_bytes()
        ).hexdigest()[:12],
    })
    response.headers.update({
        "Cache-Control": "no-store",
        "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff",
    })
    return response

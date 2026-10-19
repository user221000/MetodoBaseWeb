"""Private operational endpoints and the same metrics boundary in both factories."""

import hmac
import os

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from web.middleware import (
    MetricsMiddleware,
    check_metrics_alerts,
    get_error_alerter,
    get_metrics_summary,
)


PRIVATE_HEADERS = {
    "Cache-Control": "no-store",
    "Pragma": "no-cache",
    "Referrer-Policy": "no-referrer",
}


def configure_observability(app: FastAPI) -> None:
    """Capture one configured operations key; keep request data out of metrics."""
    expected = os.environ.get("METRICS_API_KEY", "").encode("utf8")
    enabled = os.environ.get("METRICS_ENABLED", "true").lower() == "true"
    app.add_middleware(
        MetricsMiddleware,
        enabled=enabled,
        exclude_paths=["/metrics", "/alerts", "/health"],
    )

    def authorized(request: Request) -> bool:
        supplied = request.headers.get("X-Metrics-Key", "").encode("utf8")
        return bool(expected and supplied) and hmac.compare_digest(supplied, expected)

    def response(request: Request, read):
        # Return the denial directly so both factories preserve the same cache
        # policy even when their HTTP exception adapters differ.
        if not authorized(request):
            return JSONResponse(
                {"detail": "Forbidden"}, status_code=403, headers=PRIVATE_HEADERS
            )
        return JSONResponse(jsonable_encoder(read()), headers=PRIVATE_HEADERS)

    @app.get("/metrics", tags=["System"])
    async def metrics_endpoint(request: Request):
        def read():
            summary = get_metrics_summary()
            summary["alerts"] = check_metrics_alerts()
            return summary

        return response(request, read)

    @app.get("/alerts", tags=["System"])
    async def alerts_endpoint(request: Request):
        def read():
            alerter = get_error_alerter()
            return {
                "status": alerter.get_status(),
                "metrics_alerts": check_metrics_alerts(),
                "recent_alerts": alerter.get_alert_history(limit=10),
            }

        return response(request, read)

    @app.get("/health/circuits", tags=["System"])
    async def circuit_status(request: Request):
        from web.services.resilience import get_all_circuit_status

        return response(request, lambda: {"circuits": get_all_circuit_status()})

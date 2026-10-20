"""Private nutrition responses without echoing declaration input in errors."""
import logging

from fastapi import HTTPException
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from web.services.nutrition_profiles import NUTRITION_ERRORS, public_error

HEADERS = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}
logger = logging.getLogger(__name__)
_PROFILE_WRITES = frozenset({
    ("POST", "/clientes"),
    ("POST", "/api/clientes"),
    ("PUT", "/clientes/{id_cliente}"),
    ("PUT", "/api/clientes/{id_cliente}"),
    ("PUT", "/usuario/perfil"),
    ("PUT", "/api/usuario/perfil"),
})


class NutritionRoute(APIRoute):
    """Keep existing errors except bounded declaration/profile validation errors.

    FastAPI's ordinary validation payload includes submitted values. A profile
    request or any body carrying the new declaration instead receives a stable
    message without those values. This does not change identity or permissions.
    """

    def get_route_handler(self):
        original = super().get_route_handler()

        async def private(request):
            try:
                response = await original(request)
            except RequestValidationError as error:
                # A rejected envelope can itself contain health facts. Select
                # profile writes by their declared/mounted route templates,
                # regardless of body type or router-prefix implementation.
                if ((request.method, self.path) in _PROFILE_WRITES
                        or request.url.path.rstrip("/").endswith("/perfil")
                        or isinstance(error.body, dict) and "restricciones_nutricionales" in error.body):
                    return JSONResponse({"detail": {"code": "nutrition_profile_invalid_input",
                        "message": "Revisa los datos del perfil."}}, status_code=422, headers=HEADERS)
                response = await request_validation_exception_handler(request, error)
            except NUTRITION_ERRORS as error:
                status, detail = public_error(error)
                return JSONResponse({"detail": detail}, status_code=status, headers=HEADERS)
            except HTTPException as error:
                return JSONResponse({"detail": error.detail}, status_code=error.status_code,
                                    headers={**HEADERS, **(error.headers or {})})
            except Exception as error:
                # SQL/renderer exception text can contain declared facts.
                # Explicitly omit exception values and tracebacks from the log.
                logger.exception("Nutrition request failed class=%s", type(error).__name__, exc_info=None)
                body = {"detail": "Error interno del servidor"}
                request_id = getattr(request.state, "request_id", None)
                if request_id:
                    body["request_id"] = request_id
                return JSONResponse(body, status_code=500, headers=HEADERS)
            response.headers.update(HEADERS)
            return response

        return private

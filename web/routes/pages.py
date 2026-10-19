"""
web/routes/pages.py — HTML page routes (template rendering).
BUILD_VERSION: v6-TEMPLATEFIX-20260401

Extracted from web/main_web.py (god function) for maintainability.
"""
# BUILD MARKER: v6-20260401-2130-TEMPLATEFIX
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from web.template_compat import template_response
from core.plan_catalog import get_individual_plan_catalog, get_plan_catalog

_TMPL_DIR = Path(__file__).resolve().parent.parent / "templates"

templates = Jinja2Templates(directory=str(_TMPL_DIR))

# csrf_token is injected from main_web.py at startup (overrides this default)
from web.middleware.csrf import get_csrf_token as _csrf_token_fn
templates.env.globals["csrf_token"] = _csrf_token_fn

router = APIRouter(include_in_schema=False)


@router.get("/")
async def index(request: Request):
    return template_response(templates, request, "landing.html", {"request": request})


@router.get("/login-gym", response_class=HTMLResponse)
async def login_gym_page(request: Request):
    from config.settings import Settings
    _s = Settings()
    return template_response(
        templates,
        request,
        "login_gym.html",
        {"request": request, "google_client_id": _s.GOOGLE_CLIENT_ID},
    )


@router.get("/login-usuario", response_class=HTMLResponse)
async def login_usuario_page(request: Request):
    from config.settings import Settings
    _s = Settings()
    return template_response(
        templates,
        request,
        "login_usuario.html",
        {"request": request, "google_client_id": _s.GOOGLE_CLIENT_ID},
    )


@router.get("/registro", response_class=HTMLResponse)
async def registro_page(request: Request):
    return template_response(templates, request, "registro.html", {"request": request})


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return template_response(templates, request, "dashboard.html", {"request": request})


@router.get("/clientes", response_class=HTMLResponse)
async def clientes(request: Request):
    return template_response(templates, request, "clientes.html", {"request": request})


@router.get("/generar-plan", response_class=HTMLResponse)
async def generar_plan(request: Request):
    return template_response(templates, request, "generar-plan.html", {"request": request})


@router.get("/planes", response_class=HTMLResponse)
async def planes_historial(request: Request):
    return template_response(templates, request, "planes.html", {"request": request})


@router.get("/suscripciones", response_class=HTMLResponse)
async def suscripciones(request: Request):
    return template_response(
        templates,
        request,
        "suscripciones.html",
        {"request": request, "plan_catalog": get_plan_catalog(target="web")},
    )


@router.get("/configuracion", response_class=HTMLResponse)
async def configuracion(request: Request):
    return template_response(templates, request, "configuracion.html", {"request": request})


# ── Individual User Pages ─────────────────────────────────────────────────

@router.get("/mi-plan", response_class=HTMLResponse)
async def mi_plan_page(request: Request):
    return template_response(templates, request, "usuario_mi_plan.html", {"request": request})

@router.get("/mi-perfil", response_class=HTMLResponse)
async def mi_perfil_page(request: Request):
    return template_response(templates, request, "usuario_perfil.html", {"request": request})

@router.get("/mi-historial", response_class=HTMLResponse)
async def mi_historial_page(request: Request):
    return template_response(templates, request, "usuario_historial.html", {"request": request})

@router.get("/mi-suscripcion", response_class=HTMLResponse)
async def mi_suscripcion_page(request: Request):
    return template_response(templates, request, "usuario_suscripcion.html", {"request": request, "individual_plans": get_individual_plan_catalog()})

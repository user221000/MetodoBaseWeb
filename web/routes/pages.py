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
    import hashlib
    import json
    example = json.loads((_TMPL_DIR.parent / "static" / "data" / "landing-example.json").read_text(encoding="utf8"))
    return template_response(templates, request, "landing.html", {
        "request": request,
        "business_plans": {key: plan for key, plan in get_plan_catalog("web").items() if plan["audiencia"] == "gym"},
        "individual_plans": get_individual_plan_catalog(),
        "example": example,
        "landing_style_version": hashlib.sha256((_TMPL_DIR.parent / "static" / "css" / "landing.css").read_bytes()).hexdigest()[:12],
    })


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
    from config.settings import Settings
    _s = Settings()
    return template_response(templates, request, "configuracion.html", {"request": request, "google_client_id": _s.GOOGLE_CLIENT_ID})


@router.get("/equipo", response_class=HTMLResponse)
async def equipo_page(request: Request):
    return template_response(templates, request, "equipo.html", {"request": request})


@router.get("/equipo/inicio", response_class=HTMLResponse)
async def equipo_inicio_page(request: Request):
    return template_response(templates, request, "equipo_inicio.html", {"request": request})


@router.get("/auth/accept-invite", response_class=HTMLResponse)
async def accept_invite_page(request: Request):
    response = template_response(templates, request, "accept_invite.html", {"request": request})
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@router.get('/auth/reset-password',response_class=HTMLResponse)
async def reset_password_page(request:Request):
    response=template_response(templates,request,'account_recovery.html',{'request':request})
    response.headers.update({'Cache-Control':'no-store','Referrer-Policy':'no-referrer',
        'X-Content-Type-Options':'nosniff',
        'Content-Security-Policy':"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"})
    return response


@router.get('/retirar-consentimientos', response_class=HTMLResponse)
async def progress_retirement_page(request: Request):
    """Public purpose-only form; it never acquires general session authority."""
    response = template_response(templates, request, 'retiro_consentimientos.html', {'request': request})
    response.headers.update({'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer'})
    return response


# ── Individual User Pages ─────────────────────────────────────────────────

@router.get("/mi-plan", response_class=HTMLResponse)
async def mi_plan_page(request: Request):
    return template_response(templates, request, "usuario_mi_plan.html", {"request": request})

@router.get("/mi-perfil", response_class=HTMLResponse)
async def mi_perfil_page(request: Request):
    from config.settings import Settings
    _s = Settings()
    return template_response(templates, request, "usuario_perfil.html", {"request": request, "google_client_id": _s.GOOGLE_CLIENT_ID})

@router.get("/mi-historial", response_class=HTMLResponse)
async def mi_historial_page(request: Request):
    return template_response(templates, request, "usuario_historial.html", {"request": request})

@router.get("/mi-suscripcion", response_class=HTMLResponse)
async def mi_suscripcion_page(request: Request):
    return template_response(templates, request, "usuario_suscripcion.html", {"request": request, "individual_plans": get_individual_plan_catalog()})


def _client_link_page(request: Request, template: str, **values):
    response = template_response(templates, request, template, {"request": request, **values})
    response.headers.update({"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})
    return response


@router.get("/clientes/{client_id}/vinculacion", response_class=HTMLResponse)
async def client_link_page(request: Request, client_id: str):
    return _client_link_page(request, "cliente_vinculacion.html", client_id=client_id)


@router.get("/mis-vinculos", response_class=HTMLResponse)
async def member_links_page(request: Request):
    return _client_link_page(request, "usuario_vinculos.html")


@router.get("/auth/accept-client-link", response_class=HTMLResponse)
async def accept_client_link_page(request: Request):
    return _client_link_page(request, "accept_client_link.html")


@router.get("/mi-progreso", response_class=HTMLResponse)
async def personal_progress_page(request: Request):
    return _client_link_page(request, "usuario_progreso.html")


@router.get("/clientes/{client_id}/progreso", response_class=HTMLResponse)
async def professional_progress_page(request: Request, client_id: str):
    return _client_link_page(request, "cliente_progreso.html", client_id=client_id)

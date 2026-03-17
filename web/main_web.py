"""
web/main_web.py — MetodoBase Web App v2 (dark premium fitness theme)

Uso:
    python web/main_web.py                      # puerto 8001
    python web/main_web.py --port 8000          # puerto 8000
    python web/main_web.py --no-browser         # sin abrir browser
"""
import argparse
import logging
import os
import sys
import threading
import webbrowser
from pathlib import Path
from typing import Optional

# Raíz del proyecto en sys.path para reutilizar core/ src/ api/
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(_ROOT / ".env")
except ImportError:
    pass

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr

# Directorios locales al módulo web/
_WEB_DIR    = Path(__file__).parent
_STATIC_DIR = _WEB_DIR / "static"
_TMPL_DIR   = _WEB_DIR / "templates"

logger = logging.getLogger("web")

# ── Schemas de Autenticación ──────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str

class RegistroRequest(BaseModel):
    email: str
    password: str
    nombre: str
    apellido: str = ""
    tipo: str = "usuario"

# ── Dependency de autenticación ───────────────────────────────────────────

_security = HTTPBearer(auto_error=False)

def get_usuario_actual(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_security),
):
    """Dependency que valida el Bearer token. Lanza 401 si inválido."""
    from web.auth import verificar_token
    token = credentials.credentials if credentials else None
    usuario = verificar_token(token)
    if not usuario:
        raise HTTPException(
            status_code=401,
            detail="Token inválido o expirado. Inicia sesión nuevamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return usuario

def get_usuario_gym(usuario=Depends(get_usuario_actual)):
    """Requiere tipo 'gym' o 'admin'."""
    if usuario.get("tipo") not in ("gym", "admin"):
        raise HTTPException(403, "Acceso permitido solo para Socios Comerciales.")
    return usuario

# ── App factory ──────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    from web.auth import init_auth
    init_auth()

    app = FastAPI(
        title="MetodoBase Web",
        version="2.0.0",
        description="Sistema de Planes Nutricionales — Fitness Dark Theme",
        docs_url="/docs",
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

    # Archivos estáticos de web/
    if _STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    templates = Jinja2Templates(directory=str(_TMPL_DIR))

    # ── Reutilizar routers del api/ existente (sin duplicar lógica) ──────────
    from api.routes import clientes as clientes_router
    from api.routes import planes   as planes_router
    from api.routes import stats    as stats_router
    from api.exceptions import MetodoBaseException

    app.include_router(clientes_router.router, prefix="/api")
    app.include_router(planes_router.router,   prefix="/api")
    app.include_router(stats_router.router,    prefix="/api")

    # ── Rutas de Autenticación ────────────────────────────────────────────────
    @app.post("/api/auth/login-gym", tags=["Auth"])
    async def login_gym(data: LoginRequest):
        from web.auth import verificar_credenciales, crear_token
        usuario = verificar_credenciales(data.email, data.password, tipo_requerido="gym")
        if not usuario:
            raise HTTPException(401, "Credenciales incorrectas o tipo de cuenta no válido.")
        token = crear_token(usuario)
        return {
            "token": token,
            "tipo": usuario["tipo"],
            "nombre": f"{usuario['nombre']} {usuario['apellido']}".strip(),
            "email": usuario["email"],
        }

    @app.post("/api/auth/login-usuario", tags=["Auth"])
    async def login_usuario(data: LoginRequest):
        from web.auth import verificar_credenciales, crear_token
        usuario = verificar_credenciales(data.email, data.password, tipo_requerido="usuario")
        if not usuario:
            raise HTTPException(401, "Credenciales incorrectas o tipo de cuenta no válido.")
        token = crear_token(usuario)
        return {
            "token": token,
            "tipo": usuario["tipo"],
            "nombre": f"{usuario['nombre']} {usuario['apellido']}".strip(),
            "email": usuario["email"],
        }

    @app.post("/api/auth/registro", tags=["Auth"])
    async def registro(data: RegistroRequest):
        from web.auth import crear_usuario, crear_token
        try:
            usuario = crear_usuario(
                email=data.email,
                password=data.password,
                nombre=data.nombre,
                apellido=data.apellido,
                tipo=data.tipo,
            )
        except ValueError as e:
            raise HTTPException(400, str(e))
        token = crear_token(usuario)
        return {
            "token": token,
            "tipo": usuario["tipo"],
            "nombre": usuario["nombre"],
            "email": usuario["email"],
            "message": "Cuenta creada exitosamente.",
        }

    @app.get("/api/auth/me", tags=["Auth"])
    async def me(usuario=Depends(get_usuario_actual)):
        return usuario

    # ── Stats extendidas ──────────────────────────────────────────────────────
    @app.get("/api/estadisticas/objetivos", tags=["Estadísticas"])
    async def stats_objetivos(usuario=Depends(get_usuario_actual)):
        from api.dependencies import get_gestor
        from src.gestor_bd import GestorBDClientes
        gestor = GestorBDClientes()
        stats = gestor.obtener_estadisticas_gym()
        objetivos = stats.get("objetivos", {})
        total = sum(objetivos.values()) or 1
        return {
            "deficit_cantidad":       objetivos.get("deficit", 0),
            "deficit_porcentaje":     round(objetivos.get("deficit", 0) / total * 100, 1),
            "mantenimiento_cantidad": objetivos.get("mantenimiento", 0),
            "mantenimiento_porcentaje": round(objetivos.get("mantenimiento", 0) / total * 100, 1),
            "superavit_cantidad":     objetivos.get("superavit", 0),
            "superavit_porcentaje":   round(objetivos.get("superavit", 0) / total * 100, 1),
        }

    @app.get("/api/estadisticas/planes-tiempo", tags=["Estadísticas"])
    async def stats_planes_tiempo(usuario=Depends(get_usuario_actual)):
        """Planes generados por día (últimos 7 días)."""
        import sqlite3
        from datetime import datetime, timedelta
        from src.gestor_bd import GestorBDClientes
        gestor = GestorBDClientes()
        dias = []
        NOMBRES = ["Dom","Lun","Mar","Mié","Jue","Vie","Sáb"]
        for i in range(6, -1, -1):
            fecha = datetime.now() - timedelta(days=i)
            fecha_inicio = fecha.replace(hour=0, minute=0, second=0, microsecond=0)
            fecha_fin    = fecha.replace(hour=23, minute=59, second=59, microsecond=999999)
            with sqlite3.connect(str(gestor.db_path)) as conn:
                count = conn.execute(
                    "SELECT COUNT(*) FROM planes_generados WHERE fecha_generacion BETWEEN ? AND ?",
                    (fecha_inicio.isoformat(), fecha_fin.isoformat())
                ).fetchone()[0]
            dias.append({"fecha": NOMBRES[fecha.weekday() + 1 if fecha.weekday() < 6 else 0], "cantidad": count})
        return dias

    # ── Manejadores de errores ────────────────────────────────────────────────
    @app.exception_handler(MetodoBaseException)
    async def _mbe(request: Request, exc: MetodoBaseException):
        return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

    @app.exception_handler(Exception)
    async def _generic(request: Request, exc: Exception):
        logger.error("Unhandled: %s", exc, exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Error interno del servidor"})

    # ── Rutas HTML (páginas) ──────────────────────────────────────────────────
    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def index(request: Request):
        return templates.TemplateResponse("index.html", {"request": request})

    @app.get("/login-gym", response_class=HTMLResponse, include_in_schema=False)
    async def login_gym_page(request: Request):
        return templates.TemplateResponse("login_gym.html", {"request": request})

    @app.get("/login-usuario", response_class=HTMLResponse, include_in_schema=False)
    async def login_usuario_page(request: Request):
        return templates.TemplateResponse("login_usuario.html", {"request": request})

    @app.get("/registro", response_class=HTMLResponse, include_in_schema=False)
    async def registro_page(request: Request):
        return templates.TemplateResponse("registro.html", {"request": request})

    @app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
    async def dashboard(request: Request):
        return templates.TemplateResponse("dashboard.html", {"request": request})

    @app.get("/clientes", response_class=HTMLResponse, include_in_schema=False)
    async def clientes(request: Request):
        return templates.TemplateResponse("clientes.html", {"request": request})

    @app.get("/generar-plan", response_class=HTMLResponse, include_in_schema=False)
    async def generar_plan(request: Request):
        return templates.TemplateResponse("generar-plan.html", {"request": request})

    return app


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="MetodoBase Web App")
    parser.add_argument("--port",       type=int, default=int(os.getenv("WEB_PORT", 8001)), help="Puerto (default: 8001)")
    parser.add_argument("--host",       default=os.getenv("WEB_HOST", "127.0.0.1"))
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--reload",     action="store_true", help="Hot-reload (solo desarrollo)")
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}"

    print(f"\n{'='*52}")
    print(f"  🚀 MetodoBase Web App v2.0  — Dark Premium")
    print(f"  Dashboard : {url}")
    print(f"  API Docs  : {url}/docs")
    print(f"  Host      : {args.host}:{args.port}")
    print(f"{'='*52}\n")

    if not args.no_browser:
        def _open():
            import time; time.sleep(1.8)
            webbrowser.open(url)
        threading.Thread(target=_open, daemon=True).start()

    import uvicorn
    if args.reload:
        uvicorn.run("web.main_web:create_app", host=args.host, port=args.port,
                    reload=True, factory=True, reload_dirs=[str(_ROOT)])
    else:
        uvicorn.run(create_app(), host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()

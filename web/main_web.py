"""
web/main_web.py — MetodoBase Web App v2 (dark premium fitness theme)

Uso:
    python web/main_web.py                      # puerto 8001
    python web/main_web.py --port 8000          # puerto 8000
    python web/main_web.py --no-browser         # sin abrir browser
"""
import argparse
import os
import sys
import threading
import webbrowser
from pathlib import Path

# Raíz del proyecto en sys.path para reutilizar core/ src/ api/
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(_ROOT / ".env")
except ImportError:
    pass

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

# Directorios locales al módulo web/
_WEB_DIR    = Path(__file__).parent
_STATIC_DIR = _WEB_DIR / "static"
_TMPL_DIR   = _WEB_DIR / "templates"

# ── App factory ──────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
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
        allow_headers=["Content-Type"],
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
    from fastapi.responses import JSONResponse

    app.include_router(clientes_router.router, prefix="/api")
    app.include_router(planes_router.router,   prefix="/api")
    app.include_router(stats_router.router,    prefix="/api")

    @app.exception_handler(MetodoBaseException)
    async def _mbe(request: Request, exc: MetodoBaseException):
        return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

    @app.exception_handler(Exception)
    async def _generic(request: Request, exc: Exception):
        import logging
        logging.getLogger("web").error("Unhandled: %s", exc, exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Error interno"})

    # ── Rutas HTML ────────────────────────────────────────────────────────────
    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
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

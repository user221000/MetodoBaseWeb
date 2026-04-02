"""
web/routes/planes.py — Generación de planes con multi-tenant.

La generación de planes sigue usando core/ y GestorBDClientes internamente
(CPU-bound, ejecutado en thread pool). El registro del plan en la BD SA
se hace post-generación.
"""
import asyncio
import logging
import os
import threading
from datetime import datetime, timezone
from functools import lru_cache
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from web.schemas import PlanRequest
from web.auth_deps import get_usuario_actual, get_effective_gym_id
from web.database.engine import get_db, get_db_readonly
from web.database import repository as repo
from web.services.permissions import verify_permission
from web.routes._utils import get_gym_id
from web.constants import (
    CARPETA_SALIDA, CARPETA_PLANES,
    DEFAULT_PAGE_SIZE_PLANES, MAX_PAGE_SIZE_PLANES,
    PERIODO_SEMANA_DIAS, PERIODO_MES_DIAS, PERIODO_ANIO_DIAS,
    ERR_CLIENTE_NO_ENCONTRADO,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Planes"])

# Lock to serialize CATEGORIAS mutations (per-client food exclusions)
_categorias_lock = threading.Lock()


@router.get("/alimentos/catalogo")
async def listar_catalogo_alimentos():
    """Retorna el catálogo completo de alimentos agrupado por categoría."""
    from web.catalogo import CATALOGO_POR_TIPO
    return {
        "categorias": {
            cat: sorted(items)
            for cat, items in CATALOGO_POR_TIPO.items()
        }
    }


# Per-client lock to prevent concurrent plan generation for the same client
# Uses LRU cache to bound memory usage (max 1024 concurrent clients)
@lru_cache(maxsize=1024)
def _get_client_lock(id_cliente: str) -> threading.Lock:
    """Get or create a lock for a specific client (bounded by LRU)."""
    return threading.Lock()


def _generar_plan_sync(
    id_cliente: str, plan_numero: int, gym_id: str, tipo_plan: str = "menu_fijo"
) -> dict:
    """
    CPU-bound: genera plan nutricional y PDF.
    Soporta tipo_plan='menu_fijo' (ConstructorPlanNuevo) y
    tipo_plan='opciones' (ConstructorPlanConOpciones).
    Uses per-client lock to prevent concurrent generation.
    """
    lock = _get_client_lock(id_cliente)
    if not lock.acquire(timeout=1):
        raise ValueError("Ya se está generando un plan para este cliente. Espera un momento.")

    try:
        return _do_generar_plan(id_cliente, plan_numero, gym_id, tipo_plan)
    finally:
        lock.release()


def _do_generar_plan(
    id_cliente: str, plan_numero: int, gym_id: str, tipo_plan: str = "menu_fijo"
) -> dict:
    """Internal plan generation logic."""
    from web.dependencies import build_cliente_from_dict
    from web.database.engine import get_engine
    from web.database.models import Cliente, GymProfile
    from sqlalchemy.orm import Session as SASession

    # Leer cliente desde SA (con aislamiento multi-tenant)
    engine = get_engine()
    with SASession(engine) as session:
        c = session.query(Cliente).filter(
            Cliente.id_cliente == id_cliente,
            Cliente.gym_id == gym_id,
        ).first()
        if not c:
            raise ValueError(f"Cliente '{id_cliente}' no encontrado")
        row = {
            "nombre": c.nombre, "telefono": c.telefono, "email": c.email,
            "edad": c.edad, "sexo": c.sexo, "peso_kg": c.peso_kg,
            "estatura_cm": c.estatura_cm, "grasa_corporal_pct": c.grasa_corporal_pct,
            "masa_magra_kg": c.masa_magra_kg, "nivel_actividad": c.nivel_actividad,
            "objetivo": c.objetivo, "id_cliente": c.id_cliente,
            "plantilla_tipo": c.plantilla_tipo,
        }

        # Per-client food exclusions
        import json as _json
        _excluidos_raw = c.alimentos_excluidos

        # Bloquear preferencias de alimentos si el plan no lo permite
        from web.subscription_guard import check_food_preferences_allowed, _get_gym_plan as _gp
        _current_plan = _gp(session, gym_id)
        if not check_food_preferences_allowed(_current_plan):
            _excluidos_raw = None  # Ignorar exclusiones en planes sin esta feature

        excluidos_cliente = set(_json.loads(_excluidos_raw)) if _excluidos_raw else set()

        # Obtener perfil del gym para personalizar el PDF
        gp = session.query(GymProfile).filter(GymProfile.gym_id == gym_id).first()
        gym_config = {}
        if gp:
            gym_config = {
                "gym_nombre":       gp.nombre_negocio or "Método Base",
                "gym_telefono":     gp.telefono or "",
                "gym_direccion":    gp.direccion or "",
                "gym_instagram":    gp.instagram or "",
                "gym_facebook":     gp.facebook or "",
                "gym_tiktok":       gp.tiktok or "",
                "color_primario":   gp.color_primario or "#E5B800",
                "color_secundario": gp.color_secundario or "#292524",
            }
            # Resolver logo: si es URL local (/static/...), convertir a path absoluto
            if gp.logo_url:
                from pathlib import Path as _P
                logo_path = gp.logo_url
                if logo_path.startswith("/static/"):
                    logo_path = str(_P(__file__).resolve().parent.parent / "static" / logo_path.removeprefix("/static/"))
                if _P(logo_path).exists():
                    gym_config["gym_logo"] = logo_path

    cliente = build_cliente_from_dict(row)
    os.makedirs(CARPETA_SALIDA, exist_ok=True)

    # Apply per-client food exclusions by patching module-level CATEGORIAS refs (thread-safe)
    _lock_held = bool(excluidos_cliente)
    _patched_modules = {}
    if _lock_held:
        _categorias_lock.acquire()
    try:
        if excluidos_cliente:
            import copy
            import src.alimentos_base as _ab_mod
            import core.generador_planes as _gp_mod
            import core.generador_opciones as _go_mod
            import config.catalogo_alimentos as _ca_mod  # direct ref: monkey-patch shared module

            original_categorias = _ab_mod.CATEGORIAS
            categorias_local = copy.deepcopy(original_categorias)
            for cat, items in categorias_local.items():
                filtrados = [a for a in items if a not in excluidos_cliente]
                if filtrados:
                    items.clear()
                    items.extend(filtrados)

            # Save original refs and patch all modules that imported CATEGORIAS
            _patched_modules = {
                'ab': (_ab_mod, 'CATEGORIAS', _ab_mod.CATEGORIAS),
                'gp': (_gp_mod, 'CATEGORIAS', _gp_mod.CATEGORIAS),
                'go': (_go_mod, 'CATEGORIAS', _go_mod.CATEGORIAS),
                'ca': (_ca_mod, 'CATEGORIAS', _ca_mod.CATEGORIAS),
            }
            _ab_mod.CATEGORIAS = categorias_local
            _gp_mod.CATEGORIAS = categorias_local
            _go_mod.CATEGORIAS = categorias_local
            _ca_mod.CATEGORIAS = categorias_local

            # Refresh derived lists in catalogo_alimentos
            from web.catalogo import _refrescar_lista
            nombre_map = {"proteina": "PROTEINAS", "carbs": "CARBS", "grasa": "GRASAS", "verdura": "VERDURAS", "fruta": "FRUTAS"}
            for cat, items in categorias_local.items():
                if cat in nombre_map:
                    _refrescar_lista(nombre_map[cat], items)

        comidas = ["desayuno", "almuerzo", "comida", "cena"]

        if tipo_plan == "opciones":
            from core.generador_opciones import ConstructorPlanConOpciones
            from core.exportador_opciones import GeneradorPDFConOpciones

            plan = ConstructorPlanConOpciones.construir(
                cliente, plan_numero=plan_numero, directorio_planes=CARPETA_PLANES,
            )

            nombre_pdf = (
                f"plan_opciones_{cliente.nombre.replace(' ', '_')}"
                f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            )
            ruta_pdf_completa = os.path.join(CARPETA_SALIDA, nombre_pdf)
            generador = GeneradorPDFConOpciones(ruta_pdf_completa, config=gym_config if gym_config else None)
            ruta_pdf = generador.generar(cliente, plan)

            kcal_total = plan.get("metadata", {}).get("kcal_totales", 0)

            # Serializar plan con opciones para el frontend
            plan_serializado = {}
            for comida in comidas:
                if comida not in plan:
                    continue
                datos = plan[comida]
                plan_serializado[comida] = {
                    "kcal_objetivo": round(datos.get("kcal_objetivo", 0), 0),
                    "tipo_plan": "opciones",
                    "proteinas": _serializar_macro_opciones(datos.get("proteinas", {})),
                    "carbohidratos": _serializar_macro_opciones(datos.get("carbohidratos", {})),
                    "grasas": _serializar_macro_opciones(datos.get("grasas", {})),
                    "vegetales": [
                        {
                            "alimento": v.get("alimento", ""),
                            "gramos": round(v.get("gramos", 0)),
                        }
                        for v in datos.get("vegetales", [])
                    ],
                }
        else:
            from core.generador_planes import ConstructorPlanNuevo
            from web.pdf import PDFGenerator

            plan = ConstructorPlanNuevo.construir(
                cliente, plan_numero=plan_numero, directorio_planes=CARPETA_PLANES,
            )

            nombre_pdf = (
                f"plan_{cliente.nombre.replace(' ', '_')}"
                f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            )
            ruta_pdf_completa = os.path.join(CARPETA_SALIDA, nombre_pdf)

            # Usar PDFGenerator moderno con datos del gym
            pdf_gen = PDFGenerator(config=gym_config if gym_config else None)
            datos_pdf = {
                "cliente": {
                    "nombre": cliente.nombre,
                    "edad": cliente.edad,
                    "sexo": getattr(cliente, "sexo", None),
                    "peso_kg": cliente.peso_kg,
                    "estatura_cm": cliente.estatura_cm,
                    "grasa_corporal_pct": cliente.grasa_corporal_pct,
                    "nivel_actividad": cliente.nivel_actividad,
                    "objetivo": cliente.objetivo,
                },
                "macros": {
                    "tmb": getattr(cliente, "tmb", 0) or 0,
                    "get_total": getattr(cliente, "get_total", 0) or 0,
                    "kcal_objetivo": getattr(cliente, "kcal_objetivo", 0) or 0,
                    "proteina_g": getattr(cliente, "proteina_g", 0) or 0,
                    "carbs_g": getattr(cliente, "carbs_g", 0) or 0,
                    "grasa_g": getattr(cliente, "grasa_g", 0) or 0,
                },
                "plan": plan,
            }
            from pathlib import Path as _PPath
            ruta_pdf = pdf_gen.generar_plan(datos_pdf, _PPath(ruta_pdf_completa))

            kcal_total = sum(plan.get(m, {}).get("kcal_real", 0) for m in comidas)

            plan_serializado = {
                comida: {
                    "kcal_objetivo": round(plan[comida].get("kcal_objetivo", 0), 0),
                    "kcal_real": round(plan[comida].get("kcal_real", 0), 0),
                    "alimentos": {
                        k: round(v, 0)
                        for k, v in plan[comida].get("alimentos", {}).items()
                        if v > 0
                    },
                }
                for comida in comidas
                if comida in plan
            }

        # Registrar plan en SA
        desv_max = max(
            (plan.get(m, {}).get("desviacion_pct", 0) for m in comidas if m in plan),
            default=0,
        )

        with SASession(engine) as session:
            repo.registrar_plan(session, gym_id, id_cliente, {
                "tmb": getattr(cliente, "tmb", 0),
                "get_total": getattr(cliente, "get_total", 0),
                "kcal_objetivo": getattr(cliente, "kcal_objetivo", 0),
                "kcal_real": kcal_total,
                "proteina_g": getattr(cliente, "proteina_g", 0),
                "carbs_g": getattr(cliente, "carbs_g", 0),
                "grasa_g": getattr(cliente, "grasa_g", 0),
                "objetivo": cliente.objetivo,
                "nivel_actividad": cliente.nivel_actividad,
                "ruta_pdf": str(ruta_pdf),
                "peso_en_momento": cliente.peso_kg,
                "grasa_en_momento": cliente.grasa_corporal_pct,
                "desviacion_maxima_pct": desv_max,
                "plantilla_tipo": getattr(cliente, "plantilla_tipo", "general"),
                "tipo_plan": tipo_plan,
            })
            session.commit()

        return {
            "success": True,
            "tipo_plan": tipo_plan,
            "id_cliente": cliente.id_cliente,
            "nombre": cliente.nombre,
            "ruta_pdf": str(ruta_pdf),
            "macros": {
                "tmb": round(cliente.tmb or 0, 1),
                "get_total": round(cliente.get_total or 0, 1),
                "kcal_objetivo": round(cliente.kcal_objetivo or 0, 0),
                "kcal_real": round(kcal_total, 0),
                "proteina_g": round(cliente.proteina_g or 0, 1),
                "carbs_g": round(cliente.carbs_g or 0, 1),
                "grasa_g": round(cliente.grasa_g or 0, 1),
            },
            "plan": plan_serializado,
        }
    finally:
        # Restore original CATEGORIAS refs in all patched modules
        if _patched_modules:
            from web.catalogo import _refrescar_lista
            for key, (mod, attr, original) in _patched_modules.items():
                setattr(mod, attr, original)
            nombre_map = {"proteina": "PROTEINAS", "carbs": "CARBS", "grasa": "GRASAS", "verdura": "VERDURAS", "fruta": "FRUTAS"}
            for cat, items in _patched_modules['ab'][2].items():
                if cat in nombre_map:
                    _refrescar_lista(nombre_map[cat], items)
        if _lock_held:
            _categorias_lock.release()


def _serializar_macro_opciones(macro_data: dict) -> dict:
    """Serializa un bloque de opciones de macro (proteinas/carbs/grasas)."""
    return {
        "cantidad_objetivo": round(macro_data.get("cantidad_objetivo", 0), 1),
        "opciones": [
            {
                "alimento": op.get("alimento", ""),
                "gramos": round(op.get("gramos", 0)),
                "equivalencia": op.get("equivalencia", ""),
                "macros": op.get("macros", {}),
            }
            for op in macro_data.get("opciones", [])
        ],
    }


@router.post("/generar-plan", summary="Generar plan nutricional + PDF")
async def generar_plan(
    data: PlanRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_usuario_actual),
):
    verify_permission(usuario, "create", "plan")
    gym_id = get_gym_id(usuario)
    # Verificar que el cliente pertenece al gym antes de generar
    cliente = repo.obtener_cliente(db, gym_id, data.id_cliente)
    if not cliente:
        raise HTTPException(status_code=404, detail=ERR_CLIENTE_NO_ENCONTRADO)

    # Verificar límite de planes por cliente por día
    from web.subscription_guard import check_daily_plan_limit, _get_gym_plan
    plan_name = _get_gym_plan(db, gym_id)
    check_daily_plan_limit(db, gym_id, data.id_cliente, plan_name)

    try:
        resultado = await asyncio.to_thread(
            _generar_plan_sync,
            data.id_cliente,
            data.plan_numero,
            gym_id,
            data.tipo_plan,
        )
        logger.info("Plan generado: %s", data.id_cliente)

        # Email de notificación al gym (background task, no bloquea respuesta)
        from web.services import email_service
        background_tasks.add_task(
            email_service.send_plan_generated,
            email=usuario["email"],
            nombre_cliente=resultado.get("nombre", data.id_cliente),
            pdf_path=resultado.get("ruta_pdf"),
        )

        return resultado
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        from web.settings import get_settings as _gs
        logger.error(
            "Error generando plan: %s", exc,
            exc_info=not _gs().is_production
        )
        raise HTTPException(status_code=500, detail=f"Error en generación: {exc}")


@router.get("/descargar-pdf/{id_cliente}", summary="Descargar último PDF")
async def descargar_pdf(
    id_cliente: str,
    db: Session = Depends(get_db_readonly),
    usuario: dict = Depends(get_usuario_actual),
):
    verify_permission(usuario, "read", "plan")
    gym_id = get_gym_id(usuario)
    planes = repo.obtener_historial_planes(db, gym_id, id_cliente, limite=1)
    if not planes:
        raise HTTPException(404, "No hay planes generados para este cliente")

    ruta = planes[0].get("ruta_pdf", "")
    if not ruta or not os.path.isfile(ruta):
        raise HTTPException(404, "PDF no encontrado en disco")

    return FileResponse(ruta, media_type="application/pdf", filename=os.path.basename(ruta))


# ── Listado e historial de planes ───────────────────────────────────────────

from typing import Optional
from fastapi import Query
from sqlalchemy import func
from web.database.models import PlanGenerado, Cliente
from datetime import timedelta


@router.get("/planes", summary="Listar planes generados")
def listar_planes(
    limite: int = Query(DEFAULT_PAGE_SIZE_PLANES, ge=1, le=MAX_PAGE_SIZE_PLANES),
    offset: int = Query(0, ge=0),
    id_cliente: Optional[str] = Query(None, description="Filtrar por cliente"),
    periodo: Optional[str] = Query(None, description="semana|mes|anio"),
    db: Session = Depends(get_db_readonly),
    usuario: dict = Depends(get_usuario_actual),
):
    """Lista planes del gym ordenados por fecha descendente."""
    verify_permission(usuario, "read", "plan")
    gym_id = get_gym_id(usuario)
    
    # Query base
    q = db.query(PlanGenerado).filter(PlanGenerado.gym_id == gym_id)
    
    # Filtro por cliente
    if id_cliente:
        q = q.filter(PlanGenerado.id_cliente == id_cliente)
    
    # Filtro por período
    ahora = datetime.now(timezone.utc)
    if periodo == "semana":
        fecha_inicio = ahora - timedelta(days=PERIODO_SEMANA_DIAS)
        q = q.filter(PlanGenerado.fecha_generacion >= fecha_inicio)
    elif periodo == "mes":
        fecha_inicio = ahora - timedelta(days=PERIODO_MES_DIAS)
        q = q.filter(PlanGenerado.fecha_generacion >= fecha_inicio)
    elif periodo == "anio":
        fecha_inicio = ahora - timedelta(days=PERIODO_ANIO_DIAS)
        q = q.filter(PlanGenerado.fecha_generacion >= fecha_inicio)
    
    total = q.count()
    
    # Ordenar y paginar
    planes = q.order_by(PlanGenerado.fecha_generacion.desc()).offset(offset).limit(limite).all()
    
    # Obtener nombres de clientes en batch
    cliente_ids = list(set(p.id_cliente for p in planes))
    clientes = {}
    if cliente_ids:
        clientes_q = db.query(Cliente.id_cliente, Cliente.nombre).filter(
            Cliente.id_cliente.in_(cliente_ids)
        ).all()
        clientes = {c.id_cliente: c.nombre for c in clientes_q}
    
    result = []
    for p in planes:
        result.append({
            "id": p.id,
            "id_cliente": p.id_cliente,
            "nombre_cliente": clientes.get(p.id_cliente, "—"),
            "fecha_generacion": p.fecha_generacion.isoformat() if p.fecha_generacion else None,
            "kcal_objetivo": round(p.kcal_objetivo, 0) if p.kcal_objetivo else None,
            "proteina_g": round(p.proteina_g, 0) if p.proteina_g else None,
            "carbs_g": round(p.carbs_g, 0) if p.carbs_g else None,
            "grasa_g": round(p.grasa_g, 0) if p.grasa_g else None,
            "objetivo": p.objetivo,
            "plantilla_tipo": p.plantilla_tipo,
            "ruta_pdf": p.ruta_pdf,
        })
    
    return {
        "planes": result,
        "total": total,
        "limit": limite,
        "offset": offset,
    }


@router.get("/planes/resumen", summary="Resumen de planes por período")
def resumen_planes(
    db: Session = Depends(get_db_readonly),
    usuario: dict = Depends(get_usuario_actual),
):
    """Resumen de planes generados por período."""
    verify_permission(usuario, "read", "stats")
    gym_id = get_gym_id(usuario)
    ahora = datetime.now(timezone.utc)
    
    # Planes esta semana
    semana = ahora - timedelta(days=PERIODO_SEMANA_DIAS)
    planes_semana = db.query(func.count(PlanGenerado.id)).filter(
        PlanGenerado.gym_id == gym_id,
        PlanGenerado.fecha_generacion >= semana,
    ).scalar() or 0
    
    # Planes este mes
    mes = ahora - timedelta(days=PERIODO_MES_DIAS)
    planes_mes = db.query(func.count(PlanGenerado.id)).filter(
        PlanGenerado.gym_id == gym_id,
        PlanGenerado.fecha_generacion >= mes,
    ).scalar() or 0
    
    # Planes totales
    planes_total = db.query(func.count(PlanGenerado.id)).filter(
        PlanGenerado.gym_id == gym_id,
    ).scalar() or 0
    
    # Promedio kcal
    promedio_kcal = db.query(func.avg(PlanGenerado.kcal_objetivo)).filter(
        PlanGenerado.gym_id == gym_id,
        PlanGenerado.fecha_generacion >= mes,
    ).scalar() or 0
    
    return {
        "planes_semana": planes_semana,
        "planes_mes": planes_mes,
        "planes_total": planes_total,
        "promedio_kcal": round(promedio_kcal, 0),
    }

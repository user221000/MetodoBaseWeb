"""Shared authorized nutrition generation and persistence for web/API adapters."""
import os
import threading
import uuid
from functools import lru_cache

from web.constants import CARPETA_SALIDA, CARPETA_PLANES
from web.database import repository as repo
from web.database.tenant_context import tenant_task


@lru_cache(maxsize=1024)
def _client_lock(gym_id, client_id):
    return threading.Lock()


@tenant_task("gym_id")
def generate_plan(id_cliente, plan_numero, gym_id, tipo_plan="menu_fijo", *, reservation_id=None, builder=None):
    lock = _client_lock(gym_id, id_cliente)
    if not lock.acquire(timeout=1):
        raise ValueError("Generation is already in progress for this client")
    try:
        selected = builder or build_plan
        if reservation_id is None:
            return selected(id_cliente, plan_numero, gym_id, tipo_plan)
        return selected(id_cliente, plan_numero, gym_id, tipo_plan, reservation_id=reservation_id)
    finally:
        lock.release()


def build_plan(
    id_cliente: str, plan_numero: int, gym_id: str, tipo_plan: str = "menu_fijo", *, reservation_id: str | None = None
) -> dict:
    """Build and persist an authorized plan using an immutable food snapshot.

    Tenant is resolved by the authenticated caller; this function checks client
    ownership again. Restrictions are independent of paid capabilities. Domain
    failures occur before PDF/persistence; the caller owns quota compensation.
    The returned plan_id identifies exactly the committed JSON/PDF record.
    """
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
            Cliente.activo.is_(True),
            Cliente.deleted_at.is_(None),
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

        excluidos_cliente = set(_json.loads(_excluidos_raw)) if _excluidos_raw else set()

        # Obtener perfil del gym para personalizar el PDF
        from pathlib import Path as _P
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
            # Resolver logo del gym: si es URL local (/static/...), convertir a path absoluto
            if gp.logo_url:
                logo_path = gp.logo_url
                if logo_path.startswith("/static/"):
                    logo_path = str(_P(__file__).resolve().parent.parent / "static" / logo_path.removeprefix("/static/"))
                if _P(logo_path).exists():
                    gym_config["gym_logo"] = logo_path
        else:
            # Usuario individual: siempre usa el logo de Consultoría Hernández
            import os as _os
            _app_root = _P(_os.environ.get("PYTHONPATH", "").split(":")[0]) if _os.environ.get("PYTHONPATH") else _P(__file__).resolve().parent.parent.parent
            _usuario_logo = _app_root / "static" / "img" / "logo_consultoria_hernandez.png"
            gym_config = {
                "gym_nombre": "Consultoría Hernández",
                "gym_logo": str(_usuario_logo) if _usuario_logo.exists() else None,
            }

    cliente = build_cliente_from_dict(row)
    os.makedirs(CARPETA_SALIDA, exist_ok=True)

    # Safety exclusions apply to every subscription tier. No shared references
    # are modified, including requests without exclusions running in parallel.
    from core.food_catalog import FoodCatalog
    from src.alimentos_base import ALIMENTOS_BASE, CATEGORIAS
    catalogo = FoodCatalog.from_data(ALIMENTOS_BASE, CATEGORIAS, excluidos_cliente)

    comidas = ["desayuno", "almuerzo", "comida", "cena"]

    if tipo_plan == "opciones":
        from core.generador_opciones import ConstructorPlanConOpciones
        from core.exportador_opciones import GeneradorPDFConOpciones

        plan = ConstructorPlanConOpciones.construir(
            cliente, plan_numero=plan_numero, directorio_planes=CARPETA_PLANES, catalogo=catalogo,
        )

        nombre_pdf = "plan_opciones_" + uuid.uuid4().hex + ".pdf"
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
                "proteinas": serialize_macro_options(datos.get("proteinas", {})),
                "carbohidratos": serialize_macro_options(datos.get("carbohidratos", {})),
                "grasas": serialize_macro_options(datos.get("grasas", {})),
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
            cliente, plan_numero=plan_numero, directorio_planes=CARPETA_PLANES, catalogo=catalogo,
        )

        nombre_pdf = "plan_" + uuid.uuid4().hex + ".pdf"
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
        plan_id = repo.registrar_plan(session, gym_id, id_cliente, {
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
            "plan_json": _json.dumps(plan_serializado, ensure_ascii=False),
        }, return_id=True, reservation_id=reservation_id)
        if not plan_id:
            raise ValueError("No fue posible registrar el plan autorizado")
        session.commit()

    return {
        "success": True,
        "plan_id": plan_id,
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


def serialize_macro_options(macro_data: dict) -> dict:
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



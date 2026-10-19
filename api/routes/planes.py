"""
api/routes/planes.py — Generación de planes nutricionales con autenticación multi-tenant.

Endpoints:
- POST /api/generar-plan: Genera plan nutricional + PDF
- GET /api/descargar-pdf/{id_cliente}: Descarga último PDF del cliente
"""
import asyncio
import logging
import os
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from api.schemas import PlanRequest
from api.dependencies import build_cliente_from_dict
from web.database.engine import get_db
from web.database.tenant_context import tenant_task
from web.auth_deps import get_usuario_gym
from web.database import repository as repo
from config.constantes import CARPETA_SALIDA, CARPETA_PLANES

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Planes"])


@router.get("/alimentos/catalogo")
async def listar_catalogo_alimentos():
    """Retorna el catálogo completo de alimentos agrupado por categoría."""
    from config.catalogo_alimentos import CATALOGO_POR_TIPO
    return {
        "categorias": {
            cat: sorted(items)
            for cat, items in CATALOGO_POR_TIPO.items()
        }
    }


@tenant_task("gym_id")
def _generar_plan_sync(gym_id: str, id_cliente: str, plan_numero: int) -> dict:
    """
    Función CPU-bound que se ejecuta en un thread executor.
    Verifica pertenencia del cliente al gym antes de generar.
    """
    # Importaciones locales al thread para evitar problemas de estado
    from core.generador_planes import ConstructorPlanNuevo
    from api.pdf_generator import PDFGenerator
    from web.database.engine import get_engine
    from web.database.models import Cliente
    from sqlalchemy.orm import Session as SQLASession

    engine = get_engine()
    with SQLASession(engine) as session:
        # Obtener cliente verificando pertenencia al gym
        cliente_row = session.query(Cliente).filter(
            Cliente.id_cliente == id_cliente,
            Cliente.gym_id == gym_id,
        ).first()
        
        if not cliente_row:
            raise ValueError(f"Cliente '{id_cliente}' no encontrado o no pertenece al gym")
        
        # Convertir a dict para build_cliente_from_dict
        row = {
            "id_cliente": cliente_row.id_cliente,
            "nombre": cliente_row.nombre,
            "telefono": cliente_row.telefono,
            "edad": cliente_row.edad,
            "peso_kg": cliente_row.peso_kg,
            "estatura_cm": cliente_row.estatura_cm,
            "grasa_corporal_pct": cliente_row.grasa_corporal_pct,
            "nivel_actividad": cliente_row.nivel_actividad,
            "objetivo": cliente_row.objetivo,
        }
        cliente = build_cliente_from_dict(row)

        # Generar plan nutricional
        os.makedirs(CARPETA_SALIDA, exist_ok=True)
        plan = ConstructorPlanNuevo.construir(
            cliente,
            plan_numero=plan_numero,
            directorio_planes=CARPETA_PLANES,
        )

        # Generar PDF
        nombre_pdf = (
            f"plan_{cliente.nombre.replace(' ', '_')}"
            f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )
        ruta_pdf_completa = os.path.join(CARPETA_SALIDA, nombre_pdf)
        pdf_gen = PDFGenerator()
        datos_pdf = PDFGenerator.datos_from_cliente(cliente, plan)
        from pathlib import Path as _PPath
        ruta_pdf = pdf_gen.generar_plan(datos_pdf, _PPath(ruta_pdf_completa))

        # Registrar plan en BD con aislamiento de tenant
        comidas = ["desayuno", "almuerzo", "comida", "cena"]
        kcal_real = sum(plan.get(c, {}).get("kcal_real", 0) for c in comidas)
        
        from web.database import repository as repo_sync
        repo_sync.registrar_plan(session, gym_id, id_cliente, {
            "tmb": cliente.tmb,
            "get_total": cliente.get_total,
            "kcal_objetivo": cliente.kcal_objetivo,
            "kcal_real": kcal_real,
            "proteina_g": cliente.proteina_g,
            "carbs_g": cliente.carbs_g,
            "grasa_g": cliente.grasa_g,
            "objetivo": cliente.objetivo,
            "nivel_actividad": cliente.nivel_actividad,
            "ruta_pdf": str(ruta_pdf),
            "peso_en_momento": cliente.peso_kg,
            "grasa_en_momento": cliente.grasa_corporal_pct,
        })
        session.commit()

        # Armar respuesta
        return {
            "success": True,
            "id_cliente": cliente.id_cliente,
            "nombre": cliente.nombre,
            "ruta_pdf": str(ruta_pdf),
            "macros": {
                "tmb": round(cliente.tmb or 0, 1),
                "get_total": round(cliente.get_total or 0, 1),
                "kcal_objetivo": round(cliente.kcal_objetivo or 0, 0),
                "kcal_real": round(kcal_real, 0),
                "proteina_g": round(cliente.proteina_g or 0, 1),
                "carbs_g": round(cliente.carbs_g or 0, 1),
                "grasa_g": round(cliente.grasa_g or 0, 1),
            },
            "plan": {
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
            },
        }


@router.post("/generar-plan", summary="Generar plan nutricional + PDF")
async def generar_plan(
    data: PlanRequest,
    usuario: dict = Depends(get_usuario_gym),
):
    """
    Genera un plan nutricional diario para un cliente del gym autenticado.
    La generación es CPU-bound (~5–15 seg); se ejecuta en un thread executor.
    """
    gym_id = usuario["id"]
    try:
        resultado = await asyncio.to_thread(
            _generar_plan_sync, gym_id, data.id_cliente, data.plan_numero
        )
        logger.info("Plan generado para cliente: %s (gym: %s)", data.id_cliente, gym_id)
        return resultado
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(
            "Error generando plan para %s: %s", data.id_cliente, exc, exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Error en generación: {exc}")


@router.get("/descargar-pdf/{id_cliente}", summary="Descargar último PDF del cliente")
async def descargar_pdf(
    id_cliente: str,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_usuario_gym),
):
    """Descarga el PDF del plan más reciente del cliente (verificando pertenencia al gym)."""
    gym_id = usuario["id"]
    
    # Verificar que el cliente pertenece al gym
    cliente = repo.obtener_cliente(db, gym_id, id_cliente)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Obtener historial de planes
    historial = repo.obtener_historial_planes(db, gym_id, id_cliente, limite=1)
    if not historial:
        raise HTTPException(
            status_code=404, detail="No hay planes generados para este cliente"
        )

    ruta_pdf = historial[0].get("ruta_pdf")
    if not ruta_pdf or not os.path.exists(ruta_pdf):
        raise HTTPException(status_code=404, detail="Archivo PDF no encontrado en disco")

    filename = os.path.basename(ruta_pdf)
    return FileResponse(
        path=ruta_pdf,
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

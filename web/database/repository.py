"""
web/database/repository.py — Data access layer with multi-tenant isolation.

Cada método recibe `gym_id` y filtra automáticamente.
NUNCA exponer datos de un gym a otro.
"""
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from web.database.models import Cliente, PlanGenerado, Usuario, RefreshToken, GymProfile, PlanSuscripcion

logger = logging.getLogger("web.db")


# ── Clientes ─────────────────────────────────────────────────────────────────

def listar_clientes(
    db: Session,
    gym_id: str,
    termino: str = "",
    solo_activos: Optional[bool] = None,
    filtro_suscripcion: Optional[str] = None,
    limite: int = 100,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """
    Lista clientes del gym, con búsqueda y filtros opcionales.
    
    Args:
        solo_activos: None = todos, True = suscripción vigente (o plan en 30 días),
                      False = suscripción expirada (o sin plan en 30 días)
        filtro_suscripcion: sub-nuevas | sub-activas | sub-inactivas
    
    Returns: (clientes, total)
    """
    from datetime import timedelta
    
    q = db.query(Cliente).filter(
        Cliente.gym_id == gym_id,
        Cliente.activo == True,  # noqa: E712 - siempre filtrar soft-deleted
    )

    # Filtro por suscripción activa / inactiva
    if solo_activos is not None:
        ahora = datetime.now(timezone.utc)
        un_mes_atras = ahora - timedelta(days=30)
        if solo_activos:
            # Clientes CON suscripción vigente o plan en últimos 30 días
            q = q.filter(
                (Cliente.fecha_fin_suscripcion >= ahora) |
                (
                    (Cliente.fecha_fin_suscripcion.is_(None)) &
                    (Cliente.ultimo_plan >= un_mes_atras)
                )
            )
        else:
            # Clientes CON suscripción expirada o sin plan reciente
            q = q.filter(
                (
                    (Cliente.fecha_fin_suscripcion.isnot(None)) &
                    (Cliente.fecha_fin_suscripcion < ahora)
                ) |
                (
                    (Cliente.fecha_fin_suscripcion.is_(None)) &
                    (
                        (Cliente.ultimo_plan.is_(None)) |
                        (Cliente.ultimo_plan < un_mes_atras)
                    )
                )
            )

    # Filtros de suscripción de clientes al gym
    if filtro_suscripcion == "sub-nuevas":
        ahora = datetime.now(timezone.utc)
        inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        q = q.filter(
            Cliente.fecha_suscripcion.isnot(None),
            Cliente.fecha_suscripcion >= inicio_mes,
        )
    elif filtro_suscripcion == "sub-activas":
        ahora = datetime.now(timezone.utc)
        q = q.filter(
            Cliente.fecha_fin_suscripcion.isnot(None),
            Cliente.fecha_fin_suscripcion >= ahora,
        )
    elif filtro_suscripcion == "sub-inactivas":
        ahora = datetime.now(timezone.utc)
        q = q.filter(
            (Cliente.fecha_fin_suscripcion.is_(None)) |
            (Cliente.fecha_fin_suscripcion < ahora)
        )

    if termino:
        like = f"%{termino}%"
        q = q.filter(
            (Cliente.nombre.ilike(like))
            | (Cliente.telefono.ilike(like))
            | (Cliente.id_cliente.ilike(like))
        )

    total = q.count()
    q = q.order_by(Cliente.ultimo_plan.desc().nullslast(), Cliente.nombre.asc())
    rows = q.offset(offset).limit(limite).all()

    return [_cliente_to_dict(c) for c in rows], total


def obtener_cliente(db: Session, gym_id: str, id_cliente: str) -> Optional[dict]:
    """Obtiene un cliente verificando que pertenece al gym."""
    c = db.query(Cliente).filter(
        Cliente.id_cliente == id_cliente,
        Cliente.gym_id == gym_id,
    ).first()
    return _cliente_to_dict(c) if c else None


def crear_cliente(db: Session, gym_id: str, data: dict) -> dict:
    """Crea un cliente asignándolo al gym."""
    c = Cliente(
        gym_id=gym_id,
        nombre=data["nombre"],
        telefono=data.get("telefono"),
        email=data.get("email"),
        edad=data.get("edad"),
        sexo=data.get("sexo"),
        peso_kg=data.get("peso_kg"),
        estatura_cm=data.get("estatura_cm"),
        grasa_corporal_pct=data.get("grasa_corporal_pct"),
        masa_magra_kg=data.get("masa_magra_kg"),
        nivel_actividad=data.get("nivel_actividad"),
        objetivo=data.get("objetivo"),
        notas=data.get("notas"),
        plantilla_tipo=data.get("plantilla_tipo", "general"),
        alimentos_excluidos=json.dumps(data["alimentos_excluidos"]) if data.get("alimentos_excluidos") else None,
        fecha_suscripcion=data.get("fecha_suscripcion"),
        fecha_fin_suscripcion=data.get("fecha_fin_suscripcion"),
    )
    db.add(c)
    db.flush()  # get id_cliente generated
    logger.info("[DB] Cliente creado: %s (gym: %s)", c.id_cliente, gym_id)
    return _cliente_to_dict(c)


def actualizar_cliente(db: Session, gym_id: str, id_cliente: str, data: dict) -> Optional[dict]:
    """Actualiza un cliente verificando pertenencia al gym."""
    c = db.query(Cliente).filter(
        Cliente.id_cliente == id_cliente,
        Cliente.gym_id == gym_id,
    ).first()
    if not c:
        return None

    for key in (
        "nombre", "telefono", "email", "edad", "sexo", "peso_kg",
        "estatura_cm", "grasa_corporal_pct", "masa_magra_kg",
        "nivel_actividad", "objetivo", "notas", "plantilla_tipo",
        "fecha_suscripcion", "fecha_fin_suscripcion",
    ):
        if key in data and data[key] is not None:
            setattr(c, key, data[key])

    if "alimentos_excluidos" in data:
        val = data["alimentos_excluidos"]
        c.alimentos_excluidos = json.dumps(val) if val else None

    db.flush()
    logger.info("[DB] Cliente actualizado: %s", id_cliente)
    return _cliente_to_dict(c)


def eliminar_cliente(db: Session, gym_id: str, id_cliente: str) -> bool:
    """Soft-delete: marca como inactivo."""
    c = db.query(Cliente).filter(
        Cliente.id_cliente == id_cliente,
        Cliente.gym_id == gym_id,
    ).first()
    if not c:
        return False
    c.activo = False
    db.flush()
    logger.info("[DB] Cliente desactivado: %s", id_cliente)
    return True


# ── Planes ───────────────────────────────────────────────────────────────────

def registrar_plan(db: Session, gym_id: str, id_cliente: str, plan_data: dict) -> bool:
    """Registra un plan generado y actualiza contadores del cliente."""
    c = db.query(Cliente).filter(
        Cliente.id_cliente == id_cliente,
        Cliente.gym_id == gym_id,
    ).first()
    if not c:
        return False

    p = PlanGenerado(
        id_cliente=id_cliente,
        gym_id=gym_id,
        tmb=plan_data.get("tmb"),
        get_total=plan_data.get("get_total"),
        kcal_objetivo=plan_data.get("kcal_objetivo"),
        kcal_real=plan_data.get("kcal_real"),
        proteina_g=plan_data.get("proteina_g"),
        carbs_g=plan_data.get("carbs_g"),
        grasa_g=plan_data.get("grasa_g"),
        objetivo=plan_data.get("objetivo"),
        nivel_actividad=plan_data.get("nivel_actividad"),
        ruta_pdf=plan_data.get("ruta_pdf"),
        peso_en_momento=plan_data.get("peso_en_momento"),
        grasa_en_momento=plan_data.get("grasa_en_momento"),
        desviacion_maxima_pct=plan_data.get("desviacion_maxima_pct"),
        plantilla_tipo=plan_data.get("plantilla_tipo", "general"),
        tipo_plan=plan_data.get("tipo_plan", "menu_fijo"),
    )
    db.add(p)

    c.total_planes_generados = (c.total_planes_generados or 0) + 1
    c.ultimo_plan = datetime.now(timezone.utc)
    db.flush()
    return True


def obtener_historial_planes(
    db: Session, gym_id: str, id_cliente: str, limite: int = 20
) -> list[dict]:
    """Historial de planes de un cliente, verificando gym."""
    rows = db.query(PlanGenerado).filter(
        PlanGenerado.id_cliente == id_cliente,
        PlanGenerado.gym_id == gym_id,
    ).order_by(PlanGenerado.fecha_generacion.desc()).limit(limite).all()

    return [_plan_to_dict(p) for p in rows]


# ── Estadísticas ─────────────────────────────────────────────────────────────

def obtener_estadisticas(
    db: Session,
    gym_id: str,
    fecha_inicio: Optional[datetime] = None,
    fecha_fin: Optional[datetime] = None,
) -> dict:
    """Estadísticas del gym con aislamiento multi-tenant."""
    if fecha_fin is None:
        fecha_fin = datetime.now(timezone.utc)
    if fecha_inicio is None:
        fecha_inicio = fecha_fin - timedelta(days=30)

    # Total clientes activos
    total_clientes = db.query(func.count(Cliente.id)).filter(
        Cliente.gym_id == gym_id,
        Cliente.activo == True,  # noqa: E712
    ).scalar() or 0

    # Clientes nuevos en período
    clientes_nuevos = db.query(func.count(Cliente.id)).filter(
        Cliente.gym_id == gym_id,
        Cliente.fecha_registro.between(fecha_inicio, fecha_fin),
    ).scalar() or 0

    # Planes en período
    planes_q = db.query(PlanGenerado).filter(
        PlanGenerado.gym_id == gym_id,
        PlanGenerado.fecha_generacion.between(fecha_inicio, fecha_fin),
    )
    planes_periodo = planes_q.count()
    promedio_kcal = db.query(func.avg(PlanGenerado.kcal_objetivo)).filter(
        PlanGenerado.gym_id == gym_id,
        PlanGenerado.fecha_generacion.between(fecha_inicio, fecha_fin),
    ).scalar() or 0

    # Clientes activos (con plan en el último mes)
    un_mes_atras = datetime.now(timezone.utc) - timedelta(days=30)
    clientes_activos = db.query(func.count(func.distinct(PlanGenerado.id_cliente))).filter(
        PlanGenerado.gym_id == gym_id,
        PlanGenerado.fecha_generacion >= un_mes_atras,
    ).scalar() or 0

    # Tasa retención
    tasa_retencion = (clientes_activos / total_clientes * 100) if total_clientes > 0 else 0

    # Objetivos
    objetivos = {}
    for obj_val in ("deficit", "mantenimiento", "superavit"):
        count = db.query(func.count(Cliente.id)).filter(
            Cliente.gym_id == gym_id,
            Cliente.activo == True,  # noqa: E712
            Cliente.objetivo == obj_val,
        ).scalar() or 0
        objetivos[obj_val] = count

    # Top clientes
    top_clientes_q = db.query(
        Cliente.id_cliente, Cliente.nombre, Cliente.total_planes_generados,
        Cliente.objetivo, Cliente.telefono, Cliente.ultimo_plan,
        Cliente.fecha_registro,
    ).filter(
        Cliente.gym_id == gym_id,
        Cliente.activo == True,  # noqa: E712
    ).order_by(Cliente.fecha_registro.desc()).limit(8).all()

    top_clientes = [
        {
            "id_cliente": r[0], "nombre": r[1], "total_planes": r[2],
            "objetivo": r[3], "telefono": r[4],
            "ultimo_plan": r[5].isoformat() if r[5] else None,
            "fecha_registro": r[6].isoformat() if r[6] else None,
        }
        for r in top_clientes_q
    ]

    return {
        "total_clientes": total_clientes,
        "clientes_nuevos": clientes_nuevos,
        "planes_periodo": planes_periodo,
        "promedio_kcal": round(promedio_kcal, 1),
        "clientes_activos": clientes_activos,
        "tasa_retencion": round(tasa_retencion, 1),
        "objetivos": objetivos,
        "top_clientes": top_clientes,
    }


def obtener_planes_por_dia(db: Session, gym_id: str, dias: int = 7) -> list[dict]:
    """Planes por día para gráfico de evolución."""
    ahora = datetime.now(timezone.utc)
    DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    result = []
    for i in range(dias - 1, -1, -1):
        fecha = ahora - timedelta(days=i)
        inicio = fecha.replace(hour=0, minute=0, second=0, microsecond=0)
        fin = fecha.replace(hour=23, minute=59, second=59, microsecond=999999)
        count = db.query(func.count(PlanGenerado.id)).filter(
            PlanGenerado.gym_id == gym_id,
            PlanGenerado.fecha_generacion.between(inicio, fin),
        ).scalar() or 0
        result.append({"fecha": DIAS[fecha.weekday()], "cantidad": count})
    return result


# ── Auth helpers (refresh tokens) ────────────────────────────────────────────

def crear_refresh_token_db(db: Session, jti: str, user_id: str, expires_at: float, created_at: float) -> None:
    rt = RefreshToken(jti=jti, user_id=user_id, expires_at=expires_at, created_at=created_at)
    db.add(rt)
    db.flush()


def verificar_refresh_token_db(db: Session, jti: str) -> Optional[bool]:
    """Returns None if not found, True if valid, False if revoked."""
    rt = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()
    if not rt:
        return None
    return not rt.revoked


def revocar_refresh_token_db(db: Session, jti: str) -> None:
    db.query(RefreshToken).filter(RefreshToken.jti == jti).update({"revoked": True})


def revocar_todos_refresh_tokens_db(db: Session, user_id: str) -> None:
    db.query(RefreshToken).filter(RefreshToken.user_id == user_id).update({"revoked": True})


def cleanup_expired_refresh_tokens_db(db: Session) -> None:
    import time
    db.query(RefreshToken).filter(RefreshToken.expires_at < time.time()).delete()


# ── Usuarios ─────────────────────────────────────────────────────────────────

def obtener_usuario_por_id(db: Session, user_id: str) -> Optional[dict]:
    u = db.query(Usuario).filter(Usuario.id == user_id, Usuario.activo == True).first()  # noqa: E712
    if not u:
        return None
    return {"id": u.id, "email": u.email, "nombre": u.nombre, "apellido": u.apellido, "tipo": u.tipo}


def obtener_usuario_por_email(db: Session, email: str) -> Optional[Usuario]:
    return db.query(Usuario).filter(Usuario.email == email, Usuario.activo == True).first()  # noqa: E712


# ── Serialización ────────────────────────────────────────────────────────────

def _cliente_to_dict(c: Cliente) -> dict:
    _fecha_reg = c.fecha_registro.isoformat() if c.fecha_registro else None
    _ultimo = c.ultimo_plan.isoformat() if c.ultimo_plan else None
    _fecha_sub = c.fecha_suscripcion.isoformat() if c.fecha_suscripcion else None
    _fecha_fin_sub = c.fecha_fin_suscripcion.isoformat() if c.fecha_fin_suscripcion else None
    return {
        "id_cliente": c.id_cliente,
        "nombre": c.nombre,
        "telefono": c.telefono,
        "email": c.email,
        "edad": c.edad,
        "sexo": c.sexo,
        "peso_kg": c.peso_kg,
        "estatura_cm": c.estatura_cm,
        "grasa_corporal_pct": c.grasa_corporal_pct,
        "masa_magra_kg": c.masa_magra_kg,
        "nivel_actividad": c.nivel_actividad,
        "objetivo": c.objetivo,
        "fecha_registro": _fecha_reg,
        "ultimo_plan": _ultimo,
        "ultima_actualizacion": _ultimo or _fecha_reg,
        "total_planes_generados": c.total_planes_generados or 0,
        "total_planes": c.total_planes_generados or 0,
        "activo": c.activo,
        "notas": c.notas,
        "plantilla_tipo": c.plantilla_tipo,
        "alimentos_excluidos": json.loads(c.alimentos_excluidos) if c.alimentos_excluidos else [],
        "fecha_suscripcion": _fecha_sub,
        "fecha_fin_suscripcion": _fecha_fin_sub,
        "dias_restantes": c.dias_restantes,
    }


def _plan_to_dict(p: PlanGenerado) -> dict:
    return {
        "id": p.id,
        "id_cliente": p.id_cliente,
        "fecha_generacion": p.fecha_generacion.isoformat() if p.fecha_generacion else None,
        "tmb": p.tmb,
        "get_total": p.get_total,
        "kcal_objetivo": p.kcal_objetivo,
        "kcal_real": p.kcal_real,
        "proteina_g": p.proteina_g,
        "carbs_g": p.carbs_g,
        "grasa_g": p.grasa_g,
        "objetivo": p.objetivo,
        "nivel_actividad": p.nivel_actividad,
        "ruta_pdf": p.ruta_pdf,
        "peso_en_momento": p.peso_en_momento,
        "grasa_en_momento": p.grasa_en_momento,
        "desviacion_maxima_pct": p.desviacion_maxima_pct,
        "plantilla_tipo": p.plantilla_tipo,
        "tipo_plan": p.tipo_plan,
    }


# ── GymProfile ───────────────────────────────────────────────────────────────

def obtener_gym_profile(db: Session, gym_id: str) -> Optional[dict]:
    """Obtiene el perfil del gym. Retorna None si no existe."""
    p = db.query(GymProfile).filter(GymProfile.gym_id == gym_id).first()
    return _gym_profile_to_dict(p) if p else None


def crear_gym_profile(db: Session, gym_id: str, data: Optional[dict] = None) -> dict:
    """Crea perfil de gym (upsert: si ya existe, retorna el existente)."""
    existing = db.query(GymProfile).filter(GymProfile.gym_id == gym_id).first()
    if existing:
        return _gym_profile_to_dict(existing)
    profile = GymProfile(gym_id=gym_id, **(data or {}))
    db.add(profile)
    db.flush()
    logger.info("[DB] GymProfile creado para gym: %s", gym_id)
    return _gym_profile_to_dict(profile)


def actualizar_gym_profile(db: Session, gym_id: str, data: dict) -> Optional[dict]:
    """Actualiza perfil del gym. Crea si no existe."""
    p = db.query(GymProfile).filter(GymProfile.gym_id == gym_id).first()
    if not p:
        p = GymProfile(gym_id=gym_id)
        db.add(p)
        db.flush()
    for key in (
        "nombre_negocio", "telefono", "direccion", "ciudad", "estado", "pais",
        "logo_url", "color_primario", "color_secundario", "sitio_web", "rfc",
        "instagram", "facebook", "tiktok",
        "razon_social", "regimen_fiscal", "codigo_postal_fiscal", "uso_cfdi",
        "horarios_comidas",
    ):
        if key in data and data[key] is not None:
            setattr(p, key, data[key])
    p.updated_at = datetime.now(timezone.utc)
    db.flush()
    logger.info("[DB] GymProfile actualizado: %s", gym_id)
    return _gym_profile_to_dict(p)


def _gym_profile_to_dict(p: GymProfile) -> dict:
    return {
        "gym_id": p.gym_id,
        "nombre_negocio": p.nombre_negocio or "",
        "telefono": p.telefono or "",
        "direccion": p.direccion or "",
        "ciudad": p.ciudad or "",
        "estado": p.estado or "",
        "pais": p.pais or "",
        "logo_url": p.logo_url or "",
        "color_primario": p.color_primario or "#E5B800",
        "color_secundario": p.color_secundario or "#292524",
        "sitio_web": p.sitio_web or "",
        "rfc": p.rfc or "",
        "instagram": p.instagram or "",
        "facebook": p.facebook or "",
        "tiktok": p.tiktok or "",
    }


# ── Planes de Suscripción (configurables por gym) ───────────────────────────

# Planes por defecto que se crean automáticamente para un gym nuevo
_PLANES_DEFAULT = [
    {"nombre": "1 Semana",  "duracion_dias": 7,   "precio": 150.0},
    {"nombre": "1 Mes",     "duracion_dias": 30,  "precio": 500.0},
    {"nombre": "3 Meses",   "duracion_dias": 90,  "precio": 1200.0},
    {"nombre": "6 Meses",   "duracion_dias": 180, "precio": 2000.0},
    {"nombre": "1 Año",     "duracion_dias": 365, "precio": 3500.0},
]


def listar_planes_suscripcion(db: Session, gym_id: str) -> list[dict]:
    """Lista los planes de suscripción del gym. Crea defaults si no existen."""
    planes = db.query(PlanSuscripcion).filter(
        PlanSuscripcion.gym_id == gym_id,
    ).order_by(PlanSuscripcion.duracion_dias.asc()).all()

    if not planes:
        planes = _crear_planes_default(db, gym_id)

    return [_plan_sub_to_dict(p) for p in planes]


def obtener_plan_suscripcion(db: Session, gym_id: str, plan_id: int) -> Optional[dict]:
    """Obtiene un plan de suscripción por ID verificando pertenencia al gym."""
    p = db.query(PlanSuscripcion).filter(
        PlanSuscripcion.id == plan_id,
        PlanSuscripcion.gym_id == gym_id,
    ).first()
    return _plan_sub_to_dict(p) if p else None


def actualizar_plan_suscripcion(
    db: Session, gym_id: str, plan_id: int, data: dict
) -> Optional[dict]:
    """Actualiza precio y/o nombre de un plan de suscripción."""
    p = db.query(PlanSuscripcion).filter(
        PlanSuscripcion.id == plan_id,
        PlanSuscripcion.gym_id == gym_id,
    ).first()
    if not p:
        return None
    for key in ("nombre", "precio", "moneda", "activo"):
        if key in data and data[key] is not None:
            setattr(p, key, data[key])
    p.updated_at = datetime.now(timezone.utc)
    db.flush()
    logger.info("[DB] PlanSuscripcion %d actualizado (gym: %s)", plan_id, gym_id)
    return _plan_sub_to_dict(p)


def _crear_planes_default(db: Session, gym_id: str) -> list[PlanSuscripcion]:
    """Crea los 5 planes de suscripción por defecto para un gym."""
    planes = []
    for d in _PLANES_DEFAULT:
        p = PlanSuscripcion(gym_id=gym_id, **d)
        db.add(p)
        planes.append(p)
    db.flush()
    logger.info("[DB] Planes de suscripción default creados para gym: %s", gym_id)
    return planes


def _plan_sub_to_dict(p: PlanSuscripcion) -> dict:
    return {
        "id": p.id,
        "nombre": p.nombre,
        "duracion_dias": p.duracion_dias,
        "precio": p.precio,
        "moneda": p.moneda,
        "activo": p.activo,
    }

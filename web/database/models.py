"""
web/database/models.py — SQLAlchemy ORM models for MetodoBase Web.

Multi-tenant: clientes y planes pertenecen a un gym (usuario tipo 'gym'/'admin').
Cada query DEBE filtrar por gym_id para aislar datos entre gimnasios.

RBAC: Sistema de roles para equipos de nutriólogos.
- owner: Dueño del gym (legacy tipo='gym')
- admin: Administrador del gym con casi todos los permisos
- nutriologo: Puede gestionar clientes y planes
- viewer: Solo lectura
"""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text,
    CheckConstraint, UniqueConstraint, Enum as SQLEnum, text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


# ── RBAC Enums ────────────────────────────────────────────────────────────────

class UserRole(str, PyEnum):
    """Roles disponibles para usuarios del sistema."""
    OWNER = "owner"           # Dueño del gym - permisos completos
    ADMIN = "admin"           # Administrador - casi todos los permisos
    NUTRIOLOGO = "nutriologo" # Puede gestionar clientes y planes
    VIEWER = "viewer"         # Solo lectura


class AccountType(str, PyEnum):
    """Tipo de cuenta (para compatibilidad con legacy y system admin)."""
    GYM = "gym"       # Legacy - maps to OWNER role
    USER = "user"     # Usuario regular
    ADMIN = "admin"   # System admin (no gym-specific)


class Base(DeclarativeBase):
    pass


# ── Usuarios (auth) ─────────────────────────────────────────────────────────

class Usuario(Base):
    """
    Usuario del sistema.
    
    Para owners (tipo='gym'):
    - gym_id is NULL (ellos SON el gym)
    - role = UserRole.OWNER
    
    Para team members:
    - gym_id apunta al owner del gym
    - role = ADMIN | NUTRIOLOGO | VIEWER
    - invited_by = ID del usuario que los invitó
    """
    __tablename__ = "usuarios"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    nombre = Column(String(150), nullable=False)
    apellido = Column(String(150), nullable=False, default="")
    
    # Legacy tipo - mantener para compatibilidad
    tipo = Column(
        String(20), nullable=False, default="usuario",
    )
    
    # ── RBAC Fields ──
    role = Column(
        SQLEnum(UserRole, native_enum=False, length=20), 
        nullable=False, 
        default=UserRole.VIEWER
    )
    
    # Para team members: a qué gym pertenecen (NULL si es owner)
    team_gym_id = Column(
        String(36), 
        ForeignKey("usuarios.id", ondelete="CASCADE"), 
        nullable=True,
        index=True
    )
    
    # Quién invitó a este usuario (C4 FIX: String para UUID, no Integer)
    invited_by = Column(
        String(36), 
        ForeignKey("usuarios.id", ondelete="SET NULL"), 
        nullable=True
    )
    
    # Invitación pendiente
    invitation_token = Column(String(64), nullable=True, unique=True)
    invitation_expires = Column(DateTime, nullable=True)
    invitation_role = Column(
        SQLEnum(UserRole, native_enum=False, length=20),
        nullable=True
    )
    
    activo = Column(Boolean, nullable=False, default=True)
    # Incremented transactionally on logout/revocation; legacy tokens use zero.
    session_version = Column(Integer, nullable=False, default=0, server_default="0")
    deleted_at = Column(DateTime, nullable=True)
    fecha_registro = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relaciones
    refresh_tokens = relationship("RefreshToken", back_populates="usuario", cascade="all, delete-orphan")
    clientes = relationship("Cliente", back_populates="gym", foreign_keys="[Cliente.gym_id]")
    
    # Team members de este gym (solo para owners)
    team_members = relationship(
        "Usuario",
        backref="parent_gym",
        foreign_keys=[team_gym_id],
        remote_side=[id]
    )

    __table_args__ = (
        CheckConstraint("tipo IN ('gym', 'usuario', 'admin')", name="ck_usuario_tipo"),
        Index("ix_usuarios_deleted", "deleted_at", sqlite_where=text("deleted_at IS NULL")),
        # NOTE: team_gym_id already has index=True on the column definition
        # NOTE: invitation_token already has unique=True which creates an index
    )

    @property
    def effective_gym_id(self) -> str:
        """
        Retorna el gym_id efectivo para queries multi-tenant.
        
        - Si es owner (tipo='gym'), retorna su propio ID
        - Si es team member, retorna team_gym_id
        """
        if self.tipo == "gym" or self.role == UserRole.OWNER:
            return self.id
        return self.team_gym_id
    
    @property
    def is_owner(self) -> bool:
        """True si es owner del gym."""
        return self.tipo == "gym" or self.role == UserRole.OWNER
    
    @property
    def is_team_member(self) -> bool:
        """True si es miembro de un equipo (no owner)."""
        return self.team_gym_id is not None


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    jti = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    expires_at = Column(Float, nullable=False)
    revoked = Column(Boolean, nullable=False, default=False)
    created_at = Column(Float, nullable=False)

    usuario = relationship("Usuario", back_populates="refresh_tokens")


# ── Clientes (multi-tenant via gym_id) ───────────────────────────────────────

class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_cliente = Column(String(36), nullable=False, unique=True, default=lambda: str(uuid.uuid4()))
    gym_id = Column(String(36), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)

    nombre = Column(String(200), nullable=False)
    telefono = Column(String(50))
    email = Column(String(255))
    edad = Column(Integer)
    sexo = Column(String(10))
    peso_kg = Column(Float)
    estatura_cm = Column(Float)
    grasa_corporal_pct = Column(Float)
    masa_magra_kg = Column(Float)
    nivel_actividad = Column(String(30))
    objetivo = Column(String(30))

    fecha_registro = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    ultimo_plan = Column(DateTime)
    total_planes_generados = Column(Integer, default=0)
    activo = Column(Boolean, default=True)
    deleted_at = Column(DateTime, nullable=True)
    notas = Column(Text)
    plantilla_tipo = Column(String(30), default="general")
    alimentos_excluidos = Column(Text, nullable=True)  # JSON list of excluded foods

    # ── Suscripción a nivel cliente ──
    fecha_suscripcion = Column(DateTime, nullable=True)       # Cuándo se suscribió / pagó
    fecha_fin_suscripcion = Column(DateTime, nullable=True, index=True)   # Cuándo expira la suscripción

    @property
    def dias_restantes(self) -> Optional[int]:
        """Días restantes de suscripción. None si no tiene fechas."""
        if not self.fecha_fin_suscripcion:
            return None
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        delta = self.fecha_fin_suscripcion - now
        return max(0, delta.days)

    # Relaciones
    gym = relationship("Usuario", back_populates="clientes", foreign_keys=[gym_id])
    planes = relationship("PlanGenerado", back_populates="cliente", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_clientes_gym_activo", "gym_id", "activo"),
        Index("ix_clientes_gym_nombre", "gym_id", "nombre"),
        Index("ix_clientes_deleted", "deleted_at", sqlite_where=text("deleted_at IS NULL")),
        CheckConstraint("sexo IN ('M', 'F', 'Otro') OR sexo IS NULL", name="ck_cliente_sexo"),
    )


# ── Planes generados ────────────────────────────────────────────────────────

class PlanGenerado(Base):
    __tablename__ = "planes_generados"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_cliente = Column(String(36), ForeignKey("clientes.id_cliente", ondelete="CASCADE"), nullable=False, index=True)
    gym_id = Column(String(36), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)

    fecha_generacion = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    tmb = Column(Float)
    get_total = Column(Float)
    kcal_objetivo = Column(Float)
    kcal_real = Column(Float)
    proteina_g = Column(Float)
    carbs_g = Column(Float)
    grasa_g = Column(Float)
    objetivo = Column(String(30))
    nivel_actividad = Column(String(30))
    ruta_pdf = Column(String(500))
    plan_json = Column(Text, nullable=True)  # serialized plan JSON (persists across container restarts)
    deleted_at = Column(DateTime, nullable=True)
    peso_en_momento = Column(Float)
    grasa_en_momento = Column(Float)
    desviacion_maxima_pct = Column(Float)
    plantilla_tipo = Column(String(30), default="general")
    tipo_plan = Column(String(30), default="menu_fijo")

    # Relaciones
    cliente = relationship("Cliente", back_populates="planes")

    __table_args__ = (
        Index("ix_planes_gym_fecha", "gym_id", "fecha_generacion"),
        Index("ix_planes_generados_deleted", "deleted_at", sqlite_where=text("deleted_at IS NULL")),
    )


# ── Suscripciones (Stripe) ──────────────────────────────────────────────────

class StripeCustomer(Base):
    """
    Relación 1:1 entre gym y Stripe Customer.
    
    Separar de Subscription permite:
    - Tener customer sin subscription (trial expirado)
    - Reactivar subscriptions sin perder historial
    - Múltiples subscriptions futuras (add-ons)
    """
    __tablename__ = "stripe_customers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    gym_id = Column(String(36), ForeignKey("usuarios.id", ondelete="CASCADE"), 
                    nullable=False, unique=True, index=True)
    stripe_customer_id = Column(String(255), nullable=False, unique=True)
    
    email = Column(String(255))  # Email en Stripe (puede diferir del usuario)
    name = Column(String(255))
    
    # Metadata útil
    default_payment_method = Column(String(255))  # pm_xxx
    currency = Column(String(3), default="usd")
    tax_exempt = Column(String(20), default="none")  # none | exempt | reverse
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relación
    gym = relationship("Usuario", backref="stripe_customer", uselist=False)

    # NOTE: stripe_customer_id already has unique=True which creates an index
    # NOTE: gym_id already has unique=True, index=True on column definition


class Subscription(Base):
    """
    Suscripción de un gym a un plan de MetodoBase.
    
    Estados posibles:
    - active: Pago al día
    - trialing: En período de prueba
    - past_due: Pago pendiente (grace period)
    - canceled: Cancelada pero activa hasta period_end
    - unpaid: Sin pago, acceso restringido
    - incomplete: Checkout iniciado pero no completado
    - paused: Pausada por el gym
    """
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    gym_id = Column(String(36), ForeignKey("usuarios.id", ondelete="CASCADE"), 
                    nullable=False, unique=True, index=True)
    
    # ── Plan info ──
    plan = Column(String(30), nullable=False)  # free | standard | gym_comercial | clinica
    stripe_price_id = Column(String(255))  # price_xxx de Stripe
    
    # ── Status ──
    status = Column(String(30), nullable=False, default="active")
    
    # ── Stripe IDs ──
    stripe_customer_id = Column(String(255))
    stripe_subscription_id = Column(String(255), unique=True)
    provider = Column(String(20), nullable=True)
    provider_payment_id = Column(String(255), unique=True, nullable=True)
    
    # ── Periods ──
    current_period_start = Column(DateTime)
    current_period_end = Column(DateTime)
    trial_start = Column(DateTime)
    trial_end = Column(DateTime)
    canceled_at = Column(DateTime)
    ended_at = Column(DateTime)
    
    # ── Flags ──
    cancel_at_period_end = Column(Boolean, default=False)
    
    # ── Limits ──
    max_clientes = Column(Integer, nullable=False, default=10)  # Free default

    # ── Audit ──
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relaciones
    gym = relationship("Usuario", backref="subscription", foreign_keys=[gym_id])

    __table_args__ = (
        CheckConstraint(
            "plan IN ('free', 'standard', 'gym_comercial', 'clinica', 'pro_usuario')",
            name="ck_subscription_plan",
        ),
        CheckConstraint(
            "status IN ('active', 'canceled', 'past_due', 'trialing', 'unpaid', 'incomplete', 'incomplete_expired', 'paused')",
            name="ck_subscription_status",
        ),
    )


class Invoice(Base):
    """
    Historial de facturas de Stripe.
    
    Separar de Payment porque:
    - Una factura puede tener múltiples intentos de pago
    - Contiene line items, descuentos, impuestos
    - Necesario para reportes fiscales
    """
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    gym_id = Column(String(36), ForeignKey("usuarios.id", ondelete="CASCADE"), 
                    nullable=False, index=True)
    stripe_invoice_id = Column(String(255), nullable=False, unique=True)
    stripe_subscription_id = Column(String(255), index=True)
    
    # ── Amounts (en centavos) ──
    amount_due = Column(Integer, nullable=False)
    amount_paid = Column(Integer, nullable=False, default=0)
    amount_remaining = Column(Integer, nullable=False, default=0)
    subtotal = Column(Integer)
    tax = Column(Integer, default=0)
    total = Column(Integer, nullable=False)
    
    currency = Column(String(3), nullable=False, default="usd")
    
    # ── Status ──
    status = Column(String(30), nullable=False)  # draft | open | paid | uncollectible | void
    paid = Column(Boolean, default=False)
    
    # ── URLs ──
    hosted_invoice_url = Column(String(500))  # URL para pagar
    invoice_pdf = Column(String(500))         # URL del PDF
    
    # ── Dates ──
    period_start = Column(DateTime)
    period_end = Column(DateTime)
    due_date = Column(DateTime)
    paid_at = Column(DateTime)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_invoices_gym_created", "gym_id", "created_at"),
    )


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    gym_id = Column(String(36), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    stripe_payment_intent_id = Column(String(255), unique=True)
    stripe_invoice_id = Column(String(255))

    amount_cents = Column(Integer, nullable=False)  # En centavos USD
    currency = Column(String(3), nullable=False, default="usd")
    status = Column(String(30), nullable=False)  # succeeded | failed | pending | refunded
    plan = Column(String(30))

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ── Webhook Idempotency (Stripe) ─────────────────────────────────────────────

class StripeWebhookEvent(Base):
    """
    Registro de eventos de Stripe procesados para idempotencia.
    
    Stripe puede enviar el mismo webhook múltiples veces.
    Esta tabla evita procesamiento duplicado verificando el event_id.
    Se purgan eventos antiguos (>7 días) periódicamente.
    """
    __tablename__ = "stripe_webhook_events"

    event_id = Column(String(255), primary_key=True)  # evt_xxx de Stripe
    event_type = Column(String(100), nullable=False)  # checkout.session.completed, etc.
    processed_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    result = Column(String(255))  # Resultado del procesamiento o error

    __table_args__ = (
        Index("ix_stripe_webhook_events_processed_at", "processed_at"),
    )

class GymProfile(Base):
    __tablename__ = "gym_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    gym_id = Column(String(36), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    nombre_negocio = Column(String(255), default="")
    telefono = Column(String(50), default="")
    direccion = Column(Text, default="")
    ciudad = Column(String(150), default="")
    estado = Column(String(100), default="")
    pais = Column(String(100), default="México")
    logo_url = Column(String(500), default="")
    color_primario = Column(String(7), default="#E5B800")
    color_secundario = Column(String(7), default="#292524")
    sitio_web = Column(String(500), default="")
    rfc = Column(String(20), default="")
    # ── Datos Fiscales (CFDI México) ──
    razon_social = Column(String(255), default="")  # Nombre fiscal oficial
    regimen_fiscal = Column(String(10), default="")  # Clave SAT: "601", "612", etc.
    codigo_postal_fiscal = Column(String(5), default="")  # CP del domicilio fiscal
    uso_cfdi = Column(String(10), default="G03")  # Uso CFDI default: "G03" (Gastos en general)
    instagram = Column(String(255), default="")
    facebook = Column(String(255), default="")
    tiktok = Column(String(255), default="")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    horarios_comidas = Column(JSON, nullable=True, default=None)

    gym = relationship("Usuario", backref="gym_profile", foreign_keys=[gym_id])


# ── Planes de suscripción configurables por gym ─────────────────────────────

class PlanSuscripcion(Base):
    """
    Planes de suscripción que cada gym define con su propio precio.
    Duración en días: 7 (1 semana), 30 (1 mes), 90 (3 meses), 180 (6 meses), 365 (1 año).
    """
    __tablename__ = "planes_suscripcion"

    id = Column(Integer, primary_key=True, autoincrement=True)
    gym_id = Column(String(36), ForeignKey("usuarios.id", ondelete="CASCADE"),
                    nullable=False, index=True)
    template_key = Column(String(40), nullable=True)

    nombre = Column(String(100), nullable=False)        # "1 Semana", "1 Mes", etc.
    duracion_dias = Column(Integer, nullable=False)      # 7, 30, 90, 180, 365
    precio = Column(Float, nullable=False, default=0.0)  # Precio en moneda local
    moneda = Column(String(10), nullable=False, default="MXN")
    activo = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    gym = relationship("Usuario", backref="planes_suscripcion", foreign_keys=[gym_id])

    __table_args__ = (
        Index("ix_planes_sub_gym", "gym_id", "activo"),
        UniqueConstraint("gym_id", "template_key", name="uq_membership_gym_template"),
    )


# ── Historial de progreso del cliente ────────────────────────────────────────

class ClientProgress(Base):
    __tablename__ = "client_progress"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_cliente = Column(String(36), ForeignKey("clientes.id_cliente", ondelete="CASCADE"), nullable=False, index=True)
    gym_id = Column(String(36), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)

    fecha = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    peso_kg = Column(Float)
    grasa_corporal_pct = Column(Float)
    masa_magra_kg = Column(Float)
    notas = Column(Text, default="")

    cliente = relationship("Cliente", backref="progreso", foreign_keys=[id_cliente])

    __table_args__ = (
        Index("ix_progress_cliente_fecha", "id_cliente", "fecha"),
    )


# ── Log de auditoría ────────────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    gym_id = Column(String(36), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    accion = Column(String(50), nullable=False)  # login, crear_cliente, generar_plan, etc.
    entidad = Column(String(50))  # cliente, plan, suscripcion
    entidad_id = Column(String(36))
    detalle = Column(Text, default="")
    ip = Column(String(45))
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


# ── Branding dinámico per-gym ────────────────────────────────────────────────

class GymBranding(Base):
    """Configuración de branding personalizada por gimnasio."""
    __tablename__ = "gym_branding"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    gym_id = Column(String(36), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    nombre_gym = Column(String(255), nullable=False, default="")
    nombre_corto = Column(String(100), nullable=False, default="Método Base")
    tagline = Column(String(255), nullable=False, default="")
    telefono = Column(String(30), nullable=False, default="")
    email = Column(String(255), nullable=False, default="")
    whatsapp = Column(String(30), nullable=False, default="")
    direccion_linea1 = Column(String(255), nullable=False, default="")
    direccion_linea2 = Column(String(255), nullable=False, default="")
    direccion_linea3 = Column(String(255), nullable=False, default="")
    instagram = Column(String(100), nullable=False, default="")
    facebook = Column(String(255), nullable=False, default="")
    tiktok = Column(String(100), nullable=False, default="")
    cuota_mensual = Column(Float, nullable=False, default=0.0)
    logo_path = Column(String(500), nullable=False, default="assets/logo.png")
    color_primario = Column(String(7), nullable=False, default="#FFEB3B")
    color_secundario = Column(String(7), nullable=False, default="#FFD700")

    gym = relationship("Usuario", backref="branding_config")


# ── License Activations (persistent — replaces in-memory dict) ───────────────

class LicenseActivation(Base):
    """Activaciones de licencia persistidas en DB (no en memoria)."""
    __tablename__ = "license_activations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    gym_id = Column(String(36), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    issued_license_id = Column(Integer, ForeignKey("gym_licenses.id", ondelete="SET NULL"), nullable=True, index=True)
    hardware_id = Column(String(128), nullable=False, unique=True, index=True)
    clave_hash = Column(String(64), nullable=False)  # SHA-256 de la clave
    email = Column(String(120), nullable=False)
    plan = Column(String(30), nullable=False)
    activa = Column(Boolean, default=True)
    revocada = Column(Boolean, default=False)
    expira = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_license_activations_email", "email"),
    )


# ── Checkout Sessions (persistent — replaces in-memory dict) ─────────────────

class CheckoutSession(Base):
    """Sesiones de checkout persistidas en DB (no en memoria)."""
    __tablename__ = "checkout_sessions"

    id = Column(String(64), primary_key=True)  # Session ID interno
    gym_id = Column(String(36), ForeignKey("usuarios.id"), nullable=False, index=True)
    stripe_session_id = Column(String(255), unique=True, nullable=True)
    plan = Column(String(30), nullable=False)
    email = Column(String(120), nullable=False)
    status = Column(String(30), default="pending")  # pending | completed | expired
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    gym = relationship("Usuario", backref="checkout_sessions", foreign_keys=[gym_id])


# ── Auth Audit Log ────────────────────────────────────────────────────────────

class AuthAuditLog(Base):
    """Registro de auditoría de eventos de autenticación."""
    __tablename__ = "auth_audit_log"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    gym_id = Column(String(36), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(String(36), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    request_id = Column(String(36), nullable=True)
    event_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    __table_args__ = (
        Index("ix_auth_audit_gym_event", "gym_id", "event_type"),
        Index("ix_auth_audit_gym", "gym_id", "created_at"),
        Index("ix_auth_audit_user", "user_id", "created_at"),
        Index("ix_auth_audit_type", "event_type", "created_at"),
    )


# ── Gym Settings ──────────────────────────────────────────────────────────────

class GymSettings(Base):
    """Configuración operativa por gym (trial, timezone, locale)."""
    __tablename__ = "gym_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    legacy_id = Column(String(36), nullable=True, unique=True)
    gym_id = Column(String(36), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    trial_days = Column(Integer, default=14)
    trial_max_clients = Column(Integer, default=50)
    strict_mode = Column(Boolean, default=True)
    timezone = Column(String(64), default="America/Mexico_City")
    locale = Column(String(10), default="es_MX")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


# ── Gym License ───────────────────────────────────────────────────────────────

class GymLicense(Base):
    """Licencia persistente por gym (reemplaza sistema in-memory)."""
    __tablename__ = "gym_licenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    legacy_id = Column(String(36), nullable=True, unique=True)
    gym_id = Column(String(36), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    license_key = Column(String(255), nullable=False, unique=True)
    plan_tier = Column(String(30), nullable=False)
    max_clients = Column(Integer, nullable=False, default=50)
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    payment_provider = Column(String(30), nullable=True)
    payment_reference = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


# ── Suscripción de usuario individual ────────────────────────────────────────

class UserSubscription(Base):
    """
    Suscripción para usuarios individuales (tipo='usuario').
    Planes: starter (gratis, 1 plan/mes) | pro ($79 MXN, 5 planes/mes).
    """
    __tablename__ = "user_subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("usuarios.id", ondelete="CASCADE"),
                     nullable=False, unique=True, index=True)
    plan = Column(String(20), nullable=False, default="starter")
    max_planes_mes = Column(Integer, nullable=False, default=1)
    planes_usados_mes = Column(Integer, nullable=False, default=0)
    mes_actual = Column(String(7), nullable=False)  # "2026-03"
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("Usuario", backref="user_subscription", foreign_keys=[user_id])

    __table_args__ = (
        CheckConstraint("plan IN ('starter', 'pro')", name="ck_user_sub_plan"),
        CheckConstraint("status IN ('active', 'canceled')", name="ck_user_sub_status"),
    )


class PurchaseIntent(Base):
    """Durable purchase identity committed before contacting a payment provider.

    Amounts are MXN minor units. Operation keys are reused after provider or
    database failures; no card secrets or provider client secrets are stored.
    """
    __tablename__ = "purchase_intents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subject_id = Column(String(36), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(20), nullable=False)
    operation = Column(String(30), nullable=False)
    request_key = Column(String(128), nullable=False)
    plan = Column(String(30), nullable=False)
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String(3), nullable=False, default="mxn")
    status = Column(String(30), nullable=False, default="pending")
    provider_customer_id = Column(String(255), nullable=True)
    provider_reference_id = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("subject_id", "provider", "operation", "request_key", name="uq_purchase_operation_key"),
        CheckConstraint("amount_cents > 0", name="ck_purchase_positive_amount"),
    )


class GenerationReservation(Base):
    """One individual generation request and its quota consumption/result."""
    __tablename__ = "generation_reservations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    request_key = Column(String(128), nullable=False)
    period = Column(String(7), nullable=False)
    status = Column(String(20), nullable=False, default="reserved")
    plan_id = Column(Integer, ForeignKey("planes_generados.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("user_id", "request_key", name="uq_generation_request_key"),
        CheckConstraint("status IN ('reserved', 'completed', 'released')", name="ck_generation_reservation_status"),
    )


class ProviderSubjectAssociation(Base):
    """Minimal provider resource identity; contains no entitlement or money.

    Legacy links come only from existing canonical mappings, with provenance.
    Verified callbacks use this control plane before entering a tenant scope.
    """
    __tablename__ = "provider_subject_associations"

    provider = Column(String(20), primary_key=True)
    resource_type = Column(String(30), primary_key=True)
    resource_id = Column(String(255), primary_key=True)
    subject_id = Column(String(36), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    provenance = Column(String(30), nullable=False)
    source_ref = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint("provider IN ('stripe','mercadopago')", name="ck_provider_subject_provider"),
        CheckConstraint("resource_type IN ('customer','subscription','payment','preference')", name="ck_provider_subject_resource"),
        CheckConstraint("provenance IN ('legacy_subscription','legacy_customer','verified_purchase')", name="ck_provider_subject_provenance"),
    )


class GymGenerationReservation(Base):
    """Durable gym quota ledger, retained when a client/plan reference is removed."""
    __tablename__ = "gym_generation_reservations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    gym_id = Column(String(36), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    client_id = Column(String(36), ForeignKey("clientes.id_cliente", ondelete="SET NULL"), nullable=True, index=True)
    request_key = Column(String(128), nullable=False)
    request_hash = Column(String(64), nullable=False)
    period = Column(String(7), nullable=False)
    local_date = Column(Date, nullable=False)
    timezone = Column(String(64), nullable=False)
    catalog_plan = Column(String(30), nullable=False)
    status = Column(String(20), nullable=False, default="reserved")
    plan_id = Column(Integer, ForeignKey("planes_generados.id", ondelete="SET NULL"), nullable=True, unique=True)
    persisted_at = Column(DateTime, nullable=True)
    result_json = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    __table_args__ = (
        UniqueConstraint("gym_id", "request_key", name="uq_gym_generation_request_key"),
        CheckConstraint("status IN ('reserved', 'completed', 'released')", name="ck_gym_generation_status"),
        CheckConstraint("length(request_hash) = 64", name="ck_gym_generation_request_hash"),
        CheckConstraint("status <> 'released' OR persisted_at IS NULL", name="ck_gym_generation_no_persisted_refund"),
        CheckConstraint("status <> 'completed' OR result_json IS NOT NULL", name="ck_gym_generation_completed_result"),
        Index("ix_gym_generation_period_status", "gym_id", "period", "status"),
        Index("ix_gym_generation_day_client", "gym_id", "local_date", "client_id", "status"),
    )

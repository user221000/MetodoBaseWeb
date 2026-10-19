"""
web/services/email_service.py — Servicio de email transaccional (Resend).

Centraliza TODOS los envíos de email. Degradación elegante:
si RESEND_API_KEY no está configurada, registra en log y no lanza error.

Emails soportados:
  - Bienvenida al registrarse
  - Plan nutricional generado (con adjunto PDF)
  - Suscripción activada
  - Suscripción cancelada
  - Pago fallido
"""
import logging
from html import escape
from pathlib import Path
from typing import Optional

from web.settings import get_settings
from web.storage.objects import MAX_OBJECT_BYTES

logger = logging.getLogger(__name__)

# ── Constantes ────────────────────────────────────────────────────────────────

_FROM_EMAIL = "MetodoBase <no-reply@metodobase.app>"
_BRAND_COLOR = "#FBBF24"
_BG_COLOR = "#0C0B09"
_CARD_BG = "#141519"
_TEXT_COLOR = "#FFFFFF"
_TEXT_MUTED = "#a0a2a8"


# ── Inicialización ────────────────────────────────────────────────────────────

def _is_configured() -> bool:
    return bool(get_settings().RESEND_API_KEY)


def _send(to: str, subject: str, html: str, attachments: Optional[list] = None) -> bool:
    """
    Envía email vía Resend. Retorna True si se envió, False si no (sin error).
    En dev sin API key, solo loguea.
    """
    if not _is_configured():
        logger.info("Email delivery_skipped reason=not_configured")
        return False

    import resend
    resend.api_key = get_settings().RESEND_API_KEY

    params: dict = {
        "from_": _FROM_EMAIL,
        "to": [to],
        "subject": subject,
        "html": html,
    }

    if attachments:
        params["attachments"] = attachments

    try:
        resend.Emails.send(params)
        logger.info("Email delivery_sent")
        return True
    except Exception as e:
        logger.error("Email transport failed class=%s", type(e).__name__)
        return False


# ── Templates HTML ────────────────────────────────────────────────────────────

def _base_layout(content: str) -> str:
    """Layout base dark premium para todos los emails."""
    return f"""\
<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:{_BG_COLOR};font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:{_BG_COLOR};padding:24px 0;">
<tr><td align="center">
  <table width="600" cellpadding="0" cellspacing="0" style="background:{_CARD_BG};border-radius:12px;overflow:hidden;max-width:100%;">
    <!-- Header -->
    <tr><td style="background:{_BRAND_COLOR};padding:20px 32px;">
      <h1 style="margin:0;font-size:22px;color:{_BG_COLOR};font-weight:800;letter-spacing:-0.5px;">
        ⚡ Método Base
      </h1>
    </td></tr>
    <!-- Body -->
    <tr><td style="padding:32px;color:{_TEXT_COLOR};line-height:1.6;font-size:15px;">
      {content}
    </td></tr>
    <!-- Footer -->
    <tr><td style="padding:16px 32px;border-top:1px solid #222;text-align:center;">
      <p style="margin:0;font-size:12px;color:{_TEXT_MUTED};">
        © Método Base — Sistema de Planes Nutricionales
      </p>
    </td></tr>
  </table>
</td></tr>
</table>
</body>
</html>"""


# ── Emails de negocio ────────────────────────────────────────────────────────

def send_welcome(email: str, nombre: str) -> bool:
    """Email de bienvenida tras registro."""
    content = f"""\
<h2 style="margin:0 0 16px;color:{_BRAND_COLOR};">¡Bienvenido, {nombre}!</h2>
<p>Tu cuenta en <strong>Método Base</strong> ha sido creada exitosamente.</p>
<p>Ya puedes:</p>
<ul style="padding-left:20px;color:{_TEXT_MUTED};">
  <li>Registrar tus clientes</li>
  <li>Generar planes nutricionales personalizados</li>
  <li>Exportar planes en PDF profesional</li>
</ul>
<p style="margin-top:24px;">
  <a href="https://app.metodobase.app/dashboard"
     style="display:inline-block;padding:12px 28px;background:{_BRAND_COLOR};color:{_BG_COLOR};
            text-decoration:none;border-radius:8px;font-weight:700;font-size:15px;">
    Ir al Dashboard →
  </a>
</p>
<p style="color:{_TEXT_MUTED};font-size:13px;margin-top:24px;">
  Si no creaste esta cuenta, ignora este correo.
</p>"""
    return _send(email, "¡Bienvenido a Método Base! ⚡", _base_layout(content))


def send_plan_generated(
    email: str, nombre_cliente: str, pdf_path: Optional[str] = None, *, pdf_content: bytes | None = None,
) -> bool:
    """Notify with authorized private-object bytes, or the legacy desktop path.

    The caller must authorize bytes for the recipient/tenant before passing
    them. A supplied byte payload never falls back to a filename on error.
    """
    subject_name = str(nombre_cliente).replace("\r", " ").replace("\n", " ")
    safe_name = escape(str(nombre_cliente), quote=True)
    content = f"""\
<h2 style="margin:0 0 16px;color:{_BRAND_COLOR};">Plan nutricional listo 🎯</h2>
<p>Se ha generado un nuevo plan nutricional para <strong>{safe_name}</strong>.</p>
<p>Puedes consultarlo directamente en tu dashboard o descargarlo en PDF.</p>
<p style="margin-top:24px;">
  <a href="https://app.metodobase.app/dashboard"
     style="display:inline-block;padding:12px 28px;background:{_BRAND_COLOR};color:{_BG_COLOR};
            text-decoration:none;border-radius:8px;font-weight:700;font-size:15px;">
    Ver plan →
  </a>
</p>"""

    attachments = None
    if pdf_content is not None:
        if (not isinstance(pdf_content, bytes) or not 0 < len(pdf_content) <= MAX_OBJECT_BYTES
                or not pdf_content.startswith(b"%PDF-")):
            logger.warning("Email delivery_skipped reason=invalid_plan_attachment")
            return False
        attachments = [{"filename": "plan.pdf", "content": list(pdf_content)}]
    elif pdf_path:
        p = Path(pdf_path)
        if p.exists():
            data = p.read_bytes()
            attachments = [{
                "filename": p.name,
                "content": list(data),
            }]

    return _send(
        email,
        f"Plan nutricional generado — {subject_name}",
        _base_layout(content),
        attachments=attachments,
    )


def send_subscription_activated(email: str, nombre: str, plan: str) -> bool:
    """Notificación de suscripción activada."""
    plan_display = plan.title()
    content = f"""\
<h2 style="margin:0 0 16px;color:{_BRAND_COLOR};">Suscripción activada ✅</h2>
<p>Hola, <strong>{nombre}</strong>.</p>
<p>Tu plan <strong style="color:{_BRAND_COLOR};">{plan_display}</strong> está activo.
   Ya puedes disfrutar de todas las funcionalidades incluidas.</p>
<p style="margin-top:24px;">
  <a href="https://app.metodobase.app/dashboard"
     style="display:inline-block;padding:12px 28px;background:{_BRAND_COLOR};color:{_BG_COLOR};
            text-decoration:none;border-radius:8px;font-weight:700;font-size:15px;">
    Ir al Dashboard →
  </a>
</p>"""
    return _send(email, f"Suscripción {plan_display} activada — Método Base", _base_layout(content))


def send_subscription_canceled(email: str, nombre: str) -> bool:
    """Notificación de suscripción cancelada."""
    content = f"""\
<h2 style="margin:0 0 16px;color:{_BRAND_COLOR};">Suscripción cancelada</h2>
<p>Hola, <strong>{nombre}</strong>.</p>
<p>Tu suscripción ha sido cancelada. Seguirás teniendo acceso hasta
   el final del período de facturación actual.</p>
<p style="color:{_TEXT_MUTED};font-size:13px;margin-top:16px;">
  Si fue un error, puedes reactivar tu plan desde el dashboard en cualquier momento.
</p>"""
    return _send(email, "Suscripción cancelada — Método Base", _base_layout(content))


def send_payment_failed(email: str, nombre: str) -> bool:
    """Notificación de pago fallido."""
    content = f"""\
<h2 style="margin:0 0 16px;color:#FF4444;">Problema con tu pago ⚠️</h2>
<p>Hola, <strong>{nombre}</strong>.</p>
<p>No pudimos procesar tu último pago. Por favor revisa tu método de pago
   para evitar la interrupción de tu servicio.</p>
<p style="margin-top:24px;">
  <a href="https://app.metodobase.app/dashboard"
     style="display:inline-block;padding:12px 28px;background:{_BRAND_COLOR};color:{_BG_COLOR};
            text-decoration:none;border-radius:8px;font-weight:700;font-size:15px;">
    Actualizar método de pago →
  </a>
</p>"""
    return _send(email, "⚠️ Problema con tu pago — Método Base", _base_layout(content))


def send_team_invitation(
    email: str,
    nombre: str,
    gym_name: str,
    role: str,
    invite_url: str,
) -> bool:
    """Envía email de invitación al equipo del gym."""
    subject = f"Invitación a {gym_name} — Método Base".replace("\r", " ").replace("\n", " ")
    nombre, gym_name, role, invite_url = (escape(str(value), quote=True) for value in (nombre, gym_name, role, invite_url))
    content = f"""\
<h2 style="margin:0 0 16px;color:#22c55e;">¡Has sido invitado!</h2>
<p>Hola, <strong>{nombre}</strong>.</p>
<p><strong>{gym_name}</strong> te ha invitado a unirte como
<strong>{role}</strong> en Método Base.</p>
<p style="margin-top:24px;">
  <a href="{invite_url}"
     style="display:inline-block;padding:12px 28px;background:#22c55e;color:white;
            text-decoration:none;border-radius:8px;font-weight:700;font-size:15px;">
    Aceptar Invitación →
  </a>
</p>
<p style="color:#888;font-size:13px;">Esta invitación expira en 7 días.</p>"""
    return _send(email, subject, _base_layout(content))

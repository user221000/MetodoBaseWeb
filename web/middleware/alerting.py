"""
web/middleware/alerting.py — Sistema de alertas de errores.

Proporciona:
- ErrorAlerter: Gestor central de alertas
- Canales de notificación: Slack, Email, Webhook, Log
- Detección de anomalías (spikes de errores)
- Cooldown para evitar spam de alertas

Uso:
    from web.middleware import ErrorAlerter, AlertChannel
    
    alerter = ErrorAlerter()
    alerter.add_channel(AlertChannel.SLACK, webhook_url="https://hooks.slack.com/...")
    
    # En error handler
    alerter.track_error(e, extra_context={"method": "POST"})

Configuración via ENV:
    ALERT_ENABLED=true
    ALERT_COOLDOWN_MINUTES=5
    ALERT_SLACK_WEBHOOK=https://hooks.slack.com/services/...
    ALERT_EMAIL_TO=admin@example.com
    ALERT_WEBHOOK_URL=https://your-webhook-endpoint.com/alerts
"""

import os
import json
import time
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional
from threading import Lock

logger = logging.getLogger(__name__)


# ── Configuración ────────────────────────────────────────────────────────────

ALERT_ENABLED = os.getenv("ALERT_ENABLED", "true").lower() == "true"
ALERT_COOLDOWN_MINUTES = int(os.getenv("ALERT_COOLDOWN_MINUTES", "5"))
ALERT_SLACK_WEBHOOK = os.getenv("ALERT_SLACK_WEBHOOK", "")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "")
ALERT_WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL", "")


# ── Enums ────────────────────────────────────────────────────────────────────

class AlertSeverity(Enum):
    """Niveles de severidad de alertas."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Canales de notificación disponibles."""
    LOG = "log"
    SLACK = "slack"
    EMAIL = "email"
    WEBHOOK = "webhook"


# ── Estructuras de Datos ─────────────────────────────────────────────────────

@dataclass
class Alert:
    """Representa una alerta individual."""
    id: str
    timestamp: float
    severity: AlertSeverity
    title: str
    message: str
    context: dict = field(default_factory=dict)
    source: str = "system"
    acknowledged: bool = False
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": datetime.fromtimestamp(self.timestamp, tz=timezone.utc).isoformat(),
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "context": self.context,
            "source": self.source,
            "acknowledged": self.acknowledged,
        }
    
    def to_slack_message(self) -> dict:
        """Formatea para Slack webhook."""
        color_map = {
            AlertSeverity.INFO: "#36a64f",
            AlertSeverity.WARNING: "#ffcc00",
            AlertSeverity.CRITICAL: "#ff0000",
        }
        emoji_map = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.CRITICAL: "🚨",
        }
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji_map[self.severity]} {self.title}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": self.message
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Severidad:* {self.severity.value} | *Fuente:* {self.source} | *Hora:* {datetime.fromtimestamp(self.timestamp, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
                    }
                ]
            }
        ]
        
        if self.context:
            context_text = "\n".join(f"• *{k}:* `{v}`" for k, v in self.context.items())
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Contexto:*\n{context_text}"
                }
            })
        
        return {
            "attachments": [{
                "color": color_map[self.severity],
                "blocks": blocks
            }]
        }


# ── Notificadores ────────────────────────────────────────────────────────────

class BaseNotifier:
    """Clase base para notificadores."""
    
    def send(self, alert: Alert) -> bool:
        """Envía la alerta. Retorna True si fue exitoso."""
        raise NotImplementedError


class LogNotifier(BaseNotifier):
    """Notifica mediante logs."""
    
    def send(self, alert: Alert) -> bool:
        level_map = {
            AlertSeverity.INFO: logging.INFO,
            AlertSeverity.WARNING: logging.WARNING,
            AlertSeverity.CRITICAL: logging.ERROR,
        }
        logger.log(
            level_map[alert.severity],
            f"[ALERT] {alert.title}: {alert.message} | context={alert.context}"
        )
        return True


class SlackNotifier(BaseNotifier):
    """Notifica vía Slack webhook."""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    def send(self, alert: Alert) -> bool:
        if not self.webhook_url:
            logger.warning("Slack webhook no configurado")
            return False
        
        try:
            from web.services.http_client import http_post
            
            response = http_post(
                self.webhook_url,
                json=alert.to_slack_message()
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error enviando a Slack: {e}")
            return False


class WebhookNotifier(BaseNotifier):
    """Notifica vía webhook HTTP genérico."""
    
    def __init__(self, url: str, headers: Optional[dict] = None):
        self.url = url
        self.headers = headers or {}
    
    def send(self, alert: Alert) -> bool:
        if not self.url:
            logger.warning("Webhook URL no configurado")
            return False
        
        try:
            from web.services.http_client import http_post
            
            response = http_post(
                self.url,
                json=alert.to_dict(),
                headers=self.headers
            )
            return response.status_code < 400
        except Exception as e:
            logger.error(f"Error enviando a webhook: {e}")
            return False


class EmailNotifier(BaseNotifier):
    """Notifica vía email (usando SMTP o servicio externo)."""
    
    def __init__(self, to_email: str, api_key: Optional[str] = None):
        self.to_email = to_email
        self.api_key = api_key or os.getenv("RESEND_API_KEY", "")
    
    def send(self, alert: Alert) -> bool:
        if not self.to_email:
            logger.warning("Email destino no configurado")
            return False
        
        # Intento con Resend si hay API key
        if self.api_key:
            return self._send_via_resend(alert)
        
        # Fallback a log
        logger.info(f"Email alert (no API key): TO={self.to_email}, SUBJECT=[{alert.severity.value}] {alert.title}")
        return True
    
    def _send_via_resend(self, alert: Alert) -> bool:
        """Envía email usando Resend API."""
        try:
            from web.services.http_client import http_post
            
            response = http_post(
                "https://api.resend.com/emails",
                json={
                    "from": "MetodoBase Alerts <alerts@mail.metodobase.com>",
                    "to": [self.to_email],
                    "subject": f"[{alert.severity.value.upper()}] {alert.title}",
                    "html": f"""
                    <h2>{alert.title}</h2>
                    <p><strong>Severidad:</strong> {alert.severity.value}</p>
                    <p><strong>Hora:</strong> {datetime.fromtimestamp(alert.timestamp, tz=timezone.utc).isoformat()}</p>
                    <p><strong>Mensaje:</strong> {alert.message}</p>
                    <h3>Contexto:</h3>
                    <pre>{json.dumps(alert.context, indent=2)}</pre>
                    """
                },
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            return response.status_code < 400
        except Exception as e:
            logger.error(f"Error enviando email via Resend: {e}")
            return False


# ── Error Alerter ────────────────────────────────────────────────────────────

class ErrorAlerter:
    """
    Gestor central de alertas de errores.
    
    Features:
    - Múltiples canales de notificación
    - Cooldown para evitar spam
    - Historial de alertas
    - Detección de spikes
    """
    
    def __init__(
        self,
        enabled: bool = ALERT_ENABLED,
        cooldown_minutes: int = ALERT_COOLDOWN_MINUTES,
    ):
        self.enabled = enabled
        self.cooldown_seconds = cooldown_minutes * 60
        
        self._notifiers: dict[AlertChannel, BaseNotifier] = {}
        self._alert_history: deque[Alert] = deque(maxlen=100)
        self._cooldowns: dict[str, float] = {}  # alert_key -> last_sent
        self._lock = Lock()
        self._alert_counter = 0
        
        # Error tracking para spikes
        self._error_timestamps: deque[float] = deque(maxlen=1000)
        
        # Configurar canales por defecto
        self._setup_default_channels()
        
        logger.info(f"ErrorAlerter inicializado: enabled={enabled}, cooldown={cooldown_minutes}min")
    
    def _setup_default_channels(self):
        """Configura canales según variables de entorno."""
        # Siempre log
        self.add_channel(AlertChannel.LOG)
        
        # Slack si configurado
        if ALERT_SLACK_WEBHOOK:
            self.add_channel(AlertChannel.SLACK, webhook_url=ALERT_SLACK_WEBHOOK)
        
        # Email si configurado
        if ALERT_EMAIL_TO:
            self.add_channel(AlertChannel.EMAIL, to_email=ALERT_EMAIL_TO)
        
        # Webhook si configurado
        if ALERT_WEBHOOK_URL:
            self.add_channel(AlertChannel.WEBHOOK, url=ALERT_WEBHOOK_URL)
    
    def add_channel(self, channel: AlertChannel, **kwargs):
        """Agrega un canal de notificación."""
        if channel == AlertChannel.LOG:
            self._notifiers[channel] = LogNotifier()
        elif channel == AlertChannel.SLACK:
            self._notifiers[channel] = SlackNotifier(kwargs.get("webhook_url", ""))
        elif channel == AlertChannel.EMAIL:
            self._notifiers[channel] = EmailNotifier(
                kwargs.get("to_email", ""),
                kwargs.get("api_key")
            )
        elif channel == AlertChannel.WEBHOOK:
            self._notifiers[channel] = WebhookNotifier(
                kwargs.get("url", ""),
                kwargs.get("headers")
            )
    
    def send_alert(
        self,
        title: str,
        message: str = "",
        severity: str = "warning",
        context: Optional[dict] = None,
        source: str = "system",
        bypass_cooldown: bool = False,
    ) -> Optional[Alert]:
        """
        Envía una alerta a todos los canales configurados.
        
        Args:
            title: Título corto de la alerta
            message: Descripción detallada
            severity: "info", "warning", o "critical"
            context: Datos adicionales
            source: Origen de la alerta
            bypass_cooldown: Ignorar cooldown
        
        Returns:
            Alert object si se envió, None si bloqueado por cooldown
        """
        if not self.enabled:
            return None
        
        with self._lock:
            # Generar ID único
            self._alert_counter += 1
            alert_id = f"alert_{int(time.time())}_{self._alert_counter}"
            
            # Verificar cooldown
            cooldown_key = f"{severity}:{title}"
            last_sent = self._cooldowns.get(cooldown_key, 0)
            
            if not bypass_cooldown and (time.time() - last_sent) < self.cooldown_seconds:
                logger.debug(f"Alerta bloqueada por cooldown: {title}")
                return None
            
            # Crear alerta
            alert = Alert(
                id=alert_id,
                timestamp=time.time(),
                severity=AlertSeverity(severity),
                title=title,
                message=message or title,
                context=context or {},
                source=source,
            )
            
            # Guardar en historial
            self._alert_history.append(alert)
            self._cooldowns[cooldown_key] = time.time()
            
            # Enviar a todos los canales
            for channel, notifier in self._notifiers.items():
                try:
                    notifier.send(alert)
                except Exception as e:
                    logger.error(f"Error enviando alerta por {channel.value}: {e}")
            
            return alert
    
    def track_error(self, error: Exception, request_path: str = "", extra_context: Optional[dict] = None):
        """
        Registra un error y envía alerta si hay spike.
        
        Args:
            error: Excepción ocurrida
            request_path: Argumento legacy aceptado, no retenido (puede contener identidad)
            extra_context: Solo se conserva method si es un verbo HTTP conocido
        """
        with self._lock:
            self._error_timestamps.append(time.time())
        
        # Verificar spike (más de 10 errores en 1 minuto)
        one_minute_ago = time.time() - 60
        recent_errors = sum(1 for ts in self._error_timestamps if ts > one_minute_ago)
        
        context = {
            "error_type": type(error).__name__,
            "recent_errors_1min": recent_errors,
        }
        method = extra_context.get("method") if isinstance(extra_context, dict) else None
        if isinstance(method, str) and method in {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE", "CONNECT"}:
            context["method"] = method
        
        if recent_errors > 10:
            self.send_alert(
                title="Spike de errores detectado",
                message=f"{recent_errors} errores en el último minuto. Último: {type(error).__name__}",
                severity="critical",
                context=context,
                source="error_tracker",
            )
        elif recent_errors > 5:
            self.send_alert(
                title="Incremento de errores",
                message=f"{recent_errors} errores en el último minuto",
                severity="warning",
                context=context,
                source="error_tracker",
            )
    
    def get_alert_history(self, limit: int = 20) -> list[dict]:
        """Obtiene historial de alertas recientes."""
        with self._lock:
            return [a.to_dict() for a in list(self._alert_history)[-limit:]]
    
    def get_status(self) -> dict:
        """Estado del sistema de alertas."""
        return {
            "enabled": self.enabled,
            "cooldown_minutes": self.cooldown_seconds // 60,
            "channels_configured": list(self._notifiers.keys()),
            "total_alerts_sent": len(self._alert_history),
            "recent_errors_1min": sum(1 for ts in self._error_timestamps if ts > time.time() - 60),
        }


# ── Singleton Alerter ────────────────────────────────────────────────────────

_error_alerter: Optional[ErrorAlerter] = None


def get_error_alerter() -> ErrorAlerter:
    """Obtiene el alerter singleton."""
    global _error_alerter
    if _error_alerter is None:
        _error_alerter = ErrorAlerter()
    return _error_alerter


def send_alert(
    title: str,
    message: str = "",
    severity: str = "warning",
    context: Optional[dict] = None,
    source: str = "system",
) -> Optional[Alert]:
    """
    Función de conveniencia para enviar alertas.
    
    Ejemplo:
        send_alert("Error de base de datos", severity="critical", context={"failure_count": 1})
    """
    return get_error_alerter().send_alert(title, message, severity, context, source)


def track_error(error: Exception, request_path: str = "", extra_context: Optional[dict] = None):
    """
    Función de conveniencia para trackear errores.
    
    Ejemplo:
        try:
            ...
        except Exception as e:
            track_error(e, extra_context={"method": request.method})
            raise
    """
    get_error_alerter().track_error(error, request_path, extra_context)

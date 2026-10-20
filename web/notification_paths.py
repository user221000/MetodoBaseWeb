"""Exact36 route shapes, including redirects/errors; no adjacent prefixes."""
import re

_EXACT=frozenset({"/api/notificaciones/contexto","/api/notificaciones/preferencias",
    "/api/notificaciones/candidatos","/api/notificaciones/outbox","/api/notificaciones/metricas",
    "/api/notificaciones/observar","/api/notificaciones/excluir","/notificaciones/excluir",
    "/recordatorios","/mis-recordatorios"})
_RESOURCE=re.compile(r"/api/notificaciones/(?:preferencias/[^/]+|outbox/[^/]+/cancelar)\Z")


def is_notification_private(path):
    stripped=path.rstrip("/")
    return stripped in _EXACT or _RESOURCE.fullmatch(stripped) is not None

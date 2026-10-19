"""Exact private wire34 paths, including canonical slash redirects only."""
import re

_STATIC = frozenset({"/seguimiento", "/api/seguimiento/contexto", "/api/seguimiento/responsables",
    "/api/seguimiento/metricas", "/api/seguimiento/tareas", "/api/estadisticas/seguimiento"})
# Match route shapes, including invalid parameter values handled as422. A
# canonical-ID-only matcher would miss those real private error responses.
_TASK = re.compile(r"/api/seguimiento/tareas/[^/]+(?:/(?:historial|completar|cancelar))?\Z")
_CANDIDATE = re.compile(r"/api/seguimiento/clientes/[^/]+/candidatos\Z")
_CLIENT_SHELL = re.compile(r"/clientes/[^/]+/seguimiento\Z")


def is_followup_private(path):
    candidate = path.removesuffix("/")
    return candidate in _STATIC or bool(_TASK.fullmatch(candidate) or _CANDIDATE.fullmatch(candidate) or _CLIENT_SHELL.fullmatch(candidate))

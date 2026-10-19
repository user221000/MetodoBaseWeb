"""Exact private route shapes for R25, independent of parameter validity."""
import re

_PATH=re.compile(r"(?:/api/usuario/progreso(?:/[^/]*)*|/api/usuario/vinculos/[^/]+/progreso/consentimiento(?:/retirar)?|/api/clientes/[^/]+/progreso|/api/clientes/[^/]+/vinculacion/[^/]+/progreso(?:/contexto)?)\Z")


def is_progress_private(path):
    return isinstance(path,str) and _PATH.fullmatch(path) is not None

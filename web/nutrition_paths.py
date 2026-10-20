"""Finite private profile/generation paths, including one slash alias."""
import re

_EXACT = frozenset({
    "/api/clientes",
    "/api/generar-plan",
    "/api/usuario/perfil",
    "/api/usuario/generar-plan",
})
_CLIENT = re.compile(r"/api/clientes/[^/]+\Z")


def is_nutrition_private(path: str) -> bool:
    """Match actual APIs without widening to prefixes, SSR or extra segments."""
    canonical = path.removesuffix("/")
    return canonical in _EXACT or _CLIENT.fullmatch(canonical) is not None

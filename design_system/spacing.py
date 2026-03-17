# -*- coding: utf-8 -*-
"""
Espaciado — Sistema 4px para márgenes, paddings y gaps.

Uso:
    from design_system.spacing import sp
    margin = sp("lg")   # 24
"""

SPACING: dict[str, int] = {
    "xs": 4,
    "sm": 8,
    "md": 12,
    "lg": 16,
    "xl": 24,
    "xl2": 32,
    "xl3": 40,
    "xl4": 48,
    "xl5": 64,
}

RADIUS: dict[str, int] = {
    "sm": 6,
    "md": 8,
    "lg": 12,
    "xl": 16,
    "xl2": 24,
    "full": 9999,
}


def sp(key: str) -> int:
    """Devuelve un valor de espaciado por clave."""
    return SPACING.get(key, 16)

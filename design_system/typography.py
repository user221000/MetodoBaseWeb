# -*- coding: utf-8 -*-
"""
Tipografía — Escala de tipos y fuentes para el tema Verde Premium.

Uso:
    from design_system.typography import font
    size = font("heading_1")  # 48
"""

TYPOGRAPHY: dict[str, dict] = {
    "display": {"size": 48, "weight": 800, "family": "Inter"},
    "heading_1": {"size": 32, "weight": 700, "family": "Inter"},
    "heading_2": {"size": 24, "weight": 700, "family": "Inter"},
    "heading_3": {"size": 20, "weight": 600, "family": "Inter"},
    "body_large": {"size": 16, "weight": 400, "family": "Inter"},
    "body": {"size": 14, "weight": 400, "family": "Inter"},
    "body_small": {"size": 13, "weight": 400, "family": "Inter"},
    "caption": {"size": 12, "weight": 500, "family": "Inter"},
    "overline": {"size": 11, "weight": 600, "family": "Inter"},
    "tiny": {"size": 10, "weight": 400, "family": "Inter"},
}


def font(key: str) -> dict:
    """Devuelve datos de tipografía por clave."""
    return TYPOGRAPHY.get(key, TYPOGRAPHY["body"])

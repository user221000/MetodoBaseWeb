# -*- coding: utf-8 -*-
"""
Paleta de colores — Método Base v2.0
Bases: Verde oscuro profundo + Amarillo dorado + Acentos cyan

Uso:
    from design_system.colors import color
    bg = color("bg_primary")           # "#0a1409"
    acento = color("amarillo_primary")  # "#ffd700"
"""

THEME_METODO_BASE: dict[str, str] = {
    # === BACKGROUNDS ===
    "bg_primary": "#0a1409",       # Verde oscuro casi negro (fondo principal)
    "bg_secondary": "#1a2419",    # Verde oscuro (sidebar, cards)
    "bg_card": "#1e2e1d",         # Cards elevadas
    "bg_input": "#1a2419",        # Inputs y fields
    "bg_hover": "#243324",        # Hover states

    # === SIDEBAR ===
    "sidebar_bg": "#1a2419",
    "sidebar_nav_active": "#1f4520",
    "sidebar_nav_hover": "#243324",
    "sidebar_border": "#2a4a2a",

    # === AMARILLO DORADO (Color principal de acento) ===
    "amarillo_primary": "#ffd700",    # Dorado brillante
    "amarillo_hover": "#ffed4e",      # Dorado más claro hover
    "amarillo_pressed": "#e6c200",   # Dorado oscuro pressed
    "amarillo_disabled": "#665500",  # Dorado desaturado

    # Alias para compatibilidad con código existente
    "accent_gold_primary": "#ffd700",
    "accent_gold_dark": "#d4af37",
    "accent_gold_soft": "#ffed4e",

    # === VERDE NEÓN (Solo acentos secundarios pequeños) ===
    "verde_neon": "#39ff14",        # Verde neón brillante
    "verde_neon_soft": "#4ade80",   # Verde neón suave

    # Alias para compatibilidad
    "accent_green_primary": "#39ff14",
    "accent_green_medium": "#00e676",
    "accent_green_soft": "#4caf50",

    # === CYAN/AZUL (Iconos usuario regular) ===
    "cyan_primary": "#22d3ee",     # Cyan brillante
    "cyan_dark": "#0891b2",        # Cyan oscuro
    "cyan_hover": "#06b6d4",       # Cyan hover

    # === BORDERS ===
    "border_default": "#2a4a2a",   # Verde oscuro (default)
    "border_amarillo": "#ffd700",  # Dorado (premium/GYM)
    "border_cyan": "#22d3ee",      # Cyan (usuario regular)
    "border_focus": "#ffed4e",     # Focus state
    "border_premium": "#ffd700",   # Alias compatibilidad
    "border_card": "#1e2e1d",

    # === TEXTO ===
    "text_primary": "#f0f0f0",      # Blanco principal
    "text_secondary": "#a8b5a8",   # Gris verdoso
    "text_muted": "#6b7b6b",       # Verde grisáceo oscuro
    "text_disabled": "#4a5f4a",    # Muy oscuro
    "text_amarillo": "#ffd700",    # Texto dorado énfasis

    # Alias compatibilidad
    "text_secondary_alias": "#a5d6a7",

    # === BADGES Y TAGS ===
    "badge_premium_bg": "#ffd700",
    "badge_premium_text": "#0a1409",

    # === TAGS OBJETIVO ===
    "tag_deficit_bg": "#1a2c3a",
    "tag_deficit_text": "#3b82f6",
    "tag_mantenimiento_bg": "#3a2f1a",
    "tag_mantenimiento_text": "#f59e0b",
    "tag_superavit_bg": "#2a1a3a",
    "tag_superavit_text": "#a855f7",

    # === KPI CARDS ===
    "kpi_purple": "#7e57c2",
    "kpi_blue": "#42a5f5",
    "kpi_orange": "#ff7043",
    "kpi_cyan": "#26c6da",

    # === ESTADOS ===
    "success": "#10b981",
    "warning": "#f59e0b",
    "error": "#ef4444",
    "info": "#3b82f6",

    # === WHATSAPP (color oficial — NO modificar) ===
    "whatsapp_bg": "#25d366",
    "whatsapp_hover": "#1fb858",
    "whatsapp_pressed": "#128c41",

    # === SUSCRIPCIONES ===
    "sub_active": "#10b981",
    "sub_expired": "#ef4444",
    "sub_pending": "#f59e0b",
}

# Alias para nombre anterior
THEME_VERDE_PREMIUM = THEME_METODO_BASE


def color(key: str, fallback: str = "#ffffff") -> str:
    """Devuelve un color del tema por su clave."""
    return THEME_METODO_BASE.get(key, fallback)

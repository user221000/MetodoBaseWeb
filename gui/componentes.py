# -*- coding: utf-8 -*-
"""
Componentes GUI reutilizables para Método Base.

Centraliza widgets y helpers visuales compartidos por múltiples ventanas,
evitando duplicación de código entre app_gui, ventana_admin, ventana_reportes, etc.
"""
from __future__ import annotations

import customtkinter as ctk
from typing import Callable, Optional


# ─── Paleta por defecto (override-able) ───────────────────────────────
_DEFAULTS = {
    "COLOR_BG":         "#0D0D0D",
    "COLOR_CARD":       "#1A1A1A",
    "COLOR_PRIMARY":    "#9B4FB0",
    "COLOR_TEXT":       "#F5F5F5",
    "COLOR_TEXT_MUTED": "#B8B8B8",
    "COLOR_BORDER":     "#444444",
    "COLOR_INPUT_BG":   "#2A2A2A",
    "COLOR_ERROR":      "#F44336",
    "COLOR_SUCCESS":    "#4CAF50",
    "COLOR_SECONDARY":  "#D4A84B",
    "FONT_FAMILY":      "Segoe UI",
}


def _c(key: str, overrides: dict | None = None) -> str:
    if overrides and key in overrides:
        return overrides[key]
    return _DEFAULTS[key]


# ─── Sección con header ──────────────────────────────────────────────

def crear_seccion(parent, titulo: str, icono: str = "", **kw) -> ctk.CTkFrame:
    """Crea una sección card con título e ícono, devuelve el frame de contenido."""
    card = ctk.CTkFrame(
        parent,
        fg_color=_c("COLOR_CARD", kw),
        corner_radius=12,
        border_width=1,
        border_color=_c("COLOR_BORDER", kw),
    )
    card.pack(fill="x", padx=kw.get("padx", 40), pady=kw.get("pady", 8))

    header = ctk.CTkFrame(card, fg_color="transparent")
    header.pack(fill="x", padx=16, pady=(14, 8))

    if icono:
        ctk.CTkLabel(
            header, text=icono,
            font=ctk.CTkFont(family=_c("FONT_FAMILY", kw), size=14),
            text_color=_c("COLOR_PRIMARY", kw), anchor="w",
        ).pack(side="left", padx=(0, 8))

    ctk.CTkLabel(
        header, text=titulo,
        font=ctk.CTkFont(family=_c("FONT_FAMILY", kw), size=14, weight="bold"),
        text_color=_c("COLOR_SECONDARY", kw), anchor="w",
    ).pack(side="left")

    content = ctk.CTkFrame(card, fg_color="transparent")
    content.pack(fill="x", padx=8, pady=(0, 12))
    for i in range(4):
        content.grid_columnconfigure(i, weight=1)

    return content


# ─── KPI card ─────────────────────────────────────────────────────────

def crear_kpi_card(
    parent,
    row: int,
    col: int,
    icono: str,
    label: str,
    valor: str,
    **kw,
) -> ctk.CTkFrame:
    """Crea un widget KPI reutilizable en un grid."""
    card = ctk.CTkFrame(
        parent,
        fg_color=_c("COLOR_CARD", kw),
        corner_radius=10,
        border_width=1,
        border_color=kw.get("border_color", "#2A2A2A"),
    )
    card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

    ctk.CTkLabel(card, text=icono, font=ctk.CTkFont(size=32)).pack(pady=(20, 5))
    ctk.CTkLabel(
        card, text=valor,
        font=ctk.CTkFont(size=28, weight="bold"),
        text_color=_c("COLOR_PRIMARY", kw),
    ).pack(pady=(0, 5))
    ctk.CTkLabel(
        card, text=label,
        font=ctk.CTkFont(size=11),
        text_color=_c("COLOR_TEXT_MUTED", kw),
    ).pack(pady=(0, 20))
    return card


# ─── Input con label y error ─────────────────────────────────────────

def crear_input_con_label(
    parent,
    label_text: str,
    placeholder: str = "",
    row: int = 0,
    colspan: int = 4,
    col: int = 0,
    **kw,
) -> tuple[ctk.CTkEntry, ctk.CTkLabel]:
    """Crea un campo de entrada con label y label de error, devuelve (entry, lbl_error)."""
    base_row = row * 3

    ctk.CTkLabel(
        parent, text=label_text,
        font=ctk.CTkFont(family=_c("FONT_FAMILY", kw), size=12),
        text_color=_c("COLOR_TEXT", kw), anchor="w",
    ).grid(row=base_row, column=col, columnspan=colspan, padx=(16, 4), pady=(8, 2), sticky="w")

    entry = ctk.CTkEntry(
        parent,
        placeholder_text=placeholder,
        height=38,
        corner_radius=8,
        border_width=1,
        border_color=_c("COLOR_BORDER", kw),
        fg_color=_c("COLOR_INPUT_BG", kw),
        font=ctk.CTkFont(family=_c("FONT_FAMILY", kw), size=13),
        placeholder_text_color=_c("COLOR_TEXT_MUTED", kw),
    )
    entry.grid(row=base_row + 1, column=col, columnspan=colspan, padx=16, pady=(0, 2), sticky="ew")

    lbl_error = ctk.CTkLabel(
        parent, text="", anchor="w",
        font=ctk.CTkFont(family=_c("FONT_FAMILY", kw), size=10),
        text_color=_c("COLOR_ERROR", kw),
        wraplength=580, justify="left",
    )
    lbl_error.grid(row=base_row + 2, column=col, columnspan=colspan, padx=20, pady=(0, 6), sticky="w")

    return entry, lbl_error


# ─── Botón de acción con estilo ──────────────────────────────────────

def crear_boton(
    parent,
    texto: str,
    command: Callable,
    estilo: str = "primary",
    **kw,
) -> ctk.CTkButton:
    """Crea un botón con estilo predefinido: primary, success, danger, ghost."""
    estilos = {
        "primary": {"fg_color": _c("COLOR_PRIMARY", kw), "hover_color": "#B565C6"},
        "success": {"fg_color": _c("COLOR_SUCCESS", kw), "hover_color": "#43A047"},
        "danger":  {"fg_color": _c("COLOR_ERROR", kw), "hover_color": "#D32F2F"},
        "ghost":   {
            "fg_color": "transparent",
            "hover_color": _c("COLOR_CARD", kw),
            "border_width": 1,
            "border_color": _c("COLOR_BORDER", kw),
            "text_color": _c("COLOR_TEXT_MUTED", kw),
        },
    }
    props = estilos.get(estilo, estilos["primary"])
    height = kw.pop("height", 36)
    return ctk.CTkButton(parent, text=texto, command=command, height=height, **props)


# ─── Card de lista con callback ──────────────────────────────────────

def crear_lista_items(
    parent_scroll: ctk.CTkScrollableFrame,
    items: list[str],
    on_select: Callable[[str], None],
    empty_msg: str = "Sin resultados",
    **kw,
) -> None:
    """Llena un scrollable-frame con botones seleccionables de una lista."""
    for widget in parent_scroll.winfo_children():
        widget.destroy()

    if not items:
        ctk.CTkLabel(
            parent_scroll,
            text=empty_msg,
            font=ctk.CTkFont(size=12),
            text_color=_c("COLOR_TEXT_MUTED", kw),
        ).pack(pady=20)
        return

    for item in items:
        ctk.CTkButton(
            parent_scroll,
            text=item.replace("_", " ").title(),
            command=lambda n=item: on_select(n),
            fg_color=_c("COLOR_BG", kw),
            hover_color=_c("COLOR_PRIMARY", kw),
            text_color=_c("COLOR_TEXT", kw),
            height=34,
        ).pack(fill="x", padx=10, pady=6)

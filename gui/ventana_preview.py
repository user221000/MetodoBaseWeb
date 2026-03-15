# -*- coding: utf-8 -*-
"""Ventana modal de preview del plan nutricional antes de exportar."""
from typing import Callable

import customtkinter as ctk

from utils.helpers import activar_modal_seguro


class PlanPreviewWindow(ctk.CTkToplevel):
    """
    Ventana modal para revisar el plan antes de exportarlo.
    Pensada para operación rápida de staff en piso de gimnasio.
    """

    COMIDAS_ORDEN = ["desayuno", "almuerzo", "comida", "cena"]
    COMIDAS_LABEL = {
        "desayuno": "Desayuno",
        "almuerzo": "Almuerzo",
        "comida": "Comida",
        "cena": "Cena",
    }

    COLOR_BG = "#0D0D0D"
    COLOR_CARD = "#1A1A1A"
    COLOR_CARD_SOFT = "#232323"
    COLOR_BORDER = "#444444"
    COLOR_PRIMARY = "#9B4FB0"
    COLOR_PRIMARY_HOVER = "#B565C6"
    COLOR_SECONDARY = "#D4A84B"
    COLOR_TEXT = "#F5F5F5"
    COLOR_TEXT_MUTED = "#B8B8B8"
    COLOR_SUCCESS = "#4CAF50"

    def __init__(self, parent, cliente, plan: dict, on_confirm: Callable, on_cancel: Callable):
        super().__init__(parent)
        self.title("Preview del Plan")
        self.geometry("760x830")
        self.resizable(False, True)
        self.configure(fg_color=self.COLOR_BG)
        activar_modal_seguro(self, parent)

        self._on_confirm = on_confirm
        self._on_cancel = on_cancel

        self._build_header(cliente)

        scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=self.COLOR_PRIMARY,
            scrollbar_button_hover_color=self.COLOR_PRIMARY_HOVER,
        )
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 8))
        self._renderizar_preview(scroll, cliente, plan)

        self._build_footer()
        self.protocol("WM_DELETE_WINDOW", self._cancelar)

    def _build_header(self, cliente) -> None:
        ctk.CTkLabel(
            self,
            text="Paso 2 de 3 · Preview del plan",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=self.COLOR_PRIMARY,
        ).pack(pady=(16, 4))

        ctk.CTkLabel(
            self,
            text=f"Cliente: {cliente.nombre}",
            font=ctk.CTkFont(family="Segoe UI", size=21, weight="bold"),
            text_color=self.COLOR_TEXT,
        ).pack(pady=(0, 2))

        obj = getattr(cliente, "objetivo", "").upper()
        kcal = getattr(cliente, "kcal_objetivo", 0)
        ctk.CTkLabel(
            self,
            text=f"Meta: {obj}  |  Kcal objetivo del día: {kcal:.0f}",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=self.COLOR_SECONDARY,
        ).pack(pady=(0, 10))

    def _build_footer(self) -> None:
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(4, 16))
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            btn_frame,
            text="Confirmar y Exportar",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color=self.COLOR_PRIMARY,
            hover_color=self.COLOR_PRIMARY_HOVER,
            text_color="#FFFFFF",
            height=42,
            corner_radius=10,
            command=self._confirmar,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            btn_frame,
            text="Volver a Captura",
            font=ctk.CTkFont(family="Segoe UI", size=14),
            fg_color="transparent",
            hover_color="#2A2A2A",
            border_width=1,
            border_color=self.COLOR_BORDER,
            text_color=self.COLOR_TEXT_MUTED,
            height=42,
            corner_radius=10,
            command=self._cancelar,
        ).grid(row=0, column=1, sticky="ew", padx=(8, 0))

    def _renderizar_preview(self, parent, _cliente, plan: dict) -> None:
        kcal_total = 0.0
        prot_total = 0.0
        carb_total = 0.0
        grasa_total = 0.0

        for clave in self.COMIDAS_ORDEN:
            if clave not in plan:
                continue

            comida = plan[clave]
            label = self.COMIDAS_LABEL.get(clave, clave.capitalize())
            kcal_comida = comida.get("kcal_real", comida.get("kcal_objetivo", 0))
            p = comida.get("proteinas_g", 0)
            c = comida.get("carbohidratos_g", 0)
            g = comida.get("grasas_g", 0)

            kcal_total += kcal_comida
            prot_total += p
            carb_total += c
            grasa_total += g

            card = ctk.CTkFrame(
                parent,
                fg_color=self.COLOR_CARD,
                corner_radius=10,
                border_width=1,
                border_color=self.COLOR_BORDER,
            )
            card.pack(fill="x", pady=6)

            ctk.CTkLabel(
                card,
                text=f"{label}",
                font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                text_color=self.COLOR_TEXT,
                anchor="w",
            ).pack(padx=14, pady=(10, 2), anchor="w")

            ctk.CTkLabel(
                card,
                text="Resumen nutricional de la comida",
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=self.COLOR_TEXT_MUTED,
                anchor="w",
            ).pack(padx=14, pady=(0, 8), anchor="w")

            metrics = ctk.CTkFrame(card, fg_color="transparent")
            metrics.pack(fill="x", padx=12, pady=(0, 8))
            metrics.grid_columnconfigure((0, 1, 2, 3), weight=1)

            self._metric_card(metrics, 0, "Kcal", f"{kcal_comida:.0f}", self.COLOR_SECONDARY)
            self._metric_card(metrics, 1, "Proteína", f"{p:.0f} g", self.COLOR_SUCCESS)
            self._metric_card(metrics, 2, "Carbohidrato", f"{c:.0f} g", "#42A5F5")
            self._metric_card(metrics, 3, "Grasas", f"{g:.0f} g", "#FFA726")

            ctk.CTkFrame(card, height=1, fg_color="#333333").pack(fill="x", padx=14, pady=(0, 6))

            alimentos = comida.get("alimentos", {})
            ctk.CTkLabel(
                card,
                text="Guía de porciones",
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                text_color=self.COLOR_TEXT_MUTED,
                anchor="w",
            ).pack(padx=14, pady=(0, 4), anchor="w")

            for alimento, gramos in alimentos.items():
                nombre_fmt = alimento.replace("_", " ").title()
                row = ctk.CTkFrame(card, fg_color="transparent")
                row.pack(fill="x", padx=14, pady=1)

                ctk.CTkLabel(
                    row,
                    text=f"• {nombre_fmt}",
                    font=ctk.CTkFont(family="Segoe UI", size=11),
                    text_color="#D0D0D0",
                    anchor="w",
                ).pack(side="left")

                equiv = self._equivalencia(alimento, gramos)
                ctk.CTkLabel(
                    row,
                    text=f"{gramos:.0f} g{equiv}",
                    font=ctk.CTkFont(family="Segoe UI", size=11),
                    text_color=self.COLOR_TEXT_MUTED,
                    anchor="e",
                ).pack(side="right")

            ctk.CTkLabel(
                card,
                text=f"Macros de esta comida: P {p:.0f} g | C {c:.0f} g | G {g:.0f} g",
                font=ctk.CTkFont(family="Segoe UI", size=10),
                text_color="#7E7E7E",
                anchor="w",
            ).pack(padx=14, pady=(6, 10), anchor="w")

        total_card = ctk.CTkFrame(
            parent,
            fg_color=self.COLOR_CARD_SOFT,
            corner_radius=10,
            border_width=1,
            border_color=self.COLOR_SECONDARY,
        )
        total_card.pack(fill="x", pady=(10, 8))
        total_card.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkLabel(
            total_card,
            text="Resumen del día",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=self.COLOR_TEXT,
        ).grid(row=0, column=0, columnspan=4, pady=(10, 2))

        self._metric_card(total_card, 0, "Kcal totales", f"{kcal_total:.0f}", self.COLOR_SECONDARY, row=1)
        self._metric_card(total_card, 1, "Proteína", f"{prot_total:.0f} g", self.COLOR_SUCCESS, row=1)
        self._metric_card(total_card, 2, "Carbohidrato", f"{carb_total:.0f} g", "#42A5F5", row=1)
        self._metric_card(total_card, 3, "Grasas", f"{grasa_total:.0f} g", "#FFA726", row=1)

    def _metric_card(self, parent, col: int, title: str, value: str, accent: str, row: int = 0) -> None:
        frame = ctk.CTkFrame(
            parent,
            fg_color="#262626",
            corner_radius=8,
            border_width=1,
            border_color="#3A3A3A",
        )
        frame.grid(row=row, column=col, padx=4, pady=(0, 8), sticky="ew")

        ctk.CTkLabel(
            frame,
            text=title,
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=self.COLOR_TEXT_MUTED,
        ).pack(pady=(6, 0))

        ctk.CTkLabel(
            frame,
            text=value,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=accent,
        ).pack(pady=(0, 6))

    @staticmethod
    def _equivalencia(alimento: str, gramos: float) -> str:
        """Devuelve texto de equivalencia fácil de leer (entre paréntesis)."""
        if alimento == "huevo":
            n = int(round(gramos / 50))
            if n >= 1:
                return f"  ({n} huevo{'s' if n > 1 else ''})"
        elif alimento == "tortilla_maiz":
            n = int(round(gramos / 30))
            if n >= 1:
                return f"  ({n} tortilla{'s' if n > 1 else ''})"
        elif alimento in ("aguacate",):
            n = round(gramos / 150, 1)
            if n >= 0.5:
                return f"  ({n} aguacate{'s' if n > 1 else ''})"
        elif alimento in ("banana", "platano"):
            n = int(round(gramos / 100))
            if n >= 1:
                return f"  ({n} plátano{'s' if n > 1 else ''})"
        return ""

    def _confirmar(self) -> None:
        self.destroy()
        self._on_confirm()

    def _cancelar(self) -> None:
        self.destroy()
        self._on_cancel()

# -*- coding: utf-8 -*-
"""
Ventana de activacion de licencia por key.
"""

import customtkinter as ctk
from tkinter import messagebox

from core.licencia import GestorLicencias
from utils.helpers import activar_modal_seguro
from utils.telemetria import registrar_evento


class VentanaActivacionLicencia(ctk.CTkToplevel):
    """Modal que bloquea el acceso hasta activar licencia valida."""

    COLOR_BG = "#0D0D0D"
    COLOR_CARD = "#1A1A1A"
    COLOR_PRIMARY = "#9B4FB0"
    COLOR_TEXT = "#F5F5F5"
    COLOR_TEXT_MUTED = "#B8B8B8"
    COLOR_BORDER = "#444444"
    PLANES_COMERCIALES = {
        "semestral": {"label": "Plan Semestral (180 días)", "periodo_meses": 6},
        "anual": {"label": "Plan Anual (365 días)", "periodo_meses": 12},
    }

    def __init__(self, parent, gestor: GestorLicencias, nombre_gym: str) -> None:
        super().__init__(parent)
        self.gestor = gestor
        self.nombre_gym = nombre_gym.strip() or "MetodoBase"
        self.activada = False

        self.title("Activacion de licencia")
        self.geometry("620x500")
        self.resizable(False, False)
        self.configure(fg_color=self.COLOR_BG)
        self.protocol("WM_DELETE_WINDOW", self._cerrar_sin_activar)

        self._render()
        activar_modal_seguro(self, parent)

    def _render(self) -> None:
        card = ctk.CTkFrame(
            self,
            fg_color=self.COLOR_CARD,
            corner_radius=12,
            border_width=1,
            border_color=self.COLOR_BORDER,
        )
        card.pack(fill="both", expand=True, padx=22, pady=22)

        ctk.CTkLabel(
            card,
            text="Activacion de licencia",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=self.COLOR_PRIMARY,
        ).pack(pady=(20, 8))

        ctk.CTkLabel(
            card,
            text=(
                "Ingresa la key generada por proveedor y selecciona el periodo.\n"
                "Sin licencia valida no se puede abrir el sistema."
            ),
            font=ctk.CTkFont(size=12),
            text_color=self.COLOR_TEXT_MUTED,
        ).pack(pady=(0, 16))

        self._id_instalacion = self.gestor.obtener_id_instalacion()

        id_frame = ctk.CTkFrame(card, fg_color="transparent")
        id_frame.pack(fill="x", padx=20, pady=(0, 12))
        ctk.CTkLabel(
            id_frame,
            text="ID instalacion",
            text_color=self.COLOR_TEXT,
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w")
        self.entry_id = ctk.CTkEntry(id_frame, height=34, fg_color="#2A2A2A")
        self.entry_id.pack(fill="x", pady=(4, 0))
        self.entry_id.insert(0, self._id_instalacion)
        self.entry_id.configure(state="disabled")

        periodo_frame = ctk.CTkFrame(card, fg_color="transparent")
        periodo_frame.pack(fill="x", padx=20, pady=(0, 12))
        ctk.CTkLabel(
            periodo_frame,
            text="Plan comercial",
            text_color=self.COLOR_TEXT,
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w")
        labels_plan = [v["label"] for v in self.PLANES_COMERCIALES.values()]
        self.combo_periodo = ctk.CTkOptionMenu(
            periodo_frame,
            values=labels_plan,
            fg_color="#2A2A2A",
            button_color=self.COLOR_PRIMARY,
            button_hover_color=self.COLOR_PRIMARY,
            text_color=self.COLOR_TEXT,
        )
        self.combo_periodo.set(self.PLANES_COMERCIALES["semestral"]["label"])
        self.combo_periodo.pack(fill="x", pady=(4, 0))
        self.combo_periodo.configure(command=lambda _value: self._actualizar_ayuda_key())

        canal_frame = ctk.CTkFrame(card, fg_color="transparent")
        canal_frame.pack(fill="x", padx=20, pady=(0, 12))
        ctk.CTkLabel(
            canal_frame,
            text="Canal de venta (opcional)",
            text_color=self.COLOR_TEXT,
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w")
        self.entry_canal_venta = ctk.CTkEntry(
            canal_frame,
            height=34,
            fg_color="#2A2A2A",
            placeholder_text="Ej: WhatsApp, Distribuidor, Web",
        )
        self.entry_canal_venta.pack(fill="x", pady=(4, 0))

        key_frame = ctk.CTkFrame(card, fg_color="transparent")
        key_frame.pack(fill="x", padx=20, pady=(0, 12))
        ctk.CTkLabel(
            key_frame,
            text="Key de activacion",
            text_color=self.COLOR_TEXT,
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w")
        self.entry_key = ctk.CTkEntry(
            key_frame,
            height=38,
            fg_color="#2A2A2A",
            placeholder_text="Ej: MB06-XXXX-XXXX-XXXX-XXXX",
        )
        self.entry_key.pack(fill="x", pady=(4, 0))
        self.entry_key.bind("<KeyRelease>", lambda _e: self._actualizar_ayuda_key())
        self.entry_key.bind("<FocusIn>", lambda _e: self._actualizar_ayuda_key())

        self.lbl_estado_form = ctk.CTkLabel(
            key_frame,
            text="Ayuda: selecciona periodo y escribe la key completa.",
            text_color=self.COLOR_TEXT_MUTED,
            font=ctk.CTkFont(size=10),
            anchor="w",
            justify="left",
            wraplength=560,
        )
        self.lbl_estado_form.pack(fill="x", pady=(6, 0))

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.pack(fill="x", padx=20, pady=(12, 16))
        btns.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(
            btns,
            text="Copiar ID",
            command=self._copiar_id,
            fg_color="transparent",
            border_width=1,
            border_color=self.COLOR_BORDER,
            hover_color="#2A2A2A",
        ).grid(row=0, column=0, padx=(0, 8), sticky="ew")

        ctk.CTkButton(
            btns,
            text="Activar",
            command=self._activar,
            fg_color=self.COLOR_PRIMARY,
            hover_color="#B565C6",
        ).grid(row=0, column=1, padx=8, sticky="ew")

        ctk.CTkButton(
            btns,
            text="Salir",
            command=self._cerrar_sin_activar,
            fg_color="#3A3A3A",
            hover_color="#444444",
        ).grid(row=0, column=2, padx=(8, 0), sticky="ew")

    def _copiar_id(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self._id_instalacion)
        messagebox.showinfo("ID copiado", "ID de instalacion copiado al portapapeles.", parent=self)

    def _actualizar_ayuda_key(self) -> None:
        key = self.entry_key.get().strip()
        plan = self._obtener_plan_seleccionado()
        meses = int(self.PLANES_COMERCIALES[plan]["periodo_meses"])
        dias = 180 if plan == "semestral" else 365
        prefijo = f"MB{meses:02d}"
        if not key:
            self.lbl_estado_form.configure(
                text=(
                    f"Ayuda: activación para {dias} días ({meses} meses). "
                    f"La key debe corresponder al plan seleccionado ({prefijo}...)."
                ),
                text_color=self.COLOR_TEXT_MUTED,
            )
            return
        if len(key) < 10:
            self.lbl_estado_form.configure(
                text="Error: key incompleta. Revisa bloques y guiones.",
                text_color="#F44336",
            )
            return
        self.lbl_estado_form.configure(
            text="OK: formato capturado. Puedes activar.",
            text_color="#4CAF50",
        )

    def _obtener_plan_seleccionado(self) -> str:
        actual = self.combo_periodo.get().strip()
        for key, meta in self.PLANES_COMERCIALES.items():
            if actual == meta["label"]:
                return key
        return "semestral"

    def _activar(self) -> None:
        key = self.entry_key.get().strip()
        plan = self._obtener_plan_seleccionado()
        periodo = int(self.PLANES_COMERCIALES[plan]["periodo_meses"])
        canal_venta = self.entry_canal_venta.get().strip()

        ok, msg = self.gestor.activar_licencia_con_key(
            nombre_gym=self.nombre_gym,
            key_activacion=key,
            periodo_meses=periodo,
            plan_comercial=plan,
            canal_venta=canal_venta,
        )
        if not ok:
            self.lbl_estado_form.configure(text=f"Error: {msg}", text_color="#F44336")
            messagebox.showerror("Activacion fallida", msg, parent=self)
            registrar_evento("licencia", "activacion_fallida", {"plan": plan})
            return

        self.activada = True
        self.lbl_estado_form.configure(text=f"OK: {msg}", text_color="#4CAF50")
        registrar_evento("licencia", "activacion_exitosa", {"plan": plan, "periodo": periodo})
        messagebox.showinfo("Activacion correcta", msg, parent=self)
        self.destroy()

    def _cerrar_sin_activar(self) -> None:
        self.activada = False
        self.destroy()

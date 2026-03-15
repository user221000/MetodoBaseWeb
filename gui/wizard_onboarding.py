# -*- coding: utf-8 -*-
"""
Wizard de configuración inicial para primera instalación.

Se muestra cuando ``branding.get('nombre_gym')`` está vacío, antes de
cargar la ventana principal ``GymApp``.
"""

import customtkinter as ctk
from tkinter import messagebox, colorchooser

from core.branding import branding
from utils.helpers import activar_modal_seguro
from utils.logger import logger


class WizardOnboarding(ctk.CTkToplevel):
    """Ventana modal de 3 pasos para configurar el gym en primera instalación."""

    # ── Paleta WCAG (idéntica a GymApp) ───────────────────────────────
    COLOR_BG = "#0D0D0D"
    COLOR_CARD = "#1A1A1A"
    COLOR_PRIMARY = "#9B4FB0"
    COLOR_TEXT = "#F5F5F5"
    COLOR_TEXT_MUTED = "#B8B8B8"
    COLOR_BORDER = "#444444"
    COLOR_SUCCESS = "#4CAF50"
    COLOR_ERROR = "#F44336"

    TOTAL_PASOS = 3

    def __init__(self, master: ctk.CTk) -> None:
        super().__init__(master)

        self.title("Configuración inicial — Método Base")
        self.geometry("550x580")
        self.resizable(False, False)
        self.configure(fg_color=self.COLOR_BG)

        self.paso_actual = 1
        self._ux_campos: dict = {}
        self._campos_paso1: list = []
        self._campos_paso2: list = []

        # Datos recopilados
        self.datos: dict = {
            "nombre_gym": "",
            "tagline": "",
            "contacto.telefono": "",
            "contacto.whatsapp": "",
            "contacto.email": "",
            "colores.primario": "#9B4FB0",
            "colores.secundario": "#D4A84B",
            "contacto.direccion_linea1": "",
            "contacto.direccion_linea2": "",
            "contacto.direccion_linea3": "",
            "redes_sociales.instagram": "",
        }

        # ── Layout principal ──────────────────────────────────────────
        self._contenedor = ctk.CTkFrame(self, fg_color="transparent")
        self._contenedor.pack(fill="both", expand=True, padx=24, pady=16)

        # Título
        self._lbl_titulo = ctk.CTkLabel(
            self._contenedor, text="",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.COLOR_PRIMARY,
        )
        self._lbl_titulo.pack(pady=(0, 12))

        # Frame dinámico de contenido (se reemplaza cada paso)
        self._frame_paso = ctk.CTkFrame(self._contenedor, fg_color=self.COLOR_CARD, corner_radius=10)
        self._frame_paso.pack(fill="both", expand=True)

        # Barra de navegación inferior
        self._nav = ctk.CTkFrame(self._contenedor, fg_color="transparent")
        self._nav.pack(fill="x", pady=(12, 0))

        self.btn_anterior = ctk.CTkButton(
            self._nav, text="← Anterior", width=120,
            fg_color="transparent", border_width=1, border_color=self.COLOR_BORDER,
            text_color=self.COLOR_TEXT, hover_color="#2A2A2A",
            command=self._paso_anterior,
        )
        self.btn_anterior.pack(side="left")

        self.btn_siguiente = ctk.CTkButton(
            self._nav, text="Siguiente →", width=120,
            fg_color=self.COLOR_PRIMARY, hover_color="#B565C6",
            command=self._paso_siguiente,
        )
        self.btn_siguiente.pack(side="right")

        # Indicador de paso
        self._lbl_indicador = ctk.CTkLabel(
            self._nav, text="", font=ctk.CTkFont(size=11),
            text_color=self.COLOR_TEXT_MUTED,
        )
        self._lbl_indicador.pack(side="right", padx=12)

        # Interceptar cierre con X
        self.protocol("WM_DELETE_WINDOW", self._on_cerrar)
        activar_modal_seguro(self, master)

        # Mostrar paso 1
        self._mostrar_paso()

    # ------------------------------------------------------------------
    # Renderizado de pasos
    # ------------------------------------------------------------------

    def _limpiar_paso(self) -> None:
        for w in self._frame_paso.winfo_children():
            w.destroy()

    def _mostrar_paso(self) -> None:
        self._limpiar_paso()
        self._lbl_indicador.configure(text=f"Paso {self.paso_actual} de {self.TOTAL_PASOS}")

        if self.paso_actual == 1:
            self._render_paso1()
        elif self.paso_actual == 2:
            self._render_paso2()
        elif self.paso_actual == 3:
            self._render_paso3()

        # Visibilidad de botones
        self.btn_anterior.configure(state="normal" if self.paso_actual > 1 else "disabled")
        self.btn_siguiente.configure(
            text="Finalizar ✓" if self.paso_actual == self.TOTAL_PASOS else "Siguiente →"
        )

    # ── Paso 1: Datos del gym ─────────────────────────────────────────

    def _render_paso1(self) -> None:
        self._lbl_titulo.configure(text="1 · Datos del gimnasio")
        f = self._frame_paso

        ctk.CTkLabel(f, text="Nombre del gimnasio *",
                     text_color=self.COLOR_TEXT_MUTED,
                     font=ctk.CTkFont(size=12)).pack(anchor="w", padx=20, pady=(20, 4))
        self.entry_nombre_gym = ctk.CTkEntry(
            f, placeholder_text="Ej: Fitness Gym Real del Valle",
            fg_color="#2A2A2A", border_color=self.COLOR_BORDER,
            text_color=self.COLOR_TEXT, width=420,
        )
        self.entry_nombre_gym.pack(padx=20)
        self.entry_nombre_gym.insert(0, self.datos["nombre_gym"])
        lbl_estado_nombre = ctk.CTkLabel(
            f,
            text="",
            text_color=self.COLOR_TEXT_MUTED,
            font=ctk.CTkFont(size=10),
            anchor="w",
            justify="left",
            wraplength=500,
        )
        lbl_estado_nombre.pack(fill="x", padx=20, pady=(3, 0))
        self._registrar_campo_ux(
            self.entry_nombre_gym,
            lbl_estado_nombre,
            ayuda="Ejemplo: Fitness Gym Real del Valle",
            validador=self._validar_nombre_gym,
            opcional=False,
        )
        self._campos_paso1.append(self.entry_nombre_gym)

        ctk.CTkLabel(f, text="Slogan / tagline (opcional)",
                     text_color=self.COLOR_TEXT_MUTED,
                     font=ctk.CTkFont(size=12)).pack(anchor="w", padx=20, pady=(16, 4))
        self.entry_tagline = ctk.CTkEntry(
            f, placeholder_text="Ej: Tu salud es nuestra motivación",
            fg_color="#2A2A2A", border_color=self.COLOR_BORDER,
            text_color=self.COLOR_TEXT, width=420,
        )
        self.entry_tagline.pack(padx=20)
        self.entry_tagline.insert(0, self.datos["tagline"])
        lbl_estado_tagline = ctk.CTkLabel(
            f,
            text="",
            text_color=self.COLOR_TEXT_MUTED,
            font=ctk.CTkFont(size=10),
            anchor="w",
            justify="left",
            wraplength=500,
        )
        lbl_estado_tagline.pack(fill="x", padx=20, pady=(3, 0))
        self._registrar_campo_ux(
            self.entry_tagline,
            lbl_estado_tagline,
            ayuda="Opcional. Frase corta del gym.",
            validador=self._validar_texto_corto,
            opcional=True,
        )
        self._campos_paso1.append(self.entry_tagline)

    # ── Paso 2: Contacto ──────────────────────────────────────────────

    def _render_paso2(self) -> None:
        self._lbl_titulo.configure(text="2 · Información de contacto")
        f = self._frame_paso

        campos = [
            ("Instagram", "redes_sociales.instagram", "Ej: @fitnessgym_realdelvalle"),
            ("Teléfono / WhatsApp", "contacto.whatsapp", "Ej: 5213312345678"),
            ("Dirección - Calle y Número", "contacto.direccion_linea1", "Ej: C. Valle De San José 1329B"),
            ("Dirección - Colonia", "contacto.direccion_linea2", "Ej: Fracc. Real del Valle"),
            ("Dirección - Ciudad y CP", "contacto.direccion_linea3", "Ej: 45654 Tlajomulco, Jal."),
        ]
        self._entries_contacto: dict = {}
        validadores = {
            "redes_sociales.instagram": self._validar_instagram,
            "contacto.whatsapp": self._validar_telefono,
            "contacto.direccion_linea1": self._validar_texto_corto,
            "contacto.direccion_linea2": self._validar_texto_corto,
            "contacto.direccion_linea3": self._validar_texto_corto,
        }

        for label, key, placeholder in campos:
            ctk.CTkLabel(f, text=label, text_color=self.COLOR_TEXT_MUTED,
                         font=ctk.CTkFont(size=12)).pack(anchor="w", padx=20, pady=(6, 2))
            entry = ctk.CTkEntry(
                f, placeholder_text=placeholder,
                fg_color="#2A2A2A", border_color=self.COLOR_BORDER,
                text_color=self.COLOR_TEXT, width=420,
            )
            entry.pack(padx=20)
            entry.insert(0, self.datos.get(key, ""))
            self._entries_contacto[key] = entry
            lbl_estado = ctk.CTkLabel(
                f,
                text="",
                text_color=self.COLOR_TEXT_MUTED,
                font=ctk.CTkFont(size=10),
                anchor="w",
                justify="left",
                wraplength=500,
            )
            lbl_estado.pack(fill="x", padx=20, pady=(3, 0))
            self._registrar_campo_ux(
                entry,
                lbl_estado,
                ayuda=placeholder,
                validador=validadores.get(key, self._validar_texto_corto),
                opcional=True,
            )
            self._campos_paso2.append(entry)

    # ── Paso 3: Colores ───────────────────────────────────────────────

    def _render_paso3(self) -> None:
        self._lbl_titulo.configure(text="3 · Colores del gimnasio")
        f = self._frame_paso

        ctk.CTkLabel(f, text="Selecciona los colores principales de tu marca",
                     text_color=self.COLOR_TEXT_MUTED,
                     font=ctk.CTkFont(size=12)).pack(anchor="w", padx=20, pady=(20, 12))

        # Color primario
        row1 = ctk.CTkFrame(f, fg_color="transparent")
        row1.pack(fill="x", padx=20, pady=8)
        ctk.CTkLabel(row1, text="Primario:", text_color=self.COLOR_TEXT,
                     font=ctk.CTkFont(size=13), width=100).pack(side="left")
        self._preview_primario = ctk.CTkLabel(
            row1, text="  ", width=40, height=30, corner_radius=6,
            fg_color=self.datos["colores.primario"],
        )
        self._preview_primario.pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            row1, text="Elegir color", width=120,
            fg_color=self.COLOR_PRIMARY, hover_color="#B565C6",
            command=lambda: self._elegir_color("primario"),
        ).pack(side="left")

        # Color secundario
        row2 = ctk.CTkFrame(f, fg_color="transparent")
        row2.pack(fill="x", padx=20, pady=8)
        ctk.CTkLabel(row2, text="Secundario:", text_color=self.COLOR_TEXT,
                     font=ctk.CTkFont(size=13), width=100).pack(side="left")
        self._preview_secundario = ctk.CTkLabel(
            row2, text="  ", width=40, height=30, corner_radius=6,
            fg_color=self.datos["colores.secundario"],
        )
        self._preview_secundario.pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            row2, text="Elegir color", width=120,
            fg_color=self.COLOR_PRIMARY, hover_color="#B565C6",
            command=lambda: self._elegir_color("secundario"),
        ).pack(side="left")

    def _elegir_color(self, tipo: str) -> None:
        color_actual = self.datos[f"colores.{tipo}"]
        resultado = colorchooser.askcolor(color=color_actual, title=f"Color {tipo}")
        if resultado and resultado[1]:
            hex_color = resultado[1]
            self.datos[f"colores.{tipo}"] = hex_color
            preview = self._preview_primario if tipo == "primario" else self._preview_secundario
            preview.configure(fg_color=hex_color)

    # ------------------------------------------------------------------
    # Navegación
    # ------------------------------------------------------------------

    def _guardar_paso_actual(self) -> None:
        """Guarda los valores del paso actual antes de navegar."""
        if self.paso_actual == 1:
            self.datos["nombre_gym"] = self.entry_nombre_gym.get().strip()
            self.datos["tagline"] = self.entry_tagline.get().strip()
        elif self.paso_actual == 2:
            for key, entry in self._entries_contacto.items():
                self.datos[key] = entry.get().strip()

    def _paso_siguiente(self) -> None:
        self._guardar_paso_actual()

        if self.paso_actual == 1:
            if not self._validar_campos_paso(self._campos_paso1):
                messagebox.showwarning(
                    "Revisa los campos",
                    "Corrige los campos marcados en rojo para continuar.",
                    parent=self,
                )
                return
        if self.paso_actual == 2:
            if not self._validar_campos_paso(self._campos_paso2):
                messagebox.showwarning(
                    "Revisa los campos",
                    "Hay datos de contacto con formato invalido.",
                    parent=self,
                )
                return

        if self.paso_actual < self.TOTAL_PASOS:
            self.paso_actual += 1
            self._mostrar_paso()
        else:
            self._finalizar()

    def _paso_anterior(self) -> None:
        self._guardar_paso_actual()
        if self.paso_actual > 1:
            self.paso_actual -= 1
            self._mostrar_paso()

    # ------------------------------------------------------------------
    # Finalizar / cerrar
    # ------------------------------------------------------------------

    def _finalizar(self) -> None:
        """Persiste todos los datos recopilados en branding."""
        for key, valor in self.datos.items():
            if valor:
                branding.set(key, valor)
        branding.guardar()
        logger.info("[WIZARD] Configuración inicial completada: %s", self.datos.get("nombre_gym"))
        self.grab_release()
        self.destroy()

    def _on_cerrar(self) -> None:
        respuesta = messagebox.askokcancel(
            "Sin configurar",
            "Si no configuras el gym, los PDFs saldrán sin nombre. ¿Continuar sin configurar?",
            parent=self,
        )
        if respuesta:
            self.grab_release()
            self.destroy()

    # ------------------------------------------------------------------
    # UX y validaciones inline
    # ------------------------------------------------------------------

    def _registrar_campo_ux(self, entry, lbl_estado, ayuda: str, validador, opcional: bool) -> None:
        self._ux_campos[entry] = {
            "label": lbl_estado,
            "ayuda": ayuda,
            "validador": validador,
            "opcional": opcional,
        }
        entry.bind("<FocusIn>", lambda _e, e=entry: self._on_focus_campo(e))
        entry.bind("<FocusOut>", lambda _e, e=entry: self._validar_campo(e))
        entry.bind("<KeyRelease>", lambda _e, e=entry: self._validar_campo(e))
        self._aplicar_estado_campo(entry, "neutral", f"Ayuda: {ayuda}")

    def _on_focus_campo(self, entry) -> None:
        meta = self._ux_campos.get(entry)
        if not meta:
            return
        if not entry.get().strip():
            self._aplicar_estado_campo(entry, "focus", f"Ayuda: {meta['ayuda']}")

    def _aplicar_estado_campo(self, entry, estado: str, texto: str = "") -> None:
        meta = self._ux_campos.get(entry)
        if not meta:
            return
        lbl_estado = meta["label"]
        if estado == "focus":
            entry.configure(border_color=self.COLOR_PRIMARY)
            lbl_estado.configure(text=texto, text_color=self.COLOR_TEXT_MUTED)
        elif estado == "ok":
            entry.configure(border_color=self.COLOR_SUCCESS)
            lbl_estado.configure(text=texto or "OK: formato valido.", text_color=self.COLOR_SUCCESS)
        elif estado == "error":
            entry.configure(border_color=self.COLOR_ERROR)
            lbl_estado.configure(text=texto, text_color=self.COLOR_ERROR)
        else:
            entry.configure(border_color=self.COLOR_BORDER)
            lbl_estado.configure(text=texto, text_color=self.COLOR_TEXT_MUTED)

    def _validar_campo(self, entry) -> bool:
        meta = self._ux_campos.get(entry)
        if not meta:
            return True

        valor = entry.get().strip()
        if valor == "" and meta["opcional"]:
            self._aplicar_estado_campo(entry, "neutral", f"Opcional. {meta['ayuda']}")
            return True

        ok, msg = meta["validador"](valor)
        if ok:
            self._aplicar_estado_campo(entry, "ok")
            return True
        self._aplicar_estado_campo(entry, "error", f"Error: {msg}")
        return False

    def _validar_campos_paso(self, campos: list) -> bool:
        validos = [self._validar_campo(entry) for entry in campos]
        return all(validos)

    @staticmethod
    def _validar_nombre_gym(valor: str) -> tuple[bool, str]:
        if not valor:
            return False, "El nombre del gimnasio es obligatorio."
        if len(valor) < 3:
            return False, "Minimo 3 caracteres."
        return True, ""

    @staticmethod
    def _validar_texto_corto(valor: str) -> tuple[bool, str]:
        if not valor:
            return True, ""
        if len(valor) < 3:
            return False, "Muy corto (minimo 3 caracteres)."
        return True, ""

    @staticmethod
    def _validar_instagram(valor: str) -> tuple[bool, str]:
        if not valor:
            return True, ""
        if not valor.startswith("@"):
            return False, "Debe iniciar con @ (ejemplo: @tu_gym)."
        if len(valor) < 4:
            return False, "Usuario de Instagram muy corto."
        return True, ""

    @staticmethod
    def _validar_telefono(valor: str) -> tuple[bool, str]:
        if not valor:
            return True, ""
        limpio = valor.replace(" ", "")
        if not limpio.isdigit():
            return False, "Solo numeros, sin guiones ni letras."
        if len(limpio) < 10:
            return False, "Minimo 10 digitos."
        if len(limpio) > 15:
            return False, "Maximo 15 digitos."
        return True, ""

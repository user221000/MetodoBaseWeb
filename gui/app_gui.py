# -*- coding: utf-8 -*-
"""Interfaz gráfica CustomTkinter para Método Base."""
import os
import re
import threading
import webbrowser
import urllib.parse
from datetime import datetime

import customtkinter as ctk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageFilter, ImageEnhance

from utils.helpers import resource_path, abrir_carpeta_pdf
from config.constantes import (
    FACTORES_ACTIVIDAD, NIVELES_ACTIVIDAD, OBJETIVOS_VALIDOS, CARPETA_SALIDA,
    CARPETA_PLANES,
)
from config.plantillas_cliente import (
    PLANTILLAS_CLIENTE,
    PLANTILLAS_LABELS,
    PLANTILLAS_POR_LABEL,
)
from core.modelos import ClienteEvaluacion
from core.motor_nutricional import MotorNutricional
from core.generador_planes import ConstructorPlanNuevo
from core.exportador_salida import GeneradorPDFProfesional
from core.exportador_multi import ExportadorMultiformato


# ─────────────────────────────────────────────
# Validación de campos en tiempo real
# ─────────────────────────────────────────────

from gui.validadores import ValidadorCamposTiempoReal  # noqa: E402
from gui.widgets_progress import ProgressIndicator, StepFlowIndicator     # noqa: E402
from gui.ventana_preview import PlanPreviewWindow      # noqa: E402
from gui.widgets_toast import mostrar_toast            # noqa: E402
from core.branding import branding                     # noqa: E402
from src.gestor_bd import GestorBDClientes              # noqa: E402
from gui.ventana_admin import VentanaAdmin              # noqa: E402
from gui.ventana_clientes import VentanaClientes        # noqa: E402
from utils.logger import logger                         # noqa: E402



class GymApp(ctk.CTk):
    """Aplicacion principal con CustomTkinter - Diseño profesional moderno."""

    # ── Paleta de colores WCAG 2.1 AA ──────────────────────────────────
    # Todos los pares texto/fondo cumplen ratio mínimo 4.5:1
    COLOR_BG           = "#0D0D0D"   # Fondo principal
    COLOR_CARD         = "#1A1A1A"   # Fondo de cards
    COLOR_PRIMARY      = "#9B4FB0"   # Morado — ratio 6.18:1 sobre BG ✅
    COLOR_PRIMARY_HOVER = "#B565C6"
    COLOR_SECONDARY    = "#D4A84B"
    COLOR_SECONDARY_HOVER = "#E4B85B"
    COLOR_BORDER       = "#444444"
    COLOR_TEXT         = "#F5F5F5"   # Blanco — ratio 19.77:1 sobre BG ✅
    COLOR_TEXT_MUTED   = "#B8B8B8"   # Gris — ratio 9.42:1 sobre BG  ✅
    COLOR_INPUT_BG     = "#2A2A2A"
    COLOR_SUCCESS      = "#4CAF50"   # Verde Material Design
    COLOR_SUCCESS_HOVER = "#43A047"
    COLOR_ERROR        = "#F44336"   # Rojo Material Design
    COLOR_WARNING      = "#FF9800"   # Naranja Material Design
    COLOR_INFO         = "#2196F3"   # Azul Material Design
    FONT_FAMILY        = "Segoe UI"
    SPACE_XS           = 4
    SPACE_SM           = 8
    SPACE_MD           = 12
    SPACE_LG           = 16
    SPACE_XL           = 20

    def __init__(self):
        super().__init__()

        # Branding configurable
        self.branding = branding
        self.COLOR_PRIMARY      = branding.get('colores.primario', self.COLOR_PRIMARY)
        self.COLOR_PRIMARY_HOVER = branding.get('colores.primario_hover', self.COLOR_PRIMARY_HOVER)
        self.COLOR_SECONDARY    = branding.get('colores.secundario', self.COLOR_SECONDARY)
        self.COLOR_SECONDARY_HOVER = branding.get('colores.secundario_hover', self.COLOR_SECONDARY_HOVER)

        self.title(f"{branding.get('nombre_corto')} - {branding.get('nombre_gym')}")
        self.geometry("820x900")
        self.resizable(False, False)
        self.configure(fg_color=self.COLOR_BG)
        ctk.set_appearance_mode("Dark")
        
        self.ultimo_pdf = None
        self.ultima_ruta_pdf = None

        # Inicializar gestor de BD
        try:
            self.gestor_bd = GestorBDClientes()
            logger.info("[APP] Gestor de BD inicializado")
        except Exception as e:
            logger.error("[APP] Error inicializando BD: %s", e)
            self.gestor_bd = None

        # Atajo para panel admin (Ctrl+Shift+A)
        self.bind("<Control-Shift-A>", self._abrir_panel_admin)

        # Contenedor principal con scroll
        self.main_container = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=self.COLOR_PRIMARY,
            scrollbar_button_hover_color=self.COLOR_PRIMARY_HOVER
        )
        self.main_container.pack(fill="both", expand=True, padx=0, pady=0)
        
        # ═══════════════ HEADER / BRANDING ═══════════════
        self.header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.header_frame.pack(fill="x", pady=(20, 4))
        
        self.title_container = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.title_container.pack()
        
        self._crear_header_watermark(self.title_container)
        
        self.lbl_titulo = ctk.CTkLabel(
            self.title_container,
            text=branding.get('nombre_corto', 'Metodo Base'),
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=40, weight="bold"),
            text_color=self.COLOR_TEXT
        )
        self.lbl_titulo.pack(pady=(0, self.SPACE_XS))

        self.lbl_subtitulo = ctk.CTkLabel(
            self.header_frame,
            text=branding.get('nombre_gym', 'Fitness Gym'),
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=15),
            text_color=self.COLOR_SECONDARY
        )
        self.lbl_subtitulo.pack(pady=(0, self.SPACE_XS))

        self.lbl_contexto = ctk.CTkLabel(
            self.header_frame,
            text=branding.get('tagline', 'Powered by C. H.'),
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=10),
            text_color=self.COLOR_TEXT_MUTED
        )
        self.lbl_contexto.pack(pady=(0, self.SPACE_MD))
        
        self.separator = ctk.CTkFrame(self.main_container, height=2, fg_color=self.COLOR_PRIMARY)
        self.separator.pack(fill="x", padx=60, pady=(0, self.SPACE_MD))

        # Flujo visual por pasos para staff
        self.step_flow = StepFlowIndicator(self.main_container)
        self.step_flow.pack(fill="x", padx=40, pady=(0, self.SPACE_SM))
        self.step_flow.set_step(0)

        # ═══════════════ SECCIÓN 1: DATOS DEL CLIENTE ═══════════════
        self.section_cliente = self._crear_seccion("Ficha del Cliente", "👤")
        
        self.entry_nombre, self.lbl_error_nombre = self._crear_input_full(
            self.section_cliente, "Nombre completo", "Ej: Oscar Hernández", row=0
        )

        self.entry_telefono, self.entry_edad, self.lbl_error_telefono, self.lbl_error_edad = self._crear_input_duo(
            self.section_cliente,
            "Teléfono", "Ej: 5213312345678",
            "Edad", "Ej: 25", row=1
        )

        # ═══════════════ SECCIÓN 2: MEDIDAS CORPORALES ═══════════════
        self.section_medidas = self._crear_seccion("Composición Corporal", "⚖")
        
        self.entry_peso, self.entry_estatura, self.lbl_error_peso, self.lbl_error_estatura = self._crear_input_duo(
            self.section_medidas,
            "Peso (kg)", "Ej: 80.5",
            "Estatura (cm)", "Ej: 175", row=0
        )

        self.entry_grasa, self.lbl_error_grasa = self._crear_input_full(
            self.section_medidas, "Grasa corporal (%)", "Ej: 18", row=1
        )

        # ═══════════════ SECCIÓN 3: PERFIL DE ENTRENAMIENTO ═══════════════
        self.section_perfil = self._crear_seccion("Contexto de Entrenamiento", "🏋")
        
        self.combo_actividad, self.combo_objetivo = self._crear_combo_duo(
            self.section_perfil,
            "Actividad", list(NIVELES_ACTIVIDAD), "moderada",
            "Objetivo", list(OBJETIVOS_VALIDOS), "mantenimiento", row=0
        )
        self.combo_objetivo.configure(state="disabled")

        self._crear_label_campo(
            self.section_perfil, "Plantilla de cliente", fila=2, col=0
        )
        self.combo_plantilla = ctk.CTkComboBox(
            self.section_perfil,
            values=PLANTILLAS_LABELS,
            height=38,
            corner_radius=8,
            border_width=1,
            border_color=self.COLOR_BORDER,
            button_color=self.COLOR_PRIMARY,
            button_hover_color=self.COLOR_PRIMARY_HOVER,
            dropdown_fg_color=self.COLOR_CARD,
            dropdown_hover_color=self.COLOR_PRIMARY,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            dropdown_font=ctk.CTkFont(family="Segoe UI", size=12),
            command=self._on_plantilla_change,
        )
        self.combo_plantilla.grid(
            row=3, column=0, columnspan=4, padx=16, pady=(0, 2), sticky="ew"
        )
        self.combo_plantilla.set(PLANTILLAS_LABELS[0])

        self.lbl_plantilla_contexto = ctk.CTkLabel(
            self.section_perfil,
            text="",
            anchor="w",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=self.COLOR_TEXT_MUTED,
            wraplength=580,
            justify="left",
        )
        self.lbl_plantilla_contexto.grid(
            row=4, column=0, columnspan=4, padx=20, pady=(0, 6), sticky="w"
        )
        self._on_plantilla_change(self.combo_plantilla.get())

        # ═══════════════ SECCIÓN 4: TIPO DE PLAN ═══════════════
        self.frame_tipo_plan = ctk.CTkFrame(
            self.main_container, fg_color=self.COLOR_CARD,
            corner_radius=12, border_width=1, border_color=self.COLOR_BORDER
        )
        self.frame_tipo_plan.pack(fill="x", padx=40, pady=8)

        self.frame_tipo_plan_inner = ctk.CTkFrame(self.frame_tipo_plan, fg_color="transparent")
        self.frame_tipo_plan_inner.pack(fill="x", padx=16, pady=12)

        self.lbl_tipo_plan = ctk.CTkLabel(
            self.frame_tipo_plan_inner,
            text="Formato de entrega:",
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=13, weight="bold"),
            text_color=self.COLOR_SECONDARY
        )
        self.lbl_tipo_plan.pack(side="left", padx=(0, 15))

        self.segmented_tipo_plan = ctk.CTkSegmentedButton(
            self.frame_tipo_plan_inner,
            values=["Menú Fijo", "Con Opciones"],
            command=self._cambiar_tipo_plan,
            font=ctk.CTkFont(size=12),
            fg_color=self.COLOR_INPUT_BG,
            selected_color=self.COLOR_PRIMARY,
            selected_hover_color=self.COLOR_PRIMARY_HOVER,
            unselected_color=self.COLOR_CARD,
            unselected_hover_color=self.COLOR_BORDER
        )
        self.segmented_tipo_plan.set("Menú Fijo")
        self.segmented_tipo_plan.pack(side="left", fill="x", expand=True)

        self.lbl_info_tipo = ctk.CTkLabel(
            self.frame_tipo_plan_inner,
            text="ℹ️",
            font=ctk.CTkFont(size=14),
            text_color=self.COLOR_TEXT_MUTED,
            cursor="hand2"
        )
        self.lbl_info_tipo.pack(side="left", padx=(10, 0))
        self.lbl_info_tipo.bind("<Button-1>", self._mostrar_info_tipo_plan)

        # ─── UX de formulario: estados + ayuda contextual + validacion ───
        self._validacion_campos = {}
        self._configurar_campo_validable(
            self.entry_nombre,
            self.lbl_error_nombre,
            ValidadorCamposTiempoReal.validar_nombre,
            ayuda="Captura nombre y apellido del cliente.",
        )
        self._configurar_campo_validable(
            self.entry_telefono,
            self.lbl_error_telefono,
            ValidadorCamposTiempoReal.validar_telefono,
            ayuda="Opcional. Solo números con lada. Ej: 5213312345678",
            opcional=True,
        )
        self._configurar_campo_validable(
            self.entry_edad,
            self.lbl_error_edad,
            ValidadorCamposTiempoReal.validar_edad,
            ayuda="Edad del cliente para ajustar su plan.",
        )
        self._configurar_campo_validable(
            self.entry_peso,
            self.lbl_error_peso,
            ValidadorCamposTiempoReal.validar_peso,
            ayuda="Peso actual en kg. Ej: 80.5",
        )
        self._configurar_campo_validable(
            self.entry_estatura,
            self.lbl_error_estatura,
            ValidadorCamposTiempoReal.validar_estatura,
            ayuda="Estatura en cm. Ej: 175",
        )
        self._configurar_campo_validable(
            self.entry_grasa,
            self.lbl_error_grasa,
            ValidadorCamposTiempoReal.validar_grasa,
            ayuda="Porcentaje estimado de grasa corporal.",
        )
        self.buttons_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.buttons_frame.pack(fill="x", padx=40, pady=(20, 12))
        
        self.btn_shadow = ctk.CTkFrame(
            self.buttons_frame, fg_color="#5a1e6a",
            corner_radius=12, height=68,
        )
        self.btn_shadow.pack(fill="x", pady=(0, 18), ipady=0)
        self.btn_shadow.pack_propagate(False)

        self.btn_procesar = ctk.CTkButton(
            self.btn_shadow, text="INICIAR FLUJO DE PLAN",
            command=self._on_procesar_click, height=60, corner_radius=12,
            font=ctk.CTkFont(family=self.FONT_FAMILY, size=18, weight="bold"),
            fg_color=self.COLOR_TEXT_MUTED, hover_color=self.COLOR_PRIMARY_HOVER,
            border_width=2, border_color=self.COLOR_PRIMARY_HOVER,
            text_color=self.COLOR_TEXT,
            state="disabled",
        )
        self.btn_procesar.pack(fill="x", padx=2, pady=2, ipady=2)
        
        self.secondary_buttons = ctk.CTkFrame(self.buttons_frame, fg_color="transparent")
        self.secondary_buttons.pack(fill="x")
        self.secondary_buttons.grid_columnconfigure(0, weight=1)
        self.secondary_buttons.grid_columnconfigure(1, weight=1)
        self.secondary_buttons.grid_columnconfigure(2, weight=1)  # Añadir tercera columna

        self.btn_whatsapp = ctk.CTkButton(
            self.secondary_buttons, text="Compartir por WhatsApp",
            command=self.enviar_por_whatsapp, state="disabled",
            height=36, corner_radius=6,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=self.COLOR_SUCCESS, hover_color=self.COLOR_SUCCESS_HOVER,
            border_width=1, border_color=self.COLOR_SUCCESS_HOVER,
            text_color=self.COLOR_TEXT
        )
        self.btn_whatsapp.grid(row=0, column=0, sticky="ew", padx=(0, 4), pady=0)

        self.btn_abrir_pdf = ctk.CTkButton(
            self.secondary_buttons, text="Abrir carpeta de PDF",
            command=abrir_carpeta_pdf, height=36, corner_radius=6,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="transparent", hover_color=self.COLOR_CARD,
            border_width=1, border_color=self.COLOR_BORDER,
            text_color=self.COLOR_TEXT_MUTED
        )
        self.btn_abrir_pdf.grid(row=0, column=1, sticky="ew", padx=(4, 4), pady=0)
        
        # Nuevo botón Mis Clientes
        self.btn_clientes = ctk.CTkButton(
            self.secondary_buttons, text="👥 Mis Clientes",
            command=self._abrir_clientes, height=36, corner_radius=6,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=self.COLOR_INFO, hover_color="#1976D2",
            border_width=1, border_color=self.COLOR_INFO,
            text_color="white"
        )
        self.btn_clientes.grid(row=0, column=2, sticky="ew", padx=(4, 0), pady=0)

        # ═══════════════ PROGRESO ═══════════════
        self.progress_indicator = ProgressIndicator(self.main_container)
        self.progress_indicator.pack(fill="x", padx=40, pady=(0, 8))
        self.progress_indicator.pack_forget()  # oculto hasta que se genere

        # ═══════════════ REGISTRO DE OPERACIONES ═══════════════
        self.log_frame = ctk.CTkFrame(
            self.main_container, fg_color=self.COLOR_CARD,
            corner_radius=10, border_width=1, border_color=self.COLOR_BORDER
        )
        self.log_frame.pack(fill="x", padx=40, pady=(16, 24))
        
        self.lbl_status = ctk.CTkLabel(
            self.log_frame, text="Bitácora del Staff", anchor="w",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=self.COLOR_TEXT_MUTED
        )
        self.lbl_status.pack(padx=16, pady=(12, 4), anchor="w")
        
        self.textbox_log = ctk.CTkTextbox(
            self.log_frame, height=100, corner_radius=6,
            fg_color=self.COLOR_INPUT_BG, border_width=0,
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=self.COLOR_TEXT_MUTED
        )
        self.textbox_log.pack(padx=12, pady=(0, 12), fill="x")
        
        self._log("Sistema listo. Captura la ficha del cliente para iniciar.")

    # ───── Helpers de creación de UI ─────

    def _crear_seccion(self, titulo, icono=""):
        card = ctk.CTkFrame(
            self.main_container, fg_color=self.COLOR_CARD,
            corner_radius=12, border_width=1, border_color=self.COLOR_BORDER
        )
        card.pack(fill="x", padx=40, pady=8)
        
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(14, 8))
        
        if icono:
            lbl_icono = ctk.CTkLabel(
                header, text=icono,
                font=ctk.CTkFont(family="Segoe UI", size=14),
                text_color=self.COLOR_PRIMARY, anchor="w"
            )
            lbl_icono.pack(side="left", padx=(0, 8))
        
        lbl_titulo = ctk.CTkLabel(
            header, text=titulo,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=self.COLOR_SECONDARY, anchor="w"
        )
        lbl_titulo.pack(side="left")
        
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=8, pady=(0, 12))
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=1)
        content.grid_columnconfigure(2, weight=1)
        content.grid_columnconfigure(3, weight=1)
        
        return content
    
    def _crear_label_campo(self, parent, texto, fila, col=0):
        label = ctk.CTkLabel(
            parent, text=texto,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=self.COLOR_TEXT, anchor="w"
        )
        label.grid(row=fila, column=col, columnspan=2, padx=(16, 4), pady=(8, 2), sticky="w")
        return label
    
    def _crear_input_full(self, parent, label_text, placeholder, row):
        base_row = row * 3
        self._crear_label_campo(parent, label_text, base_row, col=0)

        entry = ctk.CTkEntry(
            parent, placeholder_text=placeholder, height=38, corner_radius=8,
            border_width=1, border_color=self.COLOR_BORDER,
            fg_color=self.COLOR_INPUT_BG,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            placeholder_text_color=self.COLOR_TEXT_MUTED
        )
        entry.grid(row=base_row + 1, column=0, columnspan=4, padx=16, pady=(0, 2), sticky="ew")

        lbl_error = ctk.CTkLabel(
            parent, text="", anchor="w",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=self.COLOR_ERROR,
            wraplength=580,
            justify="left",
        )
        lbl_error.grid(row=base_row + 2, column=0, columnspan=4, padx=20, pady=(0, 6), sticky="w")

        return entry, lbl_error
    
    def _crear_input_duo(self, parent, label1, placeholder1, label2, placeholder2, row):
        base_row = row * 3

        lbl1 = ctk.CTkLabel(parent, text=label1, font=ctk.CTkFont(family="Segoe UI", size=12),
                           text_color=self.COLOR_TEXT, anchor="w")
        lbl1.grid(row=base_row, column=0, columnspan=2, padx=(16, 4), pady=(8, 2), sticky="w")

        lbl2 = ctk.CTkLabel(parent, text=label2, font=ctk.CTkFont(family="Segoe UI", size=12),
                           text_color=self.COLOR_TEXT, anchor="w")
        lbl2.grid(row=base_row, column=2, columnspan=2, padx=(16, 4), pady=(8, 2), sticky="w")

        entry1 = ctk.CTkEntry(
            parent, placeholder_text=placeholder1, height=38, corner_radius=8,
            border_width=1, border_color=self.COLOR_BORDER,
            fg_color=self.COLOR_INPUT_BG,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            placeholder_text_color=self.COLOR_TEXT_MUTED
        )
        entry1.grid(row=base_row + 1, column=0, columnspan=2, padx=(16, 8), pady=(0, 2), sticky="ew")

        entry2 = ctk.CTkEntry(
            parent, placeholder_text=placeholder2, height=38, corner_radius=8,
            border_width=1, border_color=self.COLOR_BORDER,
            fg_color=self.COLOR_INPUT_BG,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            placeholder_text_color=self.COLOR_TEXT_MUTED
        )
        entry2.grid(row=base_row + 1, column=2, columnspan=2, padx=(8, 16), pady=(0, 2), sticky="ew")

        lbl_error1 = ctk.CTkLabel(
            parent, text="", anchor="w",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=self.COLOR_ERROR,
            wraplength=250,
            justify="left",
        )
        lbl_error1.grid(row=base_row + 2, column=0, columnspan=2, padx=(20, 4), pady=(0, 6), sticky="w")

        lbl_error2 = ctk.CTkLabel(
            parent, text="", anchor="w",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=self.COLOR_ERROR,
            wraplength=250,
            justify="left",
        )
        lbl_error2.grid(row=base_row + 2, column=2, columnspan=2, padx=(20, 16), pady=(0, 6), sticky="w")

        return entry1, entry2, lbl_error1, lbl_error2
    
    def _crear_combo_duo(self, parent, label1, values1, default1, label2, values2, default2, row):
        base_row = row * 2
        
        lbl1 = ctk.CTkLabel(parent, text=label1, font=ctk.CTkFont(family="Segoe UI", size=12),
                           text_color=self.COLOR_TEXT, anchor="w")
        lbl1.grid(row=base_row, column=0, columnspan=2, padx=(16, 4), pady=(8, 2), sticky="w")
        
        lbl2 = ctk.CTkLabel(parent, text=label2, font=ctk.CTkFont(family="Segoe UI", size=12),
                           text_color=self.COLOR_TEXT, anchor="w")
        lbl2.grid(row=base_row, column=2, columnspan=2, padx=(16, 4), pady=(8, 2), sticky="w")
        
        combo1 = ctk.CTkComboBox(
            parent, values=values1, height=38, corner_radius=8,
            border_width=1, border_color=self.COLOR_BORDER,
            button_color=self.COLOR_PRIMARY, button_hover_color=self.COLOR_PRIMARY_HOVER,
            dropdown_fg_color=self.COLOR_CARD, dropdown_hover_color=self.COLOR_PRIMARY,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            dropdown_font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        combo1.grid(row=base_row + 1, column=0, columnspan=2, padx=(16, 8), pady=(0, 8), sticky="ew")
        combo1.set(default1)
        
        combo2 = ctk.CTkComboBox(
            parent, values=values2, height=38, corner_radius=8,
            border_width=1, border_color=self.COLOR_BORDER,
            button_color=self.COLOR_PRIMARY, button_hover_color=self.COLOR_PRIMARY_HOVER,
            dropdown_fg_color=self.COLOR_CARD, dropdown_hover_color=self.COLOR_PRIMARY,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            dropdown_font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        combo2.grid(row=base_row + 1, column=2, columnspan=2, padx=(8, 16), pady=(0, 8), sticky="ew")
        combo2.set(default2)
        
        return combo1, combo2

    def _crear_header_watermark(self, parent):
        try:
            logo_file = branding.obtener_logo_path()
            if not logo_file:
                return

            logo_img = Image.open(str(logo_file))
            watermark_size = 120
            logo_img = logo_img.resize((watermark_size, watermark_size), Image.Resampling.LANCZOS)
            logo_img = logo_img.filter(ImageFilter.GaussianBlur(radius=1.5))
            
            if logo_img.mode == 'RGBA':
                alpha = logo_img.split()[3]
                alpha = ImageEnhance.Brightness(alpha).enhance(0.07)
                logo_img.putalpha(alpha)
            else:
                logo_img = logo_img.convert('RGBA')
                alpha = logo_img.split()[3]
                alpha = ImageEnhance.Brightness(alpha).enhance(0.07)
                logo_img.putalpha(alpha)
            
            self.header_watermark_photo = ImageTk.PhotoImage(logo_img)
            
            from tkinter import Label
            self.header_watermark_label = Label(
                parent._canvas if hasattr(parent, '_canvas') else parent,
                image=self.header_watermark_photo,
                bg=self.COLOR_BG, borderwidth=0
            )
            self.header_watermark_label.place(relx=0.5, rely=0.5, anchor="center")
        except Exception:
            pass

    @staticmethod
    def _aclarar_hex(hex_color: str, factor: float = 0.16) -> str:
        valor = hex_color.strip().lstrip("#")
        r = int(valor[0:2], 16)
        g = int(valor[2:4], 16)
        b = int(valor[4:6], 16)
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return f"#{r:02X}{g:02X}{b:02X}"

    @staticmethod
    def _oscurecer_hex(hex_color: str, factor: float = 0.42) -> str:
        valor = hex_color.strip().lstrip("#")
        r = int(valor[0:2], 16)
        g = int(valor[2:4], 16)
        b = int(valor[4:6], 16)
        r = max(0, int(r * (1.0 - factor)))
        g = max(0, int(g * (1.0 - factor)))
        b = max(0, int(b * (1.0 - factor)))
        return f"#{r:02X}{g:02X}{b:02X}"

    @staticmethod
    def _reemplazar_color_en_valor(valor, mapeo: dict[str, str]):
        if isinstance(valor, str):
            key = valor.strip().lower()
            return mapeo.get(key, valor)
        if isinstance(valor, (tuple, list)):
            cambiado = False
            nuevo = []
            for item in valor:
                if isinstance(item, str):
                    repl = mapeo.get(item.strip().lower(), item)
                    cambiado = cambiado or repl != item
                    nuevo.append(repl)
                else:
                    nuevo.append(item)
            if cambiado:
                return tuple(nuevo)
        return valor

    def _aplicar_mapeo_colores(self, widget, mapeo: dict[str, str]):
        opciones = (
            "fg_color",
            "hover_color",
            "border_color",
            "text_color",
            "button_color",
            "button_hover_color",
            "dropdown_hover_color",
            "selected_color",
            "selected_hover_color",
            "segmented_button_selected_color",
            "segmented_button_selected_hover_color",
            "scrollbar_button_color",
            "scrollbar_button_hover_color",
            "progress_color",
        )
        cambios = {}
        for opcion in opciones:
            try:
                actual = widget.cget(opcion)
            except Exception:
                continue
            nuevo = self._reemplazar_color_en_valor(actual, mapeo)
            if nuevo != actual:
                cambios[opcion] = nuevo
        if cambios:
            try:
                widget.configure(**cambios)
            except Exception:
                pass
        for child in widget.winfo_children():
            self._aplicar_mapeo_colores(child, mapeo)

    def aplicar_branding_preview(
        self,
        *,
        primario: str,
        primario_hover: str | None = None,
        secundario: str,
        secundario_hover: str | None = None,
        nombre_corto: str | None = None,
        nombre_gym: str | None = None,
        tagline: str | None = None,
        tema: str | None = None,
    ) -> None:
        """Aplica branding visual sin reiniciar la app."""
        old_primary = self.COLOR_PRIMARY
        old_primary_hover = self.COLOR_PRIMARY_HOVER
        old_secondary = self.COLOR_SECONDARY
        old_secondary_hover = self.COLOR_SECONDARY_HOVER

        primario = (primario or old_primary).strip()
        secundario = (secundario or old_secondary).strip()
        primario_hover = (primario_hover or self._aclarar_hex(primario)).strip()
        secundario_hover = (secundario_hover or self._aclarar_hex(secundario)).strip()

        self.COLOR_PRIMARY = primario
        self.COLOR_PRIMARY_HOVER = primario_hover
        self.COLOR_SECONDARY = secundario
        self.COLOR_SECONDARY_HOVER = secundario_hover

        mapeo = {
            old_primary.lower(): primario,
            old_primary_hover.lower(): primario_hover,
            old_secondary.lower(): secundario,
            old_secondary_hover.lower(): secundario_hover,
        }
        self._aplicar_mapeo_colores(self, mapeo)

        if hasattr(self, "btn_shadow"):
            try:
                self.btn_shadow.configure(fg_color=self._oscurecer_hex(primario))
            except Exception:
                pass

        nombre_corto_final = (nombre_corto or branding.get("nombre_corto", "Metodo Base")).strip()
        nombre_gym_final = (nombre_gym or branding.get("nombre_gym", "Fitness Gym")).strip()
        tagline_final = (tagline or branding.get("tagline", "Powered by C. H.")).strip()

        self.title(f"{nombre_corto_final} - {nombre_gym_final}")
        if hasattr(self, "lbl_titulo"):
            self.lbl_titulo.configure(text=nombre_corto_final)
        if hasattr(self, "lbl_subtitulo"):
            self.lbl_subtitulo.configure(text=nombre_gym_final, text_color=self.COLOR_SECONDARY)
        if hasattr(self, "lbl_contexto"):
            self.lbl_contexto.configure(text=tagline_final)
        if hasattr(self, "separator"):
            self.separator.configure(fg_color=self.COLOR_PRIMARY)
        if hasattr(self, "progress_indicator"):
            try:
                self.progress_indicator.barra.configure(progress_color=self.COLOR_PRIMARY)
            except Exception:
                pass
            try:
                pct_text = self.progress_indicator.lbl_pct.cget("text")
                if pct_text != "100%":
                    self.progress_indicator.lbl_pct.configure(text_color=self.COLOR_PRIMARY)
            except Exception:
                pass

        self._actualizar_estado_boton_generar()
        if tema:
            self._log(f"Tema visual aplicado: {tema}")

    # ───── Lógica de negocio ─────

    def _configurar_campo_validable(
        self,
        entry,
        lbl_error,
        validador_fn,
        ayuda: str,
        opcional: bool = False,
    ):
        self._validacion_campos[entry] = {
            "label": lbl_error,
            "validador": validador_fn,
            "opcional": opcional,
            "ayuda": ayuda,
        }
        entry.bind("<KeyRelease>", lambda _e, e=entry: self._validar_campo(e))
        entry.bind("<FocusIn>", lambda _e, e=entry: self._on_focus_campo(e))
        entry.bind("<FocusOut>", lambda _e, e=entry: self._validar_campo(e))
        self._aplicar_estado_campo(entry, "neutral", ayuda)

    def _on_focus_campo(self, entry):
        meta = self._validacion_campos.get(entry)
        if not meta:
            return
        if not entry.get().strip():
            self._aplicar_estado_campo(entry, "focus", f"Ayuda: {meta['ayuda']}")

    def _aplicar_estado_campo(self, entry, estado: str, texto: str = ""):
        meta = self._validacion_campos.get(entry)
        if not meta:
            return
        lbl_error = meta["label"]
        if estado == "focus":
            entry.configure(border_color=self.COLOR_PRIMARY)
            lbl_error.configure(text=texto, text_color=self.COLOR_TEXT_MUTED)
        elif estado == "ok":
            entry.configure(border_color=self.COLOR_SUCCESS)
            lbl_error.configure(text=texto or "Dato correcto.", text_color=self.COLOR_SUCCESS)
        elif estado == "error":
            entry.configure(border_color=self.COLOR_ERROR)
            lbl_error.configure(text=texto, text_color=self.COLOR_ERROR)
        else:
            entry.configure(border_color=self.COLOR_BORDER)
            lbl_error.configure(text=texto, text_color=self.COLOR_TEXT_MUTED)

    def _validar_campo(self, entry):
        """Valida un campo segun su metadata de UX y actualiza su estado visual."""
        meta = self._validacion_campos.get(entry)
        if not meta:
            return

        valor = entry.get()
        ok, mensaje = meta["validador"](valor)
        if not valor.strip() and meta["opcional"]:
            self._aplicar_estado_campo(entry, "neutral", f"Opcional. {meta['ayuda']}")
        elif ok:
            self._aplicar_estado_campo(entry, "ok")
        else:
            self._aplicar_estado_campo(entry, "error", f"Error: {mensaje}.")

        self._actualizar_estado_boton_generar()

    def _actualizar_estado_boton_generar(self):
        """Habilita / deshabilita el botón de generar según validez del formulario."""
        todos_validos = all([
            ValidadorCamposTiempoReal.validar_nombre(self.entry_nombre.get())[0],
            ValidadorCamposTiempoReal.validar_edad(self.entry_edad.get())[0],
            ValidadorCamposTiempoReal.validar_peso(self.entry_peso.get())[0],
            ValidadorCamposTiempoReal.validar_estatura(self.entry_estatura.get())[0],
            ValidadorCamposTiempoReal.validar_grasa(self.entry_grasa.get())[0],
        ])
        if todos_validos:
            self.btn_procesar.configure(state="normal", fg_color=self.COLOR_PRIMARY)
        else:
            self.btn_procesar.configure(state="disabled", fg_color=self.COLOR_TEXT_MUTED)

    def _mostrar_toast(self, mensaje: str, tipo: str = "info", duracion: int = 3000):
        """Muestra una notificación toast en la esquina superior derecha."""
        mostrar_toast(self, mensaje, tipo=tipo, duracion=duracion)

    def _set_flujo_captura(self):
        self.step_flow.set_step(0)

    def _set_flujo_preview(self):
        self.step_flow.complete_step(0)
        self.step_flow.set_step(1)

    def _set_flujo_exportar(self):
        self.step_flow.complete_step(0)
        self.step_flow.complete_step(1)
        self.step_flow.set_step(2)

    def _complete_flujo(self):
        self.step_flow.complete_step(2)

    def _log(self, mensaje):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.textbox_log.insert("end", f"[{timestamp}] {mensaje}\n")
        self.textbox_log.see("end")

    def _cambiar_tipo_plan(self, value):
        """Handler para cambio de tipo de plan."""
        logger.info("[GUI] Tipo de plan cambiado a: %s", value)
        if value == "Con Opciones":
            self._mostrar_toast(
                "Se activó formato con opciones para dar alternativas al cliente.",
                tipo='info', duracion=4000,
            )

    def _set_objetivo_ui(self, objetivo: str):
        self.combo_objetivo.configure(state="normal")
        self.combo_objetivo.set(objetivo)
        self.combo_objetivo.configure(state="disabled")

    def _on_plantilla_change(self, plantilla_label: str):
        """Sincroniza objetivo nutricional y ayuda contextual según plantilla."""
        plantilla_key = PLANTILLAS_POR_LABEL.get(plantilla_label, "perdida_grasa")
        plantilla_data = PLANTILLAS_CLIENTE.get(
            plantilla_key, PLANTILLAS_CLIENTE["perdida_grasa"]
        )
        objetivo = plantilla_data["objetivo_motor"]
        actividad_sugerida = plantilla_data.get("actividad_sugerida")

        if actividad_sugerida in NIVELES_ACTIVIDAD:
            self.combo_actividad.set(actividad_sugerida)
        self._set_objetivo_ui(objetivo)
        self.lbl_plantilla_contexto.configure(
            text=(
                f"Plantilla activa: {plantilla_data['label']} | "
                f"Meta sugerida: {objetivo}. "
                f"Actividad sugerida: {actividad_sugerida or 'moderada'}. "
                f"{plantilla_data['descripcion']}"
            )
        )

    def _mostrar_info_tipo_plan(self, event=None):
        """Muestra información detallada sobre tipos de plan."""
        info = (
            "FORMATOS DE ENTREGA:\n\n"
            "MENÚ FIJO:\n"
            "• Entregas una guía concreta por comida\n"
            "• Ideal para clientes nuevos o con baja adherencia\n"
            "• Facilita el seguimiento semanal\n\n"
            "CON OPCIONES:\n"
            "• Das alternativas equivalentes por macronutriente\n"
            "• Útil para clientes con horarios variables\n"
            "• Mantiene el objetivo sin perder flexibilidad\n\n"
            "Ambos formatos mantienen el objetivo calórico del cliente."
        )
        messagebox.showinfo("Formatos de Plan", info)

    def _on_procesar_click(self):
        self.btn_procesar.configure(state="disabled")
        self._show_spinner_on_button()
        self.progress_indicator.reset()
        self.step_flow.reset()
        self._set_flujo_captura()
        self.progress_indicator.pack(fill="x", padx=40, pady=(0, 8),
                                     before=self.log_frame)
        thread = threading.Thread(target=self._procesar_datos, daemon=True)
        thread.start()

    def _procesar_datos(self):
        try:
            self._log("Iniciando flujo: captura -> preview -> exportar.")
            self.after(0, self._set_flujo_captura)
            self.after(0, lambda: self.progress_indicator.set_progress(0.05, "Revisando captura del cliente..."))

            nombre = self.entry_nombre.get().strip()
            if not nombre:
                raise ValueError("El nombre es obligatorio")
            telefono = self.entry_telefono.get().strip()
            if telefono:
                if not telefono.isdigit():
                    raise ValueError("Telefono invalido: solo numeros, sin espacios ni simbolos")
                if len(telefono) < 10:
                    raise ValueError("Telefono invalido: debe tener al menos 10 digitos")
            edad = int(self.entry_edad.get())
            if edad < 1:
                raise ValueError("Edad invalida: debe ser mayor a 0 anos")
            peso = float(self.entry_peso.get())
            if peso < 20:
                raise ValueError("Peso invalido: el peso minimo permitido es 20 kg")
            if peso > 155:
                raise ValueError("Peso invalido: el peso maximo permitido es 155 kg")
            estatura = float(self.entry_estatura.get())
            grasa = float(self.entry_grasa.get())
            if grasa < 5:
                raise ValueError("Grasa corporal invalida: el porcentaje minimo permitido es 5%")
            actividad = self.combo_actividad.get()
            plantilla_label = self.combo_plantilla.get()
            plantilla_tipo = PLANTILLAS_POR_LABEL.get(plantilla_label, "perdida_grasa")
            objetivo = PLANTILLAS_CLIENTE.get(
                plantilla_tipo, PLANTILLAS_CLIENTE["perdida_grasa"]
            )["objetivo_motor"]
            self.after(0, lambda: self._set_objetivo_ui(objetivo))

            # Determinar tipo de plan seleccionado
            tipo_plan = self.segmented_tipo_plan.get()
            tipo_plan_codigo = "con_opciones" if tipo_plan == "Con Opciones" else "menu_fijo"

            self.after(0, lambda: self.progress_indicator.set_progress(0.2, "Calculando objetivo calórico..."))

            # Buscar cliente existente por teléfono
            cliente_existente = None
            if self.gestor_bd and telefono:
                clientes = self.gestor_bd.buscar_clientes(telefono)
                if clientes:
                    cliente_existente = clientes[0]

            if cliente_existente:
                id_cliente = cliente_existente['id_cliente']
            else:
                id_cliente = None

            cliente = ClienteEvaluacion(
                nombre=nombre,
                telefono=telefono if telefono else None,
                edad=edad, peso_kg=peso, estatura_cm=estatura,
                grasa_corporal_pct=grasa, nivel_actividad=actividad,
                objetivo=objetivo
            )
            cliente.plantilla_tipo = plantilla_tipo
            if id_cliente:
                cliente.id_cliente = id_cliente
            cliente.factor_actividad = FACTORES_ACTIVIDAD.get(actividad, 1.2)
            self._log(
                f"Cliente creado: {cliente.nombre} "
                f"({cliente.objetivo}, plantilla {plantilla_label})"
            )

            cliente = MotorNutricional.calcular_motor(cliente)
            self._log(
                f"Objetivo diario calculado: {cliente.kcal_objetivo:.0f} kcal "
                f"(mantenimiento estimado: {cliente.get_total:.0f} kcal)."
            )
            self.after(0, lambda: self.progress_indicator.set_progress(0.45, "Armando comidas del plan..."))

            dir_planes = CARPETA_PLANES
            os.makedirs(dir_planes, exist_ok=True)

            if tipo_plan == "Con Opciones":
                # ── Modo opciones: generar plan con alternativas ──
                from core.generador_opciones import ConstructorPlanConOpciones
                from core.exportador_opciones import GeneradorPDFConOpciones

                self._log("Generando plan con OPCIONES...")

                plan = ConstructorPlanConOpciones.construir(
                    cliente, plan_numero=1,
                    directorio_planes=dir_planes,
                    num_opciones_por_macro=3,
                )
                self._log("Plan con opciones listo para revisión rápida.")
                self.after(0, self._set_flujo_preview)
                self.after(0, lambda: self.progress_indicator.set_progress(0.62, "Validando resumen previo para exportar..."))
                self.after(0, self._set_flujo_exportar)
                self.after(0, lambda: self.progress_indicator.set_progress(0.80, "Exportando archivos..."))

                if not os.path.exists(CARPETA_SALIDA):
                    os.makedirs(CARPETA_SALIDA)
                fecha = datetime.now().strftime("%Y-%m-%d")
                nombre_cliente_sanitizado = re.sub(r'[^a-zA-Z0-9_]', '', cliente.nombre.replace(" ", "_"))
                carpeta_cliente = os.path.join(CARPETA_SALIDA, nombre_cliente_sanitizado)
                os.makedirs(carpeta_cliente, exist_ok=True)
                hora = datetime.now().strftime("%H-%M-%S")
                nombre_pdf = f"{nombre_cliente_sanitizado}_OPCIONES_{fecha}_{hora}.pdf"
                ruta_pdf_completa = os.path.join(carpeta_cliente, nombre_pdf)

                generador = GeneradorPDFConOpciones(ruta_pdf_completa)
                ruta_pdf = generador.generar(cliente, plan)
                self.ultimo_pdf = ruta_pdf if ruta_pdf and os.path.exists(ruta_pdf) else None

                # Excel
                try:
                    nombre_excel = f"{nombre_cliente_sanitizado}_OPCIONES_{fecha}_{hora}.xlsx"
                    ruta_excel = os.path.join(carpeta_cliente, nombre_excel)
                    ExportadorMultiformato.a_excel(cliente, plan, ruta_excel)
                    self._log(f"Excel generado: {nombre_excel}")
                except Exception as exc:
                    self._log("No se pudo generar Excel: %s" % exc)

            else:
                # ── Modo fijo: flujo original completo ──
                self._log("Generando plan con menú FIJO...")

                plan = ConstructorPlanNuevo.construir(cliente, plan_numero=1, directorio_planes=dir_planes)
                self._log("Plan nutricional estructurado correctamente.")
                self.after(0, self._set_flujo_preview)
                self.after(0, lambda: self.progress_indicator.set_progress(0.65, "Mostrando preview para validación del staff..."))

                # ── Vista previa: bloquear hilo hasta confirmación ──
                confirm_event = threading.Event()
                self._preview_confirmed = False

                def on_confirm():
                    self._preview_confirmed = True
                    confirm_event.set()

                def on_cancel():
                    self._preview_confirmed = False
                    confirm_event.set()

                self.after(0, lambda: PlanPreviewWindow(self, cliente, plan, on_confirm, on_cancel))
                confirm_event.wait()

                if not self._preview_confirmed:
                    self._log("Generación cancelada por el usuario.")
                    self.after(0, self.step_flow.reset)
                    return

                self.after(0, self._set_flujo_exportar)
                self.after(0, lambda: self.progress_indicator.set_progress(0.80, "Exportando archivos..."))

                if not os.path.exists(CARPETA_SALIDA):
                    os.makedirs(CARPETA_SALIDA)
                fecha = datetime.now().strftime("%Y-%m-%d")
                nombre_cliente_sanitizado = re.sub(r'[^a-zA-Z0-9_]', '', cliente.nombre.replace(" ", "_"))
                carpeta_cliente = os.path.join(CARPETA_SALIDA, nombre_cliente_sanitizado)
                os.makedirs(carpeta_cliente, exist_ok=True)
                hora = datetime.now().strftime("%H-%M-%S")
                nombre_pdf = f"{nombre_cliente_sanitizado}_{fecha}_{hora}.pdf"
                ruta_pdf_completa = os.path.join(carpeta_cliente, nombre_pdf)

                generador = GeneradorPDFProfesional(ruta_pdf_completa)
                ruta_pdf = generador.generar(cliente, plan)
                self.ultimo_pdf = ruta_pdf if ruta_pdf and os.path.exists(ruta_pdf) else None

                # Excel
                try:
                    nombre_excel = f"{nombre_cliente_sanitizado}_{fecha}_{hora}.xlsx"
                    ruta_excel = os.path.join(carpeta_cliente, nombre_excel)
                    ExportadorMultiformato.a_excel(cliente, plan, ruta_excel)
                    self._log(f"Excel generado: {nombre_excel}")
                except Exception as exc:
                    self._log("No se pudo generar Excel: %s" % exc)

            self.after(0, lambda: self.btn_abrir_pdf.configure(state="normal" if self.ultimo_pdf else "disabled"))
            self.after(0, lambda: self.btn_whatsapp.configure(state="normal" if self.ultimo_pdf else "disabled"))
            self.after(0, self._complete_flujo)
            self.after(0, lambda: self.progress_indicator.complete("✓ Plan exportado y listo para entregar"))
            self.after(0, lambda: self._mostrar_toast("✓ Plan y archivos listos", tipo="success"))

            if self.ultimo_pdf:
                try:
                    abrir_carpeta_pdf(os.path.dirname(self.ultimo_pdf))
                    self._log("PDF abierto automaticamente.")
                except Exception as exc:
                    self._log("No se pudo abrir la carpeta del PDF: %s" % exc)

            # Estadísticas y registro en BD
            comidas = ['desayuno', 'almuerzo', 'comida', 'cena']
            if tipo_plan == "Con Opciones":
                kcal_total = sum(
                    plan.get(c, {}).get('kcal_objetivo', 0)
                    for c in comidas if c in plan
                )
                self._log(
                    f"PLAN OPCIONES — {nombre} | {objetivo.upper()} | "
                    f"Kcal obj: {cliente.kcal_objetivo:.0f} | "
                    f"Tipo: Con Opciones"
                )
            else:
                kcal_real = sum(plan[c].get('kcal_real', 0) for c in comidas if c in plan)
                desv_max = max(plan[c].get('desviacion_pct', 0) for c in comidas if c in plan)
                self._log(
                    f"PLAN GENERADO — {nombre} | {objetivo.upper()} | "
                    f"Kcal obj: {cliente.kcal_objetivo:.0f} | "
                    f"Kcal real: {kcal_real:.0f} | Desv. máx: {desv_max:.2f}%"
                )

            # Registrar cliente y plan en BD con manejo de errores
            if self.gestor_bd:
                try:
                    # a) Registrar o actualizar cliente
                    success_cliente = self.gestor_bd.registrar_cliente(cliente)
                    if success_cliente:
                        self._log("Cliente registrado en BD exitosamente")
                    else:
                        self._log("Advertencia: No se pudo registrar cliente en BD")
                    
                    # b) Registrar el plan generado
                    if self.ultimo_pdf:
                        success_plan = self.gestor_bd.registrar_plan_generado(
                            cliente,
                            plan,
                            self.ultimo_pdf,
                            tipo_plan=tipo_plan_codigo,
                        )
                        if success_plan:
                            self._log("Plan registrado en BD exitosamente")
                        else:
                            self._log("Advertencia: No se pudo registrar plan en BD")
                except Exception as e:
                    logger.warning("[BD] Error al guardar en BD: %s", e)
                    self._log(f"Advertencia BD: {e}")

            self._log(f"PDF: {ruta_pdf}")

        except ValueError as ve:
            self._log(f"Error de validacion: {ve}")
            self.after(0, self.step_flow.reset)
            self.after(0, lambda: self._mostrar_toast(f"⚠️ {ve}", tipo="warning", duracion=5000))
            self.after(0, lambda: messagebox.showerror(
                "Error de Validación", f"Revisa la ficha del cliente.\nDetalle: {ve}"))
        except Exception as e:
            self._log(f"ERROR: {str(e)}")
            self.after(0, self.step_flow.reset)
            self.after(0, lambda: self._mostrar_toast(f"❌ Error: {str(e)}", tipo="error", duracion=5000))
            self.after(0, lambda: messagebox.showerror("Error", f"Ocurrio un error:\n{str(e)}"))
            import traceback
            traceback.print_exc()
        finally:
            self.after(0, self._hide_spinner_on_button)
            self.after(0, lambda: self.btn_procesar.configure(state="normal", text="INICIAR FLUJO DE PLAN"))
            self.after(0, self._actualizar_estado_boton_generar)

    def _show_spinner_on_button(self):
        try:
            spinner_path = resource_path("assets/spinner_dark.gif")
            if not os.path.exists(spinner_path):
                self.btn_procesar.configure(text="Procesando flujo...", image=None)
                return
            self.spinner_img = Image.open(spinner_path)
            self.spinner_frames = []
            try:
                while True:
                    self.spinner_frames.append(ImageTk.PhotoImage(self.spinner_img.copy()))
                    self.spinner_img.seek(len(self.spinner_frames))
            except EOFError:
                pass
            self._spinner_frame = 0
            self._spinner_running = True
            self._animate_spinner()
        except Exception:
            self.btn_procesar.configure(text="Procesando flujo...", image=None)

    def _animate_spinner(self):
        if not getattr(self, '_spinner_running', False):
            return
        frame = self.spinner_frames[self._spinner_frame]
        self.btn_procesar.configure(text="Procesando flujo...", image=frame, compound="left")
        self._spinner_frame = (self._spinner_frame + 1) % len(self.spinner_frames)
        self.after(60, self._animate_spinner)

    def _hide_spinner_on_button(self):
        self._spinner_running = False
        self.btn_procesar.configure(text="INICIAR FLUJO DE PLAN", image=None)

    def _abrir_pdf(self):
        if self.ultimo_pdf and os.path.exists(self.ultimo_pdf):
            try:
                abrir_carpeta_pdf(os.path.dirname(self.ultimo_pdf))
            except Exception as exc:
                self._log("No se pudo abrir la carpeta del PDF: %s" % exc)
        else:
            messagebox.showwarning("Aviso", "No hay PDF disponible para abrir.")

    def abrir_carpeta_pdf_btn(self):
        abrir_carpeta_pdf()

    def enviar_por_whatsapp(self):
        if not self.ultimo_pdf or not os.path.exists(self.ultimo_pdf):
            messagebox.showerror("Error", "Primero debes generar el plan.")
            return
        telefono = self.entry_telefono.get().strip()
        if not telefono.isdigit():
            messagebox.showerror("Error", "Teléfono inválido.")
            return
        if not telefono.startswith("52"):
            messagebox.showerror("Error", "El número debe iniciar con 52 (México).")
            return
        nombre = self.entry_nombre.get().strip()

        nombre_gym = branding.get('nombre_gym', 'el gimnasio')
        telefono_gym = branding.get('contacto.telefono', '')
        mensaje = (
            f"Hola {nombre} 👋\n\n"
            f"Tu plan personalizado de {nombre_gym} ya está listo.\n"
            f"Adjunto encontrarás tu plan alimenticio.\n"
            f"Cualquier duda consúltala con tu entrenador.\n"
            f"{nombre_gym} agradece tu preferencia y te espera el próximo mes con tu plan actualizado."
        )
        if telefono_gym:
            mensaje += f"\n📞 {telefono_gym}"

        mensaje_codificado = urllib.parse.quote(mensaje)
        url = f"https://wa.me/{telefono}?text={mensaje_codificado}"
        webbrowser.open(url)
        
        messagebox.showinfo(
            "WhatsApp",
            "WhatsApp Web abierto. Adjunta el PDF manualmente y envía."
        )

    def _abrir_panel_admin(self, event=None):
        """Abre el panel de administración (atajo: Ctrl+Shift+A)."""
        try:
            VentanaAdmin(self)
        except Exception as e:
            logger.error("[APP] Error abriendo panel admin: %s", e, exc_info=True)
            messagebox.showerror("Error", f"No se pudo abrir el panel:\n{e}")

    def _abrir_clientes(self):
        """Abre la ventana de gestión de clientes."""
        if not self.gestor_bd:
            messagebox.showerror("Error", "Sistema de BD no disponible")
            return

        try:
            ventana = VentanaClientes(self, self.gestor_bd)
        except Exception as e:
            logger.error("[APP] Error abriendo ventana clientes: %s", e)
            messagebox.showerror("Error", f"No se pudo abrir Mis Clientes:\n{e}")

    def cargar_cliente_para_regeneracion(self, cliente_data: dict, plan_reciente: dict | None = None) -> None:
        """
        Carga datos y preferencias previas de un cliente para regenerar plan.
        Usado desde la ventana "Mis Clientes".
        """
        nombre = (cliente_data.get("nombre") or "").strip()
        telefono = (cliente_data.get("telefono") or "").strip()
        edad = cliente_data.get("edad")
        peso = cliente_data.get("peso_kg")
        estatura = cliente_data.get("estatura_cm")
        grasa = cliente_data.get("grasa_corporal_pct")
        actividad = cliente_data.get("nivel_actividad")

        self.entry_nombre.delete(0, "end")
        self.entry_nombre.insert(0, nombre)

        self.entry_telefono.delete(0, "end")
        if telefono:
            self.entry_telefono.insert(0, telefono)

        self.entry_edad.delete(0, "end")
        if edad is not None:
            self.entry_edad.insert(0, str(int(edad)))

        self.entry_peso.delete(0, "end")
        if peso is not None:
            self.entry_peso.insert(0, f"{float(peso):.1f}")

        self.entry_estatura.delete(0, "end")
        if estatura is not None:
            self.entry_estatura.insert(0, f"{float(estatura):.0f}")

        self.entry_grasa.delete(0, "end")
        if grasa is not None:
            self.entry_grasa.insert(0, f"{float(grasa):.1f}")

        plantilla_tipo = (
            (plan_reciente or {}).get("plantilla_tipo")
            or cliente_data.get("plantilla_tipo")
            or "perdida_grasa"
        )
        plantilla_label = PLANTILLAS_CLIENTE.get(plantilla_tipo, {}).get("label")
        if plantilla_label and plantilla_label in PLANTILLAS_LABELS:
            self.combo_plantilla.set(plantilla_label)
            self._on_plantilla_change(plantilla_label)
        else:
            self._set_objetivo_ui(cliente_data.get("objetivo") or "mantenimiento")

        tipo_plan_prev = (plan_reciente or {}).get("tipo_plan") or "menu_fijo"
        if str(tipo_plan_prev).lower() == "con_opciones":
            self.segmented_tipo_plan.set("Con Opciones")
        else:
            self.segmented_tipo_plan.set("Menú Fijo")

        # Mantener preferencia previa real del cliente por encima de sugerencia de plantilla.
        if actividad in NIVELES_ACTIVIDAD:
            self.combo_actividad.set(actividad)

        self.progress_indicator.pack_forget()
        self.step_flow.reset()

        for entry in (
            self.entry_nombre,
            self.entry_telefono,
            self.entry_edad,
            self.entry_peso,
            self.entry_estatura,
            self.entry_grasa,
        ):
            self._validar_campo(entry)

        self._actualizar_estado_boton_generar()
        self._log(f"Cliente cargado para regenerar plan: {nombre}")
        self._mostrar_toast("Cliente cargado. Ajusta y regenera el plan.", tipo="info")

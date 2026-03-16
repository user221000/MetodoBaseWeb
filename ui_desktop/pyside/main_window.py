# -*- coding: utf-8 -*-
"""
Ventana principal PySide6 — reemplaza gui/app_gui.py.
GymApp → MainWindow(QMainWindow).
"""

import os
import re
import threading
import webbrowser
import urllib.parse
from datetime import datetime

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QPushButton, QPlainTextEdit, QScrollArea,
    QFrame, QMessageBox, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtGui import QKeySequence, QShortcut, QFont

from utils.helpers import resource_path, abrir_carpeta_pdf
from utils.logger import logger
from config.constantes import (
    FACTORES_ACTIVIDAD, NIVELES_ACTIVIDAD, OBJETIVOS_VALIDOS,
    CARPETA_SALIDA, CARPETA_PLANES,
)
from config.plantillas_cliente import (
    PLANTILLAS_CLIENTE, PLANTILLAS_LABELS, PLANTILLAS_POR_LABEL,
)
from core.modelos import ClienteEvaluacion
from core.motor_nutricional import MotorNutricional
from core.generador_planes import ConstructorPlanNuevo
from core.exportador_salida import GeneradorPDFProfesional
from core.exportador_multi import ExportadorMultiformato
from core.branding import branding
from src.gestor_bd import GestorBDClientes
from gui.validadores import ValidadorCamposTiempoReal

from ui_desktop.pyside.widgets.toast import mostrar_toast
from ui_desktop.pyside.widgets.progress_indicator import ProgressIndicator
from ui_desktop.pyside.widgets.step_flow import StepFlowIndicator


# ── Puente de señales para thread-safe UI ────────────────────────────────────


class _Senales(QObject):
    log_msg       = Signal(str)
    set_progress  = Signal(float, str)
    complete_prog = Signal(str)
    set_step      = Signal(int)
    complete_step = Signal(int)
    reset_step    = Signal()
    reset_prog    = Signal()        # oculta y resetea barra de progreso
    show_preview  = Signal(object, dict)
    done          = Signal(str)    # ruta_pdf
    error_msg     = Signal(str)
    enable_pdf    = Signal(bool)
    btn_spinner   = Signal(bool)   # True = mostrar spinner


# ── Ventana principal ────────────────────────────────────────────────────────


class MainWindow(QMainWindow):
    """Ventana principal Método Base en PySide6."""

    # Paleta WCAG 2.1 AA
    COLOR_BG           = "#0D0D0D"
    COLOR_CARD         = "#1A1A1A"
    COLOR_PRIMARY      = "#9B4FB0"
    COLOR_PRIMARY_HOVER= "#B565C6"
    COLOR_SECONDARY    = "#D4A84B"
    COLOR_BORDER       = "#444444"
    COLOR_TEXT         = "#F5F5F5"
    COLOR_TEXT_MUTED   = "#B8B8B8"
    COLOR_INPUT_BG     = "#2A2A2A"
    COLOR_SUCCESS      = "#4CAF50"
    COLOR_ERROR        = "#F44336"
    COLOR_WARNING      = "#FF9800"
    COLOR_INFO         = "#2196F3"

    def __init__(self):
        super().__init__()

        # Branding configurable
        self.COLOR_PRIMARY   = branding.get("colores.primario",   self.COLOR_PRIMARY)
        self.COLOR_SECONDARY = branding.get("colores.secundario", self.COLOR_SECONDARY)

        self.setWindowTitle(
            f"{branding.get('nombre_corto', 'MB')} — {branding.get('nombre_gym', 'Método Base')}"
        )
        self.setFixedSize(840, 920)

        self.ultimo_pdf: str | None = None
        self._sig = _Senales()
        self._preview_confirmed = False
        self._preview_event: threading.Event | None = None

        # BD
        try:
            self.gestor_bd = GestorBDClientes()
            logger.info("[APP] Gestor de BD inicializado")
        except Exception as exc:
            logger.error("[APP] Error inicializando BD: %s", exc)
            self.gestor_bd = None

        self._build_ui()
        self._conectar_senales()

        # Atajo Ctrl+Shift+A
        sc = QShortcut(QKeySequence("Ctrl+Shift+A"), self)
        sc.activated.connect(self._abrir_panel_admin)

    # ------------------------------------------------------------------
    # Conexión de señales
    # ------------------------------------------------------------------

    def _conectar_senales(self) -> None:
        self._sig.log_msg.connect(self._log)
        self._sig.set_progress.connect(lambda v, s: self.progress.set_progress(v, s))
        self._sig.complete_prog.connect(lambda s: self.progress.complete(s))
        self._sig.set_step.connect(self.step_flow.set_step)
        self._sig.complete_step.connect(self.step_flow.complete_step)
        self._sig.reset_step.connect(self.step_flow.reset)
        self._sig.reset_prog.connect(self._hide_progress)
        self._sig.done.connect(self._on_done)
        self._sig.error_msg.connect(self._on_error)
        self._sig.enable_pdf.connect(self._enable_pdf_buttons)
        self._sig.btn_spinner.connect(self._set_btn_spinner)
        self._sig.show_preview.connect(self._abrir_preview)

    # ------------------------------------------------------------------
    # Construcción de UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        main_layout.addWidget(scroll)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        self._vbox = QVBoxLayout(container)
        self._vbox.setContentsMargins(0, 20, 0, 24)
        self._vbox.setSpacing(8)
        scroll.setWidget(container)

        self._crear_header()
        self._crear_step_flow()
        self._crear_seccion_cliente()
        self._crear_seccion_medidas()
        self._crear_seccion_perfil()
        self._crear_seccion_tipo_plan()
        self._crear_botones()
        self._crear_progress()
        self._crear_bitacora()

    # ── Header ──────────────────────────────────────────────────────────

    def _crear_header(self) -> None:
        header = QWidget()
        header.setStyleSheet("background: transparent;")
        h = QVBoxLayout(header)
        h.setAlignment(Qt.AlignCenter)
        h.setSpacing(2)

        nombre_corto = branding.get("nombre_corto", "Método Base")
        nombre_gym   = branding.get("nombre_gym",   "Fitness Gym")
        tagline      = branding.get("tagline",      "Sistema de Planes Nutricionales")

        self.lbl_titulo = QLabel(nombre_corto)
        self.lbl_titulo.setAlignment(Qt.AlignCenter)
        self.lbl_titulo.setStyleSheet(
            f"color: {self.COLOR_PRIMARY}; font-size: 32px; font-weight: 800; letter-spacing: -0.5px;"
        )
        h.addWidget(self.lbl_titulo)

        self.lbl_subtitulo = QLabel(nombre_gym)
        self.lbl_subtitulo.setAlignment(Qt.AlignCenter)
        self.lbl_subtitulo.setStyleSheet(
            f"color: {self.COLOR_SECONDARY}; font-size: 16px; font-weight: 700; letter-spacing: -0.2px;"
        )
        h.addWidget(self.lbl_subtitulo)

        self.lbl_contexto = QLabel(tagline)
        self.lbl_contexto.setAlignment(Qt.AlignCenter)
        self.lbl_contexto.setObjectName("caption")
        h.addWidget(self.lbl_contexto)

        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setObjectName("separator_h")
        sep.setContentsMargins(40, 0, 40, 0)
        self.separator = sep

        self._vbox.addWidget(header)
        self._vbox.addWidget(sep)

    # ── Step flow ────────────────────────────────────────────────────────

    def _crear_step_flow(self) -> None:
        wrapper = QWidget()
        wrapper.setStyleSheet("background: transparent;")
        wl = QHBoxLayout(wrapper)
        wl.setContentsMargins(40, 0, 40, 0)
        self.step_flow = StepFlowIndicator()
        wl.addWidget(self.step_flow)
        self._vbox.addWidget(wrapper)

    # ── Sección genérica ─────────────────────────────────────────────────

    def _crear_card(self, titulo: str, icono: str = "") -> QWidget:
        """Crea un card con título y devuelve el widget de contenido."""
        card = QFrame()
        card.setObjectName("card")
        wrapper = QHBoxLayout()
        wrapper.setContentsMargins(40, 0, 40, 0)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 12)
        card_layout.setSpacing(4)

        # Header de la sección
        hdr = QWidget()
        hdr.setStyleSheet("background: transparent;")
        hdr_row = QHBoxLayout(hdr)
        hdr_row.setContentsMargins(0, 0, 0, 0)
        hdr_row.setSpacing(8)
        if icono:
            lbl_icono = QLabel(icono)
            lbl_icono.setStyleSheet(
                f"color: {self.COLOR_PRIMARY}; font-size: 14px; background: transparent;"
            )
            hdr_row.addWidget(lbl_icono)
        lbl_titulo = QLabel(titulo)
        lbl_titulo.setStyleSheet(
            f"color: {self.COLOR_SECONDARY}; font-size: 14px; font-weight: bold; background: transparent;"
        )
        hdr_row.addWidget(lbl_titulo)
        hdr_row.addStretch()
        card_layout.addWidget(hdr)

        # Contenido (grid de 2 columnas para los fields)
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)
        card_layout.addWidget(content)

        widget_wrapper = self._vbox
        widget_wrapper.addWidget(card)

        return content

    # ── Sección 1: Cliente ───────────────────────────────────────────────

    def _crear_seccion_cliente(self) -> None:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 14)
        layout.setSpacing(8)

        hdr = QLabel("👤  Ficha del Cliente")
        hdr.setStyleSheet(
            f"color: {self.COLOR_SECONDARY}; font-size: 14px; font-weight: bold; background: transparent;"
        )
        layout.addWidget(hdr)

        # Nombre
        layout.addWidget(self._mk_field_lbl("Nombre completo"))
        self.entry_nombre = QLineEdit()
        self.entry_nombre.setPlaceholderText("Ej: Oscar Hernández")
        self.entry_nombre.textChanged.connect(self._validar_formulario)
        layout.addWidget(self.entry_nombre)
        self.lbl_error_nombre = self._mk_error_lbl()
        layout.addWidget(self.lbl_error_nombre)

        # Teléfono + Edad
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(12)

        col1 = QVBoxLayout()
        col1.setSpacing(4)
        col1.addWidget(self._mk_field_lbl("Teléfono"))
        self.entry_telefono = QLineEdit()
        self.entry_telefono.setPlaceholderText("Ej: 5213312345678 (opcional)")
        self.entry_telefono.textChanged.connect(self._validar_formulario)
        col1.addWidget(self.entry_telefono)
        self.lbl_error_telefono = self._mk_error_lbl()
        col1.addWidget(self.lbl_error_telefono)

        col2 = QVBoxLayout()
        col2.setSpacing(4)
        col2.addWidget(self._mk_field_lbl("Edad"))
        self.entry_edad = QLineEdit()
        self.entry_edad.setPlaceholderText("Ej: 25")
        self.entry_edad.textChanged.connect(self._validar_formulario)
        col2.addWidget(self.entry_edad)
        self.lbl_error_edad = self._mk_error_lbl()
        col2.addWidget(self.lbl_error_edad)

        rl.addLayout(col1)
        rl.addLayout(col2)
        layout.addWidget(row)

        wrapper = QWidget()
        wrapper.setStyleSheet("background: transparent;")
        wl = QHBoxLayout(wrapper)
        wl.setContentsMargins(40, 0, 40, 0)
        wl.addWidget(card)
        self._vbox.addWidget(wrapper)

    # ── Sección 2: Medidas ───────────────────────────────────────────────

    def _crear_seccion_medidas(self) -> None:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 14)
        layout.setSpacing(8)

        hdr = QLabel("⚖  Composición Corporal")
        hdr.setStyleSheet(
            f"color: {self.COLOR_SECONDARY}; font-size: 14px; font-weight: bold; background: transparent;"
        )
        layout.addWidget(hdr)

        # Peso + Estatura
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(12)

        col1 = QVBoxLayout()
        col1.addWidget(self._mk_field_lbl("Peso (kg)"))
        self.entry_peso = QLineEdit()
        self.entry_peso.setPlaceholderText("Ej: 80.5")
        self.entry_peso.textChanged.connect(self._validar_formulario)
        col1.addWidget(self.entry_peso)
        self.lbl_error_peso = self._mk_error_lbl()
        col1.addWidget(self.lbl_error_peso)

        col2 = QVBoxLayout()
        col2.addWidget(self._mk_field_lbl("Estatura (cm)"))
        self.entry_estatura = QLineEdit()
        self.entry_estatura.setPlaceholderText("Ej: 175")
        self.entry_estatura.textChanged.connect(self._validar_formulario)
        col2.addWidget(self.entry_estatura)
        self.lbl_error_estatura = self._mk_error_lbl()
        col2.addWidget(self.lbl_error_estatura)

        rl.addLayout(col1)
        rl.addLayout(col2)
        layout.addWidget(row)

        # Grasa
        layout.addWidget(self._mk_field_lbl("Grasa corporal (%)"))
        self.entry_grasa = QLineEdit()
        self.entry_grasa.setPlaceholderText("Ej: 18")
        self.entry_grasa.textChanged.connect(self._validar_formulario)
        layout.addWidget(self.entry_grasa)
        self.lbl_error_grasa = self._mk_error_lbl()
        layout.addWidget(self.lbl_error_grasa)

        wrapper = QWidget()
        wrapper.setStyleSheet("background: transparent;")
        wl = QHBoxLayout(wrapper)
        wl.setContentsMargins(40, 0, 40, 0)
        wl.addWidget(card)
        self._vbox.addWidget(wrapper)

    # ── Sección 3: Perfil ────────────────────────────────────────────────

    def _crear_seccion_perfil(self) -> None:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 14)
        layout.setSpacing(8)

        hdr = QLabel("🏋  Contexto de Entrenamiento")
        hdr.setStyleSheet(
            f"color: {self.COLOR_SECONDARY}; font-size: 14px; font-weight: bold; background: transparent;"
        )
        layout.addWidget(hdr)

        # Actividad + Objetivo
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(12)

        col1 = QVBoxLayout()
        col1.addWidget(self._mk_field_lbl("Actividad"))
        self.combo_actividad = QComboBox()
        self.combo_actividad.addItems(list(NIVELES_ACTIVIDAD))
        self.combo_actividad.setCurrentText("moderada")
        col1.addWidget(self.combo_actividad)

        col2 = QVBoxLayout()
        col2.addWidget(self._mk_field_lbl("Objetivo"))
        self.combo_objetivo = QComboBox()
        self.combo_objetivo.addItems(list(OBJETIVOS_VALIDOS))
        self.combo_objetivo.setCurrentText("mantenimiento")
        col2.addWidget(self.combo_objetivo)

        rl.addLayout(col1)
        rl.addLayout(col2)
        layout.addWidget(row)

        # Plantilla
        layout.addWidget(self._mk_field_lbl("Plantilla de cliente"))
        self.combo_plantilla = QComboBox()
        self.combo_plantilla.addItems(PLANTILLAS_LABELS)
        self.combo_plantilla.currentTextChanged.connect(self._on_plantilla_change)
        layout.addWidget(self.combo_plantilla)

        self.lbl_plantilla_contexto = QLabel("")
        self.lbl_plantilla_contexto.setWordWrap(True)
        self.lbl_plantilla_contexto.setObjectName("caption")
        layout.addWidget(self.lbl_plantilla_contexto)

        wrapper = QWidget()
        wrapper.setStyleSheet("background: transparent;")
        wl = QHBoxLayout(wrapper)
        wl.setContentsMargins(40, 0, 40, 0)
        wl.addWidget(card)
        self._vbox.addWidget(wrapper)

        self._on_plantilla_change(PLANTILLAS_LABELS[0])

    # ── Sección 4: Tipo de plan ──────────────────────────────────────────

    def _crear_seccion_tipo_plan(self) -> None:
        card = QFrame()
        card.setObjectName("card")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)

        lbl = QLabel("Formato de entrega:")
        lbl.setStyleSheet(
            f"color: {self.COLOR_SECONDARY}; font-size: 13px; font-weight: 700; background: transparent;"
        )
        layout.addWidget(lbl)
        layout.addSpacing(16)

        self.btn_menu_fijo = QPushButton("Menú Fijo")
        self.btn_menu_fijo.setObjectName("btn_toggle")
        self.btn_menu_fijo.setCheckable(True)
        self.btn_menu_fijo.setChecked(True)
        self.btn_menu_fijo.clicked.connect(lambda: self._cambiar_tipo_plan("Menú Fijo"))

        self.btn_con_opciones = QPushButton("Con Opciones")
        self.btn_con_opciones.setObjectName("btn_toggle")
        self.btn_con_opciones.setCheckable(True)
        self.btn_con_opciones.clicked.connect(lambda: self._cambiar_tipo_plan("Con Opciones"))

        layout.addWidget(self.btn_menu_fijo)
        layout.addWidget(self.btn_con_opciones)
        layout.addStretch()

        wrapper = QWidget()
        wrapper.setStyleSheet("background: transparent;")
        wl = QHBoxLayout(wrapper)
        wl.setContentsMargins(40, 0, 40, 0)
        wl.addWidget(card)
        self._vbox.addWidget(wrapper)

    def _cambiar_tipo_plan(self, tipo: str) -> None:
        es_fijo = (tipo == "Menú Fijo")
        self.btn_menu_fijo.setChecked(es_fijo)
        self.btn_con_opciones.setChecked(not es_fijo)
        if not es_fijo:
            mostrar_toast(
                self,
                "Se activó formato con opciones para dar alternativas al cliente.",
                tipo="info", duracion=4000,
            )

    def _tipo_plan_activo(self) -> str:
        return "Menú Fijo" if self.btn_menu_fijo.isChecked() else "Con Opciones"

    # ── Botones de acción ────────────────────────────────────────────────

    def _crear_botones(self) -> None:
        btns_w = QWidget()
        btns_w.setStyleSheet("background: transparent;")
        bl = QVBoxLayout(btns_w)
        bl.setContentsMargins(40, 20, 40, 4)
        bl.setSpacing(10)

        # Botón principal
        self.btn_procesar = QPushButton("INICIAR FLUJO DE PLAN")
        self.btn_procesar.setEnabled(False)
        self.btn_procesar.setMinimumHeight(56)
        self.btn_procesar.setStyleSheet(
            f"QPushButton {{ background-color: {self.COLOR_TEXT_MUTED}; color: #F5F5F5;"
            f" border: none; border-radius: 28px;"
            " font-size: 16px; font-weight: 800; letter-spacing: 0.3px; }}"
            f"QPushButton:enabled {{ background-color: {self.COLOR_PRIMARY}; }}"
            f"QPushButton:enabled:hover {{ background-color: {self.COLOR_PRIMARY_HOVER}; }}"
        )
        self.btn_procesar.clicked.connect(self._on_procesar_click)
        bl.addWidget(self.btn_procesar)

        # Botones secundarios
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)

        self.btn_whatsapp = QPushButton("Compartir por WhatsApp")
        self.btn_whatsapp.setEnabled(False)
        self.btn_whatsapp.setObjectName("btn_success")
        self.btn_whatsapp.setMinimumHeight(40)
        self.btn_whatsapp.clicked.connect(self.enviar_por_whatsapp)
        rl.addWidget(self.btn_whatsapp)

        self.btn_abrir_pdf = QPushButton("Abrir carpeta de PDF")
        self.btn_abrir_pdf.setObjectName("btn_secondary")
        self.btn_abrir_pdf.setMinimumHeight(40)
        self.btn_abrir_pdf.clicked.connect(self._abrir_carpeta_salida)
        rl.addWidget(self.btn_abrir_pdf)

        self.btn_clientes = QPushButton("👥 Mis Clientes")
        self.btn_clientes.setObjectName("btn_secondary")
        self.btn_clientes.setMinimumHeight(40)
        self.btn_clientes.clicked.connect(self._abrir_clientes)
        rl.addWidget(self.btn_clientes)

        bl.addWidget(row)
        self._vbox.addWidget(btns_w)

    # ── Progreso ────────────────────────────────────────────────────────

    def _crear_progress(self) -> None:
        wrapper = QWidget()
        wrapper.setStyleSheet("background: transparent;")
        wl = QHBoxLayout(wrapper)
        wl.setContentsMargins(40, 0, 40, 4)
        self.progress = ProgressIndicator()
        self.progress.setVisible(False)
        wl.addWidget(self.progress)
        self._vbox.addWidget(wrapper)
        self._progress_wrapper = wrapper

    # ── Bitácora ─────────────────────────────────────────────────────────

    def _crear_bitacora(self) -> None:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        lbl = QLabel("Bitácora del Staff")
        lbl.setObjectName("section_title")
        layout.addWidget(lbl)

        self.textbox_log = QPlainTextEdit()
        self.textbox_log.setReadOnly(True)
        self.textbox_log.setFixedHeight(110)
        self.textbox_log.setObjectName("log_box")
        layout.addWidget(self.textbox_log)

        wrapper = QWidget()
        wrapper.setStyleSheet("background: transparent;")
        wl = QHBoxLayout(wrapper)
        wl.setContentsMargins(40, 16, 40, 0)
        wl.addWidget(card)
        self._vbox.addWidget(wrapper)

        self._log("Sistema listo. Captura la ficha del cliente para iniciar.")

    # ------------------------------------------------------------------
    # Helpers de UI
    # ------------------------------------------------------------------

    def _mk_field_lbl(self, texto: str) -> QLabel:
        lbl = QLabel(texto)
        return lbl

    @staticmethod
    def _mk_error_lbl() -> QLabel:
        lbl = QLabel("")
        lbl.setWordWrap(True)
        lbl.setObjectName("error_label")
        return lbl

    _FIELD_BASE = ""   # kept for compat; no longer used

    def _set_field_state(self, entry: QLineEdit, lbl: QLabel, ok: bool, msg: str) -> None:
        if ok:
            entry.setStyleSheet(
                "QLineEdit { border: 1.5px solid #30D158; border-radius: 10px; }"
                "QLineEdit:focus { border: 2px solid #30D158; }"
            )
            lbl.setText("")
        else:
            entry.setStyleSheet(
                "QLineEdit { border: 1.5px solid #FF453A; border-radius: 10px; }"
                "QLineEdit:focus { border: 2px solid #FF453A; }"
            )
            lbl.setText(f"⚠ {msg}")

    # ------------------------------------------------------------------
    # Validación en tiempo real
    # ------------------------------------------------------------------

    def _reset_field(self, entry: QLineEdit, lbl: QLabel) -> None:
        """Restaura el estilo QSS original (sin validación) y limpia el error."""
        entry.setStyleSheet("")
        lbl.setText("")

    def _validar_formulario(self) -> None:
        # Nombre
        ok, msg = ValidadorCamposTiempoReal.validar_nombre(self.entry_nombre.text())
        if self.entry_nombre.text().strip():
            self._set_field_state(self.entry_nombre, self.lbl_error_nombre, ok, msg)
        else:
            self._reset_field(self.entry_nombre, self.lbl_error_nombre)

        # Edad
        ok, msg = ValidadorCamposTiempoReal.validar_edad(self.entry_edad.text())
        if self.entry_edad.text().strip():
            self._set_field_state(self.entry_edad, self.lbl_error_edad, ok, msg)
        else:
            self._reset_field(self.entry_edad, self.lbl_error_edad)

        # Peso
        ok, msg = ValidadorCamposTiempoReal.validar_peso(self.entry_peso.text())
        if self.entry_peso.text().strip():
            self._set_field_state(self.entry_peso, self.lbl_error_peso, ok, msg)
        else:
            self._reset_field(self.entry_peso, self.lbl_error_peso)

        # Estatura
        ok, msg = ValidadorCamposTiempoReal.validar_estatura(self.entry_estatura.text())
        if self.entry_estatura.text().strip():
            self._set_field_state(self.entry_estatura, self.lbl_error_estatura, ok, msg)
        else:
            self._reset_field(self.entry_estatura, self.lbl_error_estatura)

        # Grasa
        ok, msg = ValidadorCamposTiempoReal.validar_grasa(self.entry_grasa.text())
        if self.entry_grasa.text().strip():
            self._set_field_state(self.entry_grasa, self.lbl_error_grasa, ok, msg)
        else:
            self._reset_field(self.entry_grasa, self.lbl_error_grasa)

        # Teléfono (opcional)
        ok, msg = ValidadorCamposTiempoReal.validar_telefono(self.entry_telefono.text())
        if self.entry_telefono.text().strip():
            self._set_field_state(self.entry_telefono, self.lbl_error_telefono, ok, msg)
        else:
            self._reset_field(self.entry_telefono, self.lbl_error_telefono)

        self._actualizar_estado_boton()

    def _actualizar_estado_boton(self) -> None:
        all_ok = all([
            ValidadorCamposTiempoReal.validar_nombre(self.entry_nombre.text())[0],
            ValidadorCamposTiempoReal.validar_edad(self.entry_edad.text())[0],
            ValidadorCamposTiempoReal.validar_peso(self.entry_peso.text())[0],
            ValidadorCamposTiempoReal.validar_estatura(self.entry_estatura.text())[0],
            ValidadorCamposTiempoReal.validar_grasa(self.entry_grasa.text())[0],
        ])
        self.btn_procesar.setEnabled(all_ok)

    # ------------------------------------------------------------------
    # Plantilla
    # ------------------------------------------------------------------

    def _on_plantilla_change(self, plantilla_label: str) -> None:
        plantilla_key  = PLANTILLAS_POR_LABEL.get(plantilla_label, "perdida_grasa")
        plantilla_data = PLANTILLAS_CLIENTE.get(
            plantilla_key, PLANTILLAS_CLIENTE["perdida_grasa"]
        )
        objetivo = plantilla_data["objetivo_motor"]
        actividad_sugerida = plantilla_data.get("actividad_sugerida")

        if actividad_sugerida and actividad_sugerida in NIVELES_ACTIVIDAD:
            self.combo_actividad.setCurrentText(actividad_sugerida)

        self.combo_objetivo.setCurrentText(objetivo)

        self.lbl_plantilla_contexto.setText(
            f"Plantilla activa: {plantilla_data['label']} | Meta sugerida: {objetivo}. "
            f"Actividad sugerida: {actividad_sugerida or 'moderada'}. "
            f"{plantilla_data['descripcion']}"
        )

    # ------------------------------------------------------------------
    # Log y notificaciones
    # ------------------------------------------------------------------

    def _log(self, mensaje: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.textbox_log.appendPlainText(f"[{ts}] {mensaje}")
        self.textbox_log.verticalScrollBar().setValue(
            self.textbox_log.verticalScrollBar().maximum()
        )

    # ------------------------------------------------------------------
    # Señales de vuelta al hilo principal
    # ------------------------------------------------------------------

    def _on_done(self, ruta_pdf: str) -> None:
        self.ultimo_pdf = ruta_pdf or None
        self.progress.setVisible(True)
        self.progress.complete("✓ Plan exportado y listo para entregar")
        mostrar_toast(self, "✓ Plan y archivos listos", tipo="success")
        tiene_pdf = bool(self.ultimo_pdf and os.path.exists(self.ultimo_pdf))
        self.btn_whatsapp.setEnabled(tiene_pdf)
        if self.ultimo_pdf:
            self._log(f"PDF guardado en: {self.ultimo_pdf}")

    def _hide_progress(self) -> None:
        self.progress.reset()
        self.progress.setVisible(False)

    def _on_error(self, msg: str) -> None:
        self.step_flow.reset()
        self._hide_progress()
        mostrar_toast(self, f"❌ {msg}", tipo="error", duracion=5000)
        QMessageBox.critical(self, "Error", msg)

    def _enable_pdf_buttons(self, enabled: bool) -> None:
        self.btn_whatsapp.setEnabled(enabled)
        self.btn_abrir_pdf.setEnabled(enabled)

    def _set_btn_spinner(self, spin: bool) -> None:
        if spin:
            self.btn_procesar.setEnabled(False)
            self.btn_procesar.setText("Procesando flujo...")
        else:
            self._actualizar_estado_boton()
            self.btn_procesar.setText("INICIAR FLUJO DE PLAN")

    # ------------------------------------------------------------------
    # Preview callback (desde worker thread vía signal)
    # ------------------------------------------------------------------

    def _abrir_preview(self, cliente, plan: dict) -> None:
        from ui_desktop.pyside.ventana_preview import PlanPreviewWindow
        dlg = PlanPreviewWindow(self, cliente, plan)
        result = dlg.exec()
        self._preview_confirmed = (result == dlg.Accepted)
        if self._preview_event:
            self._preview_event.set()

    # ------------------------------------------------------------------
    # Procesamiento en hilo
    # ------------------------------------------------------------------

    def _on_procesar_click(self) -> None:
        self.btn_procesar.setEnabled(False)
        self.btn_procesar.setText("Procesando flujo...")
        self.progress.reset()
        self.step_flow.reset()
        self.progress.setVisible(True)
        thread = threading.Thread(target=self._procesar_datos, daemon=True)
        thread.start()

    def _procesar_datos(self) -> None:  # noqa: C901
        try:
            self._sig.log_msg.emit("Iniciando flujo: captura -> preview -> exportar.")
            self._sig.set_step.emit(0)
            self._sig.set_progress.emit(0.05, "Revisando captura del cliente...")

            nombre = self.entry_nombre.text().strip()
            if not nombre:
                raise ValueError("El nombre es obligatorio")

            telefono = self.entry_telefono.text().strip()
            if telefono:
                if not telefono.isdigit():
                    raise ValueError("Teléfono inválido: solo números, sin espacios ni símbolos")
                if len(telefono) < 10:
                    raise ValueError("Teléfono inválido: debe tener al menos 10 dígitos")

            edad = int(self.entry_edad.text())
            if edad < 1:
                raise ValueError("Edad inválida: debe ser mayor a 0")

            peso = float(self.entry_peso.text())
            if peso < 20:
                raise ValueError("Peso inválido: el mínimo permitido es 20 kg")
            if peso > 155:
                raise ValueError("Peso inválido: el máximo permitido es 155 kg")

            estatura = float(self.entry_estatura.text())
            grasa    = float(self.entry_grasa.text())
            if grasa < 5:
                raise ValueError("Grasa corporal inválida: el mínimo es 5%")

            actividad     = self.combo_actividad.currentText()
            plantilla_lbl = self.combo_plantilla.currentText()
            plantilla_key = PLANTILLAS_POR_LABEL.get(plantilla_lbl, "perdida_grasa")
            objetivo = PLANTILLAS_CLIENTE.get(
                plantilla_key, PLANTILLAS_CLIENTE["perdida_grasa"]
            )["objetivo_motor"]

            tipo_plan = self._tipo_plan_activo()
            tipo_plan_codigo = "con_opciones" if tipo_plan == "Con Opciones" else "menu_fijo"

            self._sig.set_progress.emit(0.2, "Calculando objetivo calórico...")

            # Cliente existente
            cliente_existente = None
            if self.gestor_bd and telefono:
                clientes = self.gestor_bd.buscar_clientes(telefono)
                if clientes:
                    cliente_existente = clientes[0]

            cliente = ClienteEvaluacion(
                nombre=nombre,
                telefono=telefono if telefono else None,
                edad=edad, peso_kg=peso,
                estatura_cm=estatura, grasa_corporal_pct=grasa,
                nivel_actividad=actividad, objetivo=objetivo,
            )
            cliente.plantilla_tipo = plantilla_key
            if cliente_existente:
                cliente.id_cliente = cliente_existente["id_cliente"]
            cliente.factor_actividad = FACTORES_ACTIVIDAD.get(actividad, 1.2)
            self._sig.log_msg.emit(
                f"Cliente creado: {cliente.nombre} ({cliente.objetivo}, plantilla {plantilla_lbl})"
            )

            cliente = MotorNutricional.calcular_motor(cliente)
            self._sig.log_msg.emit(
                f"Objetivo diario: {cliente.kcal_objetivo:.0f} kcal "
                f"(mantenimiento: {cliente.get_total:.0f} kcal)."
            )
            self._sig.set_progress.emit(0.45, "Armando comidas del plan...")

            os.makedirs(CARPETA_PLANES, exist_ok=True)

            if tipo_plan == "Con Opciones":
                from core.generador_opciones import ConstructorPlanConOpciones
                from core.exportador_opciones import GeneradorPDFConOpciones

                self._sig.log_msg.emit("Generando plan con OPCIONES...")
                plan = ConstructorPlanConOpciones.construir(
                    cliente, plan_numero=1,
                    directorio_planes=CARPETA_PLANES,
                    num_opciones_por_macro=3,
                )
                self._sig.complete_step.emit(0)
                self._sig.set_step.emit(1)
                self._sig.set_progress.emit(0.62, "Validando resumen previo para exportar...")
                self._sig.complete_step.emit(1)
                self._sig.set_step.emit(2)
                self._sig.set_progress.emit(0.80, "Exportando archivos...")

                os.makedirs(CARPETA_SALIDA, exist_ok=True)
                fecha = datetime.now().strftime("%Y-%m-%d")
                hora  = datetime.now().strftime("%H-%M-%S")
                nombre_san = re.sub(r"[^a-zA-Z0-9_]", "", cliente.nombre.replace(" ", "_"))
                carpeta_cli = os.path.join(CARPETA_SALIDA, nombre_san)
                os.makedirs(carpeta_cli, exist_ok=True)

                ruta_pdf = os.path.join(carpeta_cli, f"{nombre_san}_OPCIONES_{fecha}_{hora}.pdf")
                generador = GeneradorPDFConOpciones(ruta_pdf)
                ruta_pdf = generador.generar(cliente, plan)
                if not (ruta_pdf and os.path.exists(ruta_pdf)):
                    ruta_pdf = None

                try:
                    ruta_excel = os.path.join(carpeta_cli, f"{nombre_san}_OPCIONES_{fecha}_{hora}.xlsx")
                    ExportadorMultiformato.a_excel(cliente, plan, ruta_excel)
                    self._sig.log_msg.emit(f"Excel generado: {os.path.basename(ruta_excel)}")
                except Exception as exc:
                    self._sig.log_msg.emit(f"No se pudo generar Excel: {exc}")

            else:
                self._sig.log_msg.emit("Generando plan con menú FIJO...")
                plan = ConstructorPlanNuevo.construir(
                    cliente, plan_numero=1, directorio_planes=CARPETA_PLANES
                )
                self._sig.log_msg.emit("Plan nutricional estructurado correctamente.")
                self._sig.complete_step.emit(0)
                self._sig.set_step.emit(1)
                self._sig.set_progress.emit(0.65, "Mostrando preview para validación del staff...")

                # Abrir preview y esperar confirmación
                self._preview_confirmed = False
                self._preview_event = threading.Event()
                self._sig.show_preview.emit(cliente, plan)
                self._preview_event.wait()

                if not self._preview_confirmed:
                    self._sig.log_msg.emit("Generación cancelada por el usuario.")
                    self._sig.reset_step.emit()
                    self._sig.reset_prog.emit()
                    return

                self._sig.complete_step.emit(1)
                self._sig.set_step.emit(2)
                self._sig.set_progress.emit(0.80, "Exportando archivos...")

                os.makedirs(CARPETA_SALIDA, exist_ok=True)
                fecha = datetime.now().strftime("%Y-%m-%d")
                hora  = datetime.now().strftime("%H-%M-%S")
                nombre_san = re.sub(r"[^a-zA-Z0-9_]", "", cliente.nombre.replace(" ", "_"))
                carpeta_cli = os.path.join(CARPETA_SALIDA, nombre_san)
                os.makedirs(carpeta_cli, exist_ok=True)

                ruta_pdf_path = os.path.join(carpeta_cli, f"{nombre_san}_{fecha}_{hora}.pdf")
                generador = GeneradorPDFProfesional(ruta_pdf_path)
                ruta_pdf = generador.generar(cliente, plan)
                if not (ruta_pdf and os.path.exists(ruta_pdf)):
                    ruta_pdf = None

                try:
                    ruta_excel = os.path.join(carpeta_cli, f"{nombre_san}_{fecha}_{hora}.xlsx")
                    ExportadorMultiformato.a_excel(cliente, plan, ruta_excel)
                    self._sig.log_msg.emit(f"Excel generado: {os.path.basename(ruta_excel)}")
                except Exception as exc:
                    self._sig.log_msg.emit(f"No se pudo generar Excel: {exc}")

            # Registro en BD
            if self.gestor_bd:
                try:
                    self.gestor_bd.registrar_cliente(cliente)
                    if ruta_pdf:
                        self.gestor_bd.registrar_plan_generado(
                            cliente, plan, ruta_pdf, tipo_plan=tipo_plan_codigo
                        )
                    self._sig.log_msg.emit("Plan y cliente registrados en BD.")
                except Exception as exc:
                    logger.warning("[BD] Error al guardar en BD: %s", exc)
                    self._sig.log_msg.emit(f"Advertencia BD: {exc}")

            self._sig.complete_step.emit(2)
            self._sig.log_msg.emit(f"PDF: {ruta_pdf}")
            self._sig.done.emit(ruta_pdf or "")

        except ValueError as ve:
            self._sig.log_msg.emit(f"Error de validación: {ve}")
            self._sig.error_msg.emit(f"Revisa la ficha del cliente.\nDetalle: {ve}")
        except Exception as exc:
            import traceback
            self._sig.log_msg.emit(f"ERROR: {exc}")
            self._sig.error_msg.emit(f"Ocurrió un error:\n{exc}")
            traceback.print_exc()
        finally:
            self._sig.btn_spinner.emit(False)

    # ------------------------------------------------------------------
    # Acciones adicionales
    # ------------------------------------------------------------------

    def enviar_por_whatsapp(self) -> None:
        if not self.ultimo_pdf or not os.path.exists(self.ultimo_pdf):
            QMessageBox.critical(self, "Error", "Primero debes generar el plan.")
            return
        telefono = self.entry_telefono.text().strip()
        if not telefono:
            QMessageBox.warning(
                self, "Teléfono requerido",
                "Ingresa el teléfono del cliente para compartir por WhatsApp."
            )
            self.entry_telefono.setFocus()
            return
        if not telefono.isdigit():
            QMessageBox.critical(
                self, "Teléfono inválido",
                "El teléfono debe contener solo dígitos, sin espacios ni símbolos."
            )
            return
        if len(telefono) < 10:
            QMessageBox.critical(
                self, "Teléfono inválido",
                "El teléfono debe tener al menos 10 dígitos."
            )
            return
        if not telefono.startswith("52"):
            QMessageBox.warning(
                self, "Formato de número",
                "Para México, el número debe iniciar con 52.\n"
                f"Número actual: {telefono}\n\nSe intentará enviar de todas formas."
            )
        nombre = self.entry_nombre.text().strip()
        msg = (
            f"Hola {nombre} 💪🏽 Tu plan nutricional personalizado está listo. "
            f"Aquí está tu archivo PDF para que puedas revisarlo cuando quieras."
        )
        url = f"https://wa.me/{telefono}?text={urllib.parse.quote(msg)}"
        webbrowser.open(url)

    def _abrir_carpeta_salida(self) -> None:
        """Abre la carpeta del último PDF generado, o la carpeta general de salida."""
        if self.ultimo_pdf and os.path.exists(self.ultimo_pdf):
            abrir_carpeta_pdf(os.path.dirname(self.ultimo_pdf))
        else:
            abrir_carpeta_pdf()

    def _abrir_panel_admin(self, _checked=False) -> None:
        from ui_desktop.pyside.ventana_admin import VentanaAdmin
        dlg = VentanaAdmin(self)
        dlg.exec()

    def _abrir_clientes(self) -> None:
        from ui_desktop.pyside.ventana_clientes import VentanaClientes
        dlg = VentanaClientes(self, self.gestor_bd)
        dlg.exec()

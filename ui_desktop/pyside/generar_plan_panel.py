# -*- coding: utf-8 -*-
"""
Panel Generar Plan — Wizard de 3 pasos para generar planes nutricionales.

Paso 1: Seleccionar cliente o registrar nuevo
Paso 2: Parámetros del plan (tipo, plantilla)
Paso 3: Resultado (progreso, PDF, WhatsApp)
"""
from __future__ import annotations

import os
import re
import threading
import urllib.parse
import webbrowser
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QObject, Signal, QTimer
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea,
    QSizePolicy, QSpinBox, QStackedWidget, QVBoxLayout, QWidget,
    QPlainTextEdit,
)

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
from src.gestor_bd import GestorBDClientes
from ui_desktop.pyside.widgets.progress_indicator import ProgressIndicator
from utils.helpers import resource_path, abrir_carpeta_pdf
from utils.logger import logger


# ── Señales de hilo ───────────────────────────────────────────────────────────

class _Senales(QObject):  # noqa: N801
    log_msg         = Signal(str)
    set_progress    = Signal(float, str)
    complete_prog   = Signal(str)
    show_preview    = Signal(object, dict)
    done            = Signal(str)
    error_msg       = Signal(str)
    btn_spinner     = Signal(bool)


# ── Panel principal ───────────────────────────────────────────────────────────

class GenerarPlanPanel(QWidget):
    """Wizard de 3 pasos para generar un plan nutricional."""

    # Emitida cuando se quiere navegar a otro panel
    navigate_to = Signal(str)   # "dashboard" | "clientes"

    def __init__(self, gestor_bd: GestorBDClientes | None = None, parent=None):
        super().__init__(parent)
        self.gestor_bd = gestor_bd or GestorBDClientes()

        # Estado del wizard
        self._cliente_actual: ClienteEvaluacion | None = None
        self._ultimo_pdf: str | None = None
        self._preview_confirmed = False
        self._preview_event: threading.Event | None = None

        # Señales thread-safe
        self._sig = _Senales()
        self._sig.log_msg.connect(self._log)
        self._sig.set_progress.connect(lambda v, s: self.progress.set_progress(v, s))
        self._sig.complete_prog.connect(lambda s: self.progress.complete(s))
        self._sig.show_preview.connect(self._abrir_preview)
        self._sig.done.connect(self._on_done)
        self._sig.error_msg.connect(self._on_error)
        self._sig.btn_spinner.connect(self._set_btn_spinner)

        self._setup_ui()

    # ── Construcción ──────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        root.addWidget(scroll)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        self._vbox = QVBoxLayout(content)
        self._vbox.setContentsMargins(32, 24, 32, 32)
        self._vbox.setSpacing(24)
        scroll.setWidget(content)

        self._crear_header()
        self._crear_wizard_steps()
        self._stack = QStackedWidget()
        self._vbox.addWidget(self._stack)

        # Páginas del wizard
        self._page1 = self._crear_pagina1()
        self._page2 = self._crear_pagina2()
        self._page3 = self._crear_pagina3()

        self._stack.addWidget(self._page1)
        self._stack.addWidget(self._page2)
        self._stack.addWidget(self._page3)

        self._ir_a_paso(0)

    def _crear_header(self) -> None:
        header = QFrame()
        header.setObjectName("headerFrame")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 16)

        left = QVBoxLayout()
        left.setSpacing(4)

        title = QLabel("Generar Plan Nutricional")
        title.setObjectName("pageTitle")
        left.addWidget(title)

        subtitle = QLabel("Crea un plan personalizado en 3 pasos")
        subtitle.setObjectName("pageSubtitle")
        left.addWidget(subtitle)

        layout.addLayout(left)
        layout.addStretch()
        self._vbox.addWidget(header)

    def _crear_wizard_steps(self) -> None:
        """Barra de progreso visual de los 3 pasos."""
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        pasos = [
            ("1", "Seleccionar cliente"),
            ("2", "Datos del plan"),
            ("3", "Resultado"),
        ]

        self._step_circles: list[QLabel] = []
        self._step_labels: list[QLabel] = []

        for i, (num, texto) in enumerate(pasos):
            # Círculo numerado
            circle = QLabel(num)
            circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
            circle.setFixedSize(36, 36)
            self._step_circles.append(circle)
            layout.addWidget(circle)

            # Texto
            lbl = QLabel(texto)
            lbl.setStyleSheet("background: transparent; font-size: 13px;")
            self._step_labels.append(lbl)
            layout.addWidget(lbl)

            # Línea separadora (excepto en el último)
            if i < len(pasos) - 1:
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.HLine)
                sep.setStyleSheet("background-color: #2d2d40; max-height: 2px; margin: 0 12px;")
                sep.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                layout.addWidget(sep, 1)

        self._vbox.addWidget(container)

    def _actualizar_steps(self, paso_actual: int) -> None:
        """Actualiza los estilos visuales de los círculos de pasos."""
        for i, (circle, lbl) in enumerate(
            zip(self._step_circles, self._step_labels)
        ):
            if i < paso_actual:
                circle.setStyleSheet(
                    "background-color: #10b981; color: white; border-radius: 18px;"
                    " font-weight: 700;"
                )
                lbl.setStyleSheet("background: transparent; color: #8e8e93; font-size: 13px;")
            elif i == paso_actual:
                circle.setStyleSheet(
                    "background-color: #667eea; color: white; border-radius: 18px;"
                    " font-weight: 700;"
                )
                lbl.setStyleSheet(
                    "background: transparent; color: #f2f2f7; font-size: 13px; font-weight: 600;"
                )
            else:
                circle.setStyleSheet(
                    "background-color: #2d2d40; color: #8e8e93; border-radius: 18px;"
                )
                lbl.setStyleSheet("background: transparent; color: #5e5e6e; font-size: 13px;")

    # ── Página 1: Selección de cliente ────────────────────────────────────────

    def _crear_pagina1(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Barra de búsqueda
        search_row = QHBoxLayout()
        self.entry_busqueda = QLineEdit()
        self.entry_busqueda.setPlaceholderText("🔍  Buscar cliente o crear nuevo...")
        self.entry_busqueda.textChanged.connect(self._on_buscar_cliente)
        search_row.addWidget(self.entry_busqueda, 1)

        btn_nuevo = QPushButton("+ Nuevo cliente")
        btn_nuevo.setObjectName("btnNuevoCliente")
        btn_nuevo.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_nuevo.clicked.connect(self._toggle_form_nuevo)
        search_row.addWidget(btn_nuevo)
        layout.addLayout(search_row)

        # Área de resultados de búsqueda
        self.resultado_container = QFrame()
        self.resultado_container.setObjectName("formCard")
        results_layout = QVBoxLayout(self.resultado_container)
        results_layout.setContentsMargins(12, 12, 12, 12)
        results_layout.setSpacing(4)
        self.lbl_sin_resultados = QLabel("Ingresa un nombre para buscar clientes existentes.")
        self.lbl_sin_resultados.setStyleSheet("color: #8e8e93; padding: 8px;")
        results_layout.addWidget(self.lbl_sin_resultados)
        self._results_layout = results_layout
        layout.addWidget(self.resultado_container)

        # Formulario nuevo cliente (oculto por defecto)
        self.form_nuevo = self._crear_form_nuevo_cliente()
        self.form_nuevo.setVisible(False)
        layout.addWidget(self.form_nuevo)

        layout.addStretch()
        return page

    def _crear_form_nuevo_cliente(self) -> QFrame:
        """Formulario para registrar un cliente nuevo en el paso 1."""
        form = QFrame()
        form.setObjectName("formCard")
        layout = QVBoxLayout(form)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        hdr = QLabel("REGISTRAR NUEVO CLIENTE")
        hdr.setStyleSheet(
            "color: #8e8e93; font-size: 12px; font-weight: 600; "
            "letter-spacing: 0.5px; background: transparent;"
        )
        layout.addWidget(hdr)

        grid = QGridLayout()
        grid.setSpacing(12)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)

        def lbl(t: str) -> QLabel:
            l = QLabel(t)
            l.setObjectName("fieldLabel")
            return l

        # Fila 0: Nombre | Teléfono
        grid.addWidget(lbl("Nombre completo *"), 0, 0, 1, 2)
        grid.addWidget(lbl("Teléfono"), 0, 2)

        self.f_nombre = QLineEdit()
        self.f_nombre.setPlaceholderText("Ej: Juan Pérez")
        self.f_nombre.textChanged.connect(self._validar_form_nuevo)
        grid.addWidget(self.f_nombre, 1, 0, 1, 2)

        self.f_telefono = QLineEdit()
        self.f_telefono.setPlaceholderText("10 dígitos")
        grid.addWidget(self.f_telefono, 1, 2)

        # Fila 2: Edad | Sexo | Objetivo
        grid.addWidget(lbl("Edad *"), 2, 0)
        grid.addWidget(lbl("Sexo"), 2, 1)
        grid.addWidget(lbl("Objetivo *"), 2, 2)

        self.f_edad = QSpinBox()
        self.f_edad.setRange(14, 100)
        self.f_edad.setValue(25)
        grid.addWidget(self.f_edad, 3, 0)

        self.f_sexo = QComboBox()
        self.f_sexo.addItems(["M", "F", "Otro"])
        grid.addWidget(self.f_sexo, 3, 1)

        self.f_objetivo = QComboBox()
        objetivos = OBJETIVOS_VALIDOS if OBJETIVOS_VALIDOS else [
            "Déficit calórico", "Mantenimiento", "Superávit calórico"
        ]
        self.f_objetivo.addItems(objetivos)
        grid.addWidget(self.f_objetivo, 3, 2)

        # Fila 4: Peso | Estatura | % Grasa
        grid.addWidget(lbl("Peso (kg) *"), 4, 0)
        grid.addWidget(lbl("Estatura (cm) *"), 4, 1)
        grid.addWidget(lbl("% Grasa"), 4, 2)

        self.f_peso = QDoubleSpinBox()
        self.f_peso.setRange(30, 250)
        self.f_peso.setValue(70.0)
        self.f_peso.setSingleStep(0.5)
        grid.addWidget(self.f_peso, 5, 0)

        self.f_estatura = QDoubleSpinBox()
        self.f_estatura.setRange(100, 250)
        self.f_estatura.setValue(170.0)
        grid.addWidget(self.f_estatura, 5, 1)

        self.f_grasa = QDoubleSpinBox()
        self.f_grasa.setRange(3, 60)
        self.f_grasa.setValue(15.0)
        self.f_grasa.setSingleStep(0.5)
        grid.addWidget(self.f_grasa, 5, 2)

        # Fila 6: Nivel actividad
        grid.addWidget(lbl("Nivel actividad *"), 6, 0)
        self.f_actividad = QComboBox()
        niveles = NIVELES_ACTIVIDAD if NIVELES_ACTIVIDAD else [
            "nula", "leve", "moderada", "intensa"
        ]
        self.f_actividad.addItems(niveles)
        self.f_actividad.setCurrentText("moderada")
        grid.addWidget(self.f_actividad, 7, 0, 1, 2)

        layout.addLayout(grid)

        # Botones del formulario
        btns_row = QHBoxLayout()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("secondaryButton")
        btn_cancelar.clicked.connect(self._toggle_form_nuevo)
        btns_row.addWidget(btn_cancelar)
        btns_row.addStretch()

        self.btn_registrar_continuar = QPushButton("Registrar y continuar →")
        self.btn_registrar_continuar.setObjectName("btnRegistrarContinuar")
        self.btn_registrar_continuar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_registrar_continuar.setEnabled(False)
        self.btn_registrar_continuar.clicked.connect(self._on_registrar_cliente_nuevo)
        btns_row.addWidget(self.btn_registrar_continuar)

        layout.addLayout(btns_row)
        return form

    # ── Página 2: Parámetros del plan ─────────────────────────────────────────

    def _crear_pagina2(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # Info del cliente seleccionado
        self.lbl_cliente_info = QLabel("Sin cliente seleccionado")
        self.lbl_cliente_info.setStyleSheet(
            "background-color: #1e1e2e; border: 1px solid #2d2d40;"
            " border-radius: 10px; padding: 12px 16px; color: #f2f2f7; font-weight: 600;"
        )
        layout.addWidget(self.lbl_cliente_info)

        # Tipo de plan
        tipo_card = QFrame()
        tipo_card.setObjectName("formCard")
        tipo_layout = QVBoxLayout(tipo_card)
        tipo_layout.setContentsMargins(20, 16, 20, 16)
        tipo_layout.setSpacing(12)

        lbl_tipo = QLabel("Formato de entrega")
        lbl_tipo.setObjectName("sectionTitle")
        tipo_layout.addWidget(lbl_tipo)

        tipo_row = QHBoxLayout()
        self.btn_menu_fijo = QPushButton("📋  Menú Fijo")
        self.btn_menu_fijo.setCheckable(True)
        self.btn_menu_fijo.setChecked(True)
        self.btn_menu_fijo.clicked.connect(lambda: self._cambiar_tipo("menu_fijo"))
        self.btn_menu_fijo.setStyleSheet(self._btn_toggle_style(True))
        tipo_row.addWidget(self.btn_menu_fijo)

        self.btn_con_opciones = QPushButton("🔀  Con Opciones")
        self.btn_con_opciones.setCheckable(True)
        self.btn_con_opciones.clicked.connect(lambda: self._cambiar_tipo("con_opciones"))
        self.btn_con_opciones.setStyleSheet(self._btn_toggle_style(False))
        tipo_row.addWidget(self.btn_con_opciones)
        tipo_row.addStretch()
        tipo_layout.addLayout(tipo_row)
        layout.addWidget(tipo_card)

        # Plantilla
        plant_card = QFrame()
        plant_card.setObjectName("formCard")
        plant_layout = QVBoxLayout(plant_card)
        plant_layout.setContentsMargins(20, 16, 20, 16)
        plant_layout.setSpacing(10)

        lbl_plant = QLabel("Plantilla del cliente")
        lbl_plant.setObjectName("sectionTitle")
        plant_layout.addWidget(lbl_plant)

        self.combo_plantilla = QComboBox()
        self.combo_plantilla.addItems(PLANTILLAS_LABELS)
        plant_layout.addWidget(self.combo_plantilla)

        self.lbl_plantilla_desc = QLabel("")
        self.lbl_plantilla_desc.setStyleSheet("color: #8e8e93; font-size: 12px;")
        self.lbl_plantilla_desc.setWordWrap(True)
        plant_layout.addWidget(self.lbl_plantilla_desc)

        self.combo_plantilla.currentTextChanged.connect(self._on_plantilla_change)
        self._on_plantilla_change(self.combo_plantilla.currentText())

        layout.addWidget(plant_card)

        # Botones
        btns_row = QHBoxLayout()
        btn_atras = QPushButton("← Atrás")
        btn_atras.setObjectName("secondaryButton")
        btn_atras.clicked.connect(lambda: self._ir_a_paso(0))
        btns_row.addWidget(btn_atras)
        btns_row.addStretch()

        self.btn_generar = QPushButton("⚡  Generar Plan")
        self.btn_generar.setObjectName("btnGenerarPlan")
        self.btn_generar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_generar.clicked.connect(self._on_generar_click)
        btns_row.addWidget(self.btn_generar)

        layout.addLayout(btns_row)
        layout.addStretch()
        return page

    # ── Página 3: Resultado ───────────────────────────────────────────────────

    def _crear_pagina3(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # Indicador de progreso
        self.progress = ProgressIndicator()
        layout.addWidget(self.progress)

        # Resultado
        resultado_card = QFrame()
        resultado_card.setObjectName("formCard")
        res_layout = QVBoxLayout(resultado_card)
        res_layout.setContentsMargins(20, 16, 20, 16)
        res_layout.setSpacing(12)

        self.lbl_resultado = QLabel("Generando plan nutricional...")
        self.lbl_resultado.setStyleSheet(
            "color: #f2f2f7; font-size: 16px; font-weight: 600;"
        )
        self.lbl_resultado.setWordWrap(True)
        res_layout.addWidget(self.lbl_resultado)

        self.lbl_pdf_ruta = QLabel("")
        self.lbl_pdf_ruta.setStyleSheet("color: #8e8e93; font-size: 12px;")
        self.lbl_pdf_ruta.setWordWrap(True)
        res_layout.addWidget(self.lbl_pdf_ruta)

        layout.addWidget(resultado_card)

        # Bitácora
        log_card = QFrame()
        log_card.setObjectName("formCard")
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(16, 12, 16, 12)

        lbl_log = QLabel("Bitácora")
        lbl_log.setStyleSheet("color: #8e8e93; font-size: 12px; font-weight: 600;")
        log_layout.addWidget(lbl_log)

        self.textbox_log = QPlainTextEdit()
        self.textbox_log.setReadOnly(True)
        self.textbox_log.setFixedHeight(100)
        self.textbox_log.setStyleSheet(
            "background-color: #0f0f1a; border: none; font-size: 12px; color: #8e8e93;"
        )
        log_layout.addWidget(self.textbox_log)
        layout.addWidget(log_card)

        # Botones de resultado
        btns_row = QHBoxLayout()
        btns_row.setSpacing(10)

        self.btn_nuevo_plan = QPushButton("+ Nuevo Plan")
        self.btn_nuevo_plan.setObjectName("secondaryButton")
        self.btn_nuevo_plan.clicked.connect(self._reset_wizard)
        btns_row.addWidget(self.btn_nuevo_plan)

        self.btn_abrir_carpeta = QPushButton("📁  Abrir carpeta")
        self.btn_abrir_carpeta.setEnabled(False)
        self.btn_abrir_carpeta.clicked.connect(self._abrir_carpeta)
        btns_row.addWidget(self.btn_abrir_carpeta)

        self.btn_whatsapp = QPushButton("💬  WhatsApp")
        self.btn_whatsapp.setEnabled(False)
        self.btn_whatsapp.clicked.connect(self._enviar_whatsapp)
        btns_row.addWidget(self.btn_whatsapp)

        btns_row.addStretch()
        layout.addLayout(btns_row)
        layout.addStretch()
        return page

    # ── Navegación del wizard ─────────────────────────────────────────────────

    def _ir_a_paso(self, paso: int) -> None:
        self._step_actual = paso
        self._stack.setCurrentIndex(paso)
        self._actualizar_steps(paso)

    def iniciar_con_cliente(self, cliente: dict) -> None:
        """Inicia el wizard con un cliente ya seleccionado (desde ClientesPanel)."""
        self._cargar_cliente_de_dict(cliente)
        self._ir_a_paso(1)

    # ── Lógica paso 1 ─────────────────────────────────────────────────────────

    def _on_buscar_cliente(self, texto: str) -> None:
        # Limpiar resultados anteriores
        while self._results_layout.count() > 0:
            item = self._results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not texto.strip():
            self.lbl_sin_resultados = QLabel(
                "Ingresa un nombre para buscar clientes existentes."
            )
            self.lbl_sin_resultados.setStyleSheet("color: #8e8e93; padding: 8px;")
            self._results_layout.addWidget(self.lbl_sin_resultados)
            return

        try:
            clientes = self.gestor_bd.buscar_clientes(texto, solo_activos=True, limite=5)
        except Exception:
            clientes = []

        if not clientes:
            lbl = QLabel("No se encontraron clientes.")
            lbl.setStyleSheet("color: #8e8e93; padding: 8px;")
            self._results_layout.addWidget(lbl)
            return

        for c in clientes:
            row = self._crear_cliente_row(c)
            self._results_layout.addWidget(row)

    def _crear_cliente_row(self, cliente: dict) -> QFrame:
        """Crea una fila clickeable para un cliente en los resultados."""
        row = QFrame()
        row.setObjectName("clienteRow")
        row.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        # Avatar
        from ui_desktop.pyside.widgets.avatar_widget import AvatarWidget
        idx = hash(cliente.get("id_cliente", "")) % 7
        avatar = AvatarWidget(cliente.get("nombre", "?"), size=36, color_idx=idx)
        layout.addWidget(avatar)

        # Info
        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        nombre_lbl = QLabel(cliente.get("nombre", "—"))
        nombre_lbl.setStyleSheet("font-weight: 600; color: #f2f2f7; font-size: 14px;")
        info_col.addWidget(nombre_lbl)
        detalle = QLabel(
            f"{cliente.get('objetivo', '—')} · {cliente.get('edad', '—')} años · "
            f"{cliente.get('peso_kg', '—')} kg"
        )
        detalle.setStyleSheet("color: #8e8e93; font-size: 12px;")
        info_col.addWidget(detalle)
        layout.addLayout(info_col)
        layout.addStretch()

        # Botón seleccionar
        btn = QPushButton("Seleccionar →")
        btn.setStyleSheet(
            "QPushButton { background-color: #2d2d40; color: #f2f2f7; border-radius: 6px;"
            " padding: 6px 12px; font-size: 12px; }"
            "QPushButton:hover { background-color: #667eea; }"
        )
        _c = dict(cliente)
        btn.clicked.connect(lambda _, cl=_c: self._on_seleccionar_cliente(cl))
        layout.addWidget(btn)

        return row

    def _on_seleccionar_cliente(self, cliente: dict) -> None:
        self._cargar_cliente_de_dict(cliente)
        self._ir_a_paso(1)

    def _cargar_cliente_de_dict(self, cliente: dict) -> None:
        """Construye un ClienteEvaluacion desde un dict de BD."""
        nivel = cliente.get("nivel_actividad") or "moderada"
        self._cliente_actual = ClienteEvaluacion(
            nombre=cliente.get("nombre", ""),
            telefono=cliente.get("telefono") or None,
            edad=int(cliente.get("edad") or 25),
            peso_kg=float(cliente.get("peso_kg") or 70),
            estatura_cm=float(cliente.get("estatura_cm") or 170),
            grasa_corporal_pct=float(cliente.get("grasa_corporal_pct") or 15),
            nivel_actividad=nivel,
            objetivo=cliente.get("objetivo") or "Mantenimiento",
        )
        if cliente.get("id_cliente"):
            self._cliente_actual.id_cliente = cliente["id_cliente"]
        self._cliente_actual.factor_actividad = FACTORES_ACTIVIDAD.get(nivel, 1.375)

        # Actualizar info en página 2
        self.lbl_cliente_info.setText(
            f"👤  {self._cliente_actual.nombre}  ·  {self._cliente_actual.objetivo}  "
            f"·  {self._cliente_actual.edad} años  ·  {self._cliente_actual.peso_kg} kg"
        )

    def _toggle_form_nuevo(self) -> None:
        visible = not self.form_nuevo.isVisible()
        self.form_nuevo.setVisible(visible)
        self.resultado_container.setVisible(not visible)
        if visible:
            self.f_nombre.setFocus()

    def _validar_form_nuevo(self) -> None:
        ok = bool(self.f_nombre.text().strip())
        self.btn_registrar_continuar.setEnabled(ok)

    def _on_registrar_cliente_nuevo(self) -> None:
        nombre = self.f_nombre.text().strip()
        if not nombre:
            return

        nivel = self.f_actividad.currentText()
        self._cliente_actual = ClienteEvaluacion(
            nombre=nombre,
            telefono=self.f_telefono.text().strip() or None,
            edad=self.f_edad.value(),
            peso_kg=self.f_peso.value(),
            estatura_cm=self.f_estatura.value(),
            grasa_corporal_pct=self.f_grasa.value(),
            nivel_actividad=nivel,
            objetivo=self.f_objetivo.currentText(),
        )
        self._cliente_actual.factor_actividad = FACTORES_ACTIVIDAD.get(nivel, 1.375)

        # Registrar en BD
        try:
            self.gestor_bd.registrar_cliente(self._cliente_actual)
        except Exception as exc:
            logger.warning("[PLAN] No se pudo pre-registrar cliente: %s", exc)

        self.lbl_cliente_info.setText(
            f"👤  {self._cliente_actual.nombre}  ·  {self._cliente_actual.objetivo}  "
            f"·  {self._cliente_actual.edad} años  ·  {self._cliente_actual.peso_kg} kg"
        )
        self.form_nuevo.setVisible(False)
        self.resultado_container.setVisible(True)
        self._ir_a_paso(1)

    # ── Lógica paso 2 ─────────────────────────────────────────────────────────

    def _cambiar_tipo(self, tipo: str) -> None:
        es_fijo = (tipo == "menu_fijo")
        self.btn_menu_fijo.setChecked(es_fijo)
        self.btn_con_opciones.setChecked(not es_fijo)
        self.btn_menu_fijo.setStyleSheet(self._btn_toggle_style(es_fijo))
        self.btn_con_opciones.setStyleSheet(self._btn_toggle_style(not es_fijo))

    @staticmethod
    def _btn_toggle_style(activo: bool) -> str:
        if activo:
            return (
                "QPushButton { background: qlineargradient("
                "x1:0,y1:0,x2:1,y2:0, stop:0 #a855f7, stop:1 #ec4899);"
                " color: white; font-weight: 600; border-radius: 8px; padding: 10px 20px; }"
            )
        return (
            "QPushButton { background-color: #2d2d40; color: #8e8e93;"
            " border-radius: 8px; padding: 10px 20px; }"
            "QPushButton:hover { background-color: #3a3a50; color: #f2f2f7; }"
        )

    def _on_plantilla_change(self, label: str) -> None:
        key = PLANTILLAS_POR_LABEL.get(label, "perdida_grasa")
        data = PLANTILLAS_CLIENTE.get(key, {})
        desc = data.get("descripcion", "")
        self.lbl_plantilla_desc.setText(desc)

    def _tipo_plan_activo(self) -> str:
        return "menu_fijo" if self.btn_menu_fijo.isChecked() else "con_opciones"

    def _on_generar_click(self) -> None:
        if self._cliente_actual is None:
            QMessageBox.warning(self, "Sin cliente", "Selecciona o registra un cliente primero.")
            return

        # Aplicar plantilla al objetivo
        plantilla_lbl = self.combo_plantilla.currentText()
        plantilla_key = PLANTILLAS_POR_LABEL.get(plantilla_lbl, "perdida_grasa")
        objetivo_motor = PLANTILLAS_CLIENTE.get(
            plantilla_key, PLANTILLAS_CLIENTE.get("perdida_grasa", {})
        ).get("objetivo_motor", self._cliente_actual.objetivo)
        self._cliente_actual.objetivo = objetivo_motor
        self._cliente_actual.plantilla_tipo = plantilla_key

        self._ir_a_paso(2)
        self.btn_whatsapp.setEnabled(False)
        self.btn_abrir_carpeta.setEnabled(False)
        self.lbl_resultado.setText("Generando plan nutricional...")
        self.lbl_resultado.setStyleSheet("color: #f2f2f7; font-size: 16px; font-weight: 600;")
        self.lbl_pdf_ruta.setText("")
        self.textbox_log.clear()
        self.progress.reset()
        self.progress.setVisible(True)

        self.btn_generar.setEnabled(False)
        thread = threading.Thread(target=self._procesar_en_hilo, daemon=True)
        thread.start()

    # ── Hilo de procesamiento ─────────────────────────────────────────────────

    def _procesar_en_hilo(self) -> None:
        try:
            self._sig.log_msg.emit("Iniciando cálculo nutricional...")
            self._sig.set_progress.emit(0.1, "Calculando objetivo calórico...")

            cliente = self._cliente_actual
            cliente = MotorNutricional.calcular_motor(cliente)
            self._sig.log_msg.emit(
                f"Objetivo: {cliente.kcal_objetivo:.0f} kcal "
                f"(GET: {cliente.get_total:.0f} kcal)"
            )

            self._sig.set_progress.emit(0.3, "Armando plan de comidas...")

            tipo = self._tipo_plan_activo()
            os.makedirs(CARPETA_PLANES, exist_ok=True)

            if tipo == "con_opciones":
                from core.generador_opciones import ConstructorPlanConOpciones
                from core.exportador_opciones import GeneradorPDFConOpciones

                plan = ConstructorPlanConOpciones.construir(
                    cliente, plan_numero=1,
                    directorio_planes=CARPETA_PLANES,
                    num_opciones_por_macro=3,
                )
                self._sig.set_progress.emit(0.7, "Exportando PDF...")

                fecha = datetime.now().strftime("%Y-%m-%d")
                hora = datetime.now().strftime("%H-%M-%S")
                nombre_san = re.sub(r"[^a-zA-Z0-9_]", "", cliente.nombre.replace(" ", "_"))
                carpeta_cli = Path(CARPETA_SALIDA) / nombre_san
                carpeta_cli.mkdir(parents=True, exist_ok=True)

                ruta_pdf = str(carpeta_cli / f"{nombre_san}_OPCIONES_{fecha}_{hora}.pdf")
                gen = GeneradorPDFConOpciones(ruta_pdf)
                ruta_pdf = gen.generar(cliente, plan)
                if not (ruta_pdf and os.path.exists(ruta_pdf)):
                    ruta_pdf = None

                try:
                    ruta_xl = str(carpeta_cli / f"{nombre_san}_OPCIONES_{fecha}_{hora}.xlsx")
                    ExportadorMultiformato.a_excel(cliente, plan, ruta_xl)
                    self._sig.log_msg.emit(f"Excel: {Path(ruta_xl).name}")
                except Exception as exc:
                    self._sig.log_msg.emit(f"Excel no disponible: {exc}")

            else:
                plan = ConstructorPlanNuevo.construir(
                    cliente, plan_numero=1, directorio_planes=CARPETA_PLANES
                )
                self._sig.set_progress.emit(0.6, "Mostrando preview...")

                self._preview_confirmed = False
                self._preview_event = threading.Event()
                self._sig.show_preview.emit(cliente, plan)
                self._preview_event.wait()

                if not self._preview_confirmed:
                    self._sig.log_msg.emit("Generación cancelada.")
                    self._sig.set_progress.emit(0.0, "Cancelado")
                    self._sig.btn_spinner.emit(False)
                    return

                self._sig.set_progress.emit(0.8, "Exportando PDF...")

                fecha = datetime.now().strftime("%Y-%m-%d")
                hora = datetime.now().strftime("%H-%M-%S")
                nombre_san = re.sub(r"[^a-zA-Z0-9_]", "", cliente.nombre.replace(" ", "_"))
                carpeta_cli = Path(CARPETA_SALIDA) / nombre_san
                carpeta_cli.mkdir(parents=True, exist_ok=True)

                ruta_pdf = str(carpeta_cli / f"{nombre_san}_{fecha}_{hora}.pdf")
                gen = GeneradorPDFProfesional(ruta_pdf)
                ruta_pdf = gen.generar(cliente, plan)
                if not (ruta_pdf and os.path.exists(ruta_pdf)):
                    ruta_pdf = None

                try:
                    ruta_xl = str(carpeta_cli / f"{nombre_san}_{fecha}_{hora}.xlsx")
                    ExportadorMultiformato.a_excel(cliente, plan, ruta_xl)
                    self._sig.log_msg.emit(f"Excel: {Path(ruta_xl).name}")
                except Exception as exc:
                    self._sig.log_msg.emit(f"Excel no disponible: {exc}")

            # Guardar en BD
            if self.gestor_bd:
                try:
                    self.gestor_bd.registrar_cliente(cliente)
                    if ruta_pdf:
                        self.gestor_bd.registrar_plan_generado(
                            cliente, plan, ruta_pdf, tipo_plan=tipo
                        )
                    self._sig.log_msg.emit("Guardado en BD correctamente.")
                except Exception as exc:
                    logger.warning("[PLAN] Error BD: %s", exc)

            self._sig.done.emit(ruta_pdf or "")

        except ValueError as ve:
            self._sig.error_msg.emit(f"Error de validación: {ve}")
        except Exception as exc:
            import traceback
            traceback.print_exc()
            self._sig.error_msg.emit(f"Error inesperado: {exc}")
        finally:
            self._sig.btn_spinner.emit(False)

    # ── Callbacks de señales ──────────────────────────────────────────────────

    def _abrir_preview(self, cliente, plan: dict) -> None:
        from ui_desktop.pyside.ventana_preview import PlanPreviewWindow
        dlg = PlanPreviewWindow(self, cliente, plan)
        result = dlg.exec()
        self._preview_confirmed = (result == dlg.Accepted)
        if self._preview_event:
            self._preview_event.set()

    def _on_done(self, ruta_pdf: str) -> None:
        self._ultimo_pdf = ruta_pdf or None
        self.progress.complete("✓ Plan generado exitosamente")
        self.lbl_resultado.setText("✅  Plan nutricional generado con éxito")
        self.lbl_resultado.setStyleSheet(
            "color: #10b981; font-size: 16px; font-weight: 600;"
        )
        if self._ultimo_pdf:
            self.lbl_pdf_ruta.setText(f"📄  {self._ultimo_pdf}")
            self.btn_abrir_carpeta.setEnabled(True)
            self.btn_whatsapp.setEnabled(
                bool(self._cliente_actual and self._cliente_actual.telefono)
            )
        self.btn_generar.setEnabled(True)

    def _on_error(self, msg: str) -> None:
        self.progress.setVisible(False)
        self.lbl_resultado.setText(f"❌  {msg}")
        self.lbl_resultado.setStyleSheet(
            "color: #ef4444; font-size: 15px; font-weight: 500;"
        )
        self.btn_generar.setEnabled(True)
        QMessageBox.critical(self, "Error", msg)

    def _set_btn_spinner(self, spin: bool) -> None:
        self.btn_generar.setEnabled(not spin)
        self.btn_generar.setText("Procesando..." if spin else "⚡  Generar Plan")

    def _log(self, mensaje: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.textbox_log.appendPlainText(f"[{ts}] {mensaje}")
        self.textbox_log.verticalScrollBar().setValue(
            self.textbox_log.verticalScrollBar().maximum()
        )

    # ── Acciones ──────────────────────────────────────────────────────────────

    def _abrir_carpeta(self) -> None:
        if self._ultimo_pdf and os.path.exists(self._ultimo_pdf):
            abrir_carpeta_pdf(os.path.dirname(self._ultimo_pdf))
        else:
            abrir_carpeta_pdf()

    def _enviar_whatsapp(self) -> None:
        if not self._ultimo_pdf or not os.path.exists(self._ultimo_pdf):
            QMessageBox.critical(self, "Error", "Primero genera el plan.")
            return
        if not self._cliente_actual or not self._cliente_actual.telefono:
            QMessageBox.warning(self, "Sin teléfono", "El cliente no tiene teléfono registrado.")
            return
        tel = self._cliente_actual.telefono
        nombre = self._cliente_actual.nombre
        msg = (
            f"Hola {nombre} 💪 Tu plan nutricional personalizado está listo. "
            "Aquí está tu PDF para que lo revises cuando quieras. ¡Éxito!"
        )
        url = f"https://wa.me/{tel}?text={urllib.parse.quote(msg)}"
        webbrowser.open(url)

    def _reset_wizard(self) -> None:
        """Reinicia el wizard para generar un nuevo plan."""
        self._cliente_actual = None
        self._ultimo_pdf = None
        self.entry_busqueda.clear()
        self._on_buscar_cliente("")
        self.lbl_cliente_info.setText("Sin cliente seleccionado")
        self.form_nuevo.setVisible(False)
        self.resultado_container.setVisible(True)
        self.textbox_log.clear()
        self.progress.reset()
        self.btn_generar.setEnabled(True)
        self._ir_a_paso(0)

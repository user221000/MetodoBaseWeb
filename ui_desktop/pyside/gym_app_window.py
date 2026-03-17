# -*- coding: utf-8 -*-
"""
GymAppWindow — Ventana principal del modo GYM con diseño dark mode premium.

Layout:
    ┌──────────────────────────────────────────────────────────┐
    │  CustomSidebar (240px) │  QStackedWidget (resto)         │
    │  ── PRINCIPAL ──        │  0: DashboardPanel              │
    │   📊 Dashboard          │  1: ClientesPanel               │
    │   👥 Clientes           │  2: GenerarPlanPanel             │
    │   📋 Generar Plan       │                                  │
    │  ── SISTEMA ──          │                                  │
    │   📖 API Docs           │                                  │
    │   ─────────────         │                                  │
    │   [usuario footer]      │                                  │
    └─────────────────────────────────────────────────────────-┘
"""
from __future__ import annotations

import os
import webbrowser
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QMainWindow,
    QStackedWidget, QWidget,
)

from core.branding import branding
from src.gestor_bd import GestorBDClientes
from ui_desktop.pyside.dashboard_panel import DashboardPanel
from ui_desktop.pyside.clientes_panel import ClientesPanel
from ui_desktop.pyside.generar_plan_panel import GenerarPlanPanel
from ui_desktop.pyside.suscripciones_panel import SuscripcionesPanel
from ui_desktop.pyside.clases_panel import ClasesPanel
from ui_desktop.pyside.instructores_panel import InstructoresPanel
from ui_desktop.pyside.facturacion_panel import FacturacionPanel
from ui_desktop.pyside.reportes_panel_gym import ReportesPanelGym
from ui_desktop.pyside.configuracion_panel import ConfiguracionPanel
from ui_desktop.pyside.widgets.sidebar import CustomSidebar
from utils.logger import logger

_VERDE_PREMIUM_QSS = Path(__file__).parent / "styles" / "verde_premium.qss"

# Mapa page_id → índice en QStackedWidget
_PAGE_INDEX = {
    "dashboard":      0,
    "clientes":       1,
    "generar_plan":   2,
    "suscripciones":  3,
    "clases":         4,
    "instructores":   5,
    "facturacion":    6,
    "reportes":       7,
    "configuracion":  8,
}


class GymAppWindow(QMainWindow):
    """Ventana principal GYM con sidebar + stacked panels."""

    def __init__(self):
        super().__init__()

        # Aplicar tema verde premium a toda la aplicación
        if _VERDE_PREMIUM_QSS.exists():
            app = QApplication.instance()
            if app:
                app.setStyleSheet(_VERDE_PREMIUM_QSS.read_text(encoding="utf-8"))
                logger.info("[THEME] verde_premium.qss aplicado")

        # Gestor de BD compartido
        try:
            self._db = GestorBDClientes()
        except Exception as exc:
            logger.error("[DB] Error al inicializar BD: %s", exc)
            self._db = None

        # Configuración de la ventana
        nombre = branding.get("nombre_gym", "Método Base")
        self.setWindowTitle(f"{nombre} — Sistema Nutricional v2.0")
        self.setMinimumSize(1100, 720)
        self.resize(1280, 800)

        self._build_ui()
        self._conectar_senales()
        self._setup_shortcuts()

        # Mostrar dashboard al iniciar
        self._navegar("dashboard")

    # ── Construcción ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        central.setStyleSheet("background: #0a1409;")
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Sidebar ───────────────────────────────────────────────────────────
        self._sidebar = CustomSidebar(self)
        main_layout.addWidget(self._sidebar)

        # ── Separador visual ──────────────────────────────────────────────────
        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("background-color: #2a4a2a; border: none; max-width: 1px;")
        main_layout.addWidget(sep)

        # ── Área de contenido (stacked) ───────────────────────────────────────
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: #0a1409;")
        main_layout.addWidget(self._stack)

        # ── Panels ────────────────────────────────────────────────────────────
        self._panel_dashboard = DashboardPanel(gestor_bd=self._db, parent=self)
        self._panel_clientes = ClientesPanel(gestor_bd=self._db, parent=self)
        self._panel_generar = GenerarPlanPanel(gestor_bd=self._db, parent=self)
        self._panel_suscripciones = SuscripcionesPanel(gestor_bd=self._db, parent=self)
        self._panel_clases = ClasesPanel(gestor_bd=self._db, parent=self)
        self._panel_instructores = InstructoresPanel(gestor_bd=self._db, parent=self)
        self._panel_facturacion = FacturacionPanel(gestor_bd=self._db, parent=self)
        self._panel_reportes = ReportesPanelGym(gestor_bd=self._db, parent=self)
        self._panel_configuracion = ConfiguracionPanel(gestor_bd=self._db, parent=self)

        self._stack.addWidget(self._panel_dashboard)       # 0
        self._stack.addWidget(self._panel_clientes)        # 1
        self._stack.addWidget(self._panel_generar)         # 2
        self._stack.addWidget(self._panel_suscripciones)   # 3
        self._stack.addWidget(self._panel_clases)          # 4
        self._stack.addWidget(self._panel_instructores)    # 5
        self._stack.addWidget(self._panel_facturacion)     # 6
        self._stack.addWidget(self._panel_reportes)        # 7
        self._stack.addWidget(self._panel_configuracion)   # 8

    def _conectar_senales(self) -> None:
        # Sidebar → stacked
        self._sidebar.navigation_changed.connect(self._navegar)

        # Dashboard → otros paneles
        self._panel_dashboard._btn_nuevo_plan.clicked.disconnect()
        self._panel_dashboard._btn_nuevo_plan.clicked.connect(
            lambda: self._navegar("generar_plan")
        )
        # El botón "Ver clientes" del dashboard
        for btn in self._panel_dashboard.findChildren(
            type(self._panel_dashboard._btn_nuevo_plan)
        ):
            if btn.objectName() == "secondaryButton":
                btn.clicked.connect(lambda: self._navegar("clientes"))
                break

        # Clientes → Generar plan
        self._panel_clientes.generar_plan_para.connect(self._generar_plan_para_cliente)

        # Generar plan → navegación
        self._panel_generar.navigate_to.connect(self._navegar)

    def _setup_shortcuts(self) -> None:
        # Ctrl+Shift+A → panel admin (heredado del MainWindow original)
        sc = QShortcut(QKeySequence("Ctrl+Shift+A"), self)
        sc.activated.connect(self._abrir_admin)

        # Ctrl+1, Ctrl+2, Ctrl+3 → navegación rápida
        QShortcut(QKeySequence("Ctrl+1"), self).activated.connect(
            lambda: self._navegar("dashboard")
        )
        QShortcut(QKeySequence("Ctrl+2"), self).activated.connect(
            lambda: self._navegar("clientes")
        )
        QShortcut(QKeySequence("Ctrl+3"), self).activated.connect(
            lambda: self._navegar("generar_plan")
        )

    # ── Navegación ────────────────────────────────────────────────────────────

    def _navegar(self, page_id: str) -> None:
        idx = _PAGE_INDEX.get(page_id)
        if idx is None:
            # API Docs → abrir navegador
            if page_id == "api_docs":
                self._abrir_api_docs()
            return

        self._stack.setCurrentIndex(idx)
        self._sidebar.set_active_page(page_id)

        # Refrescar datos al cambiar de panel
        panel_map = {
            "dashboard": self._panel_dashboard,
            "clientes": self._panel_clientes,
            "suscripciones": self._panel_suscripciones,
            "clases": self._panel_clases,
            "instructores": self._panel_instructores,
            "facturacion": self._panel_facturacion,
            "reportes": self._panel_reportes,
            "configuracion": self._panel_configuracion,
        }
        panel = panel_map.get(page_id)
        if panel and hasattr(panel, "refresh"):
            QTimer.singleShot(100, panel.refresh)

        logger.info("[NAV] Panel activo: %s", page_id)

    def _generar_plan_para_cliente(self, cliente: dict) -> None:
        """Navega al panel de generar plan con el cliente pre-cargado."""
        self._navegar("generar_plan")
        QTimer.singleShot(50, lambda: self._panel_generar.iniciar_con_cliente(cliente))

    # ── Acciones adicionales ──────────────────────────────────────────────────

    def _abrir_api_docs(self) -> None:
        webbrowser.open("http://localhost:8000/docs")

    def _abrir_admin(self) -> None:
        try:
            from ui_desktop.pyside.ventana_admin import VentanaAdmin
            dlg = VentanaAdmin(self)
            dlg.exec()
        except Exception as exc:
            logger.warning("[ADMIN] No se pudo abrir panel admin: %s", exc)

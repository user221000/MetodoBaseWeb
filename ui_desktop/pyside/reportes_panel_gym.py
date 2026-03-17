# -*- coding: utf-8 -*-
"""
ReportesPanelGym — Módulo de reportes y estadísticas del gimnasio.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from ui_desktop.pyside.widgets.kpi_card import KPICard
from utils.logger import logger


class ReportesPanelGym(QWidget):
    """Panel de reportes y estadísticas financieras y operativas."""

    def __init__(self, gestor_bd=None, parent=None):
        super().__init__(parent)
        self.gestor_bd = gestor_bd
        self._setup_ui()

    def _setup_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        root_layout.addWidget(scroll)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        self._layout = QVBoxLayout(content)
        self._layout.setContentsMargins(32, 24, 32, 32)
        self._layout.setSpacing(24)
        scroll.setWidget(content)

        self._crear_header()
        self._crear_kpis()
        self._crear_graficos_placeholder()

    def _crear_header(self) -> None:
        header = QFrame()
        header.setObjectName("headerFrame")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 16)

        left = QVBoxLayout()
        left.setSpacing(4)
        title = QLabel("Reportes")
        title.setObjectName("pageTitle")
        left.addWidget(title)
        subtitle = QLabel("Estadísticas y análisis del gimnasio")
        subtitle.setObjectName("pageSubtitle")
        left.addWidget(subtitle)
        layout.addLayout(left)
        layout.addStretch()

        btn_exportar = QPushButton("📥  Exportar")
        btn_exportar.setObjectName("secondaryButton")
        btn_exportar.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(btn_exportar)

        self._layout.addWidget(header)

    def _crear_kpis(self) -> None:
        row = QHBoxLayout()
        row.setSpacing(16)

        self.kpi_clientes_total = KPICard("purple", "👥", 0, "CLIENTES TOTALES", "Registrados", "neutral")
        self.kpi_planes_mes = KPICard("blue", "📋", 0, "PLANES / MES", "Generados", "neutral")
        self.kpi_tasa_retencion = KPICard("cyan", "📈", 0, "RETENCIÓN %", "Tasa mensual", "up")
        self.kpi_ingresos = KPICard("yellow", "💰", 0, "INGRESOS", "Este mes", "neutral")

        row.addWidget(self.kpi_clientes_total)
        row.addWidget(self.kpi_planes_mes)
        row.addWidget(self.kpi_tasa_retencion)
        row.addWidget(self.kpi_ingresos)

        self._layout.addLayout(row)

    def _crear_graficos_placeholder(self) -> None:
        """Sección de gráficos — placeholder para integración futura."""
        container = QFrame()
        container.setObjectName("chartContainer")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("Análisis")
        title.setObjectName("chartTitle")
        layout.addWidget(title)

        placeholder = QLabel("📊 Los gráficos de análisis estarán disponibles próximamente.")
        placeholder.setObjectName("chartSubtitle")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setMinimumHeight(200)
        layout.addWidget(placeholder)

        self._layout.addWidget(container)

    def refresh(self) -> None:
        """Recarga datos de reportes."""
        logger.info("📈 Refrescando panel de reportes")

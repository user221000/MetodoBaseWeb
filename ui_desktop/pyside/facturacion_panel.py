# -*- coding: utf-8 -*-
"""
FacturacionPanel — Módulo de facturación e inventario del gimnasio.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QHeaderView, QLabel,
    QPushButton, QScrollArea, QTableWidget,
    QVBoxLayout, QWidget,
)

from ui_desktop.pyside.widgets.kpi_card import KPICard
from utils.logger import logger


class FacturacionPanel(QWidget):
    """Panel de facturación, pagos y finanzas."""

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
        self._crear_tabla()

    def _crear_header(self) -> None:
        header = QFrame()
        header.setObjectName("headerFrame")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 16)

        left = QVBoxLayout()
        left.setSpacing(4)
        title = QLabel("Facturación")
        title.setObjectName("pageTitle")
        left.addWidget(title)
        subtitle = QLabel("Control de pagos, ingresos y egresos")
        subtitle.setObjectName("pageSubtitle")
        left.addWidget(subtitle)
        layout.addLayout(left)
        layout.addStretch()

        btn_nuevo = QPushButton("  + Nuevo Cobro")
        btn_nuevo.setObjectName("primaryButton")
        btn_nuevo.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(btn_nuevo)

        self._layout.addWidget(header)

    def _crear_kpis(self) -> None:
        row = QHBoxLayout()
        row.setSpacing(16)

        self.kpi_ingresos = KPICard("cyan", "💰", 0, "INGRESOS MES", "Total cobrado", "neutral")
        self.kpi_pendientes = KPICard("yellow", "⏳", 0, "PAGOS PENDIENTES", "Por cobrar", "neutral")
        self.kpi_clientes_al_dia = KPICard("purple", "✅", 0, "AL DÍA", "Clientes activos", "up")

        row.addWidget(self.kpi_ingresos)
        row.addWidget(self.kpi_pendientes)
        row.addWidget(self.kpi_clientes_al_dia)

        self._layout.addLayout(row)

    def _crear_tabla(self) -> None:
        container = QFrame()
        container.setObjectName("chartContainer")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("Últimos Movimientos")
        title.setObjectName("chartTitle")
        layout.addWidget(title)

        self._tabla = QTableWidget(0, 5)
        self._tabla.setHorizontalHeaderLabels(
            ["Fecha", "Cliente", "Concepto", "Monto", "Estado"]
        )
        self._tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._tabla.setAlternatingRowColors(True)
        self._tabla.verticalHeader().setVisible(False)
        self._tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self._tabla)

        self._layout.addWidget(container)

    def refresh(self) -> None:
        """Recarga datos de facturación."""
        logger.info("💰 Refrescando panel de facturación")

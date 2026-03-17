# -*- coding: utf-8 -*-
"""
SuscripcionesPanel — Módulo de gestión de suscripciones y membresías.
"""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QHeaderView, QLabel,
    QPushButton, QScrollArea, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from utils.logger import logger


class SuscripcionesPanel(QWidget):
    """Panel de gestión de suscripciones y membresías del gimnasio."""

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
        self._crear_resumen()
        self._crear_tabla()

    def _crear_header(self) -> None:
        header = QFrame()
        header.setObjectName("headerFrame")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 16)

        left = QVBoxLayout()
        left.setSpacing(4)
        title = QLabel("Suscripciones")
        title.setObjectName("pageTitle")
        left.addWidget(title)
        subtitle = QLabel("Gestión de membresías y planes de pago")
        subtitle.setObjectName("pageSubtitle")
        left.addWidget(subtitle)
        layout.addLayout(left)
        layout.addStretch()

        btn_nueva = QPushButton("  + Nueva Suscripción")
        btn_nueva.setObjectName("primaryButton")
        btn_nueva.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(btn_nueva)

        self._layout.addWidget(header)

    def _crear_resumen(self) -> None:
        """Cards de resumen de suscripciones."""
        row = QHBoxLayout()
        row.setSpacing(16)

        for label, valor, tag_name in [
            ("ACTIVAS", "0", "tagSubActiva"),
            ("VENCIDAS", "0", "tagSubVencida"),
            ("PENDIENTES", "0", "tagSubPendiente"),
        ]:
            card = QFrame()
            card.setObjectName("kpiCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(24, 24, 24, 20)

            v = QLabel(valor)
            v.setObjectName("kpiValue")
            card_layout.addWidget(v)

            l = QLabel(label)
            l.setObjectName("kpiLabel")
            card_layout.addWidget(l)

            tag = QLabel("●")
            tag.setObjectName(tag_name)
            card_layout.addWidget(tag)

            card_layout.addStretch()
            row.addWidget(card)

        self._layout.addLayout(row)

    def _crear_tabla(self) -> None:
        container = QFrame()
        container.setObjectName("chartContainer")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("Suscripciones Recientes")
        title.setObjectName("chartTitle")
        layout.addWidget(title)

        self._tabla = QTableWidget(0, 5)
        self._tabla.setHorizontalHeaderLabels(
            ["Cliente", "Plan", "Inicio", "Vencimiento", "Estado"]
        )
        self._tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._tabla.setAlternatingRowColors(True)
        self._tabla.verticalHeader().setVisible(False)
        self._tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self._tabla)

        self._layout.addWidget(container)

    def refresh(self) -> None:
        """Recarga datos de suscripciones."""
        logger.info("📋 Refrescando panel de suscripciones")

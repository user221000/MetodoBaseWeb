# -*- coding: utf-8 -*-
"""
ConfiguracionPanel — Módulo de configuración del sistema.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from utils.logger import logger


class ConfiguracionPanel(QWidget):
    """Panel de configuración del gimnasio y preferencias del sistema."""

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
        self._crear_seccion_gym()
        self._crear_seccion_sistema()

    def _crear_header(self) -> None:
        header = QFrame()
        header.setObjectName("headerFrame")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 16)

        left = QVBoxLayout()
        left.setSpacing(4)
        title = QLabel("Configuración")
        title.setObjectName("pageTitle")
        left.addWidget(title)
        subtitle = QLabel("Preferencias del gimnasio y sistema")
        subtitle.setObjectName("pageSubtitle")
        left.addWidget(subtitle)
        layout.addLayout(left)
        layout.addStretch()

        self._layout.addWidget(header)

    def _crear_seccion_gym(self) -> None:
        container = QFrame()
        container.setObjectName("formCard")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("Datos del Gimnasio")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        for label_text in ["Nombre del Gimnasio", "Dirección", "Teléfono", "Email"]:
            lbl = QLabel(label_text)
            lbl.setObjectName("fieldLabel")
            layout.addWidget(lbl)
            inp = QLineEdit()
            inp.setPlaceholderText(f"Ingresa {label_text.lower()}")
            layout.addWidget(inp)

        btn_guardar = QPushButton("💾  Guardar Cambios")
        btn_guardar.setObjectName("primaryButton")
        btn_guardar.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(btn_guardar)

        self._layout.addWidget(container)

    def _crear_seccion_sistema(self) -> None:
        container = QFrame()
        container.setObjectName("formCard")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("Sistema")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        btn_admin = QPushButton("⚙️  Panel de Administración")
        btn_admin.setObjectName("secondaryButton")
        btn_admin.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_admin.clicked.connect(self._abrir_admin)
        layout.addWidget(btn_admin)

        btn_backup = QPushButton("📦  Crear Backup")
        btn_backup.setObjectName("secondaryButton")
        btn_backup.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(btn_backup)

        self._layout.addWidget(container)

    def _abrir_admin(self) -> None:
        try:
            from ui_desktop.pyside.ventana_admin import VentanaAdmin
            dlg = VentanaAdmin(self)
            dlg.exec()
        except Exception as exc:
            logger.warning("⚠️ No se pudo abrir panel admin: %s", exc)

    def refresh(self) -> None:
        """Recarga configuración."""
        logger.info("⚙️ Refrescando panel de configuración")

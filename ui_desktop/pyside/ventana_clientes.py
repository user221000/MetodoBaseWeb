# -*- coding: utf-8 -*-
"""
Ventana de gestión de clientes — PySide6.
Reemplaza gui/ventana_clientes.py.
"""

import csv
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFileDialog, QApplication, QWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from core.exportador_multi import filtrar_campos_cliente_export
from src.gestor_bd import GestorBDClientes
from utils.logger import logger


_COLS = [
    ("Nombre",             "nombre"),
    ("Teléfono",           "telefono"),
    ("Edad",               "edad"),
    ("Peso (kg)",          "peso"),
    ("Objetivo",           "objetivo"),
    ("Planes",             "total_planes"),
    ("Último plan",        "ultimo_plan"),
]


class VentanaClientes(QDialog):
    """Listado y búsqueda de clientes del gimnasio."""

    def __init__(self, parent=None, gestor_bd=None):
        super().__init__(parent)
        self.setWindowTitle("Gestión de Clientes — Método Base")
        self.resize(920, 680)
        self.setModal(True)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        self.gestor_bd = gestor_bd if gestor_bd is not None else GestorBDClientes()

        self._build_ui()
        self._cargar_clientes()
        logger.info("[CLIENTES] Ventana clientes abierta")

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(10)

        # Header
        hdr = QFrame()
        hdr.setStyleSheet(
            "QFrame { background-color: #1A1A1A; border-radius: 10px; border: none; }"
        )
        hdr.setFixedHeight(68)
        hl = QVBoxLayout(hdr)
        hl.setAlignment(Qt.AlignCenter)
        t = QLabel("👥  Clientes del Gimnasio")
        t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet("color: #9B4FB0; font-size: 20px; font-weight: bold;")
        hl.addWidget(t)
        root.addWidget(hdr)

        # Barra de acciones
        bar = QWidget()
        bar.setStyleSheet("background: transparent;")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(0, 0, 0, 0)
        self.entry_busqueda = QLineEdit()
        self.entry_busqueda.setPlaceholderText("Buscar por nombre, teléfono o ID…")
        self.entry_busqueda.textChanged.connect(self._on_busqueda_cambia)
        bl.addWidget(self.entry_busqueda, 1)
        self.lbl_total = QLabel("")
        self.lbl_total.setStyleSheet("color: #B8B8B8; font-size: 11px;")
        bl.addWidget(self.lbl_total)
        bl.addSpacing(12)
        btn_refresh = QPushButton("🔄 Actualizar")
        btn_refresh.setStyleSheet(
            "QPushButton { background-color: transparent; border: 1px solid #B8B8B8;"
            " color: #B8B8B8; border-radius: 6px; padding: 6px 12px; }"
            "QPushButton:hover { background-color: #1A1A1A; }"
        )
        btn_refresh.clicked.connect(self._cargar_clientes)
        bl.addWidget(btn_refresh)
        btn_csv = QPushButton("📊 Exportar CSV")
        btn_csv.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: #FFFFFF;"
            " border-radius: 6px; padding: 6px 12px; }"
            "QPushButton:hover { background-color: #43A047; }"
        )
        btn_csv.clicked.connect(self._exportar_csv)
        bl.addWidget(btn_csv)
        root.addWidget(bar)

        # Tabla
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(len(_COLS))
        self.tabla.setHorizontalHeaderLabels([c[0] for c in _COLS])
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setStyleSheet(
            "QTableWidget { background-color: #0D0D0D; border: 1px solid #333333;"
            " border-radius: 8px; gridline-color: #2A2A2A; }"
            "QTableWidget::item { color: #F5F5F5; padding: 6px; }"
            "QTableWidget::item:selected { background-color: #9B4FB0; }"
            "QHeaderView::section { background-color: #1A1A1A; color: #D4A84B;"
            " border: none; padding: 6px; font-weight: bold; }"
        )
        root.addWidget(self.tabla, 1)

        # Footer
        ftr = QWidget()
        ftr.setStyleSheet("background: transparent;")
        fl = QHBoxLayout(ftr)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.addStretch()
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setStyleSheet(
            "QPushButton { background-color: transparent; border: 1px solid #B8B8B8;"
            " color: #B8B8B8; border-radius: 6px; padding: 6px 20px; }"
            "QPushButton:hover { background-color: #1A1A1A; }"
        )
        btn_cerrar.clicked.connect(self.accept)
        fl.addWidget(btn_cerrar)
        root.addWidget(ftr)

    # ------------------------------------------------------------------
    # Lógica
    # ------------------------------------------------------------------

    def _cargar_clientes(self, query: str = "") -> None:
        try:
            if query.strip():
                clientes = self.gestor_bd.buscar_clientes(query.strip())
            else:
                clientes = self.gestor_bd.obtener_todos_clientes()
        except Exception as exc:
            logger.error("[CLIENTES] Error al cargar clientes: %s", exc)
            QMessageBox.critical(self, "Error", f"Error al cargar clientes:\n{exc}")
            return

        self._poblar_tabla(clientes or [])

    def _on_busqueda_cambia(self, text: str) -> None:
        self._cargar_clientes(query=text)

    def _poblar_tabla(self, clientes: list) -> None:
        self.tabla.setRowCount(0)
        self.tabla.setRowCount(len(clientes))
        for row, cli in enumerate(clientes):
            for col, (_, key) in enumerate(_COLS):
                val = cli.get(key, "")
                item = QTableWidgetItem(str(val) if val is not None else "")
                item.setForeground(QColor("#F5F5F5"))
                self.tabla.setItem(row, col, item)

        total = len(clientes)
        self.lbl_total.setText(f"{total} cliente{'s' if total != 1 else ''}")

    def _exportar_csv(self) -> None:
        if not self._confirmar_exportacion():
            return
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Exportar CSV", "clientes.csv", "CSV (*.csv)"
        )
        if not ruta:
            return
        try:
            with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                # Solo encabezados de campos públicos permitidos
                writer.writerow([c[0] for c in _COLS])
                for row in range(self.tabla.rowCount()):
                    writer.writerow([
                        (self.tabla.item(row, col).text() if self.tabla.item(row, col) else "")
                        for col in range(len(_COLS))
                    ])
            QMessageBox.information(self, "Exportado", f"CSV guardado en:\n{ruta}")
            logger.info("[CLIENTES] CSV exportado (campos públicos): %s", ruta)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No se pudo exportar:\n{exc}")

    def _confirmar_exportacion(self) -> bool:
        """Muestra aviso de privacidad obligatorio antes de cualquier exportación."""
        aviso = QMessageBox(self)
        aviso.setWindowTitle("⚠️  Aviso de Privacidad — Exportación")
        aviso.setIcon(QMessageBox.Warning)
        aviso.setText(
            "<b>Estás a punto de exportar datos de clientes.</b>"
        )
        aviso.setInformativeText(
            "<ul>"
            "<li>Solo se incluyen <b>campos públicos</b> (nombre, edad, peso, objetivo).</li>"
            "<li><b>No</b> se exportan contraseñas, hashes, tokens cifrados ni emails.</li>"
            "<li>El archivo exportado <b>no estará cifrado</b>; guárdalo en un lugar seguro.</li>"
            "<li>Comparte este archivo solo con personas autorizadas.</li>"
            "</ul>"
            "¿Deseas continuar con la exportación?"
        )
        aviso.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        aviso.setDefaultButton(QMessageBox.Cancel)
        aviso.button(QMessageBox.Yes).setText("Sí, exportar")
        aviso.button(QMessageBox.Cancel).setText("Cancelar")
        return aviso.exec() == QMessageBox.Yes

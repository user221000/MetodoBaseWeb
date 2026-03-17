# -*- coding: utf-8 -*-
"""
Panel Dashboard — Métricas KPI, gráficos y tabla de clientes recientes.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
    QPushButton, QScrollArea, QSizePolicy, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from src.gestor_bd import GestorBDClientes
from ui_desktop.pyside.widgets.kpi_card import KPICard
from ui_desktop.pyside.widgets.charts import LineChartWidget, DonutChartWidget
from ui_desktop.pyside.widgets.avatar_widget import AvatarWidget
from utils.logger import logger

_MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]
_DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


class DashboardPanel(QWidget):
    """Panel principal del dashboard con KPIs, gráficos y clientes recientes."""

    def __init__(self, gestor_bd: GestorBDClientes | None = None, parent=None):
        super().__init__(parent)
        self.gestor_bd = gestor_bd or GestorBDClientes()
        self._setup_ui()
        # Cargar datos con small delay para que la ventana pinte primero
        QTimer.singleShot(200, self.cargar_datos)

    # ── Construcción ──────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Scroll area para el contenido
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
        self._crear_charts_row()
        self._crear_tabla_clientes()

    def _crear_header(self) -> None:
        header = QFrame()
        header.setObjectName("headerFrame")

        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 16)
        layout.setSpacing(16)

        # Título y fecha
        left = QVBoxLayout()
        left.setSpacing(4)

        title = QLabel("Dashboard")
        title.setObjectName("pageTitle")
        left.addWidget(title)

        now = datetime.now()
        fecha_str = f"{_DIAS[now.weekday()]}, {now.day} de {_MESES[now.month - 1]} de {now.year}"
        subtitle = QLabel(fecha_str)
        subtitle.setObjectName("pageSubtitle")
        left.addWidget(subtitle)

        layout.addLayout(left)
        layout.addStretch()

        # Botones
        btn_ver = QPushButton("Ver clientes")
        btn_ver.setObjectName("secondaryButton")
        btn_ver.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ver.clicked.connect(self._on_ver_clientes)
        layout.addWidget(btn_ver)

        self._btn_nuevo_plan = QPushButton("  + Nuevo Plan")
        self._btn_nuevo_plan.setObjectName("btnNuevoPlan")
        self._btn_nuevo_plan.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_nuevo_plan.clicked.connect(self._on_nuevo_plan)
        layout.addWidget(self._btn_nuevo_plan)

        self._layout.addWidget(header)

    def _crear_kpis(self) -> None:
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(16)

        self.kpi_clientes = KPICard(
            "purple", "👥", 0, "TOTAL CLIENTES", "+0 este mes", "neutral"
        )
        self.kpi_planes = KPICard(
            "blue", "📋", 0, "PLANES / MES", "Este período", "neutral"
        )
        self.kpi_kcal = KPICard(
            "yellow", "🔥", 0, "PROM. KCAL / PLAN", "Objetivo promedio", "neutral"
        )
        self.kpi_activos = KPICard(
            "cyan", "⚡", 0, "ACTIVOS ESTA SEMANA", "Clientes activos", "up"
        )

        kpi_grid.addWidget(self.kpi_clientes, 0, 0)
        kpi_grid.addWidget(self.kpi_planes,   0, 1)
        kpi_grid.addWidget(self.kpi_kcal,     0, 2)
        kpi_grid.addWidget(self.kpi_activos,  0, 3)

        self._layout.addLayout(kpi_grid)

    def _crear_charts_row(self) -> None:
        charts_row = QHBoxLayout()
        charts_row.setSpacing(16)

        # ── Gráfico de línea ──────────────────────────────────────────────────
        line_container = QFrame()
        line_container.setObjectName("chartContainer")
        line_layout = QVBoxLayout(line_container)
        line_layout.setContentsMargins(24, 20, 24, 20)
        line_layout.setSpacing(8)

        lc_title = QLabel("Planes Generados")
        lc_title.setObjectName("chartTitle")
        line_layout.addWidget(lc_title)

        lc_subtitle = QLabel("Evolución de los últimos 7 días")
        lc_subtitle.setObjectName("chartSubtitle")
        line_layout.addWidget(lc_subtitle)

        self.line_chart = LineChartWidget()
        self.line_chart.setMinimumHeight(200)
        line_layout.addWidget(self.line_chart)

        charts_row.addWidget(line_container, 3)

        # ── Gráfico donut ─────────────────────────────────────────────────────
        donut_container = QFrame()
        donut_container.setObjectName("chartContainer")
        donut_layout = QVBoxLayout(donut_container)
        donut_layout.setContentsMargins(24, 20, 24, 20)
        donut_layout.setSpacing(8)

        dc_title = QLabel("Estado de Clientes")
        dc_title.setObjectName("chartTitle")
        donut_layout.addWidget(dc_title)

        dc_subtitle = QLabel("Activos · Inactivos · Planes generados")
        dc_subtitle.setObjectName("chartSubtitle")
        donut_layout.addWidget(dc_subtitle)

        self.donut_chart = DonutChartWidget()
        self.donut_chart.setMinimumHeight(200)
        donut_layout.addWidget(self.donut_chart)

        charts_row.addWidget(donut_container, 2)

        self._layout.addLayout(charts_row)

    def _crear_tabla_clientes(self) -> None:
        container = QFrame()
        container.setObjectName("chartContainer")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # Encabezado
        hdr_row = QHBoxLayout()
        title = QLabel("Clientes Recientes")
        title.setObjectName("chartTitle")
        hdr_row.addWidget(title)

        subtitle = QLabel("Última actividad")
        subtitle.setObjectName("chartSubtitle")
        hdr_row.addWidget(subtitle)
        hdr_row.addStretch()

        btn_todos = QPushButton("Ver todos →")
        btn_todos.setObjectName("secondaryButton")
        btn_todos.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_todos.clicked.connect(self._on_ver_clientes)
        hdr_row.addWidget(btn_todos)

        layout.addLayout(hdr_row)

        # Tabla
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(5)
        self.tabla.setHorizontalHeaderLabels(
            ["CLIENTE", "EDAD / PESO", "OBJETIVO", "ÚLTIMO PLAN", "PLANES"]
        )
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setShowGrid(False)
        self.tabla.setWordWrap(False)

        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla.setMinimumHeight(160)

        layout.addWidget(self.tabla)
        self._layout.addWidget(container)

    # ── Carga de datos ────────────────────────────────────────────────────────

    def cargar_datos(self) -> None:
        """Carga datos reales de la BD y actualiza toda la UI."""
        try:
            ahora = datetime.now()
            inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            inicio_semana = ahora - timedelta(days=ahora.weekday())

            stats = self.gestor_bd.obtener_estadisticas_gym(inicio_mes, ahora)
            stats_semana = self.gestor_bd.obtener_estadisticas_gym(inicio_semana, ahora)

            # KPIs
            total = stats.get("total_clientes", 0)
            nuevos = stats.get("clientes_nuevos", 0)
            planes = stats.get("planes_periodo", 0)
            kcal = int(stats.get("promedio_kcal", 0))
            activos = stats_semana.get("clientes_activos", 0)

            self.kpi_clientes._target_value = total
            self.kpi_clientes._change_label.setText(f"+{nuevos} este mes")
            self.kpi_planes._target_value = planes
            self.kpi_kcal._target_value = kcal
            self.kpi_activos._target_value = activos

            for kpi in [self.kpi_clientes, self.kpi_planes, self.kpi_kcal, self.kpi_activos]:
                kpi.animate_value(900)

            # Gráfico de línea: últimos 7 días
            self._cargar_datos_linea(ahora)

            # Gráfico donut: clientes activos / inactivos / planes del período
            activos_count = total  # total_clientes = activo=1
            planes_mes = planes        # planes en el período
            inactivos_count = 0
            total_planes_bd = 0
            try:
                with sqlite3.connect(self.gestor_bd.db_path) as _conn:
                    _c = _conn.cursor()
                    inactivos_count = _c.execute(
                        "SELECT COUNT(*) FROM clientes WHERE activo=0"
                    ).fetchone()[0]
                    total_planes_bd = _c.execute(
                        "SELECT COUNT(*) FROM planes_generados"
                    ).fetchone()[0]
            except Exception:
                pass

            donut_labels = ["Activos", "Inactivos", "Planes / mes"]
            donut_values = [
                max(float(activos_count), 0.01),
                max(float(inactivos_count), 0.01),
                max(float(planes_mes), 0.01),
            ]
            self.donut_chart.set_data(
                donut_labels,
                donut_values,
                ["#10b981", "#ef4444", "#ffd700"],
            )
            self.donut_chart.set_center_text(
                str(total_planes_bd),
                "planes",
            )

            # Tabla de clientes recientes
            self._cargar_tabla_recientes()

        except Exception as exc:
            logger.error("[DASHBOARD] Error al cargar datos: %s", exc, exc_info=True)

    def _cargar_datos_linea(self, ahora: datetime) -> None:
        """Carga datos de planes de los últimos 7 días para el gráfico de línea."""
        dias_labels = []
        dias_valores = []
        dias_nombres = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

        for i in range(6, -1, -1):
            dia = ahora - timedelta(days=i)
            inicio_dia = dia.replace(hour=0, minute=0, second=0, microsecond=0)
            fin_dia = dia.replace(hour=23, minute=59, second=59, microsecond=999999)
            try:
                planes_dia = self.gestor_bd.obtener_planes_periodo(inicio_dia, fin_dia)
                dias_labels.append(dias_nombres[dia.weekday()])
                dias_valores.append(float(len(planes_dia)))
            except Exception:
                dias_labels.append(dias_nombres[dia.weekday()])
                dias_valores.append(0.0)

        self.line_chart.set_data(dias_labels, dias_valores)

    def _cargar_tabla_recientes(self) -> None:
        """Carga los últimos 5 clientes en la tabla."""
        try:
            clientes = self.gestor_bd.buscar_clientes("", solo_activos=True, limite=8)
        except Exception:
            clientes = []

        _COLORES_OBJ = {
            "deficit": ("#2d3a52", "#4a90e2"),
            "déficit": ("#2d3a52", "#4a90e2"),
            "mantenimiento": ("#4a3d2a", "#feca57"),
            "superavit": ("#3a2d42", "#a855f7"),
            "superávit": ("#3a2d42", "#a855f7"),
        }

        self.tabla.setRowCount(len(clientes))
        self.tabla.setRowCount(min(len(clientes), 8))

        for i, cliente in enumerate(clientes[:8]):
            nombre = cliente.get("nombre", "—")
            edad = cliente.get("edad", "—")
            peso = cliente.get("peso_kg", "—")
            objetivo = cliente.get("objetivo", "—") or "—"
            ultimo = cliente.get("ultimo_plan", "") or ""
            planes = cliente.get("total_planes_generados", 0)

            # Columna 0: nombre con avatar
            nombre_item = QTableWidgetItem(f"  {nombre}")
            nombre_item.setForeground(QColor("#f2f2f7"))  # type: ignore[attr-defined]
            self.tabla.setItem(i, 0, nombre_item)

            # Columna 1: edad / peso
            edad_peso = f"{edad} años / {peso} kg" if edad and peso else "—"
            self.tabla.setItem(i, 1, QTableWidgetItem(edad_peso))

            # Columna 2: objetivo con color
            obj_lower = objetivo.lower()
            colors = _COLORES_OBJ.get(obj_lower, ("#2d2d40", "#8e8e93"))
            obj_item = QTableWidgetItem(f"  {objetivo.capitalize()}  ")
            from PySide6.QtGui import QColor
            obj_item.setForeground(QColor(colors[1]))
            self.tabla.setItem(i, 2, obj_item)

            # Columna 3: último plan
            if ultimo:
                try:
                    dt = datetime.fromisoformat(str(ultimo)[:19])
                    ultimo_str = dt.strftime("%d/%m/%Y")
                except Exception:
                    ultimo_str = str(ultimo)[:10]
            else:
                ultimo_str = "Sin planes"
            self.tabla.setItem(i, 3, QTableWidgetItem(ultimo_str))

            # Columna 4: total planes
            planes_item = QTableWidgetItem(str(planes))
            planes_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla.setItem(i, 4, planes_item)

            self.tabla.setRowHeight(i, 48)

    # ── Señales externas (conectadas desde GymAppWindow) ─────────────────────

    def _on_ver_clientes(self) -> None:
        # Será conectado por GymAppWindow
        pass

    def _on_nuevo_plan(self) -> None:
        # Será conectado por GymAppWindow
        pass

    def set_on_ver_clientes(self, callback) -> None:
        self._btn_nuevo_plan.clicked.disconnect()
        # Re-asignar
        pass

    def refresh(self) -> None:
        """Recarga todos los datos del panel."""
        self.cargar_datos()


# Importación necesaria para evitar NameError en el método _cargar_tabla_recientes
from PySide6.QtGui import QColor  # noqa: E402, F401

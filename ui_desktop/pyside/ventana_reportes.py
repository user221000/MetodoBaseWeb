# -*- coding: utf-8 -*-
"""
Ventana de reportes — PySide6 + matplotlib QtAgg.
Reemplaza gui/ventana_reportes.py.
"""

from datetime import datetime, timedelta

try:
    import matplotlib
    matplotlib.use("QtAgg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    _MPL_OK = True
except Exception:
    _MPL_OK = False

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTabWidget, QWidget, QScrollArea, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFileDialog, QGridLayout,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from src.gestor_bd import GestorBDClientes
from utils.logger import logger


_PERIODOS = {
    "Últimos 7 días":   7,
    "Últimos 30 días":  30,
    "Últimos 90 días":  90,
    "Último año":       365,
    "Todo el tiempo":   None,
}


class VentanaReportes(QDialog):
    """Panel de reportes y métricas del gimnasio."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reportes — Método Base")
        self.resize(1020, 760)
        self.setModal(True)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        self.gestor_bd = GestorBDClientes()
        self._datos: dict = {}

        self._build_ui()
        self._actualizar()
        logger.info("[REPORTES] Ventana reportes abierta")

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
        t = QLabel("📊  Reportes del Gimnasio")
        t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet("color: #9B4FB0; font-size: 20px; font-weight: bold;")
        hl.addWidget(t)
        root.addWidget(hdr)

        # Toolbar
        bar = QWidget()
        bar.setStyleSheet("background: transparent;")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(0, 0, 0, 0)
        self.combo_periodo = QComboBox()
        self.combo_periodo.addItems(list(_PERIODOS.keys()))
        self.combo_periodo.setCurrentIndex(1)   # 30 días
        bl.addWidget(QLabel("Período:"))
        bl.addWidget(self.combo_periodo)
        bl.addSpacing(16)
        btn_act = QPushButton("🔄 Actualizar")
        btn_act.clicked.connect(self._actualizar)
        bl.addWidget(btn_act)
        btn_exp = QPushButton("📤 Exportar")
        btn_exp.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: #FFFFFF;"
            " border-radius: 6px; padding: 6px 14px; }"
            "QPushButton:hover { background-color: #43A047; }"
        )
        btn_exp.clicked.connect(self._exportar)
        bl.addWidget(btn_exp)
        bl.addStretch()
        root.addWidget(bar)

        # Tabs
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        self._crear_tab_dashboard()
        self._crear_tab_graficas()
        self._crear_tab_clientes()

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
        )
        btn_cerrar.clicked.connect(self.accept)
        fl.addWidget(btn_cerrar)
        root.addWidget(ftr)

    # ------------------------------------------------------------------
    # Pestaña Dashboard (KPIs)
    # ------------------------------------------------------------------

    def _crear_tab_dashboard(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        inner = QWidget()
        self.dash_layout = QVBoxLayout(inner)
        self.dash_layout.setContentsMargins(20, 20, 20, 20)
        self.dash_layout.setSpacing(16)
        scroll.setWidget(inner)
        self.tabs.addTab(scroll, "📋 Dashboard")

    def _poblar_dashboard(self) -> None:
        # Limpiar anterior
        while self.dash_layout.count():
            item = self.dash_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        d = self._datos
        kpis = [
            ("👥 Total Clientes",          d.get("total_clientes", 0),           "#9B4FB0"),
            ("📈 Clientes Nuevos",          d.get("clientes_nuevos", 0),          "#D4A84B"),
            ("🍽️ Planes Generados",         d.get("planes_generados", 0),         "#4CAF50"),
            ("⚡ Promedio Kcal / Plan",     f"{d.get('promedio_kcal', 0):.0f}",   "#2196F3"),
            ("💪 Objetivo + Común",         d.get("objetivo_comun", "—"),         "#9B4FB0"),
            ("🕐 Planes (período)",          d.get("planes_periodo", 0),           "#D4A84B"),
        ]

        grid = QGridLayout()
        grid.setSpacing(12)
        for i, (titulo, valor, color) in enumerate(kpis):
            f = QFrame()
            f.setStyleSheet(
                f"QFrame {{ background-color: #1A1A1A; border-radius: 10px; border: none; }}"
            )
            fl = QVBoxLayout(f)
            fl.setContentsMargins(16, 14, 16, 14)
            fl.setSpacing(4)
            tl = QLabel(titulo)
            tl.setAlignment(Qt.AlignCenter)
            tl.setStyleSheet("color: #B8B8B8; font-size: 12px;")
            fl.addWidget(tl)
            vl = QLabel(str(valor))
            vl.setAlignment(Qt.AlignCenter)
            vl.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: bold;")
            fl.addWidget(vl)
            grid.addWidget(f, i // 3, i % 3)
        self.dash_layout.addLayout(grid)

        # Distribución de objetivos
        obj_dist = d.get("distribucion_objetivos", {})
        if obj_dist:
            t = QLabel("📊  Distribución de Objetivos")
            t.setStyleSheet("color: #D4A84B; font-size: 14px; font-weight: bold;")
            self.dash_layout.addWidget(t)
            for objetivo, cnt in sorted(obj_dist.items(), key=lambda x: -x[1])[:8]:
                row = QWidget()
                row.setStyleSheet("background: transparent;")
                rl = QHBoxLayout(row)
                rl.setContentsMargins(0, 0, 0, 0)
                lbl = QLabel(f"• {objetivo}")
                lbl.setStyleSheet("color: #F5F5F5; font-size: 12px;")
                rl.addWidget(lbl, 1)
                cnt_lbl = QLabel(str(cnt))
                cnt_lbl.setStyleSheet("color: #9B4FB0; font-size: 12px; font-weight: bold;")
                rl.addWidget(cnt_lbl)
                self.dash_layout.addWidget(row)

        self.dash_layout.addStretch()

    # ------------------------------------------------------------------
    # Pestaña Gráficas
    # ------------------------------------------------------------------

    def _crear_tab_graficas(self) -> None:
        w = QWidget()
        self.graficas_layout = QVBoxLayout(w)
        self.graficas_layout.setContentsMargins(4, 4, 4, 4)
        self.tabs.addTab(w, "📈 Gráficas")
        self._canvas_clientes = None
        self._canvas_objetivos = None

    def _poblar_graficas(self) -> None:
        if not _MPL_OK:
            lbl = QLabel("matplotlib no disponible — instala con: pip install matplotlib")
            lbl.setStyleSheet("color: #F44336;")
            self.graficas_layout.addWidget(lbl)
            return

        # Limpiar
        while self.graficas_layout.count():
            item = self.graficas_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        plt.style.use("dark_background")
        d = self._datos

        # Gráfica 1: evolución de clientes nuevos (simplificada como barras)
        clientes_x = list(range(1, 8))
        clientes_y = d.get("clientes_nuevos_semana", [0] * 7)

        fig, axes = plt.subplots(1, 2, figsize=(9, 3.5))
        fig.patch.set_facecolor("#0D0D0D")

        axes[0].bar(
            clientes_x, clientes_y[:7] if len(clientes_y) >= 7 else clientes_y + [0] * (7 - len(clientes_y)),
            color="#9B4FB0", edgecolor="#1A1A1A"
        )
        axes[0].set_title("Nuevos clientes (últimos 7 días)", color="#F5F5F5", fontsize=10)
        axes[0].set_facecolor("#1A1A1A")
        axes[0].tick_params(colors="#B8B8B8")

        obj_dist = d.get("distribucion_objetivos", {})
        if obj_dist:
            labels = list(obj_dist.keys())[:6]
            vals   = [obj_dist[k] for k in labels]
            axes[1].pie(vals, labels=labels, autopct="%1.0f%%",
                        colors=["#9B4FB0", "#D4A84B", "#4CAF50", "#2196F3", "#FF9800", "#E91E63"],
                        textprops={"color": "#F5F5F5", "fontsize": 8})
            axes[1].set_title("Distribución de objetivos", color="#F5F5F5", fontsize=10)
        else:
            axes[1].text(0.5, 0.5, "Sin datos", ha="center", va="center", color="#B8B8B8")

        fig.tight_layout(pad=1.5)
        canvas = FigureCanvas(fig)
        canvas.setMinimumHeight(280)
        self.graficas_layout.addWidget(canvas)
        self.graficas_layout.addStretch()

    # ------------------------------------------------------------------
    # Pestaña Clientes recientes
    # ------------------------------------------------------------------

    def _crear_tab_clientes(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        inner = QWidget()
        self.clientes_tab_layout = QVBoxLayout(inner)
        self.clientes_tab_layout.setContentsMargins(12, 12, 12, 12)
        scroll.setWidget(inner)
        self.tabs.addTab(scroll, "👥 Clientes")

        self.tabla_cli = QTableWidget()
        self.tabla_cli.setColumnCount(5)
        self.tabla_cli.setHorizontalHeaderLabels(["Nombre", "Teléfono", "Objetivo", "Peso (kg)", "Último plan"])
        self.tabla_cli.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tabla_cli.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla_cli.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla_cli.setAlternatingRowColors(True)
        self.tabla_cli.setStyleSheet(
            "QTableWidget { background-color: #0D0D0D; border: 1px solid #333;"
            " border-radius: 8px; gridline-color: #2A2A2A; }"
            "QTableWidget::item { color: #F5F5F5; padding: 6px; }"
            "QTableWidget::item:selected { background-color: #9B4FB0; }"
            "QHeaderView::section { background-color: #1A1A1A; color: #D4A84B;"
            " border: none; padding: 6px; font-weight: bold; }"
        )
        self.clientes_tab_layout.addWidget(self.tabla_cli, 1)

    def _poblar_tabla_clientes(self) -> None:
        clientes = self._datos.get("clientes_recientes", [])
        self.tabla_cli.setRowCount(0)
        self.tabla_cli.setRowCount(len(clientes))
        for row, cli in enumerate(clientes):
            for col, key in enumerate(["nombre", "telefono", "objetivo", "peso", "ultimo_plan"]):
                val = cli.get(key, "")
                item = QTableWidgetItem(str(val) if val is not None else "")
                item.setForeground(QColor("#F5F5F5"))
                self.tabla_cli.setItem(row, col, item)

    # ------------------------------------------------------------------
    # Actualizar datos
    # ------------------------------------------------------------------

    def _actualizar(self) -> None:
        periodo_nombre = self.combo_periodo.currentText()
        dias = _PERIODOS.get(periodo_nombre)
        fecha_inicio = None
        if dias:
            fecha_inicio = datetime.now() - timedelta(days=dias)

        try:
            stats = self.gestor_bd.obtener_estadisticas_gym(fecha_inicio=fecha_inicio)
            self._datos = stats or {}
        except Exception as exc:
            logger.error("[REPORTES] Error al cargar estadísticas: %s", exc)
            self._datos = {}

        # Cargar clientes recientes
        try:
            todos = self.gestor_bd.obtener_todos_clientes()
            self._datos["clientes_recientes"] = (todos or [])[:100]
        except Exception:
            self._datos["clientes_recientes"] = []

        self._poblar_dashboard()
        self._poblar_graficas()
        self._poblar_tabla_clientes()

    # ------------------------------------------------------------------
    # Exportar
    # ------------------------------------------------------------------

    def _exportar(self) -> None:
        if not _MPL_OK:
            QMessageBox.warning(self, "Advertencia", "matplotlib no disponible para exportar gráficas.")
            return
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Exportar reporte como imagen PNG",
            f"reporte_{datetime.now().strftime('%Y%m%d')}.png",
            "PNG (*.png)",
        )
        if not ruta:
            return
        try:
            plt.savefig(ruta, facecolor="#0D0D0D", bbox_inches="tight")
            QMessageBox.information(self, "Exportado", f"Reporte guardado en:\n{ruta}")
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No se pudo exportar:\n{exc}")

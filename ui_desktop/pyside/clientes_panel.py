# -*- coding: utf-8 -*-
"""
Panel Clientes — Gestión embebida de clientes del gimnasio.
Reemplaza a VentanaClientes (QDialog) con un panel inline (QWidget).
"""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QDoubleSpinBox, QFrame, QGridLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
    QPushButton, QScrollArea, QSizePolicy, QSpinBox, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget, QComboBox,
)

from src.gestor_bd import GestorBDClientes
from ui_desktop.pyside.widgets.avatar_widget import AvatarWidget
from config.constantes import OBJETIVOS_VALIDOS, NIVELES_ACTIVIDAD
from utils.logger import logger


_COLS = [
    ("CLIENTE",        "nombre"),
    ("EDAD / PESO",    "edad_peso"),
    ("OBJETIVO",       "objetivo"),
    ("KCAL OBJ.",      "kcal_obj"),
    ("REGISTRADO",     "fecha_registro"),
    ("ACCIONES",       "acciones"),
]

_TAG_COLORS: dict[str, tuple[str, str]] = {
    "deficit":         ("#2d3a52", "#4a90e2"),
    "déficit":         ("#2d3a52", "#4a90e2"),
    "déficit calórico":("#2d3a52", "#4a90e2"),
    "mantenimiento":   ("#4a3d2a", "#feca57"),
    "superavit":       ("#3a2d42", "#a855f7"),
    "superávit":       ("#3a2d42", "#a855f7"),
    "superávit calórico": ("#3a2d42", "#a855f7"),
}


class ClientesPanel(QWidget):
    """Panel de gestión de clientes con tabla, búsqueda y registro."""

    generar_plan_para = Signal(dict)   # emite el dict del cliente seleccionado

    def __init__(self, gestor_bd: GestorBDClientes | None = None, parent=None):
        super().__init__(parent)
        self.gestor_bd = gestor_bd or GestorBDClientes()
        self._todos_clientes: list[dict] = []
        self._setup_ui()
        self._cargar_clientes()

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
        self._layout = QVBoxLayout(content)
        self._layout.setContentsMargins(32, 24, 32, 32)
        self._layout.setSpacing(20)
        scroll.setWidget(content)

        self._crear_header()
        self._crear_barra_acciones()
        self._crear_tabla()

    def _crear_header(self) -> None:
        header = QFrame()
        header.setObjectName("headerFrame")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 16)

        left = QVBoxLayout()
        left.setSpacing(4)

        title = QLabel("Clientes")
        title.setObjectName("pageTitle")
        left.addWidget(title)

        subtitle = QLabel("Gestión y búsqueda de clientes registrados")
        subtitle.setObjectName("pageSubtitle")
        left.addWidget(subtitle)

        layout.addLayout(left)
        layout.addStretch()

        btn_nuevo = QPushButton("  + Nuevo Cliente")
        btn_nuevo.setObjectName("btnNuevoCliente")
        btn_nuevo.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_nuevo.clicked.connect(self._abrir_dialogo_registro)
        layout.addWidget(btn_nuevo)

        self._layout.addWidget(header)

    def _crear_barra_acciones(self) -> None:
        bar = QWidget()
        bar.setStyleSheet("background: transparent;")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(10)

        self.entry_busqueda = QLineEdit()
        self.entry_busqueda.setPlaceholderText("🔍  Buscar por nombre, teléfono o ID…")
        self.entry_busqueda.textChanged.connect(self._on_busqueda)
        bl.addWidget(self.entry_busqueda, 1)

        btn_buscar = QPushButton("Buscar")
        btn_buscar.setObjectName("btnBuscar")
        btn_buscar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_buscar.clicked.connect(self._on_buscar_click)
        bl.addWidget(btn_buscar)

        bl.addSpacing(8)
        self.lbl_total = QLabel("")
        self.lbl_total.setObjectName("pageSubtitle")
        bl.addWidget(self.lbl_total)

        btn_refresh = QPushButton("⟳ Actualizar")
        btn_refresh.setObjectName("secondaryButton")
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.clicked.connect(self._cargar_clientes)
        bl.addWidget(btn_refresh)

        self._layout.addWidget(bar)

    def _crear_tabla(self) -> None:
        container = QFrame()
        container.setObjectName("chartContainer")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(len(_COLS))
        self.tabla.setHorizontalHeaderLabels([c[0] for c in _COLS])
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setShowGrid(False)

        hdr = self.tabla.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(5, 150)

        layout.addWidget(self.tabla)
        self._layout.addWidget(container)

    # ── Carga de datos ────────────────────────────────────────────────────────

    def _cargar_clientes(self) -> None:
        termino = self.entry_busqueda.text().strip() if hasattr(self, "entry_busqueda") else ""
        try:
            if termino:
                clientes = self.gestor_bd.buscar_clientes(termino, solo_activos=True, limite=200)
            else:
                self._todos_clientes = self.gestor_bd.obtener_todos_clientes(solo_activos=True)
                clientes = self._todos_clientes
        except Exception as exc:
            logger.error("[CLIENTES] Error al cargar: %s", exc)
            clientes = []

        self._poblar_tabla(clientes)

    def _poblar_tabla(self, clientes: list[dict]) -> None:
        self.tabla.setRowCount(0)
        self.lbl_total.setText(f"{len(clientes)} cliente{'s' if len(clientes) != 1 else ''}")

        for i, c in enumerate(clientes):
            self.tabla.insertRow(i)
            self.tabla.setRowHeight(i, 54)

            nombre = c.get("nombre", "—")
            edad = c.get("edad", "—")
            peso = c.get("peso_kg", "—")
            objetivo = (c.get("objetivo") or "—").strip()
            fecha_reg = c.get("fecha_registro", "") or ""
            total_planes = c.get("total_planes_generados", 0) or 0

            # Col 0: Nombre con avatar inline
            widget_nombre = QWidget()
            widget_nombre.setStyleSheet("background: transparent;")
            wl = QHBoxLayout(widget_nombre)
            wl.setContentsMargins(12, 4, 4, 4)
            wl.setSpacing(10)
            avatar = AvatarWidget(nombre, size=36, color_idx=i % 7)
            wl.addWidget(avatar)
            lbl_nombre = QLabel(nombre)
            lbl_nombre.setStyleSheet("color: #f2f2f7; font-weight: 600; background: transparent;")
            wl.addWidget(lbl_nombre)
            wl.addStretch()
            self.tabla.setCellWidget(i, 0, widget_nombre)

            # Col 1: Edad / peso
            edad_peso = f"{edad} a / {peso} kg" if edad and peso else "—"
            item_ep = QTableWidgetItem(edad_peso)
            item_ep.setForeground(QColor("#8e8e93"))
            self.tabla.setItem(i, 1, item_ep)

            # Col 2: Objetivo con tag de color
            obj_lower = objetivo.lower()
            tag_bg, tag_fg = _TAG_COLORS.get(obj_lower, ("#2d2d40", "#8e8e93"))
            widget_obj = QWidget()
            widget_obj.setStyleSheet("background: transparent;")
            ol = QHBoxLayout(widget_obj)
            ol.setContentsMargins(8, 4, 8, 4)
            tag = QLabel(f"  {objetivo.capitalize()}  ")
            tag.setStyleSheet(
                f"background-color: {tag_bg}; color: {tag_fg}; border-radius: 10px;"
                " padding: 2px 8px; font-size: 12px; font-weight: 500;"
            )
            ol.addWidget(tag)
            ol.addStretch()
            self.tabla.setCellWidget(i, 2, widget_obj)

            # Col 3: Kcal objetivo (calculado)
            kcal_str = self._calcular_kcal_display(c)
            item_kcal = QTableWidgetItem(kcal_str)
            item_kcal.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_kcal.setForeground(QColor("#feca57"))
            self.tabla.setItem(i, 3, item_kcal)

            # Col 4: Fecha registro
            if fecha_reg:
                try:
                    dt = datetime.fromisoformat(str(fecha_reg)[:19])
                    fecha_str = dt.strftime("%d/%m/%Y")
                except Exception:
                    fecha_str = str(fecha_reg)[:10]
            else:
                fecha_str = "—"
            self.tabla.setItem(i, 4, QTableWidgetItem(fecha_str))

            # Col 5: Acciones
            widget_acc = QWidget()
            widget_acc.setStyleSheet("background: transparent;")
            al = QHBoxLayout(widget_acc)
            al.setContentsMargins(4, 2, 4, 2)
            al.setSpacing(6)

            _STYLE_PLAN = (
                "QPushButton { background-color: #1a2c1a; border: 1px solid #2a4a2a;"
                " border-radius: 7px; font-size: 12px; color: #a8c8a8; padding: 2px 8px; }"
                "QPushButton:hover { background-color: #1f3e20; border-color: #ffd700;"
                " color: #ffd700; }"
            )
            _STYLE_EDIT = (
                "QPushButton { background-color: #1a2c2c; border: 1px solid #2a4040;"
                " border-radius: 7px; font-size: 12px; color: #a8c8c8; padding: 2px 8px; }"
                "QPushButton:hover { background-color: #1a3a3a; border-color: #22d3ee;"
                " color: #22d3ee; }"
            )
            _STYLE_DEL = (
                "QPushButton { background-color: #2c1a1a; border: 1px solid #4a2a2a;"
                " border-radius: 7px; font-size: 12px; color: #c8a8a8; padding: 2px 8px; }"
                "QPushButton:hover { background-color: #3a1a1a; border-color: #ef4444;"
                " color: #ef4444; }"
            )

            btn_plan = QPushButton("🍽 Plan")
            btn_plan.setToolTip("Generar plan nutricional")
            btn_plan.setFixedHeight(28)
            btn_plan.setStyleSheet(_STYLE_PLAN)
            _c = dict(c)
            btn_plan.clicked.connect(lambda _, cl=_c: self._on_generar_plan(cl))
            al.addWidget(btn_plan)

            btn_edit = QPushButton("✎ Editar")
            btn_edit.setToolTip("Editar cliente")
            btn_edit.setFixedHeight(28)
            btn_edit.setStyleSheet(_STYLE_EDIT)
            _c2 = dict(c)
            btn_edit.clicked.connect(lambda _, cl=_c2: self._on_editar(cl))
            al.addWidget(btn_edit)

            btn_delete = QPushButton("✕ Borrar")
            btn_delete.setToolTip("Eliminar cliente")
            btn_delete.setFixedHeight(28)
            btn_delete.setStyleSheet(_STYLE_DEL)
            _c3 = dict(c)
            btn_delete.clicked.connect(lambda _, cl=_c3: self._on_eliminar(cl))
            al.addWidget(btn_delete)

            al.addStretch()
            self.tabla.setCellWidget(i, 5, widget_acc)

    @staticmethod
    def _calcular_kcal_display(c: dict) -> str:
        """Calcula la kcal objetivo aproximada usando el motor nutricional."""
        try:
            from core.modelos import ClienteEvaluacion
            from core.motor_nutricional import MotorNutricional
            from config.constantes import FACTORES_ACTIVIDAD

            cliente = ClienteEvaluacion(
                nombre=c.get("nombre", ""),
                edad=int(c.get("edad") or 25),
                peso_kg=float(c.get("peso_kg") or 70),
                estatura_cm=float(c.get("estatura_cm") or 170),
                grasa_corporal_pct=float(c.get("grasa_corporal_pct") or 15),
                nivel_actividad=c.get("nivel_actividad") or "moderada",
                objetivo=c.get("objetivo") or "mantenimiento",
            )
            nivel = c.get("nivel_actividad") or "moderada"
            cliente.factor_actividad = FACTORES_ACTIVIDAD.get(nivel, 1.375)
            cliente = MotorNutricional.calcular_motor(cliente)
            return f"{int(cliente.kcal_objetivo):,} kcal"
        except Exception:
            return "—"

    # ── Eventos ───────────────────────────────────────────────────────────────

    def _on_busqueda(self, texto: str) -> None:
        self._cargar_clientes()

    def _on_buscar_click(self) -> None:
        self._cargar_clientes()

    def _on_generar_plan(self, cliente: dict) -> None:
        self.generar_plan_para.emit(cliente)

    def _on_editar(self, cliente: dict) -> None:
        dlg = _DialogoEditar(cliente, self.gestor_bd, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._cargar_clientes()

    def _on_eliminar(self, cliente: dict) -> None:
        nombre = cliente.get("nombre", "Este cliente")
        resp = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Deseas eliminar a <b>{nombre}</b>?<br>"
            "El registro quedará inactivo y no aparecerá en la lista.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resp != QMessageBox.StandardButton.Yes:
            return
        id_cliente = cliente.get("id_cliente", "")
        if not id_cliente:
            return
        try:
            ok = self.gestor_bd.desactivar_cliente(id_cliente)
            if ok:
                self._cargar_clientes()
            else:
                QMessageBox.warning(self, "Error", "No se pudo eliminar el cliente.")
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Error al eliminar: {exc}")

    def _abrir_dialogo_registro(self) -> None:
        dlg = _DialogoRegistro(self.gestor_bd, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._cargar_clientes()

    def refresh(self) -> None:
        self._cargar_clientes()


# ── Diálogo de registro rápido ────────────────────────────────────────────────

class _DialogoRegistro(QDialog):
    """Diálogo para registrar un nuevo cliente."""

    def __init__(self, gestor_bd: GestorBDClientes, parent=None):
        super().__init__(parent)
        self.gestor_bd = gestor_bd
        self.setWindowTitle("Registrar Nuevo Cliente")
        self.setMinimumWidth(520)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(16)

        title = QLabel("REGISTRAR NUEVO CLIENTE")
        title.setStyleSheet(
            "color: #8e8e93; font-size: 12px; font-weight: 600; letter-spacing: 0.5px;"
        )
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(12)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        def field(label_text: str, widget) -> None:
            pass

        # Nombre
        grid.addWidget(self._lbl("Nombre completo *"), 0, 0)
        self.entry_nombre = QLineEdit()
        self.entry_nombre.setPlaceholderText("Ej: Juan Pérez")
        grid.addWidget(self.entry_nombre, 1, 0)

        # Teléfono
        grid.addWidget(self._lbl("Teléfono"), 0, 1)
        self.entry_telefono = QLineEdit()
        self.entry_telefono.setPlaceholderText("Ej: 5512345678")
        grid.addWidget(self.entry_telefono, 1, 1)

        # Edad
        grid.addWidget(self._lbl("Edad *"), 2, 0)
        self.spin_edad = QSpinBox()
        self.spin_edad.setRange(14, 100)
        self.spin_edad.setValue(25)
        grid.addWidget(self.spin_edad, 3, 0)

        # Sexo
        grid.addWidget(self._lbl("Sexo"), 2, 1)
        self.combo_sexo = QComboBox()
        self.combo_sexo.addItems(["M", "F", "Otro"])
        grid.addWidget(self.combo_sexo, 3, 1)

        # Objetivo
        grid.addWidget(self._lbl("Objetivo *"), 4, 0)
        self.combo_objetivo = QComboBox()
        self.combo_objetivo.addItems(
            OBJETIVOS_VALIDOS if OBJETIVOS_VALIDOS else
            ["Déficit calórico", "Mantenimiento", "Superávit calórico"]
        )
        grid.addWidget(self.combo_objetivo, 5, 0)

        # Nivel actividad
        grid.addWidget(self._lbl("Nivel actividad *"), 4, 1)
        self.combo_actividad = QComboBox()
        self.combo_actividad.addItems(
            NIVELES_ACTIVIDAD if NIVELES_ACTIVIDAD else
            ["nula", "leve", "moderada", "intensa"]
        )
        grid.addWidget(self.combo_actividad, 5, 1)

        # Peso
        grid.addWidget(self._lbl("Peso (kg) *"), 6, 0)
        self.spin_peso = QDoubleSpinBox()
        self.spin_peso.setRange(30, 250)
        self.spin_peso.setValue(70.0)
        self.spin_peso.setSingleStep(0.5)
        grid.addWidget(self.spin_peso, 7, 0)

        # Estatura
        grid.addWidget(self._lbl("Estatura (cm) *"), 6, 1)
        self.spin_estatura = QDoubleSpinBox()
        self.spin_estatura.setRange(100, 250)
        self.spin_estatura.setValue(170.0)
        grid.addWidget(self.spin_estatura, 7, 1)

        # % Grasa
        grid.addWidget(self._lbl("% Grasa corporal"), 8, 0)
        self.spin_grasa = QDoubleSpinBox()
        self.spin_grasa.setRange(3, 60)
        self.spin_grasa.setValue(15.0)
        self.spin_grasa.setSingleStep(0.5)
        grid.addWidget(self.spin_grasa, 9, 0)

        layout.addLayout(grid)

        # Botones
        btns = QHBoxLayout()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("secondaryButton")
        btn_cancelar.clicked.connect(self.reject)
        btns.addWidget(btn_cancelar)
        btns.addStretch()

        btn_registrar = QPushButton("Registrar cliente")
        btn_registrar.setObjectName("btnRegistrar")
        btn_registrar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_registrar.clicked.connect(self._on_registrar)
        btns.addWidget(btn_registrar)

        layout.addLayout(btns)

    @staticmethod
    def _lbl(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("fieldLabel")
        return lbl

    def _on_registrar(self) -> None:
        nombre = self.entry_nombre.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Campo requerido", "El nombre es obligatorio.")
            return

        from core.modelos import ClienteEvaluacion
        cliente = ClienteEvaluacion(
            nombre=nombre,
            telefono=self.entry_telefono.text().strip() or None,
            edad=self.spin_edad.value(),
            peso_kg=self.spin_peso.value(),
            estatura_cm=self.spin_estatura.value(),
            grasa_corporal_pct=self.spin_grasa.value(),
            nivel_actividad=self.combo_actividad.currentText(),
            objetivo=self.combo_objetivo.currentText(),
        )
        try:
            ok = self.gestor_bd.registrar_cliente(cliente)
            if ok:
                self.accept()
            else:
                QMessageBox.warning(self, "Error", "No se pudo registrar el cliente.")
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Error al registrar: {exc}")


# ── Diálogo de edición ────────────────────────────────────────────────────────

class _DialogoEditar(_DialogoRegistro):
    """Diálogo para editar un cliente existente."""

    def __init__(self, cliente: dict, gestor_bd: GestorBDClientes, parent=None):
        self._cliente_data = cliente
        super().__init__(gestor_bd, parent)
        self.setWindowTitle("Editar Cliente")
        self._rellenar_campos()

    def _rellenar_campos(self) -> None:
        c = self._cliente_data
        self.entry_nombre.setText(c.get("nombre", ""))
        self.entry_telefono.setText(c.get("telefono", "") or "")
        if c.get("edad"):
            self.spin_edad.setValue(int(c["edad"]))
        if c.get("peso_kg"):
            self.spin_peso.setValue(float(c["peso_kg"]))
        if c.get("estatura_cm"):
            self.spin_estatura.setValue(float(c["estatura_cm"]))
        if c.get("grasa_corporal_pct"):
            self.spin_grasa.setValue(float(c["grasa_corporal_pct"]))
        # Objetivo e itero la lista de combo
        obj = c.get("objetivo", "")
        idx = self.combo_objetivo.findText(obj, Qt.MatchFlag.MatchContains)
        if idx >= 0:
            self.combo_objetivo.setCurrentIndex(idx)
        # Nivel actividad
        nivel = c.get("nivel_actividad", "")
        idx2 = self.combo_actividad.findText(nivel, Qt.MatchFlag.MatchContains)
        if idx2 >= 0:
            self.combo_actividad.setCurrentIndex(idx2)

    def _on_registrar(self) -> None:
        nombre = self.entry_nombre.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Campo requerido", "El nombre es obligatorio.")
            return

        from core.modelos import ClienteEvaluacion
        cliente = ClienteEvaluacion(
            nombre=nombre,
            telefono=self.entry_telefono.text().strip() or None,
            edad=self.spin_edad.value(),
            peso_kg=self.spin_peso.value(),
            estatura_cm=self.spin_estatura.value(),
            grasa_corporal_pct=self.spin_grasa.value(),
            nivel_actividad=self.combo_actividad.currentText(),
            objetivo=self.combo_objetivo.currentText(),
        )
        if self._cliente_data.get("id_cliente"):
            cliente.id_cliente = self._cliente_data["id_cliente"]

        try:
            ok = self.gestor_bd.registrar_cliente(cliente)
            if ok:
                self.accept()
            else:
                QMessageBox.warning(self, "Error", "No se pudo actualizar el cliente.")
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Error al actualizar: {exc}")

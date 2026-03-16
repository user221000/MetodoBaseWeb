# -*- coding: utf-8 -*-
"""
PanelPreferenciasAlimentos — Selector de alimentos por categoría.

Carga los 101 alimentos desde CATEGORIAS (src.alimentos_base) y los
presenta como chips seleccionables (QPushButton#chip_food checkable).

Un chip ACTIVO  → alimento incluido en planes.
Un chip INACTIVO → alimento excluido (UI lo marca como checked=True para
                   que el usuario vea «esto está excluido»).

La lista de excluidos se auto-guarda en GestorPreferencias cada vez que
el usuario toglea un chip (señal excluidos_actualizados(list[str])).
"""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from utils.logger import logger


# ── Metada de categorías ───────────────────────────────────────────────────────
_INFO_CATEGORIA: dict[str, dict[str, str]] = {
    "proteina":  {"icon": "🥩", "label": "Proteínas"},
    "carbs":     {"icon": "🍚", "label": "Carbohidratos"},
    "grasa":     {"icon": "🥑", "label": "Grasas"},
    "fruta":     {"icon": "🍎", "label": "Frutas"},
    "verdura":   {"icon": "🥦", "label": "Verduras"},
}
_ORDEN_CATEGORIAS = ["proteina", "carbs", "grasa", "fruta", "verdura"]


class PanelPreferenciasAlimentos(QDialog):
    """Panel de selección de preferencias alimentarias (exclusiones)."""

    excluidos_actualizados = Signal(list)   # [str] lista de alimentos excluidos

    def __init__(
        self,
        id_usuario: str,
        excluidos_actuales: list[str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._id_usuario = id_usuario
        self._excluidos: set[str] = set(excluidos_actuales or [])
        self._chips: dict[str, QPushButton] = {}  # alimento → chip widget

        self.setWindowTitle("Mis alimentos")
        self.setMinimumSize(580, 640)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self._build_ui()

    # ── Construcción de UI ────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Encabezado fijo ───────────────────────────────────────────────
        header = QFrame()
        header.setObjectName("card")
        header.setStyleSheet(
            "QFrame#card { border-radius: 0; border-bottom: 1px solid #232323;"
            "border-left: none; border-right: none; border-top: none; }"
        )
        h_lay = QVBoxLayout(header)
        h_lay.setContentsMargins(32, 24, 32, 20)
        h_lay.setSpacing(4)

        title = QLabel("🥗  Mis alimentos")
        title.setObjectName("title")
        h_lay.addWidget(title)

        subtitle = QLabel(
            "Marca los alimentos que querés excluir de tus planes nutricionales.\n"
            "Los chips naranjas están excluidos."
        )
        subtitle.setObjectName("subheadline")
        subtitle.setWordWrap(True)
        h_lay.addWidget(subtitle)
        root.addWidget(header)

        # ── Área scrollable ───────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        content_lay = QVBoxLayout(content)
        content_lay.setContentsMargins(32, 24, 32, 32)
        content_lay.setSpacing(0)
        scroll.setWidget(content)

        # Cargar categorías con manejo robusto de imports
        categorias = self._cargar_categorias()

        for clave in _ORDEN_CATEGORIAS:
            alimentos = categorias.get(clave, [])
            if not alimentos:
                continue
            info = _INFO_CATEGORIA.get(clave, {"icon": "🍽️", "label": clave.capitalize()})
            content_lay.addWidget(self._build_seccion(clave, info, alimentos))
            content_lay.addSpacerItem(
                QSpacerItem(0, 16, QSizePolicy.Minimum, QSizePolicy.Fixed)
            )

        # Categorías extra no tipificadas
        extras = {k: v for k, v in categorias.items() if k not in _ORDEN_CATEGORIAS and v}
        for clave, alimentos in sorted(extras.items()):
            info = {"icon": "🍽️", "label": clave.capitalize()}
            content_lay.addWidget(self._build_seccion(clave, info, alimentos))
            content_lay.addSpacerItem(
                QSpacerItem(0, 16, QSizePolicy.Minimum, QSizePolicy.Fixed)
            )

        content_lay.addStretch()
        root.addWidget(scroll)

        # ── Footer fijo ───────────────────────────────────────────────────
        footer = QFrame()
        footer.setObjectName("card")
        footer.setStyleSheet(
            "QFrame#card { border-radius: 0; border-top: 1px solid #232323;"
            "border-left: none; border-right: none; border-bottom: none; }"
        )
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(32, 16, 32, 16)

        self._lbl_conteo = QLabel(self._texto_conteo())
        self._lbl_conteo.setObjectName("caption")
        f_lay.addWidget(self._lbl_conteo)
        f_lay.addStretch()

        btn_limpiar = QPushButton("Quitar exclusiones")
        btn_limpiar.setObjectName("btn_secondary")
        btn_limpiar.setFixedHeight(36)
        btn_limpiar.clicked.connect(self._limpiar_exclusiones)
        f_lay.addWidget(btn_limpiar)

        f_lay.addSpacerItem(QSpacerItem(8, 0, QSizePolicy.Fixed))

        btn_listo = QPushButton("Listo ✓")
        btn_listo.setFixedHeight(36)
        btn_listo.clicked.connect(self._finalizar)
        f_lay.addWidget(btn_listo)
        root.addWidget(footer)

    def _build_seccion(
        self, clave: str, info: dict[str, str], alimentos: list[str]
    ) -> QWidget:
        """Construye un bloque de categoría con chips."""
        bloque = QWidget()
        lay = QVBoxLayout(bloque)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        # Encabezado de categoría
        cat_lbl = QLabel(f"{info['icon']}  {info['label']}")
        cat_lbl.setObjectName("headline")
        lay.addWidget(cat_lbl)

        # Contenedor de chips con wrap
        chips_container = _FlowWidget()
        for alimento in alimentos:
            chip = self._make_chip(alimento)
            chips_container.addWidget(chip)
            self._chips[alimento] = chip

        lay.addWidget(chips_container)
        return bloque

    def _make_chip(self, alimento: str) -> QPushButton:
        """Crea un chip checkable para un alimento."""
        chip = QPushButton(alimento)
        chip.setObjectName("chip_food")
        chip.setCheckable(True)
        chip.setChecked(alimento in self._excluidos)
        chip.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        chip.clicked.connect(lambda checked, a=alimento: self._on_chip_toggle(a, checked))
        return chip

    # ── Slots ─────────────────────────────────────────────────────────────

    def _on_chip_toggle(self, alimento: str, excluido: bool) -> None:
        if excluido:
            self._excluidos.add(alimento)
        else:
            self._excluidos.discard(alimento)
        self._lbl_conteo.setText(self._texto_conteo())
        # Auto-guardar
        self._persistir()

    def _limpiar_exclusiones(self) -> None:
        self._excluidos.clear()
        for chip in self._chips.values():
            chip.setChecked(False)
        self._lbl_conteo.setText(self._texto_conteo())
        self._persistir()

    def _finalizar(self) -> None:
        self._persistir()
        self.accept()

    # ── Helpers ────────────────────────────────────────────────────────────

    def _texto_conteo(self) -> str:
        n = len(self._excluidos)
        return f"{n} alimentos excluidos" if n else "Ningún alimento excluido"

    def _persistir(self) -> None:
        excluidos_list = sorted(self._excluidos)
        try:
            from src.gestor_preferencias import GestorPreferencias
            GestorPreferencias(self._id_usuario).actualizar(
                "alimentos_excluidos", excluidos_list
            )
        except Exception as exc:
            logger.warning("[PREFS] No se pudo guardar exclusiones: %s", exc)
        self.excluidos_actualizados.emit(excluidos_list)

    @staticmethod
    def _cargar_categorias() -> dict[str, list[str]]:
        """Carga CATEGORIAS con fallback a seeds si SQLite falla."""
        try:
            from src.alimentos_base import CATEGORIAS
            return {k: list(v) for k, v in CATEGORIAS.items() if isinstance(v, list)}
        except Exception as exc:
            logger.warning("[PREFS] Fallback a seeds: %s", exc)
            try:
                from src.alimentos_seed_runtime import CATEGORIAS_SEED
                return {k: list(v) for k, v in CATEGORIAS_SEED.items() if isinstance(v, list)}
            except Exception:
                return {}

    # ── API pública ───────────────────────────────────────────────────────

    @property
    def excluidos(self) -> list[str]:
        return sorted(self._excluidos)


# ── FlowWidget —permite chips en varias filas sin scroll horizontal ────────────

class _FlowWidget(QWidget):
    """Layout que envuelve widgets en múltiples filas (flow layout)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._widgets: list[QWidget] = []
        self._spacing = 8

    def addWidget(self, widget: QWidget) -> None:  # noqa: N802
        self._widgets.append(widget)
        widget.setParent(self)
        widget.show()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._relayout()

    def _relayout(self) -> None:
        x, y, row_h = 0, 0, 0
        w_available = self.width()
        for widget in self._widgets:
            ww = widget.sizeHint().width()
            wh = widget.sizeHint().height()
            if x + ww > w_available and x > 0:
                x = 0
                y += row_h + self._spacing
                row_h = 0
            widget.setGeometry(x, y, ww, wh)
            x += ww + self._spacing
            row_h = max(row_h, wh)
        total_h = y + row_h + 4
        self.setMinimumHeight(total_h)
        self.setMaximumHeight(total_h)

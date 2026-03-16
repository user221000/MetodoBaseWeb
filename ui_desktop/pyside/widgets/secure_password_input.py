# -*- coding: utf-8 -*-
"""
SecurePasswordInput — Widget reutilizable para entrada de contraseña.

Características:
  - QLineEdit con echo mode password por defecto.
  - Botón de ojo para mostrar/ocultar texto (el texto visible nunca
    se registra en logs ni señales externas).
  - Barra de fortaleza visual (weak → fair → strong → very strong).
  - Señal ``strength_changed(int)`` emitida con nivel 0-3.
  - La fuerza se computa localmente; la contraseña nunca sale del widget
    como texto plano hacia el exterior (solo al solicitar .value() de forma
    explícita desde código de servicio).
"""
from __future__ import annotations

import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# ── Etiquetas de fortaleza ───────────────────────────────────────────────────

_STRENGTH_LABELS = ["Débil", "Aceptable", "Fuerte", "Muy fuerte"]
_STRENGTH_COLORS = ["#F44336", "#FF9800", "#2196F3", "#4CAF50"]
_STRENGTH_WIDTHS = [25, 50, 75, 100]   # % del ancho total de la barra


def _calcular_fortaleza(password: str) -> int:
    """
    Devuelve nivel de fortaleza 0–3 sin revelar la contraseña en logs.

    Criterios (acumulativos):
      +1  longitud >= 8
      +1  longitud >= 12 Y tiene mayúscula Y minúscula Y dígito
      +1  longitud >= 14 Y tiene símbolo Y no tiene patrones comunes
    """
    if not password:
        return 0
    score = 0
    has_upper  = bool(re.search(r"[A-Z]", password))
    has_lower  = bool(re.search(r"[a-z]", password))
    has_digit  = bool(re.search(r"\d", password))
    has_symbol = bool(re.search(r"[^A-Za-z0-9]", password))
    length = len(password)

    if length >= 8:
        score += 1
    if length >= 12 and has_upper and has_lower and has_digit:
        score += 1
    if length >= 14 and has_symbol and not re.search(
        r"(.)\1{2,}|012|123|234|345|456|567|678|789|890|abc|qwerty|password",
        password.lower(),
    ):
        score += 1
    return min(score, 3)


# ── Widget ───────────────────────────────────────────────────────────────────


class SecurePasswordInput(QWidget):
    """
    Widget de contraseña seguro con barra de fortaleza.

    Uso::

        campo = SecurePasswordInput(placeholder="Contraseña")
        campo.strength_changed.connect(lambda lvl: ...)
        # Al enviar el formulario:
        pw = campo.value()  # str — úsalo inmediatamente, no lo guardes en UI
        campo.clear()       # limpia en cuanto terminas
    """

    #: Emitida cuando cambia el nivel de fortaleza (0–3).
    strength_changed = Signal(int)
    #: Emitida cuando el texto cambia (sin exponer el texto).
    changed = Signal()

    def __init__(
        self,
        placeholder: str = "Contraseña",
        show_strength_bar: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._show_strength = show_strength_bar
        self._strength_level = 0
        self._build_ui(placeholder)

    # ------------------------------------------------------------------
    # Construcción de UI
    # ------------------------------------------------------------------

    def _build_ui(self, placeholder: str) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)

        # ── Fila: input + botón ojo ─────────────────────────────────
        row = QHBoxLayout()
        row.setSpacing(0)
        row.setContentsMargins(0, 0, 0, 0)

        self._entry = QLineEdit()
        self._entry.setEchoMode(QLineEdit.Password)
        self._entry.setPlaceholderText(placeholder)
        self._entry.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._entry.textChanged.connect(self._on_text_changed)
        row.addWidget(self._entry, 1)

        self._btn_ojo = QPushButton("👁")
        self._btn_ojo.setFixedSize(38, 38)
        self._btn_ojo.setCheckable(True)
        self._btn_ojo.setFocusPolicy(Qt.NoFocus)
        self._btn_ojo.setObjectName("btn_ojo")
        self._btn_ojo.setToolTip("Mostrar / ocultar contraseña")
        self._btn_ojo.toggled.connect(self._toggle_visibilidad)
        row.addWidget(self._btn_ojo)

        root.addLayout(row)

        # ── Barra de fortaleza ───────────────────────────────────────
        if self._show_strength:
            barra_container = QWidget()
            barra_container.setFixedHeight(6)
            barra_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            barra_container.setObjectName("strength_container")
            barra_layout = QHBoxLayout(barra_container)
            barra_layout.setContentsMargins(0, 0, 0, 0)
            barra_layout.setSpacing(3)

            self._segmentos: list[QWidget] = []
            for _ in range(4):
                seg = QWidget()
                seg.setFixedHeight(6)
                seg.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                seg.setObjectName("strength_segment_inactive")
                self._segmentos.append(seg)
                barra_layout.addWidget(seg)

            root.addWidget(barra_container)

            # Etiqueta de nivel
            self._lbl_strength = QLabel("")
            self._lbl_strength.setObjectName("strength_label")
            self._lbl_strength.setStyleSheet("font-size: 10px; color: #B8B8B8;")
            root.addWidget(self._lbl_strength)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def value(self) -> str:
        """Retorna el texto de contraseña. Úsalo una sola vez y descártalo."""
        return self._entry.text()

    def clear(self) -> None:
        """Limpia el campo. Llama esto en cuanto termines de usar value()."""
        self._entry.clear()

    def set_enabled(self, enabled: bool) -> None:
        self._entry.setEnabled(enabled)
        self._btn_ojo.setEnabled(enabled)

    def setFocus(self) -> None:  # noqa: N802
        self._entry.setFocus()

    # ------------------------------------------------------------------
    # Slots privados
    # ------------------------------------------------------------------

    def _toggle_visibilidad(self, checked: bool) -> None:
        if checked:
            self._entry.setEchoMode(QLineEdit.Normal)
            self._btn_ojo.setToolTip("Ocultar contraseña")
        else:
            self._entry.setEchoMode(QLineEdit.Password)
            self._btn_ojo.setToolTip("Mostrar contraseña")

    def _on_text_changed(self, _text: str) -> None:
        # NOTA: no usamos _text para no propagar la contraseña;
        # calculamos directamente desde el widget.
        nivel = _calcular_fortaleza(self._entry.text())
        self.changed.emit()

        if not self._show_strength:
            return

        if nivel != self._strength_level:
            self._strength_level = nivel
            self.strength_changed.emit(nivel)

        self._actualizar_barra(nivel)

    def _actualizar_barra(self, nivel: int) -> None:
        # Activar N segmentos (nivel 0 → ninguno coloreado)
        texto_entrada = self._entry.text()
        if not texto_entrada:
            for seg in self._segmentos:
                seg.setStyleSheet(
                    "background-color: #2A2A2A; border-radius: 3px;"
                )
            self._lbl_strength.setText("")
            return

        color = _STRENGTH_COLORS[nivel]
        etiqueta = _STRENGTH_LABELS[nivel]

        for i, seg in enumerate(self._segmentos):
            if i <= nivel:
                seg.setStyleSheet(
                    f"background-color: {color}; border-radius: 3px;"
                )
            else:
                seg.setStyleSheet(
                    "background-color: #2A2A2A; border-radius: 3px;"
                )
        self._lbl_strength.setText(etiqueta)
        self._lbl_strength.setStyleSheet(
            f"font-size: 10px; color: {color};"
        )

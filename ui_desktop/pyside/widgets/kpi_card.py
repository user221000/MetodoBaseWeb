# -*- coding: utf-8 -*-
"""
Widget KPI card reutilizable con ícono, valor animado y texto de cambio.
"""
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QTimer


class KPICard(QFrame):
    """Card KPI con animación de contador numérico."""

    def __init__(
        self,
        icon_color: str,      # "purple" | "blue" | "yellow" | "cyan"
        icon_emoji: str,      # emoji para el ícono
        value: int,
        label: str,
        change_text: str,
        trend: str = "neutral",  # "up" | "down" | "neutral"
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("kpiCard")
        self._target_value = value
        self._current_value = 0
        self._timer: QTimer | None = None
        self._setup_ui(icon_color, icon_emoji, label, change_text, trend)

    # ── Construcción ──────────────────────────────────────────────────────────

    def _setup_ui(
        self, icon_color: str, icon_emoji: str,
        label: str, change_text: str, trend: str
    ) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(10)

        # ── Ícono ─────────────────────────────────────────────────────────────
        icon_label = QLabel(icon_emoji)
        icon_label.setObjectName("kpiIcon")
        icon_label.setProperty("color", icon_color)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFixedSize(48, 48)
        layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignLeft)

        # ── Valor ─────────────────────────────────────────────────────────────
        self._value_label = QLabel("0")
        self._value_label.setObjectName("kpiValue")
        layout.addWidget(self._value_label)

        # ── Label ─────────────────────────────────────────────────────────────
        label_widget = QLabel(label)
        label_widget.setObjectName("kpiLabel")
        layout.addWidget(label_widget)

        # ── Cambio ────────────────────────────────────────────────────────────
        self._change_label = QLabel(change_text)
        self._change_label.setObjectName("kpiChange")
        self._change_label.setProperty("trend", trend)
        layout.addWidget(self._change_label)

        layout.addStretch()

    # ── API pública ───────────────────────────────────────────────────────────

    def set_value(self, value: int, change_text: str = "") -> None:
        """Actualiza el valor sin animación."""
        self._target_value = value
        self._value_label.setText(str(value))
        if change_text:
            self._change_label.setText(change_text)

    def animate_value(self, duration_ms: int = 1000) -> None:
        """Anima el contador desde 0 hasta el valor objetivo."""
        if self._target_value == 0:
            self._value_label.setText("0")
            return

        steps = 40
        step_val = max(1, self._target_value // steps)
        interval = max(20, duration_ms // steps)
        self._current_value = 0

        if self._timer:
            self._timer.stop()
            self._timer.deleteLater()

        self._timer = QTimer(self)

        def _update() -> None:
            self._current_value = min(
                self._current_value + step_val, self._target_value
            )
            self._value_label.setText(str(self._current_value))
            if self._current_value >= self._target_value:
                self._timer.stop()
                self._value_label.setText(str(self._target_value))

        self._timer.timeout.connect(_update)
        self._timer.start(interval)

    def update_value(self, value: int, animate: bool = True) -> None:
        """Actualiza el valor, opcionalmente animado."""
        self._target_value = value
        if animate:
            self.animate_value()
        else:
            self._value_label.setText(str(value))

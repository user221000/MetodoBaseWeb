# -*- coding: utf-8 -*-
"""Indicador de flujo de pasos PySide6 — reemplaza gui/widgets_progress.StepFlowIndicator."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt


class StepFlowIndicator(QWidget):
    """Widget visual de pasos: Captura → Preview → Exportar."""

    COLOR_BG = "#1E1E1E"
    COLOR_BORDER = "#444444"
    COLOR_TEXT = "#F5F5F5"
    COLOR_MUTED = "#A8A8A8"
    COLOR_ACTIVE = "#9B4FB0"
    COLOR_DONE = "#4CAF50"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.steps = ["Captura", "Preview", "Exportar"]
        self._active_step = 0
        self._completed: set[int] = set()
        self._dot_labels: list[QLabel] = []
        self._step_labels: list[QLabel] = []
        self._connectors: list[QFrame] = []
        self._build()
        self._paint()

    def _build(self) -> None:
        self.setStyleSheet(
            f"StepFlowIndicator {{ background-color: {self.COLOR_BG}; "
            f"border: 1px solid {self.COLOR_BORDER}; border-radius: 10px; }}"
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 10, 14, 10)
        outer.setSpacing(4)

        title = QLabel("Flujo de trabajo")
        title.setStyleSheet(
            f"color: {self.COLOR_TEXT}; font-size: 12px; font-weight: bold;"
            " background: transparent; border: none;"
        )
        outer.addWidget(title)

        row_widget = QWidget()
        row_widget.setStyleSheet("background: transparent; border: none;")
        row = QHBoxLayout(row_widget)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        outer.addWidget(row_widget)

        for i, step_name in enumerate(self.steps):
            cell = QWidget()
            cell.setStyleSheet("background: transparent; border: none;")
            cell_layout = QVBoxLayout(cell)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.setSpacing(4)
            cell_layout.setAlignment(Qt.AlignCenter)

            dot = QLabel(str(i + 1))
            dot.setFixedSize(28, 28)
            dot.setAlignment(Qt.AlignCenter)
            dot.setStyleSheet(
                "background-color: #2A2A2A; color: #A8A8A8; border-radius: 14px;"
                " font-size: 12px; font-weight: bold; border: none;"
            )
            cell_layout.addWidget(dot, alignment=Qt.AlignCenter)

            lbl = QLabel(step_name)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(
                "color: #A8A8A8; font-size: 11px; background: transparent; border: none;"
            )
            cell_layout.addWidget(lbl, alignment=Qt.AlignCenter)

            self._dot_labels.append(dot)
            self._step_labels.append(lbl)
            row.addWidget(cell, stretch=1)

            if i < len(self.steps) - 1:
                line = QFrame()
                line.setFrameShape(QFrame.HLine)
                line.setFixedHeight(2)
                line.setStyleSheet(f"background-color: {self.COLOR_BORDER}; border: none;")
                self._connectors.append(line)
                row.addWidget(line, stretch=2)

    def set_step(self, step_idx: int) -> None:
        self._active_step = max(0, min(step_idx, len(self.steps) - 1))
        self._paint()

    def complete_step(self, step_idx: int) -> None:
        if 0 <= step_idx < len(self.steps):
            self._completed.add(step_idx)
        self._paint()

    def reset(self) -> None:
        self._active_step = 0
        self._completed.clear()
        self._paint()

    def _paint(self) -> None:
        for idx, dot in enumerate(self._dot_labels):
            lbl = self._step_labels[idx]
            if idx in self._completed:
                dot.setText("✓")
                dot.setStyleSheet(
                    f"background-color: {self.COLOR_DONE}; color: #FFFFFF;"
                    " border-radius: 14px; font-size: 12px; font-weight: bold; border: none;"
                )
                lbl.setStyleSheet(f"color: {self.COLOR_DONE}; font-size: 11px; background: transparent; border: none;")
            elif idx == self._active_step:
                dot.setText(str(idx + 1))
                dot.setStyleSheet(
                    f"background-color: {self.COLOR_ACTIVE}; color: #FFFFFF;"
                    " border-radius: 14px; font-size: 12px; font-weight: bold; border: none;"
                )
                lbl.setStyleSheet(f"color: {self.COLOR_TEXT}; font-size: 11px; background: transparent; border: none;")
            else:
                dot.setText(str(idx + 1))
                dot.setStyleSheet(
                    "background-color: #2A2A2A; color: #A8A8A8;"
                    " border-radius: 14px; font-size: 12px; font-weight: bold; border: none;"
                )
                lbl.setStyleSheet("color: #A8A8A8; font-size: 11px; background: transparent; border: none;")

        for idx, connector in enumerate(self._connectors):
            if idx in self._completed:
                connector.setStyleSheet(f"background-color: {self.COLOR_DONE}; border: none;")
            elif idx < self._active_step:
                connector.setStyleSheet(f"background-color: {self.COLOR_ACTIVE}; border: none;")
            else:
                connector.setStyleSheet(f"background-color: {self.COLOR_BORDER}; border: none;")

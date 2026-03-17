# -*- coding: utf-8 -*-
"""
Widgets de gráficas simples usando QPainter — sin dependencias de red.

Incluye:
  LineChartWidget  — gráfico de línea con relleno degradado
  DonutChartWidget — gráfico de donut con leyenda
"""
from __future__ import annotations

from typing import List

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import (
    QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen,
)
from PySide6.QtWidgets import QWidget


# ── Gráfico de línea ──────────────────────────────────────────────────────────

class LineChartWidget(QWidget):
    """Gráfico de línea con área degradado bajo la curva."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._labels: List[str] = []
        self._values: List[float] = []
        self._line_color = "#667eea"
        self.setMinimumHeight(180)

    def set_data(self, labels: List[str], values: List[float]) -> None:
        self._labels = labels
        self._values = values
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        if not self._values:
            self._paint_empty()
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        pad_l, pad_r, pad_t, pad_b = 46, 16, 16, 36

        chart_w = w - pad_l - pad_r
        chart_h = h - pad_t - pad_b

        if chart_w <= 0 or chart_h <= 0:
            painter.end()
            return

        n = len(self._values)
        max_v = max(self._values)
        min_v = min(self._values)
        val_range = (max_v - min_v) or 1.0

        def to_pt(i: int, v: float) -> QPointF:
            x = pad_l + (i / max(n - 1, 1)) * chart_w
            y = pad_t + (1.0 - (v - min_v) / val_range) * chart_h
            return QPointF(x, y)

        # Líneas de cuadrícula horizontales
        grid_pen = QPen(QColor("#2d2d40"), 1)
        painter.setPen(grid_pen)
        label_font = QFont("Segoe UI", 9)
        painter.setFont(label_font)
        painter.setPen(QColor("#8e8e93"))
        for i in range(5):
            y = pad_t + (i / 4) * chart_h
            painter.setPen(QPen(QColor("#2d2d40"), 1))
            painter.drawLine(int(pad_l), int(y), int(w - pad_r), int(y))
            val = max_v - (i / 4) * val_range
            painter.setPen(QColor("#8e8e93"))
            painter.drawText(0, int(y) - 8, pad_l - 6, 16,
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                             str(int(val)))

        if n < 2:
            painter.end()
            return

        points = [to_pt(i, v) for i, v in enumerate(self._values)]

        # Área degradado
        grad = QLinearGradient(0, pad_t, 0, pad_t + chart_h)
        grad.setColorAt(0, QColor(102, 126, 234, 110))
        grad.setColorAt(1, QColor(102, 126, 234, 5))

        fill_path = QPainterPath()
        fill_path.moveTo(QPointF(pad_l, pad_t + chart_h))
        fill_path.lineTo(points[0])
        for pt in points[1:]:
            fill_path.lineTo(pt)
        fill_path.lineTo(QPointF(points[-1].x(), pad_t + chart_h))
        fill_path.closeSubpath()
        painter.fillPath(fill_path, QBrush(grad))

        # Línea
        line_path = QPainterPath()
        line_path.moveTo(points[0])
        for pt in points[1:]:
            line_path.lineTo(pt)

        line_pen = QPen(QColor(self._line_color), 2)
        line_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        line_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(line_pen)
        painter.drawPath(line_path)

        # Puntos
        painter.setBrush(QBrush(QColor(self._line_color)))
        painter.setPen(QPen(QColor("#1e1e2e"), 2))
        for pt in points:
            painter.drawEllipse(pt, 4.5, 4.5)

        # Etiquetas eje X
        painter.setPen(QColor("#8e8e93"))
        painter.setFont(label_font)
        for i, lbl in enumerate(self._labels):
            x = pad_l + (i / max(n - 1, 1)) * chart_w
            painter.drawText(
                int(x) - 22, h - pad_b + 6, 44, 20,
                Qt.AlignmentFlag.AlignCenter,
                lbl[:4],
            )

        painter.end()

    def _paint_empty(self) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor("#5e5e6e"))
        painter.setFont(QFont("Segoe UI", 11))
        painter.drawText(
            self.rect(), Qt.AlignmentFlag.AlignCenter,
            "Sin datos disponibles"
        )
        painter.end()


# ── Gráfico donut ─────────────────────────────────────────────────────────────

class DonutChartWidget(QWidget):
    """Gráfico de tipo donut con leyenda inferior."""

    _DEFAULT_COLORS = ["#10b981", "#ef4444", "#ffd700", "#4a90e2", "#a855f7"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._labels: List[str] = []
        self._values: List[float] = []
        self._colors: List[str] = self._DEFAULT_COLORS
        self._center_value: str = ""
        self._center_label: str = ""
        self.setMinimumHeight(200)

    def set_data(
        self,
        labels: List[str],
        values: List[float],
        colors: List[str] | None = None,
    ) -> None:
        self._labels = labels
        self._values = values
        if colors:
            self._colors = colors
        self.update()

    def set_center_text(self, value: str, label: str = "") -> None:
        """Muestra un valor grande + etiqueta pequeña en el centro del donut."""
        self._center_value = value
        self._center_label = label
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        if not self._values or sum(self._values) == 0:
            self._paint_empty()
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        n = len(self._labels)
        legend_h = 26 * ((n + 2) // 3)  # filas de leyenda
        chart_h = max(80, h - legend_h - 16)

        outer_r = min(w, chart_h) // 2 - 12
        inner_r = int(outer_r * 0.62)
        cx = w // 2
        cy = chart_h // 2

        total = sum(self._values)
        start = 90 * 16  # grados en unidades Qt (×16)

        outer_rect = QRectF(cx - outer_r, cy - outer_r, outer_r * 2, outer_r * 2)
        inner_rect = QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2)

        for i, (_, val) in enumerate(zip(self._labels, self._values)):
            span = int((val / total) * 360 * 16)
            color = QColor(self._colors[i % len(self._colors)])

            path = QPainterPath()
            path.arcMoveTo(outer_rect, start / 16)
            path.arcTo(outer_rect, start / 16, span / 16)
            path.arcTo(inner_rect, (start + span) / 16, -(span / 16))
            path.closeSubpath()

            painter.fillPath(path, QBrush(color))
            start += span

        # Texto central (valor + etiqueta dentro del hueco)
        if self._center_value:
            val_font = QFont("Segoe UI", max(10, inner_r // 2), QFont.Weight.Bold)
            painter.setFont(val_font)
            painter.setPen(QColor("#f0f0f0"))
            painter.drawText(
                int(cx - inner_r), int(cy - inner_r),
                int(inner_r * 2), int(inner_r * 2),
                Qt.AlignmentFlag.AlignCenter,
                self._center_value,
            )
            if self._center_label:
                lbl_font = QFont("Segoe UI", max(7, inner_r // 4))
                painter.setFont(lbl_font)
                painter.setPen(QColor("#8e8e93"))
                painter.drawText(
                    int(cx - inner_r), int(cy + inner_r // 3),
                    int(inner_r * 2), int(inner_r),
                    Qt.AlignmentFlag.AlignCenter,
                    self._center_label,
                )

        # Leyenda
        legend_font = QFont("Segoe UI", 10)
        painter.setFont(legend_font)
        cols = min(n, 3)
        col_w = w // cols if cols > 0 else w
        legend_y = chart_h + 8

        for i, (lbl, val) in enumerate(zip(self._labels, self._values)):
            col = i % cols
            row = i // cols
            x = col * col_w + 12
            y = legend_y + row * 26
            color = QColor(self._colors[i % len(self._colors)])

            # Punto de color
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(x, y + 6, 10, 10)

            # Texto
            pct = f"{val / total * 100:.0f}%" if total > 0 else "0%"
            painter.setPen(QColor("#8e8e93"))
            painter.drawText(
                x + 16, y, col_w - 20, 22,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                f"{lbl} {pct}",
            )

        painter.end()

    def _paint_empty(self) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor("#5e5e6e"))
        painter.setFont(QFont("Segoe UI", 11))
        painter.drawText(
            self.rect(), Qt.AlignmentFlag.AlignCenter,
            "Sin datos disponibles"
        )
        painter.end()

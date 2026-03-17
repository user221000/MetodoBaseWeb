# -*- coding: utf-8 -*-
"""
Widget avatar circular con iniciales en color.
"""
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPixmap, QColor, QFont, QBrush

_AVATAR_COLORS = [
    "#667eea",  # morado
    "#48dbfb",  # cyan
    "#ff6b9d",  # rosa
    "#feca57",  # amarillo
    "#10b981",  # verde
    "#a855f7",  # violeta
    "#4a90e2",  # azul
]


class AvatarWidget(QLabel):
    """Avatar circular con iniciales y color de fondo.

    Args:
        name: Nombre completo del cliente (se extraen las iniciales).
        size: Tamaño en píxeles (ancho = alto).
        color_idx: Índice para seleccionar color de la paleta.
    """

    def __init__(self, name: str, size: int = 40, color_idx: int = 0, parent=None):
        super().__init__(parent)
        initials = self._get_initials(name)
        color = _AVATAR_COLORS[color_idx % len(_AVATAR_COLORS)]
        pix = self._draw_avatar(initials, size, color)
        self.setPixmap(pix)
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    @staticmethod
    def _get_initials(name: str) -> str:
        parts = name.strip().split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        if parts:
            return parts[0][:2].upper()
        return "??"

    @staticmethod
    def _draw_avatar(initials: str, size: int, color: str) -> QPixmap:
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Círculo de fondo
        painter.setBrush(QBrush(QColor(color)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, size, size)

        # Iniciales
        font_size = max(8, size // 3)
        font = QFont("Segoe UI", font_size)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("white"))
        painter.drawText(
            0, 0, size, size,
            Qt.AlignmentFlag.AlignCenter,
            initials,
        )

        painter.end()
        return pix

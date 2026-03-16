# -*- coding: utf-8 -*-
"""Widget de notificación toast para PySide6 — reemplaza gui/widgets_toast.py."""

from PySide6.QtWidgets import QLabel, QWidget
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui import QColor


_COLORES = {
    "success": ("#1B5E20", "#4CAF50"),   # fondo, texto
    "error":   ("#B71C1C", "#FF7043"),
    "warning": ("#E65100", "#FFB300"),
    "info":    ("#0D47A1", "#42A5F5"),
}


class ToastWidget(QLabel):
    """Notificación flotante en la esquina superior-derecha de su padre."""

    def __init__(self, parent: QWidget, mensaje: str, tipo: str = "info", duracion: int = 3000):
        super().__init__(mensaje, parent)
        bg, fg = _COLORES.get(tipo, _COLORES["info"])
        self.setStyleSheet(
            f"background-color: {bg}; color: {fg}; border-radius: 8px;"
            f" padding: 10px 16px; font-size: 13px; font-weight: bold;"
        )
        self.setAlignment(Qt.AlignCenter)
        self.setWordWrap(True)
        self.adjustSize()
        self.setFixedWidth(min(400, max(250, self.sizeHint().width() + 20)))
        self._reposicionar(parent)

        # Animación de entrada
        self._anim = QPropertyAnimation(self, b"pos")
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.setDuration(280)
        start_pos = QPoint(self.x(), self.y() - 20)
        end_pos = QPoint(self.x(), self.y())
        self._anim.setStartValue(start_pos)
        self._anim.setEndValue(end_pos)

        self.show()
        self.raise_()
        self._anim.start()

        QTimer.singleShot(duracion, self._fadeout)

    def _reposicionar(self, parent: QWidget) -> None:
        pw = parent.width()
        margin = 16
        self.adjustSize()
        self.setGeometry(pw - self.width() - margin, margin + 60, self.width(), self.height())

    def _fadeout(self) -> None:
        self._anim2 = QPropertyAnimation(self, b"pos")
        self._anim2.setDuration(220)
        self._anim2.setStartValue(self.pos())
        self._anim2.setEndValue(QPoint(self.x(), self.y() - 20))
        self._anim2.finished.connect(self.deleteLater)
        self._anim2.start()


def mostrar_toast(
    parent: QWidget,
    mensaje: str,
    tipo: str = "info",
    duracion: int = 3000,
) -> None:
    """Muestra un toast flotante en la esquina superior-derecha de *parent*."""
    ToastWidget(parent, mensaje, tipo=tipo, duracion=duracion)

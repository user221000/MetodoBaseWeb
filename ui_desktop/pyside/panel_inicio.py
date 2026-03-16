# -*- coding: utf-8 -*-
"""
PanelInicio — Selector de tipo de usuario.

Muestra dos tarjetas grandes:
  · GYM         → activa flujo de licencia + MainWindow (herramienta profesional)
  · Usuario     → activa flujo Auth → PerfilDetalle → MetodoBase (dashboard personal)

Uso:
    dlg = PanelInicio()
    resultado = dlg.exec()   # ResultadoInicio.GYM | ResultadoInicio.USUARIO | 0 (cancelar)
"""
from __future__ import annotations

from enum import IntEnum

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QPixmap, QColor, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)
from ui_desktop.pyside.theme_manager import ThemeSwitcher


class ResultadoInicio(IntEnum):
    CANCELADO = 0
    GYM = 1
    USUARIO = 2


class PanelInicio(QDialog):
    """Diálogo de bienvenida con selector de perfil."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Método Base")
        self.setFixedSize(620, 560)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self._resultado = ResultadoInicio.CANCELADO
        self._build_ui()

    # ── Construcción de UI ────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(0)

        # Barra superior: selector de tema alineado a la derecha
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        top_bar.addStretch()
        top_bar.addWidget(ThemeSwitcher(parent=self))
        root.addLayout(top_bar)
        root.addSpacerItem(QSpacerItem(0, 8, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Logo / título
        root.addLayout(self._header())
        root.addSpacerItem(QSpacerItem(0, 32, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Subtítulo
        sub = QLabel("¿Cómo vas a usar Método Base hoy?")
        sub.setObjectName("subheadline")
        sub.setAlignment(Qt.AlignHCenter)
        root.addWidget(sub)
        root.addSpacerItem(QSpacerItem(0, 32, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Tarjetas de elección
        cards = QHBoxLayout()
        cards.setSpacing(16)
        cards.addWidget(self._build_card(
            icon="🏋️",
            title="Soy GYM / Profesional",
            desc="Gestiona clientes, genera planes\nnutricionales y exporta reportes.",
            resultado=ResultadoInicio.GYM,
            accent=True,
        ))
        cards.addWidget(self._build_card(
            icon="👤",
            title="Soy Usuario Regular",
            desc="Crea tu perfil personal, elige\ntus alimentos y consulta tu plan.",
            resultado=ResultadoInicio.USUARIO,
            accent=False,
        ))
        root.addLayout(cards)

        root.addSpacerItem(QSpacerItem(0, 24, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Aviso versión
        ver = QLabel("Método Base v2.0  •  Sistema de Planes Nutricionales")
        ver.setObjectName("caption")
        ver.setAlignment(Qt.AlignHCenter)
        root.addWidget(ver)

    def _header(self) -> QVBoxLayout:
        lay = QVBoxLayout()
        lay.setSpacing(6)

        # Punto naranja decorativo (reemplaza logo si no existe)
        dot = QLabel("●")
        dot.setObjectName("dot_accent")
        dot.setAlignment(Qt.AlignHCenter)
        lay.addWidget(dot)

        title = QLabel("Método Base")
        title.setObjectName("display")
        title.setAlignment(Qt.AlignHCenter)
        lay.addWidget(title)
        return lay

    def _build_card(
        self,
        icon: str,
        title: str,
        desc: str,
        resultado: ResultadoInicio,
        accent: bool,
    ) -> QPushButton:
        btn = QPushButton()
        btn.setObjectName("btn_choice_card")
        btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn.setFixedHeight(220)

        # Montar layout interno con widget  
        inner = QVBoxLayout(btn)
        inner.setContentsMargins(20, 24, 20, 24)
        inner.setSpacing(12)
        inner.setAlignment(Qt.AlignCenter)

        # Icono
        ic = QLabel(icon)
        ic.setObjectName("card_icon")
        ic.setAlignment(Qt.AlignHCenter)
        inner.addWidget(ic)

        # Título
        tl = QLabel(title)
        tl.setObjectName("card_title")
        tl.setAlignment(Qt.AlignHCenter)
        inner.addWidget(tl)

        # Descripción
        ds = QLabel(desc)
        ds.setObjectName("card_desc")
        ds.setAlignment(Qt.AlignHCenter)
        ds.setWordWrap(True)
        inner.addWidget(ds)

        if accent:
            btn.setObjectName("btn_choice_card_accent")

        btn.clicked.connect(lambda _checked, r=resultado: self._elegir(r))
        return btn

    # ── Slots ─────────────────────────────────────────────────────────────

    def _elegir(self, resultado: ResultadoInicio) -> None:
        self._resultado = resultado
        self.done(int(resultado))

    # ── API pública ───────────────────────────────────────────────────────

    @property
    def resultado(self) -> ResultadoInicio:
        return self._resultado

# -*- coding: utf-8 -*-
"""
PanelInicio — Selector de tipo de usuario con tema verde premium.

Muestra dos tarjetas grandes:
  · GYM         → activa flujo de licencia + MainWindow (herramienta profesional)
  · Usuario     → activa flujo Auth → PerfilDetalle → MetodoBase (dashboard personal)

Uso:
    dlg = PanelInicio()
    resultado = dlg.exec()   # ResultadoInicio.GYM | ResultadoInicio.USUARIO | 0 (cancelar)
"""
from __future__ import annotations

from enum import IntEnum

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)


class ResultadoInicio(IntEnum):
    CANCELADO = 0
    GYM = 1
    USUARIO = 2


class PanelInicio(QDialog):
    """Diálogo de bienvenida con selector de perfil — tema verde premium."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Método Base — Selección de Perfil")
        self.setFixedSize(860, 600)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self._resultado = ResultadoInicio.CANCELADO
        self._build_ui()
        self._animar_entrada()

    # ── Construcción de UI ────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Banner superior (mismo patrón que VentanaAccesoGym)
        root.addWidget(self._banner())

        # Área de contenido
        content = QWidget()
        content_lay = QVBoxLayout(content)
        content_lay.setContentsMargins(48, 32, 48, 28)
        content_lay.setSpacing(0)
        root.addWidget(content)

        # Subtítulo descriptivo
        sub = QLabel("Sistema de Gestión Nutricional y Gimnasio")
        sub.setObjectName("subheadline")
        sub.setAlignment(Qt.AlignHCenter)
        content_lay.addWidget(sub)
        content_lay.addSpacing(28)

        # Pregunta principal
        pregunta = QLabel("¿Cómo deseas acceder hoy?")
        pregunta.setObjectName("headline")
        pregunta.setAlignment(Qt.AlignHCenter)
        content_lay.addWidget(pregunta)
        content_lay.addSpacing(32)

        # Tarjetas de elección
        cards = QHBoxLayout()
        cards.setSpacing(24)
        cards.addWidget(self._build_card(
            icon="🏢",
            title="Modo Gimnasio",
            desc=(
                "Gestión completa: clientes, suscripciones,\n"
                "clases, facturación y planes nutricionales."
            ),
            bullets=["Clientes ilimitados", "Facturación integrada", "Reportes avanzados"],
            resultado=ResultadoInicio.GYM,
            accent=True,
            badge_text="PREMIUM",
            btn_text="Acceder Premium →",
        ))
        cards.addWidget(self._build_card(
            icon="👤",
            title="Usuario Regular",
            desc=(
                "Genera tu plan nutricional personalizado\n"
                "y lleva el control de tu progreso."
            ),
            bullets=["Plan personalizado", "Control de progreso", "Sin costo mensual"],
            resultado=ResultadoInicio.USUARIO,
            accent=False,
            badge_text="",
            btn_text="Acceder →",
        ))
        content_lay.addLayout(cards)
        content_lay.addStretch()

        # Footer
        content_lay.addWidget(self._footer())

    def _banner(self) -> QWidget:
        """Banner superior con gradiente oscuro y badge 'BIENVENIDA'."""
        banner = QWidget()
        banner.setFixedHeight(60)
        banner.setStyleSheet(
            "QWidget { background: qlineargradient("
            "x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #0a1409,stop:0.5 #0f1e0d,stop:1 #152515"
            "); border-bottom: 2px solid #2a4a2a; }"
        )
        lay = QHBoxLayout(banner)
        lay.setContentsMargins(28, 0, 28, 0)
        lay.setSpacing(10)

        dot = QLabel("●")
        dot.setStyleSheet(
            "color: #39ff14; font-size: 16px; background: transparent;"
        )
        lay.addWidget(dot)

        brand = QLabel("Método Base")
        brand.setStyleSheet(
            "color: #f0f0f0; font-size: 18px; font-weight: 700; background: transparent;"
        )
        lay.addWidget(brand)
        lay.addStretch()

        tagline = QLabel("Sistema Nutricional Profesional")
        tagline.setStyleSheet("color: #6b7b6b; font-size: 12px; background: transparent;")
        lay.addWidget(tagline)

        lay.addSpacing(12)

        badge = QLabel(" BIENVENIDA ")
        badge.setStyleSheet(
            "background: qlineargradient("
            "x1:0,y1:0,x2:1,y2:0,stop:0 #ffd700,stop:1 #d4af37"
            "); color: #0a1409; font-size: 11px; font-weight: 700;"
            " padding: 4px 12px; border-radius: 10px; background-clip: padding;"
        )
        lay.addWidget(badge)

        return banner

    def _build_card(
        self,
        icon: str,
        title: str,
        desc: str,
        bullets: list[str],
        resultado: ResultadoInicio,
        accent: bool,
        badge_text: str = "",
        btn_text: str = "Acceder →",
    ) -> QWidget:
        """Crea una card interactiva para selección de modo."""
        # Colores según modo
        border_color = "#ffd700" if accent else "#22d3ee"
        hover_bg = "#1f3e1a" if accent else "#1a2e2e"
        shadow_color = "#ffd700" if accent else "#22d3ee"

        card = QWidget()
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(32)
        shadow.setColor(QColor(shadow_color))
        shadow.setOffset(0, 4)
        card.setGraphicsEffect(shadow)

        card.setStyleSheet(f"""
            QWidget {{
                background-color: #1e2e1d;
                border: 2px solid {border_color};
                border-radius: 18px;
            }}
            QWidget:hover {{
                background-color: {hover_bg};
            }}
        """)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(28, 28, 28, 24)
        lay.setSpacing(0)

        # Badge premium (si aplica)
        if badge_text:
            badge = QLabel(f" {badge_text} ")
            badge.setAlignment(Qt.AlignCenter)
            badge.setFixedWidth(100)
            badge.setStyleSheet(
                "background: qlineargradient("
                "x1:0,y1:0,x2:1,y2:0,stop:0 #ffd700,stop:1 #d4af37"
                "); color: #0a1409; font-size: 10px; font-weight: 700;"
                " padding: 4px 12px; border-radius: 12px;"
            )
            lay.addWidget(badge, 0, Qt.AlignCenter)
            lay.addSpacing(14)

        # Ícono grande
        ic = QLabel(icon)
        ic.setAlignment(Qt.AlignHCenter)
        ic.setStyleSheet(
            "font-size: 48px; background: transparent; border: none;"
        )
        lay.addWidget(ic)
        lay.addSpacing(12)

        # Título de la card
        tl = QLabel(title)
        tl.setAlignment(Qt.AlignHCenter)
        tl.setStyleSheet(
            "font-size: 22px; font-weight: 700; color: #f0f0f0;"
            " background: transparent; border: none;"
        )
        lay.addWidget(tl)
        lay.addSpacing(8)

        # Descripción
        ds = QLabel(desc)
        ds.setAlignment(Qt.AlignHCenter)
        ds.setWordWrap(True)
        ds.setStyleSheet(
            "font-size: 13px; color: #a8b5a8; background: transparent; border: none;"
        )
        lay.addWidget(ds)
        lay.addSpacing(16)

        # Separador fino
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {border_color}44; border: none;")
        lay.addWidget(sep)
        lay.addSpacing(14)

        # Bullets de características
        for bullet in bullets:
            row = QHBoxLayout()
            row.setSpacing(8)
            dot = QLabel("✓")
            dot.setFixedWidth(16)
            dot.setStyleSheet(
                f"color: {border_color}; font-weight: 700;"
                " background: transparent; border: none;"
            )
            txt = QLabel(bullet)
            txt.setStyleSheet(
                "color: #c8d5c8; font-size: 12px; background: transparent; border: none;"
            )
            row.addWidget(dot)
            row.addWidget(txt)
            row.addStretch()
            lay.addLayout(row)

        lay.addSpacing(20)
        lay.addStretch()

        # Botón de acción
        btn = QPushButton(btn_text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setObjectName("premiumButton" if accent else "cyanButton")
        btn.setFixedHeight(44)
        btn.clicked.connect(lambda _checked, r=resultado: self._elegir(r))
        lay.addWidget(btn)

        return card

    def _footer(self) -> QWidget:
        """Franja inferior con info de versión."""
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.setAlignment(Qt.AlignCenter)

        for text, style in [
            ("v2.0.0", "color: #ffd700; font-size: 12px;"),
            ("  |  ", "color: #2a4a2a; font-size: 12px;"),
            ("Método Base — Sistema de Planes Nutricionales",
             "color: #4a5f4a; font-size: 12px;"),
        ]:
            lbl = QLabel(text)
            lbl.setStyleSheet(style + " background: transparent;")
            lay.addWidget(lbl)

        return w

    # ── Animaciones ───────────────────────────────────────────────────────

    def _animar_entrada(self) -> None:
        """Fade-in al abrir."""
        self.setWindowOpacity(0)
        self._fade_in = QPropertyAnimation(self, b"windowOpacity")
        self._fade_in.setDuration(400)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_in.start()

    # ── Slots ─────────────────────────────────────────────────────────────

    def _elegir(self, resultado: ResultadoInicio) -> None:
        self._resultado = resultado
        # Animación de salida
        self._fade_out = QPropertyAnimation(self, b"windowOpacity")
        self._fade_out.setDuration(250)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.setEasingCurve(QEasingCurve.InCubic)
        self._fade_out.finished.connect(lambda: self.done(int(resultado)))
        self._fade_out.start()

    # ── API pública ───────────────────────────────────────────────────────

    @property
    def resultado(self) -> ResultadoInicio:
        return self._resultado



class ResultadoInicio(IntEnum):
    CANCELADO = 0
    GYM = 1
    USUARIO = 2


class PanelInicio(QDialog):
    """Diálogo de bienvenida con selector de perfil — tema verde premium."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Método Base — Bienvenida")
        self.setFixedSize(900, 620)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self._resultado = ResultadoInicio.CANCELADO
        self._build_ui()
        self._animar_entrada()

    # ── Construcción de UI ────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(60, 50, 60, 40)
        root.setSpacing(0)

        # Logo / título
        root.addLayout(self._header())
        root.addSpacerItem(QSpacerItem(0, 12, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Subtítulo
        sub = QLabel("Sistema de Gestión Nutricional y Gimnasio")
        sub.setObjectName("subheadline")
        sub.setAlignment(Qt.AlignHCenter)
        root.addWidget(sub)
        root.addSpacerItem(QSpacerItem(0, 32, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Pregunta
        pregunta = QLabel("¿Cómo deseas acceder?")
        pregunta.setStyleSheet("color: #e8f5e9; font-size: 20px; font-weight: 600;")
        pregunta.setAlignment(Qt.AlignHCenter)
        root.addWidget(pregunta)
        root.addSpacerItem(QSpacerItem(0, 28, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Tarjetas de elección
        cards = QHBoxLayout()
        cards.setSpacing(24)
        cards.addWidget(self._build_card(
            icon="🏢",
            title="Modo Gimnasio",
            desc="Gestión completa: clientes, suscripciones,\nclases, facturación y planes nutricionales.",
            resultado=ResultadoInicio.GYM,
            accent=True,
            badge_text="PREMIUM",
            btn_text="Acceder Premium →",
        ))
        cards.addWidget(self._build_card(
            icon="👤",
            title="Usuario Regular",
            desc="Genera tu plan nutricional personalizado\ny lleva el control de tu progreso.",
            resultado=ResultadoInicio.USUARIO,
            accent=False,
            badge_text="",
            btn_text="Acceder →",
        ))
        root.addLayout(cards)

        root.addSpacerItem(QSpacerItem(0, 28, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Footer
        footer = QHBoxLayout()
        footer.setAlignment(Qt.AlignCenter)

        ver = QLabel("v2.0.0")
        ver.setStyleSheet("color: #66bb6a; font-size: 12px;")
        footer.addWidget(ver)

        sep = QLabel("  |  ")
        sep.setStyleSheet("color: #4a5f4a;")
        footer.addWidget(sep)

        ayuda = QLabel("Método Base — Sistema de Planes Nutricionales")
        ayuda.setStyleSheet("color: #4a5f4a; font-size: 12px;")
        footer.addWidget(ayuda)

        root.addLayout(footer)

    def _header(self) -> QVBoxLayout:
        lay = QVBoxLayout()
        lay.setSpacing(8)

        # Punto verde decorativo
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
        badge_text: str = "",
        btn_text: str = "Acceder →",
    ) -> QWidget:
        """Crea una card interactiva para selección de modo."""
        card = QWidget()
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        card.setFixedHeight(300)

        # Sombra suave
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QColor("#ffd700") if accent else QColor("#22d3ee"))
        shadow.setOffset(0, 4)
        card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 28, 28, 28)
        card_layout.setSpacing(12)
        card_layout.setAlignment(Qt.AlignTop)

        # Badge premium
        if badge_text:
            badge = QLabel(badge_text)
            badge.setAlignment(Qt.AlignCenter)
            badge.setFixedWidth(90)
            badge.setStyleSheet("""
                QLabel {
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:0,
                        stop:0 #ffd700,
                        stop:1 #d4af37
                    );
                    color: #0a1409;
                    font-size: 10px;
                    font-weight: 700;
                    padding: 4px 12px;
                    border-radius: 12px;
                }
            """)
            card_layout.addWidget(badge, 0, Qt.AlignCenter)

        # Ícono
        ic = QLabel(icon)
        ic.setObjectName("card_icon")
        ic.setAlignment(Qt.AlignHCenter)
        card_layout.addWidget(ic)

        # Título
        tl = QLabel(title)
        tl.setObjectName("card_title")
        tl.setStyleSheet("font-size: 22px; font-weight: 700; color: #e8f5e9;")
        tl.setAlignment(Qt.AlignHCenter)
        card_layout.addWidget(tl)

        # Descripción
        ds = QLabel(desc)
        ds.setObjectName("card_desc")
        ds.setAlignment(Qt.AlignHCenter)
        ds.setWordWrap(True)
        card_layout.addWidget(ds)

        card_layout.addStretch()

        # Botón de acción
        btn = QPushButton(btn_text)
        btn.setCursor(Qt.PointingHandCursor)
        if accent:
            btn.setObjectName("premiumButton")
        else:
            btn.setObjectName("cyanButton")
        btn.clicked.connect(lambda _checked, r=resultado: self._elegir(r))
        card_layout.addWidget(btn)

        # Estilo del contenedor card
        border_color = "#ffd700" if accent else "#22d3ee"
        hover_color = "#1f3e1a" if accent else "#1a2e2e"
        card.setStyleSheet(f"""
            QWidget {{
                background-color: #1e2e1d;
                border: 2px solid {border_color};
                border-radius: 16px;
            }}
            QWidget:hover {{
                background-color: {hover_color};
            }}
        """)

        return card

    # ── Animaciones ───────────────────────────────────────────────────────

    def _animar_entrada(self) -> None:
        """Fade-in al abrir."""
        self.setWindowOpacity(0)
        self._fade_in = QPropertyAnimation(self, b"windowOpacity")
        self._fade_in.setDuration(400)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_in.start()

    # ── Slots ─────────────────────────────────────────────────────────────

    def _elegir(self, resultado: ResultadoInicio) -> None:
        self._resultado = resultado
        # Animación de salida
        self._fade_out = QPropertyAnimation(self, b"windowOpacity")
        self._fade_out.setDuration(250)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.setEasingCurve(QEasingCurve.InCubic)
        self._fade_out.finished.connect(lambda: self.done(int(resultado)))
        self._fade_out.start()

    # ── API pública ───────────────────────────────────────────────────────

    @property
    def resultado(self) -> ResultadoInicio:
        return self._resultado

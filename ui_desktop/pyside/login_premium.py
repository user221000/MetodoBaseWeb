# -*- coding: utf-8 -*-
"""
Login Premium — SaaS-Grade Login Screen (2026 Redesign).

Conversion-optimized login with visual product demo, results-oriented
copy, glassmorphism card, social proof, and micro-interactions.

Layout (1200×700):
  ┌──────────────────────────────────────────┬─────────────────────────┐
  │  PRODUCT DEMO + VALUE PROPOSITION        │   GLASSMORPHISM CARD    │
  │                                          │  ┌─────────────────────┐│
  │  "Haz que tus clientes vean             │  │  ⚡ Método Base     ││
  │   resultados… y te paguen más"          │  │                     ││
  │                                          │  │ [🏢 Dueño] [👤 Cli] ││
  │  ┌─ Dashboard Mockup ──────┐             │  │                     ││
  │  │  📊 12 planes hoy       │             │  │  Email              ││
  │  │  📲 8 WhatsApp enviados │             │  │  [_____________]    ││
  │  │  ⚡ 30s por plan        │             │  │                     ││
  │  └─────────────────────────┘             │  │  Contraseña         ││
  │                                          │  │  [_____________]    ││
  │  ✓ Planes en menos de 30 segundos       │  │                     ││
  │  ✓ Automatiza tu gym sin esfuerzo       │  │ [Entrar y generar]  ││
  │  ✓ Más resultados = más clientes        │  │                     ││
  │                                          │  │ +100 planes/semana  ││
  │                                          │  └─────────────────────┘│
  └──────────────────────────────────────────┴─────────────────────────┘

Color: Black & Yellow Neon Premium SaaS
Micro-interactions: Button glow, input focus, fade+slide entrance
"""
from __future__ import annotations

import re
from enum import IntEnum
from pathlib import Path
from typing import Optional

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    QRect,
    QSequentialAnimationGroup,
    QSize,
    QTimer,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontDatabase,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.services.auth_service import SesionActiva, crear_auth_service
from utils.helpers import resource_path
from utils.logger import logger

# ══════════════════════════════════════════════════════════════════════════════
# DESIGN TOKENS — Imported from centralized design system
# ══════════════════════════════════════════════════════════════════════════════
from design_system.tokens import Colors, Spacing, Radius, Typography


# ══════════════════════════════════════════════════════════════════════════════
# QSS STYLESHEETS
# ══════════════════════════════════════════════════════════════════════════════

QSS_INPUT = f"""
QLineEdit {{
    background: rgba(26, 26, 26, 0.8);
    color: {Colors.TEXT_PRIMARY};
    border: 1.5px solid {Colors.BORDER_SUBTLE};
    border-radius: {Radius.LG}px;
    padding: 0 {Spacing.LG}px;
    font-family: {Typography.FONT_FAMILY};
    font-size: {Typography.SIZE_MD}px;
    selection-background-color: {Colors.PRIMARY};
}}
QLineEdit:hover {{
    border: 1.5px solid {Colors.BORDER_DEFAULT};
    background: rgba(30, 30, 30, 0.9);
}}
QLineEdit:focus {{
    border: 1.5px solid {Colors.PRIMARY};
    background: rgba(26, 26, 26, 0.95);
}}
QLineEdit:disabled {{
    background: {Colors.BG_DEEP};
    color: {Colors.TEXT_SECONDARY};
    border: 1.5px solid {Colors.BORDER_SUBTLE};
}}
QLineEdit::placeholder {{
    color: {Colors.TEXT_HINT};
}}
"""

QSS_BUTTON_PRIMARY = f"""
QPushButton {{
    background: {Colors.PRIMARY};
    color: {Colors.TEXT_INVERSE};
    border: none;
    border-radius: {Radius.LG}px;
    font-family: {Typography.FONT_FAMILY};
    font-size: 15px;
    font-weight: 700;
    padding: 0 {Spacing.XL}px;
    letter-spacing: 0.3px;
}}
QPushButton:hover {{
    background: {Colors.PRIMARY_HOVER};
}}
QPushButton:pressed {{
    background: {Colors.PRIMARY_PRESSED};
}}
QPushButton:disabled {{
    background: {Colors.BG_HOVER};
    color: {Colors.TEXT_SECONDARY};
}}
"""

QSS_TAB_ACTIVE = f"""
QPushButton {{
    background: {Colors.PRIMARY};
    color: {Colors.TEXT_INVERSE};
    border: none;
    border-radius: {Radius.SM}px;
    font-family: {Typography.FONT_FAMILY};
    font-size: {Typography.SIZE_SM}px;
    font-weight: 600;
}}
"""

QSS_TAB_INACTIVE = f"""
QPushButton {{
    background: transparent;
    color: {Colors.TEXT_SECONDARY};
    border: none;
    border-radius: {Radius.SM}px;
    font-family: {Typography.FONT_FAMILY};
    font-size: {Typography.SIZE_SM}px;
    font-weight: 500;
}}
QPushButton:hover {{
    background: {Colors.BG_HOVER};
    color: {Colors.TEXT_PRIMARY};
}}
"""


# ══════════════════════════════════════════════════════════════════════════════
# UTILITY COMPONENTS
# ══════════════════════════════════════════════════════════════════════════════

_RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ResultadoLogin(IntEnum):
    """Login result codes."""
    CANCELADO = 0
    GYM = 1
    USUARIO = 2


def _create_label(
    text: str,
    size: int = Typography.SIZE_MD,
    bold: bool = False,
    color: str = Colors.TEXT_PRIMARY,
    align: Qt.AlignmentFlag = Qt.AlignLeft,
) -> QLabel:
    """Create a styled QLabel."""
    label = QLabel(text)
    font = QFont(Typography.FONT_FAMILY, size)
    font.setBold(bold)
    label.setFont(font)
    label.setStyleSheet(f"color: {color}; background: transparent;")
    label.setAlignment(align)
    return label


def _create_input(
    placeholder: str = "",
    password: bool = False,
    height: int = 50,
) -> QLineEdit:
    """Create a styled input field."""
    entry = AnimatedInput()
    entry.setPlaceholderText(placeholder)
    entry.setFixedHeight(height)
    entry.setStyleSheet(QSS_INPUT)
    if password:
        entry.setEchoMode(QLineEdit.Password)
    return entry


def _create_error_label() -> QLabel:
    """Create an error message label."""
    label = QLabel("")
    label.setWordWrap(True)
    label.setStyleSheet(
        f"color: {Colors.ERROR}; background: transparent; "
        f"font-family: {Typography.FONT_FAMILY}; font-size: {Typography.SIZE_SM}px;"
    )
    label.hide()
    return label


def _fade_in_widget(
    widget: QWidget,
    duration: int = 500,
    delay: int = 0,
    on_finished: object = None,
) -> None:
    """Apply a fade-in opacity animation to a widget.

    FIXED: Store previous effect and restore it after animation to avoid
    conflicts with QGraphicsDropShadowEffect on buttons and cards.
    """
    # Store any existing effect (e.g., drop shadow) to restore later
    previous_effect = widget.graphicsEffect()
    
    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(0.0)
    widget.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity")
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.OutCubic)

    def _cleanup() -> None:
        # Restore previous effect if it existed
        if previous_effect is not None:
            widget.setGraphicsEffect(previous_effect)
        else:
            widget.setGraphicsEffect(None)
        
        if callable(on_finished):
            on_finished()
        
        # Clean up animation references
        if hasattr(widget, '_fade_anim'):
            delattr(widget, '_fade_anim')
        if hasattr(widget, '_fade_effect'):
            delattr(widget, '_fade_effect')

    anim.finished.connect(_cleanup)
    # Keep reference to prevent garbage collection
    widget._fade_anim = anim
    widget._fade_effect = effect
    if delay > 0:
        QTimer.singleShot(delay, anim.start)
    else:
        anim.start()


# ══════════════════════════════════════════════════════════════════════════════
# ANIMATED INPUT — With focus border transition
# ══════════════════════════════════════════════════════════════════════════════

class AnimatedInput(QLineEdit):
    """Input field with animated focus state."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._is_focused = False

    def focusInEvent(self, event) -> None:
        self._is_focused = True
        self.setStyleSheet(
            QSS_INPUT + f"QLineEdit {{ border: 1.5px solid {Colors.PRIMARY}; }}"
        )
        super().focusInEvent(event)

    def focusOutEvent(self, event) -> None:
        self._is_focused = False
        self.setStyleSheet(QSS_INPUT)
        super().focusOutEvent(event)


# ══════════════════════════════════════════════════════════════════════════════
# ANIMATED BUTTON — With glow effect and scale feedback
# ══════════════════════════════════════════════════════════════════════════════

class PremiumButton(QPushButton):
    """Premium CTA button with hover glow (180ms) and press feedback.
    
    FIXED: Reduced glow intensity and made it optional to avoid rendering
    issues on Linux/Wayland systems.
    """

    def __init__(self, text: str, parent: QWidget | None = None, enable_glow: bool = True):
        super().__init__(text, parent)
        self.setFixedHeight(54)
        self.setCursor(Qt.PointingHandCursor)
        self._setup_style()
        self._enable_glow = enable_glow
        if self._enable_glow:
            self._setup_glow()

    def _setup_style(self) -> None:
        self.setObjectName("loginPrimaryBtn")

    def _setup_glow(self) -> None:
        """Setup shadow effect with safety checks for platform compatibility."""
        try:
            self._glow = QGraphicsDropShadowEffect(self)
            self._glow.setBlurRadius(2)
            self._glow.setColor(QColor(255, 235, 59, 60))  # FIXED: Reduced opacity
            self._glow.setOffset(0, 2)
            self.setGraphicsEffect(self._glow)

            self._glow_anim = QPropertyAnimation(self._glow, b"blurRadius")
            self._glow_anim.setDuration(180)
            self._glow_anim.setEasingCurve(QEasingCurve.OutCubic)
        except Exception as e:
            logger.warning(f"[LOGIN_PREMIUM] Could not setup button glow: {e}")
            self._enable_glow = False

    def enterEvent(self, event) -> None:
        if self._enable_glow and hasattr(self, '_glow_anim'):
            self._glow_anim.stop()
            self._glow_anim.setStartValue(self._glow.blurRadius())
            self._glow_anim.setEndValue(24)  # FIXED: Reduced from 32
            self._glow.setColor(QColor(255, 235, 59, 100))  # FIXED: Reduced from 140
            self._glow_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        if self._enable_glow and hasattr(self, '_glow_anim'):
            self._glow_anim.stop()
            self._glow_anim.setStartValue(self._glow.blurRadius())
            self._glow_anim.setEndValue(2)
            self._glow.setColor(QColor(255, 235, 59, 60))  # FIXED: Reduced from 100
            self._glow_anim.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)


# ══════════════════════════════════════════════════════════════════════════════
# ANIMATED TAB SWITCHER
# ══════════════════════════════════════════════════════════════════════════════

class RoleSwitcher(QFrame):
    """Animated role switcher (Gym Owner / Client)."""

    roleChanged = Signal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._current_role = 0
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setFixedHeight(52)
        self.setStyleSheet(f"""
            QFrame {{
                background: rgba(26, 26, 26, 0.6);
                border-radius: {Radius.LG}px;
                border: 1px solid {Colors.BORDER_SUBTLE};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self._btn_gym = QPushButton("🏢  Dueño de Gym")
        self._btn_gym.setCheckable(True)
        self._btn_gym.setChecked(True)
        self._btn_gym.setCursor(Qt.PointingHandCursor)
        self._btn_gym.setFixedHeight(44)
        self._btn_gym.setObjectName("loginTabActive")
        self._btn_gym.setToolTip("Acceso para dueños y administradores de gimnasio")

        self._btn_client = QPushButton("👤  Cliente")
        self._btn_client.setCheckable(True)
        self._btn_client.setCursor(Qt.PointingHandCursor)
        self._btn_client.setFixedHeight(44)
        self._btn_client.setObjectName("loginTabInactive")
        self._btn_client.setToolTip("Acceso para clientes del gimnasio")

        layout.addWidget(self._btn_gym, 1)
        layout.addWidget(self._btn_client, 1)

        self._btn_gym.clicked.connect(self._select_gym)
        self._btn_client.clicked.connect(self._select_client)

    def _select_gym(self) -> None:
        if self._current_role == 0:
            return
        self._current_role = 0
        self._update_styles()
        self.roleChanged.emit(0)

    def _select_client(self) -> None:
        if self._current_role == 1:
            return
        self._current_role = 1
        self._update_styles()
        self.roleChanged.emit(1)

    def _update_styles(self) -> None:
        if self._current_role == 0:
            self._btn_gym.setChecked(True)
            self._btn_gym.setObjectName("loginTabActive")
            self._btn_client.setChecked(False)
            self._btn_client.setObjectName("loginTabInactive")
        else:
            self._btn_gym.setChecked(False)
            self._btn_gym.setObjectName("loginTabInactive")
            self._btn_client.setChecked(True)
            self._btn_client.setObjectName("loginTabActive")
        self._btn_gym.style().unpolish(self._btn_gym)
        self._btn_gym.style().polish(self._btn_gym)
        self._btn_client.style().unpolish(self._btn_client)
        self._btn_client.style().polish(self._btn_client)

    @property
    def current_role(self) -> int:
        return self._current_role


# ══════════════════════════════════════════════════════════════════════════════
# FORM FIELD WITH LABEL
# ══════════════════════════════════════════════════════════════════════════════

class FormField(QWidget):
    """Form field with visible label, clear focus states, error support."""

    def __init__(
        self,
        label: str,
        placeholder: str = "",
        password: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._label_text = label
        self._has_error = False
        self._setup_ui(label, placeholder, password)

    def _setup_ui(self, label: str, placeholder: str, password: bool) -> None:
        self.setObjectName("transparentWidget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._label = _create_label(
            label,
            size=Typography.SIZE_SM,
            bold=True,
            color=Colors.TEXT_SECONDARY,
        )
        layout.addWidget(self._label)

        self._input = _create_input(placeholder, password)
        layout.addWidget(self._input)

        self._error = _create_error_label()
        layout.addWidget(self._error)

    @property
    def input(self) -> QLineEdit:
        return self._input

    def text(self) -> str:
        return self._input.text()

    def set_text(self, text: str) -> None:
        self._input.setText(text)

    def clear(self) -> None:
        self._input.clear()
        self.clear_error()

    def show_error(self, message: str) -> None:
        self._has_error = True
        self._error.setText(f"❌  {message}")
        self._error.show()
        self._input.setStyleSheet(
            QSS_INPUT + f"QLineEdit {{ border: 1.5px solid {Colors.ERROR}; }}"
        )

    def clear_error(self) -> None:
        self._has_error = False
        self._error.hide()
        self._error.setText("")
        self._input.setStyleSheet(QSS_INPUT)


# ══════════════════════════════════════════════════════════════════════════════
# SOCIAL PROOF WIDGET
# ══════════════════════════════════════════════════════════════════════════════

class SocialProofBar(QWidget):
    """Subtle social proof indicators below CTA."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("transparentWidget")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, Spacing.MD, 0, 0)
        layout.setSpacing(6)

        line1 = QLabel()
        line1.setText(
            f"<div style='text-align:center;color:{Colors.TEXT_HINT};"
            f"font-size:{Typography.SIZE_SM}px;font-family:{Typography.FONT_FAMILY};'>"
            f"⚡ <span style='color:{Colors.PRIMARY};font-weight:600;'>+100 planes</span>"
            f" generados esta semana</div>"
        )
        line1.setAlignment(Qt.AlignCenter)
        line1.setStyleSheet("background: transparent;")
        layout.addWidget(line1)

        line2 = QLabel()
        line2.setText(
            f"<div style='text-align:center;color:{Colors.TEXT_HINT};"
            f"font-size:{Typography.SIZE_XS}px;font-family:{Typography.FONT_FAMILY};'>"
            f"Usado por entrenadores en Guadalajara, CDMX y Monterrey</div>"
        )
        line2.setAlignment(Qt.AlignCenter)
        line2.setStyleSheet("background: transparent;")
        layout.addWidget(line2)


# ══════════════════════════════════════════════════════════════════════════════
# GYM LOGIN PANEL
# ══════════════════════════════════════════════════════════════════════════════

class GymLoginPanel(QWidget):
    """Login form for gym owners/admins."""

    autenticado = Signal(SesionActiva)
    solicitar_registro = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("transparentWidget")
        self._auth = crear_auth_service()
        self._sesion: Optional[SesionActiva] = None
        self._build_ui()

    @property
    def sesion(self) -> Optional[SesionActiva]:
        return self._sesion

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.LG)

        # Email field
        self._email_field = FormField(
            label="Correo electrónico",
            placeholder="tucorreo@tudominio.com",
        )
        layout.addWidget(self._email_field)

        # Password field
        self._password_field = FormField(
            label="Contraseña",
            placeholder="••••••••",
            password=True,
        )
        layout.addWidget(self._password_field)

        # Error label
        self._error = _create_error_label()
        layout.addWidget(self._error)

        # CTA button — results-oriented
        self._btn_login = PremiumButton("⚡  Entrar y generar planes")
        layout.addWidget(self._btn_login)
        self._btn_login.clicked.connect(self._attempt_login)

        # Microcopy — conversion-oriented (replaces "datos protegidos")
        micro = _create_label(
            "Tus clientes reciben su plan en menos de 30 segundos",
            size=Typography.SIZE_XS,
            color=Colors.TEXT_HINT,
            align=Qt.AlignHCenter,
        )
        layout.addWidget(micro)

        # Social proof
        self._social_proof = SocialProofBar()
        layout.addWidget(self._social_proof)

        layout.addSpacing(Spacing.SM)

        # Register link
        register_link = QLabel(
            f"<span style='color:{Colors.TEXT_SECONDARY};'>¿Primera vez? </span>"
            f"<a href='register' style='color:{Colors.PRIMARY};text-decoration:none;"
            f"font-weight:600;'>Registrar mi gym →</a>"
        )
        register_link.setOpenExternalLinks(False)
        register_link.setAlignment(Qt.AlignCenter)
        register_link.setStyleSheet(
            f"font-family: {Typography.FONT_FAMILY}; font-size: {Typography.SIZE_SM}px;"
            f"background: transparent;"
        )
        register_link.linkActivated.connect(lambda _: self.solicitar_registro.emit())
        layout.addWidget(register_link)

        # Keyboard shortcuts
        self._email_field.input.returnPressed.connect(
            lambda: self._password_field.input.setFocus()
        )
        self._password_field.input.returnPressed.connect(self._attempt_login)
        
    def limpiar(self) -> None:
        """Clear sensitive fields."""
        self._password_field.clear()
        self._email_field.clear_error()
        self._error.hide()
        
    def _attempt_login(self) -> None:
        """Validate and attempt login."""
        email = self._email_field.text().strip().lower()
        password = self._password_field.text()
        
        # Clear previous errors
        self._error.hide()
        self._email_field.clear_error()
        self._password_field.clear_error()
        
        # Validation
        if not email:
            self._email_field.show_error("El correo es obligatorio")
            return
        if not _RE_EMAIL.match(email):
            self._email_field.show_error("Ingresa un correo válido")
            return
        if not password:
            self._password_field.show_error("La contraseña es obligatoria")
            return
            
        # Attempt login
        self._btn_login.setEnabled(False)
        self._btn_login.setText("Verificando...")
        
        resultado = self._auth.login(email, password)
        
        self._btn_login.setEnabled(True)
        self._btn_login.setText("⚡  Entrar y generar planes")
        
        if not resultado.ok:
            msg = resultado.errores[0] if resultado.errores else "Credenciales incorrectas"
            self._error.setText(f"❌  {msg}")
            self._error.show()
            self._password_field.clear()
            logger.warning("[LOGIN_PREMIUM] Login attempt failed for gym")
            return
            
        sesion = resultado.sesion
        if sesion is None or sesion.rol not in ("gym", "admin"):
            self._error.setText("❌  Esta cuenta no tiene acceso de administrador")
            self._error.show()
            self._password_field.clear()
            return
            
        self._sesion = sesion
        self._password_field.clear()
        logger.info("[LOGIN_PREMIUM] Gym authenticated rol=%s", sesion.rol)
        self.autenticado.emit(sesion)


# ══════════════════════════════════════════════════════════════════════════════
# CLIENT LOGIN PANEL
# ══════════════════════════════════════════════════════════════════════════════

class ClientLoginPanel(QWidget):
    """Login/Register form for clients."""
    
    autenticado = Signal(SesionActiva)
    
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("transparentWidget")
        self._auth = crear_auth_service()
        self._sesion: Optional[SesionActiva] = None
        self._build_ui()
        
    @property
    def sesion(self) -> Optional[SesionActiva]:
        return self._sesion
        
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Stack for login/register views
        self._stack = QStackedWidget()
        self._stack.setObjectName("transparentWidget")
        layout.addWidget(self._stack)
        
        self._stack.addWidget(self._build_login_view())
        self._stack.addWidget(self._build_register_view())
        
    def _build_login_view(self) -> QWidget:
        """Build login form."""
        page = QWidget()
        page.setObjectName("transparentWidget")
        
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.LG)
        
        # Email field
        self._email_login = FormField(
            label="Correo electrónico",
            placeholder="tucorreo@tudominio.com",
        )
        layout.addWidget(self._email_login)
        
        # Password field
        self._password_login = FormField(
            label="Contraseña",
            placeholder="••••••••",
            password=True,
        )
        layout.addWidget(self._password_login)
        
        # Error label
        self._error_login = _create_error_label()
        layout.addWidget(self._error_login)
        
        # CTA button — results-oriented
        self._btn_client_login = PremiumButton("⚡  Entrar y ver mi plan")
        layout.addWidget(self._btn_client_login)
        self._btn_client_login.clicked.connect(self._attempt_login)

        # Microcopy — conversion-oriented
        micro = _create_label(
            "Tu plan personalizado te espera",
            size=Typography.SIZE_XS,
            color=Colors.TEXT_HINT,
            align=Qt.AlignHCenter,
        )
        layout.addWidget(micro)

        layout.addSpacing(Spacing.SM)

        # Register link
        register_link = QLabel(
            f"<span style='color:{Colors.TEXT_SECONDARY};'>¿Sin cuenta? </span>"
            f"<a href='register' style='color:{Colors.PRIMARY};text-decoration:none;"
            f"font-weight:600;'>Regístrate</a>"
        )
        register_link.setOpenExternalLinks(False)
        register_link.setAlignment(Qt.AlignCenter)
        register_link.setStyleSheet(
            f"font-family: {Typography.FONT_FAMILY}; font-size: {Typography.SIZE_SM}px;"
        )
        register_link.linkActivated.connect(lambda _: self._stack.setCurrentIndex(1))
        layout.addWidget(register_link)
        
        # Keyboard shortcuts
        self._email_login.input.returnPressed.connect(
            lambda: self._password_login.input.setFocus()
        )
        self._password_login.input.returnPressed.connect(self._attempt_login)
        
        return page
        
    def _build_register_view(self) -> QWidget:
        """Build registration form."""
        page = QWidget()
        page.setObjectName("transparentWidget")
        
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.MD)
        
        # Title
        title = _create_label(
            "Crear cuenta",
            size=Typography.SIZE_LG,
            bold=True,
            color=Colors.TEXT_PRIMARY,
            align=Qt.AlignHCenter,
        )
        layout.addWidget(title)
        
        layout.addSpacing(Spacing.SM)
        
        # Name fields
        self._reg_nombre = FormField(label="Nombre", placeholder="Tu nombre")
        layout.addWidget(self._reg_nombre)
        
        self._reg_apellido = FormField(label="Apellido", placeholder="Tu apellido")
        layout.addWidget(self._reg_apellido)
        
        self._reg_email = FormField(
            label="Correo electrónico",
            placeholder="tucorreo@tudominio.com",
        )
        layout.addWidget(self._reg_email)
        
        self._reg_password = FormField(
            label="Contraseña",
            placeholder="Mínimo 8 caracteres",
            password=True,
        )
        layout.addWidget(self._reg_password)
        
        self._reg_password2 = FormField(
            label="Confirmar contraseña",
            placeholder="Repite tu contraseña",
            password=True,
        )
        layout.addWidget(self._reg_password2)
        
        # Error label
        self._error_register = _create_error_label()
        layout.addWidget(self._error_register)
        
        # Register button
        self._btn_register = PremiumButton("✅  Crear cuenta")
        layout.addWidget(self._btn_register)
        self._btn_register.clicked.connect(self._attempt_register)
        
        # Back link
        back_link = QLabel(
            f"<a href='back' style='color:{Colors.ACCENT};text-decoration:none;'>"
            f"← Volver a inicio de sesión</a>"
        )
        back_link.setOpenExternalLinks(False)
        back_link.setAlignment(Qt.AlignCenter)
        back_link.setStyleSheet(
            f"font-family: {Typography.FONT_FAMILY}; font-size: {Typography.SIZE_SM}px;"
        )
        back_link.linkActivated.connect(lambda _: self._stack.setCurrentIndex(0))
        layout.addWidget(back_link)
        
        return page
        
    def limpiar(self) -> None:
        """Clear all fields."""
        self._password_login.clear()
        self._email_login.clear_error()
        self._error_login.hide()
        self._reg_password.clear()
        self._reg_password2.clear()
        self._error_register.hide()
        self._stack.setCurrentIndex(0)
        
    def _attempt_login(self) -> None:
        """Attempt client login."""
        email = self._email_login.text().strip().lower()
        password = self._password_login.text()
        
        self._error_login.hide()
        self._email_login.clear_error()
        self._password_login.clear_error()
        
        if not email or not _RE_EMAIL.match(email):
            self._email_login.show_error("Ingresa un correo válido")
            return
        if not password:
            self._password_login.show_error("La contraseña es obligatoria")
            return
            
        self._btn_client_login.setEnabled(False)
        self._btn_client_login.setText("Verificando...")
        
        resultado = self._auth.login(email, password)
        
        self._btn_client_login.setEnabled(True)
        self._btn_client_login.setText("⚡  Entrar y ver mi plan")
        
        if not resultado.ok:
            msg = resultado.errores[0] if resultado.errores else "Credenciales incorrectas"
            self._error_login.setText(f"❌  {msg}")
            self._error_login.show()
            self._password_login.clear()
            return
            
        self._sesion = resultado.sesion
        self._password_login.clear()
        logger.info("[LOGIN_PREMIUM] Client authenticated rol=%s", self._sesion.rol)
        self.autenticado.emit(self._sesion)
        
    def _attempt_register(self) -> None:
        """Attempt client registration."""
        nombre = self._reg_nombre.text().strip()
        apellido = self._reg_apellido.text().strip()
        email = self._reg_email.text().strip().lower()
        password = self._reg_password.text()
        password2 = self._reg_password2.text()
        
        self._error_register.hide()
        
        # Validations
        if not nombre:
            self._reg_nombre.show_error("El nombre es obligatorio")
            return
        if not apellido:
            self._reg_apellido.show_error("El apellido es obligatorio")
            return
        if not email or not _RE_EMAIL.match(email):
            self._reg_email.show_error("Ingresa un correo válido")
            return
        if not password:
            self._reg_password.show_error("La contraseña es obligatoria")
            return
        if password != password2:
            self._reg_password2.show_error("Las contraseñas no coinciden")
            return
            
        self._btn_register.setEnabled(False)
        self._btn_register.setText("Registrando...")
        
        resultado = self._auth.registrar(
            nombre=nombre, apellido=apellido, email=email, password=password
        )
        
        self._btn_register.setEnabled(True)
        self._btn_register.setText("✅  Crear cuenta")
        
        if not resultado.ok:
            msg = "\n".join(resultado.errores) if resultado.errores else "Error al registrar"
            self._error_register.setText(f"❌  {msg}")
            self._error_register.show()
            self._reg_password.clear()
            self._reg_password2.clear()
            return
            
        self._sesion = resultado.sesion
        self._reg_password.clear()
        self._reg_password2.clear()
        logger.info("[LOGIN_PREMIUM] Client registered")
        self.autenticado.emit(self._sesion)


# ══════════════════════════════════════════════════════════════════════════════
# PRODUCT DEMO MOCKUP WIDGET (LEFT SIDE — REPLACES PHOTO)
# ══════════════════════════════════════════════════════════════════════════════

class ProductDemoMockup(QFrame):
    """
    Visual mockup of the product in action — painted via QPainter.
    Shows dashboard KPIs, a mini plan card, and a WhatsApp message.
    Uses brand colors to look like a real running product.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMinimumHeight(220)
        self.setStyleSheet("background: transparent; border: none;")

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # ── Background card (dark surface with neon border glow) ──
        card_rect = QRect(0, 0, w, h)
        path = QPainterPath()
        path.addRoundedRect(card_rect.adjusted(1, 1, -1, -1), 16, 16)

        # Subtle dark fill
        p.fillPath(path, QColor(18, 18, 18, 230))

        # Neon yellow border (subtle)
        pen = QPen(QColor(255, 235, 59, 50), 1.0)
        p.setPen(pen)
        p.drawPath(path)

        # ── "Dashboard" title bar ──
        p.setPen(Qt.NoPen)
        title_bar = QRect(16, 12, w - 32, 32)
        tb_path = QPainterPath()
        tb_path.addRoundedRect(title_bar, 8, 8)
        p.fillPath(tb_path, QColor(26, 26, 26))

        # Window dots
        for i, color in enumerate(["#FF5F57", "#FEBC2E", "#28C840"]):
            p.setBrush(QColor(color))
            p.drawEllipse(26 + i * 18, 20, 10, 10)

        # Title text
        p.setPen(QColor(Colors.TEXT_SECONDARY))
        font = QFont(Typography.FONT_FAMILY, 9)
        font.setWeight(QFont.DemiBold)
        p.setFont(font)
        p.drawText(QRect(90, 12, w - 120, 32), Qt.AlignVCenter, "MetodoBase — Dashboard")

        y_start = 56

        # ── KPI Row ──
        kpi_data = [
            ("📊", "12", "Planes hoy", Colors.PRIMARY),
            ("📲", "8", "WhatsApp", Colors.SUCCESS),
            ("⚡", "30s", "Por plan", Colors.ACCENT_LIGHT),
        ]

        kpi_w = (w - 56) // 3
        for i, (icon, value, label, color) in enumerate(kpi_data):
            x = 16 + i * (kpi_w + 8)
            kpi_rect = QRect(x, y_start, kpi_w, 64)
            kpi_path = QPainterPath()
            kpi_path.addRoundedRect(kpi_rect, 10, 10)
            p.fillPath(kpi_path, QColor(26, 26, 26))

            # Value
            vfont = QFont(Typography.FONT_FAMILY, 18)
            vfont.setWeight(QFont.Bold)
            p.setFont(vfont)
            p.setPen(QColor(color))
            p.drawText(kpi_rect.adjusted(12, 6, 0, -22), Qt.AlignLeft | Qt.AlignVCenter, value)

            # Label
            lfont = QFont(Typography.FONT_FAMILY, 8)
            p.setFont(lfont)
            p.setPen(QColor(Colors.TEXT_HINT))
            p.drawText(kpi_rect.adjusted(12, 28, 0, -4), Qt.AlignLeft | Qt.AlignVCenter, label)

        y_cards = y_start + 80

        # ── Mini Plan Card ──
        plan_w = (w - 48) // 2
        plan_rect = QRect(16, y_cards, plan_w, 80)
        plan_path = QPainterPath()
        plan_path.addRoundedRect(plan_rect, 10, 10)
        p.fillPath(plan_path, QColor(26, 26, 26))

        # Plan accent bar
        bar_path = QPainterPath()
        bar_path.addRoundedRect(QRect(16, y_cards, 4, 80), 2, 2)
        p.fillPath(bar_path, QColor(Colors.PRIMARY))

        p.setPen(QColor(Colors.TEXT_PRIMARY))
        pfont = QFont(Typography.FONT_FAMILY, 9)
        pfont.setWeight(QFont.DemiBold)
        p.setFont(pfont)
        p.drawText(plan_rect.adjusted(14, 10, -8, -50), Qt.AlignLeft, "Plan: María López")

        p.setPen(QColor(Colors.TEXT_HINT))
        sfont = QFont(Typography.FONT_FAMILY, 8)
        p.setFont(sfont)
        p.drawText(plan_rect.adjusted(14, 32, -8, -26), Qt.AlignLeft, "2,100 kcal · Definición")
        p.drawText(plan_rect.adjusted(14, 48, -8, -8), Qt.AlignLeft, "5 comidas · Generado ✓")

        # ── WhatsApp Preview ──
        wa_rect = QRect(plan_w + 32, y_cards, plan_w, 80)
        wa_path = QPainterPath()
        wa_path.addRoundedRect(wa_rect, 10, 10)
        p.fillPath(wa_path, QColor(37, 211, 102, 20))

        # WA border
        p.setPen(QPen(QColor(37, 211, 102, 60), 1.0))
        p.drawRoundedRect(wa_rect, 10, 10)

        p.setPen(QColor(Colors.WHATSAPP_BG))
        wfont = QFont(Typography.FONT_FAMILY, 9)
        wfont.setWeight(QFont.DemiBold)
        p.setFont(wfont)
        p.drawText(wa_rect.adjusted(14, 10, -8, -50), Qt.AlignLeft, "📲 WhatsApp enviado")

        p.setPen(QColor(Colors.TEXT_HINT))
        p.setFont(sfont)
        p.drawText(wa_rect.adjusted(14, 32, -8, -26), Qt.AlignLeft, "María López recibió")
        p.drawText(wa_rect.adjusted(14, 48, -8, -8), Qt.AlignLeft, "su plan hace 12 seg")

        p.end()


# ══════════════════════════════════════════════════════════════════════════════
# VALUE PROPOSITION PANEL (LEFT SIDE — COMPLETE REDESIGN)
# ══════════════════════════════════════════════════════════════════════════════

class ValuePropositionPanel(QWidget):
    """
    Left panel: results-oriented copy + visual product demo mockup.
    Eliminates generic photo. Focuses on conversion.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        self.setObjectName("transparentWidget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.XXXL, Spacing.XXL, Spacing.XL, Spacing.XXL)
        layout.setSpacing(0)

        # ── Main headline (results-oriented) ──
        headline = QLabel()
        headline.setText(
            f"<div style='line-height:1.15;'>"
            f"<span style='color:{Colors.TEXT_PRIMARY};font-size:28px;"
            f"font-weight:700;font-family:{Typography.FONT_FAMILY};'>"
            f"Haz que tus clientes<br>vean resultados…<br>"
            f"<span style='color:{Colors.PRIMARY};'>y te paguen más</span>"
            f"</span></div>"
        )
        headline.setWordWrap(True)
        headline.setObjectName("transparentWidget")
        layout.addWidget(headline)

        layout.addSpacing(Spacing.MD)

        # ── Subtitle (action-oriented) ──
        subtitle = _create_label(
            "Genera planes personalizados y entrégalos\nen segundos por WhatsApp",
            size=Typography.SIZE_MD,
            color=Colors.TEXT_SECONDARY,
        )
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        layout.addSpacing(Spacing.XL)

        # ── Product demo mockup (replaces background image) ──
        self._mockup = ProductDemoMockup()
        layout.addWidget(self._mockup)

        layout.addSpacing(Spacing.XL)

        # ── Results bullets ──
        bullets = [
            ("⚡", "Planes en menos de 30 segundos"),
            ("🔄", "Automatiza tu gym sin esfuerzo"),
            ("📈", "Más resultados = más clientes retenidos"),
        ]

        for icon, text in bullets:
            bullet = self._create_result_bullet(icon, text)
            layout.addWidget(bullet)

        layout.addStretch()

    def _create_result_bullet(self, icon: str, text: str) -> QWidget:
        container = QWidget()
        container.setObjectName("transparentWidget")

        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(Spacing.MD)

        # Icon with yellow accent background
        icon_label = QLabel(icon)
        icon_label.setFixedSize(32, 32)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet(
            f"background: {Colors.PRIMARY_SOFT};"
            f"border-radius: {Radius.SM}px;"
            f"font-size: 15px;"
            f"border: 1px solid {Colors.BORDER_YELLOW};"
        )
        layout.addWidget(icon_label)

        # Text
        text_label = _create_label(text, size=Typography.SIZE_SM, color=Colors.TEXT_PRIMARY)
        layout.addWidget(text_label, 1)

        return container


# ══════════════════════════════════════════════════════════════════════════════
# LOGIN CARD (RIGHT SIDE)
# ══════════════════════════════════════════════════════════════════════════════

class LoginCard(QFrame):
    """
    Glassmorphism login card:
    - Semi-transparent background with subtle border
    - Deep soft shadow
    - Generous radius (XXL = 24px)
    - Wide padding (32px)
    """

    gym_autenticado = Signal(SesionActiva)
    usuario_autenticado = Signal(SesionActiva)
    solicitar_registro_gym = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._build_ui()
        self._setup_shadow()

    def _setup_shadow(self) -> None:
        """Setup shadow effect with safety checks for platform compatibility.
        
        FIXED: Added try-except to handle platforms where QGraphicsDropShadowEffect
        may not render correctly (e.g., Wayland).
        """
        try:
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(80)
            shadow.setColor(QColor(0, 0, 0, 200))
            shadow.setOffset(0, 20)
            self.setGraphicsEffect(shadow)
        except Exception as e:
            logger.warning(f"[LOGIN_PREMIUM] Could not setup card shadow: {e}")

    def _build_ui(self) -> None:
        self.setObjectName("LoginCard")
        self.setStyleSheet(f"""
            QFrame#LoginCard {{
                background: rgba(14, 14, 14, 0.85);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: {Radius.XXL}px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            Spacing.XXL, Spacing.XL, Spacing.XXL, Spacing.XL
        )
        layout.setSpacing(0)

        # Logo and brand
        logo_row = QHBoxLayout()
        logo_row.setAlignment(Qt.AlignCenter)
        logo_row.setSpacing(Spacing.SM)

        logo_icon = QLabel("⚡")
        logo_icon.setFixedSize(44, 44)
        logo_icon.setAlignment(Qt.AlignCenter)
        logo_icon.setStyleSheet(
            f"background: {Colors.PRIMARY};"
            f"border-radius: {Radius.LG}px;"
            f"color: {Colors.TEXT_INVERSE};"
            f"font-size: 22px;"
        )
        logo_row.addWidget(logo_icon)

        brand = _create_label("Método Base", size=Typography.SIZE_XL, bold=True)
        logo_row.addWidget(brand)
        layout.addLayout(logo_row)

        layout.addSpacing(6)

        # Tagline
        tagline = _create_label(
            "Tu gym genera resultados",
            size=Typography.SIZE_SM,
            color=Colors.TEXT_HINT,
            align=Qt.AlignHCenter,
        )
        layout.addWidget(tagline)

        layout.addSpacing(Spacing.XL)

        # Divider (subtle neon)
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 transparent, stop:0.5 {Colors.BORDER_YELLOW}, stop:1 transparent);"
            f"border: none;"
        )
        layout.addWidget(divider)

        layout.addSpacing(Spacing.XL)

        # Role switcher
        self._role_switcher = RoleSwitcher()
        layout.addWidget(self._role_switcher)

        layout.addSpacing(Spacing.XL)

        # Form stack
        self._stack = QStackedWidget()
        self._stack.setObjectName("transparentWidget")
        layout.addWidget(self._stack, 1)

        # Panels
        self._gym_panel = GymLoginPanel()
        self._stack.addWidget(self._gym_panel)

        self._client_panel = ClientLoginPanel()
        self._stack.addWidget(self._client_panel)

        # Connections
        self._role_switcher.roleChanged.connect(self._on_role_changed)
        self._gym_panel.autenticado.connect(self.gym_autenticado.emit)
        self._gym_panel.solicitar_registro.connect(self.solicitar_registro_gym.emit)
        self._client_panel.autenticado.connect(self.usuario_autenticado.emit)

    def _on_role_changed(self, role: int) -> None:
        if role == 0:
            self._client_panel.limpiar()
        else:
            self._gym_panel.limpiar()
        self._stack.setCurrentIndex(role)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN LOGIN WINDOW — Premium SaaS Grade
# ══════════════════════════════════════════════════════════════════════════════

class VentanaLoginPremium(QDialog):
    """
    Premium SaaS-Grade Login Dialog (2026 Redesign).

    - Two-panel: left = demo visual + copy, right = glassmorphism card
    - Deep black gradient (no background image dependency)
    - Fade + slide entrance animations
    - Results-oriented copy + social proof
    """

    login_exitoso = Signal(dict)

    WIN_W = 1200
    WIN_H = 700
    CARD_W = 460
    CARD_H = 640

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._sesion_gym: Optional[SesionActiva] = None
        self._sesion_usuario: Optional[SesionActiva] = None
        self._setup_window()
        self._build_ui()
        # FIXED: Check platform support before running animations
        # Entrance animations after show (disabled on problematic platforms)
        if self._should_enable_animations():
            QTimer.singleShot(50, self._run_entrance_animations)
        else:
            logger.info("[LOGIN_PREMIUM] Animations disabled for platform compatibility")
    
    def _should_enable_animations(self) -> bool:
        """Check if animations should be enabled based on platform.
        
        FIXED: Disable animations on platforms known to have rendering issues.
        """
        try:
            app = QApplication.instance()
            if app is None:
                return False
            platform = app.platformName().lower()
            # Disable on Wayland and other problematic platforms
            problematic = {"wayland", "wayland-egl", "wlroots", "offscreen"}
            return platform not in problematic
        except Exception:
            return False  # Safe default

    def _setup_window(self) -> None:
        self.setWindowTitle("Método Base — Iniciar Sesión")
        self.setFixedSize(self.WIN_W, self.WIN_H)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setStyleSheet(f"QDialog {{ background: {Colors.BG_DEEP}; }}")

    @property
    def sesion_gym(self) -> Optional[SesionActiva]:
        return self._sesion_gym

    @property
    def sesion_usuario(self) -> Optional[SesionActiva]:
        return self._sesion_usuario

    def _build_ui(self) -> None:
        # Background gradient (replaces FONDO.PNG)
        self._bg = QLabel(self)
        self._bg.setGeometry(0, 0, self.WIN_W, self.WIN_H)
        self._paint_gradient_bg()

        # Value proposition panel (left)
        self._value_panel = ValuePropositionPanel(self)
        self._value_panel.setGeometry(
            0, 0,
            self.WIN_W - self.CARD_W - Spacing.XL,
            self.WIN_H,
        )

        # Login card (right, vertically centered)
        card_x = self.WIN_W - self.CARD_W - Spacing.XXL
        card_y = (self.WIN_H - self.CARD_H) // 2

        self._login_card = LoginCard(self)
        self._login_card.setGeometry(card_x, card_y, self.CARD_W, self.CARD_H)

        # Connect signals
        self._login_card.gym_autenticado.connect(self._on_gym_autenticado)
        self._login_card.usuario_autenticado.connect(self._on_usuario_autenticado)
        self._login_card.solicitar_registro_gym.connect(self._on_registro_gym)

    def _paint_gradient_bg(self) -> None:
        """Paint a premium gradient background (eliminates FONDO.PNG dependency)."""
        pixmap = QPixmap(self.WIN_W, self.WIN_H)
        pixmap.fill(QColor(Colors.BG_DEEP))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Subtle radial-like gradient from top-left (brand warmth)
        grad = QLinearGradient(0, 0, self.WIN_W, self.WIN_H)
        grad.setColorAt(0.0, QColor(20, 18, 8, 255))     # Warm dark
        grad.setColorAt(0.3, QColor(10, 10, 10, 255))     # Pure dark
        grad.setColorAt(0.7, QColor(10, 10, 14, 255))     # Cool hint
        grad.setColorAt(1.0, QColor(8, 8, 10, 255))        # Pure dark

        painter.fillRect(0, 0, self.WIN_W, self.WIN_H, grad)

        # Subtle neon yellow glow spot (top-left for Z-pattern eye flow)
        glow = QLinearGradient(0, 0, 400, 400)
        glow.setColorAt(0.0, QColor(255, 235, 59, 8))
        glow.setColorAt(1.0, QColor(255, 235, 59, 0))
        painter.fillRect(0, 0, 400, 400, glow)

        # Subtle yellow glow (bottom-right, accent)
        glow2 = QLinearGradient(self.WIN_W - 300, self.WIN_H - 300, self.WIN_W, self.WIN_H)
        glow2.setColorAt(0.0, QColor(255, 235, 59, 0))
        glow2.setColorAt(1.0, QColor(255, 235, 59, 8))
        painter.fillRect(self.WIN_W - 300, self.WIN_H - 300, 300, 300, glow2)

        painter.end()
        self._bg.setPixmap(pixmap)

    def _run_entrance_animations(self) -> None:
        """Staggered fade + slide for left panel and login card."""
        # Left panel: fade in + slide from left
        _fade_in_widget(self._value_panel, duration=600, delay=0)

        # Login card: fade in + slide from right (staggered)
        # FIXED: Shadow is now preserved through the animation, no need to recreate
        _fade_in_widget(self._login_card, duration=600, delay=150)

    def _on_gym_autenticado(self, sesion: SesionActiva) -> None:
        self._sesion_gym = sesion
        self.login_exitoso.emit({"tipo": "gym", "sesion": sesion})
        logger.info("[LOGIN_PREMIUM] Closing with GYM result")
        self.done(int(ResultadoLogin.GYM))

    def _on_usuario_autenticado(self, sesion: SesionActiva) -> None:
        self._sesion_usuario = sesion
        self.login_exitoso.emit({"tipo": "usuario", "sesion": sesion})
        logger.info("[LOGIN_PREMIUM] Closing with USUARIO result")
        self.done(int(ResultadoLogin.USUARIO))

    def _on_registro_gym(self) -> None:
        logger.info("[LOGIN_PREMIUM] Gym registration requested")
        self.done(int(ResultadoLogin.GYM))


# ══════════════════════════════════════════════════════════════════════════════
# BACKWARD COMPATIBILITY ALIAS
# ══════════════════════════════════════════════════════════════════════════════

# Alias for drop-in replacement
VentanaLoginUnificada = VentanaLoginPremium

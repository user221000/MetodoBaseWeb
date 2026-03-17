# -*- coding: utf-8 -*-
"""
VentanaAuth — Diálogo de autenticación PySide6.

Flujo:
  1. Pantalla Login  → email + contraseña → AuthService.login()
  2. Pantalla Registro → nombre, apellido, email, contraseña x2 →
       DialogoPrivacidad → AuthService.registrar() →
       Pantalla de confirmación (ID mostrado una sola vez, con advertencia).

La UI NUNCA:
  - Registra en logs nombres, emails ni contraseñas.
  - Guarda contraseñas en atributos de instancia más allá del tiempo mínimo.
  - Muestra el password_hash ni tokens cifrados.
  - Permite saltar la aceptación de privacidad.

Seguridad UX aplicada:
  - Inputs tipo password con show/hide y barra de fortaleza.
  - Confirmación de contraseña con comparación visual.
  - Advertencia explícita de ID único: «solo visible esta vez, no compartas».
  - Botón "Copiar ID" con aviso TTL de 30 s; luego se oculta.
  - Mensajes de error genéricos ante credenciales incorrectas.
"""
from __future__ import annotations

import re
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QClipboard, QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.services.auth_service import AuthService, SesionActiva
from ui_desktop.pyside.widgets.secure_password_input import SecurePasswordInput
from utils.logger import logger


# ── RE email simple ──────────────────────────────────────────────────────────
_RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ── Helpers de estilo ─────────────────────────────────────────────────────────


def _lbl(texto: str, obj_name: str = "subheadline") -> QLabel:
    lbl = QLabel(texto)
    lbl.setObjectName(obj_name)
    return lbl


def _separador() -> QFrame:
    line = QFrame()
    line.setObjectName("separator_h")
    line.setFixedHeight(1)
    return line


def _btn(texto: str, primary: bool = False) -> QPushButton:
    b = QPushButton(texto)
    if primary:
        b.setObjectName("primaryButton")
    else:
        b.setObjectName("btn_text")
    return b


def _entry(placeholder: str = "", password: bool = False) -> QLineEdit:
    e = QLineEdit()
    e.setPlaceholderText(placeholder)
    if password:
        e.setEchoMode(QLineEdit.Password)
    return e


# ── Panel Login ───────────────────────────────────────────────────────────────


class _PanelLogin(QWidget):
    def __init__(self, parent: "VentanaAuth") -> None:
        super().__init__()
        self._padre = parent
        self._build()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(14)

        lay.addWidget(_lbl("Iniciar sesión", "title"), alignment=Qt.AlignHCenter)
        lay.addWidget(_lbl("Ingresa tus credenciales para continuar.", "subheadline"),
                      alignment=Qt.AlignHCenter)
        lay.addWidget(_separador())

        lay.addWidget(_lbl("Correo electrónico"))
        self._email = _entry("tu@correo.com")
        lay.addWidget(self._email)

        lay.addWidget(_lbl("Contraseña"))
        self._pw = SecurePasswordInput("Contraseña", show_strength_bar=False)
        lay.addWidget(self._pw)

        self._lbl_error = _lbl("", "error_label")
        self._lbl_error.setWordWrap(True)
        lay.addWidget(self._lbl_error)

        lay.addSpacing(4)
        self._btn_login = _btn("Iniciar sesión", primary=True)
        self._btn_login.clicked.connect(self._on_login)
        lay.addWidget(self._btn_login)

        lay.addSpacing(8)
        fila_reg = QHBoxLayout()
        fila_reg.addStretch()
        fila_reg.addWidget(_lbl("¿No tienes cuenta?", "caption"))
        btn_ir_reg = _btn("Regístrate aquí")
        btn_ir_reg.clicked.connect(self._padre.ir_registro)
        fila_reg.addWidget(btn_ir_reg)
        fila_reg.addStretch()
        lay.addLayout(fila_reg)
        lay.addStretch()

    def limpiar(self) -> None:
        self._email.clear()
        self._pw.clear()
        self._lbl_error.setText("")

    def set_error(self, msg: str) -> None:
        self._lbl_error.setText(msg)

    def _on_login(self) -> None:
        email = self._email.text().strip()
        pw = self._pw.value()

        self._lbl_error.setText("")
        self._btn_login.setEnabled(False)

        resultado = self._padre.auth.login(email, pw)

        # Limpiar contraseña de memoria tan rápido como sea posible
        self._pw.clear()

        self._btn_login.setEnabled(True)

        if resultado.ok:
            self._padre.accept()
        else:
            self.set_error(resultado.errores[0] if resultado.errores else "Error de autenticación.")


# ── Panel Registro ────────────────────────────────────────────────────────────


class _PanelRegistro(QWidget):
    def __init__(self, parent: "VentanaAuth") -> None:
        super().__init__()
        self._padre = parent
        self._build()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(12)

        lay.addWidget(_lbl("Crear cuenta", "title"), alignment=Qt.AlignHCenter)
        lay.addWidget(
            _lbl("Tus datos se cifran en la base de datos.", "subheadline"),
            alignment=Qt.AlignHCenter,
        )
        lay.addWidget(_separador())

        fila = QHBoxLayout()
        col_n = QVBoxLayout()
        col_n.addWidget(_lbl("Nombre *"))
        self._nombre = _entry("Tu nombre")
        col_n.addWidget(self._nombre)
        fila.addLayout(col_n)

        col_a = QVBoxLayout()
        col_a.addWidget(_lbl("Apellido *"))
        self._apellido = _entry("Tu apellido")
        col_a.addWidget(self._apellido)
        fila.addLayout(col_a)
        lay.addLayout(fila)

        lay.addWidget(_lbl("Correo electrónico *"))
        self._email = _entry("tu@correo.com")
        lay.addWidget(self._email)

        lay.addWidget(_lbl("Contraseña * (mín. 12 car., mayúsc., núm. y símbolo)"))
        self._pw = SecurePasswordInput("Contraseña", show_strength_bar=True)
        self._pw.strength_changed.connect(self._on_strength)
        lay.addWidget(self._pw)

        lay.addWidget(_lbl("Confirmar contraseña *"))
        self._pw2 = SecurePasswordInput("Repite la contraseña", show_strength_bar=False)
        self._pw2.changed.connect(self._verificar_coincidencia)
        lay.addWidget(self._pw2)

        self._lbl_match = QLabel("")
        self._lbl_match.setObjectName("caption")
        lay.addWidget(self._lbl_match)

        self._lbl_error = _lbl("", "error_label")
        self._lbl_error.setWordWrap(True)
        lay.addWidget(self._lbl_error)

        self._btn_reg = _btn("Crear cuenta", primary=True)
        self._btn_reg.setEnabled(False)
        self._btn_reg.clicked.connect(self._on_registrar)
        lay.addWidget(self._btn_reg)

        fila_login = QHBoxLayout()
        fila_login.addStretch()
        fila_login.addWidget(_lbl("¿Ya tienes cuenta?", "caption"))
        btn_ir_login = _btn("Iniciar sesión")
        btn_ir_login.clicked.connect(self._padre.ir_login)
        fila_login.addWidget(btn_ir_login)
        fila_login.addStretch()
        lay.addLayout(fila_login)
        lay.addStretch()

        self._strength_level = 0

    def limpiar(self) -> None:
        self._nombre.clear()
        self._apellido.clear()
        self._email.clear()
        self._pw.clear()
        self._pw2.clear()
        self._lbl_error.setText("")
        self._lbl_match.setText("")
        self._btn_reg.setEnabled(False)

    def _on_strength(self, nivel: int) -> None:
        self._strength_level = nivel
        self._actualizar_btn()

    def _verificar_coincidencia(self) -> None:
        self._actualizar_btn()

    def _actualizar_btn(self) -> None:
        # Habilitar solo si hay fortaleza mínima aceptable (≥1) y hay texto
        hay_texto = bool(
            self._nombre.text().strip()
            and self._apellido.text().strip()
            and self._email.text().strip()
            and self._pw.value()
        )
        self._btn_reg.setEnabled(hay_texto and self._strength_level >= 1)

        # Indicador de coincidencia
        p1 = self._pw.value()
        p2 = self._pw2.value()
        if p2:
            if p1 == p2:
                self._lbl_match.setText("✓ Las contraseñas coinciden")
                self._lbl_match.setStyleSheet("color: #30D158; font-size: 10px;")
            else:
                self._lbl_match.setText("✗ Las contraseñas no coinciden")
                self._lbl_match.setStyleSheet("color: #FF453A; font-size: 10px;")
        else:
            self._lbl_match.setText("")
            self._lbl_match.setStyleSheet("")

    def _on_registrar(self) -> None:
        nombre = self._nombre.text().strip()
        apellido = self._apellido.text().strip()
        email = self._email.text().strip()
        pw1 = self._pw.value()
        pw2 = self._pw2.value()

        self._lbl_error.setText("")

        if pw1 != pw2:
            self._lbl_error.setText("Las contraseñas no coinciden.")
            self._pw.clear()
            self._pw2.clear()
            return

        if not _RE_EMAIL.match(email):
            self._lbl_error.setText("El email no tiene formato válido.")
            return

        # Solicitar consentimiento de privacidad
        from ui_desktop.pyside.ventana_privacidad import DialogoPrivacidad
        dlg = DialogoPrivacidad(self)
        if not dlg.exec():
            self._pw.clear()
            self._pw2.clear()
            return

        self._btn_reg.setEnabled(False)
        resultado = self._padre.auth.registrar(nombre, apellido, email, pw1)

        # Limpiar contraseñas de memoria inmediatamente
        self._pw.clear()
        self._pw2.clear()

        self._btn_reg.setEnabled(True)

        if resultado.ok:
            self._padre._mostrar_confirmacion(resultado.sesion)
        else:
            self._lbl_error.setText(
                resultado.errores[0] if resultado.errores else "No se pudo registrar la cuenta."
            )


# ── Panel Confirmación (ID único, mostrado 1 vez) ─────────────────────────────


class _PanelConfirmacion(QWidget):
    def __init__(self, parent: "VentanaAuth") -> None:
        super().__init__()
        self._padre = parent
        self._timer: Optional[QTimer] = None
        self._build()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(14)

        lay.addWidget(_lbl("🎉 ¡Cuenta creada!", "title"), alignment=Qt.AlignHCenter)
        lay.addWidget(
            _lbl("Tu cuenta ha sido registrada de forma segura.", "subheadline"),
            alignment=Qt.AlignHCenter,
        )
        lay.addWidget(_separador())

        aviso_frame = QFrame()
        aviso_frame.setObjectName("warning_frame")
        aviso_inner = QVBoxLayout(aviso_frame)
        aviso_inner.setContentsMargins(12, 10, 12, 10)
        aviso_lbl = QLabel(
            "⚠️  Tu ID de usuario se muestra UNA SOLA VEZ.\n"
            "Guárdalo en un lugar seguro — no lo compartas con nadie."
        )
        aviso_lbl.setWordWrap(True)
        aviso_inner.addWidget(aviso_lbl)
        lay.addWidget(aviso_frame)

        lay.addSpacing(6)
        lay.addWidget(_lbl("Tu ID de usuario:", "caption"))

        fila_id = QHBoxLayout()
        self._lbl_id = QLabel("")
        self._lbl_id.setObjectName("id_display")
        self._lbl_id.setTextInteractionFlags(Qt.TextSelectableByMouse)
        fila_id.addWidget(self._lbl_id, 1)

        self._btn_copiar = _btn("📋 Copiar", primary=False)
        self._btn_copiar.clicked.connect(self._copiar_id)
        fila_id.addWidget(self._btn_copiar)
        lay.addLayout(fila_id)

        self._lbl_copiado = QLabel("")
        self._lbl_copiado.setObjectName("success_label")
        lay.addWidget(self._lbl_copiado)

        self._lbl_countdown = _lbl(
            "Este panel se cerrará en 30 s o pulsa Continuar.", "caption"
        )
        lay.addWidget(self._lbl_countdown)

        lay.addStretch()

        self._btn_continuar = _btn("Continuar →", primary=True)
        self._btn_continuar.clicked.connect(self._padre.accept)
        lay.addWidget(self._btn_continuar)

    def mostrar_id(self, id_usuario: str) -> None:
        self._lbl_id.setText(id_usuario)
        self._lbl_copiado.setText("")
        self._iniciar_countdown()

    def _copiar_id(self) -> None:
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self._lbl_id.text())
        self._lbl_copiado.setText("✓ Copiado al portapapeles")
        # Limpiar portapapeles auto después de 60 s (seguridad)
        QTimer.singleShot(60_000, lambda: clipboard.clear())

    def _iniciar_countdown(self) -> None:
        self._segundos = 30
        if self._timer:
            self._timer.stop()
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self) -> None:
        self._segundos -= 1
        self._lbl_countdown.setText(
            f"Este panel se cerrará en {self._segundos} s o pulsa Continuar."
        )
        if self._segundos <= 0:
            if self._timer:
                self._timer.stop()
            self._padre.accept()


# ── Ventana principal ─────────────────────────────────────────────────────────


class VentanaAuth(QDialog):
    """
    Diálogo de autenticación con stack Login / Registro / Confirmación.

    Uso::

        auth_svc = crear_auth_service()
        dlg = VentanaAuth(auth_service=auth_svc)
        if dlg.exec():
            sesion = auth_svc.sesion_activa  # SesionActiva(...)
    """

    _IDX_LOGIN = 0
    _IDX_REGISTRO = 1
    _IDX_CONFIRMACION = 2

    def __init__(
        self,
        auth_service: AuthService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.auth = auth_service
        self.setWindowTitle("Método Base — Acceso")
        self.setFixedSize(540, 700)
        self.setModal(True)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Banner header verde
        banner = QWidget()
        banner.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #0a1409,stop:1 #152515);"
            "border-bottom: 1px solid #2a4a2a;"
        )
        banner_lay = QHBoxLayout(banner)
        banner_lay.setContentsMargins(32, 16, 32, 16)

        dot = QLabel("●")
        dot.setStyleSheet("color: #39ff14; font-size: 14px; background: transparent;")
        banner_lay.addWidget(dot)

        brand = QLabel("  Método Base")
        brand.setStyleSheet(
            "color: #e8f5e9; font-size: 16px; font-weight: 700; background: transparent;"
        )
        banner_lay.addWidget(brand)
        banner_lay.addStretch()

        plan_lbl = QLabel("Usuario Regular")
        plan_lbl.setStyleSheet(
            "color: #66bb6a; font-size: 12px; background: transparent; padding: 2px 8px;"
            "border: 1px solid #2a4a2a; border-radius: 10px;"
        )
        banner_lay.addWidget(plan_lbl)

        root.addWidget(banner)

        # Card central
        card = QFrame()
        card.setObjectName("card")
        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(0, 0, 0, 0)

        self._stack = QStackedWidget()
        self._panel_login = _PanelLogin(self)
        self._panel_registro = _PanelRegistro(self)
        self._panel_confirm = _PanelConfirmacion(self)

        self._stack.addWidget(self._panel_login)       # idx 0
        self._stack.addWidget(self._panel_registro)    # idx 1
        self._stack.addWidget(self._panel_confirm)     # idx 2

        c_lay.addWidget(self._stack)
        root.addWidget(card)

    # ------------------------------------------------------------------
    # Navegación
    # ------------------------------------------------------------------

    def ir_login(self) -> None:
        self._panel_login.limpiar()
        self._stack.setCurrentIndex(self._IDX_LOGIN)

    def ir_registro(self) -> None:
        self._panel_registro.limpiar()
        self._stack.setCurrentIndex(self._IDX_REGISTRO)

    def _mostrar_confirmacion(self, sesion: SesionActiva) -> None:
        self._panel_confirm.mostrar_id(sesion.id_usuario)
        self._stack.setCurrentIndex(self._IDX_CONFIRMACION)

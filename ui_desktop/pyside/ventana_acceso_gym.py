# -*- coding: utf-8 -*-
"""
VentanaAccesoGym — Registro e inicio de sesión para cuentas de tipo 'gym'.

Flujo
─────
  · Primera vez (sin cuenta gym en la BD):
      Muestra el formulario de REGISTRO completo:
        - Credenciales:   nombre del gym, nombre de usuario, email, contraseña ×2
        - Perfil del gym: teléfono, dirección (3 líneas)
        - Redes sociales: Instagram, Facebook, TikTok, WhatsApp
      Al aceptar:
        → Crea cuenta rol='gym' en usuarios.db  (via AuthService)
        → Guarda datos de perfil/contacto en branding.json

  · Regreso (ya existe cuenta gym):
      Muestra la pantalla de LOGIN simplificada (email + contraseña).

Seguridad
─────────
  - Nunca almacena contraseñas en texto plano ni en atributos de instancia
    más del tiempo imprescindible.
  - Los campos email y contraseña se limpian tras cada operación.
  - Los mensajes de error son genéricos (no revelan si el email existe).
  - password_hash y email_idx solo viven dentro de AuthService/GestorUsuarios.
"""
from __future__ import annotations

import re
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.services.auth_service import AuthService, SesionActiva, crear_auth_service
from core.branding import branding
from utils.logger import logger

_RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ── Helpers de UI ────────────────────────────────────────────────────────────

def _lbl(texto: str, obj_name: str = "subheadline") -> QLabel:
    lbl = QLabel(texto)
    lbl.setObjectName(obj_name)
    return lbl


def _section(texto: str) -> QLabel:
    lbl = QLabel(texto)
    lbl.setObjectName("section_title")
    return lbl


def _entry(placeholder: str = "", password: bool = False) -> QLineEdit:
    e = QLineEdit()
    e.setPlaceholderText(placeholder)
    if password:
        e.setEchoMode(QLineEdit.Password)
    return e


def _separador() -> QFrame:
    f = QFrame()
    f.setObjectName("separator_h")
    f.setFixedHeight(1)
    return f


def _error_lbl() -> QLabel:
    lbl = QLabel("")
    lbl.setObjectName("error_label")
    lbl.setWordWrap(True)
    lbl.hide()
    return lbl


def _success_lbl() -> QLabel:
    lbl = QLabel("")
    lbl.setObjectName("success_label")
    lbl.setWordWrap(True)
    lbl.hide()
    return lbl


# ── Vista Registro ───────────────────────────────────────────────────────────

class _PaginaRegistro(QWidget):
    """
    Formulario de registro completo para un gym.

    Secciones
    ─────────
      1  Credenciales de acceso   (nombre gym, usuario, email, contraseñas)
      2  Datos de contacto         (teléfono, dirección)
      3  Redes sociales            (Instagram, Facebook, TikTok, WhatsApp)
    """

    def __init__(self, auth_service: AuthService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._auth = auth_service
        self._sesion: Optional[SesionActiva] = None
        self._build_ui()

    # ── API ──────────────────────────────────────────────────────────────────

    @property
    def sesion(self) -> Optional[SesionActiva]:
        return self._sesion

    def get_branding_data(self) -> dict:
        """Devuelve los campos extra (perfil + redes) para guardar en branding."""
        return {
            "nombre_gym":                self._e_nombre_gym.text().strip(),
            "tagline":                   "",
            "contacto.telefono":         self._e_telefono.text().strip(),
            "contacto.whatsapp":         self._e_telefono.text().strip(),
            "contacto.email":            self._e_email.text().strip().lower(),
            "contacto.direccion_linea1": self._e_dir1.text().strip(),
            "contacto.direccion_linea2": self._e_dir2.text().strip(),
            "contacto.direccion_linea3": self._e_dir3.text().strip(),
            "redes_sociales.instagram":  self._e_instagram.text().strip(),
            "redes_sociales.facebook":   self._e_facebook.text().strip(),
            "redes_sociales.tiktok":     self._e_tiktok.text().strip(),
        }

    def intenta_registrar(self) -> bool:
        """
        Valida campos y ejecuta el registro.

        Returns True si el registro fue exitoso.
        """
        self._lbl_error.hide()

        nombre_gym = self._e_nombre_gym.text().strip()
        nombre_usuario = self._e_nombre_usuario.text().strip()
        email = self._e_email.text().strip().lower()
        pw1 = self._e_pw1.text()
        pw2 = self._e_pw2.text()

        # ── Validaciones UI ──────────────────────────────────────────────
        errores: list[str] = []

        if not nombre_gym or len(nombre_gym) < 3:
            errores.append("El nombre del gym debe tener al menos 3 caracteres.")
        if not nombre_usuario or len(nombre_usuario) < 2:
            errores.append("El nombre de usuario debe tener al menos 2 caracteres.")
        if not email or not _RE_EMAIL.match(email):
            errores.append("El correo electrónico no tiene un formato válido.")
        if not pw1:
            errores.append("La contraseña no puede estar vacía.")
        elif pw1 != pw2:
            errores.append("Las contraseñas no coinciden.")

        if errores:
            self._mostrar_error("\n".join(f"• {e}" for e in errores))
            return False

        # ── Registro en AuthService ──────────────────────────────────────
        # nombre = display name del gym (nombre_gym), apellido = dummy "GYM"
        resultado = self._auth.registrar(
            nombre=nombre_gym,
            apellido=nombre_usuario,  # apellido se usa como "username display"
            email=email,
            password=pw1,
            rol="gym",
        )

        # Limpiar contraseña de memoria
        self._e_pw1.clear()
        self._e_pw2.clear()

        if not resultado.ok:
            self._mostrar_error("\n".join(resultado.errores) if resultado.errores
                                else "No se pudo completar el registro.")
            return False

        self._sesion = resultado.sesion
        logger.info("[GYM_AUTH] Cuenta gym registrada exitosamente")
        return True

    # ── Build ────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(0, 0, 12, 0)
        lay.setSpacing(6)

        # ── Sección 1: Credenciales ──────────────────────────────────────
        lay.addWidget(_section("ACCESO AL SISTEMA"))
        lay.addSpacerItem(QSpacerItem(0, 6, QSizePolicy.Minimum, QSizePolicy.Fixed))

        lay.addWidget(_lbl("Nombre del Gym *"))
        self._e_nombre_gym = _entry("Ej:  Fitness Elite Plaza")
        lay.addWidget(self._e_nombre_gym)

        lay.addSpacerItem(QSpacerItem(0, 6, QSizePolicy.Minimum, QSizePolicy.Fixed))
        lay.addWidget(_lbl("Nombre de usuario (para mostrar en el sistema) *"))
        self._e_nombre_usuario = _entry("Ej:  admin_gym  o  Carlos Rodríguez")
        lay.addWidget(self._e_nombre_usuario)

        lay.addSpacerItem(QSpacerItem(0, 6, QSizePolicy.Minimum, QSizePolicy.Fixed))
        lay.addWidget(_lbl("Correo electrónico *"))
        self._e_email = _entry("Ej:  admin@fitnesselite.com")
        lay.addWidget(self._e_email)

        lay.addSpacerItem(QSpacerItem(0, 6, QSizePolicy.Minimum, QSizePolicy.Fixed))
        lay.addWidget(_lbl("Contraseña *  (mín. 12 car., mayús., número y símbolo)"))
        self._e_pw1 = _entry("Contraseña", password=True)
        lay.addWidget(self._e_pw1)

        lay.addSpacerItem(QSpacerItem(0, 4, QSizePolicy.Minimum, QSizePolicy.Fixed))
        lay.addWidget(_lbl("Confirmar contraseña *"))
        self._e_pw2 = _entry("Repite la contraseña", password=True)
        lay.addWidget(self._e_pw2)

        lay.addSpacerItem(QSpacerItem(0, 14, QSizePolicy.Minimum, QSizePolicy.Fixed))
        lay.addWidget(_separador())
        lay.addSpacerItem(QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # ── Sección 2: Contacto ──────────────────────────────────────────
        lay.addWidget(_section("DATOS DE CONTACTO"))
        lay.addSpacerItem(QSpacerItem(0, 6, QSizePolicy.Minimum, QSizePolicy.Fixed))

        lay.addWidget(_lbl("Teléfono (opcional)"))
        self._e_telefono = _entry("Ej:  3312345678")
        lay.addWidget(self._e_telefono)

        lay.addSpacerItem(QSpacerItem(0, 6, QSizePolicy.Minimum, QSizePolicy.Fixed))
        lay.addWidget(_lbl("Dirección — Calle y Número (opcional)"))
        self._e_dir1 = _entry("Ej:  Av. Insurgentes Sur 1234")
        lay.addWidget(self._e_dir1)

        lay.addSpacerItem(QSpacerItem(0, 4, QSizePolicy.Minimum, QSizePolicy.Fixed))
        lay.addWidget(_lbl("Colonia / Barrio (opcional)"))
        self._e_dir2 = _entry("Ej:  Col. Insurgentes Mixcoac")
        lay.addWidget(self._e_dir2)

        lay.addSpacerItem(QSpacerItem(0, 4, QSizePolicy.Minimum, QSizePolicy.Fixed))
        lay.addWidget(_lbl("Ciudad y Código Postal (opcional)"))
        self._e_dir3 = _entry("Ej:  03920 Ciudad de México, CDMX")
        lay.addWidget(self._e_dir3)

        lay.addSpacerItem(QSpacerItem(0, 14, QSizePolicy.Minimum, QSizePolicy.Fixed))
        lay.addWidget(_separador())
        lay.addSpacerItem(QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # ── Sección 3: Redes sociales ────────────────────────────────────
        lay.addWidget(_section("REDES SOCIALES (opcionales)"))
        lay.addSpacerItem(QSpacerItem(0, 6, QSizePolicy.Minimum, QSizePolicy.Fixed))

        lay.addWidget(_lbl("Instagram"))
        self._e_instagram = _entry("Ej:  @fitnesselite")
        lay.addWidget(self._e_instagram)

        lay.addSpacerItem(QSpacerItem(0, 4, QSizePolicy.Minimum, QSizePolicy.Fixed))
        lay.addWidget(_lbl("Facebook"))
        self._e_facebook = _entry("Ej:  facebook.com/fitnesselite")
        lay.addWidget(self._e_facebook)

        lay.addSpacerItem(QSpacerItem(0, 4, QSizePolicy.Minimum, QSizePolicy.Fixed))
        lay.addWidget(_lbl("TikTok"))
        self._e_tiktok = _entry("Ej:  @fitnesselite.ok")
        lay.addWidget(self._e_tiktok)

        lay.addStretch()

        scroll.setWidget(inner)

        # Label de error
        self._lbl_error = _error_lbl()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(8)
        outer.addWidget(scroll)
        outer.addWidget(self._lbl_error)

    def _mostrar_error(self, msg: str) -> None:
        self._lbl_error.setText(msg)
        self._lbl_error.show()


# ── Vista Login ──────────────────────────────────────────────────────────────

class _PaginaLogin(QWidget):
    """
    Pantalla simplificada de inicio de sesión para cuentas gym existentes.
    Solo pide email y contraseña.
    """

    def __init__(self, auth_service: AuthService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._auth = auth_service
        self._sesion: Optional[SesionActiva] = None
        self._build_ui()

    @property
    def sesion(self) -> Optional[SesionActiva]:
        return self._sesion

    def intenta_login(self) -> bool:
        self._lbl_error.hide()

        email = self._e_email.text().strip().lower()
        pw = self._e_pw.text()

        if not email or not pw:
            self._mostrar_error("Ingresa tu correo y contraseña.")
            self._e_pw.clear()
            return False

        resultado = self._auth.login(email, pw)
        self._e_pw.clear()

        if not resultado.ok:
            msg = resultado.errores[0] if resultado.errores else "Credenciales incorrectas."
            self._mostrar_error(msg)
            return False

        # Verificar que la cuenta sea de tipo gym
        if resultado.sesion and resultado.sesion.rol != "gym":
            self._mostrar_error("Esta cuenta no tiene acceso al modo GYM.")
            self._auth.logout()
            return False

        self._sesion = resultado.sesion
        return True

    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lay.addStretch()

        icon = QLabel("🏋️")
        icon.setAlignment(Qt.AlignCenter)
        icon.setObjectName("card_icon")
        lay.addWidget(icon)

        titulo = QLabel("Inicia sesión en tu Gym")
        titulo.setObjectName("headline")
        titulo.setAlignment(Qt.AlignCenter)
        lay.addWidget(titulo)

        sub = QLabel("Usa las credenciales que registraste al configurar el gym.")
        sub.setObjectName("subheadline")
        sub.setAlignment(Qt.AlignCenter)
        sub.setWordWrap(True)
        lay.addWidget(sub)

        lay.addSpacerItem(QSpacerItem(0, 24, QSizePolicy.Minimum, QSizePolicy.Fixed))

        lay.addWidget(_lbl("Correo electrónico"))
        self._e_email = _entry("admin@tusgym.com")
        lay.addWidget(self._e_email)

        lay.addSpacerItem(QSpacerItem(0, 8, QSizePolicy.Minimum, QSizePolicy.Fixed))
        lay.addWidget(_lbl("Contraseña"))
        self._e_pw = _entry("Contraseña", password=True)
        self._e_pw.returnPressed.connect(lambda: None)  # conectado desde VentanaAccesoGym
        lay.addWidget(self._e_pw)

        self._lbl_error = _error_lbl()
        lay.addWidget(self._lbl_error)
        lay.addStretch()

    def _mostrar_error(self, msg: str) -> None:
        self._lbl_error.setText(f"⚠  {msg}")
        self._lbl_error.show()


# ── Diálogo principal ────────────────────────────────────────────────────────

class VentanaAccesoGym(QDialog):
    """
    Diálogo de acceso al módulo GYM.

    · Si NO existe ninguna cuenta gym → muestra registro completo.
    · Si ya existe cuenta gym → muestra login.

    El llamador obtiene la sesión activa via `.sesion_gym`.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._sesion: Optional[SesionActiva] = None
        self._auth_service: AuthService = crear_auth_service()
        self._modo: str = "registro"   # 'registro' | 'login'

        self.setWindowTitle("Acceso GYM — Método Base")
        self.setMinimumSize(540, 640)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        # Determinar modo
        try:
            from src.gestor_usuarios import GestorUsuarios
            from pathlib import Path
            from config.constantes import CARPETA_REGISTROS
            _gu = GestorUsuarios(crypto_service=self._auth_service._gu._crypto)
            existe = _gu.existe_cuenta_gym()
        except Exception:
            existe = False

        self._modo = "login" if existe else "registro"
        self._build_ui()

    # ── API pública ──────────────────────────────────────────────────────────

    @property
    def sesion_gym(self) -> Optional[SesionActiva]:
        """Sesión activa del gym tras autenticación exitosa, o None."""
        return self._sesion

    # ── Build ────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(36, 28, 36, 28)
        outer.setSpacing(0)

        # ── Header ───────────────────────────────────────────────────────
        hdr_title_text = (
            "Configura tu Gym" if self._modo == "registro" else "Bienvenido de vuelta"
        )
        hdr_sub_text = (
            "Crea tu cuenta de administrador para el módulo GYM."
            if self._modo == "registro"
            else "Inicia sesión con el correo y contraseña de tu gym."
        )

        hdr = QLabel("● Método Base  —  Módulo GYM")
        hdr.setObjectName("accent")
        outer.addWidget(hdr)
        outer.addSpacerItem(QSpacerItem(0, 16, QSizePolicy.Minimum, QSizePolicy.Fixed))

        title = QLabel(hdr_title_text)
        title.setObjectName("title")
        outer.addWidget(title)

        sub = QLabel(hdr_sub_text)
        sub.setObjectName("subheadline")
        sub.setWordWrap(True)
        outer.addWidget(sub)

        outer.addSpacerItem(QSpacerItem(0, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))
        outer.addWidget(_separador())
        outer.addSpacerItem(QSpacerItem(0, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # ── Stacked content ───────────────────────────────────────────────
        self._stack = QStackedWidget()
        outer.addWidget(self._stack)

        if self._modo == "registro":
            self._pag_reg = _PaginaRegistro(self._auth_service)
            self._stack.addWidget(self._pag_reg)
        else:
            self._pag_login = _PaginaLogin(self._auth_service)
            self._stack.addWidget(self._pag_login)

        outer.addSpacerItem(QSpacerItem(0, 16, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # ── Botones ───────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._btn_accion = QPushButton(
            "Crear cuenta y continuar  →" if self._modo == "registro" else "Iniciar sesión  →"
        )
        self._btn_accion.clicked.connect(self._on_accion)
        btn_row.addWidget(self._btn_accion)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("btn_secondary")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        outer.addLayout(btn_row)

        # Link para cambiar de login → registro (en caso de querer crear otra cuenta)
        if self._modo == "login":
            outer.addSpacerItem(QSpacerItem(0, 8, QSizePolicy.Minimum, QSizePolicy.Fixed))
            lnk = QPushButton("Crear nueva cuenta de gym")
            lnk.setObjectName("btn_text")
            lnk.setFixedHeight(28)
            lnk.clicked.connect(self._cambiar_a_registro)
            outer.addWidget(lnk, alignment=Qt.AlignCenter)

    # ── Slots ────────────────────────────────────────────────────────────────

    def _on_accion(self) -> None:
        if self._modo == "registro":
            self._ejecutar_registro()
        else:
            self._ejecutar_login()

    def _ejecutar_registro(self) -> None:
        ok = self._pag_reg.intenta_registrar()
        if not ok:
            return
        # Persistir datos de contacto + branding
        _guardar_branding(self._pag_reg.get_branding_data())
        self._sesion = self._pag_reg.sesion
        self.accept()

    def _ejecutar_login(self) -> None:
        ok = self._pag_login.intenta_login()
        if not ok:
            return
        self._sesion = self._pag_login.sesion
        self.accept()

    def _cambiar_a_registro(self) -> None:
        """Añade la página de registro al stack si aún no existe y la muestra."""
        if not hasattr(self, "_pag_reg"):
            self._pag_reg = _PaginaRegistro(self._auth_service)
            self._stack.addWidget(self._pag_reg)
        self._modo = "registro"
        self._stack.setCurrentWidget(self._pag_reg)
        self._btn_accion.setText("Crear cuenta y continuar  →")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _guardar_branding(datos: dict) -> None:
    """Persiste los datos del gym en branding.json."""
    try:
        for key, valor in datos.items():
            if valor:
                branding.set(key, valor)
        branding.guardar()
        logger.info("[GYM_AUTH] Branding guardado para nuevo gym: %s",
                    datos.get("nombre_gym", ""))
    except Exception as exc:
        logger.warning("[GYM_AUTH] No se pudo guardar branding: %s", exc)

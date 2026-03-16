# -*- coding: utf-8 -*-
"""
DialogoPrivacidad — Consentimiento informado GDPR/LGPD antes del registro.

El usuario DEBE aceptar para continuar; el rechazo cierra el diálogo
y devuelve QDialog.Rejected, abortando el flujo de registro.

Contenido:
  - Qué datos recopilamos (nombre, apellido, email, perfil físico).
  - Cómo los protegemos (cifrado Fernet, bcrypt, jamás en texto plano).
  - Para qué se usan (generar planes nutricionales personalizados).
  - Derechos del usuario (acceso, rectificación, eliminación).
  - Botones Aceptar / Rechazar.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from utils.logger import logger

_POLITICA_TEXTO = """
<h3 style="color:#9B4FB0;">Aviso de Privacidad — Método Base</h3>

<p><b>¿Qué datos recopilamos?</b><br>
Al registrarte almacenamos: nombre, apellido, correo electrónico, datos
antropométricos opcionales (peso, estatura, grasa corporal) y el objetivo
de entrenamiento que indiques. <i>No recopilamos datos de pago ni de
geolocalización.</i></p>

<p><b>¿Cómo protegemos tus datos?</b></p>
<ul>
  <li>Las contraseñas se almacenan como un hash <b>bcrypt</b> (nunca en texto
      plano). Un atacante que acceda a la base de datos no podrá leer tu
      contraseña.</li>
  <li>Los campos de identidad (nombre, apellido, email) se cifran con
      <b>AES-128 Fernet</b> antes de guardarlos. La clave de cifrado se
      gestiona fuera del código fuente.</li>
  <li>Los registros de actividad (logs) nunca incluyen datos personales.</li>
  <li>Los archivos exportados (Excel, CSV) solo contienen datos no sensibles;
      no incluyen contraseñas ni tokens cifrados.</li>
</ul>

<p><b>¿Para qué usamos tus datos?</b><br>
Exclusivamente para generar planes nutricionales personalizados dentro de
esta aplicación. <b>No vendemos ni compartimos tu información con terceros.</b></p>

<p><b>Tus derechos</b><br>
Puedes solicitar al administrador: acceso a tus datos, rectificación,
portabilidad o eliminación (derecho al olvido). Contacta al responsable
de la instalación.</p>

<p><b>Retención</b><br>
Tus datos se conservan mientras tengas una cuenta activa. Al desactivarla,
los datos quedan marcados como inactivos y pueden eliminarse a petición.</p>

<p style="color:#FF9800;"><b>⚠️  Al pulsar «Acepto» confirmas que has leído
este aviso y consientes el tratamiento de tus datos según lo descrito.</b></p>
"""


class DialogoPrivacidad(QDialog):
    """
    Modal de consentimiento de privacidad.

    Devuelve ``QDialog.Accepted`` solo si el usuario hace clic en «Acepto».
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Aviso de Privacidad")
        self.setFixedSize(540, 540)
        self.setModal(True)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(12)

        # Título
        titulo = QLabel("Aviso de Privacidad y Consentimiento")
        titulo.setAlignment(Qt.AlignHCenter)
        titulo.setStyleSheet("color: #9B4FB0; font-size: 18px; font-weight: bold;")
        root.addWidget(titulo)

        # Área con scroll para la política
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { border: 1px solid #444444; border-radius: 8px; background-color: #1A1A1A; }"
        )
        contenido = QLabel(_POLITICA_TEXTO)
        contenido.setWordWrap(True)
        contenido.setTextFormat(Qt.RichText)
        contenido.setStyleSheet(
            "color: #F5F5F5; font-size: 11px; padding: 14px; background-color: #1A1A1A; line-height: 1.5;"
        )
        contenido.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        scroll.setWidget(contenido)
        root.addWidget(scroll, 1)

        # Aviso
        aviso = QLabel("Debes desplazarte y leer el aviso completo antes de continuar.")
        aviso.setAlignment(Qt.AlignHCenter)
        aviso.setStyleSheet("color: #B8B8B8; font-size: 10px;")
        root.addWidget(aviso)

        # Botones
        fila = QHBoxLayout()
        btn_rechazar = QPushButton("Rechazar")
        btn_rechazar.setStyleSheet(
            "QPushButton { background-color: transparent; border: 1px solid #F44336;"
            " color: #F44336; border-radius: 8px; padding: 9px 20px; font-size: 13px; }"
            "QPushButton:hover { background-color: #2A0A0A; }"
        )
        btn_rechazar.clicked.connect(self.reject)

        btn_aceptar = QPushButton("Acepto — Continuar")
        btn_aceptar.setStyleSheet(
            "QPushButton { background-color: #9B4FB0; color: #FFFFFF; border: none;"
            " border-radius: 8px; padding: 9px 20px; font-size: 13px; font-weight: bold; }"
            "QPushButton:hover { background-color: #B565C6; }"
        )
        btn_aceptar.clicked.connect(self._on_aceptar)

        fila.addWidget(btn_rechazar)
        fila.addStretch()
        fila.addWidget(btn_aceptar)
        root.addLayout(fila)

    def _on_aceptar(self) -> None:
        logger.info("[PRIVACIDAD] Usuario aceptó aviso de privacidad")
        self.accept()

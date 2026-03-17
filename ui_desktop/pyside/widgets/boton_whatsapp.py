# -*- coding: utf-8 -*-
"""
Botón WhatsApp con diseño estandarizado.
Color oficial de WhatsApp: #25d366 — NO modificar.
"""
import urllib.parse

from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices

from utils.logger import logger


class BotonWhatsApp(QPushButton):
    """
    Botón para enviar mensaje por WhatsApp.
    Usa siempre el color verde oficial de WhatsApp.
    """

    def __init__(self, telefono: str = "", mensaje: str = "", parent=None):
        super().__init__(parent)
        self.telefono = telefono
        self.mensaje = mensaje

        self.setText("📱 Enviar por WhatsApp")
        self.setObjectName("btnWhatsApp")
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(self.enviar_whatsapp)

    def enviar_whatsapp(self) -> None:
        """Abre WhatsApp Web con el mensaje predefinido."""
        if not self.telefono:
            logger.warning("⚠️  No hay teléfono configurado para WhatsApp")
            return

        # Solo dígitos
        telefono_limpio = "".join(filter(str.isdigit, self.telefono))
        mensaje_encoded = urllib.parse.quote(self.mensaje)
        url = f"https://wa.me/{telefono_limpio}?text={mensaje_encoded}"

        QDesktopServices.openUrl(QUrl(url))
        logger.info("📱 Abriendo WhatsApp para %s", telefono_limpio)

    def set_telefono(self, telefono: str) -> None:
        """Actualiza el número de teléfono."""
        self.telefono = telefono

    def set_mensaje(self, mensaje: str) -> None:
        """Actualiza el mensaje."""
        self.mensaje = mensaje

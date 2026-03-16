# -*- coding: utf-8 -*-
"""
Wizard de configuración inicial — PySide6.
Reemplaza gui/wizard_onboarding.py.
Se muestra cuando branding.get('nombre_gym') está vacío.
"""

import os
import shutil

from PySide6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QColorDialog, QFileDialog, QMessageBox,
    QScrollArea, QWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap

from core.branding import branding
from utils.logger import logger


# ── Constantes de validación ───────────────────────────────────────────────


def _validar_nombre_gym(valor: str) -> tuple[bool, str]:
    valor = valor.strip()
    if not valor:
        return False, "El nombre del gym es obligatorio"
    if len(valor) < 3:
        return False, "Mínimo 3 caracteres"
    return True, ""


def _validar_texto_corto(valor: str) -> tuple[bool, str]:
    if len(valor.strip()) > 120:
        return False, "Máximo 120 caracteres"
    return True, ""


def _validar_telefono(valor: str) -> tuple[bool, str]:
    valor = valor.strip()
    if not valor:
        return True, ""  # opcional
    if not valor.isdigit():
        return False, "Solo dígitos, sin espacios ni símbolos"
    return True, ""


def _validar_instagram(valor: str) -> tuple[bool, str]:
    if len(valor.strip()) > 80:
        return False, "Máximo 80 caracteres"
    return True, ""


# ── Helpers UI ──────────────────────────────────────────────────────────────


def _lbl_seccion(texto: str) -> QLabel:
    lbl = QLabel(texto)
    lbl.setStyleSheet("color: #8E8E93; font-size: 12px; background: transparent;")
    return lbl


def _lbl_estado() -> QLabel:
    lbl = QLabel("")
    lbl.setWordWrap(True)
    lbl.setStyleSheet("color: #8E8E93; font-size: 10px; background: transparent;")
    return lbl


def _entry(placeholder: str = "") -> QLineEdit:
    e = QLineEdit()
    e.setPlaceholderText(placeholder)
    return e


# ── Páginas ─────────────────────────────────────────────────────────────────


class PaginaDatosGym(QWizardPage):
    """Paso 1: Nombre y tagline del gimnasio."""

    def __init__(self, datos: dict):
        super().__init__()
        self._datos = datos
        self.setTitle("1 · Datos del gimnasio")

        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        layout.addWidget(_lbl_seccion("Nombre del gimnasio *"))
        self.entry_nombre = _entry("Ej: Fitness Gym Real del Valle")
        self.entry_nombre.setText(datos.get("nombre_gym", ""))
        self.entry_nombre.textChanged.connect(self._validar)
        layout.addWidget(self.entry_nombre)
        self.lbl_nombre = _lbl_estado()
        layout.addWidget(self.lbl_nombre)

        layout.addSpacing(8)
        layout.addWidget(_lbl_seccion("Slogan / tagline (opcional)"))
        self.entry_tagline = _entry("Ej: Tu salud es nuestra motivación")
        self.entry_tagline.setText(datos.get("tagline", ""))
        layout.addWidget(self.entry_tagline)

        layout.addStretch()

        # Registrar campo requerido para que el botón Next se habilite
        self.registerField("nombre_gym*", self.entry_nombre)

    def _validar(self) -> None:
        ok, msg = _validar_nombre_gym(self.entry_nombre.text())
        if ok:
            self.lbl_nombre.setText("")
            self.entry_nombre.setStyleSheet("border: 1px solid #4CAF50; border-radius: 8px;")
        else:
            self.lbl_nombre.setText(f"Error: {msg}")
            self.lbl_nombre.setStyleSheet("color: #F44336; font-size: 10px;")
            self.entry_nombre.setStyleSheet("border: 1px solid #F44336; border-radius: 8px;")
        self.completeChanged.emit()

    def isComplete(self) -> bool:
        return _validar_nombre_gym(self.entry_nombre.text())[0]

    def validatePage(self) -> bool:
        ok, msg = _validar_nombre_gym(self.entry_nombre.text())
        if not ok:
            QMessageBox.warning(self, "Revisa los campos", f"Nombre del gym: {msg}")
        else:
            self._datos["nombre_gym"] = self.entry_nombre.text().strip()
            self._datos["tagline"] = self.entry_tagline.text().strip()
        return ok


class PaginaContacto(QWizardPage):
    """Paso 2: Información de contacto y redes sociales."""

    _CAMPOS = [
        ("Correo electrónico",       "contacto.email",           "Ej: info@tusgym.com",          False),
        ("Teléfono / WhatsApp",      "contacto.whatsapp",        "Ej: 5213312345678",           False),
        ("Dirección - Calle y Nro.", "contacto.direccion_linea1","Ej: C. Valle De San José 1329B",False),
        ("Dirección - Colonia",      "contacto.direccion_linea2","Ej: Fracc. Real del Valle",   False),
        ("Dirección - Ciudad y CP",  "contacto.direccion_linea3","Ej: 45654 Tlajomulco, Jal.",  False),
        ("Instagram",                "redes_sociales.instagram", "Ej: @fitnessgym_realdelvalle", False),
        ("Facebook",                 "redes_sociales.facebook",  "Ej: facebook.com/tusgym",     False),
        ("TikTok",                   "redes_sociales.tiktok",    "Ej: @tusgym",                 False),
    ]

    def __init__(self, datos: dict):
        super().__init__()
        self._datos = datos
        self.setTitle("2 · Información de contacto")
        self._entries: dict[str, QLineEdit] = {}

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("border: none;")

        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setSpacing(6)

        for label, key, placeholder, _ in self._CAMPOS:
            layout.addWidget(_lbl_seccion(label))
            entry = _entry(placeholder)
            entry.setText(datos.get(key, ""))
            layout.addWidget(entry)
            self._entries[key] = entry

        layout.addStretch()
        scroll_area.setWidget(inner)

        page_layout = QVBoxLayout(self)
        page_layout.addWidget(scroll_area)

    def validatePage(self) -> bool:
        for key, entry in self._entries.items():
            self._datos[key] = entry.text().strip()
        return True


class PaginaColores(QWizardPage):
    """Paso 3: Colores corporativos."""

    def __init__(self, datos: dict):
        super().__init__()
        self._datos = datos
        self.setTitle("3 · Colores del gimnasio")

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        lbl = QLabel("Selecciona los colores principales de tu marca")
        lbl.setStyleSheet("color: #B8B8B8; font-size: 12px;")
        layout.addWidget(lbl)

        # Color primario
        row1 = QWidget()
        h1 = QHBoxLayout(row1)
        h1.setContentsMargins(0, 0, 0, 0)
        h1.addWidget(QLabel("Primario:"))
        self.preview_primario = QLabel("   ")
        self.preview_primario.setFixedSize(40, 30)
        self._set_preview_color(self.preview_primario, datos["colores.primario"])
        h1.addWidget(self.preview_primario)
        btn1 = QPushButton("Elegir color")
        btn1.clicked.connect(lambda: self._elegir_color("primario", self.preview_primario))
        h1.addWidget(btn1)
        h1.addStretch()
        layout.addWidget(row1)

        # Color secundario
        row2 = QWidget()
        h2 = QHBoxLayout(row2)
        h2.setContentsMargins(0, 0, 0, 0)
        h2.addWidget(QLabel("Secundario:"))
        self.preview_secundario = QLabel("   ")
        self.preview_secundario.setFixedSize(40, 30)
        self._set_preview_color(self.preview_secundario, datos["colores.secundario"])
        h2.addWidget(self.preview_secundario)
        btn2 = QPushButton("Elegir color")
        btn2.clicked.connect(lambda: self._elegir_color("secundario", self.preview_secundario))
        h2.addWidget(btn2)
        h2.addStretch()
        layout.addWidget(row2)

        layout.addStretch()

    @staticmethod
    def _set_preview_color(lbl: QLabel, hex_color: str) -> None:
        lbl.setStyleSheet(
            f"background-color: {hex_color}; border-radius: 6px; border: 1px solid #444444;"
        )

    def _elegir_color(self, tipo: str, preview: QLabel) -> None:
        actual = QColor(self._datos[f"colores.{tipo}"])
        color = QColorDialog.getColor(actual, self, f"Color {tipo}")
        if color.isValid():
            hex_color = color.name().upper()
            self._datos[f"colores.{tipo}"] = hex_color
            self._set_preview_color(preview, hex_color)

    def validatePage(self) -> bool:
        return True


# ── Página Logo ─────────────────────────────────────────────────────────────


class PaginaLogo(QWizardPage):
    """Paso 4: Logo del gimnasio para el encabezado del PDF."""

    _LOGO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    ))), "assets")

    def __init__(self, datos: dict):
        super().__init__()
        self._datos = datos
        self.setTitle("4 · Logo del gimnasio")
        self._build()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setSpacing(12)

        lbl_desc = QLabel(
            "El logo aparecerá en el encabezado superior derecho de cada PDF.\n"
            "Formatos aceptados: PNG, JPG, JPEG, ICO. Tamaño recomendado: 300×100 px."
        )
        lbl_desc.setObjectName("subheadline")
        lbl_desc.setWordWrap(True)
        lay.addWidget(lbl_desc)

        # Preview
        self._preview = QLabel()
        self._preview.setFixedSize(260, 100)
        self._preview.setAlignment(Qt.AlignCenter)
        self._preview.setStyleSheet(
            "background-color: #1C1C1E; border: 1px solid #2C2C2C;"
            "border-radius: 10px; color: #48484A; font-size: 11px;"
        )
        self._preview.setText("Sin logo seleccionado")
        lay.addWidget(self._preview)

        # Ruta actual
        self._lbl_ruta = QLabel("")
        self._lbl_ruta.setStyleSheet(
            "color: #8E8E93; font-size: 10px; background: transparent;"
        )
        self._lbl_ruta.setWordWrap(True)
        lay.addWidget(self._lbl_ruta)

        # Botones
        fila = QHBoxLayout()
        btn_elegir = QPushButton("📂  Elegir logo...")
        btn_elegir.clicked.connect(self._elegir_logo)
        fila.addWidget(btn_elegir)

        btn_limpiar = QPushButton("Quitar logo")
        btn_limpiar.setObjectName("btn_secondary")
        btn_limpiar.clicked.connect(self._quitar_logo)
        fila.addWidget(btn_limpiar)
        fila.addStretch()
        lay.addLayout(fila)

        lay.addStretch()

        # Cargar logo existente si hay
        logo_actual = self._datos.get("pdf.logo_path", "") or self._datos.get("logo.path", "")
        if logo_actual and os.path.exists(logo_actual):
            self._actualizar_preview(logo_actual)

    def _elegir_logo(self) -> None:
        ruta, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar logo del gimnasio",
            os.path.expanduser("~"),
            "Imágenes (*.png *.jpg *.jpeg *.ico *.bmp);;Todos los archivos (*)",
        )
        if not ruta:
            return
        # Copiar al directorio assets para portabilidad
        try:
            os.makedirs(self._LOGO_DIR, exist_ok=True)
            ext = os.path.splitext(ruta)[1].lower()
            destino = os.path.join(self._LOGO_DIR, f"logo_gym{ext}")
            if os.path.abspath(ruta) != os.path.abspath(destino):
                shutil.copy2(ruta, destino)
            ruta = destino
        except OSError:
            pass  # usar ruta original si no se puede copiar
        self._datos["logo.path"] = ruta
        self._datos["pdf.logo_path"] = ruta
        self._actualizar_preview(ruta)

    def _quitar_logo(self) -> None:
        self._datos["logo.path"] = "assets/logo.png"
        self._datos["pdf.logo_path"] = "assets/logo.png"
        self._preview.setText("Sin logo seleccionado")
        self._preview.setPixmap(QPixmap())
        self._lbl_ruta.setText("")

    def _actualizar_preview(self, ruta: str) -> None:
        pix = QPixmap(ruta)
        if pix.isNull():
            self._preview.setText("No se pudo cargar la imagen")
            return
        scaled = pix.scaled(
            self._preview.width() - 10, self._preview.height() - 10,
            Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        self._preview.setPixmap(scaled)
        self._lbl_ruta.setText(f"✓  {os.path.basename(ruta)}")

    def validatePage(self) -> bool:
        # Logo es opcional, siempre válido
        return True


# ── Wizard principal ─────────────────────────────────────────────────────────


class WizardOnboarding(QWizard):
    """
    Wizard de 3 pasos para configurar el gym en primera instalación.
    Persiste los datos en branding cuando el usuario hace Finalizar.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Configuración inicial — Método Base")
        self.setFixedSize(560, 520)
        self.setModal(True)
        self.setWizardStyle(QWizard.ModernStyle)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        self._datos: dict = {
            "nombre_gym":              branding.get("nombre_gym", ""),
            "tagline":                 branding.get("tagline", ""),
            "contacto.telefono":       branding.get("contacto.telefono", ""),
            "contacto.whatsapp":       branding.get("contacto.whatsapp", ""),
            "contacto.email":          branding.get("contacto.email", ""),
            "colores.primario":        branding.get("colores.primario", "#FF6F0F"),
            "colores.secundario":      branding.get("colores.secundario", "#1C1C1E"),
            "contacto.direccion_linea1": branding.get("contacto.direccion_linea1", ""),
            "contacto.direccion_linea2": branding.get("contacto.direccion_linea2", ""),
            "contacto.direccion_linea3": branding.get("contacto.direccion_linea3", ""),
            "redes_sociales.instagram": branding.get("redes_sociales.instagram", ""),
            "redes_sociales.facebook":  branding.get("redes_sociales.facebook", ""),
            "redes_sociales.tiktok":    branding.get("redes_sociales.tiktok", ""),
            "logo.path":               branding.get("logo.path", "assets/logo.png"),
            "pdf.logo_path":           branding.get("pdf.logo_path", "assets/logo.png"),
        }

        self.addPage(PaginaDatosGym(self._datos))
        self.addPage(PaginaContacto(self._datos))
        self.addPage(PaginaColores(self._datos))
        self.addPage(PaginaLogo(self._datos))

        self.button(QWizard.FinishButton).setText("Finalizar ✓")
        self.button(QWizard.NextButton).setText("Siguiente →")
        self.button(QWizard.BackButton).setText("← Anterior")
        self.button(QWizard.CancelButton).setText("Omitir")

        self.finished.connect(self._on_finished)

    # ------------------------------------------------------------------

    def _on_finished(self, result: int) -> None:
        if result == QWizard.Accepted:
            for key, valor in self._datos.items():
                if valor:
                    branding.set(key, valor)
            branding.guardar()
            logger.info(
                "[WIZARD] Configuración inicial completada: %s",
                self._datos.get("nombre_gym"),
            )

    def reject(self) -> None:
        """El usuario pulsó Omitir/X."""
        resp = QMessageBox.question(
            self,
            "Sin configurar",
            "Si no configuras el gym, los PDFs saldrán sin nombre. ¿Continuar sin configurar?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if resp == QMessageBox.Yes:
            super().reject()

# -*- coding: utf-8 -*-
"""
PanelPerfilDetalle — Formulario de perfil personal del usuario regular.

Captura:
  · Nombre para mostrar (auto-completado desde la sesión)
  · Género (Masculino / Femenino / Prefiero no decir)
  · Edad  (13 – 100)
  · Estatura cm (100 – 250)
  · Peso kg (30 – 300)
  · Nivel de actividad física (5 opciones ACSM)
  · Objetivo (Perder peso / Mantener / Ganar masa)

Los datos se guardan en GestorPreferencias  y la señal
`perfil_guardado(dict)` se emite para que el FlowController continúe.
"""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.services.auth_service import SesionActiva
from utils.logger import logger


# ── Constantes de actividad ────────────────────────────────────────────────────
_NIVELES_ACTIVIDAD: list[tuple[str, str]] = [
    ("sedentario",       "Sedentario — sin ejercicio formal"),
    ("ligero",           "Ligero — 1-2 días/semana"),
    ("moderado",         "Moderado — 3-4 días/semana"),
    ("activo",           "Activo — 5-6 días/semana"),
    ("muy_activo",       "Muy activo — doble sesión o trabajo físico"),
]

_OBJETIVOS: list[tuple[str, str]] = [
    ("perder_peso",     "Perder peso (déficit calórico)"),
    ("mantener",        "Mantener peso actual"),
    ("ganar_masa",      "Ganar masa muscular (superávit)"),
]

_GENEROS: list[tuple[str, str]] = [
    ("masculino",  "Masculino"),
    ("femenino",   "Femenino"),
    ("otro",       "Prefiero no decir"),
]


class PanelPerfilDetalle(QDialog):
    """Diálogo de perfil personal del usuario regular."""

    perfil_guardado = Signal(dict)

    def __init__(
        self,
        sesion: SesionActiva,
        prefs_actuales: dict[str, Any] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._sesion = sesion
        self._prefs = prefs_actuales or {}
        self.setWindowTitle("Tu perfil")
        self.setFixedWidth(480)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self._build_ui()
        self._cargar_valores()

    # ── Construcción de UI ────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(36, 36, 36, 36)
        root.setSpacing(0)

        # Encabezado
        greeting = QLabel(f"Hola, {self._sesion.nombre_display} 👋")
        greeting.setObjectName("title")
        root.addWidget(greeting)

        sub = QLabel("Cuéntanos un poco sobre ti para personalizar tu plan nutricional.")
        sub.setObjectName("subheadline")
        sub.setWordWrap(True)
        root.addWidget(sub)

        root.addSpacerItem(QSpacerItem(0, 24, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # ── Separador de sección ─────────────────────────────────────────
        sec_datos = QLabel("DATOS PERSONALES")
        sec_datos.setObjectName("section_title")
        root.addWidget(sec_datos)
        root.addSpacerItem(QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # ── Formulario ───────────────────────────────────────────────────
        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)

        # Género
        self._cmb_genero = QComboBox()
        for _val, _lbl in _GENEROS:
            self._cmb_genero.addItem(_lbl, _val)
        form.addRow(_lbl_form("Género"), self._cmb_genero)

        # Edad
        self._spin_edad = QSpinBox()
        self._spin_edad.setRange(13, 100)
        self._spin_edad.setValue(25)
        self._spin_edad.setSuffix(" años")
        form.addRow(_lbl_form("Edad"), self._spin_edad)

        # Estatura
        self._spin_estatura = QDoubleSpinBox()
        self._spin_estatura.setRange(100.0, 250.0)
        self._spin_estatura.setValue(170.0)
        self._spin_estatura.setSingleStep(0.5)
        self._spin_estatura.setSuffix(" cm")
        form.addRow(_lbl_form("Estatura"), self._spin_estatura)

        # Peso
        self._spin_peso = QDoubleSpinBox()
        self._spin_peso.setRange(30.0, 300.0)
        self._spin_peso.setValue(70.0)
        self._spin_peso.setSingleStep(0.5)
        self._spin_peso.setSuffix(" kg")
        form.addRow(_lbl_form("Peso"), self._spin_peso)

        # Grasa corporal
        self._spin_grasa = QDoubleSpinBox()
        self._spin_grasa.setRange(5.0, 60.0)
        self._spin_grasa.setValue(20.0)
        self._spin_grasa.setSingleStep(0.5)
        self._spin_grasa.setSuffix(" %")
        self._spin_grasa.setToolTip(
            "Porcentaje estimado de grasa corporal.\n"
            "Promedio referencial: hombres 15-25 %, mujeres 20-35 %."
        )
        form.addRow(_lbl_form("% Grasa corporal"), self._spin_grasa)

        root.addLayout(form)
        root.addSpacerItem(QSpacerItem(0, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # ── Sección actividad ────────────────────────────────────────────
        sec_act = QLabel("NIVEL DE ACTIVIDAD")
        sec_act.setObjectName("section_title")
        root.addWidget(sec_act)
        root.addSpacerItem(QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))

        self._cmb_actividad = QComboBox()
        for _val, _lbl2 in _NIVELES_ACTIVIDAD:
            self._cmb_actividad.addItem(_lbl2, _val)
        root.addWidget(self._cmb_actividad)

        root.addSpacerItem(QSpacerItem(0, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # ── Sección objetivo ─────────────────────────────────────────────
        sec_obj = QLabel("OBJETIVO")
        sec_obj.setObjectName("section_title")
        root.addWidget(sec_obj)
        root.addSpacerItem(QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))

        self._cmb_objetivo = QComboBox()
        for _val, _lbl3 in _OBJETIVOS:
            self._cmb_objetivo.addItem(_lbl3, _val)
        root.addWidget(self._cmb_objetivo)

        root.addSpacerItem(QSpacerItem(0, 28, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # ── Botones ──────────────────────────────────────────────────────
        btns = QHBoxLayout()
        btn_omitir = QPushButton("Omitir por ahora")
        btn_omitir.setObjectName("btn_secondary")
        btn_omitir.clicked.connect(self._omitir)

        btn_guardar = QPushButton("Guardar y continuar →")
        btn_guardar.clicked.connect(self._guardar)

        btns.addWidget(btn_omitir)
        btns.addStretch()
        btns.addWidget(btn_guardar)
        root.addLayout(btns)

    # ── Carga de valores previos ───────────────────────────────────────────

    def _cargar_valores(self) -> None:
        p = self._prefs
        # Género
        genero = p.get("genero", "")
        for i, (_v, _) in enumerate(_GENEROS):
            if _v == genero:
                self._cmb_genero.setCurrentIndex(i)
                break
        # Edad
        if "edad" in p:
            self._spin_edad.setValue(int(p["edad"]))
        # Estatura
        if "estatura_cm" in p:
            self._spin_estatura.setValue(float(p["estatura_cm"]))
        # Peso
        if "peso_kg" in p:
            self._spin_peso.setValue(float(p["peso_kg"]))
        # Grasa corporal
        if "grasa_corporal_pct" in p:
            self._spin_grasa.setValue(float(p["grasa_corporal_pct"]))
        # Actividad
        actividad = p.get("nivel_actividad", "")
        for i, (_v, _) in enumerate(_NIVELES_ACTIVIDAD):
            if _v == actividad:
                self._cmb_actividad.setCurrentIndex(i)
                break
        # Objetivo
        objetivo = p.get("objetivo", "")
        for i, (_v, _) in enumerate(_OBJETIVOS):
            if _v == objetivo:
                self._cmb_objetivo.setCurrentIndex(i)
                break

    # ── Slots ─────────────────────────────────────────────────────────────

    def _guardar(self) -> None:
        datos = {
            "genero":              self._cmb_genero.currentData(),
            "edad":                self._spin_edad.value(),
            "estatura_cm":         round(self._spin_estatura.value(), 1),
            "peso_kg":             round(self._spin_peso.value(), 1),
            "grasa_corporal_pct":  round(self._spin_grasa.value(), 1),
            "nivel_actividad":     self._cmb_actividad.currentData(),
            "objetivo":            self._cmb_objetivo.currentData(),
        }
        logger.info("[PERFIL] Usuario %s guardó perfil.", self._sesion.id_usuario)
        self.perfil_guardado.emit(datos)
        self.accept()

    def _omitir(self) -> None:
        self.perfil_guardado.emit(self._prefs)
        self.accept()


# ── Helpers privados ──────────────────────────────────────────────────────────

def _lbl_form(texto: str) -> QLabel:
    lbl = QLabel(texto)
    lbl.setObjectName("subheadline")
    lbl.setStyleSheet("color: #8E8E93; font-size: 12px; background: transparent;")
    return lbl

# -*- coding: utf-8 -*-
"""
DialogoGenerarPlan — Generación de plan nutricional personal.

Flujo:
  1. Muestra resumen del perfil del usuario (peso, IMC, objetivo, etc.).
  2. Permite elegir tipo de plan: Menú Fijo o Con Opciones.
  3. Ajustar % grasa corporal si no está registrado.
  4. Al pulsar "Generar", construye el plan en hilo separado y exporta PDF.
  5. Aplica las exclusiones de alimentos del usuario.
  6. Muestra el progreso en tiempo real y habilita "Abrir PDF" al terminar.
"""
from __future__ import annotations

import os
import re
import threading
from datetime import datetime
from typing import Any

from PySide6.QtCore import Qt, QObject, Signal, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from core.services.auth_service import SesionActiva
from utils.logger import logger


# ── Mapas sesión perfil → motor ────────────────────────────────────────────────

_MAP_ACTIVIDAD: dict[str, str] = {
    "sedentario": "nula",
    "ligero":     "leve",
    "moderado":   "moderada",
    "activo":     "intensa",
    "muy_activo": "intensa",
}
_MAP_OBJETIVO: dict[str, str] = {
    "perder_peso": "deficit",
    "mantener":    "mantenimiento",
    "ganar_masa":  "superavit",
}
_LABEL_OBJETIVO: dict[str, str] = {
    "perder_peso": "Pérdida de grasa",
    "mantener":    "Mantenimiento",
    "ganar_masa":  "Ganancia muscular",
}
_LABEL_ACTIVIDAD: dict[str, str] = {
    "sedentario": "Sedentario",
    "ligero":     "Ligero",
    "moderado":   "Moderado",
    "activo":     "Activo",
    "muy_activo": "Muy activo",
}


# ── Puente de señales para thread-safe ─────────────────────────────────────────

class _Signals(QObject):
    progress  = Signal(int, str)   # pct, mensaje
    done      = Signal(str)        # ruta_pdf
    error     = Signal(str)        # mensaje de error


# ── Diálogo principal ──────────────────────────────────────────────────────────

class DialogoGenerarPlan(QDialog):
    """Modal de generación de plan nutricional para usuario regular."""

    def __init__(
        self,
        sesion: SesionActiva,
        perfil: dict[str, Any],
        excluidos: list[str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._sesion   = sesion
        self._perfil   = perfil
        self._excluidos = excluidos
        self._ruta_pdf: str | None = None
        self._sig = _Signals()
        self._sig.progress.connect(self._on_progress)
        self._sig.done.connect(self._on_done)
        self._sig.error.connect(self._on_error)

        self.setWindowTitle("Generar mi plan nutricional")
        self.setFixedWidth(520)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self._build_ui()

    # ── Construcción de UI ──────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 32, 32, 32)
        root.setSpacing(0)

        # Title
        title = QLabel("⚡  Generar plan nutricional")
        title.setObjectName("title")
        root.addWidget(title)

        subtitle = QLabel(
            "Revisá tus datos antes de generar. El plan se adaptará a tus preferencias alimentarias."
        )
        subtitle.setObjectName("subheadline")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)
        root.addSpacerItem(QSpacerItem(0, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # ── Tarjeta resumen de perfil ────────────────────────────────────
        sec_perfil = QLabel("TU PERFIL")
        sec_perfil.setObjectName("section_title")
        root.addWidget(sec_perfil)
        root.addSpacerItem(QSpacerItem(0, 8, QSizePolicy.Minimum, QSizePolicy.Fixed))

        root.addWidget(self._build_perfil_card())
        root.addSpacerItem(QSpacerItem(0, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # ── Grasa corporal (si no está en perfil) ────────────────────────
        grasa_actual = float(self._perfil.get("grasa_corporal_pct", 0) or 0)
        self._tiene_grasa = grasa_actual >= 5.0
        if not self._tiene_grasa:
            sec_g = QLabel("% GRASA CORPORAL")
            sec_g.setObjectName("section_title")
            root.addWidget(sec_g)
            root.addSpacerItem(QSpacerItem(0, 8, QSizePolicy.Minimum, QSizePolicy.Fixed))
            grasa_row = QHBoxLayout()
            lbl_g = QLabel(
                "No registramos tu % de grasa. Ingresá un valor estimado para un plan más preciso:"
            )
            lbl_g.setObjectName("subheadline")
            lbl_g.setWordWrap(True)
            root.addWidget(lbl_g)
            self._spin_grasa = QDoubleSpinBox()
            self._spin_grasa.setRange(5.0, 60.0)
            self._spin_grasa.setValue(20.0)
            self._spin_grasa.setSuffix(" %")
            self._spin_grasa.setFixedWidth(110)
            grasa_row.addWidget(self._spin_grasa)
            grasa_row.addStretch()
            root.addLayout(grasa_row)
            root.addSpacerItem(QSpacerItem(0, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))
        else:
            self._spin_grasa = None

        # ── Tipo de plan ──────────────────────────────────────────────────
        sec_tipo = QLabel("TIPO DE PLAN")
        sec_tipo.setObjectName("section_title")
        root.addWidget(sec_tipo)
        root.addSpacerItem(QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))

        tipo_card = QFrame()
        tipo_card.setObjectName("card")
        tipo_lay = QVBoxLayout(tipo_card)
        tipo_lay.setContentsMargins(16, 14, 16, 14)
        tipo_lay.setSpacing(10)

        self._radio_fijo = QRadioButton("📋  Menú fijo  —  un menú detallado por día")
        self._radio_fijo.setChecked(True)
        self._radio_fijo.setStyleSheet("font-size: 13px; font-weight: 600;")
        tipo_lay.addWidget(self._radio_fijo)

        desc_fijo = QLabel("Recibís las cantidades exactas en gramos de cada alimento para cada comida.")
        desc_fijo.setObjectName("caption")
        desc_fijo.setContentsMargins(26, 0, 0, 0)
        tipo_lay.addWidget(desc_fijo)

        self._radio_opciones = QRadioButton("🔀  Con opciones  —  3 alternativas por macronutriente")
        self._radio_opciones.setStyleSheet("font-size: 13px; font-weight: 600;")
        tipo_lay.addWidget(self._radio_opciones)

        desc_opc = QLabel("Elegís entre 3 opciones de proteína, carbohidrato y grasa en cada comida.")
        desc_opc.setObjectName("caption")
        desc_opc.setContentsMargins(26, 0, 0, 0)
        tipo_lay.addWidget(desc_opc)

        root.addWidget(tipo_card)
        root.addSpacerItem(QSpacerItem(0, 8, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Info exclusiones
        n_excl = len(self._excluidos)
        if n_excl:
            lbl_excl = QLabel(f"🚫  {n_excl} alimentos excluidos serán ignorados en el plan.")
            lbl_excl.setObjectName("warning_label")
        else:
            lbl_excl = QLabel("✅  Todos los alimentos habilitados.")
            lbl_excl.setObjectName("success_label")
        root.addWidget(lbl_excl)
        root.addSpacerItem(QSpacerItem(0, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # ── Barra de progreso ─────────────────────────────────────────────
        self._barra = QProgressBar()
        self._barra.setRange(0, 100)
        self._barra.setValue(0)
        self._barra.setFixedHeight(6)
        self._barra.setVisible(False)
        root.addWidget(self._barra)

        self._lbl_progreso = QLabel("")
        self._lbl_progreso.setObjectName("caption")
        self._lbl_progreso.setVisible(False)
        root.addWidget(self._lbl_progreso)
        root.addSpacerItem(QSpacerItem(0, 12, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # ── Botones ───────────────────────────────────────────────────────
        btns = QHBoxLayout()

        self._btn_cancelar = QPushButton("Cancelar")
        self._btn_cancelar.setObjectName("btn_secondary")
        self._btn_cancelar.clicked.connect(self.reject)
        btns.addWidget(self._btn_cancelar)
        btns.addStretch()

        self._btn_abrir = QPushButton("📂  Abrir PDF")
        self._btn_abrir.setObjectName("btn_success")
        self._btn_abrir.setVisible(False)
        self._btn_abrir.clicked.connect(self._abrir_pdf)
        btns.addWidget(self._btn_abrir)

        self._btn_generar = QPushButton("⚡  Generar plan")
        self._btn_generar.setFixedWidth(160)
        self._btn_generar.clicked.connect(self._iniciar_generacion)
        btns.addWidget(self._btn_generar)

        root.addLayout(btns)

    def _build_perfil_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(0)

        p = self._perfil
        items = [
            ("Peso",       f"{p.get('peso_kg', '—')} kg"),
            ("Estatura",   f"{p.get('estatura_cm', '—')} cm"),
            ("Edad",       f"{p.get('edad', '—')} años"),
            ("Actividad",  _LABEL_ACTIVIDAD.get(p.get("nivel_actividad", ""), "—")),
            ("Objetivo",   _LABEL_OBJETIVO.get(p.get("objetivo", ""), "—")),
        ]
        for label, valor in items:
            col = QVBoxLayout()
            val_lbl = QLabel(str(valor))
            val_lbl.setStyleSheet(
                "font-size: 15px; font-weight: 700; color: #F2F2F7; background: transparent;"
            )
            et_lbl = QLabel(label)
            et_lbl.setObjectName("stat_label")
            col.addWidget(val_lbl)
            col.addWidget(et_lbl)
            lay.addLayout(col)
            lay.addStretch()

        return card

    # ── Generación ──────────────────────────────────────────────────────────

    def _iniciar_generacion(self) -> None:
        self._btn_generar.setEnabled(False)
        self._btn_cancelar.setEnabled(False)
        self._barra.setVisible(True)
        self._lbl_progreso.setVisible(True)
        self._btn_abrir.setVisible(False)

        tipo = "con_opciones" if self._radio_opciones.isChecked() else "fijo"
        t = threading.Thread(target=self._worker, args=(tipo,), daemon=True)
        t.start()

    def _worker(self, tipo: str) -> None:
        try:
            self._sig.progress.emit(5, "Preparando datos del plan...")
            from config.constantes import FACTORES_ACTIVIDAD, CARPETA_PLANES
            from core.modelos import ClienteEvaluacion
            from core.motor_nutricional import MotorNutricional

            p = self._perfil
            grasa = (
                float(p.get("grasa_corporal_pct") or 0)
                if self._tiene_grasa
                else self._spin_grasa.value()
            )
            if grasa < 5:
                grasa = 20.0

            actividad_motor = _MAP_ACTIVIDAD.get(p.get("nivel_actividad", "sedentario"), "nula")
            objetivo_motor  = _MAP_OBJETIVO.get(p.get("objetivo", "mantener"), "mantenimiento")
            factor          = FACTORES_ACTIVIDAD.get(actividad_motor, 1.2)

            cliente = ClienteEvaluacion(
                nombre          = self._sesion.nombre_display,
                telefono        = None,
                edad            = int(p.get("edad") or 25),
                peso_kg         = float(p.get("peso_kg") or 70),
                estatura_cm     = float(p.get("estatura_cm") or 170),
                grasa_corporal_pct = grasa,
                nivel_actividad = actividad_motor,
                objetivo        = objetivo_motor,
                plantilla_tipo  = "perdida_grasa" if objetivo_motor == "deficit" else "mantenimiento",
                factor_actividad= factor,
            )
            cliente = MotorNutricional.calcular_motor(cliente)

            self._sig.progress.emit(25, "Aplicando preferencias alimentarias...")

            # Aplicar exclusiones del usuario temporalmente
            backup = self._backup_categorias()
            self._aplicar_exclusiones(self._excluidos)

            self._sig.progress.emit(40, "Construyendo el plan...")
            os.makedirs(CARPETA_PLANES, exist_ok=True)

            try:
                if tipo == "con_opciones":
                    from core.generador_opciones import ConstructorPlanConOpciones
                    from core.exportador_opciones import GeneradorPDFConOpciones
                    plan = ConstructorPlanConOpciones.construir(
                        cliente, plan_numero=1,
                        directorio_planes=CARPETA_PLANES,
                        num_opciones_por_macro=3,
                    )
                    self._sig.progress.emit(70, "Exportando PDF...")
                    ruta_pdf = self._generar_ruta_pdf(cliente, "OPCIONES", CARPETA_PLANES)
                    gen = GeneradorPDFConOpciones(ruta_pdf)
                    ruta_pdf = gen.generar(cliente, plan)
                else:
                    from core.generador_planes import ConstructorPlanNuevo
                    from core.exportador_salida import GeneradorPDFProfesional
                    plan = ConstructorPlanNuevo.construir(
                        cliente, plan_numero=1, directorio_planes=CARPETA_PLANES
                    )
                    self._sig.progress.emit(70, "Exportando PDF...")
                    ruta_pdf = self._generar_ruta_pdf(cliente, "PLAN", CARPETA_PLANES)
                    gen = GeneradorPDFProfesional(ruta_pdf)
                    ruta_pdf = gen.generar(cliente, plan)
            finally:
                # Restaurar siempre aunque falle
                self._restaurar_categorias(backup)

            self._sig.progress.emit(95, "Finalizando...")
            if ruta_pdf and os.path.exists(ruta_pdf):
                self._sig.done.emit(ruta_pdf)
            else:
                self._sig.error.emit("El PDF se generó pero no se encontró en disco.")
        except Exception as exc:
            logger.error("[PLAN_USUARIO] Error al generar plan: %s", exc, exc_info=True)
            self._sig.error.emit(f"Error al generar el plan: {exc}")

    # ── Helpers de categorías ───────────────────────────────────────────────

    @staticmethod
    def _backup_categorias() -> dict[str, list[str]]:
        from src.alimentos_base import CATEGORIAS
        return {k: list(v) for k, v in CATEGORIAS.items() if isinstance(v, list)}

    @staticmethod
    def _aplicar_exclusiones(excluidos: list[str]) -> None:
        if not excluidos:
            return
        exc_set = set(excluidos)
        from src.alimentos_base import CATEGORIAS
        for items in CATEGORIAS.values():
            if isinstance(items, list):
                filtrados = [a for a in items if a not in exc_set]
                items.clear()
                items.extend(filtrados)

    @staticmethod
    def _restaurar_categorias(backup: dict[str, list[str]]) -> None:
        from src.alimentos_base import CATEGORIAS
        for cat, items_bak in backup.items():
            if cat in CATEGORIAS and isinstance(CATEGORIAS[cat], list):
                CATEGORIAS[cat].clear()
                CATEGORIAS[cat].extend(items_bak)

    @staticmethod
    def _generar_ruta_pdf(cliente: Any, sufijo: str, carpeta_base: str) -> str:
        fecha   = datetime.now().strftime("%Y-%m-%d")
        hora    = datetime.now().strftime("%H-%M-%S")
        nombre_san = re.sub(r"[^a-zA-Z0-9_]", "", cliente.nombre.replace(" ", "_"))
        carpeta = os.path.join(carpeta_base, nombre_san)
        os.makedirs(carpeta, exist_ok=True)
        return os.path.join(carpeta, f"{nombre_san}_{sufijo}_{fecha}_{hora}.pdf")

    # ── Slots ───────────────────────────────────────────────────────────────

    def _on_progress(self, pct: int, msg: str) -> None:
        self._barra.setValue(pct)
        self._lbl_progreso.setText(msg)

    def _on_done(self, ruta_pdf: str) -> None:
        self._ruta_pdf = ruta_pdf
        self._barra.setValue(100)
        self._lbl_progreso.setStyleSheet("color: #30D158; font-size: 12px;")
        self._lbl_progreso.setText(f"✓  Plan generado: {os.path.basename(ruta_pdf)}")
        self._btn_generar.setVisible(False)
        self._btn_abrir.setVisible(True)
        self._btn_cancelar.setText("Cerrar")
        self._btn_cancelar.setEnabled(True)

    def _on_error(self, msg: str) -> None:
        self._barra.setValue(0)
        self._barra.setVisible(False)
        self._lbl_progreso.setStyleSheet("color: #FF453A; font-size: 12px;")
        self._lbl_progreso.setText(f"✗  {msg}")
        self._btn_generar.setEnabled(True)
        self._btn_cancelar.setEnabled(True)

    def _abrir_pdf(self) -> None:
        if self._ruta_pdf and os.path.exists(self._ruta_pdf):
            import subprocess, sys
            if sys.platform.startswith("linux"):
                subprocess.Popen(["xdg-open", self._ruta_pdf])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", self._ruta_pdf])
            else:
                os.startfile(self._ruta_pdf)  # type: ignore[attr-defined]

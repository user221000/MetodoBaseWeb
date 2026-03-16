# -*- coding: utf-8 -*-
"""
Ventana de activación de licencia — PySide6.
Reemplaza gui/ventana_licencia.py.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QFrame, QMessageBox, QApplication, QWidget,
)
from PySide6.QtCore import Qt

from core.licencia import GestorLicencias
from utils.telemetria import registrar_evento
from utils.logger import logger


PLANES_COMERCIALES = {
    "semestral": {"label": "Plan Semestral (180 días)", "periodo_meses": 6},
    "anual":     {"label": "Plan Anual (365 días)",     "periodo_meses": 12},
}


class VentanaActivacionLicencia(QDialog):
    """Modal que bloquea el acceso hasta activar una licencia válida."""

    def __init__(self, parent=None, gestor: GestorLicencias | None = None, nombre_gym: str = "MetodoBase"):
        super().__init__(parent)
        self.gestor = gestor or GestorLicencias()
        self.nombre_gym = nombre_gym.strip() or "MetodoBase"
        self.activada = False

        self.setWindowTitle("Activación de licencia")
        self.setFixedSize(620, 530)
        self.setModal(True)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        self._id_instalacion = self.gestor.obtener_id_instalacion()
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 22, 22, 22)
        root.setSpacing(0)

        # Card
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 20)
        card_layout.setSpacing(12)
        root.addWidget(card)

        # Título
        lbl_titulo = QLabel("Activación de licencia")
        lbl_titulo.setAlignment(Qt.AlignCenter)
        lbl_titulo.setStyleSheet("color: #9B4FB0; font-size: 22px; font-weight: bold;")
        card_layout.addWidget(lbl_titulo)

        # Subtítulo
        lbl_sub = QLabel(
            "Ingresa la key generada por proveedor y selecciona el periodo.\n"
            "Sin licencia válida no se puede abrir el sistema."
        )
        lbl_sub.setAlignment(Qt.AlignCenter)
        lbl_sub.setWordWrap(True)
        lbl_sub.setStyleSheet("color: #B8B8B8; font-size: 12px;")
        card_layout.addWidget(lbl_sub)

        # ID de instalación
        card_layout.addWidget(self._lbl_campo("ID instalación"))
        self.entry_id = QLineEdit(self._id_instalacion)
        self.entry_id.setReadOnly(True)
        card_layout.addWidget(self.entry_id)

        # Plan comercial
        card_layout.addWidget(self._lbl_campo("Plan comercial"))
        self.combo_periodo = QComboBox()
        for v in PLANES_COMERCIALES.values():
            self.combo_periodo.addItem(v["label"])
        self.combo_periodo.currentIndexChanged.connect(self._actualizar_ayuda)
        card_layout.addWidget(self.combo_periodo)

        # Canal de venta
        card_layout.addWidget(self._lbl_campo("Canal de venta (opcional)"))
        self.entry_canal = QLineEdit()
        self.entry_canal.setPlaceholderText("Ej: WhatsApp, Distribuidor, Web")
        card_layout.addWidget(self.entry_canal)

        # Key de activación
        card_layout.addWidget(self._lbl_campo("Key de activación"))
        self.entry_key = QLineEdit()
        self.entry_key.setPlaceholderText("Ej: MB06-XXXX-XXXX-XXXX-XXXX")
        self.entry_key.textChanged.connect(self._actualizar_ayuda)
        card_layout.addWidget(self.entry_key)

        # Etiqueta de estado
        self.lbl_estado = QLabel("Ayuda: selecciona periodo y escribe la key completa.")
        self.lbl_estado.setWordWrap(True)
        self.lbl_estado.setStyleSheet("color: #B8B8B8; font-size: 10px;")
        card_layout.addWidget(self.lbl_estado)

        # Botones
        btns_widget = QWidget()
        btns = QHBoxLayout(btns_widget)
        btns.setSpacing(10)
        btns.setContentsMargins(0, 8, 0, 0)

        btn_copiar = QPushButton("Copiar ID")
        btn_copiar.setObjectName("btn_secondary")
        btn_copiar.clicked.connect(self._copiar_id)
        btns.addWidget(btn_copiar)

        btn_activar = QPushButton("Activar")
        btn_activar.clicked.connect(self._activar)
        btns.addWidget(btn_activar)

        btn_salir = QPushButton("Salir")
        btn_salir.setObjectName("btn_secondary")
        btn_salir.clicked.connect(self._cerrar_sin_activar)
        btns.addWidget(btn_salir)

        card_layout.addWidget(btns_widget)

    @staticmethod
    def _lbl_campo(texto: str) -> QLabel:
        lbl = QLabel(texto)
        lbl.setStyleSheet("color: #F5F5F5; font-size: 12px; font-weight: bold;")
        return lbl

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _obtener_plan_seleccionado(self) -> str:
        label_actual = self.combo_periodo.currentText()
        for key, meta in PLANES_COMERCIALES.items():
            if label_actual == meta["label"]:
                return key
        return "semestral"

    def _actualizar_ayuda(self) -> None:
        key = self.entry_key.text().strip()
        plan = self._obtener_plan_seleccionado()
        meses = PLANES_COMERCIALES[plan]["periodo_meses"]
        dias = 180 if plan == "semestral" else 365
        prefijo = f"MB{meses:02d}"
        if not key:
            self.lbl_estado.setText(
                f"Ayuda: activación para {dias} días ({meses} meses). "
                f"La key debe corresponder al plan seleccionado ({prefijo}...)."
            )
            self.lbl_estado.setStyleSheet("color: #B8B8B8; font-size: 10px;")
            return
        if len(key) < 10:
            self.lbl_estado.setText("Error: key incompleta. Revisa bloques y guiones.")
            self.lbl_estado.setStyleSheet("color: #F44336; font-size: 10px;")
            return
        self.lbl_estado.setText("OK: formato capturado. Puedes activar.")
        self.lbl_estado.setStyleSheet("color: #4CAF50; font-size: 10px;")

    def _copiar_id(self) -> None:
        QApplication.clipboard().setText(self._id_instalacion)
        QMessageBox.information(self, "ID copiado", "ID de instalación copiado al portapapeles.")

    def _activar(self) -> None:
        key = self.entry_key.text().strip()
        plan = self._obtener_plan_seleccionado()
        periodo = PLANES_COMERCIALES[plan]["periodo_meses"]
        canal = self.entry_canal.text().strip()

        ok, msg = self.gestor.activar_licencia_con_key(
            nombre_gym=self.nombre_gym,
            key_activacion=key,
            periodo_meses=periodo,
            plan_comercial=plan,
            canal_venta=canal,
        )
        if not ok:
            self.lbl_estado.setText(f"Error: {msg}")
            self.lbl_estado.setStyleSheet("color: #F44336; font-size: 10px;")
            QMessageBox.critical(self, "Activación fallida", msg)
            registrar_evento("licencia", "activacion_fallida", {"plan": plan})
            return

        self.activada = True
        self.lbl_estado.setText(f"OK: {msg}")
        self.lbl_estado.setStyleSheet("color: #4CAF50; font-size: 10px;")
        registrar_evento("licencia", "activacion_exitosa", {"plan": plan, "periodo": periodo})
        QMessageBox.information(self, "Activación correcta", msg)
        self.accept()

    def _cerrar_sin_activar(self) -> None:
        self.activada = False
        self.reject()

    def closeEvent(self, event):
        self.activada = False
        super().closeEvent(event)

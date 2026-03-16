# -*- coding: utf-8 -*-
"""
Vista previa del plan nutricional — PySide6.
Reemplaza gui/ventana_preview.py.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QWidget, QPushButton, QGridLayout,
)
from PySide6.QtCore import Qt


_EQUIV_CASERAS: dict[str, tuple[float, str]] = {
    "arroz":              (185, "taza cocida"),
    "avena":              (85,  "taza cruda"),
    "papa":               (150, "papa med"),
    "leche":              (240, "1 vaso"),
    "aceite_oliva":       (14,  "1 cda"),
    "aceite_coco":        (14,  "1 cda"),
    "mantequilla":        (14,  "1 cda"),
    "nueces":             (28,  "pequeño puño"),
    "almendras":          (28,  "pequeño puño"),
    "huevo":              (55,  "1 huevo gr"),
    "pan_integral":       (30,  "1 rebanada"),
    "tortilla_maiz":      (30,  "1 tortilla"),
    "tortilla_trigo":     (45,  "1 tortilla gr"),
    "platano_macho":      (150, "½ plátano gr"),
    "manzana":            (140, "manzana med"),
    "pechuga_pollo":      (100, "fillete med"),
}


def _equiv_txt(nombre: str, gramos: float) -> str:
    info = _EQUIV_CASERAS.get(nombre)
    if not info:
        return ""
    porcion_g, desc = info
    n = gramos / porcion_g
    if abs(n - round(n)) < 0.15 and n <= 5:
        n_fmt = str(int(round(n))) if abs(n - round(n)) < 0.05 else f"{n:.1f}"
        return f"  ≈ {n_fmt} × {desc}"
    return ""


class PlanPreviewWindow(QDialog):
    """Modal de revisión del plan antes de exportar."""

    COMIDAS_ORDEN = ["desayuno", "almuerzo", "comida", "cena"]
    COMIDAS_LABEL = {
        "desayuno": "Desayuno",
        "almuerzo": "Almuerzo",
        "comida":   "Comida",
        "cena":     "Cena",
    }

    def __init__(self, parent, cliente, plan: dict):
        super().__init__(parent)
        self.setWindowTitle("Preview del Plan — Paso 2 de 3")
        self.resize(760, 850)
        self.setModal(True)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(8)

        # Header
        lbl_step = QLabel("Paso 2 de 3 · Preview del plan")
        lbl_step.setAlignment(Qt.AlignCenter)
        lbl_step.setStyleSheet("color: #9B4FB0; font-size: 13px; font-weight: bold;")
        root.addWidget(lbl_step)

        lbl_nombre = QLabel(f"Cliente: {cliente.nombre}")
        lbl_nombre.setAlignment(Qt.AlignCenter)
        lbl_nombre.setStyleSheet("color: #F5F5F5; font-size: 21px; font-weight: bold;")
        root.addWidget(lbl_nombre)

        obj = getattr(cliente, "objetivo", "").upper()
        kcal = getattr(cliente, "kcal_objetivo", 0)
        lbl_meta = QLabel(f"Meta: {obj}  |  Kcal objetivo del día: {kcal:.0f}")
        lbl_meta.setAlignment(Qt.AlignCenter)
        lbl_meta.setStyleSheet("color: #D4A84B; font-size: 12px;")
        root.addWidget(lbl_meta)

        # Scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        inner = QWidget()
        inner.setStyleSheet("background-color: #0D0D0D;")
        inner_layout = QVBoxLayout(inner)
        inner_layout.setSpacing(8)
        inner_layout.setContentsMargins(4, 4, 4, 4)
        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

        self._renderizar(inner_layout, plan)

        # Footer
        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setSpacing(12)

        btn_confirmar = QPushButton("Confirmar y Exportar")
        btn_confirmar.setMinimumHeight(42)
        btn_confirmar.setStyleSheet(
            "QPushButton { background-color: #9B4FB0; color: #FFFFFF;"
            " border-radius: 10px; font-size: 14px; font-weight: bold; }"
            "QPushButton:hover { background-color: #B565C6; }"
        )
        btn_confirmar.clicked.connect(self.accept)
        btn_layout.addWidget(btn_confirmar)

        btn_cancelar = QPushButton("Volver a Captura")
        btn_cancelar.setMinimumHeight(42)
        btn_cancelar.setStyleSheet(
            "QPushButton { background-color: transparent; color: #B8B8B8;"
            " border: 1px solid #444444; border-radius: 10px; font-size: 14px; }"
            "QPushButton:hover { background-color: #2A2A2A; }"
        )
        btn_cancelar.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancelar)

        root.addWidget(btn_row)

    # ------------------------------------------------------------------

    def _renderizar(self, layout: QVBoxLayout, plan: dict) -> None:
        kcal_t = prot_t = carb_t = gras_t = 0.0

        for clave in self.COMIDAS_ORDEN:
            if clave not in plan:
                continue
            comida = plan[clave]
            label  = self.COMIDAS_LABEL.get(clave, clave.capitalize())
            kcal   = comida.get("kcal_real", comida.get("kcal_objetivo", 0))
            p, c, g = (
                comida.get("proteinas_g", 0),
                comida.get("carbohidratos_g", 0),
                comida.get("grasas_g", 0),
            )
            kcal_t += kcal; prot_t += p; carb_t += c; gras_t += g

            card = QFrame()
            card.setStyleSheet(
                "QFrame { background-color: #1A1A1A; border: 1px solid #444444;"
                " border-radius: 10px; }"
            )
            cl = QVBoxLayout(card)
            cl.setContentsMargins(14, 10, 14, 10)
            cl.setSpacing(4)

            lbl_n = QLabel(label)
            lbl_n.setStyleSheet("color: #F5F5F5; font-size: 15px; font-weight: bold;")
            cl.addWidget(lbl_n)

            # Métricas
            metrics_w = QWidget()
            metrics_w.setStyleSheet("background: transparent;")
            mg = QGridLayout(metrics_w)
            mg.setSpacing(6)
            mg.setContentsMargins(0, 0, 0, 0)
            self._metric(mg, 0, "Kcal",       f"{kcal:.0f}",  "#D4A84B")
            self._metric(mg, 1, "Proteína",   f"{p:.0f} g",   "#4CAF50")
            self._metric(mg, 2, "Carbohid.",  f"{c:.0f} g",   "#42A5F5")
            self._metric(mg, 3, "Grasas",     f"{g:.0f} g",   "#FFA726")
            cl.addWidget(metrics_w)

            # Separador
            sep = QFrame()
            sep.setFrameShape(QFrame.HLine)
            sep.setStyleSheet("background-color: #333333; border: none;")
            sep.setFixedHeight(1)
            cl.addWidget(sep)

            lbl_g = QLabel("Guía de porciones")
            lbl_g.setStyleSheet("color: #B8B8B8; font-size: 11px; font-weight: bold;")
            cl.addWidget(lbl_g)

            alimentos = comida.get("alimentos", {})
            for nombre, gramos in alimentos.items():
                nombre_fmt = nombre.replace("_", " ").title()
                equiv = _equiv_txt(nombre, gramos)
                row_w = QWidget()
                row_w.setStyleSheet("background: transparent;")
                rl = QHBoxLayout(row_w)
                rl.setContentsMargins(0, 0, 0, 0)
                rl.setSpacing(0)
                lbl_al = QLabel(f"• {nombre_fmt}")
                lbl_al.setStyleSheet("color: #D0D0D0; font-size: 11px;")
                rl.addWidget(lbl_al)
                rl.addStretch()
                lbl_gr = QLabel(f"{gramos:.0f} g{equiv}")
                lbl_gr.setStyleSheet("color: #B8B8B8; font-size: 11px;")
                rl.addWidget(lbl_gr)
                cl.addWidget(row_w)

            layout.addWidget(card)

        # Totales
        total = QFrame()
        total.setStyleSheet(
            "QFrame { background-color: #232323; border: 1px solid #D4A84B; border-radius: 10px; }"
        )
        tl = QVBoxLayout(total)
        tl.setContentsMargins(14, 10, 14, 10)
        lbl_rt = QLabel("Resumen del día")
        lbl_rt.setAlignment(Qt.AlignCenter)
        lbl_rt.setStyleSheet("color: #F5F5F5; font-size: 13px; font-weight: bold;")
        tl.addWidget(lbl_rt)
        mg2 = QGridLayout()
        mg2.setSpacing(6)
        self._metric(mg2, 0, "Kcal totales", f"{kcal_t:.0f}",  "#D4A84B")
        self._metric(mg2, 1, "Proteína",     f"{prot_t:.0f} g","#4CAF50")
        self._metric(mg2, 2, "Carbohid.",    f"{carb_t:.0f} g","#42A5F5")
        self._metric(mg2, 3, "Grasas",       f"{gras_t:.0f} g","#FFA726")
        tl.addLayout(mg2)
        layout.addWidget(total)

    @staticmethod
    def _metric(grid: QGridLayout, col: int, title: str, value: str, accent: str) -> None:
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background-color: #262626; border: 1px solid #3A3A3A; border-radius: 8px; }"
        )
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(6, 6, 6, 6)
        fl.setSpacing(2)
        lt = QLabel(title)
        lt.setAlignment(Qt.AlignCenter)
        lt.setStyleSheet("color: #B8B8B8; font-size: 10px;")
        fl.addWidget(lt)
        lv = QLabel(value)
        lv.setAlignment(Qt.AlignCenter)
        lv.setStyleSheet(f"color: {accent}; font-size: 15px; font-weight: bold;")
        fl.addWidget(lv)
        grid.addWidget(frame, 0, col)

# -*- coding: utf-8 -*-
"""
Panel de administración — PySide6.
Reemplaza gui/ventana_admin.py.
"""

import shutil
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QTabWidget, QWidget, QScrollArea,
    QComboBox, QFileDialog, QMessageBox, QApplication, QGridLayout,
)
from PySide6.QtCore import Qt

from core.branding import branding
from core.licencia import GestorLicencias
from config.constantes import CARPETA_CONFIG
from src.gestor_bd import GestorBDClientes
from utils.logger import logger


class VentanaAdmin(QDialog):
    """Panel de administración del sistema."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Panel de Administración — Método Base")
        self.resize(820, 720)
        self.setModal(True)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        self.branding    = branding
        self.gestor_bd   = GestorBDClientes()
        self.gestor_lic  = GestorLicencias()
        self._temas      = self.branding.obtener_temas_preconfigurados()

        self._build_ui()
        logger.info("[ADMIN] Panel de administración abierto")

    # ------------------------------------------------------------------
    # UI principal
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(8)

        # Header
        hdr = QFrame()
        hdr.setStyleSheet(
            "QFrame { background-color: #1A1A1A; border-radius: 10px; border: none; }"
        )
        hdr.setFixedHeight(72)
        hl = QVBoxLayout(hdr)
        hl.setAlignment(Qt.AlignCenter)
        t = QLabel("⚙️  Panel de Administración")
        t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet("color: #9B4FB0; font-size: 22px; font-weight: bold;")
        hl.addWidget(t)
        sub = QLabel("Configuración avanzada del sistema")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("color: #B8B8B8; font-size: 12px;")
        hl.addWidget(sub)
        root.addWidget(hdr)

        # Tabs
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        self._crear_tab_branding()
        self._crear_tab_bd()
        self._crear_tab_busqueda()

        # Cerrar
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setFixedWidth(140)
        btn_cerrar.setStyleSheet(
            "QPushButton { background-color: transparent; border: 1px solid #B8B8B8;"
            " color: #B8B8B8; border-radius: 6px; font-size: 13px; padding: 6px; }"
            "QPushButton:hover { background-color: #1A1A1A; color: #F5F5F5; }"
        )
        btn_cerrar.clicked.connect(self.accept)
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        rl = QHBoxLayout(row)
        rl.addStretch()
        rl.addWidget(btn_cerrar)
        root.addWidget(row)

    # ------------------------------------------------------------------
    # Pestaña Branding
    # ------------------------------------------------------------------

    def _crear_tab_branding(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        scroll.setWidget(inner)
        self.tabs.addTab(scroll, "🎨 Branding")

        # Tema visual
        self._seccion(layout, "Tema Visual del Gym")
        temas = list(self._temas.keys())
        tema_actual = self.branding.get("tema_visual", temas[0] if temas else "")

        row_tema = QWidget()
        row_tema.setStyleSheet("background: transparent;")
        rt = QHBoxLayout(row_tema)
        rt.setContentsMargins(0, 0, 0, 0)
        rt.addWidget(QLabel("Tema preconfigurado:"))
        self.combo_tema = QComboBox()
        self.combo_tema.addItems(temas or ["Metodo Base Clasico"])
        if tema_actual in temas:
            self.combo_tema.setCurrentText(tema_actual)
        rt.addWidget(self.combo_tema, 1)
        btn_aplicar_tema = QPushButton("Aplicar")
        btn_aplicar_tema.clicked.connect(self._aplicar_tema)
        rt.addWidget(btn_aplicar_tema)
        layout.addWidget(row_tema)

        # Datos del gym
        self._seccion(layout, "Información del Gimnasio")
        self.entry_nombre_gym   = self._campo(layout, "Nombre del Gym:",  self.branding.get("nombre_gym", ""))
        self.entry_nombre_corto = self._campo(layout, "Nombre Corto:",    self.branding.get("nombre_corto", ""))
        self.entry_tagline      = self._campo(layout, "Tagline:",         self.branding.get("tagline", ""))

        self._seccion(layout, "Información de Contacto")
        self.entry_tel     = self._campo(layout, "Teléfono:",   self.branding.get("contacto.telefono", ""))
        self.entry_email   = self._campo(layout, "Email:",      self.branding.get("contacto.email", ""))
        self.entry_dir     = self._campo(layout, "Dirección:",  self.branding.get("contacto.direccion", ""))
        self.entry_wa      = self._campo(layout, "WhatsApp:",   self.branding.get("contacto.whatsapp", ""))

        self._seccion(layout, "Colores Corporativos")
        self.entry_col_prim = self._campo(layout, "Color Primario (hex):",      self.branding.get("colores.primario", "#9B4FB0"))
        self.entry_col_sec  = self._campo(layout, "Color Secundario (hex):",    self.branding.get("colores.secundario", "#D4A84B"))
        self.entry_col_pdf  = self._campo(layout, "Color Encabezado PDF (hex):", self.branding.get("pdf.color_encabezado", "#9B4FB0"))

        self._seccion(layout, "Logo del PDF")
        self.entry_logo = self._campo(layout, "Ruta logo PDF:", self.branding.get("pdf.logo_path", "assets/logo.png"))
        self.entry_logo.setReadOnly(True)

        logo_btns = QWidget()
        logo_btns.setStyleSheet("background: transparent;")
        lb = QHBoxLayout(logo_btns)
        lb.setContentsMargins(0, 0, 0, 0)
        b1 = QPushButton("Seleccionar Logo...")
        b1.clicked.connect(self._seleccionar_logo)
        lb.addWidget(b1)
        b2 = QPushButton("Restaurar Predeterminado")
        b2.setObjectName("btn_secondary")
        b2.setStyleSheet(
            "QPushButton { background-color: transparent; border: 1px solid #B8B8B8;"
            " color: #B8B8B8; border-radius: 6px; padding: 6px 10px; }"
            "QPushButton:hover { background-color: #2A2A2A; }"
        )
        b2.clicked.connect(self._restaurar_logo)
        lb.addWidget(b2)
        lb.addStretch()
        layout.addWidget(logo_btns)

        # Guardar
        btn_guardar = QPushButton("💾  Guardar Configuración")
        btn_guardar.setMinimumHeight(44)
        btn_guardar.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: #FFFFFF;"
            " border-radius: 8px; font-size: 13px; font-weight: bold; }"
            "QPushButton:hover { background-color: #43A047; }"
        )
        btn_guardar.clicked.connect(self._guardar_branding)
        layout.addWidget(btn_guardar)
        layout.addStretch()

    # ------------------------------------------------------------------
    # Pestaña Base de Datos
    # ------------------------------------------------------------------

    def _crear_tab_bd(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        scroll.setWidget(inner)
        self.tabs.addTab(scroll, "💾 Base de Datos")

        # Estado de licencia
        lic_card = self._card()
        lc = QVBoxLayout(lic_card)
        lc.setContentsMargins(16, 14, 16, 14)
        t = QLabel("🔐  Estado de Licencia")
        t.setStyleSheet("color: #9B4FB0; font-size: 16px; font-weight: bold;")
        lc.addWidget(t)

        self.lbl_lic_estado = QLabel("Estado: consultando...")
        self.lbl_lic_plan   = QLabel("Plan: --")
        self.lbl_lic_dias   = QLabel("Días restantes: --")
        self.lbl_lic_corte  = QLabel("Fecha de corte: --")
        for lbl in (self.lbl_lic_estado, self.lbl_lic_plan, self.lbl_lic_dias, self.lbl_lic_corte):
            lbl.setStyleSheet("color: #F5F5F5; font-size: 12px;")
            lc.addWidget(lbl)

        lic_btns = QWidget()
        lic_btns.setStyleSheet("background: transparent;")
        lb = QHBoxLayout(lic_btns)
        lb.setContentsMargins(0, 8, 0, 0)
        b_renov = QPushButton("🔄 Renovar ahora")
        b_renov.setStyleSheet(
            "QPushButton { background-color: #FF9800; color: #000; border-radius: 6px; padding: 8px; }"
            "QPushButton:hover { background-color: #F57C00; }"
        )
        b_renov.clicked.connect(self._renovar_licencia)
        lb.addWidget(b_renov)
        b_cid = QPushButton("📋 Copiar ID instalación")
        b_cid.setStyleSheet(
            "QPushButton { background-color: transparent; border: 1px solid #B8B8B8;"
            " color: #B8B8B8; border-radius: 6px; padding: 8px; }"
        )
        b_cid.clicked.connect(self._copiar_id_lic)
        lb.addWidget(b_cid)
        lb.addStretch()
        lc.addWidget(lic_btns)
        layout.addWidget(lic_card)

        self._refrescar_licencia()

        # Estadísticas
        stats = self.gestor_bd.obtener_estadisticas_gym()
        stats_card = self._card()
        sl = QVBoxLayout(stats_card)
        sl.setContentsMargins(16, 14, 16, 14)
        t2 = QLabel("📊  Estadísticas del Gimnasio")
        t2.setStyleSheet("color: #9B4FB0; font-size: 16px; font-weight: bold;")
        sl.addWidget(t2)
        sg = QGridLayout()
        sg.setSpacing(8)
        self._stat_box(sg, 0, 0, "👥 Total Clientes",          str(stats.get("total_clientes", 0)))
        self._stat_box(sg, 0, 1, "📈 Clientes Nuevos (30d)",   str(stats.get("clientes_nuevos", 0)))
        self._stat_box(sg, 1, 0, "🍽️ Planes Generados (30d)",  str(stats.get("planes_periodo", 0)))
        self._stat_box(sg, 1, 1, "⚡ Promedio Kcal",            f"{stats.get('promedio_kcal', 0):.0f}")
        sl.addLayout(sg)
        layout.addWidget(stats_card)

        # Backups
        back_card = self._card()
        bl = QVBoxLayout(back_card)
        bl.setContentsMargins(16, 14, 16, 14)
        t3 = QLabel("💾  Gestión de Backups")
        t3.setStyleSheet("color: #9B4FB0; font-size: 16px; font-weight: bold;")
        bl.addWidget(t3)
        info = QLabel("Los backups se crean automáticamente cada 7 días.")
        info.setStyleSheet("color: #B8B8B8; font-size: 11px;")
        info.setWordWrap(True)
        bl.addWidget(info)
        back_btns = QWidget()
        back_btns.setStyleSheet("background: transparent;")
        bb = QHBoxLayout(back_btns)
        bb.setContentsMargins(0, 8, 0, 0)
        b_cr = QPushButton("📦 Crear Backup")
        b_cr.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: #FFFFFF; border-radius: 6px; padding: 8px; }"
            "QPushButton:hover { background-color: #43A047; }"
        )
        b_cr.clicked.connect(self._crear_backup)
        bb.addWidget(b_cr)
        b_lm = QPushButton("🗑️ Limpiar Antiguos")
        b_lm.setStyleSheet(
            "QPushButton { background-color: #FF9800; color: #000; border-radius: 6px; padding: 8px; }"
        )
        b_lm.clicked.connect(self._limpiar_backups)
        bb.addWidget(b_lm)
        bb.addStretch()
        bl.addWidget(back_btns)
        layout.addWidget(back_card)

        # Reportes
        btn_rep = QPushButton("📊  Ver Reportes Completos")
        btn_rep.setMinimumHeight(50)
        btn_rep.setStyleSheet(
            "QPushButton { background-color: #9B4FB0; color: #FFFFFF;"
            " border-radius: 8px; font-size: 14px; font-weight: bold; }"
            "QPushButton:hover { background-color: #B565C6; }"
        )
        btn_rep.clicked.connect(self._abrir_reportes)
        layout.addWidget(btn_rep)
        layout.addStretch()

    # ------------------------------------------------------------------
    # Pestaña Búsqueda
    # ------------------------------------------------------------------

    def _crear_tab_busqueda(self) -> None:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        self.tabs.addTab(w, "🔍 Búsqueda")

        s_card = self._card()
        sl = QVBoxLayout(s_card)
        sl.setContentsMargins(16, 12, 16, 12)
        t = QLabel("🔍  Buscar Cliente")
        t.setStyleSheet("color: #9B4FB0; font-size: 14px; font-weight: bold;")
        sl.addWidget(t)
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        self.entry_busqueda = QLineEdit()
        self.entry_busqueda.setPlaceholderText("Nombre, teléfono o ID del cliente...")
        rl.addWidget(self.entry_busqueda, 1)
        btn_b = QPushButton("Buscar")
        btn_b.clicked.connect(self._buscar_clientes)
        rl.addWidget(btn_b)
        sl.addWidget(row)
        layout.addWidget(s_card)

        # Resultados
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: 1px solid #444444; border-radius: 8px;")
        self.resultados_inner = QWidget()
        self.resultados_inner.setStyleSheet("background-color: #0D0D0D;")
        self.resultados_layout = QVBoxLayout(self.resultados_inner)
        self.resultados_layout.setSpacing(6)
        self.resultados_layout.setContentsMargins(8, 8, 8, 8)
        scroll.setWidget(self.resultados_inner)
        layout.addWidget(scroll, 1)

    # ------------------------------------------------------------------
    # Helpers de UI
    # ------------------------------------------------------------------

    def _seccion(self, layout: QVBoxLayout, titulo: str) -> None:
        lbl = QLabel(titulo)
        lbl.setStyleSheet(
            "color: #D4A84B; font-size: 13px; font-weight: bold; margin-top: 8px;"
        )
        layout.addWidget(lbl)

    def _campo(self, layout: QVBoxLayout, label: str, valor: str) -> QLineEdit:
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(label)
        lbl.setFixedWidth(200)
        lbl.setStyleSheet("color: #F5F5F5; font-size: 12px;")
        rl.addWidget(lbl)
        entry = QLineEdit(valor)
        rl.addWidget(entry, 1)
        layout.addWidget(row)
        return entry

    def _card(self) -> QFrame:
        f = QFrame()
        f.setStyleSheet(
            "QFrame { background-color: #1A1A1A; border-radius: 10px; border: none; }"
        )
        return f

    def _stat_box(self, grid: QGridLayout, row: int, col: int, titulo: str, valor: str) -> None:
        f = QFrame()
        f.setStyleSheet(
            "QFrame { background-color: #2A2A2A; border-radius: 8px; border: none; }"
        )
        fl = QVBoxLayout(f)
        fl.setContentsMargins(12, 10, 12, 10)
        fl.setSpacing(4)
        t = QLabel(titulo)
        t.setStyleSheet("color: #B8B8B8; font-size: 11px;")
        t.setAlignment(Qt.AlignCenter)
        fl.addWidget(t)
        v = QLabel(valor)
        v.setAlignment(Qt.AlignCenter)
        v.setStyleSheet("color: #9B4FB0; font-size: 22px; font-weight: bold;")
        fl.addWidget(v)
        grid.addWidget(f, row, col)

    # ------------------------------------------------------------------
    # Acciones de Branding
    # ------------------------------------------------------------------

    def _aplicar_tema(self) -> None:
        tema_name = self.combo_tema.currentText()
        tema_data = self._temas.get(tema_name, {})
        if not tema_data:
            return
        for key, val in tema_data.items():
            self.branding.set(key, val)
        # Actualizar entries de colores
        self.entry_col_prim.setText(self.branding.get("colores.primario", "#9B4FB0"))
        self.entry_col_sec.setText(self.branding.get("colores.secundario", "#D4A84B"))
        logger.info("[ADMIN] Tema aplicado: %s", tema_name)

    def _guardar_branding(self) -> None:
        cambios = {
            "nombre_gym":            self.entry_nombre_gym.text().strip(),
            "nombre_corto":          self.entry_nombre_corto.text().strip(),
            "tagline":               self.entry_tagline.text().strip(),
            "contacto.telefono":     self.entry_tel.text().strip(),
            "contacto.email":        self.entry_email.text().strip(),
            "contacto.direccion":    self.entry_dir.text().strip(),
            "contacto.whatsapp":     self.entry_wa.text().strip(),
            "colores.primario":      self.entry_col_prim.text().strip(),
            "colores.secundario":    self.entry_col_sec.text().strip(),
            "pdf.color_encabezado":  self.entry_col_pdf.text().strip(),
            "pdf.logo_path":         self.entry_logo.text().strip(),
        }
        for key, val in cambios.items():
            if val:
                self.branding.set(key, val)
        self.branding.guardar()
        logger.info("[ADMIN] Branding guardado")
        QMessageBox.information(self, "Guardado", "Configuración de branding guardada correctamente.")

        # Notificar a la ventana principal
        if self.parent() and hasattr(self.parent(), "aplicar_branding_preview"):
            self.parent().aplicar_branding_preview(
                primario=cambios["colores.primario"],
                secundario=cambios["colores.secundario"],
                nombre_corto=cambios.get("nombre_corto"),
                nombre_gym=cambios.get("nombre_gym"),
                tagline=cambios.get("tagline"),
            )

    def _seleccionar_logo(self) -> None:
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Logo",
            str(Path(CARPETA_CONFIG)),
            "Imágenes (*.png *.jpg *.jpeg *.svg)",
        )
        if not ruta:
            return
        destino = Path(CARPETA_CONFIG) / "logo_custom.png"
        try:
            shutil.copy2(ruta, destino)
            self.entry_logo.setText(str(destino))
            QMessageBox.information(self, "Logo actualizado", f"Logo copiado a:\n{destino}")
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No se pudo copiar el logo:\n{exc}")

    def _restaurar_logo(self) -> None:
        self.entry_logo.setText("assets/logo.png")

    # ------------------------------------------------------------------
    # Acciones de BD
    # ------------------------------------------------------------------

    def _refrescar_licencia(self) -> None:
        try:
            valida, msg, info = self.gestor_lic.validar_licencia()
            color = "#4CAF50" if valida else "#F44336"
            self.lbl_lic_estado.setText(f"Estado: {msg}")
            self.lbl_lic_estado.setStyleSheet(f"color: {color}; font-size: 12px;")
            if info:
                self.lbl_lic_plan.setText(f"Plan: {info.get('plan_comercial', '--')}")
                self.lbl_lic_dias.setText(f"Días restantes: {info.get('dias_restantes', '--')}")
                self.lbl_lic_corte.setText(f"Fecha de corte: {info.get('fecha_corte', '--')}")
        except Exception as exc:
            self.lbl_lic_estado.setText(f"Error al consultar licencia: {exc}")

    def _renovar_licencia(self) -> None:
        from ui_desktop.pyside.ventana_licencia import VentanaActivacionLicencia
        nombre = self.branding.get("nombre_gym", "MetodoBase")
        dlg = VentanaActivacionLicencia(self, gestor=self.gestor_lic, nombre_gym=nombre)
        if dlg.exec() and dlg.activada:
            self._refrescar_licencia()

    def _copiar_id_lic(self) -> None:
        id_inst = self.gestor_lic.obtener_id_instalacion()
        QApplication.clipboard().setText(id_inst)
        QMessageBox.information(self, "ID copiado", "ID de instalación copiado al portapapeles.")

    def _crear_backup(self) -> None:
        try:
            resultado = self.gestor_bd.crear_backup()
            if resultado:
                QMessageBox.information(self, "Backup creado", f"Backup guardado en:\n{resultado}")
            else:
                QMessageBox.warning(self, "Advertencia", "No se pudo crear el backup.")
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Error al crear backup:\n{exc}")

    def _limpiar_backups(self) -> None:
        resp = QMessageBox.question(
            self, "Limpiar backups",
            "¿Deseas eliminar los backups con más de 30 días?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if resp == QMessageBox.Yes:
            eliminados = self.gestor_bd.limpiar_backups_antiguos(dias=30)
            QMessageBox.information(self, "Listos", f"Se eliminaron {eliminados} backups antiguos.")

    def _abrir_reportes(self) -> None:
        from ui_desktop.pyside.ventana_reportes import VentanaReportes
        dlg = VentanaReportes(self)
        dlg.exec()

    # ------------------------------------------------------------------
    # Búsqueda de clientes
    # ------------------------------------------------------------------

    def _buscar_clientes(self) -> None:
        # Limpiar resultados anteriores
        while self.resultados_layout.count():
            item = self.resultados_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        query = self.entry_busqueda.text().strip()
        if not query:
            lbl = QLabel("Escribe un término de búsqueda.")
            lbl.setStyleSheet("color: #B8B8B8;")
            self.resultados_layout.addWidget(lbl)
            return

        try:
            clientes = self.gestor_bd.buscar_clientes(query)
            if not clientes:
                lbl = QLabel("No se encontraron clientes.")
                lbl.setStyleSheet("color: #B8B8B8;")
                self.resultados_layout.addWidget(lbl)
                return
            for cli in clientes[:50]:
                card = QFrame()
                card.setStyleSheet(
                    "QFrame { background-color: #1A1A1A; border-radius: 8px; border: none; }"
                )
                cl = QHBoxLayout(card)
                cl.setContentsMargins(12, 8, 12, 8)
                nombre = cli.get("nombre", "—")
                tel    = cli.get("telefono", "—")
                lbl = QLabel(f"<b>{nombre}</b>  •  {tel}")
                lbl.setStyleSheet("color: #F5F5F5; font-size: 12px;")
                cl.addWidget(lbl, 1)
                self.resultados_layout.addWidget(card)
            self.resultados_layout.addStretch()
        except Exception as exc:
            lbl = QLabel(f"Error: {exc}")
            lbl.setStyleSheet("color: #F44336;")
            self.resultados_layout.addWidget(lbl)

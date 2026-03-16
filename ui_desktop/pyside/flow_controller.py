# -*- coding: utf-8 -*-
"""
FlowController — Orquestador del flujo de usuarios regulares.

Gestiona la secuencia de paneles para el flujo "Usuario Regular":

  VentanaAuth ──login/registro──▶ PanelPerfilDetalle ──▶ PanelMetodoBase
                                                              │
                                              ┌───────────────▼───────────────┐
                                              │ PanelPreferenciasAlimentos     │
                                              └───────────────────────────────┘

Para el flujo GYM este controlador no se usa; main.py lo maneja directamente.

Uso mínimo:
    ctrl = FlowController()
    resultado = ctrl.exec()
    if resultado == FlowController.RESULTADO_SESION_OK:
        # sesion disponible en ctrl.sesion_activa
        ...
    elif resultado == FlowController.RESULTADO_MODO_GYM:
        # continuar con activación de licencia + MainWindow
        ...
"""
from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QWidget

from core.services.auth_service import AuthService, SesionActiva, crear_auth_service
from ui_desktop.pyside.panel_inicio import PanelInicio, ResultadoInicio
from utils.logger import logger

if TYPE_CHECKING:
    from ui_desktop.pyside.panel_metodo_base import PanelMetodoBase


class FlowController(QDialog):
    """Orquestador modal del flujo completo de la aplicación."""

    # Códigos de retorno de exec()
    RESULTADO_CANCELADO   = 0
    RESULTADO_SESION_OK   = 1   # usuario regular autenticado y con perfil
    RESULTADO_MODO_GYM    = 2   # el usuario eligió "GYM"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._auth_service: AuthService | None = None
        self._sesion: SesionActiva | None = None
        self._perfil: dict = {}
        self._excluidos: list[str] = []
        self._resultado_final = self.RESULTADO_CANCELADO

        self.setWindowTitle("Método Base")
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        # El diálogo es "invisible" — sólo orquesta modales hijos
        self.setVisible(False)

    # ── API pública ───────────────────────────────────────────────────────

    @property
    def sesion_activa(self) -> SesionActiva | None:
        return self._sesion

    @property
    def perfil(self) -> dict:
        return self._perfil

    @property
    def excluidos(self) -> list[str]:
        return self._excluidos

    # ── Punto de entrada ──────────────────────────────────────────────────

    def exec(self) -> int:  # type: ignore[override]
        """Lanza el flujo completo; devuelve el código de resultado."""
        resultado = self._ejecutar_flujo()
        self._resultado_final = resultado
        return resultado

    # ── Flujo principal ───────────────────────────────────────────────────

    def _ejecutar_flujo(self) -> int:
        # 1) Selección de tipo de usuario
        inicio = PanelInicio(self.parent())
        code = inicio.exec()

        if code == ResultadoInicio.GYM:
            logger.info("[FLOW] Usuario eligió flujo GYM.")
            return self.RESULTADO_MODO_GYM

        if code != ResultadoInicio.USUARIO:
            logger.info("[FLOW] Panel inicio cancelado.")
            return self.RESULTADO_CANCELADO

        # 2) Autenticación (flujo usuario regular)
        try:
            self._auth_service = crear_auth_service()
            from ui_desktop.pyside.ventana_auth import VentanaAuth
            auth_dlg = VentanaAuth(auth_service=self._auth_service, parent=self.parent())
            if not auth_dlg.exec() or not self._auth_service.autenticado:
                logger.info("[FLOW] Autenticación cancelada.")
                return self.RESULTADO_CANCELADO
            self._sesion = self._auth_service.sesion_activa
            logger.info("[FLOW] Autenticado id=%s rol=%s",
                        self._sesion.id_usuario, self._sesion.rol)
        except Exception as exc:
            logger.error("[FLOW] Error en autenticación: %s", exc)
            return self.RESULTADO_CANCELADO

        # 3) Cargar preferencias guardadas
        self._cargar_prefs()

        # 4) Perfil detalle (usuario nuevo sin perfil → forzado; con prefs → omitible)
        has_perfil = bool(self._perfil.get("peso_kg"))
        if not has_perfil:
            if not self._mostrar_perfil_detalle():
                return self.RESULTADO_CANCELADO

        # 5) Dashboard MetodoBase (permanece abierto mientras el usuario trabaje)
        self._mostrar_metodo_base()

        return self.RESULTADO_SESION_OK

    # ── Pasos individuales ────────────────────────────────────────────────

    def _cargar_prefs(self) -> None:
        if not self._sesion:
            return
        try:
            from src.gestor_preferencias import GestorPreferencias
            gp = GestorPreferencias(self._sesion.id_usuario)
            datos = gp.cargar()
            # Separar perfil corporal de exclusiones
            self._excluidos = datos.get("alimentos_excluidos", [])
            self._perfil = {k: v for k, v in datos.items() if k != "alimentos_excluidos"}
        except Exception as exc:
            logger.warning("[FLOW] No se pudo cargar prefs: %s", exc)

    def _guardar_perfil(self, perfil: dict) -> None:
        """Persiste el perfil en GestorPreferencias."""
        self._perfil = perfil
        if not self._sesion:
            return
        try:
            from src.gestor_preferencias import GestorPreferencias
            gp = GestorPreferencias(self._sesion.id_usuario)
            datos_actuales = gp.cargar()
            datos_actuales.update(perfil)
            gp.guardar(datos_actuales)
        except Exception as exc:
            logger.warning("[FLOW] No se pudo guardar perfil: %s", exc)

    def _mostrar_perfil_detalle(self) -> bool:
        """Muestra el diálogo de perfil. Retorna False si el usuario cancela."""
        from ui_desktop.pyside.panel_perfil_detalle import PanelPerfilDetalle
        dlg = PanelPerfilDetalle(
            sesion=self._sesion,
            prefs_actuales=self._perfil,
            parent=self.parent(),
        )
        dlg.perfil_guardado.connect(self._guardar_perfil)
        resultado = dlg.exec()
        return resultado != QDialog.Rejected or self._perfil  # omitir es válido si hay datos

    def _mostrar_metodo_base(self) -> None:
        """Muestra el dashboard MetodoBase y gestiona sus señales."""
        from ui_desktop.pyside.panel_metodo_base import PanelMetodoBase
        dashboard = PanelMetodoBase(
            sesion=self._sesion,
            perfil=self._perfil,
            alimentos_excluidos=self._excluidos,
            parent=self.parent(),
        )
        dashboard.abrir_preferencias.connect(
            lambda: self._mostrar_preferencias(dashboard)
        )
        dashboard.editar_perfil.connect(
            lambda: self._editar_perfil(dashboard)
        )
        dashboard.generar_plan.connect(
            lambda: self._generar_plan(dashboard)
        )
        dashboard.cerrar_sesion.connect(dashboard.reject)
        dashboard.exec()

    def _mostrar_preferencias(self, dashboard: "PanelMetodoBase") -> None:
        from ui_desktop.pyside.panel_preferencias_alimentos import PanelPreferenciasAlimentos
        dlg = PanelPreferenciasAlimentos(
            id_usuario=self._sesion.id_usuario,
            excluidos_actuales=self._excluidos,
            parent=dashboard,
        )
        dlg.excluidos_actualizados.connect(self._on_excluidos_actualizados)
        dlg.exec()
        # Refrescar badge en dashboard
        dashboard.actualizar_excluidos(self._excluidos)

    def _on_excluidos_actualizados(self, excluidos: list[str]) -> None:
        self._excluidos = excluidos

    def _editar_perfil(self, dashboard: "PanelMetodoBase") -> None:
        from ui_desktop.pyside.panel_perfil_detalle import PanelPerfilDetalle
        dlg = PanelPerfilDetalle(
            sesion=self._sesion,
            prefs_actuales=self._perfil,
            parent=dashboard,
        )
        dlg.perfil_guardado.connect(self._guardar_perfil)
        dlg.exec()

    def _generar_plan(self, dashboard: "PanelMetodoBase") -> None:
        """Abre el dialogo de generación de plan nutricional para el usuario."""
        from ui_desktop.pyside.dialogo_generar_plan import DialogoGenerarPlan
        dlg = DialogoGenerarPlan(
            sesion=self._sesion,
            perfil=self._perfil,
            excluidos=self._excluidos,
            parent=dashboard,
        )
        dlg.exec()

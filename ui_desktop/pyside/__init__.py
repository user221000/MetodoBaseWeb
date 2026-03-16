# -*- coding: utf-8 -*-
"""Subpaquete PySide6 — expone las ventanas principales."""
from ui_desktop.pyside.main_window import MainWindow
from ui_desktop.pyside.ventana_licencia import VentanaActivacionLicencia
from ui_desktop.pyside.wizard_onboarding import WizardOnboarding
from ui_desktop.pyside.ventana_admin import VentanaAdmin
from ui_desktop.pyside.ventana_clientes import VentanaClientes
from ui_desktop.pyside.ventana_reportes import VentanaReportes
from ui_desktop.pyside.ventana_preview import PlanPreviewWindow

__all__ = [
    "MainWindow",
    "VentanaActivacionLicencia",
    "WizardOnboarding",
    "VentanaAdmin",
    "VentanaClientes",
    "VentanaReportes",
    "PlanPreviewWindow",
]

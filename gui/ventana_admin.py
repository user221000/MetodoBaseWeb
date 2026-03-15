# -*- coding: utf-8 -*-
"""
Panel de administración para configuración del sistema.

Permite:
- Editar branding del gym
- Ver estadísticas
- Backup de base de datos
- Búsqueda de clientes
"""

import shutil
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog, messagebox
from datetime import datetime
from typing import Dict

from core.branding import branding
from core.licencia import GestorLicencias
from config.constantes import CARPETA_CONFIG
from src.gestor_bd import GestorBDClientes
from src import alimentos_sqlite
from src.alimentos_base import recargar_desde_db
from src.validaciones_alimentos import validar_alimento
from config import catalogo_alimentos
from gui.ventana_reportes import VentanaReportes
from utils.helpers import activar_modal_seguro
from utils.logger import logger
from utils.telemetria import registrar_evento


class VentanaAdmin(ctk.CTkToplevel):
    """
    Ventana de administración del sistema.

    Pestañas:
    1. Branding: Editar nombre, colores, contacto
    2. Base de Datos: Backups y estadísticas
    3. Búsqueda: Buscar y ver clientes

    Acceso: Ctrl+Shift+A en la ventana principal
    """

    COLOR_BG = "#0D0D0D"
    COLOR_CARD = "#1A1A1A"
    COLOR_PRIMARY = "#9B4FB0"
    COLOR_TEXT = "#F5F5F5"
    COLOR_TEXT_MUTED = "#B8B8B8"
    COLOR_SUCCESS = "#4CAF50"
    COLOR_ERROR = "#F44336"
    COLOR_WARNING = "#FF9800"

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_app = parent

        self.title("Panel de Administración - Método Base")
        self.geometry("800x700")
        self.resizable(True, True)
        self.configure(fg_color=self.COLOR_BG)

        # Gestores
        self.branding = branding
        self.gestor_bd = GestorBDClientes()
        self.gestor_licencias = GestorLicencias()

        self._crear_ui()
        activar_modal_seguro(self, parent)

        logger.info("[ADMIN] Panel de administración abierto")

    def _crear_ui(self):
        """Crea la interfaz del panel."""
        # Header
        header = ctk.CTkFrame(self, fg_color=self.COLOR_CARD, height=80)
        header.pack(fill="x", padx=20, pady=(20, 10))
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="⚙️ Panel de Administración",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=self.COLOR_PRIMARY,
        ).pack(pady=10)

        ctk.CTkLabel(
            header,
            text="Configuración avanzada del sistema",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=self.COLOR_TEXT_MUTED,
        ).pack()

        # Tabview
        self.tabview = ctk.CTkTabview(
            self,
            fg_color=self.COLOR_BG,
            segmented_button_fg_color=self.COLOR_CARD,
            segmented_button_selected_color=self.COLOR_PRIMARY,
            segmented_button_selected_hover_color=self.COLOR_PRIMARY,
            text_color=self.COLOR_TEXT,
        )
        self.tabview.pack(fill="both", expand=True, padx=20, pady=10)

        tab_branding = self.tabview.add("🎨 Branding")
        tab_bd = self.tabview.add("💾 Base de Datos")
        tab_busqueda = self.tabview.add("🔍 Búsqueda")
        tab_alimentos = self.tabview.add("🥗 Alimentos")

        self._crear_tab_branding(tab_branding)
        self._crear_tab_bd(tab_bd)
        self._crear_tab_busqueda(tab_busqueda)
        self._crear_tab_alimentos(tab_alimentos)

        # Botón cerrar
        ctk.CTkButton(
            self,
            text="Cerrar",
            command=self.destroy,
            width=120,
            height=36,
            fg_color="transparent",
            border_width=1,
            border_color=self.COLOR_TEXT_MUTED,
            hover_color=self.COLOR_CARD,
        ).pack(pady=(0, 20))

    # ========== Pestaña Branding ==========

    def _crear_tab_branding(self, parent):
        """Crea la pestaña de configuración de branding."""
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        self._crear_seccion_admin(scroll, "Tema Visual del Gym")

        self._temas_branding = self.branding.obtener_temas_preconfigurados()
        temas_nombres = list(self._temas_branding.keys())
        tema_actual = self.branding.get("tema_visual", temas_nombres[0] if temas_nombres else "")
        if tema_actual not in temas_nombres and temas_nombres:
            tema_actual = temas_nombres[0]

        tema_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        tema_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(
            tema_frame,
            text="Tema preconfigurado:",
            font=ctk.CTkFont(size=12),
            text_color=self.COLOR_TEXT,
            anchor="w",
            width=150,
        ).pack(side="left", padx=(0, 10))

        self.var_tema_visual = ctk.StringVar(value=tema_actual)
        self.menu_tema_visual = ctk.CTkOptionMenu(
            tema_frame,
            values=temas_nombres or ["Metodo Base Clasico"],
            variable=self.var_tema_visual,
            fg_color=self.COLOR_CARD,
            button_color=self.COLOR_PRIMARY,
            button_hover_color=self.COLOR_PRIMARY,
            command=lambda tema: self._aplicar_tema_preconfigurado(tema, mostrar_feedback=False),
        )
        self.menu_tema_visual.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(
            tema_frame,
            text="Aplicar",
            width=90,
            command=lambda: self._aplicar_tema_preconfigurado(mostrar_feedback=True),
            fg_color=self.COLOR_PRIMARY,
        ).pack(side="left")

        self.lbl_tema_info = ctk.CTkLabel(
            scroll,
            text=(
                "Tip: el tema ajusta colores de app y encabezado PDF. "
                "Puedes afinar los hex manualmente debajo."
            ),
            font=ctk.CTkFont(size=11),
            text_color=self.COLOR_TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=680,
        )
        self.lbl_tema_info.pack(fill="x", pady=(2, 8))

        self._crear_seccion_admin(scroll, "Información del Gimnasio")

        self.entry_nombre_gym = self._crear_campo_admin(
            scroll, "Nombre del Gym:", self.branding.get("nombre_gym")
        )
        self.entry_nombre_corto = self._crear_campo_admin(
            scroll, "Nombre Corto:", self.branding.get("nombre_corto")
        )
        self.entry_tagline = self._crear_campo_admin(
            scroll, "Tagline:", self.branding.get("tagline")
        )

        self._crear_seccion_admin(scroll, "Información de Contacto")

        self.entry_telefono = self._crear_campo_admin(
            scroll, "Teléfono:", self.branding.get("contacto.telefono", "")
        )
        self.entry_email = self._crear_campo_admin(
            scroll, "Email:", self.branding.get("contacto.email", "")
        )
        self.entry_direccion = self._crear_campo_admin(
            scroll, "Dirección:", self.branding.get("contacto.direccion", "")
        )
        self.entry_whatsapp = self._crear_campo_admin(
            scroll, "WhatsApp:", self.branding.get("contacto.whatsapp", "")
        )

        self._crear_seccion_admin(scroll, "Colores Corporativos")

        self.entry_color_primario = self._crear_campo_admin(
            scroll, "Color Primario (hex):", self.branding.get("colores.primario")
        )
        self.entry_color_secundario = self._crear_campo_admin(
            scroll, "Color Secundario (hex):", self.branding.get("colores.secundario")
        )
        self.entry_color_pdf = self._crear_campo_admin(
            scroll,
            "Color Encabezado PDF (hex):",
            self.branding.get("pdf.color_encabezado", self.branding.get("colores.primario")),
        )

        self._crear_seccion_admin(scroll, "Logo del PDF (esquina superior derecha)")
        self.entry_logo_pdf_path = self._crear_campo_admin(
            scroll,
            "Ruta logo PDF:",
            self.branding.get("pdf.logo_path", self.branding.get("logo.path", "assets/logo.png")),
        )
        self.entry_logo_pdf_path.configure(state="readonly")

        logo_botones = ctk.CTkFrame(scroll, fg_color="transparent")
        logo_botones.pack(fill="x", pady=(2, 10))
        ctk.CTkButton(
            logo_botones,
            text="Seleccionar Logo...",
            command=self._seleccionar_logo_pdf,
            fg_color=self.COLOR_PRIMARY,
            width=170,
            height=34,
        ).pack(side="left")
        ctk.CTkButton(
            logo_botones,
            text="Usar Logo Predeterminado",
            command=self._restaurar_logo_pdf_default,
            fg_color="transparent",
            border_width=1,
            border_color=self.COLOR_TEXT_MUTED,
            text_color=self.COLOR_TEXT,
            width=210,
            height=34,
        ).pack(side="left", padx=(10, 0))

        ctk.CTkLabel(
            scroll,
            text=(
                "El logo seleccionado se copia al perfil local de esta computadora, "
                "así cada instalación puede tener su propio branding."
            ),
            font=ctk.CTkFont(size=11),
            text_color=self.COLOR_TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=680,
        ).pack(fill="x", pady=(0, 8))

        ctk.CTkButton(
            scroll,
            text="💾 Guardar Configuración",
            command=self._guardar_branding,
            height=44,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=self.COLOR_SUCCESS,
            hover_color="#43A047",
        ).pack(pady=30, fill="x")

    # ========== Pestaña Base de Datos ==========

    def _crear_tab_bd(self, parent):
        """Crea la pestaña de gestión de base de datos."""
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        stats = self.gestor_bd.obtener_estadisticas_gym()

        # Card de licencia
        card_licencia = ctk.CTkFrame(container, fg_color=self.COLOR_CARD, corner_radius=10)
        card_licencia.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            card_licencia,
            text="🔐 Estado de Licencia",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.COLOR_PRIMARY,
        ).pack(pady=(18, 10))

        lic_info = ctk.CTkFrame(card_licencia, fg_color="transparent")
        lic_info.pack(fill="x", padx=20, pady=(0, 12))

        self.lbl_licencia_estado = ctk.CTkLabel(
            lic_info,
            text="Estado: consultando...",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.COLOR_TEXT,
            anchor="w",
        )
        self.lbl_licencia_estado.pack(fill="x", pady=(0, 4))

        self.lbl_licencia_plan = ctk.CTkLabel(
            lic_info,
            text="Plan comercial: --",
            font=ctk.CTkFont(size=12),
            text_color=self.COLOR_TEXT,
            anchor="w",
        )
        self.lbl_licencia_plan.pack(fill="x", pady=2)

        self.lbl_licencia_dias = ctk.CTkLabel(
            lic_info,
            text="Días restantes: --",
            font=ctk.CTkFont(size=12),
            text_color=self.COLOR_TEXT,
            anchor="w",
        )
        self.lbl_licencia_dias.pack(fill="x", pady=2)

        self.lbl_licencia_corte = ctk.CTkLabel(
            lic_info,
            text="Fecha de corte: --",
            font=ctk.CTkFont(size=12),
            text_color=self.COLOR_TEXT,
            anchor="w",
        )
        self.lbl_licencia_corte.pack(fill="x", pady=2)

        self.lbl_licencia_canal = ctk.CTkLabel(
            lic_info,
            text="Canal de venta: --",
            font=ctk.CTkFont(size=12),
            text_color=self.COLOR_TEXT_MUTED,
            anchor="w",
        )
        self.lbl_licencia_canal.pack(fill="x", pady=(2, 0))

        acciones_lic = ctk.CTkFrame(card_licencia, fg_color="transparent")
        acciones_lic.pack(fill="x", padx=20, pady=(0, 18))
        acciones_lic.grid_columnconfigure((0, 1), weight=1)

        self.btn_renovar_licencia = ctk.CTkButton(
            acciones_lic,
            text="🔄 Renovar ahora",
            command=self._renovar_licencia_ahora,
            height=38,
            fg_color=self.COLOR_WARNING,
        )
        self.btn_renovar_licencia.grid(row=0, column=0, padx=(0, 8), sticky="ew")

        ctk.CTkButton(
            acciones_lic,
            text="📋 Copiar ID instalación",
            command=self._copiar_id_licencia,
            height=38,
            fg_color="transparent",
            border_width=1,
            border_color=self.COLOR_TEXT_MUTED,
            text_color=self.COLOR_TEXT,
        ).grid(row=0, column=1, padx=(8, 0), sticky="ew")

        self._refrescar_estado_licencia_ui()

        # Card de estadísticas
        card_stats = ctk.CTkFrame(container, fg_color=self.COLOR_CARD, corner_radius=10)
        card_stats.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            card_stats,
            text="📊 Estadísticas del Gimnasio",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.COLOR_PRIMARY,
        ).pack(pady=(20, 15))

        stats_grid = ctk.CTkFrame(card_stats, fg_color="transparent")
        stats_grid.pack(fill="x", padx=20, pady=(0, 20))
        stats_grid.grid_columnconfigure((0, 1), weight=1)

        self._crear_stat_box(
            stats_grid, "👥 Total Clientes",
            str(stats.get("total_clientes", 0)), row=0, col=0,
        )
        self._crear_stat_box(
            stats_grid, "📈 Clientes Nuevos (30d)",
            str(stats.get("clientes_nuevos", 0)), row=0, col=1,
        )
        self._crear_stat_box(
            stats_grid, "🍽️ Planes Generados (30d)",
            str(stats.get("planes_periodo", 0)), row=1, col=0,
        )
        self._crear_stat_box(
            stats_grid, "⚡ Promedio Kcal",
            f"{stats.get('promedio_kcal', 0):.0f}", row=1, col=1,
        )

        # Card de backups
        card_backup = ctk.CTkFrame(container, fg_color=self.COLOR_CARD, corner_radius=10)
        card_backup.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            card_backup,
            text="💾 Gestión de Backups",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.COLOR_PRIMARY,
        ).pack(pady=(20, 15))

        ctk.CTkLabel(
            card_backup,
            text=(
                "Los backups se crean automáticamente cada 7 días.\n"
                "Puedes crear un backup manual en cualquier momento."
            ),
            font=ctk.CTkFont(size=11),
            text_color=self.COLOR_TEXT_MUTED,
            wraplength=600,
        ).pack(pady=(0, 15))

        btn_backup_frame = ctk.CTkFrame(card_backup, fg_color="transparent")
        btn_backup_frame.pack(fill="x", padx=20, pady=(0, 20))
        btn_backup_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            btn_backup_frame,
            text="📦 Crear Backup",
            command=self._crear_backup,
            height=40,
            fg_color=self.COLOR_SUCCESS,
        ).grid(row=0, column=0, padx=(0, 10), sticky="ew")

        ctk.CTkButton(
            btn_backup_frame,
            text="🗑️ Limpiar Antiguos",
            command=self._limpiar_backups,
            height=40,
            fg_color=self.COLOR_WARNING,
        ).grid(row=0, column=1, padx=(10, 0), sticky="ew")

        # Botón de reportes completos
        ctk.CTkButton(
            container,
            text="📊 Ver Reportes Completos",
            command=lambda: VentanaReportes(self),
            height=50,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=self.COLOR_PRIMARY,
        ).pack(pady=20, fill="x", padx=20)

    # ========== Pestaña Búsqueda ==========

    def _crear_tab_busqueda(self, parent):
        """Crea la pestaña de búsqueda de clientes."""
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        search_frame = ctk.CTkFrame(container, fg_color=self.COLOR_CARD, corner_radius=10)
        search_frame.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(
            search_frame,
            text="🔍 Buscar Cliente",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.COLOR_PRIMARY,
        ).pack(pady=(15, 10))

        entry_frame = ctk.CTkFrame(search_frame, fg_color="transparent")
        entry_frame.pack(fill="x", padx=20, pady=(0, 15))

        self.entry_busqueda = ctk.CTkEntry(
            entry_frame,
            placeholder_text="Nombre, teléfono o ID del cliente...",
            height=40,
            font=ctk.CTkFont(size=13),
        )
        self.entry_busqueda.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkButton(
            entry_frame,
            text="Buscar",
            command=self._buscar_clientes,
            width=100,
            height=40,
            fg_color=self.COLOR_PRIMARY,
        ).pack(side="left")

        # Área de resultados
        self.resultados_frame = ctk.CTkScrollableFrame(
            container, fg_color=self.COLOR_BG, corner_radius=10
        )
        self.resultados_frame.pack(fill="both", expand=True)

    # ========== Pestaña Alimentos ==========

    def _crear_tab_alimentos(self, parent):
        """Crea la pestaña de administración de alimentos."""
        self._alimento_actual = None

        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        header = ctk.CTkFrame(container, fg_color=self.COLOR_CARD, corner_radius=10)
        header.pack(fill="x", pady=(0, 15))

        header_inner = ctk.CTkFrame(header, fg_color="transparent")
        header_inner.pack(fill="x", padx=15, pady=12)
        header_inner.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header_inner,
            text="🥗 Catálogo de Alimentos",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=self.COLOR_PRIMARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            header_inner,
            text="Edita macros, límites, equivalencias y categorías desde SQLite.",
            font=ctk.CTkFont(size=11),
            text_color=self.COLOR_TEXT_MUTED,
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        ctk.CTkButton(
            header_inner,
            text="Preferencias del Gym",
            command=self._abrir_preferencias_alimentos,
            height=34,
            fg_color=self.COLOR_PRIMARY,
        ).grid(row=0, column=1, rowspan=2, padx=(10, 0), sticky="e")

        buscador = ctk.CTkFrame(container, fg_color=self.COLOR_CARD, corner_radius=10)
        buscador.pack(fill="x", pady=(0, 15))

        buscador_inner = ctk.CTkFrame(buscador, fg_color="transparent")
        buscador_inner.pack(fill="x", padx=15, pady=12)

        self.entry_alimentos_buscar = ctk.CTkEntry(
            buscador_inner,
            placeholder_text="Buscar alimento...",
            height=38,
            font=ctk.CTkFont(size=12),
        )
        self.entry_alimentos_buscar.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_alimentos_buscar.bind("<KeyRelease>", self._filtrar_alimentos)

        ctk.CTkButton(
            buscador_inner,
            text="Nuevo",
            command=self._nuevo_alimento,
            height=38,
            width=110,
            fg_color=self.COLOR_SUCCESS,
        ).pack(side="left")

        cuerpo = ctk.CTkFrame(container, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True)
        cuerpo.grid_columnconfigure(0, weight=1, minsize=240)
        cuerpo.grid_columnconfigure(1, weight=2, minsize=360)
        cuerpo.grid_rowconfigure(0, weight=1)

        self.alimentos_lista = ctk.CTkScrollableFrame(
            cuerpo, fg_color=self.COLOR_CARD, corner_radius=10
        )
        self.alimentos_lista.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        self.alimentos_form = ctk.CTkFrame(cuerpo, fg_color=self.COLOR_CARD, corner_radius=10)
        self.alimentos_form.grid(row=0, column=1, sticky="nsew")

        self._crear_formulario_alimentos(self.alimentos_form)
        self._cargar_lista_alimentos()

    def _crear_formulario_alimentos(self, parent):
        """Formulario para editar alimento."""
        form = ctk.CTkFrame(parent, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=20, pady=20)
        form.grid_columnconfigure(1, weight=1)

        def add_row(row: int, label: str, widget):
            ctk.CTkLabel(
                form,
                text=label,
                font=ctk.CTkFont(size=12),
                text_color=self.COLOR_TEXT,
                anchor="w",
            ).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 10))
            widget.grid(row=row, column=1, sticky="ew", pady=6)

        self.entry_alimento_nombre = ctk.CTkEntry(form, height=32)
        add_row(0, "Nombre", self.entry_alimento_nombre)

        categorias_db = alimentos_sqlite.listar_categorias()
        categorias_default = ["proteina", "carbs", "grasa", "verdura", "fruta"]
        self._categorias_disponibles = sorted(set(categorias_db) | set(categorias_default))

        self.var_categoria = ctk.StringVar(value=self._categorias_disponibles[0])
        self.menu_categoria = ctk.CTkOptionMenu(
            form,
            values=self._categorias_disponibles,
            variable=self.var_categoria,
            fg_color=self.COLOR_BG,
            button_color=self.COLOR_PRIMARY,
            button_hover_color=self.COLOR_PRIMARY,
        )
        add_row(1, "Categoría", self.menu_categoria)

        self.entry_proteina = ctk.CTkEntry(form, height=32)
        add_row(2, "Proteína (g/100)", self.entry_proteina)

        self.entry_carbs = ctk.CTkEntry(form, height=32)
        add_row(3, "Carbs (g/100)", self.entry_carbs)

        self.entry_grasa = ctk.CTkEntry(form, height=32)
        add_row(4, "Grasa (g/100)", self.entry_grasa)

        self.entry_kcal = ctk.CTkEntry(form, height=32)
        add_row(5, "Kcal (100g)", self.entry_kcal)

        self.entry_meal_idx = ctk.CTkEntry(form, height=32)
        self.entry_meal_idx.insert(0, "0,1,2,3")
        add_row(6, "Meal IDX", self.entry_meal_idx)

        ctk.CTkLabel(
            form,
            text="Formato: 0,1,2,3 (desayuno, almuerzo, comida, cena)",
            font=ctk.CTkFont(size=10),
            text_color=self.COLOR_TEXT_MUTED,
            anchor="w",
        ).grid(row=7, column=1, sticky="w", pady=(0, 8))

        self.entry_limite = ctk.CTkEntry(form, height=32)
        add_row(8, "Límite (g)", self.entry_limite)

        self.entry_equivalencia = ctk.CTkEntry(form, height=32)
        add_row(9, "Equivalencia", self.entry_equivalencia)

        acciones = ctk.CTkFrame(form, fg_color="transparent")
        acciones.grid(row=10, column=0, columnspan=2, sticky="ew", pady=(18, 0))
        acciones.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(
            acciones,
            text="Guardar",
            command=self._guardar_alimento,
            height=36,
            fg_color=self.COLOR_PRIMARY,
        ).grid(row=0, column=0, padx=(0, 8), sticky="ew")

        ctk.CTkButton(
            acciones,
            text="Limpiar",
            command=self._nuevo_alimento,
            height=36,
            fg_color=self.COLOR_CARD,
            border_width=1,
            border_color=self.COLOR_TEXT_MUTED,
        ).grid(row=0, column=1, padx=8, sticky="ew")

        ctk.CTkButton(
            acciones,
            text="Eliminar",
            command=self._eliminar_alimento,
            height=36,
            fg_color=self.COLOR_ERROR,
            hover_color="#D32F2F",
        ).grid(row=0, column=2, padx=(8, 0), sticky="ew")

        self.label_estado_alimentos = ctk.CTkLabel(
            form,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=self.COLOR_TEXT_MUTED,
            anchor="w",
        )
        self.label_estado_alimentos.grid(row=11, column=0, columnspan=2, sticky="w", pady=(10, 0))

    def _cargar_lista_alimentos(self, filtro: str | None = None):
        """Carga la lista de alimentos con filtro opcional."""
        for widget in self.alimentos_lista.winfo_children():
            widget.destroy()

        alimentos = alimentos_sqlite.listar_alimentos(filtro=filtro)
        if not alimentos:
            ctk.CTkLabel(
                self.alimentos_lista,
                text="Sin resultados",
                font=ctk.CTkFont(size=12),
                text_color=self.COLOR_TEXT_MUTED,
            ).pack(pady=20)
            return

        for nombre in alimentos:
            ctk.CTkButton(
                self.alimentos_lista,
                text=nombre.replace("_", " ").title(),
                command=lambda n=nombre: self._seleccionar_alimento(n),
                fg_color=self.COLOR_BG,
                hover_color=self.COLOR_PRIMARY,
                text_color=self.COLOR_TEXT,
                height=34,
            ).pack(fill="x", padx=10, pady=6)

    def _filtrar_alimentos(self, event=None):
        termino = self.entry_alimentos_buscar.get().strip()
        self._cargar_lista_alimentos(filtro=termino if termino else None)

    def _seleccionar_alimento(self, nombre: str):
        detalle = alimentos_sqlite.obtener_detalle(nombre)
        if not detalle:
            return

        self._alimento_actual = nombre
        self.entry_alimento_nombre.configure(state="normal")
        self.entry_alimento_nombre.delete(0, "end")
        self.entry_alimento_nombre.insert(0, detalle.get("nombre", ""))
        self.entry_alimento_nombre.configure(state="disabled")

        categoria = detalle.get("categoria")
        if categoria and categoria in self._categorias_disponibles:
            self.var_categoria.set(categoria)
        elif self._categorias_disponibles:
            self.var_categoria.set(self._categorias_disponibles[0])

        self._set_entry(self.entry_proteina, detalle.get("proteina"))
        self._set_entry(self.entry_carbs, detalle.get("carbs"))
        self._set_entry(self.entry_grasa, detalle.get("grasa"))
        self._set_entry(self.entry_kcal, detalle.get("kcal"))
        self._set_entry(self.entry_limite, detalle.get("limite"))
        self._set_entry(self.entry_equivalencia, detalle.get("equivalencia"), raw=True)

        meal_idx = detalle.get("meal_idx") or []
        self.entry_meal_idx.delete(0, "end")
        self.entry_meal_idx.insert(0, ",".join(str(i) for i in meal_idx))

        self.label_estado_alimentos.configure(text=f"Editando: {nombre}")

    def _nuevo_alimento(self):
        self._alimento_actual = None
        self.entry_alimento_nombre.configure(state="normal")
        self._limpiar_entry(self.entry_alimento_nombre)
        self._limpiar_entry(self.entry_proteina)
        self._limpiar_entry(self.entry_carbs)
        self._limpiar_entry(self.entry_grasa)
        self._limpiar_entry(self.entry_kcal)
        self._limpiar_entry(self.entry_limite)
        self._limpiar_entry(self.entry_equivalencia)
        self.entry_meal_idx.delete(0, "end")
        self.entry_meal_idx.insert(0, "0,1,2,3")
        if self._categorias_disponibles:
            self.var_categoria.set(self._categorias_disponibles[0])
        self.label_estado_alimentos.configure(text="Nuevo alimento")

    def _guardar_alimento(self):
        nombre = self.entry_alimento_nombre.get().strip()
        if not nombre:
            messagebox.showwarning("Aviso", "El nombre del alimento es obligatorio")
            return

        try:
            detalle = {
                "nombre": nombre,
                "categoria": self.var_categoria.get(),
                "proteina": self._parse_float(self.entry_proteina.get(), "Proteína"),
                "carbs": self._parse_float(self.entry_carbs.get(), "Carbs"),
                "grasa": self._parse_float(self.entry_grasa.get(), "Grasa"),
                "kcal": self._parse_float(self.entry_kcal.get(), "Kcal"),
                "meal_idx": self._parse_meal_idx(self.entry_meal_idx.get()),
                "limite": self._parse_optional_float(self.entry_limite.get()),
                "equivalencia": self.entry_equivalencia.get().strip() or None,
            }
        except ValueError as exc:
            messagebox.showerror("Error", str(exc))
            return

        # Validación de reglas de negocio
        valido, errores = validar_alimento(detalle)
        if not valido:
            messagebox.showerror(
                "Validación",
                "Corrige los siguientes errores:\n\n" + "\n".join(f"• {e}" for e in errores),
            )
            return

        try:
            alimentos_sqlite.guardar_alimento(detalle)
            recargar_desde_db()
            catalogo_alimentos.refrescar_catalogo()
            self._cargar_lista_alimentos(self.entry_alimentos_buscar.get().strip() or None)
            self.label_estado_alimentos.configure(text=f"Guardado: {nombre}")
            registrar_evento("alimentos", "alimento_guardado", {"nombre": nombre})
            messagebox.showinfo("Éxito", "Alimento guardado correctamente.")
        except Exception as exc:
            logger.error("[ADMIN] Error guardando alimento: %s", exc, exc_info=True)
            messagebox.showerror("Error", f"No se pudo guardar el alimento:\n{exc}")

    def _eliminar_alimento(self):
        if not self._alimento_actual:
            messagebox.showwarning("Aviso", "Selecciona un alimento para eliminar")
            return

        confirm = messagebox.askyesno(
            "Confirmar",
            f"¿Deseas eliminar '{self._alimento_actual}' del catálogo?\n\n"
            "Esto no eliminará planes ya generados.",
        )
        if not confirm:
            return

        try:
            alimentos_sqlite.eliminar_alimento(self._alimento_actual)
            recargar_desde_db()
            catalogo_alimentos.refrescar_catalogo()
            self._cargar_lista_alimentos(self.entry_alimentos_buscar.get().strip() or None)
            registrar_evento("alimentos", "alimento_eliminado", {"nombre": self._alimento_actual})
            self._nuevo_alimento()
            messagebox.showinfo("Eliminado", "Alimento eliminado correctamente.")
        except Exception as exc:
            logger.error("[ADMIN] Error eliminando alimento: %s", exc, exc_info=True)
            messagebox.showerror("Error", f"No se pudo eliminar el alimento:\n{exc}")

    @staticmethod
    def _limpiar_entry(entry: ctk.CTkEntry) -> None:
        entry.delete(0, "end")

    @staticmethod
    def _set_entry(entry: ctk.CTkEntry, valor, raw: bool = False) -> None:
        entry.delete(0, "end")
        if valor is None:
            return
        if raw:
            entry.insert(0, str(valor))
        else:
            entry.insert(0, f"{valor}")

    @staticmethod
    def _parse_float(valor: str, label: str) -> float:
        texto = valor.strip()
        if texto == "":
            raise ValueError(f"{label} es obligatorio.")
        try:
            return float(texto)
        except ValueError:
            raise ValueError(f"{label} debe ser numérico.")

    @staticmethod
    def _parse_optional_float(valor: str) -> float | None:
        texto = valor.strip()
        if texto == "":
            return None
        try:
            return float(texto)
        except ValueError:
            raise ValueError("El límite debe ser numérico o vacío.")

    @staticmethod
    def _parse_meal_idx(valor: str) -> list[int]:
        texto = valor.strip()
        if texto == "":
            return []
        partes = [p.strip() for p in texto.replace(";", ",").split(",") if p.strip()]
        resultado = []
        for p in partes:
            if not p.isdigit():
                raise ValueError("Meal IDX debe ser una lista de enteros separados por coma.")
            resultado.append(int(p))
        return resultado

    # ========== Preferencias de alimentos (Gym) ==========

    def _abrir_preferencias_alimentos(self):
        """Modal para definir alimentos no disponibles del gym."""
        self._pref_vars = {}
        self._pref_excluidos = set(branding.get("alimentos.excluidos", []) or [])

        ventana = ctk.CTkToplevel(self)
        ventana.title("Preferencias de Alimentos del Gym")
        ventana.geometry("520x620")
        ventana.resizable(True, True)
        ventana.configure(fg_color=self.COLOR_BG)

        activar_modal_seguro(ventana, self)

        header = ctk.CTkFrame(ventana, fg_color=self.COLOR_CARD, corner_radius=10)
        header.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            header,
            text="✅ Alimentos no disponibles",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=self.COLOR_PRIMARY,
        ).pack(pady=(12, 4))

        ctk.CTkLabel(
            header,
            text="Marca los alimentos que tu gym NO quiere sugerir.",
            font=ctk.CTkFont(size=11),
            text_color=self.COLOR_TEXT_MUTED,
        ).pack(pady=(0, 12))

        buscador = ctk.CTkFrame(ventana, fg_color=self.COLOR_CARD, corner_radius=10)
        buscador.pack(fill="x", padx=20, pady=(0, 10))

        buscador_inner = ctk.CTkFrame(buscador, fg_color="transparent")
        buscador_inner.pack(fill="x", padx=12, pady=10)

        self.entry_pref_buscar = ctk.CTkEntry(
            buscador_inner,
            placeholder_text="Buscar alimento...",
            height=34,
            font=ctk.CTkFont(size=12),
        )
        self.entry_pref_buscar.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_pref_buscar.bind("<KeyRelease>", lambda e: self._refrescar_preferencias_lista())

        ctk.CTkButton(
            buscador_inner,
            text="Limpiar Exclusiones",
            command=self._limpiar_exclusiones,
            height=34,
            fg_color=self.COLOR_WARNING,
        ).pack(side="left")

        self.pref_lista = ctk.CTkScrollableFrame(
            ventana, fg_color=self.COLOR_CARD, corner_radius=10
        )
        self.pref_lista.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        acciones = ctk.CTkFrame(ventana, fg_color="transparent")
        acciones.pack(fill="x", padx=20, pady=(0, 20))
        acciones.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            acciones,
            text="Guardar Preferencias",
            command=lambda: self._guardar_preferencias_alimentos(ventana),
            height=38,
            fg_color=self.COLOR_SUCCESS,
        ).grid(row=0, column=0, padx=(0, 10), sticky="ew")

        ctk.CTkButton(
            acciones,
            text="Cerrar",
            command=ventana.destroy,
            height=38,
            fg_color=self.COLOR_CARD,
            border_width=1,
            border_color=self.COLOR_TEXT_MUTED,
        ).grid(row=0, column=1, padx=(10, 0), sticky="ew")

        self._refrescar_preferencias_lista()

    def _refrescar_preferencias_lista(self):
        """Renderiza la lista de alimentos para exclusión."""
        for widget in self.pref_lista.winfo_children():
            widget.destroy()

        filtro = self.entry_pref_buscar.get().strip() if hasattr(self, "entry_pref_buscar") else ""
        alimentos = alimentos_sqlite.listar_alimentos(filtro=filtro or None)

        if not alimentos:
            ctk.CTkLabel(
                self.pref_lista,
                text="Sin resultados",
                font=ctk.CTkFont(size=12),
                text_color=self.COLOR_TEXT_MUTED,
            ).pack(pady=20)
            return

        for nombre in alimentos:
            var = self._pref_vars.get(nombre)
            if var is None:
                var = ctk.BooleanVar(value=nombre in self._pref_excluidos)
                self._pref_vars[nombre] = var

            ctk.CTkCheckBox(
                self.pref_lista,
                text=nombre.replace("_", " ").title(),
                variable=var,
                onvalue=True,
                offvalue=False,
                text_color=self.COLOR_TEXT,
                fg_color=self.COLOR_PRIMARY,
                hover_color=self.COLOR_PRIMARY,
            ).pack(anchor="w", padx=12, pady=6)

    def _limpiar_exclusiones(self):
        if not hasattr(self, "_pref_vars"):
            return
        for var in self._pref_vars.values():
            var.set(False)
        self._pref_excluidos = set()
        self._refrescar_preferencias_lista()

    def _guardar_preferencias_alimentos(self, ventana):
        try:
            excluidos = [nombre for nombre, var in self._pref_vars.items() if var.get()]
            branding.set("alimentos.excluidos", sorted(excluidos))
            recargar_desde_db()
            catalogo_alimentos.refrescar_catalogo()
            self._cargar_lista_alimentos(self.entry_alimentos_buscar.get().strip() or None)
            messagebox.showinfo(
                "Preferencias guardadas",
                "Se guardaron las exclusiones del gym.",
                parent=ventana,
            )
        except Exception as exc:
            logger.error("[ADMIN] Error guardando preferencias: %s", exc, exc_info=True)
            messagebox.showerror("Error", f"No se pudieron guardar las preferencias:\n{exc}", parent=ventana)

    # ========== Métodos auxiliares ==========

    def _crear_seccion_admin(self, parent, titulo: str):
        """Crea un encabezado de sección."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=(15, 10))

        ctk.CTkLabel(
            frame,
            text=titulo,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.COLOR_PRIMARY,
            anchor="w",
        ).pack(side="left")

        sep = ctk.CTkFrame(frame, fg_color=self.COLOR_PRIMARY, height=2)
        sep.pack(side="left", fill="x", expand=True, padx=(15, 0))

    def _crear_campo_admin(self, parent, label: str, valor_default: str) -> ctk.CTkEntry:
        """Crea un campo de entrada con label."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=5)

        ctk.CTkLabel(
            frame,
            text=label,
            font=ctk.CTkFont(size=12),
            text_color=self.COLOR_TEXT,
            anchor="w",
            width=150,
        ).pack(side="left", padx=(0, 10))

        entry = ctk.CTkEntry(frame, height=36, font=ctk.CTkFont(size=12))
        entry.pack(side="left", fill="x", expand=True)
        entry.insert(0, valor_default or "")

        return entry

    def _crear_info_label(self, parent, label: str, valor: str):
        """Crea una fila de información."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=15, pady=5)

        ctk.CTkLabel(
            frame,
            text=label,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=self.COLOR_TEXT,
            anchor="w",
            width=180,
        ).pack(side="left")

        ctk.CTkLabel(
            frame,
            text=valor,
            font=ctk.CTkFont(size=11),
            text_color=self.COLOR_TEXT_MUTED,
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

    def _crear_stat_box(self, parent, label: str, valor: str, row: int, col: int):
        """Crea una caja de estadística."""
        box = ctk.CTkFrame(parent, fg_color=self.COLOR_BG, corner_radius=8)
        box.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(
            box,
            text=valor,
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=self.COLOR_PRIMARY,
        ).pack(pady=(15, 5))

        ctk.CTkLabel(
            box,
            text=label,
            font=ctk.CTkFont(size=11),
            text_color=self.COLOR_TEXT_MUTED,
        ).pack(pady=(0, 15))

    # ========== Handlers ==========

    def _set_logo_pdf_path_entry(self, valor: str) -> None:
        self.entry_logo_pdf_path.configure(state="normal")
        self.entry_logo_pdf_path.delete(0, "end")
        self.entry_logo_pdf_path.insert(0, valor)
        self.entry_logo_pdf_path.configure(state="readonly")

    def _aplicar_tema_preconfigurado(self, tema: str | None = None, mostrar_feedback: bool = False):
        tema = (tema or self.var_tema_visual.get() or "").strip()
        data = self._temas_branding.get(tema)
        if not data:
            if mostrar_feedback:
                messagebox.showwarning(
                    "Tema no disponible",
                    "No se encontró el tema seleccionado.",
                    parent=self,
                )
            return

        self.var_tema_visual.set(tema)
        if not hasattr(self, "entry_color_primario"):
            return

        self.entry_color_primario.delete(0, "end")
        self.entry_color_primario.insert(0, data["primario"])
        self.entry_color_secundario.delete(0, "end")
        self.entry_color_secundario.insert(0, data["secundario"])
        self.entry_color_pdf.delete(0, "end")
        self.entry_color_pdf.insert(0, data.get("pdf_color", data["primario"]))

        self.lbl_tema_info.configure(
            text=(
                f"Tema activo: {tema}. "
                f"Primario {data['primario']} | Secundario {data['secundario']}"
            )
        )
        self._aplicar_preview_ui(
            tema=tema,
            primario=data["primario"],
            primario_hover=data.get("primario_hover") or self._aclarar_hex(data["primario"], factor=0.16),
            secundario=data["secundario"],
            secundario_hover=data.get("secundario_hover") or self._aclarar_hex(data["secundario"], factor=0.16),
        )
        if mostrar_feedback:
            messagebox.showinfo(
                "Tema aplicado",
                "Tema aplicado a la UI actual.\nPulsa 'Guardar Configuración' para persistirlo.",
                parent=self,
            )

    def _aplicar_preview_ui(
        self,
        *,
        tema: str,
        primario: str,
        primario_hover: str,
        secundario: str,
        secundario_hover: str,
    ) -> None:
        if not hasattr(self.parent_app, "aplicar_branding_preview"):
            return
        nombre_corto = self.entry_nombre_corto.get().strip() if hasattr(self, "entry_nombre_corto") else None
        nombre_gym = self.entry_nombre_gym.get().strip() if hasattr(self, "entry_nombre_gym") else None
        tagline = self.entry_tagline.get().strip() if hasattr(self, "entry_tagline") else None
        self.parent_app.aplicar_branding_preview(
            primario=primario,
            primario_hover=primario_hover,
            secundario=secundario,
            secundario_hover=secundario_hover,
            nombre_corto=nombre_corto,
            nombre_gym=nombre_gym,
            tagline=tagline,
            tema=tema,
        )

    def _seleccionar_logo_pdf(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar logo para PDF",
            filetypes=[
                ("Imágenes", "*.png *.jpg *.jpeg *.webp"),
                ("Todos los archivos", "*.*"),
            ],
            parent=self,
        )
        if not ruta:
            return
        try:
            ruta_local = self._copiar_logo_pdf_a_config(ruta)
            self._set_logo_pdf_path_entry(ruta_local)
            messagebox.showinfo(
                "Logo actualizado",
                "Logo PDF cargado correctamente.\nGuarda la configuración para aplicarlo.",
                parent=self,
            )
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo cargar el logo:\n{exc}", parent=self)

    def _restaurar_logo_pdf_default(self):
        self._set_logo_pdf_path_entry("assets/logo.png")

    @staticmethod
    def _copiar_logo_pdf_a_config(ruta_origen: str) -> str:
        origen = Path(ruta_origen).expanduser()
        if not origen.exists():
            raise FileNotFoundError("El archivo seleccionado no existe.")

        ext = origen.suffix.lower()
        if ext not in {".png", ".jpg", ".jpeg", ".webp"}:
            raise ValueError("Formato no soportado. Usa PNG, JPG, JPEG o WEBP.")

        destino_dir = Path(CARPETA_CONFIG) / "logos"
        destino_dir.mkdir(parents=True, exist_ok=True)

        for previo in destino_dir.glob("logo_pdf.*"):
            try:
                previo.unlink()
            except Exception:
                pass

        destino = destino_dir / f"logo_pdf{ext}"
        shutil.copy2(origen, destino)
        return str(destino)

    @staticmethod
    def _es_hex_color(valor: str) -> bool:
        if not isinstance(valor, str):
            return False
        valor = valor.strip()
        if len(valor) != 7 or not valor.startswith("#"):
            return False
        try:
            int(valor[1:], 16)
            return True
        except ValueError:
            return False

    @staticmethod
    def _aclarar_hex(hex_color: str, factor: float = 0.15) -> str:
        hex_color = hex_color.strip().lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)

        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return f"#{r:02X}{g:02X}{b:02X}"

    def _guardar_branding(self):
        """Guarda la configuración de branding."""
        try:
            color_primario = self.entry_color_primario.get().strip()
            color_secundario = self.entry_color_secundario.get().strip()
            color_pdf = self.entry_color_pdf.get().strip() or color_primario
            if not self._es_hex_color(color_primario):
                raise ValueError("Color primario inválido. Usa formato #RRGGBB.")
            if not self._es_hex_color(color_secundario):
                raise ValueError("Color secundario inválido. Usa formato #RRGGBB.")
            if not self._es_hex_color(color_pdf):
                raise ValueError("Color de encabezado PDF inválido. Usa formato #RRGGBB.")

            cfg = self.branding.config
            cfg["nombre_gym"] = self.entry_nombre_gym.get().strip()
            cfg["nombre_corto"] = self.entry_nombre_corto.get().strip()
            cfg["tagline"] = self.entry_tagline.get().strip()
            cfg.setdefault("contacto", {})
            cfg["contacto"]["telefono"] = self.entry_telefono.get().strip()
            cfg["contacto"]["email"] = self.entry_email.get().strip()
            cfg["contacto"]["direccion"] = self.entry_direccion.get().strip()
            cfg["contacto"]["whatsapp"] = self.entry_whatsapp.get().strip()

            cfg.setdefault("colores", {})
            cfg["colores"]["primario"] = color_primario
            cfg["colores"]["secundario"] = color_secundario
            cfg["colores"]["primario_hover"] = self._aclarar_hex(color_primario, factor=0.16)
            cfg["colores"]["secundario_hover"] = self._aclarar_hex(color_secundario, factor=0.16)

            cfg.setdefault("pdf", {})
            cfg["pdf"]["color_encabezado"] = color_pdf
            cfg["pdf"]["logo_path"] = self.entry_logo_pdf_path.get().strip() or "assets/logo.png"
            cfg["tema_visual"] = self.var_tema_visual.get().strip() or "Metodo Base Clasico"

            if not self.branding.guardar():
                raise RuntimeError("No se pudo guardar branding.json")
            self.branding.recargar()

            self._aplicar_preview_ui(
                tema=cfg["tema_visual"],
                primario=cfg["colores"]["primario"],
                primario_hover=cfg["colores"]["primario_hover"],
                secundario=cfg["colores"]["secundario"],
                secundario_hover=cfg["colores"]["secundario_hover"],
            )

            messagebox.showinfo(
                "Éxito",
                "Configuración guardada exitosamente.\n\n"
                "Cambios aplicados en esta sesión.",
            )
            logger.info("[ADMIN] Configuración de branding guardada")

        except Exception as e:
            logger.error("[ADMIN] Error guardando branding: %s", e, exc_info=True)
            messagebox.showerror("Error", f"No se pudo guardar la configuración:\n{e}")

    def _refrescar_estado_licencia_ui(self):
        estado = self.gestor_licencias.obtener_estado_licencia()
        mensaje = estado.get("mensaje", "Sin información")
        dias_restantes = int(estado.get("dias_restantes", 0) or 0)
        plan_label = estado.get("plan_label", "Plan personalizado")
        plan_key = estado.get("plan_comercial", "")
        fecha_corte = estado.get("fecha_corte", "") or "N/D"
        canal = (estado.get("canal_venta", "") or "").strip() or "No especificado"
        renovar = bool(estado.get("renovar_ahora", True))
        activa = bool(estado.get("activa", False))

        color_estado = self.COLOR_SUCCESS if activa else self.COLOR_ERROR
        if activa and renovar:
            color_estado = self.COLOR_WARNING

        self.lbl_licencia_estado.configure(text=f"Estado: {mensaje}", text_color=color_estado)
        if plan_key:
            self.lbl_licencia_plan.configure(
                text=f"Plan comercial: {plan_label} ({plan_key})"
            )
        else:
            self.lbl_licencia_plan.configure(text=f"Plan comercial: {plan_label}")
        self.lbl_licencia_dias.configure(text=f"Días restantes: {dias_restantes}")
        self.lbl_licencia_corte.configure(text=f"Fecha de corte: {fecha_corte}")
        self.lbl_licencia_canal.configure(text=f"Canal de venta: {canal}")

        if renovar:
            self.btn_renovar_licencia.configure(text="⚠️ Renovar ahora", fg_color=self.COLOR_WARNING)
        else:
            self.btn_renovar_licencia.configure(text="✅ Licencia vigente", fg_color=self.COLOR_SUCCESS)

    def _copiar_id_licencia(self):
        id_instalacion = self.gestor_licencias.obtener_id_instalacion()
        self.clipboard_clear()
        self.clipboard_append(id_instalacion)
        messagebox.showinfo(
            "ID copiado",
            "ID de instalación copiado al portapapeles.",
            parent=self,
        )

    def _renovar_licencia_ahora(self):
        from gui.ventana_licencia import VentanaActivacionLicencia

        nombre_gym = self.branding.get("nombre_gym", "").strip() or "MetodoBase"
        ventana = VentanaActivacionLicencia(self, self.gestor_licencias, nombre_gym)
        self.wait_window(ventana)
        self._refrescar_estado_licencia_ui()
        if getattr(ventana, "activada", False):
            messagebox.showinfo(
                "Licencia actualizada",
                "Licencia activada/renovada correctamente.",
                parent=self,
            )

    def _crear_backup(self):
        """Crea un backup manual de la BD."""
        try:
            ruta_backup = self.gestor_bd.crear_backup()

            if ruta_backup:
                messagebox.showinfo(
                    "Backup Creado",
                    f"Backup creado exitosamente:\n\n{ruta_backup}",
                )
            else:
                messagebox.showerror("Error", "No se pudo crear el backup")

        except Exception as e:
            logger.error("[ADMIN] Error creando backup: %s", e, exc_info=True)
            messagebox.showerror("Error", f"Error creando backup:\n{e}")

    def _limpiar_backups(self):
        """Limpia backups antiguos (>90 días)."""
        respuesta = messagebox.askyesno(
            "Confirmar",
            "¿Deseas eliminar backups con más de 90 días de antigüedad?\n\n"
            "Los backups recientes se mantendrán intactos.",
        )

        if respuesta:
            try:
                eliminados = self.gestor_bd.limpiar_backups_antiguos(90)
                messagebox.showinfo(
                    "Limpieza Completada",
                    f"Se eliminaron {eliminados} backups antiguos.",
                )

            except Exception as e:
                logger.error("[ADMIN] Error limpiando backups: %s", e, exc_info=True)
                messagebox.showerror("Error", f"Error limpiando backups:\n{e}")

    def _buscar_clientes(self):
        """Busca clientes y muestra resultados."""
        termino = self.entry_busqueda.get().strip()

        if not termino:
            messagebox.showwarning("Aviso", "Ingresa un término de búsqueda")
            return

        try:
            # Limpiar resultados anteriores
            for widget in self.resultados_frame.winfo_children():
                widget.destroy()

            resultados = self.gestor_bd.buscar_clientes(termino, limite=50)

            if not resultados:
                ctk.CTkLabel(
                    self.resultados_frame,
                    text="No se encontraron resultados",
                    font=ctk.CTkFont(size=13),
                    text_color=self.COLOR_TEXT_MUTED,
                ).pack(pady=40)
                return

            for cliente in resultados:
                self._crear_card_cliente(self.resultados_frame, cliente)

            logger.info("[ADMIN] Búsqueda '%s': %s resultados", termino, len(resultados))

        except Exception as e:
            logger.error("[ADMIN] Error en búsqueda: %s", e, exc_info=True)
            messagebox.showerror("Error", f"Error buscando clientes:\n{e}")

    def _crear_card_cliente(self, parent, cliente: Dict):
        """Crea una tarjeta con información de un cliente."""
        card = ctk.CTkFrame(parent, fg_color=self.COLOR_CARD, corner_radius=10)
        card.pack(fill="x", pady=10, padx=10)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(15, 10))

        ctk.CTkLabel(
            header,
            text=cliente["nombre"],
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.COLOR_TEXT,
            anchor="w",
        ).pack(side="left")

        ctk.CTkLabel(
            header,
            text=f"{cliente['total_planes']} planes",
            font=ctk.CTkFont(size=11),
            text_color=self.COLOR_PRIMARY,
            anchor="e",
        ).pack(side="right")

        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.pack(fill="x", padx=15, pady=(0, 15))

        info_text = []
        if cliente["telefono"]:
            info_text.append(f"📱 {cliente['telefono']}")
        if cliente["edad"]:
            info_text.append(f"👤 {cliente['edad']} años")
        if cliente["objetivo"]:
            info_text.append(f"🎯 {cliente['objetivo'].title()}")

        ctk.CTkLabel(
            info_frame,
            text=" | ".join(info_text),
            font=ctk.CTkFont(size=11),
            text_color=self.COLOR_TEXT_MUTED,
            anchor="w",
        ).pack()

# -*- coding: utf-8 -*-
"""
Ventana de reportes y estadísticas avanzadas.

Muestra:
- Gráficas de planes generados por mes
- Distribución de objetivos (déficit/superávit/mantenimiento)
- Top clientes más activos
- Exportación a Excel
"""

import customtkinter as ctk
from tkinter import messagebox, filedialog
from datetime import datetime, timedelta
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import pandas as pd
from typing import Dict, List

from src.gestor_bd import GestorBDClientes
from utils.logger import logger
from utils.telemetria import registrar_evento


class VentanaReportes(ctk.CTkToplevel):
    """
    Ventana de reportes estadísticos del gimnasio.

    Pestañas:
    1. Dashboard: KPIs principales y resumen
    2. Gráficas: Visualizaciones con matplotlib
    3. Clientes: Top clientes y listados
    """

    COLOR_BG = "#0D0D0D"
    COLOR_CARD = "#1A1A1A"
    COLOR_PRIMARY = "#9B4FB0"
    COLOR_SECONDARY = "#D4A84B"
    COLOR_TEXT = "#F5F5F5"
    COLOR_TEXT_MUTED = "#B8B8B8"
    COLOR_SUCCESS = "#4CAF50"

    def __init__(self, parent):
        super().__init__(parent)

        self.title("Reportes y Estadísticas - Método Base")
        self.geometry("1000x750")
        self.resizable(True, True)
        self.configure(fg_color=self.COLOR_BG)

        self.gestor_bd = GestorBDClientes()

        self._crear_ui()
        self._cargar_datos()

        logger.info("[REPORTES] Ventana de reportes abierta")

    def _crear_ui(self):
        """Crea la interfaz de reportes."""
        # Header
        header = ctk.CTkFrame(self, fg_color=self.COLOR_CARD, height=80)
        header.pack(fill="x", padx=20, pady=(20, 10))
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="📊 Reportes y Estadísticas",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=self.COLOR_PRIMARY,
        ).pack(pady=10)

        ctk.CTkLabel(
            header,
            text="Análisis de desempeño del gimnasio",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=self.COLOR_TEXT_MUTED,
        ).pack()

        # Selector de período
        periodo_frame = ctk.CTkFrame(self, fg_color=self.COLOR_CARD, height=60)
        periodo_frame.pack(fill="x", padx=20, pady=(0, 10))
        periodo_frame.pack_propagate(False)

        ctk.CTkLabel(
            periodo_frame,
            text="Período:",
            font=ctk.CTkFont(size=12),
            text_color=self.COLOR_TEXT,
        ).pack(side="left", padx=(20, 10))

        self.combo_periodo = ctk.CTkComboBox(
            periodo_frame,
            values=[
                "Últimos 7 días",
                "Últimos 30 días",
                "Últimos 90 días",
                "Último año",
                "Todo el tiempo",
            ],
            command=self._cambiar_periodo,
            width=180,
            height=36,
            button_color=self.COLOR_PRIMARY,
            button_hover_color="#B565C6",
        )
        self.combo_periodo.set("Últimos 30 días")
        self.combo_periodo.pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            periodo_frame,
            text="🔄 Actualizar",
            command=self._cargar_datos,
            width=120,
            height=36,
            fg_color=self.COLOR_SUCCESS,
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            periodo_frame,
            text="📤 Exportar",
            command=self._exportar_reporte,
            width=120,
            height=36,
            fg_color=self.COLOR_SECONDARY,
        ).pack(side="left")

        # Tabview
        self.tabview = ctk.CTkTabview(
            self,
            fg_color=self.COLOR_BG,
            segmented_button_fg_color=self.COLOR_CARD,
            segmented_button_selected_color=self.COLOR_PRIMARY,
        )
        self.tabview.pack(fill="both", expand=True, padx=20, pady=10)

        self.tab_dashboard = self.tabview.add("📈 Dashboard")
        self.tab_graficas = self.tabview.add("📊 Gráficas")
        self.tab_clientes = self.tabview.add("👥 Clientes")

        self._crear_tab_dashboard(self.tab_dashboard)
        self._crear_tab_graficas(self.tab_graficas)
        self._crear_tab_clientes(self.tab_clientes)

    def _crear_tab_dashboard(self, parent):
        """Crea el dashboard con KPIs principales."""
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        self.kpi_container = ctk.CTkFrame(scroll, fg_color="transparent")
        self.kpi_container.pack(fill="x", pady=(0, 20))
        self.kpi_container.grid_columnconfigure((0, 1, 2, 3), weight=1)

    def _crear_tab_graficas(self, parent):
        """Crea pestaña con gráficas matplotlib."""
        self.graficas_container = ctk.CTkFrame(parent, fg_color="transparent")
        self.graficas_container.pack(fill="both", expand=True, padx=20, pady=20)

    def _crear_tab_clientes(self, parent):
        """Crea pestaña de listado de clientes."""
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        self.clientes_container = scroll

    # ========== Carga de datos ==========

    def _cargar_datos(self, _event=None):
        """Carga datos y actualiza todas las vistas."""
        try:
            periodo = self.combo_periodo.get()
            fecha_inicio, fecha_fin = self._calcular_fechas_periodo(periodo)
            self.stats = self.gestor_bd.obtener_estadisticas_gym(fecha_inicio, fecha_fin)

            self._actualizar_dashboard()
            self._actualizar_graficas()
            self._actualizar_clientes()

            logger.info("[REPORTES] Datos cargados para período: %s", periodo)

        except Exception as e:
            logger.error("[REPORTES] Error cargando datos: %s", e, exc_info=True)
            messagebox.showerror("Error", f"No se pudieron cargar los datos:\n{e}")

    def _calcular_fechas_periodo(self, periodo: str) -> tuple:
        """Calcula fechas de inicio y fin según el período seleccionado."""
        fecha_fin = datetime.now()

        dias_map = {
            "Últimos 7 días": 7,
            "Últimos 30 días": 30,
            "Últimos 90 días": 90,
            "Último año": 365,
        }
        dias = dias_map.get(periodo)
        fecha_inicio = fecha_fin - timedelta(days=dias) if dias else datetime(2020, 1, 1)
        return fecha_inicio, fecha_fin

    # ========== Dashboard ==========

    def _actualizar_dashboard(self):
        """Actualiza los KPIs del dashboard."""
        for widget in self.kpi_container.winfo_children():
            widget.destroy()

        self.kpi_container.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # Fila 1: volumen
        self._crear_kpi(0, 0, "👥", "Total Clientes",
                        str(self.stats.get("total_clientes", 0)))
        self._crear_kpi(0, 1, "🆕", "Clientes Nuevos",
                        str(self.stats.get("clientes_nuevos", 0)))
        self._crear_kpi(0, 2, "✅", "Clientes Activos",
                        str(self.stats.get("clientes_activos", 0)))
        self._crear_kpi(0, 3, "🍽️", "Planes Generados",
                        str(self.stats.get("planes_periodo", 0)))

        # Fila 2: objetivos
        objetivos = self.stats.get("objetivos", {})
        self._crear_kpi(1, 0, "📉", "Déficit",
                        str(objetivos.get("deficit", 0)))
        self._crear_kpi(1, 1, "📈", "Superávit",
                        str(objetivos.get("superavit", 0)))
        self._crear_kpi(1, 2, "➡️", "Mantenimiento",
                        str(objetivos.get("mantenimiento", 0)))
        self._crear_kpi(1, 3, "⚡", "Promedio Kcal",
                        f"{self.stats.get('promedio_kcal', 0):.0f}")

        # Fila 3: negocio
        self._crear_kpi(2, 0, "🔄", "Renovaciones",
                        str(self.stats.get("renovaciones", 0)))
        self._crear_kpi(2, 1, "📊", "Tasa Retención",
                        f"{self.stats.get('tasa_retencion', 0):.1f}%")

        total = self.stats.get("total_clientes", 0)
        nuevos = self.stats.get("clientes_nuevos", 0)
        tasa = (nuevos / total * 100) if total > 0 and nuevos > 0 else 0
        self._crear_kpi(2, 2, "🚀", "Tasa Crecimiento", f"{tasa:.1f}%")

        planes_tipo = self.stats.get("planes_por_tipo", {})
        menu_fijo = planes_tipo.get("menu_fijo", 0)
        opciones = planes_tipo.get("con_opciones", 0)
        self._crear_kpi(2, 3, "📋", "Fijo / Opciones",
                        f"{menu_fijo} / {opciones}")

    def _crear_kpi(self, row: int, col: int, icono: str, label: str, valor: str):
        """Crea un widget KPI."""
        card = ctk.CTkFrame(
            self.kpi_container,
            fg_color=self.COLOR_CARD,
            corner_radius=10,
            border_width=1,
            border_color="#2A2A2A",
        )
        card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(card, text=icono, font=ctk.CTkFont(size=32)).pack(pady=(20, 5))
        ctk.CTkLabel(
            card, text=valor,
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=self.COLOR_PRIMARY,
        ).pack(pady=(0, 5))
        ctk.CTkLabel(
            card, text=label,
            font=ctk.CTkFont(size=11),
            text_color=self.COLOR_TEXT_MUTED,
        ).pack(pady=(0, 20))

    # ========== Gráficas ==========

    def _actualizar_graficas(self):
        """Actualiza las gráficas matplotlib."""
        for widget in self.graficas_container.winfo_children():
            widget.destroy()

        plt.style.use("dark_background")
        fig = Figure(figsize=(10, 8), facecolor="#0D0D0D")

        # Gráfica 1: Distribución de objetivos (Pie)
        ax1 = fig.add_subplot(2, 1, 1)
        objetivos = self.stats.get("objetivos", {})

        if objetivos:
            labels = [k.title() for k in objetivos.keys()]
            sizes = list(objetivos.values())
            colors = ["#F44336", "#4CAF50", "#2196F3"][:len(sizes)]
            ax1.pie(sizes, labels=labels, autopct="%1.1f%%",
                    colors=colors, startangle=90)
            ax1.set_title("Distribución de Objetivos",
                          color="#9B4FB0", fontsize=14, fontweight="bold")
        else:
            ax1.text(0.5, 0.5, "Sin datos de objetivos",
                     ha="center", va="center", color="#B8B8B8", fontsize=14)
            ax1.set_title("Distribución de Objetivos",
                          color="#9B4FB0", fontsize=14, fontweight="bold")

        # Gráfica 2: Top 10 clientes (Barras horizontales)
        ax2 = fig.add_subplot(2, 1, 2)
        top_clientes = self.stats.get("top_clientes", [])

        if top_clientes:
            nombres = [c["nombre"][:20] for c in top_clientes[:10]]
            planes = [c["planes"] for c in top_clientes[:10]]
            y_pos = range(len(nombres))
            ax2.barh(y_pos, planes, color="#9B4FB0")
            ax2.set_yticks(y_pos)
            ax2.set_yticklabels(nombres)
            ax2.set_xlabel("Planes Generados", color="#B8B8B8")
            ax2.set_title("Top 10 Clientes Más Activos",
                          color="#9B4FB0", fontsize=14, fontweight="bold")
            ax2.invert_yaxis()
            ax2.grid(axis="x", alpha=0.3)
        else:
            ax2.text(0.5, 0.5, "Sin datos de clientes",
                     ha="center", va="center", color="#B8B8B8", fontsize=14)
            ax2.set_title("Top 10 Clientes Más Activos",
                          color="#9B4FB0", fontsize=14, fontweight="bold")

        fig.tight_layout(pad=3.0)

        canvas = FigureCanvasTkAgg(fig, self.graficas_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    # ========== Clientes ==========

    def _actualizar_clientes(self):
        """Actualiza el listado de top clientes."""
        for widget in self.clientes_container.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            self.clientes_container,
            text="🏆 Top Clientes Más Activos",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.COLOR_PRIMARY,
        ).pack(pady=(0, 20))

        top_clientes = self.stats.get("top_clientes", [])

        if not top_clientes:
            ctk.CTkLabel(
                self.clientes_container,
                text="No hay clientes registrados aún",
                font=ctk.CTkFont(size=13),
                text_color=self.COLOR_TEXT_MUTED,
            ).pack(pady=40)
            return

        for i, cliente in enumerate(top_clientes, 1):
            self._crear_card_cliente_reporte(
                self.clientes_container, i,
                cliente["nombre"], cliente["planes"],
            )

    def _crear_card_cliente_reporte(self, parent, posicion: int,
                                    nombre: str, planes: int):
        """Crea una tarjeta de cliente en el reporte."""
        card = ctk.CTkFrame(parent, fg_color=self.COLOR_CARD, corner_radius=10)
        card.pack(fill="x", pady=8)

        medallas = {1: "🥇", 2: "🥈", 3: "🥉"}
        icono = medallas.get(posicion, f"{posicion}.")

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=20, pady=15)

        ctk.CTkLabel(
            content, text=icono,
            font=ctk.CTkFont(size=20), width=50,
        ).pack(side="left")

        ctk.CTkLabel(
            content, text=nombre,
            font=ctk.CTkFont(size=13),
            text_color=self.COLOR_TEXT, anchor="w",
        ).pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            content, text=f"{planes} planes",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.COLOR_PRIMARY,
        ).pack(side="right")

    # ========== Handlers ==========

    def _cambiar_periodo(self, _evento=None):
        """Handler para cambio de período."""
        self._cargar_datos()

    def _exportar_reporte(self):
        """Exporta el reporte a Excel con 5 hojas completas."""
        try:
            archivo = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel", "*.xlsx"), ("CSV", "*.csv")],
                initialfile=f"reporte_gym_{datetime.now().strftime('%Y%m%d')}",
            )
            if not archivo:
                return

            # ── Datos para hojas existentes ──
            df_resumen = pd.DataFrame([{
                "Total Clientes": self.stats.get("total_clientes", 0),
                "Clientes Nuevos": self.stats.get("clientes_nuevos", 0),
                "Planes Generados": self.stats.get("planes_periodo", 0),
                "Promedio Kcal": self.stats.get("promedio_kcal", 0),
            }])

            top_raw = self.stats.get("top_clientes", [])
            df_top = pd.DataFrame(top_raw)
            if not df_top.empty:
                df_top = df_top.rename(columns={
                    "nombre": "Nombre",
                    "planes": "Total Planes",
                })

            df_objetivos = pd.DataFrame([
                {"Objetivo": k.title(), "Cantidad": v}
                for k, v in self.stats.get("objetivos", {}).items()
            ])

            # ── Hoja: Todos los Clientes ──
            todos_clientes = self.gestor_bd.obtener_todos_clientes(solo_activos=False)
            df_clientes = pd.DataFrame(todos_clientes)
            if not df_clientes.empty:
                columnas_clientes = {
                    "nombre": "Nombre",
                    "telefono": "Teléfono",
                    "email": "Email",
                    "edad": "Edad",
                    "peso_kg": "Peso (kg)",
                    "objetivo": "Objetivo",
                    "nivel_actividad": "Nivel Actividad",
                    "total_planes_generados": "Total Planes",
                    "ultimo_plan": "Último Plan",
                    "activo": "Activo",
                }
                cols_disponibles = [c for c in columnas_clientes if c in df_clientes.columns]
                df_clientes = df_clientes[cols_disponibles].rename(columns=columnas_clientes)
            else:
                df_clientes = pd.DataFrame(columns=[
                    "Nombre", "Teléfono", "Email", "Edad", "Peso (kg)",
                    "Objetivo", "Nivel Actividad", "Total Planes",
                    "Último Plan", "Activo",
                ])

            # ── Hoja: Historial de Planes ──
            periodo = self.combo_periodo.get()
            fecha_inicio, fecha_fin = self._calcular_fechas_periodo(periodo)
            planes_periodo = self.gestor_bd.obtener_planes_periodo(fecha_inicio, fecha_fin)
            df_planes = pd.DataFrame(planes_periodo)
            if not df_planes.empty:
                columnas_planes = {
                    "nombre": "Nombre Cliente",
                    "fecha_generacion": "Fecha Generación",
                    "kcal_objetivo": "Kcal Objetivo",
                    "kcal_real": "Kcal Real",
                    "proteina_g": "Proteína (g)",
                    "carbs_g": "Carbohidratos (g)",
                    "grasa_g": "Grasa (g)",
                    "objetivo": "Objetivo",
                    "peso_en_momento": "Peso en Momento",
                    "grasa_en_momento": "Grasa en Momento",
                    "desviacion_maxima_pct": "Desviación Máx (%)",
                    "ruta_pdf": "Ruta PDF",
                }
                cols_disponibles = [c for c in columnas_planes if c in df_planes.columns]
                df_planes = df_planes[cols_disponibles].rename(columns=columnas_planes)
            else:
                df_planes = pd.DataFrame(columns=[
                    "Nombre Cliente", "Fecha Generación", "Kcal Objetivo",
                    "Kcal Real", "Proteína (g)", "Carbohidratos (g)",
                    "Grasa (g)", "Objetivo", "Peso en Momento",
                    "Grasa en Momento", "Desviación Máx (%)", "Ruta PDF",
                ])

            # ── Escribir Excel ──
            hojas = {
                "Resumen": df_resumen,
                "Top Clientes": df_top,
                "Objetivos": df_objetivos,
                "Todos los Clientes": df_clientes,
                "Historial de Planes": df_planes,
            }

            if archivo.endswith(".xlsx"):
                with pd.ExcelWriter(archivo, engine="xlsxwriter") as writer:
                    for nombre_hoja, df in hojas.items():
                        df.to_excel(writer, sheet_name=nombre_hoja, index=False)
                        worksheet = writer.sheets[nombre_hoja]
                        worksheet.set_column(0, max(len(df.columns) - 1, 0), 18)
            elif archivo.endswith(".csv"):
                df_clientes.to_csv(archivo, index=False, encoding="utf-8-sig")

            messagebox.showinfo("Éxito", f"Reporte exportado exitosamente:\n{archivo}")
            logger.info("[REPORTES] Reporte exportado: %s", archivo)
            registrar_evento("reportes", "reporte_exportado", {"formato": archivo.rsplit('.', 1)[-1]})

        except Exception as e:
            logger.error("[REPORTES] Error exportando: %s", e, exc_info=True)
            messagebox.showerror("Error", f"No se pudo exportar:\n{e}")

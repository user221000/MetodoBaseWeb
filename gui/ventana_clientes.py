# -*- coding: utf-8 -*-
"""
Ventana de gestión de clientes con historial y seguimiento.

Esta ventana permite:
- Ver lista de todos los clientes registrados
- Buscar clientes por nombre/teléfono
- Ver historial detallado de cada cliente
- Exportar datos a Excel
"""

import os
import csv
from datetime import datetime
from typing import Dict, List

import customtkinter as ctk
from tkinter import messagebox

from src.gestor_bd import GestorBDClientes
from utils.logger import logger
from utils.helpers import activar_modal_seguro, centrar_ventana
from config.constantes import CARPETA_SALIDA
from config.plantillas_cliente import PLANTILLAS_CLIENTE
from gui.widgets_toast import mostrar_toast


PLANTILLA_LABELS = {
    clave: data["label"] for clave, data in PLANTILLAS_CLIENTE.items()
}


class VentanaClientes(ctk.CTkToplevel):
    """Ventana de gestión y seguimiento de clientes."""
    
    # Paleta de colores consistente con la app principal
    COLOR_BG = "#0D0D0D"
    COLOR_CARD = "#1A1A1A"
    COLOR_PRIMARY = "#9B4FB0"
    COLOR_PRIMARY_HOVER = "#B565C6"
    COLOR_SECONDARY = "#D4A84B"
    COLOR_BORDER = "#444444"
    COLOR_TEXT = "#F5F5F5"
    COLOR_TEXT_MUTED = "#B8B8B8"
    COLOR_SUCCESS = "#4CAF50"
    COLOR_INFO = "#2196F3"
    COLOR_WARNING = "#FF7043"
    
    def __init__(self, master, gestor_bd: GestorBDClientes):
        super().__init__(master)
        
        self.gestor_bd = gestor_bd
        self.clientes_todos: List[dict] = []
        self.clientes_filtrados: List[dict] = []
        self.progreso_por_cliente: Dict[str, dict] = {}
        
        self.title("Mis Clientes — Método Base")
        self.geometry("900x700")
        self.configure(fg_color=self.COLOR_BG)

        centrar_ventana(self, 900, 700)
        
        self._construir_ui()
        self._cargar_clientes()
        activar_modal_seguro(self, master)
        
        logger.info("[CLIENTES] Ventana abierta")
        
    def _construir_ui(self) -> None:
        """Construye la interfaz de usuario."""
        # Header con título y búsqueda
        self.header_frame = ctk.CTkFrame(
            self, fg_color="transparent", height=80
        )
        self.header_frame.pack(fill="x", padx=20, pady=20)
        self.header_frame.pack_propagate(False)
        
        # Título
        self.lbl_titulo = ctk.CTkLabel(
            self.header_frame,
            text="🏋️ Clientes Registrados",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=self.COLOR_TEXT
        )
        self.lbl_titulo.pack(side="left", anchor="w")
        
        # Campo de búsqueda
        self.search_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.search_frame.pack(side="right", anchor="e")
        
        self.lbl_buscar = ctk.CTkLabel(
            self.search_frame,
            text="🔍 Buscar:",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=self.COLOR_TEXT_MUTED
        )
        self.lbl_buscar.pack(side="left", padx=(0, 8))
        
        self.entry_buscar = ctk.CTkEntry(
            self.search_frame,
            placeholder_text="Nombre o teléfono...",
            width=250,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=self.COLOR_CARD,
            border_color=self.COLOR_BORDER,
            text_color=self.COLOR_TEXT
        )
        self.entry_buscar.pack(side="left")
        self.entry_buscar.bind("<KeyRelease>", self._filtrar_clientes)
        
        # Frame principal con scroll
        self.scroll_frame = ctk.CTkScrollableFrame(
            self,
            fg_color=self.COLOR_BG,
            scrollbar_button_color=self.COLOR_PRIMARY,
            scrollbar_button_hover_color=self.COLOR_PRIMARY_HOVER
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Footer con estadísticas y botón exportar
        self.footer_frame = ctk.CTkFrame(
            self, fg_color=self.COLOR_CARD, height=60
        )
        self.footer_frame.pack(fill="x", padx=20, pady=(0, 20))
        self.footer_frame.pack_propagate(False)
        
        # Contador de clientes
        self.lbl_total = ctk.CTkLabel(
            self.footer_frame,
            text="Total: 0 clientes activos",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=self.COLOR_TEXT_MUTED
        )
        self.lbl_total.pack(side="left", padx=15, pady=15)
        
        # Botón exportar CSV
        self.btn_exportar = ctk.CTkButton(
            self.footer_frame,
            text="📊 Exportar CSV",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=self.COLOR_SUCCESS,
            hover_color="#43A047",
            text_color="white",
            width=140,
            command=self._exportar_excel
        )
        self.btn_exportar.pack(side="right", padx=15, pady=15)

    @staticmethod
    def _fmt_num(valor, sufijo: str = "", decimales: int = 1) -> str:
        if valor is None:
            return "N/D"
        return f"{float(valor):.{decimales}f}{sufijo}"

    @staticmethod
    def _fmt_delta(valor, sufijo: str = "", decimales: int = 1) -> str:
        if valor is None:
            return "N/D"
        return f"{float(valor):+.{decimales}f}{sufijo}"

    def _color_delta(self, delta) -> str:
        if delta is None:
            return self.COLOR_TEXT_MUTED
        if abs(float(delta)) < 0.05:
            return self.COLOR_INFO
        return self.COLOR_SUCCESS if float(delta) < 0 else self.COLOR_WARNING

    def _obtener_label_plantilla(self, cliente: dict) -> str:
        plantilla_tipo = cliente.get("plantilla_tipo") or "general"
        return PLANTILLA_LABELS.get(plantilla_tipo, "General")

    def _construir_progreso_cliente(self, cliente: dict) -> dict:
        id_cliente = cliente.get("id_cliente")
        progreso = self.gestor_bd.obtener_progreso_cliente(id_cliente) if id_cliente else {}
        progreso = progreso or {}

        if not progreso.get("planes_registrados"):
            peso = cliente.get("peso_kg")
            grasa = cliente.get("grasa_corporal_pct")
            progreso = {
                "planes_registrados": int(cliente.get("total_planes_generados") or 0),
                "peso_inicial": peso,
                "peso_actual": peso,
                "delta_peso": 0.0 if peso is not None else None,
                "grasa_inicial": grasa,
                "grasa_actual": grasa,
                "delta_grasa": 0.0 if grasa is not None else None,
            }
        return progreso
        
    def _cargar_clientes(self, filtro: str = "") -> None:
        """Carga los clientes desde la BD y los muestra."""
        try:
            if filtro.strip():
                self.clientes_filtrados = self.gestor_bd.buscar_clientes(filtro.strip())
            else:
                self.clientes_todos = self.gestor_bd.obtener_todos_clientes(solo_activos=True)
                self.clientes_filtrados = self.clientes_todos.copy()

            self.progreso_por_cliente = {}
            for cliente in self.clientes_filtrados:
                id_cliente = cliente.get("id_cliente")
                if not id_cliente:
                    continue
                self.progreso_por_cliente[id_cliente] = self._construir_progreso_cliente(cliente)
            
            self._repoblar_tarjetas()
            
        except Exception as e:
            logger.error("[CLIENTES] Error cargando clientes: %s", e)
            messagebox.showerror("Error", f"Error cargando clientes:\\n{e}")
            
    def _repoblar_tarjetas(self) -> None:
        """Limpia el scroll frame y crea nuevas tarjetas de cliente."""
        # Limpiar tarjetas existentes
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
            
        # Actualizar contador
        total = len(self.clientes_filtrados)
        self.lbl_total.configure(text=f"Total: {total} cliente{'s' if total != 1 else ''}")
        
        if not self.clientes_filtrados:
            # Mensaje cuando no hay resultados
            self.lbl_vacio = ctk.CTkLabel(
                self.scroll_frame,
                text="😔 No se encontraron clientes",
                font=ctk.CTkFont(family="Segoe UI", size=16),
                text_color=self.COLOR_TEXT_MUTED
            )
            self.lbl_vacio.pack(pady=50)
            return
            
        # Crear tarjetas para cada cliente
        for cliente in self.clientes_filtrados:
            self._crear_tarjeta_cliente(self.scroll_frame, cliente)
            
    def _crear_tarjeta_cliente(self, parent, cliente: dict) -> None:
        """Crea una tarjeta visual para un cliente."""
        tarjeta = ctk.CTkFrame(
            parent,
            fg_color=self.COLOR_CARD,
            border_width=1,
            border_color=self.COLOR_BORDER,
            corner_radius=12
        )
        tarjeta.pack(fill="x", pady=8, padx=10)
        
        # Layout interno
        tarjeta.grid_columnconfigure(0, weight=1)
        
        # Fila 1: Nombre y fecha
        fila1 = ctk.CTkFrame(tarjeta, fg_color="transparent")
        fila1.grid(row=0, column=0, sticky="ew", padx=15, pady=(12, 4))
        fila1.grid_columnconfigure(0, weight=1)
        
        nombre_texto = cliente.get('nombre', 'Sin nombre')
        fecha_registro = cliente.get('fecha_registro', '')
        if fecha_registro:
            try:
                fecha_obj = datetime.fromisoformat(fecha_registro.replace('Z', '+00:00'))
                fecha_texto = fecha_obj.strftime('%d/%m/%Y')
            except:
                fecha_texto = str(fecha_registro)[:10]
        else:
            fecha_texto = 'Sin fecha'
            
        lbl_nombre = ctk.CTkLabel(
            fila1,
            text=f"👤 {nombre_texto}",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=self.COLOR_TEXT,
            anchor="w"
        )
        lbl_nombre.grid(row=0, column=0, sticky="w")
        
        lbl_fecha = ctk.CTkLabel(
            fila1,
            text=f"📅 {fecha_texto}",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=self.COLOR_TEXT_MUTED
        )
        lbl_fecha.grid(row=0, column=1, sticky="e")
        
        # Fila 2: Datos físicos y objetivo
        fila2 = ctk.CTkFrame(tarjeta, fg_color="transparent")
        fila2.grid(row=1, column=0, sticky="ew", padx=15, pady=2)

        peso = cliente.get('peso_kg')
        grasa = cliente.get('grasa_corporal_pct')
        objetivo = cliente.get('objetivo', 'Sin objetivo')
        plantilla_label = self._obtener_label_plantilla(cliente)

        info_texto = (
            f"{self._fmt_num(peso, ' kg')} · "
            f"{self._fmt_num(grasa, '%')} grasa · "
            f"{objetivo.title()} · Plantilla: {plantilla_label}"
        )

        lbl_info = ctk.CTkLabel(
            fila2,
            text=info_texto,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=self.COLOR_TEXT_MUTED,
            anchor="w"
        )
        lbl_info.pack(anchor="w")

        # Fila 3: Progreso visual de peso y grasa
        fila3 = ctk.CTkFrame(tarjeta, fg_color="transparent")
        fila3.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 2))
        fila3.grid_columnconfigure(0, weight=1)
        fila3.grid_columnconfigure(1, weight=1)

        progreso = self.progreso_por_cliente.get(cliente.get("id_cliente"), {})
        peso_i = progreso.get("peso_inicial")
        peso_a = progreso.get("peso_actual")
        delta_peso = progreso.get("delta_peso")
        grasa_i = progreso.get("grasa_inicial")
        grasa_a = progreso.get("grasa_actual")
        delta_grasa = progreso.get("delta_grasa")

        lbl_progreso_peso = ctk.CTkLabel(
            fila3,
            text=(
                f"Peso: {self._fmt_num(peso_i, 'kg')} -> {self._fmt_num(peso_a, 'kg')} "
                f"(Δ {self._fmt_delta(delta_peso, 'kg')})"
            ),
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=self._color_delta(delta_peso),
            anchor="w",
        )
        lbl_progreso_peso.grid(row=0, column=0, sticky="w")

        lbl_progreso_grasa = ctk.CTkLabel(
            fila3,
            text=(
                f"Grasa: {self._fmt_num(grasa_i, '%')} -> {self._fmt_num(grasa_a, '%')} "
                f"(Δ {self._fmt_delta(delta_grasa, '%')})"
            ),
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=self._color_delta(delta_grasa),
            anchor="w",
        )
        lbl_progreso_grasa.grid(row=0, column=1, sticky="w")

        # Fila 4: Planes y botones
        fila4 = ctk.CTkFrame(tarjeta, fg_color="transparent")
        fila4.grid(row=3, column=0, sticky="ew", padx=15, pady=(2, 12))
        fila4.grid_columnconfigure(0, weight=1)

        total_planes = (
            cliente.get('total_planes_generados')
            or cliente.get('total_planes')
            or progreso.get("planes_registrados")
            or 0
        )
        txt_planes = f"Planes generados: {int(total_planes)}"
        if int(total_planes) <= 1:
            txt_planes += " · Genera mas planes para ver tendencia completa"

        lbl_planes = ctk.CTkLabel(
            fila4,
            text=txt_planes,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=self.COLOR_TEXT_MUTED,
            anchor="w"
        )
        lbl_planes.grid(row=0, column=0, sticky="w")
        
        # Botones
        botones_frame = ctk.CTkFrame(fila4, fg_color="transparent")
        botones_frame.grid(row=0, column=1, sticky="e")
        
        btn_historial = ctk.CTkButton(
            botones_frame,
            text="Ver Historial",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            width=90,
            height=28,
            fg_color=self.COLOR_INFO,
            hover_color="#1976D2",
            command=lambda c=cliente: self._ver_historial(c['id_cliente'], c['nombre'])
        )
        btn_historial.pack(side="left", padx=(0, 8))
        
        btn_nuevo_plan = ctk.CTkButton(
            botones_frame,
            text="Regenerar",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            width=90,
            height=28,
            fg_color=self.COLOR_PRIMARY,
            hover_color=self.COLOR_PRIMARY_HOVER,
            command=lambda c=cliente: self._nuevo_plan(c)
        )
        btn_nuevo_plan.pack(side="left")
        
    def _filtrar_clientes(self, event=None) -> None:
        """Filtra clientes según el texto de búsqueda."""
        filtro = self.entry_buscar.get().strip()
        self._cargar_clientes(filtro)
        
    def _ver_historial(self, id_cliente: str, nombre: str) -> None:
        """Abre la ventana de historial para un cliente específico."""
        try:
            VentanaHistorialCliente(self, self.gestor_bd, id_cliente, nombre)
        except Exception as e:
            logger.error("[CLIENTES] Error abriendo historial: %s", e)
            messagebox.showerror("Error", f"Error abriendo historial:\\n{e}")
            
    def _nuevo_plan(self, cliente: dict) -> None:
        """Carga cliente en la ventana principal para regenerar plan."""
        try:
            id_cliente = cliente.get("id_cliente")
            if not id_cliente:
                messagebox.showwarning("Aviso", "No se encontró ID de cliente.")
                return

            cliente_completo = self.gestor_bd.obtener_cliente_por_id(id_cliente) or cliente
            historial = self.gestor_bd.obtener_historial_planes(id_cliente, limite=1)
            plan_reciente = historial[0] if historial else None

            if not hasattr(self.master, "cargar_cliente_para_regeneracion"):
                messagebox.showwarning(
                    "No disponible",
                    "La ventana principal no soporta regeneración automática en esta versión.",
                )
                return

            self.master.cargar_cliente_para_regeneracion(cliente_completo, plan_reciente)
            self.master.lift()
            self.master.focus_force()
            mostrar_toast(self, "Cliente enviado a captura para regenerar plan", tipo="success")
            self.destroy()

        except Exception as e:
            logger.error("[CLIENTES] Error preparando regeneración: %s", e, exc_info=True)
            messagebox.showerror("Error", f"No se pudo preparar la regeneración:\n{e}")
        
    def _exportar_excel(self) -> None:
        """Exporta todos los clientes a un archivo CSV."""
        try:
            fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_archivo = f"clientes_reporte_{fecha}.csv"
            ruta = os.path.join(CARPETA_SALIDA, nombre_archivo)
            
            # Asegurar directorio existe
            os.makedirs(CARPETA_SALIDA, exist_ok=True)
            
            # Headers para CSV
            headers = [
                'ID Cliente', 'Nombre', 'Teléfono', 'Edad', 'Peso (kg)',
                'Estatura (cm)', 'Grasa (%)', 'Nivel Actividad', 'Objetivo',
                'Plantilla', 'Fecha Registro', 'Último Plan', 'Total Planes'
            ]
            
            # Escribir CSV
            with open(ruta, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(headers)
                
                for cliente in self.clientes_todos:
                    # Formatear fechas
                    fecha_reg = cliente.get('fecha_registro', '')
                    if fecha_reg:
                        try:
                            fecha_obj = datetime.fromisoformat(fecha_reg.replace('Z', '+00:00'))
                            fecha_reg_str = fecha_obj.strftime('%d/%m/%Y %H:%M')
                        except:
                            fecha_reg_str = str(fecha_reg)
                    else:
                        fecha_reg_str = ''
                        
                    ultimo_plan = cliente.get('ultimo_plan', '')
                    if ultimo_plan:
                        try:
                            fecha_obj = datetime.fromisoformat(ultimo_plan.replace('Z', '+00:00'))
                            ultimo_plan_str = fecha_obj.strftime('%d/%m/%Y %H:%M')
                        except:
                            ultimo_plan_str = str(ultimo_plan)
                    else:
                        ultimo_plan_str = ''
                    
                    fila = [
                        cliente.get('id_cliente', ''),
                        cliente.get('nombre', ''),
                        cliente.get('telefono', ''),
                        cliente.get('edad', ''),
                        cliente.get('peso_kg', ''),
                        cliente.get('estatura_cm', ''),
                        cliente.get('grasa_corporal_pct', ''),
                        cliente.get('nivel_actividad', ''),
                        cliente.get('objetivo', ''),
                        self._obtener_label_plantilla(cliente),
                        fecha_reg_str,
                        ultimo_plan_str,
                        cliente.get('total_planes_generados', 0)
                    ]
                    writer.writerow(fila)
            
            logger.info("[CLIENTES] CSV exportado: %s", ruta)
            mostrar_toast(self, f"✅ CSV exportado: {nombre_archivo}", tipo="success")
            
            # Abrir carpeta
            try:
                from utils.helpers import abrir_carpeta_pdf
                abrir_carpeta_pdf(os.path.dirname(ruta))
            except:
                pass
                
        except Exception as e:
            logger.error("[CLIENTES] Error exportando CSV: %s", e)
            messagebox.showerror("Error", f"Error exportando CSV:\\n{e}")


class VentanaHistorialCliente(ctk.CTkToplevel):
    """Sub-ventana que muestra el historial detallado de un cliente."""
    
    COLOR_BG = "#0D0D0D"
    COLOR_CARD = "#1A1A1A"
    COLOR_PRIMARY = "#9B4FB0"
    COLOR_BORDER = "#444444"
    COLOR_TEXT = "#F5F5F5"
    COLOR_TEXT_MUTED = "#B8B8B8"
    COLOR_SUCCESS = "#4CAF50"
    COLOR_INFO = "#2196F3"
    COLOR_WARNING = "#FF7043"
    
    def __init__(self, master, gestor_bd: GestorBDClientes, id_cliente: str, nombre: str):
        super().__init__(master)
        
        self.gestor_bd = gestor_bd
        self.id_cliente = id_cliente
        self.nombre = nombre
        self._planes_historial: List[dict] = []
        
        self.title(f"Historial: {nombre}")
        self.geometry("640x560")
        self.configure(fg_color=self.COLOR_BG)

        centrar_ventana(self, 640, 560)
        
        self._construir_ui()
        self._cargar_historial()
        activar_modal_seguro(self, master)
        
    def _construir_ui(self) -> None:
        """Construye la interfaz del historial."""
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent", height=60)
        header.pack(fill="x", padx=20, pady=(20, 10))
        header.pack_propagate(False)
        
        lbl_titulo = ctk.CTkLabel(
            header,
            text=f"📈 Historial: {self.nombre}",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=self.COLOR_TEXT
        )
        lbl_titulo.pack(anchor="w")

        # Filtros rápidos
        filtros = ctk.CTkFrame(self, fg_color=self.COLOR_CARD, corner_radius=10)
        filtros.pack(fill="x", padx=20, pady=(0, 10))
        filtros.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(
            filtros,
            text="Formato",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=self.COLOR_TEXT_MUTED,
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 2))
        self.seg_formato = ctk.CTkSegmentedButton(
            filtros,
            values=["Todos", "Menú Fijo", "Con Opciones"],
            command=lambda _v: self._aplicar_filtros_historial(),
            fg_color="#2A2A2A",
            selected_color=self.COLOR_PRIMARY,
            selected_hover_color="#B565C6",
            unselected_color="#1F1F1F",
            unselected_hover_color="#333333",
            font=ctk.CTkFont(family="Segoe UI", size=11),
        )
        self.seg_formato.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 8))
        self.seg_formato.set("Todos")

        ctk.CTkLabel(
            filtros,
            text="Objetivo",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=self.COLOR_TEXT_MUTED,
        ).grid(row=0, column=1, sticky="w", padx=10, pady=(8, 2))
        self.seg_objetivo = ctk.CTkSegmentedButton(
            filtros,
            values=["Todos", "Deficit", "Mantenimiento", "Superavit"],
            command=lambda _v: self._aplicar_filtros_historial(),
            fg_color="#2A2A2A",
            selected_color=self.COLOR_PRIMARY,
            selected_hover_color="#B565C6",
            unselected_color="#1F1F1F",
            unselected_hover_color="#333333",
            font=ctk.CTkFont(family="Segoe UI", size=11),
        )
        self.seg_objetivo.grid(row=1, column=1, sticky="ew", padx=10, pady=(0, 8))
        self.seg_objetivo.set("Todos")

        ctk.CTkLabel(
            filtros,
            text="Plantilla",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=self.COLOR_TEXT_MUTED,
        ).grid(row=0, column=2, sticky="w", padx=10, pady=(8, 2))
        self.combo_plantilla_filtro = ctk.CTkComboBox(
            filtros,
            values=["Todas"],
            command=lambda _v: self._aplicar_filtros_historial(),
            fg_color="#1F1F1F",
            border_color=self.COLOR_BORDER,
            button_color=self.COLOR_PRIMARY,
            button_hover_color=self.COLOR_PRIMARY,
            dropdown_fg_color=self.COLOR_CARD,
            dropdown_hover_color=self.COLOR_PRIMARY,
            font=ctk.CTkFont(family="Segoe UI", size=11),
        )
        self.combo_plantilla_filtro.grid(row=1, column=2, sticky="ew", padx=10, pady=(0, 8))
        self.combo_plantilla_filtro.set("Todas")
        
        # Tabla de historial
        self.scroll_historial = ctk.CTkScrollableFrame(
            self,
            fg_color=self.COLOR_BG,
            scrollbar_button_color=self.COLOR_PRIMARY
        )
        self.scroll_historial.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Footer con botón exportar individual
        footer = ctk.CTkFrame(self, fg_color=self.COLOR_CARD, height=50)
        footer.pack(fill="x", padx=20, pady=(0, 20))
        footer.pack_propagate(False)
        
        btn_exportar_individual = ctk.CTkButton(
            footer,
            text="📊 Exportar CSV Individual",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=self.COLOR_SUCCESS,
            hover_color="#43A047",
            command=self._exportar_excel_individual
        )
        btn_exportar_individual.pack(side="right", padx=15, pady=10)

    @staticmethod
    def _label_formato(tipo_plan: str | None) -> str:
        return "Con Opciones" if str(tipo_plan or "").lower() == "con_opciones" else "Menú Fijo"

    @staticmethod
    def _normalizar_numero(valor):
        try:
            if valor is None:
                return None
            return float(valor)
        except Exception:
            return None

    def _crear_comparativa_visual(
        self,
        parent,
        *,
        peso_inicial,
        peso_actual,
        grasa_inicial,
        grasa_actual,
    ) -> None:
        """Renderiza comparativa visual rápida (inicial vs actual)."""
        card = ctk.CTkFrame(parent, fg_color=self.COLOR_CARD, corner_radius=10)
        card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            card,
            text="Comparativa visual rápida",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=self.COLOR_TEXT,
            anchor="w",
        ).pack(anchor="w", padx=12, pady=(10, 4))

        self._fila_comparativa(card, "Peso (kg)", peso_inicial, peso_actual, color_actual=self.COLOR_INFO)
        self._fila_comparativa(card, "Grasa (%)", grasa_inicial, grasa_actual, color_actual=self.COLOR_WARNING)

    def _fila_comparativa(self, parent, titulo: str, inicial, actual, color_actual: str) -> None:
        fila = ctk.CTkFrame(parent, fg_color="transparent")
        fila.pack(fill="x", padx=12, pady=(2, 8))

        ini = self._normalizar_numero(inicial)
        act = self._normalizar_numero(actual)
        if ini is None or act is None:
            ctk.CTkLabel(
                fila,
                text=f"{titulo}: N/D",
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=self.COLOR_TEXT_MUTED,
                anchor="w",
            ).pack(anchor="w")
            return

        delta = act - ini
        delta_txt = f"{delta:+.1f}"
        tendencia = "↘ mejora" if delta < 0 else ("↗ sube" if delta > 0 else "→ estable")

        ctk.CTkLabel(
            fila,
            text=f"{titulo}: {ini:.1f} → {act:.1f} ({delta_txt}) {tendencia}",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=self.COLOR_TEXT,
            anchor="w",
        ).pack(anchor="w", pady=(0, 3))

        max_ref = max(ini, act, 1.0)
        bar_ini = ctk.CTkProgressBar(
            fila,
            height=10,
            fg_color="#2A2A2A",
            progress_color="#6E6E6E",
        )
        bar_ini.pack(fill="x", pady=(0, 2))
        bar_ini.set(ini / max_ref)

        bar_act = ctk.CTkProgressBar(
            fila,
            height=10,
            fg_color="#2A2A2A",
            progress_color=color_actual,
        )
        bar_act.pack(fill="x")
        bar_act.set(act / max_ref)

    def _limpiar_historial_view(self) -> None:
        for widget in self.scroll_historial.winfo_children():
            widget.destroy()

    def _aplicar_filtros_historial(self) -> None:
        self._limpiar_historial_view()

        if not self._planes_historial:
            lbl_vacio = ctk.CTkLabel(
                self.scroll_historial,
                text="📝 Este cliente aún no tiene planes generados",
                font=ctk.CTkFont(family="Segoe UI", size=14),
                text_color=self.COLOR_TEXT_MUTED,
            )
            lbl_vacio.pack(pady=50)
            return

        formato_sel = self.seg_formato.get()
        objetivo_sel = self.seg_objetivo.get().strip().lower()
        plantilla_sel = self.combo_plantilla_filtro.get().strip()

        planes_filtrados = list(self._planes_historial)

        if formato_sel == "Menú Fijo":
            planes_filtrados = [p for p in planes_filtrados if p.get("tipo_plan") != "con_opciones"]
        elif formato_sel == "Con Opciones":
            planes_filtrados = [p for p in planes_filtrados if p.get("tipo_plan") == "con_opciones"]

        if objetivo_sel != "todos":
            planes_filtrados = [
                p for p in planes_filtrados
                if str(p.get("objetivo", "")).strip().lower() == objetivo_sel
            ]

        if plantilla_sel and plantilla_sel != "Todas":
            planes_filtrados = [
                p for p in planes_filtrados
                if PLANTILLA_LABELS.get(p.get("plantilla_tipo"), "General") == plantilla_sel
            ]

        if not planes_filtrados:
            ctk.CTkLabel(
                self.scroll_historial,
                text="Sin resultados para los filtros seleccionados.",
                font=ctk.CTkFont(family="Segoe UI", size=13),
                text_color=self.COLOR_TEXT_MUTED,
            ).pack(pady=50)
            return

        self._render_historial(planes_filtrados)

    def _render_historial(self, planes: List[dict]) -> None:
        def _fecha_display(plan: dict) -> str:
            fecha = str(plan.get("fecha_generacion", "") or "")
            if not fecha:
                return "Sin fecha"
            try:
                fecha_obj = datetime.fromisoformat(fecha.replace("Z", "+00:00"))
                return fecha_obj.strftime('%d/%m/%Y')
            except Exception:
                return str(fecha)[:10]

        def _fecha_sort_key(plan: dict) -> float:
            fecha = str(plan.get("fecha_generacion", "") or "")
            if not fecha:
                return -1.0
            try:
                return datetime.fromisoformat(fecha.replace("Z", "+00:00")).timestamp()
            except Exception:
                return -1.0

        def _to_num(valor):
            return self._normalizar_numero(valor)

        def _fmt_num(valor, sufijo: str = "", decimales: int = 1):
            if valor is None:
                return "N/D"
            return f"{valor:.{decimales}f}{sufijo}"

        def _fmt_delta(valor, sufijo: str = "", decimales: int = 1):
            if valor is None:
                return "N/D"
            return f"{valor:+.{decimales}f}{sufijo}"

        def _color_delta(delta):
            if delta is None:
                return self.COLOR_TEXT_MUTED
            if abs(delta) < 0.05:
                return self.COLOR_INFO
            return self.COLOR_SUCCESS if delta < 0 else self.COLOR_WARNING

        planes_asc = sorted(planes, key=_fecha_sort_key)
        planes_desc = list(reversed(planes_asc))

        peso_vals = [_to_num(p.get("peso_en_momento")) for p in planes_asc]
        grasa_vals = [_to_num(p.get("grasa_en_momento")) for p in planes_asc]
        peso_vals = [v for v in peso_vals if v is not None]
        grasa_vals = [v for v in grasa_vals if v is not None]

        peso_inicial = peso_vals[0] if peso_vals else None
        peso_actual = peso_vals[-1] if peso_vals else None
        grasa_inicial = grasa_vals[0] if grasa_vals else None
        grasa_actual = grasa_vals[-1] if grasa_vals else None
        delta_peso = (
            round(peso_actual - peso_inicial, 2)
            if peso_inicial is not None and peso_actual is not None
            else None
        )
        delta_grasa = (
            round(grasa_actual - grasa_inicial, 2)
            if grasa_inicial is not None and grasa_actual is not None
            else None
        )

        resumen = ctk.CTkFrame(self.scroll_historial, fg_color=self.COLOR_CARD)
        resumen.pack(fill="x", pady=(0, 8))
        resumen.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(
            resumen,
            text=(
                f"Peso: {_fmt_num(peso_inicial, 'kg')} -> {_fmt_num(peso_actual, 'kg')} "
                f"(Δ {_fmt_delta(delta_peso, 'kg')})"
            ),
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=_color_delta(delta_peso),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=10)

        ctk.CTkLabel(
            resumen,
            text=(
                f"Grasa: {_fmt_num(grasa_inicial, '%')} -> {_fmt_num(grasa_actual, '%')} "
                f"(Δ {_fmt_delta(delta_grasa, '%')})"
            ),
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=_color_delta(delta_grasa),
        ).grid(row=0, column=1, sticky="w", padx=12, pady=10)

        self._crear_comparativa_visual(
            self.scroll_historial,
            peso_inicial=peso_inicial,
            peso_actual=peso_actual,
            grasa_inicial=grasa_inicial,
            grasa_actual=grasa_actual,
        )

        header_frame = ctk.CTkFrame(
            self.scroll_historial, fg_color=self.COLOR_PRIMARY, height=40
        )
        header_frame.pack(fill="x", pady=(0, 5))
        header_frame.pack_propagate(False)

        headers = ["Fecha", "Plantilla", "Formato", "Objetivo", "Kcal", "Peso", "Grasa"]
        header_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6), weight=1)

        for i, header in enumerate(headers):
            lbl = ctk.CTkLabel(
                header_frame,
                text=header,
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                text_color="white",
            )
            lbl.grid(row=0, column=i, padx=10, pady=10)

        for plan in planes_desc:
            fecha_str = _fecha_display(plan)
            objetivo = (plan.get('objetivo') or 'N/A').title()
            kcal = _to_num(plan.get('kcal_objetivo')) or 0
            peso = _to_num(plan.get('peso_en_momento'))
            grasa = _to_num(plan.get('grasa_en_momento'))
            plantilla = PLANTILLA_LABELS.get(plan.get("plantilla_tipo"), "General")
            tipo_plan = self._label_formato(plan.get("tipo_plan"))

            fila = ctk.CTkFrame(self.scroll_historial, fg_color=self.COLOR_CARD)
            fila.pack(fill="x", pady=2)
            fila.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6), weight=1)

            datos = [
                fecha_str,
                plantilla,
                tipo_plan,
                objetivo,
                f"{kcal:.0f}",
                _fmt_num(peso, "kg"),
                _fmt_num(grasa, "%"),
            ]
            for i, dato in enumerate(datos):
                lbl = ctk.CTkLabel(
                    fila,
                    text=dato,
                    font=ctk.CTkFont(family="Segoe UI", size=11),
                    text_color=self.COLOR_TEXT,
                )
                lbl.grid(row=0, column=i, padx=10, pady=8)
        
    def _cargar_historial(self) -> None:
        """Carga y muestra el historial del cliente."""
        try:
            self._planes_historial = self.gestor_bd.obtener_historial_planes(self.id_cliente)

            plantillas_disponibles = sorted({
                PLANTILLA_LABELS.get(p.get("plantilla_tipo"), "General")
                for p in self._planes_historial
            })
            valores_plantilla = ["Todas"] + plantillas_disponibles
            self.combo_plantilla_filtro.configure(values=valores_plantilla)
            if self.combo_plantilla_filtro.get() not in valores_plantilla:
                self.combo_plantilla_filtro.set("Todas")

            self._aplicar_filtros_historial()
                
        except Exception as e:
            logger.error("[HISTORIAL] Error cargando historial: %s", e)
            messagebox.showerror("Error", f"Error cargando historial:\\n{e}")
            
    def _exportar_excel_individual(self) -> None:
        """Exporta el seguimiento individual del cliente usando ExportadorMultiformato."""
        from core.exportador_multi import ExportadorMultiformato
        
        try:
            planes = self.gestor_bd.obtener_historial_planes(self.id_cliente)
            if not planes:
                messagebox.showwarning("Aviso", "Este cliente no tiene planes para exportar")
                return
                
            exportador = ExportadorMultiformato()
            ruta_csv = exportador.exportar_seguimiento_cliente(
                self.id_cliente, self.nombre, planes
            )
            
            mostrar_toast(self, "✅ CSV individual exportado", tipo="success")
            
            # Abrir carpeta
            try:
                from utils.helpers import abrir_carpeta_pdf
                abrir_carpeta_pdf(os.path.dirname(ruta_csv))
            except:
                pass
                
        except Exception as e:
            logger.error("[HISTORIAL] Error exportando Excel individual: %s", e)
            messagebox.showerror("Error", f"Error exportando Excel individual:\\n{e}")

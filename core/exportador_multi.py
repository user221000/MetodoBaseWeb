"""Exportación de planes nutricionales a múltiples formatos (Excel / CSV)."""
from __future__ import annotations

from datetime import datetime

from src.alimentos_base import ALIMENTOS_BASE

_COMIDAS_ORDEN = ["desayuno", "almuerzo", "comida", "cena"]

_CLIENTE_PUBLIC_FIELDS = {
    "nombre", "edad", "peso_kg", "estatura_cm", "grasa_corporal_pct",
    "objetivo", "nivel_actividad",
}


def filtrar_campos_cliente_export(cliente: dict | object) -> dict:
    """Retorna solo campos publicos permitidos para exportacion."""
    data: dict = {}
    if isinstance(cliente, dict):
        data = cliente
    else:
        data = {k: getattr(cliente, k, None) for k in _CLIENTE_PUBLIC_FIELDS}
    return {k: v for k, v in data.items() if k in _CLIENTE_PUBLIC_FIELDS}


class ExportadorMultiformato:
    """Exporta planes a múltiples formatos."""

    # ------------------------------------------------------------------ #
    # Excel                                                                #
    # ------------------------------------------------------------------ #

    @staticmethod
    def a_excel(cliente, plan, ruta_salida: str) -> str:
        """
        Genera Excel con cuatro hojas:
          1. Cliente  — resumen de datos del cliente
          2. Plan Semanal — alimentos y gramos por comida
          3. Lista de Compras — totales agrupados por alimento
          4. Macros Detallados — proteínas, carbs, grasas y kcal reales
        """
        import pandas as pd
        
        with pd.ExcelWriter(ruta_salida, engine="xlsxwriter") as writer:
            wb = writer.book

            # ── formatos ──
            fmt_header = wb.add_format({
                "bold": True, "bg_color": "#7B2D8E", "font_color": "#FFFFFF",
                "border": 1, "align": "center",
            })
            fmt_num = wb.add_format({"num_format": "0.0", "align": "right"})
            fmt_int = wb.add_format({"num_format": "0", "align": "right"})

            # ── Hoja 1: Cliente ──────────────────────────────────────── #
            public_cli = filtrar_campos_cliente_export(cliente)
            df_cliente = pd.DataFrame([{
                "Nombre":       public_cli.get("nombre", ""),
                "Edad":         public_cli.get("edad", ""),
                "Peso (kg)":    public_cli.get("peso_kg", ""),
                "Estatura (cm)": public_cli.get("estatura_cm", ""),
                "% Grasa":      public_cli.get("grasa_corporal_pct", ""),
                "Objetivo":     public_cli.get("objetivo", ""),
                "Actividad":    public_cli.get("nivel_actividad", ""),
                "TMB":          round(getattr(cliente, "tmb", 0), 1),
                "GET":          round(getattr(cliente, "get_total", 0), 1),
                "Kcal objetivo": round(getattr(cliente, "kcal_objetivo", 0), 1),
                "Proteína (g)": round(getattr(cliente, "proteina_g", 0), 1),
                "Carbs (g)":    round(getattr(cliente, "carbs_g", 0), 1),
                "Grasas (g)":   round(getattr(cliente, "grasa_g", 0), 1),
                "Fecha":        datetime.now().strftime("%Y-%m-%d"),
            }])
            df_cliente.to_excel(writer, sheet_name="Cliente", index=False)
            _autofit(writer.sheets["Cliente"], df_cliente, fmt_header)

            # ── Hoja 2: Plan Semanal ─────────────────────────────────── #
            rows_plan = []
            for comida_nombre in _COMIDAS_ORDEN:
                if comida_nombre not in plan:
                    continue
                comida = plan[comida_nombre]
                kcal_obj = comida.get("kcal_objetivo", 0)
                for alimento, gramos in comida.get("alimentos", {}).items():
                    rows_plan.append({
                        "Comida":        comida_nombre.capitalize(),
                        "Alimento":      alimento.replace("_", " ").capitalize(),
                        "Cantidad (g)":  int(gramos),
                        "Kcal objetivo": round(kcal_obj, 1),
                    })
            df_plan = pd.DataFrame(rows_plan) if rows_plan else pd.DataFrame(
                columns=["Comida", "Alimento", "Cantidad (g)", "Kcal objetivo"])
            df_plan.to_excel(writer, sheet_name="Plan Semanal", index=False)
            _autofit(writer.sheets["Plan Semanal"], df_plan, fmt_header)

            # ── Hoja 3: Lista de Compras ─────────────────────────────── #
            if not df_plan.empty:
                df_compras = (
                    df_plan.groupby("Alimento")["Cantidad (g)"]
                    .sum()
                    .reset_index()
                    .rename(columns={"Cantidad (g)": "Total diario (g)"})
                    .sort_values("Alimento")
                )
                df_compras["Total semanal (g)"] = df_compras["Total diario (g)"] * 7
            else:
                df_compras = pd.DataFrame(
                    columns=["Alimento", "Total diario (g)", "Total semanal (g)"])
            df_compras.to_excel(writer, sheet_name="Lista de Compras", index=False)
            _autofit(writer.sheets["Lista de Compras"], df_compras, fmt_header)

            # ── Hoja 4: Macros Detallados ────────────────────────────── #
            rows_macros = []
            totales = {"proteina_g": 0.0, "carbs_g": 0.0, "grasa_g": 0.0, "kcal": 0.0}
            for comida_nombre in _COMIDAS_ORDEN:
                if comida_nombre not in plan:
                    continue
                comida = plan[comida_nombre]
                p = c = g = k = 0.0
                for alimento, gramos in comida.get("alimentos", {}).items():
                    data = ALIMENTOS_BASE.get(alimento, {})
                    factor = gramos / 100
                    p += data.get("proteina", 0) * factor
                    c += data.get("carbs",    0) * factor
                    g += data.get("grasa",    0) * factor
                    k += data.get("kcal",     0) * factor
                rows_macros.append({
                    "Comida":       comida_nombre.capitalize(),
                    "Proteína (g)": round(p, 1),
                    "Carbs (g)":    round(c, 1),
                    "Grasas (g)":   round(g, 1),
                    "Kcal reales":  round(k, 1),
                    "Kcal objetivo": round(comida.get("kcal_objetivo", 0), 1),
                    "Desviación (%)": round(comida.get("desviacion_pct", 0), 2),
                })
                totales["proteina_g"] += p
                totales["carbs_g"]    += c
                totales["grasa_g"]    += g
                totales["kcal"]       += k

            rows_macros.append({
                "Comida":       "TOTAL",
                "Proteína (g)": round(totales["proteina_g"], 1),
                "Carbs (g)":    round(totales["carbs_g"],    1),
                "Grasas (g)":   round(totales["grasa_g"],    1),
                "Kcal reales":  round(totales["kcal"],       1),
                "Kcal objetivo": round(getattr(cliente, "kcal_objetivo", 0), 1),
                "Desviación (%)": "",
            })

            df_macros = pd.DataFrame(rows_macros)
            df_macros.to_excel(writer, sheet_name="Macros Detallados", index=False)
            _autofit(writer.sheets["Macros Detallados"], df_macros, fmt_header)

        return ruta_salida

    @staticmethod
    def a_excel_seguro(cliente_publico: dict, plan, ruta_salida: str) -> str:
        """Wrapper seguro: exporta usando solo campos publicos ya filtrados."""
        return ExportadorMultiformato.a_excel(cliente_publico, plan, ruta_salida)

    # ------------------------------------------------------------------ #
    # CSV                                                                  #
    # ------------------------------------------------------------------ #

    @staticmethod
    def a_csv_simple(plan, ruta_salida: str) -> str:
        """CSV simple para impresión rápida (compatible con Excel vía utf-8-sig)."""
        import pandas as pd
        
        rows = []
        for comida, datos in plan.items():
            if comida == "metadata_mes_anterior":
                continue
            for ali, gramos in datos.get("alimentos", {}).items():
                rows.append({
                    "comida":   comida,
                    "alimento": ali.replace("_", " ").capitalize(),
                    "gramos":   int(gramos),
                })
        df = pd.DataFrame(rows)
        df.to_csv(ruta_salida, index=False, encoding="utf-8-sig")
        return ruta_salida


# ────────────────────────────────────────────────────────────────────────── #
# Helpers                                                                    #
# ────────────────────────────────────────────────────────────────────────── #

    @staticmethod
    def exportar_seguimiento_cliente(id_cliente: str, nombre_cliente: str, planes: list) -> str:
        """
        Exporta el seguimiento completo de un cliente con historial de planes usando CSV básico.
        
        Args:
            id_cliente: ID único del cliente
            nombre_cliente: Nombre del cliente para el archivo
            planes: Lista de diccionarios con historial de planes generados
            
        Returns:
            str: Ruta del archivo CSV generado
        """
        import os
        import csv
        from config.constantes import CARPETA_SALIDA
        from utils.logger import logger
        
        # Preparar nombre de archivo seguro
        nombre_limpio = "".join(c for c in nombre_cliente if c.isalnum() or c in (' ', '-', '_')).rstrip()
        fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"seguimiento_{nombre_limpio}_{fecha}.csv"
        ruta_salida = os.path.join(CARPETA_SALIDA, nombre_archivo)
        
        # Asegurar directorio
        os.makedirs(CARPETA_SALIDA, exist_ok=True)
        
        # Validar que hay datos
        if not planes:
            logger.warning("[EXPORT] No hay planes para exportar para cliente %s", id_cliente)
            # Crear archivo vacío con headers mínimos
            with open(ruta_salida, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Cliente', 'ID', 'Estado'])
                writer.writerow([nombre_cliente, id_cliente, 'Sin planes generados'])
            return ruta_salida
            
        # Ordenar planes por fecha
        planes_ordenados = sorted(planes, key=lambda p: p.get('fecha_generacion', ''))
        
        # Headers para CSV de seguimiento
        headers = [
            'Fecha', 'Objetivo', 'Kcal Objetivo', 'Peso (kg)', 'Grasa (%)',
            'TMB', 'GET', 'Proteínas (g)', 'Carbohidratos (g)', 'Grasas (g)'
        ]
        
        try:
            with open(ruta_salida, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                
                # Escribir información del cliente como encabezado
                writer.writerow([f"SEGUIMIENTO NUTRICIONAL: {nombre_cliente}"])
                writer.writerow([f"ID Cliente: {id_cliente}"])
                writer.writerow([f"Total Planes: {len(planes)}"])
                writer.writerow([f"Reporte generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"])
                writer.writerow([])  # Línea vacía
                
                # Headers de datos
                writer.writerow(headers)
                
                # Datos del historial
                for plan in planes_ordenados:
                    # Formatear fecha
                    fecha_gen = plan.get('fecha_generacion', '')
                    if fecha_gen:
                        try:
                            fecha_obj = datetime.fromisoformat(fecha_gen.replace('Z', '+00:00'))
                            fecha_str = fecha_obj.strftime('%d/%m/%Y')
                        except:
                            fecha_str = str(fecha_gen)[:10]
                    else:
                        fecha_str = 'Sin fecha'
                        
                    fila = [
                        fecha_str,
                        plan.get('objetivo', 'N/A').title(),
                        plan.get('kcal_objetivo', 0),
                        plan.get('peso_en_momento', 0),
                        plan.get('grasa_en_momento', 0),
                        plan.get('tmb', 0),
                        plan.get('get_total', 0),
                        round(plan.get('proteinas_g', 0), 1),
                        round(plan.get('carbohidratos_g', 0), 1),
                        round(plan.get('grasas_g', 0), 1)
                    ]
                    writer.writerow(fila)
                
                # Sección de evolución del peso si hay múltiples planes
                if len(planes_ordenados) > 1:
                    writer.writerow([])  # Línea vacía
                    writer.writerow(["EVOLUCIÓN DEL PESO"])
                    writer.writerow(["Fecha", "Peso (kg)", "Cambio (kg)", "% Cambio"])
                    
                    peso_inicial = planes_ordenados[0].get('peso_en_momento', 0) if planes_ordenados else 0
                    
                    for plan in planes_ordenados:
                        fecha_gen = plan.get('fecha_generacion', '')
                        if fecha_gen:
                            try:
                                fecha_obj = datetime.fromisoformat(fecha_gen.replace('Z', '+00:00'))
                                fecha_str = fecha_obj.strftime('%d/%m/%Y')
                            except:
                                fecha_str = str(fecha_gen)[:10]
                        else:
                            fecha_str = 'Sin fecha'
                            
                        peso_actual = plan.get('peso_en_momento', 0)
                        cambio = peso_actual - peso_inicial if peso_inicial > 0 else 0
                        pct_cambio = (cambio / peso_inicial * 100) if peso_inicial > 0 else 0
                        
                        writer.writerow([
                            fecha_str,
                            peso_actual,
                            round(cambio, 1),
                            f"{pct_cambio:.1f}%"
                        ])
                        
        except Exception as e:
            logger.error("[EXPORT] Error creando CSV de seguimiento: %s", e)
            raise
        
        logger.info("[EXPORT] Seguimiento cliente exportado: %s", nombre_archivo)
        return ruta_salida


def _autofit(sheet, df, fmt_header) -> None:
    """Aplica ancho automático y formato de encabezado."""
    for col_idx, col_name in enumerate(df.columns):
        width = max(len(str(col_name)), df[col_name].astype(str).map(len).max()
                    if not df.empty else 0) + 2
        sheet.set_column(col_idx, col_idx, min(width, 40))
        sheet.write(0, col_idx, col_name, fmt_header)

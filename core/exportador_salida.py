"""Generación de PDF profesional y exportación de planes a JSON."""
import os
import json
import textwrap
from datetime import datetime

from reportlab.lib.pagesizes import LETTER, letter
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from utils.helpers import resource_path
from config.constantes import CARPETA_SALIDA, CARPETA_PLANES
from src.alimentos_base import ALIMENTOS_BASE
from core.branding import branding

# Registrar fuente Inter_18pt-BoldItalic para PDF (portabilidad total)
_font_inter_bolditalic = resource_path("fonts/Inter_18pt-BoldItalic.ttf")
if os.path.exists(_font_inter_bolditalic):
    pdfmetrics.registerFont(TTFont("Inter-BoldItalic", _font_inter_bolditalic))
else:
    print(f"[WARNING] Font not found: {_font_inter_bolditalic}")


# ============================================================================
# GENERADOR DE PDF PROFESIONAL
# ============================================================================

class GeneradorPDFProfesional:
    def __init__(self, ruta_salida, ruta_logo=None):
        self.ruta_salida = ruta_salida
        self.ruta_logo = ruta_logo
        self.width, self.height = LETTER

    def _dibujar_header(self, c, cliente, kcal_total=None):
        """Encabezado profesional con branding, logo y bloque de cliente."""
        logo = None
        if branding.get("pdf.mostrar_logo", True):
            logo_file = self.ruta_logo or branding.obtener_logo_pdf_path()
            if logo_file:
                try:
                    logo = ImageReader(str(logo_file))
                except Exception as e:
                    print(f"[ERROR] No se pudo cargar el logo para el PDF: {e}")
                    logo = None

        page_width, page_height = letter
        margin_x = 50
        header_top = page_height - 50
        tagline = (branding.get('tagline', '') or '').strip()
        color_encabezado = branding.get(
            "pdf.color_encabezado",
            branding.get("colores.primario", "#2A3A7A"),
        )

        # --- GYM BRANDING LEFT ---
        LEFT_MARGIN = margin_x
        y_pos = header_top
        c.setFillColor(colors.black)
        c.setFont("Inter-BoldItalic", 16)
        c.drawString(LEFT_MARGIN, y_pos, branding.get('nombre_gym', 'Gimnasio'))
        y_pos -= 15

        c.setFont("Inter-BoldItalic", 9)
        c.setFillColor(colors.HexColor("#333333"))
        c.drawString(LEFT_MARGIN, y_pos, branding.get('contacto.direccion_linea1', ''))
        y_pos -= 11
        c.drawString(LEFT_MARGIN, y_pos, branding.get('contacto.direccion_linea2', ''))
        y_pos -= 11
        c.drawString(LEFT_MARGIN, y_pos, branding.get('contacto.direccion_linea3', ''))
        y_pos -= 13

        c.setFont("Inter-BoldItalic", 8)
        c.setFillColor(colors.HexColor("#888888"))
        c.drawString(LEFT_MARGIN, y_pos, f"📷 {branding.get('redes_sociales.instagram', '')}")
        y_pos -= 14

        # --- GYM LOGO RIGHT ---
        if logo:
            logo_width = 70
            logo_height = 35
            logo_x = page_width - logo_width - LEFT_MARGIN
            logo_y = header_top - 25
            try:
                c.drawImage(
                    logo, logo_x, logo_y,
                    width=logo_width, height=logo_height,
                    preserveAspectRatio=True, mask='auto'
                )
            except Exception as e:
                print(f"[ERROR] drawImage logo: {e}")
            if tagline:
                c.setFont("Helvetica", 7)
                c.setFillColor(colors.gray)
                c.drawRightString(page_width - LEFT_MARGIN, logo_y - 8, tagline)

        # --- SEPARATOR LINE ---
        c.setLineWidth(0.5)
        c.setStrokeColor(colors.HexColor("#CCCCCC"))
        c.line(LEFT_MARGIN, y_pos - 8, page_width - 50, y_pos - 8)
        line_y = y_pos - 8

        # --- TITLE ---
        c.setFont("Inter-BoldItalic", 16)
        c.setFillColor(colors.HexColor(color_encabezado))
        y_title = line_y - 24
        c.drawCentredString(page_width / 2, y_title, "Plan nutricional personalizado")
        y_title -= 18

        if kcal_total:
            c.setFont("Inter-BoldItalic", 10)
            c.setFillColor(colors.HexColor("#444444"))
            c.drawCentredString(page_width / 2, y_title, f"Calorías diarias estimadas: {int(round(kcal_total))} kcal")
            y_title -= 16

        # --- CLIENT INFO ---
        c.setFont("Inter-BoldItalic", 9)
        c.setFillColor(colors.black)
        y_info = y_title - 6
        cliente_nombre = getattr(cliente, 'nombre', '') or ''
        cliente_edad = getattr(cliente, 'edad', '') or ''
        cliente_peso = getattr(cliente, 'peso_kg', '') or ''
        cliente_obj = getattr(cliente, 'objetivo', '').capitalize() if getattr(cliente, 'objetivo', None) else ''
        fecha_plan = datetime.now().strftime("%d %B %Y")
        info_linea_1 = (
            f"Cliente: {cliente_nombre}   Edad: {cliente_edad} años   "
            f"Peso: {cliente_peso} kg   Objetivo: {cliente_obj}"
        )
        info_linea_2 = f"Semana 1 | Fecha: {fecha_plan}"
        c.drawString(margin_x, y_info, info_linea_1)
        y_info -= 12
        c.setFillColor(colors.HexColor("#555555"))
        c.drawString(margin_x, y_info, info_linea_2)
        return y_info - 20

    def _dibujar_recomendaciones(self, c, y_inicial):
        """Dibuja la sección de recomendaciones básicas."""
        y = y_inicial
        c.setFillColor(colors.black)
        c.setFont("Inter-BoldItalic", 10)
        c.drawString(50, y, "RECOMENDACIONES BÁSICAS")
        y -= 14

        c.setFont("Inter-BoldItalic", 8)
        tips = [
            "Cocción: Utiliza aceite en aerosol (spray) para controlar la cantidad de grasa al cocinar.",
            "Medidas: Las tazas y cucharas deben ser medidas estándar y rasas (no copeteadas).",
            "Pesaje: Pesa los alimentos en crudo (antes de cocinar) salvo indicación contraria.",
            "Hidratación: Mantén una ingesta de agua constante de 2 a 3 litros diarios.",
            "Ansiedad: Puedes consumir GELATINA SIN AZÚCAR (light) libremente entre comidas.",
            "(Ideal para controlar el apetito en etapas de déficit o mantenimiento)."
        ]
        for tip in tips:
            wrapped = textwrap.wrap(tip, width=92)
            if not wrapped:
                continue
            c.drawString(60, y, f"• {wrapped[0]}")
            y -= 12
            for extra_line in wrapped[1:]:
                c.drawString(72, y, extra_line)
                y -= 12
        return y

    def _dibujar_disclaimer(self, c, page_width):
        """Disclaimer legal profesional al pie de página."""
        disclaimer = (
            "AVISO IMPORTANTE: Este plan nutricional es una guía general basada en objetivos de entrenamiento y composición corporal"
            " No constituye una consulta médica ni nutricional profesional. Si usted padece enfermedades crónicas "
            " como diabetes, anemia, hipertensión u otras condiciones médicas, "
            "se recomienda consultar con un médico o nutriólogo certificado antes de seguir cualquier plan alimenticio."
        )

        footer_y = 45
        left_margin = 90
        right_margin = 90
        c.setLineWidth(0.5)
        c.setStrokeColor(colors.lightgrey)
        c.line(left_margin, footer_y + 12, page_width - right_margin, footer_y + 12)
        c.setFont("Inter-BoldItalic", 6)
        c.setFillColor(colors.gray)
        text = c.beginText()
        text.setTextOrigin(left_margin, footer_y)
        text.setLeading(7)
        lines = textwrap.wrap(disclaimer, width=95)
        for line in lines:
            text.textLine(line)
        c.drawText(text)

    def generar(self, cliente, plan):
        try:
            c_pdf = canvas.Canvas(self.ruta_salida, pagesize=LETTER)
            page_width, page_height = letter

            kcal_total = sum(
                plan[n].get('kcal_objetivo', 0)
                for n in ['desayuno', 'almuerzo', 'comida', 'cena'] if n in plan
            )

            y = self._dibujar_header(c_pdf, cliente, kcal_total=kcal_total)

            comidas = ['desayuno', 'almuerzo', 'comida', 'cena']
            for idx, nombre_comida in enumerate(comidas):
                if nombre_comida in plan:
                    datos = plan[nombre_comida]
                    alimentos = datos.get('alimentos', {})
                    alimentos_filtrados = [
                        (alimento, gramos) for alimento, gramos in alimentos.items()
                        if int(round(gramos)) > 0
                    ] if alimentos else []

                    c_pdf.setFont("Inter-BoldItalic", 12)
                    c_pdf.setFillColor(colors.HexColor("#2A3A7A"))
                    c_pdf.drawString(60, y, f"{nombre_comida.upper()} — {int(round(datos.get('kcal_real', 0)))} kcal")
                    y -= 15
                    c_pdf.setStrokeColorRGB(0.1, 0.13, 0.25)
                    c_pdf.setLineWidth(1.5)
                    c_pdf.line(55, y + 12, 550, y + 12)
                    y -= 6

                    c_pdf.setFillColor(colors.HexColor("#222222"))
                    c_pdf.setFont("Inter-BoldItalic", 9)
                    if alimentos_filtrados:
                        for alimento, gramos in alimentos_filtrados:
                            nombre_ali = alimento.replace('_', ' ').capitalize()
                            gramos_int = int(round(gramos))
                            equivalencia = ""
                            if alimento == "huevo":
                                n_huevos = int(round(gramos / 50))
                                if n_huevos >= 1:
                                    equivalencia = f" ({n_huevos} huevo{'s' if n_huevos > 1 else ''})"
                            elif alimento == "tortilla_maiz":
                                n_tortillas = int(round(gramos / 30))
                                if n_tortillas >= 1:
                                    equivalencia = f" ({n_tortillas} tortilla{'s' if n_tortillas > 1 else ''})"
                            c_pdf.drawString(75, y, f"| {nombre_ali} — {gramos_int} g{equivalencia}")
                            y -= 14
                    else:
                        c_pdf.drawString(75, y, "Sin alimentos asignados")
                        y -= 14
                    y -= 14

            y -= 10
            c_pdf.setStrokeColor(colors.lightgrey)
            c_pdf.line(50, y, self.width - 50, y)
            y -= 20
            self._dibujar_recomendaciones(c_pdf, y)
            self._dibujar_disclaimer(c_pdf, page_width)

            c_pdf.save()

            # Abrir carpeta automáticamente al generar PDF
            from utils.file_operations import abrir_carpeta_en_explorador
            carpeta_output = os.path.dirname(os.path.abspath(self.ruta_salida))
            abrir_carpeta_en_explorador(carpeta_output)

            return self.ruta_salida

        except Exception as e:
            print(f"Error generando PDF: {e}")
            return None


# ============================================================================
# GENERADOR DE SALIDA (JSON)
# ============================================================================

class GeneradorSalida:
    """Genera salida (JSON principal, opciones PDF/web)."""
    
    @staticmethod
    def a_dict(cliente, plan: dict) -> dict:
        """Convierte plan a diccionario estructurado."""
        resultado = {
            'cliente': {
                'id': cliente.id_cliente,
                'nombre': cliente.nombre,
                'edad': cliente.edad,
                'peso_kg': cliente.peso_kg,
                'estatura_cm': cliente.estatura_cm,
                'grasa_corporal_pct': cliente.grasa_corporal_pct,
            },
            'motor': {
                'masa_magra_kg': round(cliente.masa_magra, 2) if cliente.masa_magra else None,
                'tmb_kcal': round(cliente.tmb, 2) if cliente.tmb else None,
                'get_kcal': round(cliente.get_total, 2) if cliente.get_total else None,
                'actividad': cliente.nivel_actividad,
                'objetivo': cliente.objetivo,
            },
            'macros_diarios': {
                'kcal_objetivo': round(cliente.kcal_objetivo, 2) if cliente.kcal_objetivo else None,
                'proteina_g': round(cliente.proteina_g, 1) if cliente.proteina_g else None,
                'grasa_g': round(cliente.grasa_g, 1) if cliente.grasa_g else None,
                'carbs_g': round(cliente.carbs_g, 1) if cliente.carbs_g else None,
            },
            'plan': {},
        }
        
        comidas_requeridas = {'desayuno', 'almuerzo', 'comida', 'cena'}
        comidas_procesadas = set()
        
        for nombre_comida, comida in plan.items():
            if nombre_comida == 'metadata_mes_anterior':
                continue
            
            if not isinstance(comida, dict):
                print(f"⚠️ GeneradorSalida.a_dict(): {nombre_comida} no es dict, es {type(comida)}")
                continue
            
            if 'kcal_objetivo' not in comida:
                print(f"❌ GeneradorSalida.a_dict() CRÍTICO: {nombre_comida} FALTA 'kcal_objetivo'")
                continue
            
            try:
                kcal_obj = float(comida['kcal_objetivo'])
                if kcal_obj <= 0:
                    print(f"✗ GeneradorSalida.a_dict(): {nombre_comida}['kcal_objetivo']={kcal_obj} inválido")
                    continue
            except (TypeError, ValueError):
                print(f"✗ GeneradorSalida.a_dict(): {nombre_comida}['kcal_objetivo'] no es número")
                continue
            
            campos_requeridos = {'kcal_real', 'desviacion_pct', 'macros_objetivo', 'alimentos'}
            campos_faltantes = campos_requeridos - set(comida.keys())
            if campos_faltantes:
                print(f"⚠️ {nombre_comida} falta campos: {campos_faltantes}")
            
            resultado['plan'][nombre_comida] = {
                'kcal_objetivo': round(comida.get('kcal_objetivo', 0), 1),
                'kcal_real': round(comida.get('kcal_real', 0), 1),
                'desviacion_pct': round(comida.get('desviacion_pct', 0), 2),
                'macros_objetivo': {
                    'proteina_g': round(comida.get('macros_objetivo', {}).get('proteina', 0), 1),
                    'carbs_g': round(comida.get('macros_objetivo', {}).get('carbs', 0), 1),
                    'grasa_g': round(comida.get('macros_objetivo', {}).get('grasa', 0), 1),
                },
                'alimentos': {
                    nombre: int(round(gramos / 10) * 10)
                    for nombre, gramos in comida.get('alimentos', {}).items()
                    if int(round(gramos / 10) * 10) > 10
                },
            }
            
            comidas_procesadas.add(nombre_comida)
        
        comidas_faltantes = comidas_requeridas - comidas_procesadas
        if comidas_faltantes:
            print(f"⚠️ GeneradorSalida.a_dict(): Faltan comidas en resultado: {comidas_faltantes}")
        
        if 'metadata_mes_anterior' in plan:
            resultado['metadata_mes_anterior'] = plan['metadata_mes_anterior']
        
        return resultado
    
    @staticmethod
    def a_json(resultado_dict: dict) -> str:
        """Convierte a JSON."""
        return json.dumps(resultado_dict, indent=2, ensure_ascii=False)
    
    @staticmethod
    def guardar_json(resultado_dict: dict, nombre_archivo: str = None) -> str:
        """Guarda JSON a archivo."""
        if nombre_archivo is None:
            cliente_id = resultado_dict['cliente']['id']
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_archivo = f"plan_{cliente_id}_{timestamp}.json"

        if not os.path.isabs(nombre_archivo):
            os.makedirs(CARPETA_PLANES, exist_ok=True)
            nombre_archivo = os.path.join(CARPETA_PLANES, nombre_archivo)
        
        with open(nombre_archivo, 'w', encoding='utf-8') as f:
            json.dump(resultado_dict, f, indent=2, ensure_ascii=False)
        
        return nombre_archivo

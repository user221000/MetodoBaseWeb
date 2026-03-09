"""
Exportador de PDF para planes con opciones múltiples.

Genera PDFs en formato educativo mostrando opciones equivalentes
que el cliente puede elegir.
"""

import os
import textwrap
from datetime import datetime
from typing import Dict

from reportlab.lib.pagesizes import LETTER, letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from utils.helpers import resource_path
from config.constantes import RUTA_LOGO
from utils.logger import logger

# Registrar fuente (idempotente: si ya está registrada no falla)
_font_inter_bolditalic = resource_path("fonts/Inter_18pt-BoldItalic.ttf")
if os.path.exists(_font_inter_bolditalic):
    try:
        pdfmetrics.getFont("Inter-BoldItalic")
    except KeyError:
        pdfmetrics.registerFont(TTFont("Inter-BoldItalic", _font_inter_bolditalic))

# Fuente por defecto si Inter no está disponible
try:
    pdfmetrics.getFont("Inter-BoldItalic")
    _FONT = "Inter-BoldItalic"
except KeyError:
    _FONT = "Helvetica"


class GeneradorPDFConOpciones:
    """
    Generador de PDF para planes con opciones múltiples.

    Formato de salida:
    - Agrupa por categoría de macronutriente
    - Muestra opciones numeradas con checkbox
    - Incluye macros detallados por opción
    - Nota educativa al final de cada comida
    """

    def __init__(self, ruta_salida: str, ruta_logo: str | None = None):
        self.ruta_salida = ruta_salida
        self.ruta_logo = ruta_logo or RUTA_LOGO
        self.width, self.height = LETTER

    def _dibujar_header(self, c, cliente, kcal_total: float | None = None) -> float:
        """Header con branding y subtítulo de 'Plan Flexible'."""
        logo_path = resource_path("assets/logo.png")
        try:
            logo = ImageReader(logo_path)
        except Exception:
            logo = None

        page_width, page_height = letter
        margin_x = 50
        header_top = page_height - 50

        # Branding del gym (izquierda)
        y_pos = header_top
        c.setFillColor(colors.black)
        c.setFont(_FONT, 16)
        c.drawString(margin_x, y_pos, "FitnessGym Real del Valle")
        y_pos -= 15

        c.setFont(_FONT, 9)
        c.drawString(margin_x, y_pos, "C. Valle De San José 1329B")
        y_pos -= 11
        c.drawString(margin_x, y_pos, "Fraccionamiento Real del Valle")
        y_pos -= 11
        c.drawString(margin_x, y_pos, "45654 Tlajomulco de Zúñiga, Jal.")
        y_pos -= 13

        c.setFont(_FONT, 8)
        c.setFillColor(colors.HexColor("#888888"))
        c.drawString(margin_x, y_pos, "@fitnessgym_realdelvalle")
        y_pos -= 14

        # Logo (derecha)
        if logo:
            logo_width = 70
            logo_height = 35
            logo_x = page_width - logo_width - margin_x
            logo_y = header_top - 25
            try:
                c.drawImage(
                    logo, logo_x, logo_y,
                    width=logo_width, height=logo_height,
                    preserveAspectRatio=True, mask='auto',
                )
            except Exception:
                pass

        # Línea separadora
        c.setLineWidth(0.5)
        c.setStrokeColor(colors.HexColor("#CCCCCC"))
        c.line(margin_x, y_pos - 8, page_width - 50, y_pos - 8)
        y_pos -= 20

        # Título principal
        c.setFont(_FONT, 16)
        c.setFillColor(colors.darkblue)
        c.drawCentredString(page_width / 2, y_pos, "Plan Nutricional Flexible con Opciones")
        y_pos -= 18

        if kcal_total:
            c.setFont(_FONT, 10)
            c.setFillColor(colors.HexColor("#444444"))
            c.drawCentredString(
                page_width / 2, y_pos,
                f"Calorías diarias objetivo: {int(round(kcal_total))} kcal",
            )
            y_pos -= 16

        # Info del cliente
        c.setFont(_FONT, 9)
        c.setFillColor(colors.black)
        cliente_nombre = getattr(cliente, 'nombre', '') or ''
        cliente_edad = getattr(cliente, 'edad', '') or ''
        cliente_peso = getattr(cliente, 'peso_kg', '') or ''
        cliente_obj = (getattr(cliente, 'objetivo', '') or '').capitalize()
        fecha_plan = datetime.now().strftime("%d %B %Y")

        info_str = (
            f"Cliente: {cliente_nombre}   Edad: {cliente_edad} años   "
            f"Peso: {cliente_peso} kg   Objetivo: {cliente_obj}   "
            f"Fecha: {fecha_plan}"
        )
        c.drawString(margin_x, y_pos, info_str)
        y_pos -= 20

        # Nota explicativa
        c.setFont(_FONT, 8)
        c.setFillColor(colors.HexColor("#666666"))
        c.drawString(
            margin_x, y_pos,
            "Este plan te ofrece OPCIONES flexibles. Elige UNA opción de cada categoría por comida.",
        )
        y_pos -= 12

        return y_pos - 10

    def _dibujar_seccion_macro(
        self, c, y: float, titulo: str,
        cantidad_objetivo: float, opciones: list,
        unidad_macro: str,
    ) -> float:
        """Dibuja una sección de macronutriente con sus opciones."""
        margin_x = 50

        # Título de sección
        c.setFont(_FONT, 10)
        c.setFillColor(colors.HexColor("#444444"))
        c.drawString(
            margin_x + 10, y,
            f"{titulo} (elige 1 opción — {cantidad_objetivo:.0f}g {unidad_macro}):",
        )
        y -= 14

        # Opciones
        c.setFont(_FONT, 9)
        c.setFillColor(colors.black)

        for idx, opcion in enumerate(opciones, 1):
            alimento = opcion['alimento'].replace('_', ' ').title()
            gramos = int(round(opcion['gramos']))
            equivalencia = opcion.get('equivalencia', '')
            macros = opcion['macros']

            texto = f"□ Opción {idx}: {gramos}g {alimento}"
            if equivalencia:
                texto += f" ({equivalencia})"

            c.drawString(margin_x + 25, y, texto)
            y -= 11

            # Macros detallados
            c.setFont(_FONT, 7)
            c.setFillColor(colors.HexColor("#666666"))
            macros_texto = (
                f"   → {macros['proteina']:.1f}g P | "
                f"{macros['carbs']:.1f}g C | "
                f"{macros['grasa']:.1f}g G | "
                f"{int(macros['kcal'])} kcal"
            )
            c.drawString(margin_x + 30, y, macros_texto)
            y -= 11

            c.setFont(_FONT, 9)
            c.setFillColor(colors.black)

        y -= 8
        return y

    def _dibujar_comida_con_opciones(
        self, c, y: float, nombre_comida: str, datos: Dict
    ) -> float:
        """Dibuja una comida completa con formato de opciones."""
        page_width = self.width
        margin_x = 50

        # Título de comida
        c.setFont(_FONT, 13)
        c.setFillColor(colors.HexColor("#2A3A7A"))
        kcal_obj = int(round(datos.get('kcal_objetivo', 0)))
        c.drawString(margin_x, y, f"{nombre_comida.upper()} — {kcal_obj} kcal objetivo")
        y -= 18

        # Línea separadora
        c.setStrokeColor(colors.HexColor("#2A3A7A"))
        c.setLineWidth(1.5)
        c.line(margin_x, y, page_width - margin_x, y)
        y -= 12

        # PROTEÍNAS
        if datos.get('proteinas', {}).get('opciones'):
            y = self._dibujar_seccion_macro(
                c, y, "PROTEÍNAS",
                datos['proteinas']['cantidad_objetivo'],
                datos['proteinas']['opciones'],
                "proteína",
            )

        # CARBOHIDRATOS
        _carbs_datos = datos.get('carbohidratos', {})
        if _carbs_datos.get('opciones'):
            y = self._dibujar_seccion_macro(
                c, y, "CARBOHIDRATOS",
                _carbs_datos['cantidad_objetivo'],
                _carbs_datos['opciones'],
                "carbohidratos",
            )
        else:
            c.setFont(_FONT, 10)
            c.setFillColor(colors.HexColor("#888888"))
            c.drawString(margin_x + 10, y, "CARBOHIDRATOS: No disponible para esta comida")
            y -= 14

        # GRASAS
        if datos.get('grasas', {}).get('opciones'):
            y = self._dibujar_seccion_macro(
                c, y, "GRASAS",
                datos['grasas']['cantidad_objetivo'],
                datos['grasas']['opciones'],
                "grasa",
            )

        # VEGETALES (fijos)
        if datos.get('vegetales'):
            c.setFont(_FONT, 10)
            c.setFillColor(colors.HexColor("#228B22"))
            c.drawString(margin_x + 10, y, "VEGETALES (siempre incluir):")
            y -= 14

            c.setFont(_FONT, 9)
            c.setFillColor(colors.black)
            for vegetal in datos['vegetales']:
                nombre = vegetal['alimento'].replace('_', ' ').title()
                gramos = int(round(vegetal['gramos']))
                c.drawString(margin_x + 25, y, f"+ {gramos}g {nombre}")
                y -= 13
            y -= 8

        # Nota educativa
        c.setFont(_FONT, 7)
        c.setFillColor(colors.HexColor("#666666"))
        nota = (
            "NOTA: Selecciona UNA opción de cada categoría. Los macros pueden variar "
            "ligeramente según tu elección, pero todas las combinaciones cumplen tu "
            "objetivo calórico."
        )
        wrapped = textwrap.wrap(nota, width=110)
        for line in wrapped:
            c.drawString(margin_x + 15, y, line)
            y -= 9

        y -= 15
        return y

    def _dibujar_instrucciones(self, c, y: float) -> float:
        """Dibuja sección de instrucciones generales."""
        margin_x = 50

        c.setFont(_FONT, 11)
        c.setFillColor(colors.HexColor("#2A3A7A"))
        c.drawString(margin_x, y, "INSTRUCCIONES DE USO")
        y -= 15

        c.setFont(_FONT, 8)
        c.setFillColor(colors.black)

        instrucciones = [
            "1. Por cada comida, selecciona UNA opción de cada categoría (proteínas, carbohidratos, grasas).",
            "2. SIEMPRE incluye los vegetales indicados (no son opcionales).",
            "3. Puedes variar tus opciones día a día según disponibilidad y preferencias.",
            "4. Pesa los alimentos en CRUDO antes de cocinar (excepto si se indica lo contrario).",
            "5. Las equivalencias son aproximadas (1 huevo ≈ 50g, 1 tortilla ≈ 30g, etc.).",
            "6. Si no tienes un alimento, elige otra opción de la misma categoría.",
            "7. Mantén 2-3 litros de agua diarios independientemente de las opciones elegidas.",
            "8. Consulta con tu entrenador si tienes dudas sobre alguna combinación.",
        ]

        for instruccion in instrucciones:
            wrapped = textwrap.wrap(instruccion, width=95)
            for line in wrapped:
                c.drawString(margin_x + 10, y, line)
                y -= 11

        y -= 10
        return y

    def _dibujar_disclaimer(self, c, y: float):
        """Disclaimer legal al pie de página."""
        disclaimer = (
            "AVISO IMPORTANTE: Este plan nutricional es una guía general basada en "
            "objetivos de entrenamiento y composición corporal. No constituye una "
            "consulta médica ni nutricional profesional. Si usted padece enfermedades "
            "crónicas, se recomienda consultar con un médico o nutriólogo certificado "
            "antes de seguir cualquier plan alimenticio."
        )

        margin_x = 50
        page_width = self.width

        y = 60
        c.setLineWidth(0.5)
        c.setStrokeColor(colors.lightgrey)
        c.line(margin_x, y, page_width - margin_x, y)
        y -= 10

        c.setFont(_FONT, 6)
        c.setFillColor(colors.gray)

        wrapped = textwrap.wrap(disclaimer, width=100)
        for line in wrapped:
            c.drawString(margin_x, y, line)
            y -= 8

    def generar(self, cliente, plan: Dict) -> str | None:
        """
        Genera PDF con plan de opciones.

        Args:
            cliente: ClienteEvaluacion
            plan: Dict con estructura de ConstructorPlanConOpciones

        Returns:
            Ruta del PDF generado, o None si hubo error
        """
        try:
            if plan.get('metadata', {}).get('tipo_plan') != 'opciones':
                raise ValueError("Plan no tiene estructura de opciones")

            c_pdf = canvas.Canvas(self.ruta_salida, pagesize=LETTER)
            _, page_height = letter

            comidas = ['desayuno', 'almuerzo', 'comida', 'cena']
            kcal_total = sum(
                plan.get(comida, {}).get('kcal_objetivo', 0)
                for comida in comidas
            )

            # Header
            y = self._dibujar_header(c_pdf, cliente, kcal_total)

            # Comidas
            for nombre_comida in comidas:
                if nombre_comida in plan:
                    if y < 250:
                        c_pdf.showPage()
                        y = page_height - 50

                    y = self._dibujar_comida_con_opciones(
                        c_pdf, y, nombre_comida, plan[nombre_comida]
                    )

            # Nueva página para instrucciones
            c_pdf.showPage()
            y = page_height - 80
            y = self._dibujar_instrucciones(c_pdf, y)

            self._dibujar_disclaimer(c_pdf, y)

            c_pdf.save()
            logger.info("[PDF OPCIONES] Generado: %s", self.ruta_salida)
            return self.ruta_salida

        except Exception as e:
            logger.error("[PDF OPCIONES] Error: %s", e, exc_info=True)
            return None

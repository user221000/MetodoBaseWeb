"""
Exportador de PDF para planes con opciones múltiples.

Genera PDFs profesionales mostrando opciones equivalentes por macronutriente
(1/3 proteínas, 1/3 carbohidratos, 1/3 grasas) que el cliente puede elegir.

Usa ReportLab Platypus para layout consistente con PDFGenerator (api/pdf_generator.py).
Acepta `config` dict para personalizar branding del gym (nombre, logo, colores, contacto).
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)

_PAGE_W, _PAGE_H = LETTER
_MARGIN = 1.5 * cm
_COLOR_WHITE = colors.white
_COLOR_GRAY  = colors.HexColor("#F3F4F6")
_COLOR_DARK  = colors.HexColor("#0F0F0F")
_COLOR_MIDNIGHT = colors.HexColor("#292524")
_COLOR_GOLD  = colors.HexColor("#E5B800")
_COLOR_MID   = colors.HexColor("#6B7280")
_COLOR_GRAY2 = colors.HexColor("#E5E5E5")


class GeneradorPDFConOpciones:
    """
    Generador de PDF para planes con opciones múltiples.

    Acepta un dict `config` con las mismas llaves que PDFGenerator:
        gym_nombre, gym_logo, gym_telefono, gym_direccion,
        gym_instagram, gym_facebook, gym_tiktok,
        color_primario, color_secundario
    """

    def __init__(self, ruta_salida: str, config: Optional[dict] = None):
        self.ruta_salida = ruta_salida
        self.config = {**self._default_config(), **(config or {})}
        self.styles = getSampleStyleSheet()
        self._build_styles()

    @staticmethod
    def _default_config() -> dict:
        _default_logo = Path(__file__).resolve().parent.parent / "static" / "img" / "logo_consultoria_hernandez.png"
        return {
            "gym_nombre":       "Método Base",
            "gym_logo":         str(_default_logo) if _default_logo.exists() else None,
            "gym_telefono":     "",
            "gym_direccion":    "",
            "gym_instagram":    "",
            "gym_facebook":     "",
            "gym_tiktok":       "",
            "color_primario":   "#E5B800",
            "color_secundario": "#292524",
        }

    # ── Public API ─────────────────────────────────────────────────────────────

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

            ruta = Path(self.ruta_salida)
            ruta.parent.mkdir(parents=True, exist_ok=True)

            doc = SimpleDocTemplate(
                str(ruta),
                pagesize=LETTER,
                leftMargin=_MARGIN,
                rightMargin=_MARGIN,
                topMargin=_MARGIN,
                bottomMargin=2 * cm,
            )

            story = []

            # Header con branding del gym
            story += self._build_header(cliente, plan)
            story.append(Spacer(1, 0.3 * cm))

            # Info del cliente
            story += self._build_client_card(cliente)
            story.append(Spacer(1, 0.3 * cm))

            # Resumen de macros
            story += self._build_macro_summary(cliente, plan)
            story.append(Spacer(1, 0.4 * cm))

            # Comidas con opciones
            comidas = ['desayuno', 'almuerzo', 'comida', 'cena']
            COMIDAS_LABELS = {
                'desayuno': 'Desayuno',
                'almuerzo': 'Colación matutina / Almuerzo',
                'comida':   'Comida principal',
                'cena':     'Cena',
            }
            for nombre_comida in comidas:
                if nombre_comida in plan:
                    story += self._build_comida_opciones(
                        COMIDAS_LABELS.get(nombre_comida, nombre_comida),
                        plan[nombre_comida],
                    )
                    story.append(Spacer(1, 0.3 * cm))

            # Instrucciones
            story += self._build_instrucciones()
            story.append(Spacer(1, 0.3 * cm))

            # Footer
            story += self._build_footer()

            doc.build(story, onFirstPage=self._draw_page_border,
                      onLaterPages=self._draw_page_border)
            logger.info("[PDF OPCIONES] Generado: %s", self.ruta_salida)
            return self.ruta_salida

        except Exception as e:
            logger.error("[PDF OPCIONES] Error: %s", e, exc_info=True)
            return None

    # ── Header ─────────────────────────────────────────────────────────────────

    def _build_header(self, cliente, plan: Dict) -> list:
        flowables = []
        gym_nombre    = self.config["gym_nombre"]
        gym_telefono  = self.config.get("gym_telefono", "")
        gym_dir       = self.config.get("gym_direccion", "")
        gym_instagram = self.config.get("gym_instagram", "")
        gym_facebook  = self.config.get("gym_facebook", "")
        gym_tiktok    = self.config.get("gym_tiktok", "")
        fecha_str     = datetime.now().strftime("%d/%m/%Y")
        logo_path     = self.config.get("gym_logo")
        usable_w      = _PAGE_W - 2 * _MARGIN
        _s = self.styles

        # ── Left block: gym name + contact + social ──
        info_parts = []
        info_parts.append(Paragraph(gym_nombre, _s["OPT_GymName"]))

        contact_lines = []
        if gym_dir:
            contact_lines.append(gym_dir)
        if gym_telefono:
            contact_lines.append(f"Tel: {gym_telefono}")
        if contact_lines:
            info_parts.append(Paragraph(" | ".join(contact_lines), _s["OPT_Contact"]))

        redes = []
        if gym_instagram:
            redes.append(f"@{gym_instagram}" if not gym_instagram.startswith("@") else gym_instagram)
        if gym_facebook:
            redes.append(f"FB: {gym_facebook}")
        if gym_tiktok:
            redes.append(f"TikTok: {gym_tiktok}")
        if redes:
            info_parts.append(Paragraph(" · ".join(redes), _s["OPT_Social"]))

        info_parts.append(Paragraph(f"Fecha: {fecha_str}", _s["OPT_Sub"]))

        info_tbl = Table([[p] for p in info_parts], colWidths=[None])
        info_tbl.setStyle(TableStyle([
            ("LEFTPADDING",  (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING",   (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 1),
        ]))

        # ── Right block: logo (standard bounding-box, aspect ratio preserved) ──
        if logo_path and Path(logo_path).exists():
            logo_w = 3.0 * cm
            logo_h = 2.2 * cm
            logo_img = Image(str(logo_path), width=logo_w, height=logo_h, kind="proportional")
            logo_img.hAlign = "RIGHT"
            logo_col_w = logo_w + 0.6 * cm
            header_tbl = Table(
                [[info_tbl, logo_img]],
                colWidths=[usable_w - logo_col_w, logo_col_w],
            )
            header_tbl.setStyle(TableStyle([
                ("VALIGN",       (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING",  (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING",   (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 0),
            ]))
            flowables.append(header_tbl)
        else:
            flowables.append(info_tbl)

        flowables.append(Spacer(1, 0.25 * cm))
        flowables.append(HRFlowable(width="100%", thickness=2.5, color=_COLOR_GOLD))
        flowables.append(Spacer(1, 0.3 * cm))
        flowables.append(
            Paragraph("Tu Plan Nutricional a la Medida", _s["OPT_Title"])
        )
        return flowables

    # ── Client card ────────────────────────────────────────────────────────────

    def _build_client_card(self, cliente) -> list:
        nombre    = getattr(cliente, "nombre", "—") or "—"
        edad      = f"{getattr(cliente, 'edad', '—')} años"
        sexo_raw  = getattr(cliente, "sexo", "") or ""
        sexo      = {"M": "Masculino", "F": "Femenino"}.get(sexo_raw.upper(), sexo_raw or "—")
        peso      = f"{getattr(cliente, 'peso_kg', '—')} kg"
        estatura  = f"{getattr(cliente, 'estatura_cm', '—')} cm"
        grasa     = getattr(cliente, "grasa_corporal_pct", None)
        grasa_str = f"{grasa}%" if grasa else "—"
        objetivo_map = {
            "deficit": "Déficit calórico",
            "mantenimiento": "Mantenimiento de peso",
            "superavit": "Superávit calórico",
        }
        objetivo  = objetivo_map.get(str(getattr(cliente, "objetivo", "")).lower(),
                                     str(getattr(cliente, "objetivo", "—")))
        nivel_map = {
            "nula": "Sedentario",
            "leve": "Leve (1-3 días/sem)",
            "moderada": "Moderada (3-5 días/sem)",
            "intensa": "Intensa (6-7 días/sem)",
        }
        nivel = nivel_map.get(str(getattr(cliente, "nivel_actividad", "")).lower(),
                              str(getattr(cliente, "nivel_actividad", "—")))

        _s = self.styles
        data = [
            [Paragraph("Información del Cliente", _s["OPT_CardTitle"]), "", "", ""],
            [Paragraph(f"<b>Nombre:</b> {nombre}", _s["OPT_Cell"]),
             Paragraph(f"<b>Edad:</b> {edad}",     _s["OPT_Cell"]),
             Paragraph(f"<b>Sexo:</b> {sexo}",     _s["OPT_Cell"]),
             Paragraph(f"<b>Peso:</b> {peso}",     _s["OPT_Cell"])],
            [Paragraph(f"<b>Estatura:</b> {estatura}", _s["OPT_Cell"]),
             Paragraph(f"<b>% Grasa:</b> {grasa_str}", _s["OPT_Cell"]),
             Paragraph(f"<b>Objetivo:</b> {objetivo}", _s["OPT_Cell"]),
             Paragraph(f"<b>Actividad:</b> {nivel}",   _s["OPT_Cell"])],
        ]
        usable_w = _PAGE_W - 2 * _MARGIN
        col_w    = usable_w / 4
        tbl = Table(data, colWidths=[col_w] * 4)
        tbl.setStyle(TableStyle([
            ("SPAN",            (0, 0), (3, 0)),
            ("BACKGROUND",      (0, 0), (3, 0), _COLOR_MIDNIGHT),
            ("TEXTCOLOR",       (0, 0), (3, 0), _COLOR_GOLD),
            ("FONTNAME",        (0, 0), (3, 0), "Helvetica-Bold"),
            ("FONTSIZE",        (0, 0), (3, 0), 9),
            ("TOPPADDING",      (0, 0), (3, 0), 5),
            ("BOTTOMPADDING",   (0, 0), (3, 0), 5),
            ("BACKGROUND",      (0, 1), (-1, -1), _COLOR_GRAY),
            ("ROWBACKGROUNDS",  (0, 1), (-1, -1), [_COLOR_GRAY, colors.white]),
            ("GRID",            (0, 0), (-1, -1), 0.4, _COLOR_GRAY2),
            ("TOPPADDING",      (0, 1), (-1, -1), 5),
            ("BOTTOMPADDING",   (0, 1), (-1, -1), 5),
            ("LEFTPADDING",     (0, 0), (-1, -1), 8),
        ]))
        result = [tbl]
        if getattr(cliente, "grasa_corporal_estimada", False):
            result.append(Paragraph(
                "Se usó 20% de grasa corporal porque no se informó el dato; no es una medición.",
                _s["OPT_Cell"],
            ))
        return result

    # ── Macro summary ──────────────────────────────────────────────────────────

    def _build_macro_summary(self, cliente, plan: Dict) -> list:
        tmb      = int(round(getattr(cliente, "tmb", 0) or 0))
        get_tot  = int(round(getattr(cliente, "get_total", 0) or 0))
        kcal_obj = int(round(getattr(cliente, "kcal_objetivo", 0) or 0))
        prot     = round(getattr(cliente, "proteina_g", 0) or 0, 1)
        carb     = round(getattr(cliente, "carbs_g", 0) or 0, 1)
        fat      = round(getattr(cliente, "grasa_g", 0) or 0, 1)

        _s = self.styles

        def _macro_cell(valor, label, bg_hex):
            bg = colors.HexColor(bg_hex)
            inner = Table(
                [[Paragraph(str(valor), _s["OPT_MacroNum"])],
                 [Paragraph(label,      _s["OPT_MacroLabel"])]],
                colWidths=[None],
            )
            inner.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, -1), bg),
                ("TEXTCOLOR",     (0, 0), (-1, -1), _COLOR_WHITE),
                ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING",    (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("ROUNDEDCORNERS", [4]),
            ]))
            return inner

        usable_w = _PAGE_W - 2 * _MARGIN
        cw = usable_w / 4

        cells = [
            _macro_cell(f"{kcal_obj}", "Calorías Objetivo", "#E5B800"),
            _macro_cell(f"{prot}g", "Proteína",            "#292524"),
            _macro_cell(f"{carb}g", "Carbohidratos",       "#292524"),
            _macro_cell(f"{fat}g", "Grasas",               "#292524"),
        ]
        tbl = Table([cells], colWidths=[cw] * 4)
        tbl.setStyle(TableStyle([
            ("LEFTPADDING",   (0, 0), (-1, -1), 3),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 3),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        return [
            Paragraph("Resumen Nutricional Diario", _s["OPT_SectionTitle"]),
            Spacer(1, 0.2 * cm),
            tbl,
        ]

    # ── Meal with options ──────────────────────────────────────────────────────

    def _build_comida_opciones(self, label: str, datos: Dict) -> list:
        _s = self.styles
        usable_w = _PAGE_W - 2 * _MARGIN
        kcal_obj = int(round(datos.get('kcal_objetivo', 0)))
        flowables = []

        # Meal header
        header_text = f"{label}  —  {kcal_obj} kcal objetivo"
        header_tbl = Table(
            [[Paragraph(header_text, _s["OPT_MealHeader"])]],
            colWidths=[usable_w],
        )
        header_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), _COLOR_MIDNIGHT),
            ("TEXTCOLOR",     (0, 0), (-1, -1), _COLOR_GOLD),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ]))
        flowables.append(header_tbl)

        # Build rows for each macro group
        macro_sections = [
            ("PROTEÍNAS",      datos.get("proteinas", {}),      "#292524"),
            ("CARBOHIDRATOS",  datos.get("carbohidratos", {}),  "#292524"),
            ("GRASAS",         datos.get("grasas", {}),         "#292524"),
        ]

        col_widths = [usable_w * 0.08, usable_w * 0.42, usable_w * 0.15, usable_w * 0.35]

        for macro_name, macro_data, accent_hex in macro_sections:
            opciones = macro_data.get("opciones", [])
            if not opciones:
                continue

            accent = colors.HexColor(accent_hex)

            # Macro section header
            macro_header = Table(
                [[Paragraph(
                    f"{macro_name}  (elige 1)",
                    _s["OPT_MacroSectionH"],
                ), "", "", ""]],
                colWidths=col_widths,
            )
            macro_header.setStyle(TableStyle([
                ("SPAN",          (0, 0), (3, 0)),
                ("BACKGROUND",    (0, 0), (-1, -1), accent),
                ("TEXTCOLOR",     (0, 0), (-1, -1), _COLOR_WHITE),
                ("TOPPADDING",    (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ]))
            flowables.append(macro_header)

            # Option rows
            rows = []
            for idx, opcion in enumerate(opciones, 1):
                alimento = opcion.get('alimento', '').replace('_', ' ').title()
                gramos = int(round(opcion.get('gramos', 0)))
                equiv = opcion.get('equivalencia', '')
                macros = opcion.get('macros', {})

                nombre_col = f"{alimento}"
                if equiv:
                    nombre_col += f"  <i>({equiv})</i>"

                macros_txt = (
                    f"P:{macros.get('proteina', 0):.0f}g  "
                    f"C:{macros.get('carbs', 0):.0f}g  "
                    f"G:{macros.get('grasa', 0):.0f}g  "
                    f"| {int(macros.get('kcal', 0))} kcal"
                )

                rows.append([
                    Paragraph(f"<b>Op. {idx}</b>", _s["OPT_CellC"]),
                    Paragraph(nombre_col, _s["OPT_Cell"]),
                    Paragraph(f"<b>{gramos} g</b>", _s["OPT_CellC"]),
                    Paragraph(macros_txt, _s["OPT_CellSmall"]),
                ])

            if rows:
                opt_tbl = Table(rows, colWidths=col_widths)
                opt_tbl.setStyle(TableStyle([
                    ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, _COLOR_GRAY]),
                    ("GRID",           (0, 0), (-1, -1), 0.3, _COLOR_GRAY2),
                    ("TOPPADDING",     (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING",  (0, 0), (-1, -1), 3),
                    ("LEFTPADDING",    (0, 0), (-1, -1), 6),
                    ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
                ]))
                flowables.append(opt_tbl)

        # Vegetales (siempre incluir)
        vegetales = datos.get("vegetales", [])
        if vegetales:
            veg_header = Table(
                [[Paragraph("VEGETALES (siempre incluir)", _s["OPT_MacroSectionH"]), "", "", ""]],
                colWidths=col_widths,
            )
            veg_header.setStyle(TableStyle([
                ("SPAN",          (0, 0), (3, 0)),
                ("BACKGROUND",    (0, 0), (-1, -1), _COLOR_GOLD),
                ("TEXTCOLOR",     (0, 0), (-1, -1), _COLOR_DARK),
                ("TOPPADDING",    (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ]))
            flowables.append(veg_header)

            veg_rows = []
            for veg in vegetales:
                nombre = veg.get('alimento', '').replace('_', ' ').title()
                gramos = int(round(veg.get('gramos', 0)))
                veg_rows.append([
                    Paragraph("✓", _s["OPT_CellC"]),
                    Paragraph(nombre, _s["OPT_Cell"]),
                    Paragraph(f"<b>{gramos} g</b>", _s["OPT_CellC"]),
                    Paragraph("", _s["OPT_Cell"]),
                ])
            if veg_rows:
                veg_tbl = Table(veg_rows, colWidths=col_widths)
                veg_tbl.setStyle(TableStyle([
                    ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#FFFDE7")),
                    ("GRID",          (0, 0), (-1, -1), 0.3, _COLOR_GRAY2),
                    ("TOPPADDING",    (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("LEFTPADDING",   (0, 0), (-1, -1), 6),
                ]))
                flowables.append(veg_tbl)

        # Nota educativa
        flowables.append(Spacer(1, 0.15 * cm))
        flowables.append(Paragraph(
            "<i>Elige una opción de cada grupo y conserva las verduras y las cantidades indicadas. "
            "El cálculo usa gramos del estado de preparación que figura en cada alimento.</i>",
            _s["OPT_Note"],
        ))

        return flowables

    # ── Instructions ───────────────────────────────────────────────────────────

    def _build_instrucciones(self) -> list:
        _s = self.styles
        usable_w = _PAGE_W - 2 * _MARGIN

        instrucciones = [
            "Por cada comida, selecciona UNA opción de cada categoría (proteínas, carbohidratos, grasas).",
            "SIEMPRE incluye los vegetales indicados (no son opcionales).",
            "Puedes variar tus opciones día a día según disponibilidad y preferencias.",
            "Pesa en gramos del estado indicado: crudo, cocido o escurrido. Si falta el estado, confírmalo con tu profesional.",
            "Las equivalencias son aproximadas (1 huevo ≈ 50g, 1 tortilla ≈ 30g, etc.).",
            "Si no tienes un alimento, elige otra opción de la misma categoría.",
            "Adapta tu hidratación a tus necesidades y a la orientación de tu profesional de salud.",
            "Consulta con tu entrenador si tienes dudas sobre alguna combinación.",
        ]

        rows = [[Paragraph("Instrucciones de Uso", _s["OPT_CardTitle"]), ""]]
        for i, instruccion in enumerate(instrucciones, 1):
            rows.append([
                Paragraph(f"<b>{i}.</b>", _s["OPT_CellC"]),
                Paragraph(instruccion, _s["OPT_Cell"]),
            ])

        tbl = Table(rows, colWidths=[usable_w * 0.06, usable_w * 0.94])
        tbl.setStyle(TableStyle([
            ("SPAN",          (0, 0), (1, 0)),
            ("BACKGROUND",    (0, 0), (1, 0), _COLOR_MIDNIGHT),
            ("TEXTCOLOR",     (0, 0), (1, 0), _COLOR_GOLD),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _COLOR_GRAY]),
            ("GRID",          (0, 0), (-1, -1), 0.3, _COLOR_GRAY2),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ]))
        return [tbl]

    # ── Footer ─────────────────────────────────────────────────────────────────

    def _build_footer(self) -> list:
        _s = self.styles
        disclaimer = (
            "AVISO: Este plan es una guía general basada en objetivos de entrenamiento y composición corporal. "
            "No constituye consulta médica ni nutricional profesional. Ante condiciones de salud crónicas, "
            "consulte con un médico o nutriólogo certificado antes de seguir cualquier plan alimenticio."
        )
        return [
            HRFlowable(width="100%", thickness=0.5, color=_COLOR_GRAY2),
            Spacer(1, 0.15 * cm),
            Paragraph(
                f"Generado con <b>Método Base</b> · {datetime.now().strftime('%d/%m/%Y')}",
                _s["OPT_Footer"],
            ),
            Spacer(1, 0.1 * cm),
            Paragraph(disclaimer, _s["OPT_Disclaimer"]),
        ]

    # ── Page border ────────────────────────────────────────────────────────────

    def _draw_page_border(self, canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#E5E5E5"))
        canvas.setLineWidth(0.4)
        x0 = _MARGIN * 0.7
        y0 = _MARGIN * 0.7
        w  = _PAGE_W - _MARGIN * 1.4
        h  = _PAGE_H - _MARGIN * 1.4
        canvas.rect(x0, y0, w, h)
        # Gold accent line at top
        canvas.setStrokeColor(colors.HexColor("#E5B800"))
        canvas.setLineWidth(2.5)
        canvas.line(x0, y0 + h, x0 + w, y0 + h)
        canvas.restoreState()

    # ── Styles ─────────────────────────────────────────────────────────────────

    def _build_styles(self) -> None:
        add = self.styles.add

        add(ParagraphStyle("OPT_GymName",     parent=self.styles["Normal"],
                           fontSize=16, fontName="Helvetica-Bold",
                           textColor=_COLOR_DARK, leading=20))
        add(ParagraphStyle("OPT_Contact",     parent=self.styles["Normal"],
                           fontSize=8, textColor=_COLOR_DARK, leading=11))
        add(ParagraphStyle("OPT_Social",      parent=self.styles["Normal"],
                           fontSize=7.5, textColor=_COLOR_GOLD,
                           fontName="Helvetica-Bold", leading=10))
        add(ParagraphStyle("OPT_Sub",         parent=self.styles["Normal"],
                           fontSize=7.5, textColor=_COLOR_MID, leading=10))
        add(ParagraphStyle("OPT_Title",       parent=self.styles["Normal"],
                           fontSize=16, fontName="Helvetica-Bold",
                           textColor=_COLOR_GOLD, alignment=TA_CENTER,
                           spaceAfter=2))
        add(ParagraphStyle("OPT_SectionTitle", parent=self.styles["Normal"],
                           fontSize=10, fontName="Helvetica-Bold",
                           textColor=_COLOR_DARK, spaceBefore=4))
        add(ParagraphStyle("OPT_CardTitle",   parent=self.styles["Normal"],
                           fontSize=9, fontName="Helvetica-Bold",
                           textColor=_COLOR_GOLD))
        add(ParagraphStyle("OPT_Cell",        parent=self.styles["Normal"],
                           fontSize=8, leading=11))
        add(ParagraphStyle("OPT_CellC",       parent=self.styles["Normal"],
                           fontSize=8, leading=11, alignment=TA_CENTER))
        add(ParagraphStyle("OPT_CellSmall",   parent=self.styles["Normal"],
                           fontSize=7, leading=10, textColor=_COLOR_MID))
        add(ParagraphStyle("OPT_MealHeader",  parent=self.styles["Normal"],
                           fontSize=9, fontName="Helvetica-Bold",
                           textColor=_COLOR_WHITE))
        add(ParagraphStyle("OPT_MacroSectionH", parent=self.styles["Normal"],
                           fontSize=8, fontName="Helvetica-Bold",
                           textColor=_COLOR_WHITE))
        add(ParagraphStyle("OPT_MacroNum",    parent=self.styles["Normal"],
                           fontSize=14, fontName="Helvetica-Bold",
                           textColor=_COLOR_WHITE, alignment=TA_CENTER))
        add(ParagraphStyle("OPT_MacroLabel",  parent=self.styles["Normal"],
                           fontSize=6.5, textColor=_COLOR_WHITE,
                           alignment=TA_CENTER))
        add(ParagraphStyle("OPT_Note",        parent=self.styles["Normal"],
                           fontSize=7, textColor=_COLOR_MID, leading=9))
        add(ParagraphStyle("OPT_Footer",      parent=self.styles["Normal"],
                           fontSize=7.5, alignment=TA_CENTER,
                           textColor=_COLOR_MID))
        add(ParagraphStyle("OPT_Disclaimer",  parent=self.styles["Normal"],
                           fontSize=6.5, textColor=_COLOR_MID, leading=9))

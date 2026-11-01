"""
api/pdf_generator.py — Generador de PDFs profesionales con ReportLab Platypus.

Premium dark-neon theme (black/yellow/purple) adaptado para impresión.
Logo normalizado: cualquier forma (oval, rectangular, cuadrada) se ajusta
a un bounding-box estándar con preserveAspectRatio para que el header
siempre tenga dimensiones consistentes.

Uso desde routes/services:
    from api.pdf_generator import PDFGenerator
    gen = PDFGenerator(config={"gym_nombre": "Fit Club GDL", ...})
    ruta = gen.generar_plan(datos_plan, ruta_salida=Path("/tmp/plan.pdf"))
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

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

# ── Paleta premium (black · gold · midnight) — print-adapted ─────────────────
_BLACK       = colors.HexColor("#0F0F0F")
_DARK        = colors.HexColor("#292524")        # warm charcoal
_GOLD        = colors.HexColor("#E5B800")        # golden yellow — primary accent
_GOLD_SOFT   = colors.HexColor("#FFF8E1")        # warm card bg
_GRAY_50     = colors.HexColor("#FAFAFA")
_GRAY_100    = colors.HexColor("#F5F5F5")
_GRAY_200    = colors.HexColor("#E5E5E5")
_GRAY_400    = colors.HexColor("#A3A3A3")
_GRAY_600    = colors.HexColor("#525252")
_WHITE       = colors.white

# Logo standard bounding-box (any shape normalizes into this)
_LOGO_MAX_W = 3.0 * cm
_LOGO_MAX_H = 2.2 * cm

_PAGE_W, _PAGE_H = LETTER
_MARGIN = 1.5 * cm


class PDFGenerator:
    """
    Generador de PDFs con branding personalizado por gimnasio.
    Tema premium: black · gold · warm charcoal, minimalista para impresión.
    """

    def __init__(self, config: Optional[dict] = None):
        self.config = {**self._default_config(), **(config or {})}
        self.styles = getSampleStyleSheet()
        self._build_styles()

    # ── Public API ─────────────────────────────────────────────────────────────

    def generar_plan(self, datos_plan: dict, ruta_salida: Path) -> Path:
        """
        Genera un PDF del plan nutricional en `ruta_salida`.

        Args:
            datos_plan: {
                'cliente': {nombre, edad, sexo, peso_kg, estatura_cm,
                            grasa_corporal_pct, nivel_actividad, objetivo},
                'macros':  {tmb, get_total, kcal_objetivo, proteina_g,
                            carbs_g, grasa_g},
                'plan': {
                    'desayuno': {'kcal_real': float, 'alimentos': {str: float}},
                    'almuerzo': ..., 'comida': ..., 'cena': ...
                },
                'fecha_generacion': datetime   (opcional)
            }
            ruta_salida: Path donde se escribirá el PDF.

        Returns:
            Path confirmada del PDF generado.

        Raises:
            Exception propagada si ReportLab falla.
        """
        ruta_salida = Path(ruta_salida)
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(
            str(ruta_salida),
            pagesize=LETTER,
            leftMargin=_MARGIN,
            rightMargin=_MARGIN,
            topMargin=_MARGIN,
            bottomMargin=2 * cm,
        )

        story = []
        story += self._build_header(datos_plan)
        story.append(Spacer(1, 0.4 * cm))
        story += self._build_client_card(datos_plan.get("cliente", {}))
        story.append(Spacer(1, 0.4 * cm))
        story += self._build_macro_summary(datos_plan.get("macros", {}))
        story.append(Spacer(1, 0.5 * cm))
        story += self._build_meal_plan(datos_plan.get("plan", {}))
        story.append(Spacer(1, 0.4 * cm))
        story += self._build_recommendations()
        story.append(Spacer(1, 0.4 * cm))
        story += self._build_footer_flowable()

        doc.build(story, onFirstPage=self._draw_page_border,
                  onLaterPages=self._draw_page_border)
        logger.info("PDF generado: %s", ruta_salida)
        return ruta_salida

    # ── Sección: Header ────────────────────────────────────────────────────────

    def _build_logo_image(self, logo_path: str) -> Optional[Image]:
        """Normalize any logo shape to a standard bounding-box."""
        p = Path(logo_path)
        if not p.exists():
            return None
        try:
            img = Image(
                str(p),
                width=_LOGO_MAX_W,
                height=_LOGO_MAX_H,
                kind="proportional",          # preserves aspect ratio
            )
            img.hAlign = "RIGHT"
            return img
        except Exception:
            logger.warning("No se pudo cargar logo: %s", logo_path)
            return None

    def _build_header(self, datos_plan: dict) -> list:
        flowables = []
        gym_nombre    = self.config["gym_nombre"]
        gym_telefono  = self.config.get("gym_telefono", "")
        gym_dir       = self.config.get("gym_direccion", "")
        gym_instagram = self.config.get("gym_instagram", "")
        gym_facebook  = self.config.get("gym_facebook", "")
        gym_tiktok    = self.config.get("gym_tiktok", "")
        fecha = datos_plan.get("fecha_generacion") or datetime.now()
        if isinstance(fecha, str):
            fecha_str = fecha[:10]
        else:
            fecha_str = fecha.strftime("%d/%m/%Y")

        logo_path = self.config.get("gym_logo")
        usable_w = _PAGE_W - 2 * _MARGIN
        _s = self.styles

        # ── Left block: gym identity (hierarchical) ──
        info_parts = []
        info_parts.append(Paragraph(gym_nombre, _s["PDF_GymName"]))

        if gym_dir:
            info_parts.append(Paragraph(gym_dir, _s["PDF_Contact"]))
        if gym_telefono:
            info_parts.append(Paragraph(gym_telefono, _s["PDF_Contact"]))

        # Social media line
        redes = []
        if gym_instagram:
            redes.append(f"@{gym_instagram}" if not gym_instagram.startswith("@") else gym_instagram)
        if gym_facebook:
            redes.append(gym_facebook)
        if gym_tiktok:
            redes.append(gym_tiktok)
        if redes:
            info_parts.append(Paragraph(" · ".join(redes), _s["PDF_Social"]))

        info_parts.append(Paragraph(fecha_str, _s["PDF_Sub"]))

        info_tbl = Table([[p] for p in info_parts], colWidths=[None])
        info_tbl.setStyle(TableStyle([
            ("LEFTPADDING",  (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING",   (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 1),
        ]))

        # ── Right block: logo (normalized to standard bounding-box) ──
        logo_img = self._build_logo_image(logo_path) if logo_path else None

        if logo_img:
            logo_col_w = _LOGO_MAX_W + 0.6 * cm
            header_tbl = Table(
                [[info_tbl, logo_img]],
                colWidths=[usable_w - logo_col_w, logo_col_w],
            )
            header_tbl.setStyle(TableStyle([
                ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING",  (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING",   (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 0),
            ]))
            flowables.append(header_tbl)
        else:
            flowables.append(info_tbl)

        # ── Gold accent line ──
        flowables.append(Spacer(1, 0.2 * cm))
        flowables.append(HRFlowable(width="100%", thickness=2, color=_GOLD))
        flowables.append(Spacer(1, 0.35 * cm))

        # ── Tagline ──
        flowables.append(
            Paragraph(
                "Tu plan nutricional personalizado, ¡Disfrútalo!",
                _s["PDF_Tagline"],
            )
        )
        return flowables

    # ── Sección: Tarjeta cliente ───────────────────────────────────────────────

    def _build_client_card(self, cliente: dict) -> list:
        nombre    = cliente.get("nombre", "—")
        edad      = f"{cliente.get('edad', '—')} años"
        sexo_raw  = cliente.get("sexo") or ""
        sexo      = {"M": "Masculino", "F": "Femenino"}.get(sexo_raw.upper(), sexo_raw or "—")
        peso      = f"{cliente.get('peso_kg', '—')} kg"
        estatura  = f"{cliente.get('estatura_cm', '—')} cm"
        grasa     = cliente.get("grasa_corporal_pct")
        grasa_str = f"{grasa}%" if grasa else "N/E"
        objetivo_map = {
            "deficit": "Déficit calórico",
            "perdida_grasa": "Pérdida de grasa",
            "mantenimiento": "Mantenimiento",
            "superavit": "Superávit calórico",
            "ganancia_muscular": "Ganancia muscular",
            "rendimiento": "Rendimiento",
            "salud_general": "Salud general",
        }
        objetivo  = objetivo_map.get(str(cliente.get("objetivo", "")).lower(), str(cliente.get("objetivo", "—")))
        nivel_map = {
            "nula": "Sedentario",
            "sedentario": "Sedentario",
            "leve": "Leve (1-3 días/sem)",
            "ligero": "Ligero (1-3 días/sem)",
            "moderada": "Moderada (3-5 días/sem)",
            "moderado": "Moderado (3-5 días/sem)",
            "intensa": "Intensa (6-7 días/sem)",
            "activo": "Activo (6-7 días/sem)",
            "muy_activo": "Muy activo (atleta)",
        }
        nivel = nivel_map.get(str(cliente.get("nivel_actividad", "")).lower(), str(cliente.get("nivel_actividad", "—")))

        _s = self.styles
        data = [
            [Paragraph("Información del Cliente", _s["PDF_CardTitle"]), "", "", ""],
            [Paragraph(f"<b>Nombre:</b> {nombre}", _s["PDF_Cell"]),
             Paragraph(f"<b>Edad:</b> {edad}",     _s["PDF_Cell"]),
             Paragraph(f"<b>Sexo:</b> {sexo}",     _s["PDF_Cell"]),
             Paragraph(f"<b>Peso:</b> {peso}",     _s["PDF_Cell"])],
            [Paragraph(f"<b>Estatura:</b> {estatura}", _s["PDF_Cell"]),
             Paragraph(f"<b>% Grasa:</b> {grasa_str}", _s["PDF_Cell"]),
             Paragraph(f"<b>Objetivo:</b> {objetivo}", _s["PDF_Cell"]),
             Paragraph(f"<b>Actividad:</b> {nivel}",   _s["PDF_Cell"])],
        ]
        usable_w = _PAGE_W - 2 * _MARGIN
        col_w    = usable_w / 4

        tbl = Table(data, colWidths=[col_w] * 4)
        tbl.setStyle(TableStyle([
            ("SPAN",            (0, 0), (3, 0)),
            ("BACKGROUND",      (0, 0), (3, 0), _DARK),
            ("TEXTCOLOR",       (0, 0), (3, 0), _GOLD),
            ("FONTNAME",        (0, 0), (3, 0), "Helvetica-Bold"),
            ("FONTSIZE",        (0, 0), (3, 0), 9),
            ("TOPPADDING",      (0, 0), (3, 0), 6),
            ("BOTTOMPADDING",   (0, 0), (3, 0), 6),
            ("BACKGROUND",      (0, 1), (-1, -1), _GRAY_50),
            ("ROWBACKGROUNDS",  (0, 1), (-1, -1), [_GRAY_50, _WHITE]),
            ("GRID",            (0, 0), (-1, -1), 0.4, _GRAY_200),
            ("TOPPADDING",      (0, 1), (-1, -1), 5),
            ("BOTTOMPADDING",   (0, 1), (-1, -1), 5),
            ("LEFTPADDING",     (0, 0), (-1, -1), 8),
        ]))
        result = [tbl]
        if cliente.get("grasa_corporal_estimada"):
            result.append(Paragraph(
                "Se usó 20% de grasa corporal porque no se informó el dato; no es una medición.",
                _s["PDF_Cell"],
            ))
        return result

    # ── Sección: Resumen de macros ─────────────────────────────────────────────

    def _build_macro_summary(self, macros: dict) -> list:
        if not macros:
            return []

        kcal_obj = int(round(macros.get("kcal_objetivo", 0)))
        prot     = round(macros.get("proteina_g", 0), 1)
        carb     = round(macros.get("carbs_g", 0), 1)
        fat      = round(macros.get("grasa_g", 0), 1)

        _s = self.styles

        def _macro_cell(valor, label, bg_color):
            inner = Table(
                [[Paragraph(str(valor), _s["PDF_MacroNum"])],
                 [Paragraph(label,      _s["PDF_MacroLabel"])]],
                colWidths=[None],
            )
            inner.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, -1), bg_color),
                ("TEXTCOLOR",     (0, 0), (-1, -1), _WHITE),
                ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING",    (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("ROUNDEDCORNERS", [4]),
            ]))
            return inner

        usable_w = _PAGE_W - 2 * _MARGIN
        cw       = usable_w / 4

        cells = [
            _macro_cell(f"{kcal_obj}","Calorías Objetivo", _GOLD),
            _macro_cell(f"{prot}g",   "Proteína",          _DARK),
            _macro_cell(f"{carb}g",   "Carbohidratos",     _DARK),
            _macro_cell(f"{fat}g",    "Grasas",            _DARK),
        ]
        tbl = Table([cells], colWidths=[cw] * 4)
        tbl.setStyle(TableStyle([
            ("LEFTPADDING",   (0, 0), (-1, -1), 3),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 3),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        return [
            Paragraph("Resumen Nutricional Diario", self.styles["PDF_SectionTitle"]),
            Spacer(1, 0.2 * cm),
            tbl,
        ]

    # ── Sección: Plan de comidas ───────────────────────────────────────────────

    def _build_meal_plan(self, plan: dict) -> list:
        if not plan:
            return []

        COMIDAS_ORDER = [
            ("desayuno",  "Desayuno"),
            ("almuerzo",  "Colación matutina / Almuerzo"),
            ("comida",    "Comida principal"),
            ("cena",      "Cena"),
        ]

        _s = self.styles
        flowables = [
            Paragraph("Plan de Alimentación", _s["PDF_SectionTitle"]),
            Spacer(1, 0.2 * cm),
        ]

        usable_w = _PAGE_W - 2 * _MARGIN
        cols     = [usable_w * 0.40, usable_w * 0.30, usable_w * 0.15, usable_w * 0.15]

        for key, label in COMIDAS_ORDER:
            if key not in plan:
                continue
            comida     = plan[key]
            alimentos  = comida.get("alimentos", {})
            kcal_real  = int(round(comida.get("kcal_real", 0)))

            header_row = [
                Paragraph(label, _s["PDF_MealHeader"]),
                Paragraph("Porción (g)", _s["PDF_MealHeaderC"]),
                Paragraph("Kcal est.", _s["PDF_MealHeaderC"]),
                Paragraph("", _s["PDF_MealHeader"]),
            ]

            rows = [header_row]
            for alimento, gramos in alimentos.items():
                nombre_fmt = alimento.replace("_", " ").title()
                gramos_int = int(round(gramos))
                rows.append([
                    Paragraph(nombre_fmt, _s["PDF_Cell"]),
                    Paragraph(f"{gramos_int} g",  _s["PDF_CellC"]),
                    Paragraph("",                  _s["PDF_CellC"]),
                    Paragraph("",                  _s["PDF_CellC"]),
                ])

            rows.append([
                Paragraph("<b>Total comida</b>", _s["PDF_CellBold"]),
                Paragraph("",        _s["PDF_CellC"]),
                Paragraph(f"<b>{kcal_real} kcal</b>", _s["PDF_CellCBold"]),
                Paragraph("",        _s["PDF_CellC"]),
            ])

            tbl = Table(rows, colWidths=cols)
            tbl.setStyle(TableStyle([
                ("BACKGROUND",     (0, 0), (-1, 0), _DARK),
                ("TEXTCOLOR",      (0, 0), (-1, 0), _GOLD),
                ("FONTNAME",       (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE",       (0, 0), (-1, 0), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -2), [_WHITE, _GRAY_50]),
                ("BACKGROUND",     (0, -1), (-1, -1), _GOLD_SOFT),
                ("GRID",           (0, 0), (-1, -1), 0.3, _GRAY_200),
                ("TOPPADDING",     (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING",  (0, 0), (-1, -1), 4),
                ("LEFTPADDING",    (0, 0), (-1, -1), 6),
                ("SPAN",           (0, -1), (1, -1)),
            ]))
            flowables.append(KeepTogether([tbl, Spacer(1, 0.4 * cm)]))

        return flowables

    # ── Sección: Recomendaciones ───────────────────────────────────────────────

    def _build_recommendations(self) -> list:
        tips = [
            ("Cocción", "Utiliza aceite en aerosol (spray) para controlar la cantidad de grasa."),
            ("Medidas", "Las tazas y cucharas deben ser medidas estándar y rasas."),
            ("Pesaje", "Usa gramos del estado indicado: crudo, cocido o escurrido. Si falta el estado, confírmalo con tu profesional antes de pesar."),
            ("Hidratación", "Adapta tu consumo de agua a tus necesidades y a la orientación de tu profesional de salud."),
            ("Extras", "Los alimentos e ingredientes adicionales cambian el cálculo del menú. Revisa sus porciones y restricciones."),
        ]
        _s = self.styles
        rows = [[Paragraph("Recomendaciones", _s["PDF_CardTitle"]), ""]]
        for titulo, texto in tips:
            rows.append([
                Paragraph(f"<b>{titulo}</b>", _s["PDF_Cell"]),
                Paragraph(texto, _s["PDF_Cell"]),
            ])

        usable_w = _PAGE_W - 2 * _MARGIN
        tbl = Table(rows, colWidths=[usable_w * 0.18, usable_w * 0.82])
        tbl.setStyle(TableStyle([
            ("SPAN",          (0, 0), (1, 0)),
            ("BACKGROUND",    (0, 0), (1, 0), _DARK),
            ("TEXTCOLOR",     (0, 0), (1, 0), _GOLD),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_WHITE, _GRAY_50]),
            ("GRID",          (0, 0), (-1, -1), 0.3, _GRAY_200),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ]))
        return [tbl]

    # ── Footer flowable ────────────────────────────────────────────────────────

    def _build_footer_flowable(self) -> list:
        disclaimer = (
            "AVISO: Este plan es una guía general basada en objetivos de entrenamiento y composición corporal. "
            "No constituye consulta médica ni nutricional profesional. Ante condiciones de salud crónicas, "
            "consulte con un médico o nutriólogo certificado antes de seguir cualquier plan alimenticio."
        )
        _s = self.styles
        return [
            HRFlowable(width="100%", thickness=0.5, color=_GRAY_200),
            Spacer(1, 0.15 * cm),
            Paragraph(
                f"Generado con <b>Método Base</b> · {datetime.now().strftime('%d/%m/%Y')}",
                _s["PDF_Footer"],
            ),
            Spacer(1, 0.1 * cm),
            Paragraph(disclaimer, _s["PDF_Disclaimer"]),
        ]

    # ── Decoración de página ───────────────────────────────────────────────────

    def _draw_page_border(self, canvas, doc):
        """Borde sutil con acento dorado superior."""
        canvas.saveState()
        # Thin outer border
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

    # ── Estilos ────────────────────────────────────────────────────────────────

    def _build_styles(self) -> None:
        add = self.styles.add

        add(ParagraphStyle("PDF_GymName",     parent=self.styles["Normal"],
                           fontSize=15, fontName="Helvetica-Bold",
                           textColor=_DARK, leading=19))
        add(ParagraphStyle("PDF_Contact",     parent=self.styles["Normal"],
                           fontSize=8, textColor=_GRAY_600, leading=11))
        add(ParagraphStyle("PDF_Social",      parent=self.styles["Normal"],
                           fontSize=7.5, textColor=_GOLD,
                           fontName="Helvetica-Bold", leading=10))
        add(ParagraphStyle("PDF_Sub",         parent=self.styles["Normal"],
                           fontSize=7.5, textColor=_GRAY_400, leading=10))
        add(ParagraphStyle("PDF_SmallRight",  parent=self.styles["Normal"],
                           fontSize=8, alignment=TA_RIGHT, textColor=_GRAY_400))
        add(ParagraphStyle("PDF_Tagline",     parent=self.styles["Normal"],
                           fontSize=12, fontName="Helvetica-BoldOblique",
                           textColor=_DARK, alignment=TA_CENTER,
                           spaceAfter=2))
        add(ParagraphStyle("PDF_Title",       parent=self.styles["Normal"],
                           fontSize=16, fontName="Helvetica-Bold",
                           textColor=_GOLD, alignment=TA_CENTER,
                           spaceAfter=2))
        add(ParagraphStyle("PDF_SectionTitle", parent=self.styles["Normal"],
                           fontSize=10, fontName="Helvetica-Bold",
                           textColor=_DARK, spaceBefore=4))
        add(ParagraphStyle("PDF_CardTitle",   parent=self.styles["Normal"],
                           fontSize=9, fontName="Helvetica-Bold",
                           textColor=_GOLD))
        add(ParagraphStyle("PDF_Cell",        parent=self.styles["Normal"],
                           fontSize=8, leading=11, textColor=_BLACK))
        add(ParagraphStyle("PDF_CellBold",    parent=self.styles["Normal"],
                           fontSize=8, fontName="Helvetica-Bold",
                           leading=11, textColor=_BLACK))
        add(ParagraphStyle("PDF_CellC",       parent=self.styles["Normal"],
                           fontSize=8, leading=11, alignment=TA_CENTER,
                           textColor=_BLACK))
        add(ParagraphStyle("PDF_CellCBold",   parent=self.styles["Normal"],
                           fontSize=8, fontName="Helvetica-Bold",
                           leading=11, alignment=TA_CENTER, textColor=_BLACK))
        add(ParagraphStyle("PDF_MealHeader",  parent=self.styles["Normal"],
                           fontSize=8.5, fontName="Helvetica-Bold",
                           textColor=_GOLD))
        add(ParagraphStyle("PDF_MealHeaderC", parent=self.styles["Normal"],
                           fontSize=8.5, fontName="Helvetica-Bold",
                           textColor=_GOLD, alignment=TA_CENTER))
        add(ParagraphStyle("PDF_MacroNum",    parent=self.styles["Normal"],
                           fontSize=14, fontName="Helvetica-Bold",
                           textColor=_WHITE, alignment=TA_CENTER))
        add(ParagraphStyle("PDF_MacroLabel",  parent=self.styles["Normal"],
                           fontSize=6.5, textColor=_WHITE, alignment=TA_CENTER))
        add(ParagraphStyle("PDF_Footer",      parent=self.styles["Normal"],
                           fontSize=7.5, alignment=TA_CENTER, textColor=_GRAY_400))
        add(ParagraphStyle("PDF_Disclaimer",  parent=self.styles["Normal"],
                           fontSize=6.5, textColor=_GRAY_400, leading=9))

    # ── Config predeterminada ──────────────────────────────────────────────────

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

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def datos_from_cliente(cliente, plan: dict) -> dict:
        """Build datos_plan dict from a ClienteEvaluacion + plan dict."""
        return {
            "cliente": {
                "nombre": getattr(cliente, "nombre", ""),
                "edad": getattr(cliente, "edad", None),
                "sexo": getattr(cliente, "sexo", None),
                "peso_kg": getattr(cliente, "peso_kg", None),
                "estatura_cm": getattr(cliente, "estatura_cm", None),
                "grasa_corporal_pct": getattr(cliente, "grasa_corporal_pct", None),
                "grasa_corporal_estimada": getattr(cliente, "grasa_corporal_estimada", False),
                "nivel_actividad": getattr(cliente, "nivel_actividad", ""),
                "objetivo": getattr(cliente, "objetivo", ""),
            },
            "macros": {
                "tmb": getattr(cliente, "tmb", 0) or 0,
                "get_total": getattr(cliente, "get_total", 0) or 0,
                "kcal_objetivo": getattr(cliente, "kcal_objetivo", 0) or 0,
                "proteina_g": getattr(cliente, "proteina_g", 0) or 0,
                "carbs_g": getattr(cliente, "carbs_g", 0) or 0,
                "grasa_g": getattr(cliente, "grasa_g", 0) or 0,
            },
            "plan": plan,
        }

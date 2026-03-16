"""
Gestor de branding configurable por gimnasio.

Lee ``config/branding.json`` y expone los valores con soporte para
*dot-notation*::

    from core.branding import branding
    branding.get('colores.primario')      # '#9B4FB0'
    branding.get('nombre_gym')            # 'Fitness Gym Real del Valle'
"""

import json
from pathlib import Path
from typing import Any, Optional

from config.constantes import CARPETA_CONFIG, resource_path


class GestorBranding:
    """Lee / escribe la configuración de branding del gimnasio."""

    ARCHIVO_BRANDING = str(Path(CARPETA_CONFIG) / "branding.json")
    TEMAS_PRECONFIGURADOS: dict[str, dict[str, str]] = {
        "Metodo Base Clasico": {
            "primario": "#9B4FB0",
            "primario_hover": "#B565C6",
            "secundario": "#D4A84B",
            "secundario_hover": "#E4B85B",
            "pdf_color": "#9B4FB0",
        },
        "Titan Rojo": {
            "primario": "#C62828",
            "primario_hover": "#D84343",
            "secundario": "#F9A825",
            "secundario_hover": "#FFB300",
            "pdf_color": "#C62828",
        },
        "Oceano Pro": {
            "primario": "#1565C0",
            "primario_hover": "#1E88E5",
            "secundario": "#26A69A",
            "secundario_hover": "#4DB6AC",
            "pdf_color": "#1565C0",
        },
        "Verde Elite": {
            "primario": "#2E7D32",
            "primario_hover": "#43A047",
            "secundario": "#F57C00",
            "secundario_hover": "#FB8C00",
            "pdf_color": "#2E7D32",
        },
        "Carbon Naranja": {
            "primario": "#E65100",
            "primario_hover": "#F57C00",
            "secundario": "#37474F",
            "secundario_hover": "#455A64",
            "pdf_color": "#E65100",
        },
        "Aurora Mint": {
            "primario": "#00897B",
            "primario_hover": "#00A693",
            "secundario": "#7CB342",
            "secundario_hover": "#8BC34A",
            "pdf_color": "#00897B",
        },
        "Solar Dorado": {
            "primario": "#F9A825",
            "primario_hover": "#FFB300",
            "secundario": "#6A1B9A",
            "secundario_hover": "#7B1FA2",
            "pdf_color": "#F9A825",
        },
        "Granate Premium": {
            "primario": "#8E2430",
            "primario_hover": "#A93242",
            "secundario": "#C9A227",
            "secundario_hover": "#D9B338",
            "pdf_color": "#8E2430",
        },
        "Cobalto Neon": {
            "primario": "#0D47A1",
            "primario_hover": "#1565C0",
            "secundario": "#00ACC1",
            "secundario_hover": "#26C6DA",
            "pdf_color": "#0D47A1",
        },
        "Aurora Fitness": {
            "primario": "#00897B",
            "primario_hover": "#006B5F",
            "secundario": "#7CB342",
            "secundario_hover": "#3D7D52",
            "pdf_color": "#00897B",
            "neutral_bg": "#0A0A0B",
            "neutral_card": "#121214",
            "neutral_text": "#E8E8EC",
        },
    }

    DEFAULTS: dict = {
        "nombre_gym": "",
        "nombre_corto": "Método Base",
        "tagline": "Powered by Consultoría Hernández",
        "tema_visual": "Aurora Fitness",
        "colores": {
            "primario": "#00897B",
            "primario_hover": "#006B5F",
            "secundario": "#7CB342",
            "secundario_hover": "#3D7D52",
        },
        "contacto": {
            "telefono": "",
            "email": "",
            "direccion": "",
            "direccion_linea1": "",
            "direccion_linea2": "",
            "direccion_linea3": "",
            "whatsapp": "",
        },
        "redes_sociales": {
            "facebook": "",
            "instagram": "",
            "tiktok": "",
        },
        "logo": {
            "path": "assets/logo.png",
            "mostrar_watermark": True,
        },
        "pdf": {
            "mostrar_logo": True,
            "logo_path": "assets/logo.png",
            "mostrar_contacto": True,
            "color_encabezado": "#9B4FB0",
        },
        "alimentos": {
            "excluidos": [],
        },
    }

    def __init__(self) -> None:
        self.ruta = Path(self.ARCHIVO_BRANDING)
        self.config: dict = self._cargar_config()

    # ------------------------------------------------------------------
    # Carga
    # ------------------------------------------------------------------

    def _cargar_config(self) -> dict:
        if not self.ruta.exists():
            self._guardar(self.DEFAULTS)
            return self.DEFAULTS.copy()
        try:
            with open(self.ruta, "r", encoding="utf-8") as f:
                return self._merge(self.DEFAULTS, json.load(f))
        except Exception:
            return self.DEFAULTS.copy()

    @staticmethod
    def _merge(base: dict, updates: dict) -> dict:
        result = base.copy()
        for k, v in updates.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = GestorBranding._merge(result[k], v)
            else:
                result[k] = v
        return result

    def _guardar(self, data: dict) -> None:
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ruta, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Acceso
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Acceso con *dot-notation*: ``branding.get('colores.primario')``."""
        cur: Any = self.config
        for part in key.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return default
        return cur

    def set(self, key: str, value: Any) -> bool:
        """Establece un valor y persiste el JSON."""
        parts = key.split(".")
        cur = self.config
        for p in parts[:-1]:
            cur = cur.setdefault(p, {})
        cur[parts[-1]] = value
        return self.guardar()

    def guardar(self) -> bool:
        try:
            self._guardar(self.config)
            return True
        except Exception:
            return False

    def recargar(self) -> None:
        self.config = self._cargar_config()

    def _resolver_ruta(self, ruta: str | None) -> Optional[Path]:
        if not ruta:
            return None
        p = Path(ruta).expanduser()
        if p.exists():
            return p
        p_resource = Path(resource_path(ruta))
        if p_resource.exists():
            return p_resource
        return None

    def obtener_logo_path(self) -> Optional[Path]:
        """Logo general de branding (UI/watermark)."""
        candidatos = [
            self.get("logo.path", "assets/logo.png"),
            "assets/logo.png",
        ]
        for candidato in candidatos:
            resuelto = self._resolver_ruta(candidato)
            if resuelto:
                return resuelto
        return None

    def obtener_logo_pdf_path(self) -> Optional[Path]:
        """Logo para esquina superior derecha de PDF."""
        candidatos = [
            self.get("pdf.logo_path", ""),
            self.get("logo.path", "assets/logo.png"),
            "assets/logo.png",
        ]
        for candidato in candidatos:
            resuelto = self._resolver_ruta(candidato)
            if resuelto:
                return resuelto
        return None

    @classmethod
    def obtener_temas_preconfigurados(cls) -> dict[str, dict[str, str]]:
        return cls.TEMAS_PRECONFIGURADOS.copy()

    def aplicar_tema_visual(self, nombre_tema: str) -> bool:
        tema = self.TEMAS_PRECONFIGURADOS.get(nombre_tema)
        if not tema:
            return False

        self.config.setdefault("colores", {})
        self.config.setdefault("pdf", {})
        self.config["tema_visual"] = nombre_tema
        self.config["colores"]["primario"] = tema["primario"]
        self.config["colores"]["primario_hover"] = tema["primario_hover"]
        self.config["colores"]["secundario"] = tema["secundario"]
        self.config["colores"]["secundario_hover"] = tema["secundario_hover"]
        self.config["pdf"]["color_encabezado"] = tema.get("pdf_color", tema["primario"])
        return self.guardar()


# Instancia global lista para importar
branding = GestorBranding()

"""
Telemetría local de uso funcional por módulo/feature.

Registra eventos accionables (generación de planes, CRUD alimentos,
licencias, reportes, etc.) en un archivo JSON rotativo local.
No envía datos externos — todo es local para análisis del gym.

Uso:
    from utils.telemetria import registrar_evento
    registrar_evento("planes", "plan_generado", {"cliente": "abc", "tipo": "menu_fijo"})
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from config.constantes import CARPETA_REGISTROS
from utils.logger import logger

_ARCHIVO_TELEMETRIA = os.path.join(CARPETA_REGISTROS, "telemetria.jsonl")
_MAX_LINEAS = 50_000
_lock = threading.Lock()


def registrar_evento(
    modulo: str,
    accion: str,
    datos: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Registra un evento de uso funcional.

    Args:
        modulo: Módulo origen (planes, alimentos, licencia, reportes, clientes, admin).
        accion: Acción realizada (plan_generado, alimento_guardado, etc.).
        datos: Datos adicionales opcionales (sin PII sensible).
    """
    evento = {
        "ts": datetime.now().isoformat(),
        "modulo": modulo,
        "accion": accion,
    }
    if datos:
        evento["datos"] = datos

    try:
        with _lock:
            os.makedirs(os.path.dirname(_ARCHIVO_TELEMETRIA), exist_ok=True)
            with open(_ARCHIVO_TELEMETRIA, "a", encoding="utf-8") as f:
                f.write(json.dumps(evento, ensure_ascii=False) + "\n")
    except OSError as e:
        logger.debug("[TELEMETRIA] Error escribiendo evento: %s", e)


def obtener_resumen(modulo: str | None = None, ultimos_dias: int = 30) -> Dict[str, int]:
    """
    Resumen de conteo de acciones, opcionalmente filtrado por módulo.

    Returns:
        Dict mapeando "modulo.accion" → conteo.
    """
    resumen: Dict[str, int] = {}
    cutoff = datetime.now().timestamp() - (ultimos_dias * 86400)

    try:
        if not os.path.exists(_ARCHIVO_TELEMETRIA):
            return resumen

        with open(_ARCHIVO_TELEMETRIA, "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if not linea:
                    continue
                try:
                    evento = json.loads(linea)
                except json.JSONDecodeError:
                    continue

                ts = evento.get("ts", "")
                try:
                    dt = datetime.fromisoformat(ts)
                    if dt.timestamp() < cutoff:
                        continue
                except (ValueError, TypeError):
                    continue

                mod = evento.get("modulo", "desconocido")
                if modulo and mod != modulo:
                    continue
                accion = evento.get("accion", "desconocida")
                key = f"{mod}.{accion}"
                resumen[key] = resumen.get(key, 0) + 1

    except OSError as e:
        logger.debug("[TELEMETRIA] Error leyendo resumen: %s", e)

    return resumen


def rotar_si_necesario() -> None:
    """Rota el archivo si excede el límite de líneas."""
    try:
        if not os.path.exists(_ARCHIVO_TELEMETRIA):
            return

        with open(_ARCHIVO_TELEMETRIA, "r", encoding="utf-8") as f:
            lineas = f.readlines()

        if len(lineas) <= _MAX_LINEAS:
            return

        # Conservar la mitad más reciente
        conservar = lineas[len(lineas) // 2:]
        with open(_ARCHIVO_TELEMETRIA, "w", encoding="utf-8") as f:
            f.writelines(conservar)

        logger.info("[TELEMETRIA] Rotación: %d → %d líneas", len(lineas), len(conservar))

    except OSError as e:
        logger.debug("[TELEMETRIA] Error rotando: %s", e)

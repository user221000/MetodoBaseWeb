# -*- coding: utf-8 -*-
"""
Utilidades para operaciones con archivos y carpetas.
Apertura automática de carpetas y archivos en el explorador del sistema.
"""
import os
import sys
import subprocess
import platform

from utils.logger import logger


def abrir_carpeta_en_explorador(ruta_carpeta: str) -> bool:
    """
    Abre la carpeta especificada en el explorador del sistema.

    Soporta Windows (Explorer), macOS (Finder) y Linux (xdg-open).

    Args:
        ruta_carpeta: Ruta absoluta de la carpeta a abrir

    Returns:
        True si se abrió correctamente, False en caso de error
    """
    try:
        ruta_carpeta = os.path.abspath(ruta_carpeta)

        if not os.path.exists(ruta_carpeta):
            logger.error("❌ Carpeta no existe: %s", ruta_carpeta)
            return False

        sistema = platform.system()

        if sistema == "Windows":
            os.startfile(ruta_carpeta)
            logger.info("📂 Abriendo carpeta en Explorer: %s", ruta_carpeta)
        elif sistema == "Darwin":
            subprocess.Popen(["open", ruta_carpeta])
            logger.info("📂 Abriendo carpeta en Finder: %s", ruta_carpeta)
        else:
            subprocess.Popen(["xdg-open", ruta_carpeta])
            logger.info("📂 Abriendo carpeta con xdg-open: %s", ruta_carpeta)

        return True

    except Exception as e:
        logger.error("❌ Error abriendo carpeta: %s", e)
        return False


def abrir_archivo_en_aplicacion_default(ruta_archivo: str) -> bool:
    """
    Abre un archivo con su aplicación predeterminada del sistema.

    Args:
        ruta_archivo: Ruta absoluta del archivo

    Returns:
        True si se abrió correctamente
    """
    try:
        ruta_archivo = os.path.abspath(ruta_archivo)

        if not os.path.exists(ruta_archivo):
            logger.error("❌ Archivo no existe: %s", ruta_archivo)
            return False

        sistema = platform.system()

        if sistema == "Windows":
            os.startfile(ruta_archivo)
        elif sistema == "Darwin":
            subprocess.Popen(["open", ruta_archivo])
        else:
            subprocess.Popen(["xdg-open", ruta_archivo])

        logger.info("📄 Abriendo archivo: %s", ruta_archivo)
        return True

    except Exception as e:
        logger.error("❌ Error abriendo archivo: %s", e)
        return False

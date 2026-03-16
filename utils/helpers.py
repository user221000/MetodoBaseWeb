"""Funciones utilitarias generales."""
import os
import sys
import json
import glob
import platform
import subprocess

from utils.logger import logger


def resource_path(relative_path):
    """Resuelve rutas portables para PyInstaller y desarrollo."""
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def abrir_carpeta_pdf(ruta: str | None = None) -> None:
    """Abre la carpeta de PDFs en el explorador de archivos. Compatible Windows/macOS/Linux."""
    from config.constantes import CARPETA_SALIDA
    carpeta = ruta or CARPETA_SALIDA
    if not os.path.exists(carpeta):
        os.makedirs(carpeta, exist_ok=True)
    sistema = platform.system()
    try:
        if sistema == "Windows":
            os.startfile(carpeta)
        elif sistema == "Darwin":
            subprocess.Popen(["open", carpeta])
        else:
            subprocess.Popen(["xdg-open", carpeta])
    except Exception as exc:
        logger.warning("No se pudo abrir carpeta %s: %s", carpeta, exc)


def centrar_ventana(ventana, ancho: int, alto: int) -> None:
    """Centra una ventana Tk/CTk en la pantalla actual."""
    ventana.update_idletasks()
    x = (ventana.winfo_screenwidth() // 2) - (ancho // 2)
    y = (ventana.winfo_screenheight() // 2) - (alto // 2)
    ventana.geometry(f"{ancho}x{alto}+{x}+{y}")


def activar_modal_seguro(ventana, parent=None) -> None:
    """Activa comportamiento modal sólo cuando la ventana ya es visible.

    En Linux/X11, ``grab_set()`` puede fallar con "window not viewable"
    si se invoca antes de que el Toplevel termine de mapearse.
    Adicionalmente, llamar ``transient()`` sobre un padre withdrawn (oculto)
    hace que el WM desmapee el hijo, bloqueando ``wait_visibility()`` para siempre.
    """
    if parent is not None:
        # Solo aplicar transient si el padre está actualmente visible/mapeado.
        # En Linux/X11, un padre withdrawn causa que el hijo también se desmapee.
        try:
            if parent.winfo_viewable():
                ventana.transient(parent)
        except Exception as exc:
            logger.warning("No se pudo configurar transient en %s: %s", ventana, exc)

    # Reemplazamos el wait_visibility() bloqueante con un after() no bloqueante.
    # Esto evita el deadlock cuando el padre está withdrawn o el WM tarda en mapear.
    def _hacer_modal():
        try:
            ventana.lift()
        except Exception as exc:
            logger.warning("No se pudo elevar la ventana %s: %s", ventana, exc)
        try:
            ventana.grab_set()
        except Exception as exc:
            logger.warning("No se pudo aplicar grab modal en %s: %s", ventana, exc)
        try:
            ventana.focus_force()
        except Exception as exc:
            logger.warning("No se pudo enfocar la ventana %s: %s", ventana, exc)

    ventana.after(200, _hacer_modal)


def cargar_plan_anterior_cliente(cliente_id: str, directorio_planes: str = ".") -> dict | None:
    """
    Carga el último plan JSON del cliente para obtener peso_base_mes anterior.
    
    Args:
        cliente_id: ID único del cliente
        directorio_planes: Ruta donde buscar archivos plan_*.json
        
    Returns:
        dict: Último plan JSON encontrado o None si no existe
    """
    try:
        if directorio_planes == ".":
            from config.constantes import CARPETA_PLANES
            directorio_planes = CARPETA_PLANES
        pattern = f"plan_{cliente_id}_*.json"
        archivos = glob.glob(os.path.join(directorio_planes, pattern))
        
        if not archivos:
            return None
        
        archivo_reciente = max(archivos, key=os.path.getctime)
        
        with open(archivo_reciente, 'r', encoding='utf-8') as f:
            plan_anterior = json.load(f)
        
        return plan_anterior
    except Exception:
        return None

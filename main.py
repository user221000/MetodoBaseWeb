"""
Método Base - Punto de entrada principal.
Sistema de generación de planes nutricionales personalizados.
"""

# === SETUP DE PATHS ===
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# === IMPORTS ===
from datetime import datetime

from config.constantes import FACTORES_ACTIVIDAD, CARPETA_SALIDA, CARPETA_PLANES
from core.modelos import ClienteEvaluacion
from core.motor_nutricional import MotorNutricional
from core.generador_planes import ConstructorPlanNuevo
from core.exportador_salida import GeneradorPDFProfesional
from core.licencia import GestorLicencias
from utils.logger import logger

# Intentar cargar PySide6 GUI
try:
    from PySide6.QtWidgets import QApplication, QSplashScreen, QLabel
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QPixmap, QColor, QFont, QPainter, QBrush
    GUI_DISPONIBLE = True
except ImportError:
    GUI_DISPONIBLE = False


def cargar_fuentes_personalizadas() -> None:
    """Registra las fuentes Inter del proyecto en QFontDatabase (PySide6).

    Debe llamarse justo después de crear QApplication para que los widgets
    creados posteriormente ya usen Inter como familia disponible.
    """
    try:
        from PySide6.QtGui import QFontDatabase

        fonts_dir = Path(__file__).parent / "fonts" / "Inter"
        if not fonts_dir.exists():
            print("⚠️  Directorio fonts/Inter no encontrado — usando fuente del sistema")
            return

        loaded: list[str] = []
        failed: list[str] = []
        for ttf in sorted(fonts_dir.glob("*.ttf")):
            fid = QFontDatabase.addApplicationFont(str(ttf))
            if fid == -1:
                failed.append(ttf.name)
            else:
                loaded.append(ttf.name)

        if loaded:
            print(f"✅ Fuentes Inter cargadas ({len(loaded)}): {', '.join(loaded)}")
        if failed:
            print(f"❌ Fuentes no cargadas: {', '.join(failed)}")

    except Exception as exc:
        print(f"⚠️  Error al cargar fuentes Inter: {exc}")


def _crear_pixmap_splash() -> "QPixmap":
    """Crea un QPixmap 400×200 para el splash screen con tema verde premium."""
    pix = QPixmap(400, 200)
    pix.fill(QColor("#0a1409"))
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    # Punto acento verde neón
    painter.setBrush(QBrush(QColor("#39ff14")))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(192, 20, 16, 16)
    # Título
    f_titulo = QFont("Inter", 20)
    f_titulo.setBold(True)
    painter.setFont(f_titulo)
    painter.setPen(QColor("#e8f5e9"))
    painter.drawText(0, 60, 400, 50, Qt.AlignHCenter | Qt.AlignVCenter, "Método Base")
    # Subtítulo
    painter.setFont(QFont("Inter", 11))
    painter.setPen(QColor("#66bb6a"))
    painter.drawText(0, 110, 400, 30, Qt.AlignHCenter | Qt.AlignVCenter,
                     "Sistema de Planes Nutricionales")
    # Barra de progreso base
    painter.setBrush(QBrush(QColor("#152515")))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(100, 160, 200, 6, 3, 3)
    painter.end()
    return pix


# === EJECUCIÓN ===
if __name__ == "__main__":
    if GUI_DISPONIBLE:
        app = QApplication(sys.argv)
        app.setApplicationName("Método Base")
        app.setStyle("Fusion")

        # Registrar fuentes Inter antes de construir cualquier widget
        cargar_fuentes_personalizadas()

        # Cargar stylesheet verde premium para toda la aplicación (todos los diálogos)
        try:
            from ui_desktop.pyside.theme_manager import ThemeManager
            _theme_mgr = ThemeManager.instance()
            # Forzar verde_premium desde el inicio, antes de cualquier diálogo
            if _theme_mgr.current_theme == "verde_premium":
                _theme_mgr.reload()
            else:
                _theme_mgr.set_theme("verde_premium", animated=False)
        except Exception as _te:
            # Fallback: cargar dark_theme.qss directamente
            logger.warning("[THEME] ThemeManager no disponible: %s — usando dark_theme.qss", _te)
            _qss_path = os.path.join(
                os.path.dirname(__file__), "ui_desktop", "pyside", "styles", "dark_theme.qss"
            )
            if os.path.exists(_qss_path):
                with open(_qss_path, encoding="utf-8") as f:
                    app.setStyleSheet(f.read())

        # Splash screen
        _pix = _crear_pixmap_splash()
        _splash = QSplashScreen(_pix)
        _splash.setWindowFlag(Qt.WindowStaysOnTopHint)
        _splash.show()
        app.processEvents()

        # Animar barra de progreso en el splash
        _prog = [0]

        def _animar():
            _prog[0] += 5
            p = _crear_pixmap_splash()
            painter = QPainter(p)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QBrush(QColor("#39ff14")))
            painter.setPen(Qt.NoPen)
            ancho = int(200 * min(_prog[0], 100) / 100)
            painter.drawRoundedRect(100, 160, ancho, 6, 3, 3)
            painter.end()
            _splash.setPixmap(p)
            app.processEvents()
            if _prog[0] < 100:
                QTimer.singleShot(15, _animar)
            else:
                QTimer.singleShot(150, _lanzar_app)

        def _lanzar_app():
            _splash.close()

            from core.branding import branding as _branding

            # ── Flujo unificado: InicioPanel → GYM | Usuario Regular ─────
            try:
                from ui_desktop.pyside.flow_controller import FlowController
                _flow = FlowController()
                _resultado = _flow.exec()
            except Exception as _fe:
                logger.error("[FLOW] Error cargando FlowController: %s", _fe)
                _resultado = FlowController.RESULTADO_MODO_GYM if 'FlowController' in dir() else 2

            if _resultado == 0:  # RESULTADO_CANCELADO
                logger.info("[FLOW] Flujo cancelado por el usuario.")
                sys.exit(0)

            elif _resultado == 2:  # RESULTADO_MODO_GYM
                # ── GYM: autenticación gym → wizard colores/logo → licencia → MainWindow ──
                logger.info("[FLOW] Flujo GYM iniciado.")

                # 1) Acceso GYM (registro primera vez / login si ya existe cuenta)
                try:
                    from ui_desktop.pyside.ventana_acceso_gym import VentanaAccesoGym
                    _acceso_gym = VentanaAccesoGym()
                    if not _acceso_gym.exec() or _acceso_gym.sesion_gym is None:
                        logger.info("[GYM] Acceso GYM cancelado.")
                        sys.exit(0)
                    _sesion_gym = _acceso_gym.sesion_gym
                    logger.info("[GYM] Autenticado rol=%s", _sesion_gym.rol)
                    _branding.recargar()
                except Exception as _gym_auth_err:
                    logger.error("[GYM] Error en acceso GYM: %s", _gym_auth_err)
                    sys.exit(1)

                # 2) Wizard de colores / logo (solo si aún no está configurado)
                _colores_ok = bool(_branding.get("colores.primario", "").strip()
                                   and _branding.get("colores.primario") != "#FF6F0F")
                if not _colores_ok:
                    try:
                        from ui_desktop.pyside.wizard_onboarding import WizardOnboarding
                        wizard = WizardOnboarding()
                        wizard.exec()
                        _branding.recargar()
                    except Exception as _wiz_err:
                        logger.warning("[WIZARD] %s", _wiz_err)

                try:
                    _gestor_lic = GestorLicencias()
                    _valida, _msg, _ = _gestor_lic.validar_licencia()
                    if not _valida:
                        logger.warning("[LICENCIA] Licencia no válida: %s", _msg)
                        _nombre_gym = _branding.get("nombre_gym", "").strip() or "MetodoBase"
                        from ui_desktop.pyside.ventana_licencia import VentanaActivacionLicencia
                        _lic_dlg = VentanaActivacionLicencia(
                            None, gestor=_gestor_lic, nombre_gym=_nombre_gym
                        )
                        if not _lic_dlg.exec() or not _lic_dlg.activada:
                            logger.info("[LICENCIA] Activación cancelada.")
                            sys.exit(0)
                        logger.info("[LICENCIA] Licencia activada.")
                    else:
                        logger.info("[LICENCIA] %s", _msg)
                except Exception as _lic_err:
                    logger.warning("[LICENCIA] No se pudo gestionar licencia: %s", _lic_err)

                from ui_desktop.pyside.gym_app_window import GymAppWindow
                window = GymAppWindow()
                window.show()
                # Almacenar referencia para evitar GC
                app._main_window = window

            else:  # RESULTADO_SESION_OK (1)
                # ── Usuario regular: FlowController ya gestionó todo ──────
                logger.info("[FLOW] Flujo usuario regular finalizado.")
                sys.exit(0)

        QTimer.singleShot(50, _animar)
        sys.exit(app.exec())

    else:
        # Fallback a modo consola
        print("\n" + "=" * 60)
        print("    SISTEMA MVP GYMS - GENERADOR DE PLANES NUTRICIONALES")
        print("    (Modo Consola - instala customtkinter para GUI)")
        print("=" * 60)

        os.makedirs(CARPETA_PLANES, exist_ok=True)
        os.makedirs("datos", exist_ok=True)

        print("\nIngrese los datos del cliente:\n")

        telefono = input("Teléfono (10+ dígitos, sin espacios): ").strip()
        from src.gestor_bd import GestorBDClientes
        gestor_bd = GestorBDClientes()
        cliente_existente = None
        if telefono:
            clientes = gestor_bd.buscar_clientes(telefono)
            if clientes:
                cliente_existente = clientes[0]

        if cliente_existente:
            print(f"Cliente encontrado: {cliente_existente['nombre']} (ID: {cliente_existente['id_cliente']})")
            nombre = cliente_existente['nombre']
            edad = cliente_existente['edad']
            peso = cliente_existente['peso_kg']
            altura = cliente_existente['estatura_cm']
            grasa = cliente_existente['grasa_corporal_pct']
            nivel = cliente_existente['nivel_actividad']
            objetivo = cliente_existente['objetivo']
            id_cliente = cliente_existente['id_cliente']
        else:
            nombre = input("Nombre completo: ").strip() or "Cliente"
            while True:
                try:
                    edad = int(input("Edad (14-80): "))
                    if 14 <= edad <= 80:
                        break
                    print("  -> Edad debe estar entre 14 y 80 anos.")
                except ValueError:
                    print("  -> Ingrese un numero valido.")
            while True:
                try:
                    peso = float(input("Peso (kg): "))
                    if 30 <= peso <= 250:
                        break
                    print("  -> Peso debe estar entre 30 y 250 kg.")
                except ValueError:
                    print("  -> Ingrese un numero valido.")
            while True:
                try:
                    altura = float(input("Estatura (cm): "))
                    if 100 <= altura <= 250:
                        break
                    print("  -> Estatura debe estar entre 100 y 250 cm.")
                except ValueError:
                    print("  -> Ingrese un numero valido.")
            while True:
                try:
                    grasa = float(input("Grasa corporal (%): "))
                    if 3 <= grasa <= 60:
                        break
                    print("  -> Grasa corporal debe estar entre 3% y 60%.")
                except ValueError:
                    print("  -> Ingrese un numero valido.")
            print("\nNivel de actividad fisica:")
            print("  1. Sedentario (nula)")
            print("  2. Leve")
            print("  3. Moderada")
            print("  4. Intensa")
            niveles = {1: "nula", 2: "leve", 3: "moderada", 4: "intensa"}
            while True:
                try:
                    opcion = int(input("Seleccione (1-4): "))
                    if opcion in niveles:
                        nivel = niveles[opcion]
                        break
                    print("  -> Seleccione una opcion valida (1-4).")
                except ValueError:
                    print("  -> Ingrese un numero valido.")
            print("\nObjetivo nutricional:")
            print("  1. Deficit (bajar de peso)")
            print("  2. Mantenimiento")
            print("  3. Superavit (subir de peso/volumen)")
            objetivos = {1: "deficit", 2: "mantenimiento", 3: "superavit"}
            while True:
                try:
                    opcion = int(input("Seleccione (1-3): "))
                    if opcion in objetivos:
                        objetivo = objetivos[opcion]
                        break
                    print("  -> Seleccione una opcion valida (1-3).")
                except ValueError:
                    print("  -> Ingrese un numero valido.")
            id_cliente = None

        print("\n" + "-" * 40)
        print("Procesando...")

        from core.modelos import ClienteEvaluacion
        cliente = ClienteEvaluacion(
            nombre=nombre, telefono=telefono if telefono else None, edad=edad, peso_kg=peso,
            estatura_cm=altura, grasa_corporal_pct=grasa, nivel_actividad=nivel, objetivo=objetivo
        )
        if id_cliente:
            cliente.id_cliente = id_cliente
        cliente.factor_actividad = FACTORES_ACTIVIDAD.get(nivel, 1.2)
        from core.motor_nutricional import MotorNutricional
        cliente = MotorNutricional.calcular_motor(cliente)
        from core.generador_planes import ConstructorPlanNuevo
        plan = ConstructorPlanNuevo.construir(cliente, plan_numero=1, directorio_planes=CARPETA_PLANES)

        if not os.path.exists(CARPETA_SALIDA):
            os.makedirs(CARPETA_SALIDA)

        nombre_pdf = f"plan_{cliente.nombre.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        ruta_pdf_completa = os.path.join(CARPETA_SALIDA, nombre_pdf)
        from core.exportador_salida import GeneradorPDFProfesional
        generador = GeneradorPDFProfesional(ruta_pdf_completa)
        ruta_pdf = generador.generar(cliente, plan)

        # Registrar cliente y plan en BD
        gestor_bd.registrar_cliente(cliente)
        gestor_bd.registrar_plan_generado(cliente, plan, ruta_pdf)

        comidas = ['desayuno', 'almuerzo', 'comida', 'cena']
        kcal_real = sum(plan[c].get('kcal_real', 0) for c in comidas if c in plan)
        desv_max = max(plan[c].get('desviacion_pct', 0) for c in comidas if c in plan)

        print("\n" + "=" * 60)
        print("  PLAN GENERADO EXITOSAMENTE!")
        print("=" * 60)
        print(f"\n  Cliente: {nombre}")
        print(f"  Objetivo: {objetivo.upper()}")
        print(f"  Kcal objetivo: {cliente.kcal_objetivo:.0f}")
        print(f"  Kcal reales: {kcal_real:.0f}")
        print(f"  Desviacion maxima: {desv_max:.2f}%")
        print(f"\n  PDF guardado en: {ruta_pdf}")
        print("\n" + "=" * 60)
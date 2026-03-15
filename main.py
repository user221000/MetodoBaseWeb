"""
Método Base - Punto de entrada principal.
Sistema de generación de planes nutricionales personalizados.
"""

# === SETUP DE PATHS ===
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# === SPLASH SCREEN DE CARGA (no bloqueante) ===
import tkinter as tk

splash = tk.Tk()
splash.title("Método Base")
splash.geometry("400x200")
splash.configure(bg="#0D0D0D")
splash.overrideredirect(True)   # sin barra de título
splash.update_idletasks()
sw, sh = splash.winfo_screenwidth(), splash.winfo_screenheight()
splash.geometry(f"400x200+{(sw-400)//2}+{(sh-200)//2}")

tk.Label(splash, text="🏋️ Método Base", bg="#0D0D0D", fg="#9B4FB0",
         font=("Segoe UI", 20, "bold")).pack(expand=True)
tk.Label(splash, text="Sistema de Planes Nutricionales", bg="#0D0D0D", fg="#B8B8B8",
         font=("Segoe UI", 11)).pack(pady=(0, 30))

bar_canvas = tk.Canvas(splash, width=200, height=6, bg="#2A2A2A",
                       highlightthickness=0)
bar_canvas.pack(pady=(0, 20))
bar_rect = bar_canvas.create_rectangle(0, 0, 0, 6, fill="#9B4FB0", outline="")

_splash_step = [0]

def _animar_splash():
    _splash_step[0] += 5
    bar_canvas.coords(bar_rect, 0, 0, _splash_step[0] * 2, 6)
    if _splash_step[0] < 100:
        splash.after(15, _animar_splash)
    else:
        splash.after(100, splash.destroy)

splash.after(50, _animar_splash)
splash.mainloop()

# === IMPORTS ===
from datetime import datetime

from config.constantes import FACTORES_ACTIVIDAD, CARPETA_SALIDA, CARPETA_PLANES
from core.modelos import ClienteEvaluacion
from core.motor_nutricional import MotorNutricional
from core.generador_planes import ConstructorPlanNuevo
from core.exportador_salida import GeneradorPDFProfesional
from core.licencia import GestorLicencias
from utils.logger import logger

# Intentar cargar GUI
try:
    import customtkinter as ctk
    from gui.app_gui import GymApp
    GUI_DISPONIBLE = True
except ImportError:
    GUI_DISPONIBLE = False


# === EJECUCIÓN ===
if __name__ == "__main__":
    if GUI_DISPONIBLE:
        # Wizard de primera vez si nombre_gym está vacío
        from core.branding import branding as _branding
        if not _branding.get('nombre_gym', '').strip():
            from gui.wizard_onboarding import WizardOnboarding
            _root_wizard = ctk.CTk()
            _root_wizard.withdraw()
            wizard = WizardOnboarding(_root_wizard)
            _root_wizard.wait_window(wizard)
            _root_wizard.destroy()
            _branding.recargar()

        # Validar licencia — sin auto-generación (requiere key de proveedor)
        try:
            _gestor_lic = GestorLicencias()
            _valida, _msg, _ = _gestor_lic.validar_licencia()
            if not _valida:
                logger.warning("[LICENCIA] Licencia no válida: %s", _msg)
                ctk.set_appearance_mode("Dark")
                ctk.set_default_color_theme("blue")
                _nombre_gym = _branding.get('nombre_gym', '').strip() or 'MetodoBase'
                from gui.ventana_licencia import VentanaActivacionLicencia
                _root_lic = ctk.CTk()
                _root_lic.withdraw()
                _vent_lic = VentanaActivacionLicencia(_root_lic, _gestor_lic, _nombre_gym)
                _root_lic.wait_window(_vent_lic)
                if not _vent_lic.activada:
                    logger.info("[LICENCIA] Activación cancelada por el usuario.")
                    _root_lic.destroy()
                    sys.exit(0)
                _root_lic.destroy()
                logger.info("[LICENCIA] Licencia activada correctamente.")
            else:
                logger.info("[LICENCIA] %s", _msg)
        except Exception as _lic_err:
            logger.warning("[LICENCIA] No se pudo gestionar licencia: %s", _lic_err)

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        app = GymApp()
        app.mainloop()
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

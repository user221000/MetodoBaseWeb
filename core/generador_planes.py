"""CAPA 4: Construcción de planes nutricionales completos."""
from core.food_catalog import FoodCatalog, FoodRestrictionError
from core.nutrition_restrictions import generation_catalog
from src.alimentos_base import ALIMENTOS_BASE as _DEFAULT_FOODS, CATEGORIAS as _DEFAULT_CATEGORIES
import os
from datetime import datetime

from config.constantes import (
    PROTEIN_FOODS, FACTORES_ACTIVIDAD, MODO_ESTRICTO,
    LIMITES_DUROS_ALIMENTOS, CARPETA_SALIDA,
)
from src.alimentos_base import ALIMENTOS_BASE, LIMITES_ALIMENTOS, CATEGORIAS
from src.gestor_rotacion import GestorRotacionAlimentos

from core.modelos import ClienteEvaluacion
from core.motor_nutricional import MotorNutricional, AjusteCaloricoMensual
from core.selector_alimentos import (
    SelectorAlimentos, generar_seed, generar_seed_bloques,
)
from core.estructura_comida import MealStructureContract, ConstructorMealStructure
from core.generador_comidas import (
    DistribuidorComidas, CalculadorGramosNuevo, CalculadorGramos,
    ValidadorEnergia, ReajustadorPlan,
)
from utils.helpers import cargar_plan_anterior_cliente
from utils.logger import logger


# ============================================================================
# REDONDEO CLÍNICO
# ============================================================================

def _aplicar_redondeo_clinico(comida_dict: dict, catalogo: FoodCatalog | None = None) -> dict:
    """
    Aplica redondeo clínico a una comida.
    
    Reglas de redondeo:
    - Proteínas: múltiplos de 5g
    - Carbohidratos: múltiplos de 10g
    - Grasas: múltiplos de 5g
    - Vegetales: múltiplos de 10g
    """
    # Each helper receives the same immutable request snapshot, including fallbacks.
    catalogo = catalogo or FoodCatalog.from_data(_DEFAULT_FOODS, _DEFAULT_CATEGORIES)
    alimentos_base = catalogo.alimentos
    categorias = catalogo.categorias
    if 'alimentos' not in comida_dict:
        return comida_dict
    
    proteinas_set = set(categorias.get('proteina', []))
    carbs_set     = set(categorias.get('carbs', []))
    grasas_set    = set(categorias.get('grasa', []))
    vegetales_set = set(categorias.get('verdura', []))
    
    def redondear(valor, multiplo):
        return round(valor / multiplo) * multiplo
    
    alimentos_redondeados = {}
    
    for nombre, gramos in comida_dict['alimentos'].items():
        if nombre in proteinas_set:
            gramos_redondeados = redondear(gramos, 5)
        elif nombre in carbs_set:
            gramos_redondeados = redondear(gramos, 10)
        elif nombre in grasas_set:
            gramos_redondeados = redondear(gramos, 5)
        elif nombre in vegetales_set:
            gramos_redondeados = redondear(gramos, 10)
        else:
            gramos_redondeados = redondear(gramos, 5)
        
        gramos_redondeados = max(0, gramos_redondeados)
        
        if gramos_redondeados > 0:
            alimentos_redondeados[nombre] = gramos_redondeados
    
    comida_dict['alimentos'] = alimentos_redondeados
    
    if comida_dict['alimentos']:
        kcal_real = sum(
            g * alimentos_base.get(n, {}).get('kcal', 0) / 100
            for n, g in comida_dict['alimentos'].items()
        )
        kcal_objetivo = comida_dict.get('kcal_objetivo', 1)
        comida_dict['kcal_real'] = kcal_real
        comida_dict['desviacion_pct'] = abs(kcal_real - kcal_objetivo) / max(kcal_objetivo, 1) * 100
    
    return comida_dict


# ============================================================================
# VALIDACIÓN FINAL: Limites estrictos por alimento
# ============================================================================

def _validar_limites_estrictos_por_plan(plan: dict, catalogo: FoodCatalog | None = None) -> dict:
    """
    Valida que alimentos con límites estrictos no excedan máximo en plan diario.
    FRIJOLES: Máximo 400g total por plan (máximo ~200g por comida individual).
    """
    # Each helper receives the same immutable request snapshot, including fallbacks.
    catalogo = catalogo or FoodCatalog.from_data(_DEFAULT_FOODS, _DEFAULT_CATEGORIES)
    alimentos_base = catalogo.alimentos
    frijoles_total = 0.0
    for nombre_comida, comida_data in plan.items():
        if 'alimentos' in comida_data and 'frijoles' in comida_data['alimentos']:
            frijoles_total += comida_data['alimentos']['frijoles']
    
    LIMITE_FRIJOLES_PLAN = 400
    
    if frijoles_total > LIMITE_FRIJOLES_PLAN:
        proporcion = LIMITE_FRIJOLES_PLAN / frijoles_total
        
        for nombre_comida, comida_data in plan.items():
            if 'alimentos' in comida_data and 'frijoles' in comida_data['alimentos']:
                frijoles_actual = comida_data['alimentos']['frijoles']
                frijoles_nuevo = min(frijoles_actual * proporcion, 200)
                
                comida_data['alimentos']['frijoles'] = frijoles_nuevo
                
                kcal_real = 0.0
                for ali_nombre, gramos in comida_data['alimentos'].items():
                    if ali_nombre in alimentos_base:
                        kcal_real += gramos * (alimentos_base[ali_nombre]['kcal'] / 100)
                
                comida_data['kcal_real'] = kcal_real
                comida_data['desviacion_pct'] = abs(kcal_real - comida_data['kcal_objetivo']) / max(comida_data['kcal_objetivo'], 1) * 100
    
    return plan


# ============================================================================
# EXCEPCIÓN CUSTOM
# ============================================================================

class PlanInvalidoError(Exception):
    """Se lanza cuando no se puede generar un plan válido tras todos los intentos."""

    def __init__(self, mensaje: str, errores: list[str], cliente_id: str):
        super().__init__(mensaje)
        self.errores = errores
        self.cliente_id = cliente_id


# ============================================================================
# #16B NUEVO CONSTRUCTOR: Flujo secuencial (Proteína → Carbs → Grasas)
# ============================================================================

class ConstructorPlanNuevo:
    """
    Nueva arquitectura: Construcción secuencial por macronutriente.
    
    Flujo:
    1. Distribuir macros por comida
    2. Para cada comida:
       a. Asignar PROTEÍNA (ESTRUCTURAL → CONGELADA)
       b. Asignar CARBS
       c. Asignar GRASAS
       d. Insertar VEGETAL BASE
       e. Validación energética (ajusta solo carbs/grasas)
    """
    
    @staticmethod
    def construir(
        cliente: ClienteEvaluacion,
        plan_numero: int = 1,
        directorio_planes: str = ".",
        max_intentos: int = 3,
        catalogo: FoodCatalog | None = None,
    ) -> dict:
        """
        Construye plan con validación robusta y reintentos.

        Args:
            max_intentos: Número máximo de intentos antes de lanzar PlanInvalidoError.

        Raises:
            PlanInvalidoError: Si después de max_intentos el plan sigue inválido
                               y MODO_ESTRICTO está activo.
        """
        # ── Una sola vez: seeds, ajuste calórico, distribución, rotación ──
        # Each helper receives the same immutable request snapshot, including fallbacks.
        catalogo = generation_catalog(
            cliente.nutrition_restrictions, _DEFAULT_FOODS, _DEFAULT_CATEGORIES, catalogo,
        )
        alimentos_base = catalogo.alimentos
        bloque = 1 if plan_numero <= 3 else 2
        seed_base, seed_variacion = generar_seed_bloques(cliente, gym_id="default")
        seed_inicial = seed_base if bloque == 1 else seed_variacion
        micro_seed = generar_seed(cliente, semana=plan_numero, gym_id="default")  # noqa: F841
        bloque_indice = bloque  # noqa: F841

        kcal_objetivo_original = cliente.kcal_objetivo
        plan_anterior = cargar_plan_anterior_cliente(cliente.id_cliente, directorio_planes)

        kcal_objetivo_para_usar, ajuste_aplicado = AjusteCaloricoMensual.aplicar_ajuste(
            cliente_id=cliente.id_cliente,
            peso_actual=cliente.peso_kg,
            objetivo=cliente.objetivo,
            kcal_objetivo_base=kcal_objetivo_original,
            plan_anterior=plan_anterior,
            directorio_planes=directorio_planes,
        )
        ajuste_desc = (
            'ajuste -5%' if (ajuste_aplicado and cliente.objetivo == 'deficit')
            else 'ajuste +5%' if (ajuste_aplicado and cliente.objetivo == 'superavit')
            else 'sin ajuste'
        )
        logger.info("[AJUSTE] Kcal base %.0f -> final %.0f (%s)",
                    kcal_objetivo_original, kcal_objetivo_para_usar, ajuste_desc)

        if ajuste_aplicado:
            macros_finales = MotorNutricional.calcular_macros(cliente.peso_kg, kcal_objetivo_para_usar)
        else:
            macros_finales = {
                'proteina_g': cliente.proteina_g,
                'grasa_g': cliente.grasa_g,
                'carbs_g': cliente.carbs_g,
            }

        distribuidor = DistribuidorComidas()
        distribucion = distribuidor.distribuir(
            kcal_objetivo_para_usar,
            macros_finales['proteina_g'],
            macros_finales['grasa_g'],
            macros_finales['carbs_g'],
        )

        gestor_rotacion = GestorRotacionAlimentos(cliente.id_cliente)
        penalizados_por_cat = gestor_rotacion.obtener_penalizados()
        pesos_ponderados = gestor_rotacion._inteligente.obtener_penalizaciones_ponderadas()
        logger.info("[ROTACION] %d alimentos con penalización ponderada", len(pesos_ponderados))

        # ── Bucle de reintentos ──
        for intento in range(1, max_intentos + 1):
            seed = seed_inicial + (intento - 1)   # variar seed en cada intento
            logger.info("Intento %d/%d de generación de plan", intento, max_intentos)

            try:
                selector = SelectorAlimentos()
                calculador_nuevo = CalculadorGramosNuevo()
                plan: dict = {}
                alimentos_usados_plan: set = set()

                for meal_idx, (nombre_comida, macros_comida) in enumerate(distribucion.items()):
                    alimentos_dict = {}

                    # FASE 1: PROTEÍNA
                    lista_proteinas = selector.seleccionar_lista(
                        'proteina', meal_idx, alimentos_usados=alimentos_usados_plan,
                        seed=seed, plan_numero=plan_numero,
                        alimentos_penalizados=penalizados_por_cat,
                        pesos_ponderados=pesos_ponderados,
                    catalogo=catalogo)
                    main_protein = None
                    for prot in lista_proteinas:
                        if not any(item in PROTEIN_FOODS for item in alimentos_dict):
                            main_protein = prot
                            break
                    proteinas_asignadas, kcal_proteina, proteina_congelada = (
                        calculador_nuevo.asignar_proteina_estructural(
                            macros_comida['proteina'],
                            [main_protein] if main_protein else lista_proteinas,
                            meal_idx,
                            penalizados=set(),
                            alimentos_usados_plan=alimentos_usados_plan,
                        catalogo=catalogo)
                    )
                    if not proteina_congelada:
                        logger.warning("Proteína no congelada en %s (plan #%d)",
                                       nombre_comida, plan_numero)
                    alimentos_dict.update(proteinas_asignadas)
                    alimentos_usados_plan.update(proteinas_asignadas.keys())
                    proteina_principal = next(iter(proteinas_asignadas.keys()), None)

                    carbs_desde_proteina = 0.0
                    grasa_desde_proteina = 0.0
                    for ali_nombre in proteinas_asignadas:
                        ali_data = alimentos_base.get(ali_nombre, {})
                        gramos = proteinas_asignadas[ali_nombre]
                        carbs_desde_proteina += gramos * (ali_data.get('carbs', 0) / 100)
                        grasa_desde_proteina += gramos * (ali_data.get('grasa', 0) / 100)

                    # FASE 2: CARBS
                    lista_carbs = selector.seleccionar_lista(
                        'carbs', meal_idx, alimentos_usados=alimentos_usados_plan,
                        seed=seed, plan_numero=plan_numero,
                        alimentos_penalizados=penalizados_por_cat,
                        pesos_ponderados=pesos_ponderados,
                    catalogo=catalogo)
                    carbs_asignados, kcal_carbs = calculador_nuevo.asignar_carbs(
                        macros_comida['carbs'], carbs_desde_proteina,
                        lista_carbs, meal_idx, alimentos_usados_plan=alimentos_usados_plan,
                    catalogo=catalogo)
                    alimentos_dict.update(carbs_asignados)
                    alimentos_usados_plan.update(carbs_asignados.keys())

                    # FASE 3: GRASAS
                    lista_grasas = selector.seleccionar_lista(
                        'grasa', meal_idx, alimentos_usados=alimentos_usados_plan,
                        seed=seed, plan_numero=plan_numero,
                        alimentos_penalizados=penalizados_por_cat,
                        pesos_ponderados=pesos_ponderados,
                    catalogo=catalogo)
                    grasas_asignados, kcal_grasas = calculador_nuevo.asignar_grasas(
                        macros_comida['grasa'], grasa_desde_proteina,
                        lista_grasas, alimentos_usados_plan=alimentos_usados_plan,
                        proteina_principal=proteina_principal,
                    catalogo=catalogo)
                    alimentos_dict.update(grasas_asignados)
                    alimentos_usados_plan.update(grasas_asignados.keys())

                    # FASE 4: VEGETAL BASE
                    alimentos_dict.update(calculador_nuevo.insertar_vegetal_base(meal_idx, catalogo=catalogo, seed=seed))

                    # FASE 5: VALIDACIÓN ENERGÉTICA
                    alimentos_dict = calculador_nuevo.validar_energetica(
                        alimentos_dict, macros_comida['kcal'],
                        proteina_congelada=True,
                        lista_carbs=lista_carbs, lista_grasas=lista_grasas,
                        lista_proteinas=lista_proteinas, macros_comida=macros_comida,
                        meal_idx=meal_idx, alimentos_usados_plan=alimentos_usados_plan,
                    catalogo=catalogo)

                    comida_estructurada = ConstructorMealStructure.construir(
                        nombre_comida=nombre_comida,
                        kcal_objetivo=macros_comida['kcal'],
                        macros_objetivo={
                            'proteina': macros_comida['proteina'],
                            'carbs':    macros_comida['carbs'],
                            'grasa':    macros_comida['grasa'],
                        },
                        alimentos_dict=alimentos_dict,
                        macros_comida=macros_comida,
                        catalogo=catalogo,
                    )

                    if meal_idx == 0:
                        comida_estructurada = _aplicar_redondeo_clinico(comida_estructurada, catalogo=catalogo)

                    if comida_estructurada.get('desviacion_pct', 0) > 5:
                        comida_estructurada = ValidadorEnergia.validar_y_ajustar(
                            comida_estructurada, macros_comida['kcal'], meal_idx=meal_idx
                        , catalogo=catalogo)

                    plan[nombre_comida] = comida_estructurada

                # ── Post-processing (límites, metadatos) ──
                plan = _validar_limites_estrictos_por_plan(plan, catalogo=catalogo)

                plan['metadata_mes_anterior'] = {
                    'peso_base_mes': cliente.peso_kg,
                    'kcal_totales_mes': kcal_objetivo_para_usar,
                    'kcal_totales_sin_ajuste': kcal_objetivo_original,
                    'ajuste_aplicado': ajuste_aplicado,
                    'version_motor': '1.0',
                    'seed_base': seed_base,
                    'seed_variacion': seed_variacion,
                    'objetivo': cliente.objetivo,
                    'fecha_plan': datetime.now().isoformat(),
                }

                FACTOR_MAXIMO = 1.2
                for comida_nombre in ['desayuno', 'almuerzo', 'comida', 'cena']:
                    if comida_nombre not in plan or 'alimentos' not in plan[comida_nombre]:
                        continue
                    for ali_nombre, gramos in list(plan[comida_nombre]['alimentos'].items()):
                        if ali_nombre not in alimentos_base:
                            continue
                        limite_maximo = LIMITES_DUROS_ALIMENTOS.get(ali_nombre, 999) * FACTOR_MAXIMO
                        if gramos > limite_maximo:
                            plan[comida_nombre]['alimentos'][ali_nombre] = limite_maximo
                    kcal_obj_c = plan[comida_nombre].get('kcal_objetivo', 1)
                    kcal_real_c = sum(
                        g * alimentos_base[n]['kcal'] / 100
                        for n, g in plan[comida_nombre]['alimentos'].items()
                        if n in alimentos_base
                    )
                    plan[comida_nombre]['kcal_real'] = kcal_real_c
                    plan[comida_nombre]['desviacion_pct'] = (
                        abs(kcal_real_c - kcal_obj_c) / max(kcal_obj_c, 1) * 100
                    )

                # ── Validación final + reajuste rápido ──
                es_valido, errores_contrato = MealStructureContract.validar_plan_completo(plan)

                if not es_valido:
                    comidas_ok = sum(
                        1 for c in ['desayuno', 'almuerzo', 'comida', 'cena']
                        if c in plan and 'kcal_objetivo' in plan.get(c, {})
                    )
                    logger.warning("ALERTA Plan cumple %d/4 comidas con contrato", comidas_ok)
                    for err in errores_contrato[:5]:
                        logger.warning("  Contrato: %s", err)

                    logger.info("[REAJUSTE AUTOMATICO] Iniciando ciclo de corrección...")
                    plan, plan_corregido, logs_reajuste = ReajustadorPlan.reajustar_plan(plan, catalogo=catalogo)
                    for log in logs_reajuste:
                        logger.debug("  %s", log)

                    if plan_corregido:
                        logger.info("[OK] Plan CORREGIDO en intento %d", intento)
                        es_valido = True
                    else:
                        es_valido, errores_contrato = MealStructureContract.validar_plan_completo(plan)

                if es_valido:
                    catalogo.validate_plan(plan)
                    logger.info("Plan válido generado en intento %d/%d", intento, max_intentos)
                    return plan

                # Plan sigue inválido
                if intento < max_intentos:
                    logger.warning(
                        "Plan inválido en intento %d, reintentando. Errores: %s",
                        intento, errores_contrato[:3],
                    )
                    continue

                # Último intento agotado
                logger.error(
                    "Plan inválido después de %d intentos. Cliente: %s, Errores: %s",
                    max_intentos, cliente.id_cliente, errores_contrato,
                )
                if MODO_ESTRICTO:
                    raise PlanInvalidoError(
                        f"No se pudo generar plan válido para {cliente.nombre}",
                        errores=errores_contrato,
                        cliente_id=cliente.id_cliente,
                    )
                logger.warning("MODO_ESTRICTO=False, retornando plan inválido")
                catalogo.validate_plan(plan)
                return plan

            except (PlanInvalidoError, FoodRestrictionError):
                raise
            except Exception:  # noqa: BLE001
                logger.error(
                    "Excepción en intento %d para cliente %s",
                    intento, cliente.id_cliente, exc_info=True,
                )
                if intento == max_intentos:
                    raise


# ============================================================================
# DEMO — Solo se ejecuta con: python generador_planes.py
# ============================================================================

if __name__ == "__main__":
    def ejecutar_demo_gym():
        """Demo completa del sistema de generación de planes nutricionales."""
        from api.pdf_generator import PDFGenerator
        from config.constantes import CARPETA_PLANES

        os.makedirs(CARPETA_PLANES, exist_ok=True)
        os.makedirs("datos", exist_ok=True)

        clientes_config = [
            {
                'nombre': 'Cliente Deficit', 'id_cliente': 'DEMO_DEF',
                'edad': 30, 'peso_kg': 80.0, 'estatura_cm': 175,
                'grasa_corporal_pct': 20.0, 'nivel_actividad': 'moderada', 'objetivo': 'deficit',
            },
            {
                'nombre': 'Cliente Mantenimiento', 'id_cliente': 'DEMO_MAN',
                'edad': 28, 'peso_kg': 70.0, 'estatura_cm': 170,
                'grasa_corporal_pct': 18.0, 'nivel_actividad': 'leve', 'objetivo': 'mantenimiento',
            },
            {
                'nombre': 'Cliente Superavit', 'id_cliente': 'DEMO_SUP',
                'edad': 25, 'peso_kg': 75.0, 'estatura_cm': 180,
                'grasa_corporal_pct': 15.0, 'nivel_actividad': 'intensa', 'objetivo': 'superavit',
            },
        ]

        resultados = []

        for config in clientes_config:
            logger.info("=" * 70)
            logger.info("PROCESANDO: %s", config['nombre'].upper())
            logger.info("=" * 70)

            cliente = ClienteEvaluacion(
                nombre=config['nombre'], id_cliente=config['id_cliente'],
                edad=config['edad'], peso_kg=config['peso_kg'],
                estatura_cm=config['estatura_cm'], grasa_corporal_pct=config['grasa_corporal_pct'],
                nivel_actividad=config['nivel_actividad'], objetivo=config['objetivo'],
            )

            cliente.factor_actividad = FACTORES_ACTIVIDAD.get(cliente.nivel_actividad, 1.2)
            logger.info("[1] Cliente creado: %s", cliente.id_cliente)

            cliente = MotorNutricional.calcular_motor(cliente)
            logger.info("[2] TMB: %.0f | GET: %.0f | Kcal: %.0f", cliente.tmb, cliente.get_total, cliente.kcal_objetivo)

            kcal_ajustado, ajuste_aplicado = AjusteCaloricoMensual.aplicar_ajuste(
                cliente_id=cliente.id_cliente, peso_actual=cliente.peso_kg,
                objetivo=cliente.objetivo, kcal_objetivo_base=cliente.kcal_objetivo,
                plan_anterior=None, directorio_planes=CARPETA_PLANES
            )
            logger.info("[3] Kcal ajustado: %.0f | Ajuste: %s", kcal_ajustado, ajuste_aplicado)

            distribucion = DistribuidorComidas.distribuir(
                cliente.kcal_objetivo, cliente.proteina_g, cliente.grasa_g, cliente.carbs_g
            )
            logger.info("[4] Distribuido: Des %.0f | Alm %.0f | Com %.0f | Cen %.0f",
                        distribucion['desayuno']['kcal'], distribucion['almuerzo']['kcal'],
                        distribucion['comida']['kcal'], distribucion['cena']['kcal'])

            plan = ConstructorPlanNuevo.construir(cliente, plan_numero=1, directorio_planes=CARPETA_PLANES)

            es_valido, errores = MealStructureContract.validar_plan_completo(plan)
            if es_valido:
                logger.info("[6] Plan VÁLIDO según contrato")
            else:
                logger.warning("[6] Plan INVÁLIDO: %s", errores)
                if MODO_ESTRICTO:
                    raise Exception("Plan invalido por violacion de contrato energetico (>5%)")

            if not os.path.exists(CARPETA_SALIDA):
                os.makedirs(CARPETA_SALIDA)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_pdf = f"demo_{cliente.id_cliente}_{timestamp}.pdf"
            ruta_pdf_completa = os.path.join(CARPETA_SALIDA, nombre_pdf)

            generador_pdf = PDFGenerator()
            datos_pdf = PDFGenerator.datos_from_cliente(cliente, plan)
            from pathlib import Path as _PPath
            ruta_pdf = str(generador_pdf.generar_plan(datos_pdf, _PPath(ruta_pdf_completa)))
            print(f"  [7] PDF: {ruta_pdf}")

            comidas_validas = ['desayuno', 'almuerzo', 'comida', 'cena']
            desviacion_max = max(plan[c].get('desviacion_pct', 0) for c in comidas_validas if c in plan)
            kcal_real = sum(plan[c].get('kcal_real', 0) for c in comidas_validas if c in plan)

            resultados.append({
                'id_cliente': cliente.id_cliente, 'kcal_objetivo': cliente.kcal_objetivo,
                'kcal_real': kcal_real, 'desviacion_max': desviacion_max,
                'pdf': ruta_pdf, 'valido': es_valido,
            })

        print("\n" + "=" * 70)
        print("RESUMEN DEMO COMPLETA")
        print("=" * 70)
        for r in resultados:
            estado = "OK" if r['valido'] else "ERROR"
            print(f"  [{estado}] {r['id_cliente']}: {r['kcal_objetivo']:.0f} kcal | Desv max: {r['desviacion_max']:.2f}%")
        print("=" * 70 + "\n")

        return resultados

    ejecutar_demo_gym()

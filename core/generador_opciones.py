"""
Generador de planes nutricionales con opciones múltiples.

Este módulo implementa el sistema de generación de planes con opciones,
donde el cliente puede elegir entre múltiples alternativas equivalentes
por cada macronutriente.

Diferencias vs ConstructorPlanNuevo:
- En lugar de asignar alimentos específicos, genera LISTAS de opciones
- Cada opción es nutricionalmente equivalente (mismo macro objetivo)
- Mantiene rotación inteligente en las opciones sugeridas
- Compatible con exportación a PDF con formato especial
"""

from core.food_catalog import FoodCatalog, FoodRestrictionError
from src.alimentos_base import ALIMENTOS_BASE as _DEFAULT_FOODS, CATEGORIAS as _DEFAULT_CATEGORIES
import random
from typing import List, Dict
from datetime import datetime

from src.alimentos_base import ALIMENTOS_BASE, CATEGORIAS, EQUIVALENCIAS_PRACTICAS
from config.constantes import LIMITES_DUROS_ALIMENTOS
from core.modelos import ClienteEvaluacion
from core.motor_nutricional import MotorNutricional, AjusteCaloricoMensual
from core.generador_comidas import DistribuidorComidas
from src.gestor_rotacion import GestorRotacionAlimentos
from utils.logger import logger


class GeneradorOpcionesEquivalentes:
    """
    Genera opciones nutricionalmente equivalentes para un macronutriente.

    Ejemplo:
        gen = GeneradorOpcionesEquivalentes()
        opciones = gen.generar_opciones_proteina(
            gramos_proteina_objetivo=30, meal_idx=0, num_opciones=3
        )
    """

    EQUIVALENCIAS = {
        'huevo': {'unidad': 'huevo', 'gramos_por_unidad': 50},
        'claras_huevo': {'unidad': 'clara', 'gramos_por_unidad': 33},
        'tortilla_maiz': {'unidad': 'tortilla', 'gramos_por_unidad': 30},
        'pan_integral': {'unidad': 'rebanada', 'gramos_por_unidad': 30},
        'aguacate': {'unidad': 'aguacate', 'gramos_por_unidad': 200},
        'banana': {'unidad': 'plátano', 'gramos_por_unidad': 120},
        'platano': {'unidad': 'plátano', 'gramos_por_unidad': 120},
        'papa': {'unidad': 'papa mediana', 'gramos_por_unidad': 150},
        'camote': {'unidad': 'camote mediano', 'gramos_por_unidad': 150},
    }

    @staticmethod
    def calcular_equivalencia(alimento: str, gramos: float, catalogo: FoodCatalog | None = None) -> str:
        """Calcula equivalencia comprensible (ej: '3 huevos', '1 pechuga mediana')."""
        # Primero intentar equivalencias de unidades contables
        # The request catalog also constrains emergency/alternative selections.
        catalogo = catalogo or FoodCatalog.from_data(_DEFAULT_FOODS, _DEFAULT_CATEGORIES)
        if alimento in GeneradorOpcionesEquivalentes.EQUIVALENCIAS:
            info = GeneradorOpcionesEquivalentes.EQUIVALENCIAS[alimento]
            cantidad = gramos / info['gramos_por_unidad']

            if cantidad >= 0.8:
                cantidad_redondeada = round(cantidad)
                if cantidad_redondeada >= 1:
                    unidad = info['unidad']
                    if cantidad_redondeada > 1 and not unidad.endswith('s'):
                        unidad += 's'
                    return f"{cantidad_redondeada} {unidad}"

        # Equivalencias especiales para proteínas
        if alimento == 'pechuga_de_pollo':
            if gramos <= 120:
                return "1 pechuga pequeña"
            elif gramos <= 160:
                return "1 pechuga mediana"
            else:
                return "1 pechuga grande"

        if alimento == 'carne_magra_res':
            if gramos <= 120:
                return "1 bistec pequeño"
            elif gramos <= 180:
                return "1 bistec mediano"
            else:
                return "1 bistec grande"

        if alimento in ('salmon', 'pescado_blanco'):
            if gramos <= 130:
                return "1 filete pequeño"
            elif gramos <= 180:
                return "1 filete mediano"
            else:
                return "1 filete grande"

        # Equivalencias para aguacate fraccionado
        if alimento == 'aguacate':
            fraccion = gramos / 200
            if 0.2 <= fraccion <= 0.3:
                return "1/4 aguacate"
            elif 0.4 <= fraccion <= 0.6:
                return "1/2 aguacate"
            elif 0.7 <= fraccion <= 0.9:
                return "3/4 aguacate"
            elif fraccion >= 1:
                return "1 aguacate completo"

        # Fallback: usar EQUIVALENCIAS_PRACTICAS de alimentos_base
        return EQUIVALENCIAS_PRACTICAS.get(alimento, "")

    @staticmethod
    def calcular_gramos_necesarios(
        alimento: str, macro_objetivo: float, tipo_macro: str
    , catalogo: FoodCatalog | None = None) -> float:
        """Calcula gramos de alimento necesarios para alcanzar objetivo de macro."""
        # The request catalog also constrains emergency/alternative selections.
        catalogo = catalogo or FoodCatalog.from_data(_DEFAULT_FOODS, _DEFAULT_CATEGORIES)
        alimentos_base = catalogo.alimentos
        if alimento not in alimentos_base:
            return 0.0

        datos_alimento = alimentos_base[alimento]
        macro_por_100g = datos_alimento.get(tipo_macro, 0)

        if macro_por_100g <= 0:
            return 0.0

        gramos_necesarios = (macro_objetivo / macro_por_100g) * 100

        # Aplicar límite máximo del alimento
        limite = LIMITES_DUROS_ALIMENTOS.get(alimento, 300)
        gramos_final = min(gramos_necesarios, limite)

        # Redondear a múltiplos de 5g para claridad
        gramos_final = round(gramos_final / 5) * 5

        return max(gramos_final, 10)  # Mínimo 10g

    @staticmethod
    def calcular_macros_reales(alimento: str, gramos: float, catalogo: FoodCatalog | None = None) -> Dict[str, float]:
        """Calcula macros reales aportados por cantidad de alimento."""
        # The request catalog also constrains emergency/alternative selections.
        catalogo = catalogo or FoodCatalog.from_data(_DEFAULT_FOODS, _DEFAULT_CATEGORIES)
        alimentos_base = catalogo.alimentos
        if alimento not in alimentos_base:
            return {'proteina': 0, 'carbs': 0, 'grasa': 0, 'kcal': 0}

        datos = alimentos_base[alimento]
        factor = gramos / 100

        return {
            'proteina': round(datos.get('proteina', 0) * factor, 1),
            'carbs': round(datos.get('carbs', 0) * factor, 1),
            'grasa': round(datos.get('grasa', 0) * factor, 1),
            'kcal': round(datos.get('kcal', 0) * factor, 0)
        }

    @staticmethod
    def _generar_opciones_macro(
        macro_objetivo: float,
        tipo_macro: str,
        lista_alimentos: list,
        prioridades_comida: list,
        meal_idx: int,
        num_opciones: int,
        penalizados: list,
        seed: int | None,
        seed_offset: int,
        umbral_minimo: float,
        catalogo: FoodCatalog | None = None,
    ) -> List[Dict]:
        """Método interno genérico para generar opciones de un macronutriente."""
        # The request catalog also constrains emergency/alternative selections.
        catalogo = catalogo or FoodCatalog.from_data(_DEFAULT_FOODS, _DEFAULT_CATEGORIES)
        permitted = catalogo.require_candidates(lista_alimentos)
        # Rotation penalties are preferences. They may be relaxed within the
        # permitted catalog; safety exclusions cannot be relaxed.
        disponibles = [a for a in permitted if a not in penalizados] or permitted

        # Ordenar: primero prioritarios, luego resto
        ordenados = []
        for p in prioridades_comida:
            if p in disponibles:
                ordenados.append(p)
        for a in disponibles:
            if a not in ordenados:
                ordenados.append(a)

        # Aplicar seed para reproducibilidad
        if seed is not None:
            rng = random.Random(seed + meal_idx + seed_offset)
            if len(ordenados) > 3:
                resto = ordenados[3:]
                rng.shuffle(resto)
                ordenados = ordenados[:3] + resto

        # Generar opciones (pool amplio para asegurar suficientes candidatos)
        opciones = []
        for alimento in ordenados:
            gramos = GeneradorOpcionesEquivalentes.calcular_gramos_necesarios(
                alimento, macro_objetivo, tipo_macro, catalogo=catalogo
            )

            if gramos < 5:
                continue

            macros = GeneradorOpcionesEquivalentes.calcular_macros_reales(alimento, gramos, catalogo=catalogo)
            equivalencia = GeneradorOpcionesEquivalentes.calcular_equivalencia(alimento, gramos, catalogo=catalogo)

            # Validar que aporte al menos el umbral del objetivo
            if macros[tipo_macro] >= macro_objetivo * umbral_minimo:
                opciones.append({
                    'alimento': alimento,
                    'gramos': gramos,
                    'equivalencia': equivalencia,
                    'macros': macros
                })

            if len(opciones) >= num_opciones:
                break

        if not opciones:
            raise FoodRestrictionError("No hay porciones válidas para estas restricciones y objetivos.")
        return opciones[:num_opciones]

    @staticmethod
    def generar_opciones_proteina(
        gramos_proteina_objetivo: float,
        meal_idx: int,
        num_opciones: int = 3,
        alimentos_penalizados: Dict[str, List[str]] | None = None,
        seed: int | None = None,
        catalogo: FoodCatalog | None = None,
    ) -> List[Dict]:
        """Genera N opciones equivalentes de proteína."""
        # The request catalog also constrains emergency/alternative selections.
        catalogo = catalogo or FoodCatalog.from_data(_DEFAULT_FOODS, _DEFAULT_CATEGORIES)
        categorias = catalogo.categorias
        penalizados = (alimentos_penalizados or {}).get('proteina', [])

        prioridades = {
            0: ['huevo', 'claras_huevo', 'yogurt_griego_light', 'proteina_suero'],
            1: ['pechuga_de_pollo', 'queso_panela', 'pescado_blanco'],
            2: ['carne_magra_res', 'salmon', 'pechuga_de_pollo'],
            3: ['pescado_blanco', 'claras_huevo', 'queso_panela'],
        }.get(meal_idx, [])

        return GeneradorOpcionesEquivalentes._generar_opciones_macro(
            macro_objetivo=gramos_proteina_objetivo,
            tipo_macro='proteina',
            lista_alimentos=categorias['proteina'],
            prioridades_comida=prioridades,
            meal_idx=meal_idx,
            num_opciones=num_opciones,
            penalizados=penalizados,
            seed=seed,
            seed_offset=0,
            umbral_minimo=0.7, catalogo=catalogo,
        )

    @staticmethod
    def generar_opciones_carbs(
        gramos_carbs_objetivo: float,
        meal_idx: int,
        num_opciones: int = 3,
        alimentos_penalizados: Dict[str, List[str]] | None = None,
        seed: int | None = None,
        catalogo: FoodCatalog | None = None,
    ) -> List[Dict]:
        """Genera N opciones equivalentes de carbohidratos."""
        # The request catalog also constrains emergency/alternative selections.
        catalogo = catalogo or FoodCatalog.from_data(_DEFAULT_FOODS, _DEFAULT_CATEGORIES)
        alimentos_base = catalogo.alimentos
        categorias = catalogo.categorias
        from utils.logger import logger
        
        penalizados = (alimentos_penalizados or {}).get('carbs', [])

        # FALLBACK por comida si pool queda vacío
        FALLBACK_CARBS_POR_COMIDA = {
            0: ['avena', 'granola', 'pan_integral'],        # desayuno
            1: ['arroz_blanco', 'papa', 'camote', 'tortilla_maiz'],  # almuerzo  
            2: ['arroz_integral', 'pasta_integral', 'papa', 'frijoles'],  # comida
            3: ['tortilla_harina', 'papa', 'camote'],       # cena
        }

        prioridades = {
            0: ['avena', 'pan_integral', 'tortilla_maiz'],
            1: ['arroz_blanco', 'papa', 'tortilla_maiz', 'camote'],
            2: ['arroz_integral', 'camote', 'papa', 'frijoles', 'quinoa'],
            3: ['papa', 'arroz_blanco', 'camote', 'tortilla_maiz'],
        }.get(meal_idx, [])

        # FIX: Filtrar alimentos por meal_idx usando restricciones en ALIMENTOS_BASE
        from src.alimentos_base import ALIMENTOS_BASE
        candidatos_carbs = [
            a for a in categorias['carbs']
            if a in alimentos_base and meal_idx in alimentos_base[a].get('meal_idx', [0, 1, 2, 3])
        ]
        
        # Si candidatos queda vacío, usar fallback hardcoded
        if not candidatos_carbs:
            candidatos_carbs = catalogo.require_candidates([
                name for name in FALLBACK_CARBS_POR_COMIDA.get(meal_idx, [])
                if meal_idx in alimentos_base.get(name, {}).get('meal_idx', [0, 1, 2, 3])
            ])
            logger.warning(
                "[OPCIONES] meal_idx=%d: pool vacío, usando fallback: %s",
                meal_idx, candidatos_carbs,
            )

        # FIX: Si el objetivo es 0 o muy bajo, usar mínimo representativo
        if gramos_carbs_objetivo <= 5:
            logger.warning(
                "[OPCIONES] meal_idx=%d: gramos_carbs_objetivo=%.1f muy bajo, "
                "se usará mínimo de 30g para generar opciones representativas",
                meal_idx, gramos_carbs_objetivo,
            )
            gramos_carbs_objetivo = 30.0

        opciones = GeneradorOpcionesEquivalentes._generar_opciones_macro(
            macro_objetivo=gramos_carbs_objetivo,
            tipo_macro='carbs',
            lista_alimentos=candidatos_carbs,
            prioridades_comida=prioridades,
            meal_idx=meal_idx,
            num_opciones=num_opciones,
            penalizados=penalizados,
            seed=seed,
            seed_offset=100,
            umbral_minimo=0.4, catalogo=catalogo,  # FIX: bajado de 0.5 para mayor tolerancia
        )
        
        # Debug log para facilitar debugging
        logger.debug(
            "[OPCIONES] meal_idx=%d generó %d opciones de carbs: %s",
            meal_idx, len(opciones), [o['alimento'] for o in opciones]
        )
        
        return opciones

    @staticmethod
    def generar_opciones_grasas(
        gramos_grasa_objetivo: float,
        meal_idx: int,
        num_opciones: int = 3,
        alimentos_penalizados: Dict[str, List[str]] | None = None,
        seed: int | None = None,
        catalogo: FoodCatalog | None = None,
    ) -> List[Dict]:
        """Genera N opciones equivalentes de grasas."""
        # The request catalog also constrains emergency/alternative selections.
        catalogo = catalogo or FoodCatalog.from_data(_DEFAULT_FOODS, _DEFAULT_CATEGORIES)
        categorias = catalogo.categorias
        penalizados = (alimentos_penalizados or {}).get('grasa', [])

        prioridades = {
            0: ['aguacate', 'nueces', 'almendras', 'mantequilla_mani'],
            1: ['aguacate', 'aceite_de_oliva', 'nueces'],
            2: ['aceite_de_oliva', 'aguacate', 'mantequilla_mani'],
            3: ['aceite_de_oliva', 'nueces', 'aguacate'],
        }.get(meal_idx, [])

        return GeneradorOpcionesEquivalentes._generar_opciones_macro(
            macro_objetivo=gramos_grasa_objetivo,
            tipo_macro='grasa',
            lista_alimentos=categorias['grasa'],
            prioridades_comida=prioridades,
            meal_idx=meal_idx,
            num_opciones=num_opciones,
            penalizados=penalizados,
            seed=seed,
            seed_offset=200,
            umbral_minimo=0.6, catalogo=catalogo,
        )


class ConstructorPlanConOpciones:
    """
    Constructor de planes nutricionales con opciones múltiples.

    Equivalente a ConstructorPlanNuevo pero genera opciones en lugar de
    alimentos fijos.
    """

    @staticmethod
    def construir(
        cliente: ClienteEvaluacion,
        plan_numero: int = 1,
        directorio_planes: str = ".",
        num_opciones_por_macro: int = 3,
        catalogo: FoodCatalog | None = None,
    ) -> Dict:
        """Construye plan con opciones múltiples."""
        # The request catalog also constrains emergency/alternative selections.
        catalogo = catalogo or FoodCatalog.from_data(_DEFAULT_FOODS, _DEFAULT_CATEGORIES)
        alimentos_base = catalogo.alimentos
        categorias = catalogo.categorias
        logger.info("[OPCIONES] Generando plan con opciones para %s", cliente.nombre)

        # Calcular ajuste calórico (igual que ConstructorPlanNuevo)
        from utils.helpers import cargar_plan_anterior_cliente

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

        if ajuste_aplicado:
            macros_finales = MotorNutricional.calcular_macros(cliente.peso_kg, kcal_objetivo_para_usar)
        else:
            macros_finales = {
                'proteina_g': cliente.proteina_g,
                'grasa_g': cliente.grasa_g,
                'carbs_g': cliente.carbs_g,
            }

        # Distribuir macros por comida
        distribucion = DistribuidorComidas.distribuir(
            kcal_objetivo_para_usar,
            macros_finales['proteina_g'],
            macros_finales['grasa_g'],
            macros_finales['carbs_g'],
        )

        # Rotación inteligente
        gestor_rotacion = GestorRotacionAlimentos(cliente.id_cliente)
        penalizados_por_cat = gestor_rotacion.obtener_penalizados()

        # Seed para reproducibilidad
        from core.selector_alimentos import generar_seed_bloques
        seed_base, seed_variacion = generar_seed_bloques(cliente, gym_id="default")
        seed = seed_base if plan_numero <= 3 else seed_variacion

        generador = GeneradorOpcionesEquivalentes()

        plan: Dict = {}

        for meal_idx, (nombre_comida, macros_comida) in enumerate(distribucion.items()):
            logger.info(
                "[OPCIONES] Generando %s: %.0f kcal",
                nombre_comida, macros_comida['kcal']
            )

            opciones_proteina = generador.generar_opciones_proteina(
                gramos_proteina_objetivo=macros_comida['proteina'],
                meal_idx=meal_idx,
                num_opciones=num_opciones_por_macro,
                alimentos_penalizados=penalizados_por_cat,
                seed=seed + meal_idx, catalogo=catalogo,
            )

            opciones_carbs = generador.generar_opciones_carbs(
                gramos_carbs_objetivo=macros_comida['carbs'],
                meal_idx=meal_idx,
                num_opciones=num_opciones_por_macro,
                alimentos_penalizados=penalizados_por_cat,
                seed=seed + meal_idx, catalogo=catalogo,
            )

            opciones_grasas = generador.generar_opciones_grasas(
                gramos_grasa_objetivo=macros_comida['grasa'],
                meal_idx=meal_idx,
                num_opciones=num_opciones_por_macro,
                alimentos_penalizados=penalizados_por_cat,
                seed=seed + meal_idx, catalogo=catalogo,
            )

            # Vegetales: siempre 125g de verduras variadas bajas en calorías
            VEGETALES_POOL = [
                'brocoli', 'espinaca', 'calabacita', 'coliflor',
                'pepino', 'lechuga', 'apio', 'champiñones',
                'ejotes', 'chayote', 'nopales', 'tomate',
            ]
            # Filtrar solo los que existen en la base de alimentos
            vegetales_disponibles = [
                v for v in VEGETALES_POOL if v in alimentos_base
            ]
            if not vegetales_disponibles:
                vegetales_disponibles = catalogo.require_candidates(categorias.get('verdura', ()))

            # Seleccionar 3 vegetales variados por comida (rotan por meal_idx)
            rng_veg = random.Random(seed + meal_idx + 500)
            rotados = vegetales_disponibles[:]
            rng_veg.shuffle(rotados)
            seleccion_veg = rotados[:3]

            # Distribuir 125g entre los vegetales seleccionados
            gramos_por_vegetal = [45, 40, 40]  # total = 125g
            vegetales_lista = []
            for vi, veg_nombre in enumerate(seleccion_veg):
                g = gramos_por_vegetal[vi] if vi < len(gramos_por_vegetal) else 40
                vegetales_lista.append({
                    'alimento': veg_nombre,
                    'gramos': g,
                    'macros': generador.calcular_macros_reales(veg_nombre, g, catalogo=catalogo),
                })

            plan[nombre_comida] = {
                'kcal_objetivo': macros_comida['kcal'],
                'tipo_plan': 'opciones',
                'proteinas': {
                    'cantidad_objetivo': macros_comida['proteina'],
                    'opciones': opciones_proteina,
                },
                'carbohidratos': {
                    'cantidad_objetivo': macros_comida['carbs'],
                    'opciones': opciones_carbs,
                },
                'grasas': {
                    'cantidad_objetivo': macros_comida['grasa'],
                    'opciones': opciones_grasas,
                },
                'vegetales': vegetales_lista,
            }

        # Metadata
        plan['metadata'] = {
            'tipo_plan': 'opciones',
            'num_opciones_por_macro': num_opciones_por_macro,
            'peso_base': cliente.peso_kg,
            'kcal_totales': kcal_objetivo_para_usar,
            'objetivo': cliente.objetivo,
            'fecha_plan': datetime.now().isoformat(),
            'version_motor': '2.0-opciones',
        }

        logger.info(
            "[OPCIONES] Plan generado exitosamente con %d opciones por macro",
            num_opciones_por_macro,
        )

        catalogo.validate_plan(plan)
        return plan

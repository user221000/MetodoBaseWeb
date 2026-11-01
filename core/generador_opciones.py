"""
Planes con opciones independientes y combinaciones energéticas verificadas.

El constructor resuelve una comida completa antes de proponer alternativas.
Todas las combinaciones publicadas conservan la tolerancia energética del 5 %.
Los objetivos se muestran separados del aporte real y de su rango de energía.
"""

import math
import random
from datetime import datetime
from itertools import product
from typing import ClassVar

from config.constantes import LIMITES_DUROS_ALIMENTOS, MINIMOS_POR_ALIMENTO
from core.food_catalog import FoodCatalog, FoodRestrictionError
from core.generador_comidas import DistribuidorComidas
from core.modelos import ClienteEvaluacion
from core.motor_nutricional import AjusteCaloricoMensual, MotorNutricional
from core.nutrition_restrictions import generation_catalog
from core.selector_alimentos import SelectorAlimentos
from src.alimentos_base import ALIMENTOS_BASE as _DEFAULT_FOODS
from src.alimentos_base import CATEGORIAS as _DEFAULT_CATEGORIES
from src.alimentos_base import (
    EQUIVALENCIAS_PRACTICAS,
    LIMITES_ALIMENTOS,
)
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

    EQUIVALENCIAS: ClassVar[dict] = {
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
    def calcular_macros_reales(alimento: str, gramos: float, catalogo: FoodCatalog | None = None) -> dict[str, float]:
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
    ) -> list[dict]:
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
        alimentos_penalizados: dict[str, list[str]] | None = None,
        seed: int | None = None,
        catalogo: FoodCatalog | None = None,
    ) -> list[dict]:
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
        alimentos_penalizados: dict[str, list[str]] | None = None,
        seed: int | None = None,
        catalogo: FoodCatalog | None = None,
    ) -> list[dict]:
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
        alimentos_penalizados: dict[str, list[str]] | None = None,
        seed: int | None = None,
        catalogo: FoodCatalog | None = None,
    ) -> list[dict]:
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


_GROUPS = (('proteinas', 'proteina'), ('carbohidratos', 'carbs'), ('grasas', 'grasa'))
_NUTRIENTS = ('proteina', 'carbs', 'grasa', 'kcal')
_ENERGY_TOLERANCE = 0.05
# Covers every current category (171 foods total) without allowing an
# unbounded catalog expansion to create unbounded Cartesian searches.
_MAX_CANDIDATES = 48


def _portion_bounds(food: str) -> tuple[int, int]:
    """Use the intersection of existing catalog and hard limits, in whole grams."""
    lower = max(1, math.ceil(MINIMOS_POR_ALIMENTO.get(food, 0)))
    upper = math.floor(min(LIMITES_ALIMENTOS.get(food, 300), LIMITES_DUROS_ALIMENTOS.get(food, 300)))
    return lower, upper


def _nutrients(catalog: FoodCatalog, food: str, grams: float) -> dict[str, float]:
    return {key: catalog.alimentos[food][key] * grams / 100 for key in _NUTRIENTS}


def _sum_nutrients(parts) -> dict[str, float]:
    return {key: sum(part[key] for part in parts) for key in _NUTRIENTS}


def _option(catalog: FoodCatalog, food: str, grams: int) -> dict:
    return {
        'alimento': food, 'gramos': grams,
        'equivalencia': GeneradorOpcionesEquivalentes.calcular_equivalencia(food, grams, catalogo=catalog),
        'macros': _nutrients(catalog, food, grams),
    }


def _solve_portions(catalog: FoodCatalog, foods: tuple[str, ...], target: dict) -> list[float] | None:
    """Solve the three foods jointly; each contributes all three macronutrients."""
    rows = [[catalog.alimentos[food][macro] / 100 for food in foods] + [target[macro]]
            for macro in ('proteina', 'carbs', 'grasa')]
    for column in range(3):
        pivot = max(range(column, 3), key=lambda index: abs(rows[index][column]))
        if abs(rows[pivot][column]) < 1e-10:
            return None
        rows[column], rows[pivot] = rows[pivot], rows[column]
        divisor = rows[column][column]
        rows[column] = [value / divisor for value in rows[column]]
        for index in range(3):
            if index == column:
                continue
            factor = rows[index][column]
            rows[index] = [value - factor * pivot_value for value, pivot_value in zip(rows[index], rows[column])]
    grams = [row[3] for row in rows]
    return grams if all(math.isfinite(value) and value > 0 for value in grams) else None


def _energy_range(groups: dict, vegetables: list, catalog: FoodCatalog) -> tuple[float, float]:
    vegetable_energy = sum(_nutrients(catalog, row['alimento'], row['gramos'])['kcal'] for row in vegetables)
    # Choices are independent, so summing each group's extrema is the exact
    # minimum/maximum over its complete Cartesian product, not a sampled menu.
    energies = [[_nutrients(catalog, row['alimento'], row['gramos'])['kcal']
                 for row in groups[group]] for group, _ in _GROUPS]
    return (vegetable_energy + sum(min(values) for values in energies),
            vegetable_energy + sum(max(values) for values in energies))


def _energy_valid(groups: dict, vegetables: list, target: float, catalog: FoodCatalog) -> bool:
    minimum, maximum = _energy_range(groups, vegetables, catalog)
    return minimum >= target * (1 - _ENERGY_TOLERANCE) - 1e-8 and maximum <= target * (1 + _ENERGY_TOLERANCE) + 1e-8


def _vegetables(catalog: FoodCatalog, meal: int, seed: int) -> list[dict]:
    """Keep the existing 125 g total while respecting eligibility and portions."""
    candidates = [food for food in catalog.categorias['verdura']
                  if catalog.alimentos[food].get('auto_generation', True)
                  and meal in catalog.alimentos[food]['meal_idx'] and _portion_bounds(food)[1] > 0]
    random.Random(seed + meal + 500).shuffle(candidates)
    # Three vegetables are a preference. Additional permitted vegetables may
    # be used if their configured limits cannot accommodate the existing total.
    chosen = []
    for food in candidates:
        lower, upper = _portion_bounds(food)
        if lower > upper:
            continue
        chosen.append(food)
        if len(chosen) >= min(3, len(candidates)) and sum(_portion_bounds(name)[1] for name in chosen) >= 125:
            break
    if not chosen or sum(_portion_bounds(food)[0] for food in chosen) > 125 or sum(_portion_bounds(food)[1] for food in chosen) < 125:
        raise FoodRestrictionError('No hay porciones de vegetales compatibles para esta comida.')
    grams = [_portion_bounds(food)[0] for food in chosen]
    remaining = 125 - sum(grams)
    # Allocate one gram at a time so small per-food limits are never exceeded.
    while remaining:
        for index, food in enumerate(chosen):
            if grams[index] < _portion_bounds(food)[1]:
                grams[index] += 1
                remaining -= 1
                if not remaining:
                    break
    return [{'alimento': food, 'gramos': weight, 'macros': _nutrients(catalog, food, weight)}
            for food, weight in zip(chosen, grams)]


def _build_meal(catalog: FoodCatalog, targets: dict, meal: int, seed: int,
                plan_number: int, penalties: dict, requested: int) -> dict:
    if any(not isinstance(targets[key], (int, float)) or not math.isfinite(targets[key])
           or targets[key] <= 0 for key in ('kcal', 'proteina', 'carbs', 'grasa')):
        raise FoodRestrictionError('Los objetivos no permiten construir porciones compatibles. Revisa los datos con tu profesional.')
    candidates = {
        group: [food for food in SelectorAlimentos.seleccionar_lista(
            macro, meal_idx=meal, seed=seed, plan_numero=plan_number,
            alimentos_penalizados=penalties, catalogo=catalog,
        ) if catalog.alimentos[food][macro] > 0 and _portion_bounds(food)[0] <= _portion_bounds(food)[1]][:_MAX_CANDIDATES]
        for group, macro in _GROUPS
    }
    groups = None
    seen_vegetables = set()
    # A random vegetable preference must not make an otherwise feasible meal
    # unavailable. Search a bounded set of permitted 125 g layouts jointly.
    for attempt in range(8):
        try:
            vegetables = _vegetables(catalog, meal, seed + attempt * 104729)
        except FoodRestrictionError:
            continue
        vegetable_signature = tuple(sorted((row['alimento'], row['gramos']) for row in vegetables))
        if vegetable_signature in seen_vegetables:
            continue
        seen_vegetables.add(vegetable_signature)
        vegetable_totals = _sum_nutrients([_nutrients(catalog, row['alimento'], row['gramos']) for row in vegetables])
        residual = {macro: targets[macro] - vegetable_totals[macro] for _, macro in _GROUPS}
        if any(value <= 0 for value in residual.values()):
            continue
        for foods in product(*(candidates[group] for group, _ in _GROUPS)):
            solved = _solve_portions(catalog, foods, residual)
            if solved is None:
                continue
            weights = [round(value) for value in solved]
            if any(not _portion_bounds(food)[0] <= grams <= _portion_bounds(food)[1] for food, grams in zip(foods, weights)):
                continue
            proposed = {group: [_option(catalog, food, grams)]
                        for (group, _), food, grams in zip(_GROUPS, foods, weights)}
            if _energy_valid(proposed, vegetables, targets['kcal'], catalog):
                groups = proposed
                break
        if groups is not None:
            break
    if groups is None:
        raise FoodRestrictionError('No hay una combinación de porciones que respete los objetivos y límites. Revisa la selección con tu profesional.')

    # Each alternative matches its base food's contribution, not the whole
    # meal target (the other groups and vegetables also contribute nutrients).
    for group, macro in _GROUPS:
        reference = groups[group][0]['macros'][macro]
        for food in candidates[group]:
            if len(groups[group]) >= requested:
                break
            if food == groups[group][0]['alimento']:
                continue
            grams = round(reference * 100 / catalog.alimentos[food][macro])
            if not _portion_bounds(food)[0] <= grams <= _portion_bounds(food)[1]:
                continue
            alternative = _option(catalog, food, grams)
            groups[group].append(alternative)
            if not _energy_valid(groups, vegetables, targets['kcal'], catalog):
                groups[group].pop()

    minimum, maximum = _energy_range(groups, vegetables, catalog)
    actual = _sum_nutrients([groups[group][0]['macros'] for group, _ in _GROUPS] + [vegetable_totals])
    result = {
        'tipo_plan': 'opciones', 'kcal_objetivo': targets['kcal'],
        'kcal_real': actual['kcal'], 'macros_reales': actual,
        'energia_min': minimum, 'energia_max': maximum,
        'desviacion_pct': max(abs(minimum - targets['kcal']), abs(maximum - targets['kcal'])) / targets['kcal'] * 100,
        'base_selection': {group: 0 for group, _ in _GROUPS},
        'vegetales': vegetables,
    }
    for group, macro in _GROUPS:
        result[group] = {'cantidad_objetivo': targets[macro], 'aporte_referencia': groups[group][0]['macros'][macro],
                         'num_opciones': len(groups[group]), 'opciones': groups[group]}
    return result


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
    ) -> dict:
        """Construye plan con opciones múltiples."""
        # The request catalog also constrains emergency/alternative selections.
        catalogo = generation_catalog(
            cliente.nutrition_restrictions, _DEFAULT_FOODS, _DEFAULT_CATEGORIES, catalogo,
        )
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

        if type(num_opciones_por_macro) is not int or not 1 <= num_opciones_por_macro <= 12:
            raise FoodRestrictionError("Solicita entre una y doce opciones por grupo.")
        plan = {
            name: _build_meal(catalogo, targets, meal, seed, plan_numero,
                              penalizados_por_cat, num_opciones_por_macro)
            for meal, (name, targets) in enumerate(distribucion.items())
        }
        counts = {name: {group: row[group]['num_opciones'] for group, _ in _GROUPS}
                  for name, row in plan.items()}
        plan['metadata'] = {
            'tipo_plan': 'opciones',
            'num_opciones_solicitadas': num_opciones_por_macro,
            'opciones_por_comida': counts,
            'peso_base': cliente.peso_kg,
            'kcal_totales': sum(row['kcal_real'] for row in plan.values()),
            'kcal_objetivo': kcal_objetivo_para_usar,
            'energia_min': sum(row['energia_min'] for row in plan.values()),
            'energia_max': sum(row['energia_max'] for row in plan.values()),
            'objetivo': cliente.objetivo,
            'fecha_plan': datetime.now().isoformat(),
            'version_motor': '2.1-opciones-verificadas',
        }
        catalogo.validate_plan(plan)
        return plan

"""Contratos y estructura de comidas (CAPA 3)."""
import logging

from config.constantes import MODO_ESTRICTO, LEGUMINOSAS
from src.alimentos_base import ALIMENTOS_BASE, CATEGORIAS
from core.food_catalog import FoodCatalog

logger = logging.getLogger(__name__)


class MealStructureContract:
    """Contrato obligatorio para la estructura de una comida."""
    
    REQUIRED_KEYS = {'kcal_objetivo', 'macros_objetivo', 'alimentos', 'kcal_real', 'desviacion_pct'}
    REQUIRED_MACROS_KEYS = {'proteina', 'carbs', 'grasa'}
    
    @classmethod
    def validar(cls, comida: dict, nombre_comida: str) -> tuple[bool, list[str]]:
        """Valida que una comida cumpla el contrato."""
        errores = []
        
        if not isinstance(comida, dict):
            return False, [f"[FAIL] CONTRATO: {nombre_comida} debe ser dict, es {type(comida)}"]
        
        keys_faltantes = cls.REQUIRED_KEYS - set(comida.keys())
        if keys_faltantes:
            errores.append(f"[FAIL] CONTRATO: {nombre_comida} falta keys: {keys_faltantes}")
        
        if 'kcal_objetivo' not in comida:
            errores.append(f"[FAIL] CRITICO: {nombre_comida} DEBE tener 'kcal_objetivo'")
        elif not isinstance(comida['kcal_objetivo'], (int, float)):
            errores.append(f"[FAIL] CONTRATO: {nombre_comida}['kcal_objetivo'] debe ser float, es {type(comida['kcal_objetivo'])}")
        elif comida['kcal_objetivo'] <= 0:
            errores.append(f"[FAIL] CONTRATO: {nombre_comida}['kcal_objetivo'] debe ser > 0, es {comida['kcal_objetivo']}")
        
        if 'kcal_real' not in comida:
            errores.append(f"[FAIL] CRITICO: {nombre_comida} DEBE tener 'kcal_real'")
        elif not isinstance(comida['kcal_real'], (int, float)):
            errores.append(f"[FAIL] CONTRATO: {nombre_comida}['kcal_real'] debe ser float, es {type(comida['kcal_real'])}")
        
        if 'desviacion_pct' not in comida:
            errores.append(f"[FAIL] CRITICO: {nombre_comida} DEBE tener 'desviacion_pct'")
        elif isinstance(comida['desviacion_pct'], (int, float)):
            if comida['desviacion_pct'] > 5.0:
                if MODO_ESTRICTO:
                    errores.append(f"[FAIL] ENERGIA: {nombre_comida} desviacion {comida['desviacion_pct']:.2f}% > 5% (maximo permitido)")
                else:
                    errores.append(f"!ALERTA: {nombre_comida} desviacion {comida['desviacion_pct']:.2f}% > 5% (maximo permitido)")
        
        if 'macros_objetivo' not in comida:
            errores.append(f"[FAIL] CONTRATO: {nombre_comida} falta 'macros_objetivo'")
        elif isinstance(comida['macros_objetivo'], dict):
            macros_faltantes = cls.REQUIRED_MACROS_KEYS - set(comida['macros_objetivo'].keys())
            if macros_faltantes:
                errores.append(f"[FAIL] CONTRATO: {nombre_comida}['macros_objetivo'] falta keys: {macros_faltantes}")
        
        if 'alimentos' not in comida:
            errores.append(f"[FAIL] CONTRATO: {nombre_comida} falta 'alimentos'")
        elif not isinstance(comida['alimentos'], dict):
            errores.append(f"[FAIL] CONTRATO: {nombre_comida}['alimentos'] debe ser dict, es {type(comida['alimentos'])}")
        
        return len(errores) == 0, errores
    
    @classmethod
    def validar_plan_completo(cls, plan: dict) -> tuple[bool, list[str]]:
        """Valida todas las comidas del plan."""
        errores = []
        comidas_requeridas = {'desayuno', 'almuerzo', 'comida', 'cena'}
        hay_error_critico = False
        
        for comida_nombre in comidas_requeridas:
            if comida_nombre not in plan:
                errores.append(f"[FAIL] CRITICO: Plan falta comida '{comida_nombre}'")
                hay_error_critico = True
            else:
                es_valida, errs_comida = cls.validar(plan[comida_nombre], comida_nombre)
                errores.extend(errs_comida)
                if MODO_ESTRICTO and not es_valida:
                    hay_error_critico = True
        
        if 'metadata_mes_anterior' not in plan:
            errores.append("!ALERTA: Plan falta 'metadata_mes_anterior'")
        
        if MODO_ESTRICTO:
            errores_criticos = [e for e in errores if e.startswith('[FAIL]')]
            return len(errores_criticos) == 0, errores
        
        return len(errores) == 0, errores


class ConstructorMealStructure:
    """
    Constructor de estructura de comida garantizando contrato de capa 3.
    CONTRATO GARANTIZADO: Siempre retorna dict con todas las keys obligatorias.
    """
    
    @staticmethod
    def construir(
        nombre_comida: str,
        kcal_objetivo: float,
        macros_objetivo: dict,
        alimentos_dict: dict,
        macros_comida: dict = None,
        catalogo: FoodCatalog | None = None,
    ) -> dict:
        """Construye estructura de comida completa con validación contractual."""
        catalogo = catalogo or FoodCatalog.from_data(ALIMENTOS_BASE, CATEGORIAS)
        catalogo.validate_plan({nombre_comida: {"alimentos": alimentos_dict}})
        assert isinstance(kcal_objetivo, (int, float)), f"kcal_objetivo debe ser número, es {type(kcal_objetivo)}"
        assert kcal_objetivo > 0, f"kcal_objetivo debe ser > 0, es {kcal_objetivo}"
        assert isinstance(alimentos_dict, dict), f"alimentos_dict debe ser dict"
        
        # Redondear gramos a múltiplos de 10
        alimentos_dict = {
            ali: round(gramos / 10) * 10
            for ali, gramos in alimentos_dict.items()
        }
        
        # Validación estructural: Limitar fuentes de carbohidrato
        meal_idx_map = {'desayuno': 0, 'almuerzo': 1, 'comida': 2, 'cena': 3}
        meal_idx = meal_idx_map.get(nombre_comida, 0)
        
        if meal_idx in (1, 2):
            max_carbs = 2
        else:
            max_carbs = 1
        
        carbs_set = set(catalogo.categorias.get('carbs', []))
        carbs_set.update(LEGUMINOSAS)
        
        fuentes_carb = [(ali, gramos) for ali, gramos in alimentos_dict.items() if ali in carbs_set]
        
        if len(fuentes_carb) > max_carbs:
            fuentes_carb_ordenadas = sorted(fuentes_carb, key=lambda x: x[1], reverse=True)
            fuentes_a_mantener = set(ali for ali, _ in fuentes_carb_ordenadas[:max_carbs])
            fuentes_a_eliminar = [ali for ali, _ in fuentes_carb if ali not in fuentes_a_mantener]
            for ali in fuentes_a_eliminar:
                del alimentos_dict[ali]
        
        # Calcular kcal reales
        kcal_real = 0.0
        for ali_nombre, gramos in alimentos_dict.items():
            if ali_nombre in catalogo.alimentos:
                kcal_real += gramos * (catalogo.alimentos[ali_nombre]['kcal'] / 100)
        
        desviacion_pct = abs(kcal_real - kcal_objetivo) / max(kcal_objetivo, 1) * 100
        
        comida_estructurada = {
            'kcal_objetivo': kcal_objetivo,
            'macros_objetivo': macros_objetivo,
            'alimentos': alimentos_dict if alimentos_dict else {},
            'kcal_real': kcal_real,
            'desviacion_pct': desviacion_pct,
        }
        
        es_valida, errores = MealStructureContract.validar(comida_estructurada, nombre_comida)
        if not es_valida:
            logger.warning("ALERTA: %s no cumple contrato: %s", nombre_comida, "; ".join(errores))
        
        return comida_estructurada

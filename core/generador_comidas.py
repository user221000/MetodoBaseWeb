"""CAPA 3: Distribución, cálculo de gramos, reajuste y validación energética."""
import random

from config.constantes import (
    PROTEINAS_ESTRUCTURALES, PROTEINAS_MIXTAS, LEGUMINOSAS,
    LIMITES_DUROS_ALIMENTOS, MINIMOS_POR_ALIMENTO, ALIMENTOS_LIMITE_ESTRICTO,
    LEAN_PROTEINS, FATTY_PROTEINS, LIGHT_FATS, HEAVY_FATS,
)
from src.alimentos_base import ALIMENTOS_BASE, LIMITES_ALIMENTOS, CATEGORIAS


class DistribuidorComidas:
    """
    CAPA 3a: Distribuye macros por comida (20/25/30/25).

    RESPONSABILIDAD: Distribuir kcal_objetivo_final y macros según porcentajes fijos.
    NO TOCA: Selección de alimentos, cálculo de energía, estructura de comida.
    """

    @staticmethod
    def distribuir(kcal_objetivo: float, proteina_g: float, grasa_g: float, carbs_g: float) -> dict:
        """
        Distribuye caloría y macros según: Desayuno 20%, Almuerzo 25%, Comida 30%, Cena 25%.
        """
        distribucion = {
            'desayuno': {
                'kcal': kcal_objetivo * 0.20,
                'proteina': proteina_g * 0.20,
                'grasa': grasa_g * 0.20,
                'carbs': carbs_g * 0.20,
            },
            'almuerzo': {
                'kcal': kcal_objetivo * 0.25,
                'proteina': proteina_g * 0.25,
                'grasa': grasa_g * 0.25,
                'carbs': carbs_g * 0.25,
            },
            'comida': {
                'kcal': kcal_objetivo * 0.30,
                'proteina': proteina_g * 0.30,
                'grasa': grasa_g * 0.30,
                'carbs': carbs_g * 0.30,
            },
            'cena': {
                'kcal': kcal_objetivo * 0.25,
                'proteina': proteina_g * 0.25,
                'grasa': grasa_g * 0.25,
                'carbs': carbs_g * 0.25,
            },
        }
        return distribucion


# ============================================================================
# #14B NUEVO FLUJO: Cálculo por fases (Proteína → Carbs → Grasas)
# ============================================================================

class CalculadorGramosNuevo:
    """
    Nueva arquitectura: Asignación secuencial por macronutriente.
    Fases: Proteína (CONGELADA) → Carbs → Grasas → Validación energética
    """

    @staticmethod
    def asignar_proteina_estructural(
        macro_proteina_g: float,
        lista_proteinas: list,
        meal_idx: int,
        penalizados: set = None,
        alimentos_usados_plan: set = None
    ) -> tuple[dict, float, bool]:
        """
        FASE 1: Asigna proteína estructural (la más importante, CONGELADA).

        Returns:
            tuple: (dict resultado, float kcal_proteina, bool fue_congelada)
        """
        penalizados = penalizados or set()
        alimentos_usados_plan = alimentos_usados_plan or set()
        resultado = {}
        kcal_total = 0.0

        def aplicar_penalizacion_repeticion(limite_original: float, alimento: str) -> float:
            if alimento in alimentos_usados_plan:
                return limite_original * 0.80
            return limite_original

        # Reorganizar lista: normales → usadas → penalizadas
        lista_ordenada = []
        lista_penalizada = []
        lista_usada = []

        for alimento in lista_proteinas:
            if alimento in penalizados:
                lista_penalizada.append(alimento)
            elif alimento in alimentos_usados_plan:
                lista_usada.append(alimento)
            else:
                lista_ordenada.append(alimento)

        lista_final = lista_ordenada + lista_usada + lista_penalizada
        if not lista_final:
            lista_final = lista_proteinas

        # INTENTO 1: Una proteína estructural >= 80g
        for alimento_nombre in lista_final:
            if alimento_nombre not in PROTEINAS_ESTRUCTURALES:
                continue

            alimento = ALIMENTOS_BASE.get(alimento_nombre, {})
            densidad_proteina = alimento.get('proteina', 1)

            if densidad_proteina <= 0:
                continue

            gramos_posibles = macro_proteina_g / (densidad_proteina / 100)
            limite = LIMITES_DUROS_ALIMENTOS.get(alimento_nombre, 999)
            limite = aplicar_penalizacion_repeticion(limite, alimento_nombre)
            gramos_final = min(gramos_posibles, limite)

            minimo = MINIMOS_POR_ALIMENTO.get(alimento_nombre, 0)
            if gramos_final < minimo:
                continue

            if gramos_final >= 80:
                resultado[alimento_nombre] = gramos_final
                kcal_total = gramos_final * (alimento.get('kcal', 0) / 100)
                return resultado, kcal_total, True

        # INTENTO 2: Dos proteínas mixtas (solo en almuerzo)
        if meal_idx == 1:
            proteina_acum = 0.0
            kcal_acum = 0.0
            mixtas_asignadas = {}

            for alimento_nombre in lista_final[:5]:
                if alimento_nombre not in PROTEINAS_MIXTAS:
                    continue

                alimento = ALIMENTOS_BASE.get(alimento_nombre, {})
                densidad = alimento.get('proteina', 1)

                if densidad <= 0:
                    continue

                gramos_posibles = (macro_proteina_g - proteina_acum) / (densidad / 100)
                limite = LIMITES_DUROS_ALIMENTOS.get(alimento_nombre, 999)
                limite = aplicar_penalizacion_repeticion(limite, alimento_nombre)
                gramos_final = min(gramos_posibles, limite)

                minimo = MINIMOS_POR_ALIMENTO.get(alimento_nombre, 0)
                if gramos_final < minimo:
                    continue

                proteina_aportada = gramos_final * (densidad / 100)
                kcal_ali = gramos_final * (alimento.get('kcal', 0) / 100)

                if proteina_aportada >= 40:
                    mixtas_asignadas[alimento_nombre] = gramos_final
                    proteina_acum += proteina_aportada
                    kcal_acum += kcal_ali

                if len(mixtas_asignadas) >= 2 and proteina_acum >= 90:
                    return mixtas_asignadas, kcal_acum, True

        # INTENTO 3: Una mixta en comida principal (si no hay estructural)
        if meal_idx != 3:
            for alimento_nombre in lista_final:
                if alimento_nombre not in PROTEINAS_MIXTAS:
                    continue

                alimento = ALIMENTOS_BASE.get(alimento_nombre, {})
                densidad = alimento.get('proteina', 1)

                if densidad <= 0:
                    continue

                gramos_posibles = macro_proteina_g / (densidad / 100)
                limite = LIMITES_DUROS_ALIMENTOS.get(alimento_nombre, 999)
                limite = aplicar_penalizacion_repeticion(limite, alimento_nombre)
                gramos_final = min(gramos_posibles, limite)

                minimo = MINIMOS_POR_ALIMENTO.get(alimento_nombre, 0)
                if gramos_final < minimo:
                    continue

                if gramos_final >= 60:
                    resultado[alimento_nombre] = gramos_final
                    kcal_total = gramos_final * (alimento.get('kcal', 0) / 100)
                    return resultado, kcal_total, True

        # FALLBACK: Pechuga de pollo (siempre disponible)
        pechuga_name = 'pechuga_de_pollo'
        pechuga = ALIMENTOS_BASE.get(pechuga_name, {})
        if pechuga and pechuga.get('proteina', 0) > 0:
            densidad = pechuga['proteina']
            gramos_posibles = macro_proteina_g / (densidad / 100)
            limite = LIMITES_DUROS_ALIMENTOS.get(pechuga_name, 999)
            limite = aplicar_penalizacion_repeticion(limite, pechuga_name)
            gramos_final = min(gramos_posibles, limite)
            kcal = gramos_final * (pechuga.get('kcal', 0) / 100)
            return {pechuga_name: gramos_final}, kcal, True

        # Last resort fallback
        if lista_final:
            alimento_nombre = lista_final[0]
            alimento = ALIMENTOS_BASE.get(alimento_nombre, {})
            densidad = alimento.get('proteina', 1)
            if densidad > 0:
                gramos = macro_proteina_g / (densidad / 100)
                limite = LIMITES_DUROS_ALIMENTOS.get(alimento_nombre, 999)
                limite = aplicar_penalizacion_repeticion(limite, alimento_nombre)
                gramos_final = min(gramos, limite)
                kcal = gramos_final * (alimento.get('kcal', 0) / 100)
                return {alimento_nombre: gramos_final}, kcal, True

        return {}, 0.0, False

    @staticmethod
    def asignar_carbs(
        macro_carbs_g: float,
        carbs_aportados_por_proteina: float,
        lista_carbs: list,
        meal_idx: int,
        alimentos_usados_plan: set = None
    ) -> tuple[dict, float]:
        """FASE 2: Asigna carbohidratos (flexibles)."""
        alimentos_usados_plan = alimentos_usados_plan or set()
        resultado = {}
        kcal_total = 0.0

        carbs_restantes = macro_carbs_g - carbs_aportados_por_proteina
        if carbs_restantes <= 0:
            return resultado, kcal_total

        # Reordenar: no usadas primero
        lista_ordenada = [a for a in lista_carbs if a not in alimentos_usados_plan]
        lista_usadas = [a for a in lista_carbs if a in alimentos_usados_plan]
        lista_final = lista_ordenada + lista_usadas

        # Máximo de fuentes según comida
        if meal_idx in (1, 2):
            max_carbs = 2
        else:
            max_carbs = 1

        carbs_set = set(CATEGORIAS.get('carbs', []))
        carbs_set.update(LEGUMINOSAS)

        candidatos = [ali for ali in lista_final if ali in carbs_set]
        candidatos = candidatos[:max_carbs]

        for alimento_nombre in candidatos:
            if carbs_restantes <= 0:
                break

            alimento = ALIMENTOS_BASE.get(alimento_nombre, {})
            densidad = alimento.get('carbs', 1)

            if densidad <= 0:
                continue

            gramos_posibles = carbs_restantes / (densidad / 100)
            limite = LIMITES_DUROS_ALIMENTOS.get(alimento_nombre, 999)
            if alimento_nombre in ALIMENTOS_LIMITE_ESTRICTO:
                limite = LIMITES_DUROS_ALIMENTOS.get(alimento_nombre, 200)

            if alimento_nombre == 'tortilla_maiz':
                if meal_idx == 0:
                    limite = min(limite, 150)
            elif meal_idx == 3 and alimento_nombre in ('arroz_blanco', 'arroz_integral'):
                limite = min(limite, 200)

            gramos_final = min(gramos_posibles, limite)

            minimo = MINIMOS_POR_ALIMENTO.get(alimento_nombre, 0)
            if gramos_final < minimo:
                continue

            if gramos_final < 50:
                continue

            kcal = gramos_final * (alimento.get('kcal', 0) / 100)
            carbs_aportados = gramos_final * (densidad / 100)

            resultado[alimento_nombre] = gramos_final
            kcal_total += kcal
            carbs_restantes -= carbs_aportados

        return resultado, kcal_total

    @staticmethod
    def asignar_grasas(
        macro_grasa_g: float,
        grasa_aportada_por_proteina: float,
        lista_grasas: list,
        alimentos_usados_plan: set = None,
        proteina_principal: str = None
    ) -> tuple[dict, float]:
        """FASE 3: Asigna grasas (ajuste fino) considerando tipo de proteína."""
        alimentos_usados_plan = alimentos_usados_plan or set()
        resultado = {}
        kcal_total = 0.0
        grasa_restante = macro_grasa_g - grasa_aportada_por_proteina
        if grasa_restante <= 0:
            return resultado, kcal_total

        grasas_permitidas = set(lista_grasas)
        if proteina_principal in FATTY_PROTEINS:
            grasas_permitidas = grasas_permitidas & LIGHT_FATS
        else:
            grasas_permitidas = grasas_permitidas & (LIGHT_FATS | HEAVY_FATS)
        if not grasas_permitidas:
            grasas_permitidas = set(lista_grasas)

        lista_ordenada = [a for a in lista_grasas if a in grasas_permitidas and a not in alimentos_usados_plan]
        lista_usadas = [a for a in lista_grasas if a in grasas_permitidas and a in alimentos_usados_plan]
        lista_final = lista_ordenada + lista_usadas

        for alimento_nombre in lista_final:
            alimento = ALIMENTOS_BASE.get(alimento_nombre, {})
            densidad = alimento.get('grasa', 1)
            if densidad <= 0:
                continue
            gramos_posibles = grasa_restante / (densidad / 100)
            limite = LIMITES_DUROS_ALIMENTOS.get(alimento_nombre, 999)
            gramos_final = min(gramos_posibles, limite)
            minimo = MINIMOS_POR_ALIMENTO.get(alimento_nombre, 0)
            if gramos_final < minimo:
                continue
            kcal = gramos_final * (alimento.get('kcal', 0) / 100)
            grasa_aportada = gramos_final * (densidad / 100)
            resultado[alimento_nombre] = gramos_final
            kcal_total += kcal
            grasa_restante -= grasa_aportada
            break
        return resultado, kcal_total

    @staticmethod
    def insertar_vegetal_base(meal_idx: int) -> dict:
        """FASE 4: Inserta vegetal automático según comida. Usa solo alimentos de ALIMENTOS_BASE."""
        opciones = {
            0: [  # Desayuno
                ("espinaca", 80),
                ("brocoli", 150),
                ("champiñones", 100),
                ("calabacita", 120),
                ("coliflor", 100),
            ],
            1: [  # Almuerzo
                ("espinaca", 150),
                ("calabacita", 150),
                ("brocoli", 150),
                ("champiñones", 120),
                ("coliflor", 120),
            ],
            2: [  # Comida
                ("brocoli", 200),
                ("calabacita", 200),
                ("coliflor", 200),
                ("champiñones", 150),
                ("espinaca", 150),
            ],
        }
        choices = opciones.get(meal_idx, [])
        if choices:
            choices_validas = [(v, g) for v, g in choices if v in ALIMENTOS_BASE]
            if choices_validas:
                veg, gramos = random.choice(choices_validas)
                return {veg: gramos}
        return {}

    @staticmethod
    def validar_energetica(
        resultado: dict,
        kcal_objetivo: float,
        proteina_congelada: bool,
        tolerancia_pct: float = 0.03,
        lista_carbs: list = None,
        lista_grasas: list = None,
        lista_proteinas: list = None,
        macros_comida: dict = None,
        meal_idx: int = 0,
        alimentos_usados_plan: set = None
    ) -> dict:
        """FASE 5: Cierre energético estructurado con reintentos (4 estrategias)."""
        alimentos_usados_plan = alimentos_usados_plan or set()
        lista_carbs = lista_carbs or []
        lista_grasas = lista_grasas or []
        lista_proteinas = lista_proteinas or []
        macros_comida = macros_comida or {}

        def calcular_desviacion(alimentos_dict: dict, objetivo: float) -> float:
            kcal_total = 0.0
            for ali_nombre, gramos in alimentos_dict.items():
                if ali_nombre in ALIMENTOS_BASE:
                    kcal_total += gramos * (ALIMENTOS_BASE[ali_nombre]['kcal'] / 100)
            return abs(kcal_total - objetivo) / max(objetivo, 1) * 100

        def calcular_kcal_total(alimentos_dict: dict) -> float:
            kcal_total = 0.0
            for ali_nombre, gramos in alimentos_dict.items():
                if ali_nombre in ALIMENTOS_BASE:
                    kcal_total += gramos * (ALIMENTOS_BASE[ali_nombre]['kcal'] / 100)
            return kcal_total

        kcal_actual = calcular_kcal_total(resultado)
        desviacion_inicial = calcular_desviacion(resultado, kcal_objetivo)

        if desviacion_inicial <= 0.05:
            return resultado

        # ESTRATEGIA 1: AJUSTE LINEAL SIMPLE
        resultado_s1 = resultado.copy()
        diferencia = kcal_objetivo - kcal_actual

        if diferencia < 0:
            carbs_en_resultado = [a for a in resultado_s1 if a in CATEGORIAS.get('carbs', [])]
            if carbs_en_resultado:
                carb_ali = carbs_en_resultado[0]
                carb_data = ALIMENTOS_BASE.get(carb_ali, {})
                kcal_por_g = carb_data.get('kcal', 0) / 100
                if kcal_por_g > 0:
                    gramos_reducir = abs(diferencia) / kcal_por_g
                    nuevo_gramos = max(50, resultado_s1[carb_ali] - gramos_reducir)
                    if nuevo_gramos >= 50:
                        resultado_s1[carb_ali] = nuevo_gramos
                        desviacion_s1 = calcular_desviacion(resultado_s1, kcal_objetivo)
                        if desviacion_s1 <= 0.05:
                            return resultado_s1
        elif diferencia > 0:
            carbs_en_resultado = [a for a in resultado_s1 if a in CATEGORIAS.get('carbs', [])]
            if carbs_en_resultado:
                carb_ali = carbs_en_resultado[0]
                carb_data = ALIMENTOS_BASE.get(carb_ali, {})
                kcal_por_g = carb_data.get('kcal', 0) / 100
                if kcal_por_g > 0:
                    gramos_agregar = diferencia / kcal_por_g
                    nuevo_gramos = resultado_s1[carb_ali] + gramos_agregar
                    limite = LIMITES_DUROS_ALIMENTOS.get(carb_ali, 999)
                    if carb_ali in ALIMENTOS_LIMITE_ESTRICTO:
                        max_gramos = limite
                    else:
                        max_gramos = limite * 1.2
                    if nuevo_gramos <= max_gramos:
                        resultado_s1[carb_ali] = nuevo_gramos
                        desviacion_s1 = calcular_desviacion(resultado_s1, kcal_objetivo)
                        if desviacion_s1 <= 0.05:
                            return resultado_s1

        # ESTRATEGIA 2: AJUSTE DE GRASAS
        resultado_s2 = resultado_s1.copy()
        diferencia = kcal_objetivo - calcular_kcal_total(resultado_s2)

        grasas_en_resultado = [a for a in resultado_s2 if a in CATEGORIAS.get('grasa', [])]
        if grasas_en_resultado and diferencia != 0:
            grasa_ali = grasas_en_resultado[0]
            grasa_data = ALIMENTOS_BASE.get(grasa_ali, {})
            kcal_por_g = grasa_data.get('kcal', 0) / 100
            if kcal_por_g > 0:
                gramos_ajuste = diferencia / kcal_por_g
                nuevo_gramos = resultado_s2[grasa_ali] + gramos_ajuste
                limite = LIMITES_DUROS_ALIMENTOS.get(grasa_ali, 999)
                if 0 < nuevo_gramos <= limite * 1.2:
                    resultado_s2[grasa_ali] = nuevo_gramos
                    desviacion_s2 = calcular_desviacion(resultado_s2, kcal_objetivo)
                    if desviacion_s2 <= 0.05:
                        return resultado_s2

        # ESTRATEGIA 3: EXPANDIR/REDUCIR PROTEÍNA
        resultado_s3 = resultado_s2.copy()
        diferencia = kcal_objetivo - calcular_kcal_total(resultado_s3)

        proteinas_en_resultado = [a for a in resultado_s3 if a in PROTEINAS_ESTRUCTURALES or a in PROTEINAS_MIXTAS]
        if proteinas_en_resultado:
            proteina_ali = proteinas_en_resultado[0]
            proteina_data = ALIMENTOS_BASE.get(proteina_ali, {})
            kcal_por_g = proteina_data.get('kcal', 0) / 100
            gramos_actual = resultado_s3[proteina_ali]

            if kcal_por_g > 0:
                if diferencia > 0:
                    gramos_ideal = gramos_actual + (diferencia / kcal_por_g)
                    gramos_max = min(gramos_ideal, gramos_actual * 1.2)
                    gramos_nuevo = min(gramos_ideal, gramos_max)
                    if gramos_nuevo > gramos_actual:
                        resultado_s3[proteina_ali] = gramos_nuevo
                        desviacion_s3 = calcular_desviacion(resultado_s3, kcal_objetivo)
                        if desviacion_s3 <= 0.05:
                            return resultado_s3
                elif diferencia < 0:
                    gramos_ideal = gramos_actual + (diferencia / kcal_por_g)
                    gramos_min = max(gramos_actual * 0.8, 80)
                    gramos_nuevo = max(gramos_ideal, gramos_min)
                    if gramos_nuevo < gramos_actual:
                        resultado_s3[proteina_ali] = gramos_nuevo
                        desviacion_s3 = calcular_desviacion(resultado_s3, kcal_objetivo)
                        if desviacion_s3 <= 0.05:
                            return resultado_s3

        # ESTRATEGIA 4: AGREGAR SEGUNDO CARB O GRASA
        resultado_s4 = resultado_s3.copy()
        diferencia = kcal_objetivo - calcular_kcal_total(resultado_s4)

        if diferencia > 50:
            carbs_actuales = [a for a in resultado_s4 if a in CATEGORIAS.get('carbs', [])]
            carbs_candidatos = [a for a in lista_carbs if a not in resultado_s4 and a not in alimentos_usados_plan]

            if carbs_candidatos and len(carbs_actuales) < 2:
                segundo_carb = carbs_candidatos[0]
                carb_data = ALIMENTOS_BASE.get(segundo_carb, {})
                kcal_por_g = carb_data.get('kcal', 0) / 100
                if kcal_por_g > 0:
                    gramos_carb = min(diferencia / kcal_por_g, 100)
                    if gramos_carb >= 30:
                        resultado_s4[segundo_carb] = gramos_carb
                        desviacion_s4 = calcular_desviacion(resultado_s4, kcal_objetivo)
                        if desviacion_s4 <= 0.05:
                            return resultado_s4

            grasas_actuales = [a for a in resultado_s4 if a in CATEGORIAS.get('grasa', [])]
            grasas_candidatos = [a for a in lista_grasas if a not in resultado_s4 and a not in alimentos_usados_plan]

            if grasas_candidatos and len(grasas_actuales) < 2:
                segunda_grasa = grasas_candidatos[0]
                resultado_s4[segunda_grasa] = 15
                desviacion_s4 = calcular_desviacion(resultado_s4, kcal_objetivo)
                if desviacion_s4 <= 0.05:
                    return resultado_s4

        # FALLBACK
        desviacion_final = calcular_desviacion(resultado_s4, kcal_objetivo)
        if desviacion_final <= 0.05:
            return resultado_s4

        desviacion_original = calcular_desviacion(resultado, kcal_objetivo)
        if desviacion_original < desviacion_final:
            return resultado

        return resultado_s4


class CalculadorGramos:
    """#14: Calcula gramos de alimento por macro requerida (iterativo con residual tracking)."""

    @staticmethod
    def calcular_iterativo(
        macro_g: float,
        macro_tipo: str,
        lista_alimentos: list,
        meal_idx: int = 0,
        penalizados: set = None
    ) -> dict:
        """Asignación iterativa de macros a alimentos con tracking de residual."""
        penalizados = penalizados or set()
        resultado = {}
        macro_restante = macro_g
        tolerancia = 2.0
        alimento_idx = 0
        max_iteraciones = len(lista_alimentos)

        while alimento_idx < max_iteraciones:
            if not lista_alimentos or alimento_idx >= len(lista_alimentos):
                break

            if macro_restante <= tolerancia:
                break

            alimento_nombre = lista_alimentos[alimento_idx]

            if alimento_nombre in penalizados:
                alimento_idx += 1
                continue

            alimento = ALIMENTOS_BASE.get(alimento_nombre, {})
            densidad = alimento.get(macro_tipo, 1)

            if densidad <= 0:
                alimento_idx += 1
                continue

            gramos_posibles = macro_restante / (densidad / 100)
            limite = LIMITES_ALIMENTOS.get(alimento_nombre, 999)
            gramos_final = min(gramos_posibles, limite)

            minimo_alimento = MINIMOS_POR_ALIMENTO.get(alimento_nombre, 0)
            if gramos_final < minimo_alimento:
                alimento_idx += 1
                continue

            if alimento_nombre == 'salmon' and gramos_final < 100:
                alimento_idx += 1
                continue

            if macro_tipo == 'proteina':
                if gramos_final <= 40:
                    alimento_idx += 1
                    continue
            else:
                if gramos_final <= 20:
                    alimento_idx += 1
                    continue

            macro_aportado = gramos_final * (densidad / 100)
            macro_restante -= macro_aportado
            resultado[alimento_nombre] = gramos_final

            if macro_tipo == 'proteina':
                proteinas_count = len([a for a in resultado if a in CATEGORIAS.get('proteina', [])])
                if meal_idx == 1:
                    if proteinas_count >= 2:
                        break
                else:
                    break

            alimento_idx += 1

        return resultado

    @staticmethod
    def filtrar_menores_a_10g(resultado: dict, macro_tipo: str) -> dict:
        """Elimina alimentos por debajo de umbral mínimo y redistribuye kcal al anterior."""
        if not resultado:
            return resultado

        umbral_minimo = 40 if macro_tipo == 'proteina' else 20

        alimentos_filtrados = {}
        alimentos_ordenados = list(resultado.items())
        kcal_acumuladas = 0.0

        for _, (alimento, gramos) in enumerate(alimentos_ordenados):
            if gramos > umbral_minimo:
                if kcal_acumuladas > 0 and alimentos_filtrados:
                    ultimo_alimento = list(alimentos_filtrados.keys())[-1]
                    dens_kcal = ALIMENTOS_BASE[ultimo_alimento]['kcal'] / 100
                    if dens_kcal > 0:
                        gramos_a_anadir = kcal_acumuladas / dens_kcal
                        limite = LIMITES_ALIMENTOS.get(ultimo_alimento, 999)
                        nuevo_total = alimentos_filtrados[ultimo_alimento] + gramos_a_anadir
                        if nuevo_total <= limite:
                            alimentos_filtrados[ultimo_alimento] = nuevo_total
                            kcal_acumuladas = 0.0
                alimentos_filtrados[alimento] = gramos
            else:
                kcal_perdidas = gramos * ALIMENTOS_BASE[alimento]['kcal'] / 100
                kcal_acumuladas += kcal_perdidas

        if kcal_acumuladas > 0 and alimentos_filtrados:
            ultimo_alimento = list(alimentos_filtrados.keys())[-1]
            dens_kcal = ALIMENTOS_BASE[ultimo_alimento]['kcal'] / 100
            if dens_kcal > 0:
                gramos_a_anadir = kcal_acumuladas / dens_kcal
                limite = LIMITES_ALIMENTOS.get(ultimo_alimento, 999)
                nuevo_total = alimentos_filtrados[ultimo_alimento] + gramos_a_anadir
                if nuevo_total <= limite:
                    alimentos_filtrados[ultimo_alimento] = nuevo_total

        return alimentos_filtrados

    @staticmethod
    def calcular(macro_g: float, alimento_nombre: str, macro_tipo: str) -> float:
        """Fallback: Calcula gramos simple para un alimento."""
        alimento = ALIMENTOS_BASE.get(alimento_nombre, {})
        densidad = alimento.get(macro_tipo, 1)
        if densidad <= 0:
            return 0.0
        gramos = macro_g / (densidad / 100)
        return max(0, gramos)


# ============================================================================
# REAJUSTADOR AUTOMATICO DE PLANES
# ============================================================================

class ReajustadorPlan:
    """
    Sistema de reajuste automático para planes con desviación >5%.
    Permite hasta MAX_INTENTOS reajustes antes de declarar el plan inválido.
    """

    MAX_INTENTOS = 7

    @classmethod
    def reajustar_plan(cls, plan: dict) -> tuple[dict, bool, list[str]]:
        """Intenta reajustar el plan hasta MAX_INTENTOS veces."""
        logs = []
        comidas = ['desayuno', 'almuerzo', 'comida', 'cena']
        meal_idx_map = {'desayuno': 0, 'almuerzo': 1, 'comida': 2, 'cena': 3}

        for intento in range(1, cls.MAX_INTENTOS + 1):
            comidas_problema = []
            for nombre in comidas:
                if nombre not in plan:
                    continue
                desv = plan[nombre].get('desviacion_pct', 0)
                if desv > 5:
                    comidas_problema.append((nombre, desv))

            if not comidas_problema:
                logs.append(f"[REAJUSTE] Intento {intento}: Plan válido")
                return plan, True, logs

            comidas_problema.sort(key=lambda x: x[1], reverse=True)
            logs.append(f"[REAJUSTE] Intento {intento}: {len(comidas_problema)} comidas con desv >5%")

            for peor_comida, peor_desviacion in comidas_problema:
                meal_idx = meal_idx_map.get(peor_comida, 0)
                kcal_objetivo = plan[peor_comida].get('kcal_objetivo', 0)

                if kcal_objetivo <= 0:
                    continue

                plan[peor_comida] = cls._reajustar_comida_agresivo(
                    plan[peor_comida], meal_idx, intento
                )
                plan[peor_comida] = cls._enforce_limites_duros(plan[peor_comida])

                nueva_desv = plan[peor_comida].get('desviacion_pct', 0)
                logs.append(f"         {peor_comida}: {peor_desviacion:.1f}% -> {nueva_desv:.1f}%")

        es_valido = all(
            plan.get(c, {}).get('desviacion_pct', 0) <= 5
            for c in comidas if c in plan
        )

        if es_valido:
            logs.append(f"[REAJUSTE] Plan válido después de {cls.MAX_INTENTOS} intentos")
        else:
            desviaciones = {c: round(plan[c].get('desviacion_pct', 0), 1) for c in comidas if c in plan}
            logs.append(f"[REAJUSTE] FALLIDO: {desviaciones}")

        return plan, es_valido, logs

    @classmethod
    def _reajustar_comida_agresivo(cls, comida_dict: dict, meal_idx: int, intento: int) -> dict:
        """Reajuste agresivo usando múltiples estrategias."""
        if 'alimentos' not in comida_dict or 'kcal_objetivo' not in comida_dict:
            return comida_dict

        kcal_objetivo = comida_dict['kcal_objetivo']

        def calcular_kcal(alimentos):
            total = 0.0
            for nombre, gramos in alimentos.items():
                if nombre in ALIMENTOS_BASE:
                    total += gramos * ALIMENTOS_BASE[nombre]['kcal'] / 100
            return total

        kcal_actual = calcular_kcal(comida_dict['alimentos'])
        diff_kcal = kcal_objetivo - kcal_actual
        umbral_kcal = max(30, 100 - (intento * 15))

        if diff_kcal > umbral_kcal:
            cls._agregar_alimento_emergencia(comida_dict, diff_kcal, meal_idx, 'carbs')
            kcal_actual = calcular_kcal(comida_dict['alimentos'])
            diff_kcal = kcal_objetivo - kcal_actual
            if intento >= 4 and diff_kcal > 30:
                cls._agregar_alimento_emergencia(comida_dict, diff_kcal, meal_idx, 'grasa')
        elif diff_kcal < -umbral_kcal:
            cls._reducir_alimentos(comida_dict, abs(diff_kcal), meal_idx)

        comida_dict = ValidadorEnergia.validar_y_ajustar(
            comida_dict, kcal_objetivo, meal_idx=meal_idx
        )

        kcal_actual = calcular_kcal(comida_dict['alimentos'])
        desviacion = abs(kcal_actual - kcal_objetivo) / max(kcal_objetivo, 1) * 100

        if intento >= 4 and desviacion > 5:
            diff_kcal = kcal_objetivo - kcal_actual
            if diff_kcal > 20:
                # Opciones de carbs diferenciadas por comida (no repetir avena fuera de desayuno)
                if meal_idx == 0:
                    opciones_carbs_base = ['avena', 'pan_integral', 'granola', 'arroz_blanco', 'papa', 'cereal_integral']
                elif meal_idx == 3:
                    opciones_carbs_base = ['papa', 'camote', 'pan_integral', 'tortilla_maiz', 'quinoa']
                else:
                    opciones_carbs_base = ['arroz_blanco', 'arroz_integral', 'papa', 'camote', 'tortilla_maiz', 'frijoles', 'lentejas']

                if intento >= 5:
                    opciones_extra = opciones_carbs_base + ['aguacate', 'nueces', 'almendras']
                else:
                    opciones_extra = opciones_carbs_base[:4] + ['aguacate', 'nueces']

                for ali in opciones_extra:
                    if ali not in ALIMENTOS_BASE:
                        continue
                    dens = ALIMENTOS_BASE[ali]['kcal'] / 100
                    limite_duro = LIMITES_DUROS_ALIMENTOS.get(ali, 200)
                    gramos_actual = comida_dict['alimentos'].get(ali, 0)
                    espacio_disponible = limite_duro - gramos_actual
                    if espacio_disponible < 30:
                        continue
                    gramos_agregar = min(diff_kcal / dens, espacio_disponible * 0.95)
                    nuevos_gramos = gramos_actual + gramos_agregar
                    minimo = MINIMOS_POR_ALIMENTO.get(ali, 30)
                    if nuevos_gramos >= minimo and nuevos_gramos <= limite_duro:
                        comida_dict['alimentos'][ali] = nuevos_gramos
                        kcal_actual = calcular_kcal(comida_dict['alimentos'])
                        diff_kcal = kcal_objetivo - kcal_actual
                        if diff_kcal < 20:
                            break
            elif diff_kcal < -20:
                cls._reducir_alimentos(comida_dict, abs(diff_kcal) * 1.2, meal_idx)

            comida_dict['kcal_real'] = calcular_kcal(comida_dict['alimentos'])
            comida_dict['desviacion_pct'] = abs(comida_dict['kcal_real'] - kcal_objetivo) / max(kcal_objetivo, 1) * 100

        return comida_dict

    @classmethod
    def _agregar_alimento_emergencia(cls, comida_dict: dict, kcal_faltantes: float, meal_idx: int, tipo: str):
        """Agrega un alimento de emergencia para cubrir kcal faltantes."""
        if tipo == 'carbs':
            if meal_idx == 0:  # Desayuno: avena es válida
                opciones = ['avena', 'pan_integral', 'granola', 'arroz_blanco', 'papa', 'camote', 'cereal_integral']
            elif meal_idx == 3:  # Cena: sin avena, preferir ligeros
                opciones = ['papa', 'camote', 'pan_integral', 'tortilla_maiz', 'quinoa', 'lentejas']
            else:  # Almuerzo (1) y Comida (2)
                opciones = ['arroz_blanco', 'arroz_integral', 'papa', 'camote',
                            'tortilla_maiz', 'frijoles', 'lentejas', 'pan_integral', 'garbanzos']
        elif tipo == 'grasa':
            opciones = ['aguacate', 'nueces', 'almendras', 'aceite_de_oliva']
        else:
            opciones = ['arroz_blanco']

        for nombre in opciones:
            if nombre not in ALIMENTOS_BASE:
                continue
            dens = ALIMENTOS_BASE[nombre]['kcal'] / 100
            if dens <= 0:
                continue
            gramos_actual = comida_dict['alimentos'].get(nombre, 0)
            gramos_necesarios = kcal_faltantes / dens
            limite_duro = LIMITES_DUROS_ALIMENTOS.get(nombre, 999)
            limite_max = limite_duro
            espacio = limite_max - gramos_actual
            if espacio > 30:
                gramos_agregar = min(gramos_necesarios, espacio)
                nuevos_gramos = gramos_actual + gramos_agregar
                minimo = MINIMOS_POR_ALIMENTO.get(nombre, 40)
                if nuevos_gramos >= minimo:
                    comida_dict['alimentos'][nombre] = nuevos_gramos
                    return

    @classmethod
    def _reducir_alimentos(cls, comida_dict: dict, kcal_sobrantes: float, meal_idx: int):
        """Reduce alimentos para eliminar kcal sobrantes."""
        carbs_set = set(CATEGORIAS.get('carbs', [])) - {'platano_macho', 'granola', 'cereal_integral'}
        grasas_set = set(['aguacate', 'nueces', 'almendras', 'aceite_de_oliva', 'mantequilla_mani'])

        restante = kcal_sobrantes

        for nombre in list(comida_dict['alimentos'].keys()):
            if restante <= 10:
                break
            if nombre not in carbs_set:
                continue
            if nombre not in ALIMENTOS_BASE:
                continue
            gramos_actual = comida_dict['alimentos'][nombre]
            dens = ALIMENTOS_BASE[nombre]['kcal'] / 100
            if dens <= 0:
                continue
            gramos_a_quitar = restante / dens
            minimo = MINIMOS_POR_ALIMENTO.get(nombre, 40)
            nuevo_g = max(minimo, gramos_actual - gramos_a_quitar)
            reduccion_real = gramos_actual - nuevo_g
            if reduccion_real > 0:
                comida_dict['alimentos'][nombre] = nuevo_g
                restante -= reduccion_real * dens

        if restante > 10:
            for nombre in list(comida_dict['alimentos'].keys()):
                if restante <= 10:
                    break
                if nombre not in grasas_set:
                    continue
                if nombre not in ALIMENTOS_BASE:
                    continue
                gramos_actual = comida_dict['alimentos'][nombre]
                dens = ALIMENTOS_BASE[nombre]['kcal'] / 100
                if dens <= 0:
                    continue
                gramos_a_quitar = restante / dens
                minimo = MINIMOS_POR_ALIMENTO.get(nombre, 20)
                nuevo_g = max(minimo, gramos_actual - gramos_a_quitar)
                reduccion_real = gramos_actual - nuevo_g
                if reduccion_real > 0:
                    comida_dict['alimentos'][nombre] = nuevo_g
                    restante -= reduccion_real * dens

    @classmethod
    def _enforce_limites_duros(cls, comida_dict: dict) -> dict:
        """Garantiza que ningún alimento exceda su límite duro * 1.2x."""
        if 'alimentos' not in comida_dict:
            return comida_dict

        FACTOR_MAXIMO = 1.2

        for nombre, gramos in list(comida_dict['alimentos'].items()):
            if nombre not in ALIMENTOS_BASE:
                continue
            limite_duro = LIMITES_DUROS_ALIMENTOS.get(nombre, 999)
            limite_maximo = limite_duro * FACTOR_MAXIMO
            if gramos > limite_maximo:
                comida_dict['alimentos'][nombre] = limite_maximo

        kcal_objetivo = comida_dict.get('kcal_objetivo', 1)
        kcal_real = sum(
            g * ALIMENTOS_BASE[n]['kcal'] / 100
            for n, g in comida_dict['alimentos'].items()
            if n in ALIMENTOS_BASE
        )
        comida_dict['kcal_real'] = kcal_real
        comida_dict['desviacion_pct'] = abs(kcal_real - kcal_objetivo) / max(kcal_objetivo, 1) * 100

        return comida_dict


class ValidadorEnergia:
    """#15: Valida y ajusta por energía (cierre kcal). ENFORCEMENT: deviation must be <= 5%"""

    @staticmethod
    def _obtener_limite_maximo(alimento: str) -> float:
        limite_duro = LIMITES_DUROS_ALIMENTOS.get(alimento, 999)
        return limite_duro * 1.2

    @staticmethod
    def _redistribuir_kcals_respetando_limites(comida_dict: dict, kcal_a_redistribuir: float) -> None:
        if kcal_a_redistribuir <= 0 or not comida_dict['alimentos']:
            return

        for nombre in sorted(comida_dict['alimentos'].keys(), key=lambda n: comida_dict['alimentos'][n], reverse=True):
            if nombre not in ALIMENTOS_BASE:
                continue
            gramos_actual = comida_dict['alimentos'][nombre]
            limite_duro = LIMITES_DUROS_ALIMENTOS.get(nombre, 999)
            if nombre in ALIMENTOS_LIMITE_ESTRICTO:
                limite_maximo = limite_duro
            else:
                limite_maximo = limite_duro * 1.2
            espacio_disponible = max(0, limite_maximo - gramos_actual)

            if espacio_disponible > 0:
                dens = ALIMENTOS_BASE[nombre]['kcal'] / 100
                if dens > 0:
                    gramos_que_caben = espacio_disponible
                    kcal_que_caben = gramos_que_caben * dens
                    if kcal_que_caben >= kcal_a_redistribuir:
                        delta_g = kcal_a_redistribuir / dens
                        comida_dict['alimentos'][nombre] = min(
                            comida_dict['alimentos'][nombre] + delta_g,
                            limite_maximo
                        )
                        return
                    else:
                        comida_dict['alimentos'][nombre] = limite_maximo
                        kcal_a_redistribuir -= kcal_que_caben

    @staticmethod
    def _obtener_factor_limite_dinamico(iteracion: int, max_iteraciones: int) -> float:
        if iteracion < 50:
            return 1.05
        elif iteracion < 100:
            return 1.10
        else:
            return 1.20

    @staticmethod
    def _redistribuir_kcals_respetando_limites_v2(comida_dict: dict, kcal_a_redistribuir: float, alimentos_base: dict = None) -> bool:
        if kcal_a_redistribuir <= 0 or not comida_dict['alimentos']:
            return True

        if alimentos_base is None:
            alimentos_base = ALIMENTOS_BASE

        fases = [
            ['arroz_blanco', 'arroz_integral', 'papa', 'camote', 'pan_integral', 'avena', 'tortilla_maiz', 'frijoles', 'banana'],
            ['avena', 'pan_integral', 'tortilla_maiz', 'frijoles'],
            ['brocoli', 'espinaca', 'calabacita', 'champiñones', 'coliflor'],
            ['aguacate', 'nueces', 'almendras', 'aceite_de_oliva', 'mantequilla_mani'],
            ['pechuga_de_pollo', 'carne_magra_res', 'pescado_blanco', 'salmon', 'claras_huevo'],
        ]

        for fase_nombres in fases:
            for nombre in fase_nombres:
                if nombre in comida_dict['alimentos']:
                    gramos_actual = comida_dict['alimentos'][nombre]
                    limite_duro = LIMITES_DUROS_ALIMENTOS.get(nombre, 999)
                    if nombre in ALIMENTOS_LIMITE_ESTRICTO:
                        limite_maximo = limite_duro
                    else:
                        limite_maximo = limite_duro * 1.2
                    espacio = max(0, limite_maximo - gramos_actual)

                    if espacio > 0 and nombre in alimentos_base:
                        dens = alimentos_base[nombre]['kcal'] / 100
                        if dens > 0:
                            kcal_posibles = espacio * dens
                            if kcal_posibles >= kcal_a_redistribuir:
                                delta_g = kcal_a_redistribuir / dens
                                comida_dict['alimentos'][nombre] = min(
                                    comida_dict['alimentos'][nombre] + delta_g,
                                    limite_maximo
                                )
                                return True
                            else:
                                comida_dict['alimentos'][nombre] = limite_maximo
                                kcal_a_redistribuir -= kcal_posibles

        return False

    @staticmethod
    def validar_y_ajustar(comida_dict: dict, kcal_objetivo: float, meal_idx: int = -1) -> dict:
        """Valida energía y ajusta si es necesario para mantener desviación <= 5%."""
        def calcular_kcal(comida):
            total = 0.0
            for nombre, gramos in comida['alimentos'].items():
                if nombre not in ALIMENTOS_BASE:
                    continue
                total += gramos * ALIMENTOS_BASE[nombre]['kcal'] / 100
            return total

        kcal_real = calcular_kcal(comida_dict)
        desviacion_pct = abs(kcal_real - kcal_objetivo) / max(kcal_objetivo, 1) * 100

        comida_dict['kcal_real'] = kcal_real
        comida_dict['desviacion_pct'] = desviacion_pct

        if desviacion_pct > 5:
            max_iteraciones = 150 if meal_idx >= 1 else 100
            for iteracion in range(max_iteraciones):
                kcal_real = calcular_kcal(comida_dict)
                desviacion_pct = abs(kcal_real - kcal_objetivo) / max(kcal_objetivo, 1) * 100
                comida_dict['kcal_real'] = kcal_real
                comida_dict['desviacion_pct'] = desviacion_pct

                if desviacion_pct <= 5:
                    break

                diff_kcal = kcal_objetivo - kcal_real
                ajustado = False

                # FASE 1: Carbos
                for carb in ['arroz_blanco', 'arroz_integral', 'papa', 'camote', 'pan_integral', 'avena', 'tortilla_maiz', 'frijoles', 'banana', 'platano']:
                    if carb not in comida_dict['alimentos'] or carb not in ALIMENTOS_BASE:
                        continue
                    dens = ALIMENTOS_BASE[carb]['kcal'] / 100
                    if dens <= 0:
                        continue
                    delta_g = diff_kcal / dens
                    nuevo_g = comida_dict['alimentos'][carb] + delta_g
                    factor_dinamico = ValidadorEnergia._obtener_factor_limite_dinamico(iteracion, max_iteraciones)
                    limite = LIMITES_ALIMENTOS.get(carb, 999) * factor_dinamico
                    if 0 <= nuevo_g <= limite:
                        comida_dict['alimentos'][carb] = nuevo_g
                        ajustado = True
                        break

                # FASE 1.5: Verduras
                if not ajustado:
                    for verdura in ['brocoli', 'espinaca', 'calabacita', 'champiñones', 'coliflor']:
                        if verdura not in comida_dict['alimentos'] or verdura not in ALIMENTOS_BASE:
                            continue
                        dens = ALIMENTOS_BASE[verdura]['kcal'] / 100
                        if dens <= 0:
                            continue
                        delta_g = diff_kcal / dens
                        nuevo_g = comida_dict['alimentos'][verdura] + delta_g
                        if meal_idx >= 1:
                            limite = LIMITES_ALIMENTOS.get(verdura, 999) * 3.5
                        else:
                            limite = LIMITES_ALIMENTOS.get(verdura, 999) * 2.0
                        if 0 <= nuevo_g <= limite:
                            comida_dict['alimentos'][verdura] = nuevo_g
                            ajustado = True
                            break

                # FASE 2: Grasas
                if not ajustado:
                    grasas_permitidas = ['aceite_de_oliva', 'aguacate', 'nueces', 'almendras', 'mantequilla_mani']
                    if meal_idx == 1:
                        grasas_permitidas.append('mantequilla_mani')

                    for grasa in grasas_permitidas:
                        if grasa not in comida_dict['alimentos'] or grasa not in ALIMENTOS_BASE:
                            continue
                        dens = ALIMENTOS_BASE[grasa]['kcal'] / 100
                        if dens <= 0:
                            continue
                        delta_g = diff_kcal / dens
                        nuevo_g = comida_dict['alimentos'][grasa] + delta_g
                        factor_dinamico = ValidadorEnergia._obtener_factor_limite_dinamico(iteracion, max_iteraciones)
                        limite = LIMITES_ALIMENTOS.get(grasa, 999) * factor_dinamico
                        if 0 <= nuevo_g <= limite:
                            comida_dict['alimentos'][grasa] = nuevo_g
                            ajustado = True
                            break

                # FASE 3: Proteínas
                if not ajustado:
                    prot_ajustables = ['pechuga_de_pollo', 'carne_magra_res', 'pescado_blanco', 'salmon', 'claras_huevo', 'huevo']
                    if iteracion >= 15 and meal_idx >= 1:
                        prot_ajustables.append('proteina_suero')

                    for prot in prot_ajustables:
                        if prot not in comida_dict['alimentos'] or prot not in ALIMENTOS_BASE:
                            continue
                        dens = ALIMENTOS_BASE[prot]['kcal'] / 100
                        if dens <= 0:
                            continue
                        delta_g = diff_kcal / dens
                        nuevo_g = comida_dict['alimentos'][prot] + delta_g
                        factor_dinamico = ValidadorEnergia._obtener_factor_limite_dinamico(iteracion, max_iteraciones)
                        limite = LIMITES_ALIMENTOS.get(prot, 999) * factor_dinamico
                        if 0 <= nuevo_g <= limite:
                            comida_dict['alimentos'][prot] = nuevo_g
                            ajustado = True
                            break

                # FASE 4: Forzar ajuste
                if not ajustado:
                    disponibles = {n: ALIMENTOS_BASE[n]['kcal'] / 100 for n, g in comida_dict['alimentos'].items() if n in ALIMENTOS_BASE and g > 0}
                    if disponibles:
                        elem = max(disponibles.items(), key=lambda x: x[1])[0] if diff_kcal > 0 else min(disponibles.items(), key=lambda x: x[1])[0]
                        dens = disponibles[elem]
                        delta_g = diff_kcal / dens * 0.75
                        nuevo_g = comida_dict['alimentos'][elem] + delta_g
                        comida_dict['alimentos'][elem] = max(0, min(nuevo_g, LIMITES_ALIMENTOS.get(elem, 999) * 1.2))

        comida_dict['kcal_real'] = calcular_kcal(comida_dict)
        comida_dict['desviacion_pct'] = abs(comida_dict['kcal_real'] - kcal_objetivo) / max(kcal_objetivo, 1) * 100

        # Filtrado de mínimos realistas
        alimentos_bajo_minimo = []
        for nombre, gramos in comida_dict['alimentos'].items():
            if nombre not in ALIMENTOS_BASE:
                continue
            minimo = MINIMOS_POR_ALIMENTO.get(nombre, 0)
            if 0 < gramos < minimo:
                alimentos_bajo_minimo.append((nombre, gramos))

        if alimentos_bajo_minimo:
            kcal_a_redistribuir = sum(
                g * ALIMENTOS_BASE[n]['kcal'] / 100
                for n, g in alimentos_bajo_minimo
                if n in ALIMENTOS_BASE
            )
            for nombre, _ in alimentos_bajo_minimo:
                del comida_dict['alimentos'][nombre]
            if kcal_a_redistribuir > 0:
                ValidadorEnergia._redistribuir_kcals_respetando_limites(comida_dict, kcal_a_redistribuir)
            comida_dict['kcal_real'] = calcular_kcal(comida_dict)
            comida_dict['desviacion_pct'] = abs(comida_dict['kcal_real'] - kcal_objetivo) / max(kcal_objetivo, 1) * 100

        # CAP FINAL: Asegurar que TODOS los alimentos respeten sus límites máximos
        for nombre in list(comida_dict['alimentos'].keys()):
            if nombre not in ALIMENTOS_BASE:
                continue
            limite_maximo = ValidadorEnergia._obtener_limite_maximo(nombre)
            gramos_actual = comida_dict['alimentos'][nombre]
            if gramos_actual > limite_maximo:
                kcal_excedentes = (gramos_actual - limite_maximo) * ALIMENTOS_BASE[nombre]['kcal'] / 100
                comida_dict['alimentos'][nombre] = limite_maximo
                if kcal_excedentes > 0:
                    ValidadorEnergia._redistribuir_kcals_respetando_limites(comida_dict, kcal_excedentes)

        comida_dict['kcal_real'] = calcular_kcal(comida_dict)
        comida_dict['desviacion_pct'] = abs(comida_dict['kcal_real'] - kcal_objetivo) / max(kcal_objetivo, 1) * 100

        return comida_dict

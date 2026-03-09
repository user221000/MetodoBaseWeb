"""Selección y rotación determinista de alimentos."""
import random
import hashlib

from config.constantes import LEGUMINOSAS
from config.catalogo_alimentos import CATALOGO_POR_TIPO, PROTEINAS, CARBS, GRASAS, FRUTAS
from src.alimentos_base import CATEGORIAS


def generar_seed(cliente, semana: int = 1, gym_id: str = "default") -> int:
    """
    Genera un seed COMPLETAMENTE DETERMINISTA basado en:
    gym_id, cliente.id_cliente, peso_kg, grasa_corporal_pct, objetivo, semana.
    """
    id_cliente = str(cliente.id_cliente).strip().upper()
    peso = float(cliente.peso_kg)
    grasa = float(cliente.grasa_corporal_pct)
    objetivo = str(cliente.objetivo).lower().strip()
    gym = str(gym_id).strip().lower()
    semana_int = int(semana)
    
    seed_string = f"{gym}:{id_cliente}:{peso}:{grasa}:{objetivo}:semana{semana_int}"
    seed_hash = hashlib.sha256(seed_string.encode('utf-8')).hexdigest()
    seed_int = int(seed_hash[:16], 16)
    
    return seed_int


def generar_seed_bloques(cliente, gym_id: str = "default") -> tuple[int, int]:
    """
    Genera seeds para un bloque de 4 semanas (3 semanas base + 1 semana de ajuste).
    Semanas 1-3: seed_base | Semana 4: seed_variacion
    """
    id_cliente = str(cliente.id_cliente).strip().upper()
    peso = float(cliente.peso_kg)
    grasa = float(cliente.grasa_corporal_pct)
    objetivo = str(cliente.objetivo).lower().strip()
    gym = str(gym_id).strip().lower()
    
    seed_base_string = f"{gym}:{id_cliente}:{peso}:{grasa}:{objetivo}:bloque_base"
    seed_base_hash = hashlib.sha256(seed_base_string.encode('utf-8')).hexdigest()
    seed_base = int(seed_base_hash[:16], 16)
    
    seed_var_string = f"{gym}:{id_cliente}:{peso}:{grasa}:{objetivo}:bloque_variacion"
    seed_var_hash = hashlib.sha256(seed_var_string.encode('utf-8')).hexdigest()
    seed_variacion = int(seed_var_hash[:16], 16)
    
    return seed_base, seed_variacion


def obtener_lista_rotada(lista: list, seed: int, meal_idx: int, plan_numero: int = 1) -> list:
    """Mezcla y rota una lista de forma determinista SIN eliminar alimentos."""
    if not lista:
        return []
    
    combined_seed = seed + (plan_numero * 7919)
    rng = random.Random(combined_seed)
    
    lista_mezclada = lista.copy()
    rng.shuffle(lista_mezclada)
    
    rotated = lista_mezclada[meal_idx:] + lista_mezclada[:meal_idx]
    
    if plan_numero > 1 and len(rotated) > 1:
        offset = (plan_numero - 1) % len(rotated)
        rotated = rotated[offset:] + rotated[:offset]
    
    return rotated


def aplicar_penalizacion_semana(lista: list, seed: int, semana: int,
                                factor_penalizacion: float = 0.8) -> list:
    """Penaliza alimentos en semanas posteriores para variar el plan."""
    if semana <= 1 or len(lista) <= 2:
        return lista
    
    porcentaje_penalizacion = 0.10 * (semana - 1)
    cantidad_penalizar = max(1, int(len(lista) * porcentaje_penalizacion))
    
    rng = random.Random(seed + semana)
    alimentos_penalizar = rng.sample(lista, min(cantidad_penalizar, len(lista)))
    
    lista_penalizada = [a for a in lista if a not in alimentos_penalizar] + alimentos_penalizar
    
    return lista_penalizada


class SelectorAlimentos:
    """Selecciona proteína/carb/grasa con rotación por comida."""
    
    @staticmethod
    def seleccionar_lista(
        tipo: str,
        meal_idx: int = 0,
        alimentos_usados=None,
        seed: int = None,
        plan_numero: int = 1,
        alimentos_penalizados: dict | None = None,
        pesos_ponderados: dict[str, float] | None = None,
    ) -> list:
        """Retorna lista de alimentos para iteración (rotado de forma DETERMINISTA).

        Args:
            alimentos_penalizados: dict ``{cat: [alimentos]}`` devuelto por
                ``GestorRotacion.obtener_penalizados()`` — mueve penalizados al final.
            pesos_ponderados: dict ``{alimento: peso}`` devuelto por
                ``RotacionInteligenteAlimentos.obtener_penalizaciones_ponderadas()``
                — ordena la lista de mayor disponibilidad a menor.  Si se
                suministran ambos parámetros, ``pesos_ponderados`` tiene
                precedencia para el ordenamiento final.
        """
        if alimentos_usados is None:
            alimentos_usados = set()
        if alimentos_penalizados is None:
            alimentos_penalizados = {}

        # --- Listas base desde el catálogo centralizado ---
        proteinas = list(PROTEINAS)
        carbs = list(CARBS)
        frutas = list(FRUTAS)
        grasas = list(GRASAS)
        
        # Ajustes por comida
        if meal_idx == 0:  # desayuno
            preferidas = ['huevo', 'claras_huevo', 'proteina_suero',
                          'yogurt_griego_light', 'yogurt_natural', 'jamon_pavo']
            otras = [p for p in proteinas if p not in preferidas]
            proteinas = [p for p in preferidas if p in proteinas] + otras
            if not proteinas:
                proteinas = ['huevo', 'claras_huevo', 'proteina_suero']
            carbs = [c for c in ['avena', 'pan_integral', 'granola',
                                 'cereal_integral', 'tortilla_maiz'] if c in CARBS]
            grasas = [g for g in ['almendras', 'nueces', 'semillas_chia',
                                  'mantequilla_mani'] if g in GRASAS]
        elif meal_idx == 1:  # almuerzo
            excluir_prot = {'yogurt_griego_light', 'yogurt_natural',
                            'proteina_suero', 'leche_descremada'}
            proteinas = [p for p in proteinas if p not in excluir_prot]
            ligeras = ['pechuga_de_pollo', 'atun', 'pescado_blanco',
                       'queso_panela', 'jamon_pavo', 'pavo', 'camarones']
            otras = [p for p in proteinas if p not in ligeras]
            proteinas = [p for p in ligeras if p in proteinas] + otras
            carbs = [c for c in ['tortilla_maiz', 'arroz_blanco', 'frijoles',
                                 'papa', 'lentejas', 'elote'] if c in CARBS]
            grasas = [g for g in ['aguacate', 'nueces', 'cacahuates',
                                  'semillas_girasol'] if g in GRASAS]
        elif meal_idx == 2:  # comida
            excluir_comida = {'huevo', 'claras_huevo', 'yogurt_griego_light',
                              'yogurt_natural', 'queso_panela', 'queso_cottage',
                              'proteina_suero', 'leche_descremada', 'jamon_pavo', 'tofu'}
            proteinas = [p for p in proteinas if p not in excluir_comida]
            alta_densidad = ['pechuga_de_pollo', 'carne_magra_res', 'salmon',
                             'pescado_blanco', 'cerdo_lomo', 'atun', 'pavo',
                             'camarones', 'sardina', 'carne_molida']
            otras = [p for p in proteinas if p not in alta_densidad]
            proteinas = [p for p in alta_densidad if p in proteinas] + otras
            frutas = []
        elif meal_idx == 3:  # cena
            excluir_cena = {'huevo', 'salmon', 'carne_magra_res', 'cerdo_lomo',
                            'sardina', 'carne_molida', 'proteina_suero',
                            'yogurt_natural', 'leche_descremada'}
            proteinas = [p for p in proteinas if p not in excluir_cena]
            ligeras_cena = ['pechuga_de_pollo', 'pescado_blanco', 'claras_huevo',
                            'pavo', 'camarones', 'queso_cottage', 'atun', 'tofu']
            otras = [p for p in proteinas if p not in ligeras_cena]
            proteinas = [p for p in ligeras_cena if p in proteinas] + otras
            dense = {'arroz_blanco', 'arroz_integral', 'pasta_integral',
                     'frijoles', 'garbanzos', 'platano_macho'}
            carbs = [c for c in carbs if c not in dense] + [c for c in carbs if c in dense]
            carbs = [c for c in carbs if c != 'tortilla_harina']
            grasas = [g for g in grasas if g != 'aguacate']
        
        # Aplicar rotación determinista
        if seed is not None and seed != 0:
            proteinas = obtener_lista_rotada(proteinas, seed, meal_idx, plan_numero)
            carbs = obtener_lista_rotada(carbs, seed, meal_idx, plan_numero)
            frutas = obtener_lista_rotada(frutas, seed, meal_idx, plan_numero)
            grasas = obtener_lista_rotada(grasas, seed, meal_idx, plan_numero)
        else:
            if proteinas:
                proteinas = proteinas[meal_idx:] + proteinas[:meal_idx]
            if carbs:
                carbs = carbs[meal_idx:] + carbs[:meal_idx]
            if frutas:
                frutas = frutas[meal_idx:] + frutas[:meal_idx]
            if grasas:
                grasas = grasas[meal_idx:] + grasas[:meal_idx]
        
        # --- Filtrar penalizados del gestor de rotación (inter-plan) ---
        # alimentos_penalizados puede ser:
        #   a) dict {cat: [list]} legacy  →  simple push-to-back
        #   b) dict {cat: [list]} de RotacionInteligente (mismo formato)
        proteinas = _filtrar_penalizados(proteinas, alimentos_penalizados.get('proteina', []))
        carbs = _filtrar_penalizados(carbs, alimentos_penalizados.get('carbs', []))
        grasas = _filtrar_penalizados(grasas, alimentos_penalizados.get('grasa', []))

        # --- Penalización intra-plan (alimentos ya usados en este mismo plan) ---
        proteinas = _priorizar_no_usados(proteinas, alimentos_usados)
        carbs = _priorizar_no_usados(carbs, alimentos_usados)
        frutas = _priorizar_no_usados(frutas, alimentos_usados)
        grasas = _priorizar_no_usados(grasas, alimentos_usados)

        # --- Aplicar pesos ponderados de RotacionInteligente (si se proveen) ---
        if pesos_ponderados:
            proteinas = _ordenar_por_peso_ponderado(proteinas, pesos_ponderados)
            carbs = _ordenar_por_peso_ponderado(carbs, pesos_ponderados)
            frutas = _ordenar_por_peso_ponderado(frutas, pesos_ponderados)
            grasas = _ordenar_por_peso_ponderado(grasas, pesos_ponderados)
        
        seleccion_map = {
            'proteina': proteinas,
            'carbs': carbs,
            'grasa': grasas,
            'fruta': frutas,
        }
        
        lista = seleccion_map.get(tipo, proteinas)
        return lista if lista else ['pechuga_de_pollo'] if tipo == 'proteina' else []
    
    @staticmethod
    def seleccionar(tipo: str) -> str:
        """Selecciona primer alimento del tipo (deprecated, use seleccionar_lista)."""
        lista = CATALOGO_POR_TIPO.get(tipo, PROTEINAS)
        return lista[0] if lista else 'pechuga_de_pollo'


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _filtrar_penalizados(lista: list[str], penalizados: list[str]) -> list[str]:
    """Mueve penalizados al final. Si la lista queda vacía, usa backup completo."""
    if not penalizados:
        return lista
    penalizados_set = set(penalizados)
    no_penalizados = [a for a in lista if a not in penalizados_set]
    if not no_penalizados:
        return lista  # backup: devolver todo si filtrar deja vacío
    cola = [a for a in lista if a in penalizados_set]
    return no_penalizados + cola


def _priorizar_no_usados(lista: list[str], usados: set) -> list[str]:
    """Pone los alimentos aún no usados al frente de la lista."""
    nuevos = [a for a in lista if a not in usados]
    ya_usados = [a for a in lista if a in usados]
    return nuevos + ya_usados if nuevos else lista


def _ordenar_por_peso_ponderado(
    lista: list[str], pesos: dict[str, float]
) -> list[str]:
    """Ordena la lista poniendo primero los alimentos con menor peso de
    penalización (más disponibles).

    Alimentos sin entrada en ``pesos`` reciben peso 0.0 (máxima prioridad).
    El orden relativo entre alimentos con el mismo peso se preserva (sort estable).
    """
    return sorted(lista, key=lambda a: pesos.get(a, 0.0))

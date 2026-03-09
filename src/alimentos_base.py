"""
Base de alimentos - Versión expandida v1.1 (PRODUCCIÓN)
Esta es la fuente única de verdad para todos los alimentos y configuración.
85 alimentos: 20 proteínas, 18 carbohidratos, 9 grasas, 20 verduras, 18 frutas.
"""

# ============================================================================
# BASE DE ALIMENTOS (proteína/carb/grasa por 100g)
# ============================================================================

ALIMENTOS_BASE = {
    # ============================================================================
    # PROTEÍNAS (20 opciones)
    # ============================================================================
    'pechuga_de_pollo':    {'proteina': 31,   'carbs': 0,   'grasa': 3.6,  'kcal': 165},
    'carne_magra_res':     {'proteina': 26,   'carbs': 0,   'grasa': 10,   'kcal': 217},
    'pescado_blanco':      {'proteina': 22,   'carbs': 0,   'grasa': 2,    'kcal': 105},
    'salmon':              {'proteina': 20,   'carbs': 0,   'grasa': 13,   'kcal': 208},
    'huevo':               {'proteina': 13,   'carbs': 1,   'grasa': 11,   'kcal': 155},
    'claras_huevo':        {'proteina': 11,   'carbs': 0.7, 'grasa': 0.2,  'kcal': 52},
    'queso_panela':        {'proteina': 18,   'carbs': 2,   'grasa': 18,   'kcal': 264},
    'yogurt_griego_light': {'proteina': 10,   'carbs': 4,   'grasa': 0.4,  'kcal': 59},
    'proteina_suero':      {'proteina': 25,   'carbs': 8,   'grasa': 6,    'kcal': 400},
    'atun':                {'proteina': 26,   'carbs': 0,   'grasa': 1,    'kcal': 116},
    'carne_molida':        {'proteina': 17,   'carbs': 0,   'grasa': 10,   'kcal': 164},
    'pavo':                {'proteina': 29,   'carbs': 0,   'grasa': 1,    'kcal': 135},
    'cerdo_lomo':          {'proteina': 27,   'carbs': 0,   'grasa': 4,    'kcal': 143},
    'camarones':           {'proteina': 24,   'carbs': 0,   'grasa': 0.3,  'kcal': 99},
    'sardina':             {'proteina': 25,   'carbs': 0,   'grasa': 11,   'kcal': 208},
    'queso_cottage':       {'proteina': 11,   'carbs': 3.4, 'grasa': 4.3,  'kcal': 98},
    'yogurt_natural':      {'proteina': 5,    'carbs': 7,   'grasa': 3.3,  'kcal': 79},
    'jamon_pavo':          {'proteina': 15,   'carbs': 2,   'grasa': 2,    'kcal': 86},
    'leche_descremada':    {'proteina': 3.4,  'carbs': 5,   'grasa': 0.1,  'kcal': 35},
    'tofu':                {'proteina': 8,    'carbs': 2,   'grasa': 4.8,  'kcal': 76},

    # ============================================================================
    # CARBOHIDRATOS (18 opciones)
    # ============================================================================
    'arroz_blanco':    {'proteina': 2.7,  'carbs': 28,  'grasa': 0.3,  'kcal': 130},
    'arroz_integral':  {'proteina': 2.6,  'carbs': 23,  'grasa': 1,    'kcal': 111},
    'papa':            {'proteina': 2,    'carbs': 17,  'grasa': 0.1,  'kcal': 77},
    'camote':          {'proteina': 1.6,  'carbs': 20,  'grasa': 0.1,  'kcal': 86},
    'avena':           {'proteina': 11,   'carbs': 66,  'grasa': 7,    'kcal': 389},
    'pan_integral':    {'proteina': 9,    'carbs': 41,  'grasa': 3.5,  'kcal': 247},
    'tortilla_maiz':   {'proteina': 5.7,  'carbs': 44,  'grasa': 2.8,  'kcal': 218},
    'frijoles':        {'proteina': 9,    'carbs': 24,  'grasa': 0.5,  'kcal': 127},
    'lentejas':        {'proteina': 9,    'carbs': 20,  'grasa': 0.4,  'kcal': 116},
    'garbanzos':       {'proteina': 9,    'carbs': 27,  'grasa': 2.6,  'kcal': 164},
    'pasta_integral':  {'proteina': 5,    'carbs': 25,  'grasa': 1,    'kcal': 124},
    'quinoa':          {'proteina': 4.4,  'carbs': 21,  'grasa': 1.9,  'kcal': 120},
    'elote':           {'proteina': 3.4,  'carbs': 19,  'grasa': 1.5,  'kcal': 96},
    'platano_macho':   {'proteina': 1,    'carbs': 32,  'grasa': 0.2,  'kcal': 122},
    'tortilla_harina': {'proteina': 8,    'carbs': 50,  'grasa': 8,    'kcal': 312},
    'pan_blanco':      {'proteina': 9,    'carbs': 49,  'grasa': 3,    'kcal': 265},
    'cereal_integral': {'proteina': 8,    'carbs': 78,  'grasa': 3,    'kcal': 370},
    'granola':         {'proteina': 10,   'carbs': 64,  'grasa': 18,   'kcal': 471},

    # ============================================================================
    # GRASAS (9 opciones)
    # ============================================================================
    'aceite_de_oliva':    {'proteina': 0,  'carbs': 0,  'grasa': 100, 'kcal': 900},
    'aguacate':           {'proteina': 2,  'carbs': 9,  'grasa': 15,  'kcal': 160},
    'nueces':             {'proteina': 15, 'carbs': 14, 'grasa': 65,  'kcal': 654},
    'almendras':          {'proteina': 21, 'carbs': 22, 'grasa': 49,  'kcal': 579},
    'mantequilla_mani':   {'proteina': 25, 'carbs': 20, 'grasa': 50,  'kcal': 588},
    'aceite_de_aguacate': {'proteina': 0,  'carbs': 0,  'grasa': 100, 'kcal': 900},
    'semillas_girasol':   {'proteina': 21, 'carbs': 20, 'grasa': 51,  'kcal': 584},
    'semillas_chia':      {'proteina': 17, 'carbs': 42, 'grasa': 31,  'kcal': 486},
    'cacahuates':         {'proteina': 26, 'carbs': 16, 'grasa': 49,  'kcal': 567},

    # ============================================================================
    # VERDURAS (20 opciones)
    # ============================================================================
    'brocoli':         {'proteina': 2.8, 'carbs': 7,   'grasa': 0.4, 'kcal': 34},
    'espinaca':        {'proteina': 2.9, 'carbs': 3.6, 'grasa': 0.4, 'kcal': 23},
    'calabacita':      {'proteina': 1.2, 'carbs': 3.1, 'grasa': 0.3, 'kcal': 17},
    'champiñones':     {'proteina': 3.1, 'carbs': 3.3, 'grasa': 0.3, 'kcal': 22},
    'coliflor':        {'proteina': 1.9, 'carbs': 5,   'grasa': 0.3, 'kcal': 25},
    'lechuga_romana':  {'proteina': 1.2, 'carbs': 3.3, 'grasa': 0.3, 'kcal': 17},
    'pepino':          {'proteina': 0.7, 'carbs': 3.6, 'grasa': 0.1, 'kcal': 15},
    'tomate':          {'proteina': 0.9, 'carbs': 3.9, 'grasa': 0.2, 'kcal': 18},
    'zanahoria':       {'proteina': 0.9, 'carbs': 10,  'grasa': 0.2, 'kcal': 41},
    'calabaza':        {'proteina': 1,   'carbs': 6.5, 'grasa': 0.1, 'kcal': 26},
    'col':             {'proteina': 1.3, 'carbs': 6,   'grasa': 0.1, 'kcal': 25},
    'nopal':           {'proteina': 1.7, 'carbs': 3.3, 'grasa': 0.1, 'kcal': 16},
    'ejotes':          {'proteina': 1.8, 'carbs': 7,   'grasa': 0.1, 'kcal': 31},
    'chayote':         {'proteina': 0.8, 'carbs': 4.5, 'grasa': 0.1, 'kcal': 19},
    'apio':            {'proteina': 0.7, 'carbs': 3,   'grasa': 0.2, 'kcal': 14},
    'pimiento_verde':  {'proteina': 0.9, 'carbs': 4.6, 'grasa': 0.2, 'kcal': 20},
    'pimiento_rojo':   {'proteina': 1,   'carbs': 6,   'grasa': 0.3, 'kcal': 31},
    'cebolla':         {'proteina': 1.1, 'carbs': 9.3, 'grasa': 0.1, 'kcal': 40},
    'jicama':          {'proteina': 0.7, 'carbs': 9,   'grasa': 0.1, 'kcal': 38},
    'betabel':         {'proteina': 1.6, 'carbs': 10,  'grasa': 0.2, 'kcal': 43},

    # ============================================================================
    # FRUTAS (18 opciones)
    # ============================================================================
    'manzana':     {'proteina': 0.3, 'carbs': 14, 'grasa': 0.2, 'kcal': 52},
    'platano':     {'proteina': 1.1, 'carbs': 27, 'grasa': 0.3, 'kcal': 89},
    'papaya':      {'proteina': 0.6, 'carbs': 12, 'grasa': 0.1, 'kcal': 43},
    'naranja':     {'proteina': 0.7, 'carbs': 12, 'grasa': 0.1, 'kcal': 47},
    'mango':       {'proteina': 0.7, 'carbs': 15, 'grasa': 0.3, 'kcal': 60},
    'melon':       {'proteina': 0.9, 'carbs': 8,  'grasa': 0.2, 'kcal': 34},
    'piña':        {'proteina': 0.5, 'carbs': 13, 'grasa': 0.1, 'kcal': 50},
    'fresa':       {'proteina': 0.7, 'carbs': 8,  'grasa': 0.3, 'kcal': 32},
    'uva':         {'proteina': 0.7, 'carbs': 18, 'grasa': 0.2, 'kcal': 69},
    'pera':        {'proteina': 0.4, 'carbs': 15, 'grasa': 0.1, 'kcal': 57},
    'guayaba':     {'proteina': 2.6, 'carbs': 14, 'grasa': 1,   'kcal': 68},
    'toronja':     {'proteina': 0.8, 'carbs': 11, 'grasa': 0.1, 'kcal': 42},
    'sandia':      {'proteina': 0.6, 'carbs': 8,  'grasa': 0.2, 'kcal': 30},
    'kiwi':        {'proteina': 1.1, 'carbs': 15, 'grasa': 0.5, 'kcal': 61},
    'mandarina':   {'proteina': 0.8, 'carbs': 13, 'grasa': 0.3, 'kcal': 53},
    'durazno':     {'proteina': 0.9, 'carbs': 10, 'grasa': 0.3, 'kcal': 39},
    'zarzamora':   {'proteina': 1.4, 'carbs': 10, 'grasa': 0.5, 'kcal': 43},
    'arandano':    {'proteina': 0.7, 'carbs': 14, 'grasa': 0.3, 'kcal': 57},
}

# ============================================================================
# LÍMITES POR COMIDA (gramos) - SIMPLIFICADOS Y REALISTAS
# ============================================================================

LIMITES_ALIMENTOS = {
    # --- Proteínas ---
    'pechuga_de_pollo':    250,
    'carne_magra_res':     250,
    'pescado_blanco':      200,
    'salmon':              150,
    'huevo':               170,
    'claras_huevo':        250,
    'queso_panela':        150,
    'yogurt_griego_light': 200,
    'proteina_suero':       40,
    'atun':                200,
    'carne_molida':        200,
    'pavo':                250,
    'cerdo_lomo':          200,
    'camarones':           200,
    'sardina':             120,
    'queso_cottage':       200,
    'yogurt_natural':      200,
    'jamon_pavo':          100,
    'leche_descremada':    300,
    'tofu':                200,
    # --- Carbohidratos ---
    'arroz_blanco':        250,
    'arroz_integral':      250,
    'papa':                250,
    'camote':              250,
    'avena':               150,
    'pan_integral':        100,
    'tortilla_maiz':       150,
    'frijoles':            250,
    'lentejas':            200,
    'garbanzos':           200,
    'pasta_integral':      250,
    'quinoa':              200,
    'elote':               200,
    'platano_macho':       200,
    'tortilla_harina':     100,
    'pan_blanco':          100,
    'cereal_integral':      80,
    'granola':              60,
    # --- Grasas ---
    'aceite_de_oliva':      20,
    'aguacate':            150,
    'nueces':               50,
    'almendras':            50,
    'mantequilla_mani':     40,
    'aceite_de_aguacate':   20,
    'semillas_girasol':     40,
    'semillas_chia':        30,
    'cacahuates':           50,
    # --- Verduras ---
    'brocoli':             150,
    'espinaca':            120,
    'calabacita':          200,
    'champiñones':         150,
    'coliflor':            120,
    'lechuga_romana':      150,
    'pepino':              200,
    'tomate':              200,
    'zanahoria':           150,
    'calabaza':            200,
    'col':                 150,
    'nopal':               200,
    'ejotes':              150,
    'chayote':             200,
    'apio':                150,
    'pimiento_verde':      150,
    'pimiento_rojo':       150,
    'cebolla':             100,
    'jicama':              150,
    'betabel':             150,
    # --- Frutas ---
    'manzana':             150,
    'platano':             150,
    'papaya':              200,
    'naranja':             150,
    'mango':               150,
    'melon':               200,
    'piña':                150,
    'fresa':               150,
    'uva':                 150,
    'pera':                150,
    'guayaba':             150,
    'toronja':             200,
    'sandia':              200,
    'kiwi':                150,
    'mandarina':           150,
    'durazno':             150,
    'zarzamora':           120,
    'arandano':            120,
}

# ============================================================================
# EQUIVALENCIAS PRÁCTICAS (para que el usuario entienda las porciones)
# ============================================================================

EQUIVALENCIAS_PRACTICAS = {
    # --- Proteínas ---
    'pechuga_de_pollo':    '≈ 1 pechuga mediana',
    'carne_magra_res':     '≈ 1 bistec mediano',
    'pescado_blanco':      '≈ 1 filete mediano',
    'salmon':              '≈ 1 filete de salmón',
    'huevo':               '≈ 2-4 huevos',
    'claras_huevo':        '≈ 8-9 claras',
    'queso_panela':        '≈ 1 porción mediana',
    'yogurt_griego_light': '≈ 1 taza (200 ml)',
    'proteina_suero':      '≈ 1 scoop (cucharada)',
    'atun':                '≈ 1 lata escurrida',
    'carne_molida':        '≈ 1 porción mediana',
    'pavo':                '≈ 1 pechuga mediana',
    'cerdo_lomo':          '≈ 1 filete mediano',
    'camarones':           '≈ 10-15 camarones medianos',
    'sardina':             '≈ 1 lata escurrida',
    'queso_cottage':       '≈ 1 taza',
    'yogurt_natural':      '≈ 1 taza (200 ml)',
    'jamon_pavo':          '≈ 3-4 rebanadas',
    'leche_descremada':    '≈ 1 vaso (250 ml)',
    'tofu':                '≈ 1 bloque pequeño',
    # --- Carbohidratos ---
    'arroz_blanco':        '≈ 0.5 taza cocida',
    'arroz_integral':      '≈ 0.5 taza cocida',
    'papa':                '≈ 1-2 papas medianas',
    'camote':              '≈ 1 camote mediano',
    'avena':               '≈ 0.3 taza cruda (puñado)',
    'pan_integral':        '≈ 2 rebanadas',
    'tortilla_maiz':       '≈ 6-8 tortillas',
    'frijoles':            '≈ 0.5 taza cocida',
    'lentejas':            '≈ 0.5 taza cocida',
    'garbanzos':           '≈ 0.5 taza cocida',
    'pasta_integral':      '≈ 0.5 taza cocida',
    'quinoa':              '≈ 0.5 taza cocida',
    'elote':               '≈ 1 elote mediano',
    'platano_macho':       '≈ 0.5 plátano macho',
    'tortilla_harina':     '≈ 2-3 tortillas',
    'pan_blanco':          '≈ 2 rebanadas',
    'cereal_integral':     '≈ 0.5 taza',
    'granola':             '≈ 0.25 taza',
    # --- Grasas ---
    'aceite_de_oliva':     '≈ 1 cucharada',
    'aguacate':            '≈ 0.5 aguacate',
    'nueces':              '≈ 15-20 nueces',
    'almendras':           '≈ 25-30 almendras',
    'mantequilla_mani':    '≈ 2 cucharadas',
    'aceite_de_aguacate':  '≈ 1 cucharada',
    'semillas_girasol':    '≈ 2 cucharadas',
    'semillas_chia':       '≈ 1.5 cucharadas',
    'cacahuates':          '≈ 1 puñado (30 g)',
    # --- Verduras ---
    'brocoli':             '≈ 2-3 puños cerrados',
    'espinaca':            '≈ 1-2 platos',
    'calabacita':          '≈ 1 calabacita pequeña',
    'champiñones':         '≈ 1 puñado grande',
    'coliflor':            '≈ 1 taza',
    'lechuga_romana':      '≈ 3-4 hojas grandes',
    'pepino':              '≈ 1 pepino mediano',
    'tomate':              '≈ 1-2 tomates medianos',
    'zanahoria':           '≈ 1-2 zanahorias',
    'calabaza':            '≈ 1 taza picada',
    'col':                 '≈ 1 taza rallada',
    'nopal':               '≈ 2 nopales medianos',
    'ejotes':              '≈ 1 taza picada',
    'chayote':             '≈ 1 chayote mediano',
    'apio':                '≈ 2-3 tallos',
    'pimiento_verde':      '≈ 1 pimiento mediano',
    'pimiento_rojo':       '≈ 1 pimiento mediano',
    'cebolla':             '≈ 0.5 cebolla mediana',
    'jicama':              '≈ 1 taza picada',
    'betabel':             '≈ 1 betabel mediano',
    # --- Frutas ---
    'manzana':             '≈ 1-2 manzanas medianas',
    'platano':             '≈ 1 plátano mediano',
    'papaya':              '≈ 1 taza',
    'naranja':             '≈ 1-2 naranjas',
    'mango':               '≈ 1 mango mediano',
    'melon':               '≈ 1 taza',
    'piña':                '≈ 1 taza',
    'fresa':               '≈ 8-10 fresas',
    'uva':                 '≈ 1 taza (15-20 uvas)',
    'pera':                '≈ 1 pera mediana',
    'guayaba':             '≈ 2-3 guayabas',
    'toronja':             '≈ 0.5 toronja',
    'sandia':              '≈ 1 taza picada',
    'kiwi':                '≈ 2 kiwis',
    'mandarina':           '≈ 2-3 mandarinas',
    'durazno':             '≈ 1-2 duraznos',
    'zarzamora':           '≈ 1 taza',
    'arandano':            '≈ 0.5 taza',
}

# ============================================================================
# CATEGORÍAS DE ALIMENTOS (para rotación y selección)
# ============================================================================

CATEGORIAS = {
    'proteina': [
        'pechuga_de_pollo',
        'carne_magra_res',
        'pescado_blanco',
        'salmon',
        'huevo',
        'claras_huevo',
        'queso_panela',
        'yogurt_griego_light',
        'proteina_suero',
        'atun',
        'carne_molida',
        'pavo',
        'cerdo_lomo',
        'camarones',
        'sardina',
        'queso_cottage',
        'yogurt_natural',
        'jamon_pavo',
        'leche_descremada',
        'tofu',
    ],
    'carbs': [
        'arroz_blanco',
        'arroz_integral',
        'papa',
        'camote',
        'avena',
        'pan_integral',
        'tortilla_maiz',
        'frijoles',
        'lentejas',
        'garbanzos',
        'pasta_integral',
        'quinoa',
        'elote',
        'platano_macho',
        'tortilla_harina',
        'pan_blanco',
        'cereal_integral',
        'granola',
    ],
    'grasa': [
        'aceite_de_oliva',
        'aguacate',
        'nueces',
        'almendras',
        'mantequilla_mani',
        'aceite_de_aguacate',
        'semillas_girasol',
        'semillas_chia',
        'cacahuates',
    ],
    'verdura': [
        'brocoli',
        'espinaca',
        'calabacita',
        'champiñones',
        'coliflor',
        'lechuga_romana',
        'pepino',
        'tomate',
        'zanahoria',
        'calabaza',
        'col',
        'nopal',
        'ejotes',
        'chayote',
        'apio',
        'pimiento_verde',
        'pimiento_rojo',
        'cebolla',
        'jicama',
        'betabel',
    ],
    'fruta': [
        'manzana',
        'platano',
        'papaya',
        'naranja',
        'mango',
        'melon',
        'piña',
        'fresa',
        'uva',
        'pera',
        'guayaba',
        'toronja',
        'sandia',
        'kiwi',
        'mandarina',
        'durazno',
        'zarzamora',
        'arandano',
    ],
}

# ============================================================================
# REGLAS DE PENALIZACIÓN (Qué NO se puede repetir en el mismo día)
# ============================================================================

REGLAS_PENALIZACION = {
    'huevo':               1,   # Max 1x día (huevo + claras = grupo)
    'claras_huevo':        1,   # Max 1x día
    'salmon':              1,   # Max 1x día (muy graso)
    'carne_magra_res':     1,   # Max 1x día (rojo)
    'pechuga_de_pollo':    2,   # Max 2x día (pollo es versátil)
    'pescado_blanco':      1,   # Max 1x día
    'aceite_de_oliva':     1,   # Max 1x día (grasa concentrada)
    'aceite_de_aguacate':  1,   # Max 1x día (grasa concentrada)
    'atun':                1,   # Max 1x día (mercurio)
    'sardina':             1,   # Max 1x día
    'carne_molida':        1,   # Max 1x día (rojo)
    'cerdo_lomo':          1,   # Max 1x día
    'camarones':           1,   # Max 1x día
}

# ============================================================================
# ROTACIONES POR COMIDA (Orden de preferencia)
# ============================================================================

ROTACIONES = {
    'desayuno': {
        'proteina': [
            'proteina_suero', 'yogurt_griego_light', 'yogurt_natural',
            'huevo', 'claras_huevo', 'queso_panela', 'queso_cottage',
            'jamon_pavo', 'leche_descremada', 'tofu',
        ],
        'carbs': ['avena', 'pan_integral', 'granola', 'cereal_integral', 'tortilla_maiz'],
        'grasa': ['almendras', 'nueces', 'semillas_chia', 'mantequilla_mani', 'semillas_girasol'],
        'verdura': ['brocoli', 'espinaca', 'champiñones', 'pimiento_rojo'],
        'fruta': [
            'platano', 'manzana', 'fresa', 'papaya', 'naranja',
            'mango', 'melon', 'piña', 'guayaba', 'mandarina',
        ],
    },
    'almuerzo': {
        'proteina': [
            'pechuga_de_pollo', 'atun', 'pescado_blanco', 'queso_panela',
            'jamon_pavo', 'pavo', 'camarones', 'huevo',
        ],
        'carbs': ['tortilla_maiz', 'arroz_blanco', 'frijoles', 'papa', 'lentejas', 'elote'],
        'grasa': ['aguacate', 'nueces', 'cacahuates', 'semillas_girasol'],
        'verdura': [
            'lechuga_romana', 'tomate', 'pepino', 'nopal',
            'chayote', 'zanahoria', 'jicama',
        ],
    },
    'comida': {
        'proteina': [
            'pechuga_de_pollo', 'carne_magra_res', 'pescado_blanco',
            'salmon', 'cerdo_lomo', 'atun', 'pavo', 'camarones',
            'sardina', 'carne_molida',
        ],
        'carbs': [
            'arroz_blanco', 'arroz_integral', 'papa', 'camote',
            'tortilla_maiz', 'frijoles', 'lentejas', 'garbanzos',
            'pasta_integral', 'quinoa', 'platano_macho',
        ],
        'grasa': ['aguacate', 'aceite_de_oliva', 'nueces', 'mantequilla_mani', 'aceite_de_aguacate'],
        'verdura': [
            'espinaca', 'calabacita', 'champiñones', 'brocoli',
            'ejotes', 'calabaza', 'col', 'chayote',
            'coliflor', 'pimiento_verde',
        ],
    },
    'cena': {
        'proteina': [
            'pechuga_de_pollo', 'pescado_blanco', 'claras_huevo',
            'pavo', 'camarones', 'queso_cottage', 'atun', 'tofu',
        ],
        'carbs': ['papa', 'camote', 'pan_integral', 'tortilla_maiz', 'avena', 'quinoa'],
        'grasa': ['nueces', 'almendras', 'semillas_chia', 'aceite_de_oliva'],
        'verdura': [
            'calabacita', 'coliflor', 'brocoli', 'espinaca',
            'nopal', 'chayote', 'pepino',
        ],
        'fruta': [
            'manzana', 'pera', 'papaya', 'naranja', 'melon',
            'piña', 'toronja', 'durazno', 'sandia', 'guayaba',
            'kiwi',
        ],
    },
}

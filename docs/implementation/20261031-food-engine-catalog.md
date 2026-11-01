# Revisión del motor y catálogo alimentario

Alcance: servicio web, cálculo y selección de alimentos. No se modifican fórmulas clínicas, límites comerciales, autenticación ni esquema PostgreSQL de clientes. El catálogo de alimentos reside por separado en `/data/config/alimentos.db`.

## Catálogo y procedencia

La lectura de producción, sin importar el inicializador ni escribir datos, confirmó 101 alimentos: 85 semillas originales y 16 extras existentes. La ampliación añade 70 perfiles de USDA SR Legacy, 14 por categoría. El catálogo contiene 171 IDs; 161 son candidatos para generación automática. Nueve altas son ingredientes o condimentos que requieren preparación y quedan fuera de selección automática. El registro histórico `proteina_suero` también se retira de esa selección cuando conserva exactamente P25/C8/G6/400 kcal por 100 g: sus valores se conservan para no alterar planes históricos ni personalizaciones.

Los 280 valores de proteína, carbohidratos, grasa y energía de las altas se cotejaron con el ZIP oficial, sus unidades, FDC ID y localizador JSON. Se conservan los valores de energía oficiales; 4P+4C+9G se usa como diagnóstico, no como igualdad universal ni regla para modificar alimentos con fibra o factores específicos. La edición y los snapshots rechazan valores ausentes, negativos, no finitos, booleanos y horarios inválidos.

Fuente: [USDA FoodData Central, descargas](https://fdc.nal.usda.gov/download-datasets/) y [SR Legacy abril de 2018, ZIP oficial](https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_json_2018-04.zip). SR Legacy es la edición final de ese conjunto histórico; no se presenta como información actual de una marca. Los 101 perfiles anteriores no reciben una certificación nutricional retrospectiva.

Datos versionados: `src/data/food_catalog_usda_2018.json`. Su SHA256 es `3ff159929282344c6fbefc9a21b11d1b41b297edd915711b6de5607c2f54091d`. La atribución USDA sólo se aplica si los cuatro nutrientes persistidos coinciden exactamente; una personalización no hereda indebidamente esa atribución. Estado de preparación y procedencia se reconstruyen desde el manifiesto, sin nuevas columnas SQLite. Horarios y topes en gramos son parámetros editoriales del producto, no recomendaciones de USDA. Las altas usan gramos del estado indicado y no equivalencias caseras inventadas.

El archivo verificado conserva sus bytes mediante una regla `-text` específica en `.gitattributes`. Así Git no convierte sus saltos de línea al crear el artefacto Linux. Las regresiones de empaquetado comprueban el blob preparado para publicar, su importación y el rechazo de una conversión que cambie su checksum. Se conserva el primer despliegue rechazado por integridad y la corrección, sin modificar nutrientes ni desactivar el verificador.

## Cálculo actual del cliente

El mapper crea `ClienteEvaluacion`; el motor conserva Katch-McArdle: masa libre de grasa = peso × (1 − grasa/100), TMB = 370 + 21,6 × masa libre de grasa, y GET = TMB × factor de actividad. Los factores existentes son 1,2; 1,375; 1,55 y 1,725. Déficit, mantenimiento y superávit aplican respectivamente 0,85; 1 y 1,10 al GET. La política existente asigna proteína de 1,8 g/kg, grasa de 0,8 g/kg y carbohidratos con las calorías restantes; conserva su ajuste de grasa a 0,6 g/kg si faltan calorías. Las comidas se reparten 20/25/30/25 %.

Si no se informó grasa corporal, se conserva el supuesto del 20 %, ahora marcado como estimado y visible en el PDF. Un 20 % informado es distinto de ese supuesto. Cero y valores inválidos ya no se camuflan como datos ausentes. El mapper también conserva sexo y plantilla; el sexo no se introduce como un nuevo coeficiente de esta fórmula.

El aporte de cada alimento se calcula como gramos × nutrientes por 100 g / 100. Esos cálculos describen el menú, no una ingesta confirmada ni una medición del paciente.

## Selección, cantidades y opciones

El catálogo se valida y congela por solicitud. La selección respeta exclusiones, disponibilidad automática, comida permitida, rotación y límites antes de recurrir a respaldos. Las listas de preferencias reordenan candidatos y no ocultan las nuevas incorporaciones. El registro de nombres canónicos se deriva del catálogo completo; los seis alias históricos se conservan.

El generador de opciones resuelve conjuntamente tres fuentes de macronutrientes, descontando primero las verduras. Después de redondear gramos verifica topes y energía. Sólo añade alternativas cuando **todas** las combinaciones independientes publicadas permanecen dentro del 5 % de la energía objetivo de esa comida. Puede publicar menos de tres opciones por grupo; no inventa alternativas. Guarda selección base, aportes reales, extremos de energía y peor desviación. El objetivo exacto se conserva en transporte y persistencia; el redondeo queda para la presentación.

Los ajustes de menú fijo respetan los mismos horarios y topes, sin el respaldo anterior de 999 g ni la expansión del 20 % sobre un límite duro. Tras recortar gramos se vuelve a calcular la energía. El modo estricto existente impide publicar un menú que no se pudo ajustar.

Un objetivo puede no ser representable con un único alimento por grupo dentro de sus topes. El perfil sintético de 70 kg, 12 % de grasa, actividad intensa y superávit puede ser rechazado en opciones; el fallo libera la reserva y no consume cuota confirmada. Ese perfil se comprobó también con menú fijo. No se relajan restricciones ni se prometen soluciones universales. Las alergias declaradas y solicitudes de revisión profesional siguen bloqueando la generación antes de CPU, PDF y publicación, sin excepciones por licencia.

## Presentación, historia y límites

Los PDF y la vista separan objetivos, cálculo de la selección base y rango de alternativas. Las instrucciones usan el estado crudo/cocido/escurrido indicado; ya no ordenan pesar universalmente en crudo. La metadata `calculo` incluye sólo método, indicador de estimación, versión/SHA del catálogo y base de pesaje. No duplica edad, peso, sexo, grasa exacta, notas ni restricciones privadas.

Se conserva la historia: no se recalculan planes o diarios anteriores. Las opciones y verduras nuevas guardan sus macros; registrar o consultar un menú no confirma consumo. El helper heredado de ajuste mensual presenta una oscilación al reutilizar su bandera, pero no está conectado al historial SQL actual de la web; no se activó ese automatismo ni se presenta como resuelto. La revisión comprueba aritmética, límites y trazabilidad; no añade una validación clínica del perfil.

## Operación y evidencia

Antes del cambio se hizo respaldo consistente de SQLite mediante su API de backup en memoria, se cifró en E: con clave en custodia separada y se ensayó la restauración e integridad. La promoción usa inserciones de faltantes y conserva los registros existentes; no se usa `--force` ni se sustituye la base de clientes. El reinicio de workers carga el catálogo ampliado y sus metadatos. La recarga local refresca también las listas derivadas.

Evidencia: `E:/MetodoBaseWorkspace/evidence/food-engine-catalog-20261031-6c64987469a5478eb5528c8bedacf668/`. Incluye archivo USDA y verificaciones independientes, controles negativos conservados, backups, contratos de datos, PDFs, casos ASGI con cuentas sintéticas y pin de fuentes. El fallo de redondeo y las fixtures históricas incompletas se conservan en sus recibos; no se relajan tolerancias ni aserciones de seguridad para obtener un PASS. Los conteos finales y la publicación efectiva se registran allí tras completar el gate y el despliegue. No se usan cobros, correo real ni cuentas de clientes para probar.

Gate final: 1.075 casos PASS, sin fallos, errores ni omisiones, con 490 archivos del producto estables. Los dos avisos son deprecaciones ya existentes. La revisión independiente ejecutó 10 escenarios con la fábrica real web y SQLite propia; recalculó 237 combinaciones publicadas, sin contarlas como 237 pruebas adicionales. Pasaron persistencia, PDF, límites, cuotas y su compensación, restricciones, privacidad y snapshots del diario. Chrome comprobó la presentación y los filtros con datos propios; no se atribuye un login ni proveedor real a ese harness. El control de nombres no definidos F821 también pasó. No se declara un gate global de estilo o una certificación clínica.

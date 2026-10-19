# R14: contrato preparatorio de fecha y consumo

Estado: helpers y DTO locales, sin ruta, tabla, sincronización ni sustitución del diario del navegador. La integración persistida corresponde a la migración26 posterior a objetos25; este módulo no acredita R14 completo.

`web/personal_diary_schemas.py` valida la selección de alimentos y cantidades del registro. `web/services/personal_diary_service.py` resuelve fecha local `America/Mexico_City` y una copia estructurada del alimento/menú procedente del plan del servidor. Rechaza fecha futura, rangos de consulta excesivos, números no finitos y selección que no pueda verificarse contra ese plan. No toma macros calculados por el navegador como autoridad ni convierte notas en restricciones clínicas.

El futuro caso de uso debe verificar principal vigente, pertenencia del plan y contexto personal/gimnasio antes de invocar estos helpers. La copia de consumo deberá conservarse aunque después se genere otro plan. Control de versión, unicidad por sujeto/fecha/contexto y concurrencia requieren persistencia; todavía no están implementados aquí. La selección de gimnasio no puede provenir de un `gym_id` arbitrario enviado por la UI.

QA revisó27 pruebas del autor y añadió ocho. Un JSON legado de5000 niveles reprodujo `RecursionError`; el lector ahora lo traduce al mismo409 `diary_source_unavailable` que otros cuerpos inválidos. Las35 pruebas finales independientes pasan con cuatro fuentes estables, en `evidence/personal-diary-values-independent-source.json`. La primera sonda de2000 niveles no reproducía el fallo en Python3.12 y se conserva como etapa, separada del caso rojo válido.

El diario previo de localStorage carece de identidad verificable en sus claves. Estos helpers no lo importan, asignan a una cuenta, exportan ni eliminan. La transición debe preservar los datos del usuario y requerir una selección explícita de alcance; la exportación personal R31 declara de momento esa exclusión. No se inventó una política de conservación ni una promesa clínica de consumo/agua.

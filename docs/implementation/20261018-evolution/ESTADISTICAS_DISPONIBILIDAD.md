# Disponibilidad de estadísticas

Contención local R15/R17/R23/B22, posterior al gate amplio de6d33b9e; todavía requiere revisión independiente. No completa el dashboard de acciones de R23.

En ambos routers `web/routes/stats.py` y `api/routes/stats.py`, una excepción al consultar los hechos o la serie diaria se capturaba y respondía HTTP200 con métricas0. La UI podía interpretar una consulta fallida como ausencia de clientes/actividad. Además, los logs incluían el texto de excepción, y el router API adjuntaba traceback e identidad del gimnasio.

Ahora ambos devuelven503 con código estable `statistics_unavailable` y mensaje acotado. Sólo se registra clase de excepción, sin identidad, texto, SQL/parámetros ni traceback. Una consulta exitosa sin datos conserva200 y ceros reales; el permiso se comprueba antes de consultar y no se convierte un403 en indisponibilidad. Los otros endpoints de estadísticas mantienen su contrato y errores existentes; no se atribuye esta corrección a ellos.

Coordinación reprodujo cuatro fallos y tres controles verdes antes, conservando el mismo archivo de pruebas. Después aprobó48 casos dirigidos (7 nuevos y regresiones API/aislamiento),19.42s; es evidencia de autor. [Antes](evidence/statistics-availability-before-source.json), [después](evidence/statistics-availability-author-source.json). No suma esas48 a los1813 del gate anterior ni presenta la suite anterior como aceptación de fuentes nuevas.

El dashboard existente muestra toast de error al fallar `Api.stats.obtener`; sus KPIs de membresía usan otro endpoint y no quedan reemplazados por ceros por esta ruta. Todavía hacen falta estados persistentes de error/reintento, fences de identidad en todo el dashboard, semántica civil de membresías, acciones/responsables verificables, accesibilidad y revisión de sus interpolaciones HTML. Esta contención no valida esas áreas ni cobra/contacta a nadie.

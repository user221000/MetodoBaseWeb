CI31: corrección congelada de tres fronteras
==========================================

Fuente `ed4a3be11fb1e921962182812362b515afd8885a`, sobre el e0 rechazado e intacto. El delta contiene11 archivos CI; producto equivalente a4a, checker original,173 identidades PG,23 helpers y8 locks permanecen iguales.

El ejecutable completo del checker se autentica por SHA256 normalizado antes de importar su API. Los132 negativos se prueban también mediante procesos CLI reales, además del positivo173. El mismo mutante que sustituye sólo main por return0 conserva el falso éxito de su CLI vacío, pero ahora el verificador FULL lo rechaza antes de importar módulos o crear la salida. No se corrige un falso éxito cambiando el contenido de los informes.

El workflow ejecuta daily_plan_snapshot.cjs y valida/publica su informe25. Se preservan sus7 casos nuevos y18 repeticiones exactas del diario. Los32 módulos frontend produjeron519 ejecuciones; esta cifra no representa519 criterios únicos. El verificador fija por separado este alcance y los hashes de ambas fuentes originales.

Los tres marcadores PG y el inventario de imagen calculan application_role_restricted_nonowner desde consultas físicas: cuatro flags del rol y owner de la base. Cada fuente exige el resultado verdadero antes de emitirlo; el consumidor exige presencia y booleano true. Los24 canarios de fragmentos SQL usan resultados simulados y no acreditan una consulta PostgreSQL real.

Resultado offline del autor:145 canarios workflow,115 bloques Bash-n y205 tests nuevos pasan; Ruff y pip check0. Los932 archivos tracked fuera de evidence y89 entradas Name/version de paquetes quedan quietos. La comprobación de paquetes no equivale a un hash de todos sus árboles instalados.

El primer recolector frontend falló después de completar todos los bloques y sus gates: un informe legado usa report[] en lugar de results[]/checks[]. Se conservan driver, scripts, logs y transcripción del error. El finalizador sólo consolidó esos mismos RAW y movió los informes propios a LAB; no repitió Node ni alteró resultados. La adaptación Windows del prelude chmod700 sigue declarada; no demuestra permisos Linux.

Alcance pendiente: revisión independiente del nuevo freeze,173 nodos PG reales, imagen, restore/browser actuales y Actions. Este lote no ejecutó PG, Chrome, QEMU, Docker ni servicios. HIST30 auténtico573 y sus23 VM/348 permanecen en el recibo previo; no se repitieron ni sustituyen CURRENT31. El directorio e0 previo y los rechazos de QA no se reescribieron.

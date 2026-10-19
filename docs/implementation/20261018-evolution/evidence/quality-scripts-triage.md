# Ampliación de calidad a scripts y entrypoints

QA implementó este ajuste; sus pruebas son validación de autor y requieren la revisión independiente del coordinador.

Se añadieron `scripts/` y todos los módulos Python de raíz salvo `conftest.py` a Ruff F821 y Bandit. AST también incluye scripts. La primera ejecución encontró siete alertas nuevas exclusivamente en utilidades archivadas: cuatro MD5 de comparación/checkpoint y tres interpolaciones SQL. Se corrigieron sin ampliar las seis excepciones históricas de Bandit.

Los MD5 conservan el formato histórico con `usedforsecurity=False`; no autentican datos. El lector del migrador elige sólo dos sentencias literales para `clientes`/`planes_generados` y parametriza límite/offset/checkpoint. Los dos muestreos del validador también parametrizan el límite. El import obsoleto `scripts.etl_mapping` se corrigió al módulo equivalente existente `scripts.archive.etl_mapping`, necesario para probar los métodos archivados. No se ejecutaron CLI de migración ni se accedió a fuentes reales.

Nueve pruebas con SQLite sintético comprueban paginación/checkpoint válidos, tabla ajena rechazada, fragmentos SQL tratados como valores y comparación de registros alterados. Evidencia: `pytest-archive-quality-author.xml`. El contrato histórico de checksum devuelve una advertencia por diferencias; se conserva. Estas pruebas no aprueban la herramienta archivada como gate de migración de producción ni cierran R23.

La tanda ampliada produjo Ruff limpio, 304 archivos Python parseados y Bandit con seis huellas conocidas/cero nuevas. `verify_quality_guards.py` copia el gate a un directorio temporal y verifica contra los binarios reales que F821, error de sintaxis y B602 bloquean tanto un script como un entrypoint. No importa ni ejecuta el código sintético inseguro. Evidencia: `quality-canary-guards.log`.

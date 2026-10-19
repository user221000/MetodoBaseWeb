# QA, aislamiento y puertas de integración

Fecha de ejecución: 18 de octubre de 2026, America/Mexico_City. Referencia histórica: [informe QA](../../audit/2026-10-18/qa/INFORME_QA.md). Este registro describe resultados nuevos y no modifica la auditoría.

## Línea base identificable

Se congelaron los archivos de `daa25efbf51d154710bad625025b345fa9ec9252` en una copia temporal independiente. [baseline-source.json](evidence/baseline-source.json) conserva rutas y SHA256. Con CPython 3.12.13 externo, el harness histórico inspeccionado, SQLite efímero y proveedores desactivados: **1168 aprobadas, 6 fallidas, 3 omitidas y 7 subtests aprobados, 88.14 s**. Evidencia: [log](evidence/pytest-baseline.log), [JUnit](evidence/pytest-baseline.xml), [dependencias realmente instaladas](evidence/environment-baseline.txt).

Los fallos eran tres expectativas Free 10 frente a implementación 5, dos usos del event loop global y una comprobación POSIX en Windows. La decisión posterior del usuario fija Free 10; se conserva esa expectativa. La línea base usaba dependencias ya instaladas y no se presenta como réplica de la imagen candidata ni del antiguo manifest desktop.

## Ejecución segura y contratos del harness

Desde el clon de implementación, después de instalar el target adecuado en un venv externo:

```powershell
python -X utf8 tests/run_isolated.py tests -q --tb=short
python -X utf8 tests/run_isolated.py tests --shuffle-seed=20261018 -n 2 -q --tb=short
python -X utf8 tests/run_isolated.py tests/test_api.py --reverse-order -q
python -X utf8 tests/run_isolated.py --serve-web
```

El último comando compone **web/main_web.py**, escucha sólo en `127.0.0.1:8765` y crea datos temporales. Cada proceso/worker tiene archivos separados. Cada caso elimina sus filas sintéticas en orden de claves foráneas antes y después, incluso cuando las rutas hacen commits propios. Una excepción de preparación/limpieza aborta; no se emite un token para un usuario cuya inserción falló. El propietario de prueba guarda `OWNER` explícito y versión de sesión inicial cero.

El runner elimina destinos/credenciales heredados de base de datos, backup, libpq, pagos, correo y telemetría; deshabilita dotenv. La ejecución directa de pytest rechaza `DATABASE_URL` heredada. PostgreSQL requiere URL explícita con host loopback y usuario/base `metodobase_test*`; no acepta overrides de conexión. TCP externo se rechaza en `connect` y `connect_ex`. Esto es una defensa del proceso Python y no un sandbox de red del sistema operativo. El proceso y el navegador no deben recibir claves reales.

SQLite `create_all` prepara exclusivamente tests unitarios/API. No demuestra migraciones, enums PostgreSQL ni RLS. PostgreSQL se valida por separado, sin `stamp` ni fallback a metadata:

```powershell
# Definir únicamente URLs del cluster sintético previamente verificado.
python -X utf8 tests/prepare_postgres.py
python -X utf8 tests/run_isolated.py tests/integration_postgres.py -q
python -X utf8 tests/run_isolated.py tests/integration_backup_restore_postgres.py -q
```

Los módulos `integration_*.py` se invocan explícitamente en un job obligatorio, por lo que no se omiten mediante skips. Requieren `METODOBASE_TEST_MIGRATOR_URL` y `METODOBASE_TEST_POSTGRES_URL`; backup usa el migrador. `METODOBASE_TEST_PG_BIN` permite fijar `pg_dump`/`pg_restore`; `METODOBASE_TEST_EVIDENCE_DIR` conserva mediciones. Nunca apuntarlos a desarrollo ni producción.

Redis tiene un opt-in independiente: `METODOBASE_TEST_REDIS_URL=redis://127.0.0.1:56379/15`. El harness sólo conserva esa variable después de validar esquema `redis`, host loopback, puerto 56379 y base 15, sin query ni fragmentos. La variable ordinaria `REDIS_URL` permanece vacía aunque se herede un destino externo. Los cuatro casos de `tests/integration_redis.py` se invocan explícitamente y fallan si falta servicio; cada caso usa un prefijo UUID y elimina únicamente sus claves. Comprueban Lua real, TTL fijo sin extensión por rechazos, reapertura al expirar, reparación de TTL ausente, cuatro procesos compitiendo por un límite compartido y dependencia HTTP de cuenta/IP con ventana de 900 segundos. La enumeración de claves se limita al prefijo propio; no hay comandos `FLUSH*`.

CI define un job Redis obligatorio con la etiqueta explícita `redis:7.4.11-bookworm`, incluida en el [catálogo oficial de imágenes](https://hub.docker.com/_/redis). La colección local verificó los cuatro casos; **su ejecución real sigue pendiente de Linux/Redis disponible**. No se presentan mocks de Redis ni pruebas HTTP de degradación como evidencia de atomicidad o distribución real.

CI también exige el escaneo del árbol entregable con Gitleaks 8.30.1, descargado fuera del checkout y validado contra el SHA256 publicado del archive Linux x64. El reporte contiene ubicaciones, reglas y hashes; no valores. La configuración hereda las reglas por defecto y limita excepciones a líneas de huellas SHA256 en archivos de evidencia concretos y dos literales CSRF sintéticos. Se probó contra el binario real que las excepciones no excluyen secretos nuevos en tests, docs, código o el mismo archivo de evidencia; los comentarios inline de exclusión no se respetan. La semántica de extensión y criterios AND está documentada en el [repositorio oficial de Gitleaks](https://github.com/gitleaks/gitleaks#configuration). El [probe independiente](evidence/secrets-config-independent-probe.json) guarda solamente metadatos; cinco tests del wrapper comprueban redacción, errores del scanner, versión y cambios/archivos nuevos durante la captura. Esto no sustituye un scan final sobre el árbol congelado ni un scan del historial Git.

## Cambios comprobables del harness y CI

Se reemplazó `pytest.created_id` por recursos propios de cada caso. Las tres pruebas HTML antes omitidas ahora usan rutas vigentes de la composición SaaS. Los tests cross-tenant locales crean dos usuarios/clientes persistidos y comprueban la ausencia de escritura ajena; ya no dependen de repositorios vacíos simulados. Su resultado SQLite no sustituye el gate PostgreSQL.

Se usa `asyncio.run` en Sentry, UTF-8 explícito y una comprobación de permisos adaptada al sistema operativo. El test Windows comprueba lectura/carga; no afirma haber auditado ACL. Los manifests de test separan runtime Linux, runtime Windows y paquetes desktop.

CI instala el runtime bloqueado del target, ejecuta SaaS serial y orden mezclado con dos workers, desktop en Windows/Linux, migración PostgreSQL real, restore cifrado e imagen/runtime reales. `ci-success` exige éxito de todos sus jobs, incluidos calidad, secretos y Redis. Los JUnit web/desktop bloquean si un caso requerido se convierte en skip; desktop exige además cargar QApplication con backend offscreen. No hay `continue-on-error` material. El gate Ruff F821 y el parseo AST son bloqueantes. Bandit permite solamente seis huellas de código históricas revisadas, con motivo y vencimiento; una alerta nueva bloquea revisión.

Los locks completos `requirements-test*.lock` incluyen runtime y herramientas con hashes para Linux/Windows y desktop por sistema. Esto evita mezclar un runtime con hashes y herramientas sin hashes en una única instalación pip. El target desktop limpio se creó aparte del target web; sus paquetes exactos están en [environment-candidate-desktop.txt](evidence/environment-candidate-desktop.txt).

La cobertura mide ramas y excluye entornos/dependencias. Los contratos nuevos `core/nutrition_validation.py`, `core/food_catalog.py` y `web/profile_schemas.py` exigen al menos **95% de líneas y 90% de ramas**, porque un fallback o entrada inválida omitidos alteran la seguridad de las exclusiones. [29 pruebas dirigidas](evidence/pytest-nutrition-focused.xml) alcanzaron **100% de líneas y ramas en esos tres módulos**. [156 pruebas independientes de motor, PDF y HTTP](evidence/pytest-nutrition-independent.xml) también pasaron. Estos porcentajes no certifican seguridad clínica ni cobertura completa de rutas web.

## PostgreSQL, restore y límites del entorno

Se localizaron binarios PostgreSQL 17.11 fuera de PATH y se creó un cluster nuevo en `127.0.0.1:55482`. El servicio PostgreSQL previo del equipo no se utilizó. El rol sintético de aplicación se verificó `NOSUPERUSER NOBYPASSRLS`: [inventario saneado](evidence/postgres-local.json). La primera migración desde vacío falló realmente por `gym_profiles` inexistente; [log](evidence/alembic-empty-psycopg2-before.log). Esto abrió R03 y no se sustituyó por `create_all`.

La primera restauración independiente cifrada validó filas, relaciones, claves foráneas, dos objetos privados sintéticos y rechazo de un destino ocupado: [JUnit](evidence/pytest-backup-postgres-independent.xml), [medición técnica](evidence/postgres-restore-independent.json). Usa bases creadas por la propia fixture. Ese ensayo pequeño se complementa después con el esquema Alembic candidato completo; no demuestra restauración de archivos históricos reales ni metas de negocio RPO/RTO.

Docker Desktop se inició con ventana oculta. El log actual del backend informó `Virtual Machine Platform not enabled` y `No virtualization available`; el daemon no respondió. No se habilitaron características del sistema ni se reinició Windows. Imagen Linux y Redis real siguen pendientes de un host con virtualización o runner autorizado. Los jobs correspondientes se prepararon, pero no se presentan como ejecutados en GitHub Actions. La instalación de clientes PostgreSQL del job usa el [repositorio oficial PGDG](https://www.postgresql.org/download/linux/ubuntu/).

Antes de cerrar R05/R18/R19 se requiere el gate congelado sobre candidato y dependencias finales, CI remota real y la evidencia PostgreSQL/imagen que todavía corresponda. Compras sandbox, correos realmente entregados, accesibilidad asistida y dictámenes clínicos conservan su validación propia.

## Observaciones de alcance que continúan abiertas

R01/B17: la primera reserva atómica implementada cubre el individuo. La ruta B2B todavía comprueba conteos diarios antes de iniciar generación; un lock de proceso no serializa varios workers. El catálogo también anuncia límites mensuales 20/100 cuya aplicación no se encontró en ese recorrido. La decisión comercial posterior fija Free en 10 clientes, 1 plan por cliente/día y 10 planes totales del gimnasio/día, iguales para web/desktop. Corresponde reproducir/corregir la última plaza/crédito B2B con ese contrato aprobado. El pase del bypass individual no cierra estas condiciones ni las aplaza a R28.

R03/R04: las migraciones desde vacío y baseline legado, conservación/rollback y restore del esquema candidato tienen evidencia independiente descrita abajo. El gate R04 conserva sus exigencias pendientes: rol restringido, políticas forzadas, dos gimnasios reales, tenant ausente, devolución al pool y commit interno. No existe aprobación de RLS por ejecutar SQLite ni por preservar flags durante una migración.

## Resultados posteriores a la contención A1

El commit local de contención es `166038f88b211c52f0d149ce550880795361707c`. Los siguientes resultados son tandas independientes con alcances que se solapan; no deben sumarse como casos únicos:

| Tanda | Resultado nuevo | Evidencia |
| --- | --- | --- |
| Harness/API/HTML/Sentry/roles/tenants locales en candidato web limpio, orden mezclado y dos workers | 109 aprobadas, ninguna omitida; 17.61 s | [JUnit](evidence/pytest-r05-frozen-candidate.xml), [huellas estables](evidence/qa-r05-frozen-hashes.json) |
| Desktop Windows limpio, servicios y PDF con Pillow 13 | 63 aprobadas y 7 subtests; 38.30 s | [JUnit](evidence/pytest-desktop-candidate.xml), [paquetes](evidence/environment-candidate-desktop.txt) |
| Catálogo y derechos B2B; expiración exacta, trial, compatibilidad temporal y decisión Free final 10/1/10 | 46 aprobadas; 4.61 s; fuentes estables | [JUnit](evidence/pytest-catalog-final-decision.xml), [huellas](evidence/catalog-final-decision-source.json) |
| Restore PostgreSQL cifrado con manifest autenticado actualizado, objetos y negativos de backup | 7 aprobadas; 5.00 s; script/test estables durante la ejecución | [JUnit](evidence/pytest-backup-postgres-mac.xml), [huellas](evidence/backup-postgres-mac-source.json) |
| Cuota individual en procesos PostgreSQL reales: último crédito y GET concurrente | A1: 2 fallidas/1 aprobada; fix posterior: 3 aprobadas, 34.37 s | [antes](evidence/pytest-quota-postgres-before.xml), [después](evidence/pytest-quota-postgres-after.xml), [snapshot A1](evidence/quota-a1-snapshot.json) |
| Revisión independiente UI de suscripción individual | 5 escenarios, sin errores JS; axe sin violaciones en 320/390/768/1440 px y diálogo; fuentes congeladas estables | [resultado](evidence/ux/subscription-independent.log), [huellas](evidence/ux/subscription-independent-source.json), [negativos HTTP200](evidence/ux/subscription-contract-review.json) |
| R17 degradación HTTP, cuenta/IP local y aislamiento Redis opt-in | 37 aprobadas; 3.58 s; no Redis real | [JUnit](evidence/pytest-redis-guard-independent.xml), [colección de integración pendiente](evidence/redis-integration-collection.log) |
| Contratos históricos adaptados a R06 y adapter MP compartido | 65 aprobadas; 4.61 s | [JUnit](evidence/pytest-audit-contract-independent.xml) |
| R17 final, aislamiento y rutas reales B2B/portales/API factory | 52 aprobadas; 5.35 s; ocho fuentes estables; no Redis real | [JUnit](evidence/pytest-redis-final-independent.xml), [huellas](evidence/redis-final-independent-source.json) |
| Sanitización y estabilidad del wrapper de secretos | 5 aprobadas; 0.92 s; scanner simulado sólo en estos tests | [JUnit](evidence/pytest-secret-scan-independent.xml), [probe separado con Gitleaks real](evidence/secrets-config-independent-probe.json) |
| UI B2B/R13 y regresión personal, revisión independiente final | 6 escenarios B2B, 17 estados R13 y 5 personales; 27 fuentes estables | [revisión y límites](evidence/ux/frontend-independent-review.md), [huellas](evidence/ux/frontend-independent-source.json) |
| R03 restaurable, negativos semánticos/timezone y factories finales | 15 aprobadas; 20.59 s; fuentes relevantes estables; incluye restore cifrado del esquema candidato completo de 22 tablas | [JUnit](evidence/pytest-r03-restorable-independent.xml), [huellas](evidence/r03-restorable-independent-source.json), [medición técnica del esquema completo](evidence/postgres-restore-release-schema-independent.json) |

Seguridad revisó independientemente el harness congelado sin observaciones altas/críticas dentro de su alcance; ver la revisión de seguridad de este lote. El smoke desktop no prueba instaladores ni sustituye una sesión manual completa de la aplicación. Los resultados web se distinguen de la imagen Linux, todavía no ejecutable en este equipo.

La prueba multiproceso de cuota prepara con metadata una base propia exclusivamente para concurrencia. No se usa como aceptación de migraciones o RLS. El mismo test nuevo ejecutado sobre el snapshot A1 reproduce un GET que pisa a cero un crédito recién reservado al cambiar de mes y una colisión al crear la proyección. Después del lock común, ambos casos y los tres procesos que disputan el último crédito pasan. La primera sonda, que no sincronizaba el arranque del escritor ni llevaba consumo del mes anterior, no reproducía esos fallos; sus resultados se preservaron como `initial-probe` y no sustentan el cierre.

H02 exigía texto de un lock global eliminado por el catálogo inmutable de R06. Sus dos pruebas ahora intentan modificar datos anidados y ejecutan selectores reales desde ocho threads con exclusiones distintas, conservando el catálogo global. La prueba adicional de planes completos concurrentes sigue vigente. H04 buscaba HMAC en un router que delega al adapter compartido; ahora verifica firma válida, firma alterada, recurso procesado diferente y vencimiento contra ese adapter. M11 exigía una llamada sin el argumento `catalogo`; ahora comprueba cantidades redondeadas y energía calculada con un catálogo propio. Ninguna de estas conversiones cambia límites comerciales o elimina el rechazo de datos inseguros.

El launcher `--serve-web` prepara explícitamente metadata en su SQLite efímera antes de componer el runtime real; esa preparación pertenece a la fixture de navegador. El producto conserva la verificación de esquema y no ejecuta DDL implícito al arrancar. El nuevo servidor sintético en `127.0.0.1:8765` respondió readiness 200; su log está en `evidence/ux/synthetic-server.log`.

La revisión R17 detectó tres nombres B2B reales ausentes de la clasificación sensible: Stripe subscribe, confirm-subscription y MP preference entraban al handler con Redis caído. [Tres fallos reproducidos](evidence/pytest-redis-paths-before.xml) preceden la corrección. El gate final añade ambos portales y comprueba composición standalone con Redis configurado; preserva 503 antes de efectos y readiness 200.

R03: las primeras 24 pruebas independientes de migración alcanzaron verde, pero su freeze quedó superado por añadir atributos de tipos y el gate standalone. La tanda posterior produjo 27 aprobadas y tres fallos: dos eran un patch de test incorrecto reparado por el autor; el tercero reprodujo que el esquema completo restaurado por pg_dump/pg_restore no satisfacía la firma textual. El [diff anterior a la corrección](evidence/postgres-restore-release-schema-drift.json) conserva siete CHECK donde PostgreSQL distribuye casts de ARRAY durante la restauración.

La corrección normaliza exclusivamente predicados completos ANY/ARRAY de literales varchar→text, preservando nombres, valores, condiciones y permiso de NULL. La revisión de código y los negativos PG reales de valor añadido, `OR true` y drift de timezone pasaron junto con factories y ambos restores: **15 aprobadas, 20.59 s**. El esquema completo de 22 tablas satisface ahora el gate de runtime después de restaurarlo; las filas de todas las tablas, revisión Alembic, relaciones, flags RLS, secuencia y dos archivos privados sintéticos coinciden. Los ensayos previos de conservación/defaults/rollback siguen como evidencia del mismo código de migración de datos, sin repetición innecesaria. El hash de `entrypoint.sh` se registra separado porque su conversión CRLF→LF y verificación Bash pertenecen al gate shell del coordinador. No se aprueba R04 por preservar flags de RLS: su activación y contexto por transacción continúan pendientes.

# Auditoría QA y pruebas — 2026-10-18

## Alcance y entorno

Revisión de los 37 archivos `test_*.py`, fixtures, CI, manifest de dependencias, migraciones, sintaxis de todo el código Python propio y análisis estático. Windows, CPython 3.12.13, SQLite efímero; variables saneadas e integraciones externas deshabilitadas. Ninguna prueba funcional se ejecutó contra Railway. No se modificó código de producto.

La aplicación web real se inició exclusivamente en `127.0.0.1:8765`, con otra BD temporal, para que el agente UX pudiera recorrerla con navegador. Sus resultados están en `../ux/`. Esa sesión no forma parte del porcentaje de cobertura pytest.

## Resultados reproducidos

| Verificación | Resultado | Evidencia |
|---|---|---|
| Colección pytest | 1177 casos, en 37 archivos | `collection.log` |
| Primera ejecución, sin sembrar esquema ni agregar dependencias de tests faltantes | 1128 pasan, 44 fallan, 5 omitidos; 74.85 s | `pytest-baseline.log`, `pytest-baseline.xml` |
| Ejecución normalizada: esquema ORM local, UTF-8, pypdf y pytest-asyncio instalados | 1168 pasan, 6 fallan, 3 omitidos; 152.40 s | `pytest-normalized.log`, `pytest-normalized.xml` |
| Dos tests Sentry que fallan en suite, ejecutados solos | 2 pasan | `pytest-sentry-isolated.log` |
| Sintaxis AST, todos los directorios propios y scripts raíz | 260 archivos; cero errores de sintaxis | `syntax-ast.json` |
| Ruff | 1976 diagnósticos; uno de nombre no definido | `ruff.json`, `summary.json` |
| Bandit `-ll --skip B101` | 6 alertas automáticas; requieren interpretación | `bandit.json` |
| Carga de usuario con rol introducido por migración | `LookupError` reproducido | `migration-probe.log` |
| Bootstrap con error de upgrade simulado localmente | Devuelve normalmente y mantiene versión head | `migration-probe.log` |

Pytest informa también 7 subtests aprobados. JUnit los cuenta aparte y por eso contiene 1184 entradas; no son 1184 tests de colección.

Los 44 fallos iniciales se descomponen en 12 por esquema/fixture sin tablas, 8 por falta de pytest-asyncio, 10 por falta de pypdf, 9 por lectura de UTF-8 con encoding Windows por defecto, 1 por permisos POSIX en Windows, 3 por límite Free discrepante y 1 login cuyo fixture no persistió el usuario. La segunda ejecución permite separar estos problemas de preparación del comportamiento de producto.

Los 6 fallos finales son: 3 discrepancias del catálogo Free, 1 supuesto de permisos POSIX y 2 tests Sentry que dependen de un event loop global. Los últimos dos pasan aislados y no prueban un defecto del servicio Sentry. Las 3 omisiones finales son rutas HTML declaradas en `tests/test_api.py:146`, `:153`, `:160` como ajenas a la app API.

## Cobertura medida

Cobertura de sentencias de esta ejecución: **6890 / 22508 = 30.61%**. No se midieron ramas. Se incluyeron expresamente `api`, `web`, `core`, `src`, `utils`, `config`, `ui_desktop`, `design_system`; se excluyeron entornos virtuales y dependencias. Los modelos/engine se importaron al sembrar esquema antes del arranque de pytest-cov; algunas líneas de importación/inicialización quedan subcontadas. El porcentaje no representa pruebas de navegador, calidad clínica, vulnerabilidades ni cobertura en producción.

| Área | Sentencias cubiertas |
|---|---:|
| API independiente | 73.64% |
| Web usada por SaaS | 41.12% |
| Motor/core | 46.24% |
| Persistencia legacy/src | 29.37% |
| Desktop | 11.05% |
| Configuración | 51.55% |
| Utilidades | 32.51% |
| Design system Python | 88.33% |

Rutas web relevantes: `planes.py` 17.89%, `usuario.py` 20.06%, `billing.py` 22.42%, `clientes.py` 28.41%, `auth.py` 30.39%, `team.py` 35.71%. Parte corresponde a importaciones/declaraciones, por lo que no implica que esos porcentajes de operaciones estén comprobados. El detalle de líneas ejecutadas y faltantes está en `coverage.json`; los agregados en `summary.json`.

## Hallazgos con evidencia y criterios de aceptación

### QA-01 — Alta: el CI no instala dependencias necesarias para recolectar y ejecutar la suite web

**Referencia:** `.github/workflows/ci.yml:95`, `:96`, `:142`; `requirements.txt:1`.

CI instala el manifest desktop más pytest, pytest-cov y pytest-xdist. Resolución seca con `uv pip compile requirements.txt --python-version 3.12` confirma ausentes `httpx`, `sqlalchemy`, `alembic`, `jinja2`, `python-multipart`, SDK de pagos, `pypdf` y `pytest-asyncio`; ver `ci-manifest-check.json`. FastAPI y bcrypt sí llegan transitivamente, por lo que no se reportan como ausentes. Los tests importan directamente bibliotecas ausentes durante colección/ejecución. No se consultó la última ejecución remota de GitHub Actions.

**Acción/aceptación:** separar dependencias web, desktop y pruebas; job SaaS instala el mismo runtime bloqueado que Docker más dependencias de tests; runner limpio Python 3.11/3.12 recolecta toda la suite sin módulos faltantes; build valida la imagen real.

### QA-02 — Alta: fixtures no aíslan ni preparan la BD de pruebas

**Referencia:** `conftest.py:18`, `:40`, `:41`, `:64`, `:65`; `web/database/engine.py:27`.

No se impone DATABASE_URL de pruebas ni schema/rollback/cleanup por caso. La fixture usa el engine por configuración, intenta insertar usuario y silencia cualquier excepción; después emite un token aunque el usuario no exista. En BD local vacía se reprodujeron respuestas 500 por `no such table: clientes` y fallos de login. Si el operador hereda variables reales, las fixtures pueden escribir usuarios sintéticos en esa BD. Esta auditoría evitó ese riesgo con harness offline y BD efímera.

**Acción/aceptación:** rechazar URL no autorizada antes de conectar; BD PostgreSQL de tests y namespace por worker; migrar una vez y rollback/limpieza garantizados; cualquier fallo al crear fixture aborta explícitamente; ejecutar suite nunca cambia BD de desarrollo o producción.

### QA-03 — Alta: las migraciones pueden aparentar éxito sin cambios aplicados

**Referencia:** `db_bootstrap.py:56`, `:80`, `:114`, `:117`; `entrypoint.sh:17`.

Bootstrap crea tablas ORM, y en ausencia de alembic_version ejecuta stamp(head). Eso omite operaciones que no forman parte de metadata, como políticas RLS de `c4f8e9d2a3b1_enable_rls_policies_multi_tenant.py:41`. Además captura fallos de upgrade como no fatales. Probe SQLite local con fallo de upgrade inyectado confirma retorno normal y versión `20260402_plan_json`. La omisión de RLS es deducción del flujo; no se verificó pg_policies de Railway.

**Acción/aceptación:** migración desde vacío y actualización desde snapshots previos reales en PostgreSQL; fallo de DDL devuelve código no cero e impide release; comprobar schema, índices, constraints y políticas, además de número de versión. Probar restauración y rollback con datos sintéticos.

### QA-04 — Alta: rol por defecto de migración incompatible con el ORM

**Referencia:** `web/database/alembic/versions/f8a1b2c3d4e5_add_all_missing_tables_production.py:44`; `web/database/models.py:82`.

La migración añade role con `server_default='viewer'`; SQLEnum(UserRole) espera los nombres `OWNER`, `ADMIN`, `NUTRIOLOGO`, `VIEWER`. Insertar localmente un usuario con el valor que produciría la migración y cargarlo por ORM reproduce LookupError. Impacta bases antiguas cuyos usuarios reciben ese default; no se afirma que existan esos registros en Railway.

**Acción/aceptación:** contrato de serialización único para enums, backfill de valores antiguos y mapeo correcto de propietarios; migración de snapshot con usuarios antiguos permite login y conserva permisos sin elevar privilegios.

### QA-05 — Alta: el aislamiento entre gimnasios no está demostrado en PostgreSQL real

**Referencia:** `tests/test_multi_tenant_isolation.py:123`, `:127`, `:150`, `:274`, `:312`, `:316`; `.github/workflows/ci.yml:68`.

Los casos de clientes cross-tenant sustituyen autenticación y repositorio por mocks vacíos; comprueban parámetros/respuestas simuladas, sin crear dos gimnasios y sus clientes reales. Algunos tests silencian errores y sólo afirman si el mock fue llamado. Los repositorios de configuración sí tienen un caso de separación local, que no cubre las rutas de clientes/planes/RLS. CI no define un servicio PostgreSQL.

**Acción/aceptación:** dos tenants, propietario/admin/nutriólogo/viewer/cliente y datos reales en PostgreSQL; intentos cruzados de listar, leer, actualizar, borrar y descargar nunca filtran datos; mismo resultado con conexiones reutilizadas y con tenant ausente; políticas comprobadas con rol de aplicación sin bypass RLS.

### QA-06 — Media: catálogo de planes discrepante entre web, desktop y tests

**Referencia:** `web/constants.py:59`, `config/constantes.py:93`, `tests/test_feature_gate.py:62`, `:277`, `:302`.

Free permite 5 clientes en web y 10 en config desktop/tests. Tres fallos persistentes lo reproducen; no debe cambiarse el test ni el límite sin fijar la decisión comercial.

**Acción/aceptación:** única definición de catálogo y contrato; pricing, endpoints, dashboard y ambos clientes muestran y aplican el mismo límite; probar N−1, N, N+1 y downgrade con datos existentes.

### QA-07 — Media: controles CI no impiden promoción con problemas de calidad/seguridad

**Referencia:** `.github/workflows/ci.yml:62`, `:110`, `:170`, `:176`.

Ruff y Bandit usan continue-on-error; ci-success no depende del job security; cobertura no impone umbral ni tiene config que excluya entornos versionados. No hay job visible de navegador, accesibilidad, performance ni migración PostgreSQL.

**Acción/aceptación:** baseline revisado de reglas relevantes y fallos de seguridad confirmados bloqueantes; gates de cobertura de código modificado y casos críticos; E2E SaaS sobre imagen candidata; exclusión explícita de venv/build/tests en métrica de producto.

### QA-08 — Media: orden/paralelismo puede omitir regresiones

**Referencia:** `tests/test_api.py:78`, `:118`, `:134`; `.github/workflows/ci.yml:113`; `tests/test_sentry_setup.py:255`, `:278`.

Lectura y borrado dependen de pytest.created_id creado por otro test. En xdist cada proceso tiene su copia y esos tests pueden omitirse. Los dos tests Sentry asumen un event loop global: fallan después de otros tests async, pero ambos pasan solos. No se ejecutó xdist en esta auditoría; el riesgo de omisión está sustentado por el estado global y el skip explícito.

**Acción/aceptación:** fixture por caso que crea/limpia recurso; ningún test depende de otro; usar asyncio.run o fixtures async; suite pasa serial, con orden aleatorio y con al menos dos workers sin omisiones por dependencia.

### QA-09 — Media: faltan contratos E2E sobre la aplicación web publicada

**Referencia:** `tests/test_api.py:16`, `tests/test_integracion.py:21`, `tests/test_auth_audit.py:309`; porcentajes por ruta en `summary.json`.

La mayor parte de integración usa api.app.create_app, mientras Railway arranca web.main_web. Sólo un test de auditoría importa la app web real; las pruebas HTML del API están omitidas. No se halló suite Playwright/axe/Selenium en el proyecto. No se probaron en suite persistencia del portal del cliente, teclado, móvil o pagos con eventos reales de sandbox. El agente UX añadió evidencia de navegador independiente en esta auditoría.

**Acción/aceptación:** flujos automatizados de propietario y cliente sobre la app/imagen que se publica: registro→onboarding→cliente→plan→PDF→portal; invitación→rol→revocación; checkout sandbox→webhook duplicado→estado; refresh/logout; accesibilidad teclado, validación visible, 390 px y desktop; estados vacíos/error/carga.

### QA-10 — Baja: pruebas/herramientas poco portables y deuda estática

**Referencia:** `tests/services/test_key_manager.py:26`, `tests/test_audit_remaining_fixes.py:155`, `requirements_web.lock:110`, `ui_desktop/pyside/login_premium.py:1365`.

Un test asume bits POSIX en Windows; 9 fallos iniciales vienen de read_text sin encoding. El lock incluye uvloop sin marcador de plataforma y su instalación falló en Windows. Ruff detectó QApplication no importado en login premium: el NameError queda capturado y desactiva animaciones silenciosamente, sin demostrar crash. Es un defecto desktop, separado del SaaS.

**Acción/aceptación:** encoding UTF-8 explícito; validación permisos acorde al SO; lock y manifests coherentes por target; reglas F821 y sintaxis bloqueantes. No convertir todos los 1976 diagnósticos Ruff en bugs de producto.

## Interpretación de Bandit

Las 6 alertas no equivalen a 6 vulnerabilidades. MD5 en `web/main_web.py:289` calcula versión de archivos estáticos, sin función criptográfica de seguridad. Las interpolaciones SQL de `src/alimentos_sqlite.py:33` y `src/migrar_catalogo_sqlite.py:38` usan allowlist/constantes. Las llamadas urllib de `core/licencia.py:565` y `:669` usan una URL base HTTPS fija. Binding 0.0.0.0 de `web/main_web.py:467` es esperado en un contenedor. Ninguna de estas 6 quedó demostrada aquí como explotación. Los hallazgos de seguridad manuales del otro agente tienen mayor relevancia.

## Roadmap QA propuesto

1. **P0, antes de otro release:** QA-01 a QA-05. CI reproducible, esquema/roles verificables, migraciones que fallen de forma explícita e integración PostgreSQL de dos tenants.
2. **P1, siguiente ciclo:** catálogo único, fixtures independientes, gates relevantes y E2E de propietario/cliente con teclado/móvil, utilizando los bugs UX reproducidos como casos de regresión.
3. **P2, antes de crecer carga:** pruebas de concurrencia y cuotas, duplicados/reintentos de webhooks, expiración de trial/token, restauración desde backup y budgets de latencia de plan/PDF con carga representativa. Definir SLO con medición; no inventar capacidad concurrente.
4. **P3:** elevar cobertura útil por riesgo, automatizar compatibilidad desktop si sigue siendo producto activo y eliminar tests basados sólo en texto cuando un contrato observable sea más estable.

## Comandos y reproducción

Se creó un venv temporal fuera del repositorio con `uv venv --python 3.12`. La instalación del lock web se intentó y falló por uvloop/Windows; se usó `requirements_web.txt` más pytest, pytest-cov, pytest-xdist, Pillow, matplotlib, pandas, openpyxl y PySide6 6.8.3. Para normalizar la segunda ejecución se añadieron pypdf y pytest-asyncio. Las versiones efectivas figuran en `environment-freeze.txt`; no son una réplica exacta del entorno Railway.

Harness portable incluido: `isolated_runner.py`. Crea BD/carpeta temporales, desactiva integraciones y bloquea conexiones no loopback. Desde un venv con esas dependencias:

```powershell
python -X utf8 docs/audit/2026-10-18/qa/isolated_runner.py --seed-schema tests -q --tb=short
python -X utf8 docs/audit/2026-10-18/qa/isolated_runner.py --seed-schema tests/test_sentry_setup.py::TestWithSentryContext -q
```

Para cobertura se usaron `--cov=api --cov=web --cov=core --cov=src --cov=utils --cov=config --cov=ui_desktop --cov=design_system --cov-report=json:docs/audit/2026-10-18/qa/coverage.json --cov-report=term`. La base de medición `.coverage` quedó dentro de esta carpeta, no en raíz.

Análisis estático: `ruff check` sobre las ocho carpetas de producto, tests y scripts Python raíz; `bandit -r api core web src utils config ui_desktop design_system -ll --skip B101 -f json`. Sintaxis mediante ast.parse de los 260 archivos propios, sin producir bytecode ni ejecutar sus módulos.

## Límites

No se ejecutó imagen Docker, PostgreSQL local, xdist, ataque activo contra producción, pago real/sandbox, carga, restauración de backup ni verificación clínica. No se afirma certificación de seguridad, cobertura 100%, conformidad normativa ni comportamiento de Railway a partir de una suite SQLite. La lectura de configuración y los probes de migración señalan riesgos reproducibles o inferencias identificadas, con evidencia diferenciada.

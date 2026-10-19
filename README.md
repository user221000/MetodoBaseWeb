# MetodoBase

Monolito Python con SaaS FastAPI/Jinja/SQLAlchemy, motor nutricional compartido y cliente desktop PySide6 soportado. Este checkout contiene el candidato local de evolución; el [estado de ejecución](docs/implementation/20261018-evolution/ESTADO.md) distingue código, validación y despliegue. El mapa conserva los [92 requisitos originales y los añadidos](docs/implementation/20261018-evolution/TRAZABILIDAD.md).

## Desarrollo y pruebas reproducibles

Python objetivo: **3.12**. Los locks web y de pruebas se resuelven por plataforma; no instalar el lock Windows en Linux. Las dependencias de pruebas incluyen el runtime correspondiente y hashes. No se requieren secretos ni acceso a producción para las pruebas locales.

Windows, desde PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements-test-windows.lock
.\.venv\Scripts\python.exe -X utf8 tests/run_isolated.py tests -q
```

Linux:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-test.lock
.venv/bin/python -X utf8 tests/run_isolated.py tests -q
```

Desktop usa `requirements-test-desktop-windows.lock` o `requirements-test-desktop.lock` para reproducir su entorno de validación. `main.py` inicia la GUI. En Linux sin pantalla se necesita el backend Qt offscreen para sus pruebas. El runtime web de la imagen usa exclusivamente `requirements_web.lock` con hashes; Windows tiene `requirements_web-windows.lock`.

El harness elimina configuración heredada de BD/proveedores, desactiva dotenv/envíos, crea SQLite temporal por worker y restringe sockets a loopback dentro del proceso. No es un sandbox del sistema operativo. Ejecutar siempre mediante `tests/run_isolated.py`; los scripts históricos de auditoría no son el runner vigente. Para paralelismo y orden reproducible:

```powershell
.\.venv\Scripts\python.exe -X utf8 tests/run_isolated.py tests -n 2 --shuffle-seed 20261018 -q
```

Las integraciones PostgreSQL y Redis se invocan por sus archivos `tests/integration_*.py`, con URLs sintéticas explícitas y validadas; no se omiten para aparentar aceptación. PostgreSQL requiere los roles migrador y app separados, este último NOSUPERUSER/NOBYPASSRLS. Redis de prueba sólo admite loopback:56379/db15. Consulte el [registro QA](docs/implementation/20261018-evolution/QA_R05.md) y la CI para la preparación exacta. SQLite no acredita RLS ni concurrencia entre procesos PostgreSQL.

## Navegador aislado

```powershell
.\.venv\Scripts\python.exe -X utf8 tests/run_isolated.py --serve-web
```

Sirve el candidato en `127.0.0.1:8765` con esquema SQLite efímero preparado por la fixture, proveedores apagados y sin usuarios reales. Los recorridos Playwright/axe viven en `tests/e2e`; la instalación Node se prepara aparte con su package-lock. Sus dobles de proveedor prueban UI/contratos; no equivalen a compra sandbox, correo entregado o lector de pantalla ejecutado.

## Arranque normal y esquema

Copiar `.env.example` a configuración local fuera de control de versiones y completar sólo los valores necesarios. `DATABASE_URL` debe ser explícita para migrar. En desarrollo se puede usar SQLite en un directorio local ya creado; producción requiere PostgreSQL. Primero ejecutar `python db_bootstrap.py`; después `python -m uvicorn web.main_web:create_app --factory --host 127.0.0.1 --port 8000`. Las fábricas validan esquema existente y no lo crean ni reparan al recibir tráfico.

Web/API también requieren un destino privado explícito: `OBJECT_STORAGE_BACKEND=local` con `OBJECT_STORAGE_LOCAL_ROOT` absoluto fuera de rutas públicas, o configuración S3 completa de un bucket existente. No hay fallback ni descubrimiento de credenciales, endpoints, CA o proxies heredados. Las fixtures lo configuran automáticamente en su raíz temporal; el arranque normal necesita [configuración de documentos](docs/implementation/20261018-evolution/ALMACENAMIENTO.md). Un directorio local sólo es durable en producción cuando montaje, backup y reemplazo han sido verificados.

Una base existente sin Alembic se rechaza. `--adopt-verified-legacy` sólo admite el snapshot estructural exacto revisado; asigna una revisión histórica conocida y ejecuta las migraciones reales. Un drift necesita reconciliación expresa. Nunca usar `stamp head` o `create_all` como atajo de despliegue. Consulte [ADR de migraciones](docs/implementation/20261018-evolution/evidence/backend-r03-design.md) y [backup/restore](docs/implementation/20261018-evolution/BACKUP_RESTORE.md).

Railway existente ejecuta `preDeployCommand`; Docker independiente migra mediante entrypoint con fallo bloqueante. La imagen base y el lock están fijados. La imagen Linux final aún necesita build/SBOM/escaneo/aceptación por digest. La [transición de Railway a IaC](docs/implementation/20261018-evolution/NUEVOS_HALLAZGOS.md) es un requisito añadido; no aplicar infraestructura ni desplegar desde este procedimiento local.

## Contratos vigentes

- [Catálogo y derechos](docs/implementation/20261018-evolution/CATALOGO.md): Free 10 clientes, 1 plan por cliente/día, 10 totales por gimnasio/día; cuotas individuales separadas y moneda MXN explícita.
- [Dinero e idempotencia](docs/implementation/20261018-evolution/evidence/backend-money-contract.md): una compra/redirect no concede acceso sin estado verificado del proveedor.
- [Sesiones, controles y datos](docs/implementation/20261018-evolution/evidence/security-controls.md): revisión acotada y pendientes explícitos; no certificación integral.
- [Redis y degradación](docs/implementation/20261018-evolution/REDIS.md): acciones sensibles cerradas ante fallo y fallback de lecturas acotado.
- [Continuidad](docs/implementation/20261018-evolution/BACKUP_RESTORE.md): fuentes explícitas, cifrado/MAC y restauración a destino vacío.
- [Arquitectura actual y transitoria](docs/implementation/20261018-evolution/ARQUITECTURA_ACTUAL.md): composición SaaS, módulos compartidos y relaciones de autoridad, con pendientes explícitos.
- [Aislamiento y migrador](docs/implementation/20261018-evolution/AISLAMIENTO.md):17 familias iniciales R04, más ledger y objetos hasta19 en esquema25; seis grupos de control, rol app distinto del propietario/migrador.
- [Equipo](docs/implementation/20261018-evolution/EQUIPO.md), [licencias](docs/implementation/20261018-evolution/LICENCIAS.md) y [objetos privados](docs/implementation/20261018-evolution/ALMACENAMIENTO.md): compatibilidad y alcance revisado de cada consumidor.

Los catálogos nutricionales nuevos son inmutables por solicitud; exclusiones estructuradas llegan a todos los selectores y se verifican en el resultado. Las notas libres no garantizan protección clínica. La revisión nutricional profesional permanece separada de las pruebas del motor.

La documentación histórica conserva fecha y evidencia propia bajo `docs/audit/2026-10-18`; no describe automáticamente la versión candidata. No versionar entornos, uploads, backups, bases ni secretos. El escaneo del entregable usa `scripts/scan_secrets.py` con Gitleaks fijado y reportes sin valores. Para revisar el mapa: `python -X utf8 scripts/implementation_registry.py --check`.

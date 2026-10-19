# R34 — Caracterización local acotada de lecturas HTTP

La captura final caracteriza siete recorridos reales de la fábrica SaaS sobre el candidato `939681e7b647b3eeeb7e68f252b2f5de2810ec52`: **1400 respuestas HTTP 200, 1400 contratos semánticos válidos y 1400 observaciones SQL completas**. No cierra R34: faltan objetivos acordados, demanda de referencia, generación/PDF/objetos y medición de las colas de esos flujos. No se modificó producto, índices, paginación ni tamaño del pool.

La evidencia aceptable para estas cifras es [qa-load-local-final-ack/report.json](evidence/qa-load-local-final-ack/report.json), con [muestras](evidence/qa-load-local-final-ack/samples.json), [observación del servidor](evidence/qa-load-local-final-ack/server-observations.jsonl) y [248 fuentes antes/después](evidence/qa-load-local-final-ack/source.json), todas estables. El origen se limita a los archivos enumerados; no es una afirmación sobre todos los archivos del repositorio.

## Entorno y carga

Windows 10.0.19045, CPython 3.12.13, 12 CPU lógicas, procesador `Intel64 Family 6 Model 158 Stepping 10, GenuineIntel`. Uvicorn 0.54.0, FastAPI 0.146.0, SQLAlchemy 2.1.5, httpx 0.28.1; PostgreSQL 17.11 local con zona de sesión `America/Mexico_City` y revisión `20261019_personal_diary`. Un worker SaaS y configuración existente de pool 20/overflow 10; no se probó la fábrica API independiente ni una imagen Linux.

Se creó, migró a head27 y eliminó únicamente una base UUID propia. El rol de aplicación se verificó mediante el helper existente como restringido, sin propiedad/BYPASSRLS/superusuario. El archivo privado se cargó dentro del proceso; sus valores no se incluyen en los artefactos. Se limpiaron proveedores y configuración heredada mediante `tests.isolation`; sockets externos bloqueados en Python, sin afirmar aislamiento de red del sistema operativo. No hubo proveedores, pagos, correos ni cuentas reales.

Se sembraron cinco espacios personales con historiales de 10/50/200/500/1000 planes (1760 filas), un perfil por sujeto y 30 días de agua por sujeto; cinco propietarios profesionales con 250 clientes cada uno (1250 clientes). Son volúmenes sintéticos de ingeniería, elegidos para observar escalado; no representan una distribución observada ni afirman derechos Free de 250 clientes. El contenido de plan es una estructura nutricional sintética almacenada de 762 bytes; no proviene del generador/PDF. No se sembró ningún objeto PDF.

Cada escenario ejecutó 100 solicitudes, alternando cinco identidades, con C1 o C5 trabajadores cliente síncronos. Son como máximo cinco llamadas HTTP pendientes, sin lote de tareas ilimitado ni tasa empresarial asumida. Se excluyeron 35 solicitudes de calentamiento, una por ruta/identidad; las cachés de Windows/PostgreSQL no se vaciaron. Se detuvo admisión a los 27 s, timeout HTTP 3 s; todos los escenarios reales terminaron por debajo de 30 s. La ronda es cerrada: una respuesta habilita la siguiente solicitud del trabajador, por lo que no caracteriza llegadas abiertas ni capacidad máxima.

## Resultados descriptivos

Percentiles por rango más próximo: p95 es la observación ordenada `ceil(0.95*n)`. Cada celda global usa 100 muestras; cada cohorte, 20. La latencia cliente incluye HTTP/lectura/decodificación y comprobación semántica. La instrumentación añade coste; las cifras no son SLO ni umbrales de aprobación.

| Flujo | C1 p50 ms | C1 p95 ms | C5 p50 ms | C5 p95 ms | SELECT por petición |
| --- | ---: | ---: | ---: | ---: | ---: |
| latest-plan | 9.61 | 11.64 | 43.34 | 101.76 | 7 |
| history | 18.72 | 69.74 | 130.42 | 209.53 | 7 |
| export-25 | 32.71 | 38.05 | 149.13 | 199.40 | 15 |
| diary-30 | 11.46 | 12.82 | 54.72 | 67.80 | 8 |
| clients-25 | 12.36 | 15.02 | 57.37 | 77.63 | 7 |
| clients-100 | 20.15 | 23.32 | 104.62 | 169.59 | 7 |
| client-detail | 8.66 | 9.70 | 37.65 | 49.57 | 6 |

`latest-plan`, `history`, `export-25` y `diary-30` recorren `/api/usuario/mi-plan`, `/api/usuario/historial`, `/api/usuario/privacidad/exportar?limit=25` y el calendario de 30 días. `clients-25` y `clients-100` recorren el listado de clientes con límites 25/100 y offsets 0/100; `client-detail` obtiene un cliente propio. Autenticación, middleware, dependencias, ORM, permisos y FORCE RLS son reales; no hay overrides de autenticación/rutas ni respuestas de negocio simuladas.

Los conteos SQL no crecen con 25→100 clientes ni con 10→1000 planes: en estos recorridos no se observó N+1. Son eventos `before_cursor_execute`: incluyen SELECT de contexto/autenticación, omiten el `pre_ping` del driver y no equivalen a todos los viajes de red. El temporizador SQL mide ejecución del cursor, no toda la hidratación/serialización.

El pool alcanzó 6 conexiones prestadas frente al tamaño 20. El mayor p95 de adquisición fue 0.014 ms. Ese contador de `_do_get` incluye adquisición/creación y excluye pre_ping; no mide la cola de CPU ni demuestra ausencia de espera bajo otra carga. No hay justificación local para aumentar el pool a partir de esta ronda. CPU del servidor por escenario: 0.734–3.516 s; máximo RSS muestreado 155.9 MiB. Es CPU/RSS del PID real, cuya relación con el lanzador Windows se verificó con nonce y parent PID; no incluye CPU/memoria de PostgreSQL ni del cliente.

El máximo de ciclos ASGI todavía abiertos fue 10: la entrega del body puede preceder al cierre de dependencias/finally, y el siguiente HTTP de un cliente puede llegar durante ese cierre. Se conserva esa métrica con el nombre `asgi_lifecycles_open_at_start`; no se presenta como número de llamadas HTTP cliente pendientes ni se oculta. Las comparaciones C1/C5 mezclan scheduling, CPU, serialización y E/S; no prueban por sí mismas un cuello de botella concreto.

## Hallazgo reproducido: historial sin paginación

`web/routes/usuario.py::historial_planes` consulta `.all()` y devuelve todo el historial del perfil. La llamada HTTP real reproduce la ausencia de tope:

| Planes del sujeto | Filas devueltas | Bytes sin compresión | C1 p95 ms, 20 muestras |
| ---: | ---: | ---: | ---: |
| 10 | 10 | 1613 | 12.03 |
| 50 | 50 | 8062 | 13.94 |
| 200 | 200 | 32373 | 21.78 |
| 500 | 500 | 81012 | 43.59 |
| 1000 | 1000 | 162773 | 142.10 |

El tamaño de respuesta crece con el historial aunque el número de SELECT permanezca en 7. Es evidencia de trabajo/bytes sin límite por historial, no de caída o incidente productivo. La exportación sí respetó 25 registros por página y cursor de continuación cuando correspondía, en las mismas identidades. No se aplicó una corrección de producto desde esta tarea de QA.

Propuesta concreta para el siguiente cambio: paginación de historial por orden estable `(fecha_generacion DESC, id DESC)` dentro del sujeto/perfil ya autorizado; parámetro de tamaño validado y acotado, cursor de continuación y UI con acceso a páginas anteriores conservando el PDF por ID. Propuesta técnica revisable: tamaño inicial 50 y máximo 200 para historial; el máximo coincide con el de exportación, cuyo tamaño inicial actual es 100. Estos valores propuestos para historial son límites técnicos, sin significado comercial. Antes de añadir índices, comparar EXPLAIN ANALYZE/BUFFERS con la consulta real a 10/200/1000 filas; no crear un índice sólo por intuición. La regresión debe cubrir empates de fecha, borrado/insert entre páginas, dos sujetos, cancelación por cambio de sesión y acceso a todo el historial sin duplicados en una lectura estable.

## Reproducción y límites pendientes

Desde una copia limpia del candidato con el entorno Windows web/test bloqueado, ejecutar el harness explícitamente (no forma parte de la colección normal de pytest):

```powershell
python -X utf8 tests/performance/characterize_local_http.py `
  --private-env <ruta-local-al-json-de-QA> `
  --output <directorio-nuevo-de-evidencia> --requests 100 --seconds 30
```

El destino se restringe a loopback QA 55483, usuarios/bases de pruebas validados y un nombre UUID creado por la misma ejecución. La salida debe ser nueva; no sobrescribe evidencia anterior. El hijo se identifica por nonce y relación directa con su propio Popen. Antes de cerrarlo se confirma la escritura de todas las observaciones; el `finally` elimina sólo la base propia. Se coordinó la ventana con Backend para que no hubiera ensayos PostgreSQL concurrentes suyos; otros procesos del host pueden introducir ruido.

Para completar R34 falta acordar por flujo volumen retenido esperado, mezcla/tasa de llegada y espera aceptable de usuario; medir generación con reglas/core/PDF reales por tipo/exclusiones, reserva/lock, render, PUT/lectura, commit, resultado ambiguo y recuperación; separar frío/caliente y CPU/RSS/esperas de PostgreSQL. Medir backlog/admisión/colas del ejecutor cuando exista ese contrato (R28), y repetir en la imagen Linux y configuración real de workers con PostgreSQL/Redis sintéticos dedicados. Ajustar paginación/índices/pools según esos hallazgos, y volver a medir con los mismos datos. No se propone broker ni capacidad comercial a partir de estas lecturas.

## Historial de preparación conservado

Los tres ensayos previos permanecen completos y separados; las correcciones fueron del harness y no cambios de criterios del producto:

- `qa-load-local-smoke`: migración/seed/limpieza correctos, readiness no alcanzó 200; se había importado el firmante lazy sin llamar `init_auth`. No se capturó el código HTTP del último intento. No hay métricas de carga válidas.
- `qa-load-local-final`: 1400 HTTP 200 y contratos válidos, pero CPU/RSS pertenecían al lanzador venv.exe (CPU 0/RSS ≈ 4.5 MiB). Esos dos contadores son inválidos. La marca de cierre de ese ensayo sólo observaba el Popen lanzador; la identificación directa del servidor se añadió después.
- `qa-load-local-verified`: CPU/RSS del PID real y 1400 HTTP 200/contratos válidos; faltó la última observación SQL porque el proceso se cerró después del body antes del `finally`. Conserva `requires_review` y exit 1. Se añadió confirmación de escritura de 1400 filas antes del cierre; no se relajó el conteo.

La captura `qa-load-local-final-ack` pasó las mismas condiciones, con 1400 observaciones, salida 0 y fuentes estables. Los contadores previos llamados `http_inflight_at_start` se referían a ciclos ASGI completos; el nombre final aclara su alcance. Los archivos originales no se reescriben. [Índice de huellas y revisiones](evidence/qa-load-local-manifest.json).

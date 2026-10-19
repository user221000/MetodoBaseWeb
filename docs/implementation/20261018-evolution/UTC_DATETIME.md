# Contrato UTC para columnas históricas sin timezone

El [probe PostgreSQL](evidence/security-privacy-timestamp-observation.md) reprodujo −21 600 segundos en `Subscription.current_period_end` y `PlanGenerado.fecha_generacion` al insertar un `datetime` UTC aware en una columna sin timezone mediante una conexión en America/Mexico_City. No se atribuye ese resultado al estado productivo ni se reescriben datos existentes.

[utc_datetime.py](../../../web/database/utc_datetime.py) añade `UTCDateTime`, un `TypeDecorator` con tipo físico `DateTime(timezone=False)`, y el helper `as_utc_naive`. Su contrato es:

| Entrada / operación | Resultado |
| --- | --- |
| `datetime` aware | Convierte el instante a UTC y retira `tzinfo` antes del bind |
| `datetime` naive | Conserva el valor; no usa la zona del sistema o de la conexión |
| `None` | Conserva `None` |
| Fecha, texto, número u otro tipo | Rechaza con error de tipo estable, sin incorporar el valor al mensaje |
| Resultado leído de la base | Devuelve el valor del driver sin desplazarlo ni atribuirle una zona histórica |

El procesamiento cubre valores enlazados mediante una columna declarada con `UTCDateTime`, incluido `insert`, `update`, filtros y sesiones/conexiones directas. SQL textual sin tipo explícito, literales SQL y escrituras desde otro servicio quedan fuera. Esos callers deben usar `as_utc_naive` para el parámetro o declarar `bindparam(..., type_=UTCDateTime())`; ambos caminos están ensayados. Configurar la zona global de conexión no es la garantía de este contrato.

El helper inicial quedó integrado en `9a53215` sin cambiar los modelos. La adopción posterior declara `UTCDateTime` explícitamente en 52 columnas de instantes de [models.py](../../../web/database/models.py): registro/borrado de usuarios y clientes; vencimiento de invitaciones; generación y borrado de planes; períodos, vencimientos y auditoría de suscripciones/facturas/pagos; callbacks; perfiles/configuración; progreso; auditoría; licencias; checkout; intenciones y reservas de generación; asociaciones de proveedor. No existe un alias global ni un monkeypatch de todos los `DateTime` de SQLAlchemy.

Las dos fechas civiles `Cliente.fecha_suscripcion` y `Cliente.fecha_fin_suscripcion` conservan `DateTime`: los formularios actuales las envían sin offset desde selectores de fecha, por lo que no existe autoridad para reinterpretarlas como instantes. También se conservan `Date` para `GymGenerationReservation.local_date`, las épocas `Float` de refresh tokens, los períodos `YYYY-MM` y los horarios JSON. `ClientProgress.fecha` conserva sus defaults; actualmente no hay una ruta de escritura de aplicación para esa columna.

Esta adopción no añade migraciones ni modifica datos históricos o configuración de producción. La compilación de DDL y los atributos físicos inspeccionados son iguales a `DateTime(timezone=False)` para PostgreSQL y SQLite. El head aceptado de 24 tablas y sus contratos estructurales/RLS se conservan; ninguna firma congelada se regenera para aceptar el nuevo mapeo. La búsqueda de escritores SQL textuales en `web/` y `api/` no encontró escrituras de timestamps fuera de columnas ORM tipadas; los literales de migraciones históricas y la preparación sintética permanecen intactos. El script legado `scripts/cleanup_expired_tokens.py` queda fuera: sus comparaciones textuales requieren revisión separada de unidades y tabla de auditoría antes de habilitar el job.

La suite [unitaria](../../../tests/test_utc_datetime.py) ensaya offsets positivos/negativos, microsegundos, valores naive y nulos, tipos rechazados, atributos del esquema y preservación literal de resultados. La suite [de integración](../../../tests/integration_utc_datetime.py) crea tablas con `MetaData` propio en SQLite y bases PostgreSQL UUID temporales, usa conexiones UTC y America/Mexico_City y compara datos y firma estructural antes/después del mapeo. La fila histórica de control permanece idéntica y no se ejecuta DDL ni `UPDATE` sobre ella al adoptar el tipo. El fixture destruye únicamente las bases que acaba de crear.

La regresión con [modelos y sesiones reales](../../../tests/integration_model_utc_postgres.py) migra una base PostgreSQL UUID al head aceptado y usa el rol de aplicación restringido con RLS. Antes de adoptar el tipo, sus cuatro casos de México fallaron: los tres offsets de entrada persistieron seis horas menos y una invitación real con 30 minutos de vigencia fue rechazada con HTTP 410 ([before](evidence/backend-utc-models-before.log)). Después exige instantes UTC sin desplazamiento en ambas zonas, filtros tipados y `UPDATE`/`onupdate`, además del canje real de la invitación. Sus lecturas SQL sin tipo impiden que un procesador de resultados disimule un valor almacenado incorrecto; sus controles comparan filas históricas, firma estructural y políticas antes/después.

Los cuatro diagnósticos PostgreSQL originales permanecen en el historial de `b81cfc1` y en la evidencia del probe inicial. [integration_timestamp_observation.py](../../../tests/integration_timestamp_observation.py) pasa a exigir cero segundos de desplazamiento para los modelos adoptados, tanto con entrada aware como naive. Estas pruebas locales no inspeccionan producción ni reparan filas que pudieran haberse desplazado antes.

El gate dirigido posterior a la adopción reúne 42 casos verdes del helper, integración propia, modelos reales y diagnóstico convertido en regresión ([log](evidence/backend-utc-models-after.log)). El baseline nuevo tuvo cuatro fallos reales, sin errores de preparación; no se presenta el probe inicial como aceptación de la aplicación.

La elección de UTC naive es compatibilidad con el esquema actual. Una futura migración a columnas con timezone necesita un plan separado y evidencia sobre el origen de cada dato; este helper no puede reparar una fila previamente desplazada ni determinar cómo se produjo.

La migración posterior74d66e8 añade dos instantes nuevos de StoredObject con UTCDateTime. Son columnas nuevas del esquema25; no forman parte de las52 columnas históricas adoptadas sin DDL ni alteran la evidencia previa. Las dos fechas civiles se conservan.

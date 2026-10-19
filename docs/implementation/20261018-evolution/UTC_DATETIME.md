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

La adopción se hace declarando explícitamente el tipo en los modelos correspondientes, después de revisión del backend. Este cambio inicial no edita `models.py`, migraciones, valores históricos ni configuración de producción. No existe un monkeypatch de todos los `DateTime` de SQLAlchemy. La compilación de DDL y los atributos físicos inspeccionados son iguales a `DateTime(timezone=False)` para PostgreSQL y SQLite; conservar el esquema evita reinterpretar filas que carecen de zona de origen verificable.

La suite [unitaria](../../../tests/test_utc_datetime.py) ensaya offsets positivos/negativos, microsegundos, valores naive y nulos, tipos rechazados, atributos del esquema y preservación literal de resultados. La suite [de integración](../../../tests/integration_utc_datetime.py) crea tablas con `MetaData` propio en SQLite y bases PostgreSQL UUID temporales, usa conexiones UTC y America/Mexico_City y compara datos y firma estructural antes/después del mapeo. La fila histórica de control permanece idéntica y no se ejecuta DDL ni `UPDATE` sobre ella al adoptar el tipo. El fixture destruye únicamente las bases que acaba de crear.

La elección de UTC naive es compatibilidad con el esquema actual. Una futura migración a columnas con timezone necesita un plan separado y evidencia sobre el origen de cada dato; este helper no puede reparar una fila previamente desplazada ni determinar cómo se produjo.

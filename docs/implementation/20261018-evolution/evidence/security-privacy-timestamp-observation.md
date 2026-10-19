# Observación temporal para seguimiento R01/R03/R14

Se reprodujo en PostgreSQL 17.11 local un desplazamiento de seis horas al persistir un `datetime` UTC con timezone en columnas históricas `TIMESTAMP WITHOUT TIME ZONE`, si la conexión tiene `TimeZone=America/Mexico_City`. Se usaron cuatro bases UUID nuevas creadas y destruidas por `migration_database`, migradas explícitamente al contrato R03 `20261018_schema_reconciliation`. No se cambió código de aplicación ni se leyeron o modificaron datos existentes.

Entrada fija: `2026-10-19T12:30:00+00:00`. Se ensayaron simultáneamente `Subscription.current_period_end` y `PlanGenerado.fecha_generacion` mediante ORM real del candidato. Ambas columnas tienen `timezone=False` en el catálogo real.

| Bind | TimeZone de conexión | Valor guardado en ambas columnas | Diferencia respecto al UTC sin timezone |
| --- | --- | --- | --- |
| Aware UTC | UTC | `2026-10-19 12:30:00` | 0 s |
| Aware UTC | America/Mexico_City | `2026-10-19 06:30:00` | −21 600 s |
| UTC convertido explícitamente a naive | UTC | `2026-10-19 12:30:00` | 0 s |
| UTC convertido explícitamente a naive | America/Mexico_City | `2026-10-19 12:30:00` | 0 s |

[Test reproducible](../../../../tests/integration_timestamp_observation.py), [log](security-privacy-timestamp-observation.log), [JUnit con propiedades por caso](security-privacy-timestamp-observation.xml), [huella estable de la fuente](security-privacy-timestamp-source.json). Las cuatro pruebas aprobadas **confirman el comportamiento observado**, no certifican que la app gestione bien estas fechas. Los cuatro casos SQLite fueron deseleccionados deliberadamente: este informe describe el driver y motor PostgreSQL reales. Las advertencias de `record_property`/JUnit2 no impidieron conservar las propiedades en el XML.

Implicación técnica: tratar luego un valor ingenuo como UTC puede adelantar el vencimiento o ubicar una generación en otro tramo del día. La sensibilidad depende de qué zona use la conexión y de si el campo recibe valores aware o naive. No se consultó la configuración horaria productiva, así que no se afirma que las filas publicadas estén desplazadas.

Seguimiento propuesto: definir un único contrato para nuevas escrituras/comparaciones (UTC naive normalizado para el esquema actual, o columnas timezone-aware tras migración explícita revisada) y probar al menos dos zonas de conexión en cobros, cuotas y diario. La corrección no debe reinterpretar o desplazar en bloque datos históricos: su zona original no puede deducirse de una columna sin timezone. El mismo ajuste ya se hizo por root en el límite de activación de licencia; este reporte no lo extiende a otras fuentes ni lo atribuye a producción.

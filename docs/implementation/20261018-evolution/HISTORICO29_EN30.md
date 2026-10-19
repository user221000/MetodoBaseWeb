# Comprobar el histórico29 después de avanzar el modelo a30

Los tests de migración de vínculos crean explícitamente una base29. Tras avanzar el modelo a30, sus tres comprobaciones posteriores deben pedir29 de forma explícita. Sólo se añaden esos tres argumentos; la inversión del AST recupera exactamente las pruebas anteriores, incluida la comprobación por defecto que exige rechazar28. No cambia ninguna aserción ni contrato histórico.

Antes: los mismos cinco casosSQLite daban tres fallos de revisión y dos verdes. Después: los diez casos originales deSQLite/PostgreSQL pasan sin omisiones. Un plugin de observación verifica que las cinco basesPostgreSQL creadas por sus fixtures se eliminan y consulta la ausencia de cada nombre exacto. El esquema30 y su índice tienen pruebas separadas; este ajuste no permite que29 pase como runtime30.

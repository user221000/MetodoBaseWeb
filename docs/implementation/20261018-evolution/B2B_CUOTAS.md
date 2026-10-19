# Reserva y publicación de planes profesionales

Estado: integración local revisada; sin despliegue. La migración `20261018_gym_generation_quota` sucede a R04 y añade la tabla24, `gym_generation_reservations`, con su propia política RLS. Los contratos históricos de22/23 tablas se conservan. Evidencia y resultado final se enlazan desde [VALIDACION.md](VALIDACION.md).

## Contrato comercial y calendario

Free permite10 clientes activos, un plan por cliente al día, diez planes totales por gimnasio al día y20 al mes. Los tres primeros valores proceden de decisiones explícitas del usuario;20 mensuales ya existían en el catálogo. Standard conserva100 al mes; cero en Gym/Clínica significa sin tope mensual. Las demás dimensiones proceden del [catálogo canónico](CATALOGO.md), sin nuevos periodos de gracia ni límites por dispositivo/equipo.

Los periodos diarios y mensuales se calculan con `America/Mexico_City`. Cada medianoche se convierte por separado a UTC para respetar cambios de offset; los límites se comparan como UTC sin zona por compatibilidad con el esquema. Las columnas `local_date`, `period` y `timezone` conservan el periodo reservado aunque el trabajo termine después de medianoche. Las pruebas de cambios DST en otras zonas validan el cálculo, sin habilitar por ello una preferencia de zona nueva en producto.

La capacidad de clientes se comprueba en el repositorio dentro de la misma transacción que el INSERT. La generación exige cliente activo al reservar y al iniciar el worker. Una desactivación impide nuevas solicitudes; un trabajo ya autorizado puede terminar. Consultar historial o repetir una respuesta ya completada no exige reactivar al cliente. Borrado lógico y desaparición del resultado se distinguen: un replay cuyo plan/cliente fue eliminado devuelve410.

## Transacción e idempotencia

`POST /api/generar-plan` en ambos consumidores acepta `Idempotency-Key` de1 a128 caracteres. Sin header se crea una clave nueva: el consumidor debe conservar la misma clave para reintentar la misma operación. La huella SHA256 usa el DTO completo serializado con claves ordenadas y valores finitos; la misma clave con otro contenido devuelve409.

1. Se bloquea la fila de la cuenta antes de leer suscripción/cupos. El orden cuenta→suscripción evita cruzarse con cambios comerciales y otros consumidores que usan ese orden.
2. Se revisan reservas y planes históricos del periodo sin contar dos veces un plan ya vinculado. La reserva se confirma antes de CPU/PDF.
3. El worker vuelve a comprobar pertenencia/estado del cliente y construye con catálogo inmutable. Los PDFs nuevos tienen nombres UUID opacos; dos solicitudes con nombres iguales no comparten archivo.
4. Plan, JSON, contador y vínculo `plan_id`/`persisted_at` de la reserva se confirman en una sola transacción. La actualización condicional exige reserva pendiente del mismo gimnasio y cliente.
5. La respuesta completa queda guardada en `result_json`. Un replay completado devuelve esa respuesta; una solicitud pendiente, fallida o con publicación aún sin respuesta devuelve409 y dirige al historial.

| Punto de fallo | Consumo y recuperación |
| --- | --- |
| Validación o cupo antes de reserva | Sin trabajo ni consumo nuevo |
| CPU/PDF antes de confirmar plan | La compensación libera una vez; misma clave no se ejecuta de nuevo |
| Rollback o compensación no confirmados | HTTP503 `generation_reconciliation_required`; conserva reserva y dirige al historial; logs sólo de clase |
| Plan confirmado y respuesta perdida | Conserva consumo; nunca compensa por ese fallo |
| Referencia del plan borrada después de confirmar | `persisted_at` conserva la prueba de publicación; SET NULL no devuelve crédito |
| Worker perdido con reserva pendiente | Reserva sigue consumiendo; no hay un TTL que libere a ciegas una operación ambigua |
| Respuesta completada repetida | Mismo resultado, sin generación ni notificación nueva |

El lock en memoria sólo reduce trabajo repetido dentro de un proceso. La garantía de cupo y publicación depende de la transacción PostgreSQL y las condiciones persistidas, ensayadas con varios procesos. El estado reservado tras perder un worker necesita reconciliación operativa/R28; no se presenta como cola durable ya implementada.

QA independiente ejecutó18 casos PostgreSQL (8 HTTP multiproceso,7 de recuperación y3 RLS/zona),41 de worker/nutrición con5 PDFs reales,6 de migraciones y un restore poblado24. Seguridad encontró dos exposiciones de parámetros al fallar compensación; el seguimiento terminó con25 controles independientes de compensación/logs/rollback/PDF/caducidad verdes. El estado combinado dio1621 aprobadas en serie y con dos workers/orden mezclado; única omisión por permiso de symlink Windows. Los manifiestos fijan las fuentes ensayadas y no representan operación productiva.

## Compatibilidad y siguientes verificaciones

La migración comprueba la firma estructural y de seguridad R04 antes del DDL. PostgreSQL conserva ENABLE/FORCE; SQLite tiene contrato propio y `foreign_key_check`. No existe downgrade automático que borre el ledger: rollback requiere decidir compatibilidad de aplicación y restaurar un backup verificado.

La UI todavía debe conservar una clave por operación y ofrecer consulta/reintento del resultado ambiguo. El almacenamiento del PDF continúa en la ruta legacy hasta integrar R07; el nombre UUID evita colisión, pero no acredita durabilidad del contenedor. No se infiere consumo histórico borrado físicamente: el workflow de borrado R31 deberá conservar consumo verificable según su política, antes de habilitar eliminación física.

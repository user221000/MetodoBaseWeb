R23: seguimiento operativo en el dashboard existente

Base aislada: `fb19c0d441bfafa9ed758d2cf7dbb78c629e58b7`, rama `implementation/r23-dashboard-20261019`. El emisor síncrono de revisión de sesión está aislado en el commit previo `e8ca8be`; el resto de este lote es el consumidor R23. No se modifica MAIN, R12, modelos, cuotas ni migraciones. No se declara R23 cerrado.

El criterio ROADMAP R23 exige lista priorizada por causa, próximo paso y responsable, distinguir cobro real de fecha de membresía y acciones medibles. UX17 pide medir hechos reales y llamar cada acción por lo que hace. La trazabilidad previa sólo aceptaba contención de errores de estadísticas, no la funcionalidad R23.

Inventario anterior y reproducción

- `/dashboard` monta `web/templates/dashboard.html`, `main.js` y estadísticas. El dashboard anterior mostraba «Sin plan activo» a partir de `Cliente.fecha_fin_suscripcion` nula/pasada y sugería generar hoy por ausencia de actividad. Esas fechas no prueban un cobro ni la vigencia clínica de un plan. La tarjeta «Clientes nuevos» contaba inicios de membresía, no fecha de registro. Se corrigen esas etiquetas, sin cambiar sus endpoints ni activar membresías.
- `repository.obtener_estadisticas` ya define clientes activos como clientes con plan en los últimos 30 días (líneas 319–329 de la base); `listar_clientes` documenta el mismo periodo. `PERIODO_MES_DIAS=30` es sólo la constante reutilizada. Esto respalda una ventana de actividad, nunca la caducidad de un plan nutricional, riesgo, fidelidad ni necesidad automática de otro plan.
- No hay campo de responsable por cliente. `AuditLog` existe, pero no hay escritores de acciones de negocio ni actor que permita atribuir trabajo histórico. No se inventan eventos ni asignaciones.
- Cuatro pruebas HTTP de contrato iniciales, ambas factories, fallan 404. Las assertions iniciales permanecen en el driver final; se añaden casos posteriores sin relajarlas. El ZIP previo conserva blobs Git de la base, no se presenta como foto RAW tomada antes. Logs iniciales `r23-before.*` quedan intactos.

Ruta y autorización

`GET /api/estadisticas/seguimiento?limit=50`, límite 1..100. El mismo router se monta una vez en `web.main_web` y `api.app`. Sólo lectura: identidad persistida canónica, permisos existentes `read:stats` y `read:cliente`, gym efectivo de pertenencia persistida. OWNER profesional y ADMIN de equipo pueden leer; nutriólogo/viewer no obtienen una capacidad nueva. OWNER histórico con tipo usuario sin equipo recibe 403 y no adopta cartera profesional. Desvinculación/sv invalida el token anterior. No hay selector de gym/cliente aportado por el usuario.

Capas: `routes/followup.py` traduce HTTP/RBAC; `services/followup_service.py` fija una sola hora y coordina; `database/followup_repository.py` proyecta y limita SQL; `services/followup_policy.py` clasifica datos sin SQLAlchemy/FastAPI. `get_db_readonly` no hace commit. No hay DML, defaults, proveedores, correos, cargos, PDF ni generación en GET.

Fuentes y DTO

`as_of` UTC, `window_start`, `window_days`, `limit`, `has_more`; `items` mínimos con `id_cliente`, `nombre`, `causes`, prioridad operativa 1..4, `last_plan_at`, `elapsed_days`, `membership_end`, `responsible:null`, `next_step`. `capabilities` procede del RBAC del servidor. No se transmiten email, teléfono, notas, medidas, plan JSON, ruta física, object keys, bearer o request keys.

Plan/Cliente se unen por id_cliente y gym_id, se filtran ambos owners y soft-delete. La lista usa sólo clientes activos, igual que el dashboard; no muestra historia de clientes desactivados. El subquery agregado de planes ignora borrados y cruzados. Dos SELECT de negocio: lista limitada a limit+1 y métricas agregadas; no N+1 ni materialización de planes completos. `has_more` comunica truncamiento; el selector permite 50/100 y cada consulta es explícita. No hay carga automática de toda la cartera ni cursor que prometa una foto histórica estable.

Prioridad declarada de revisión (no urgencia médica):

1. `no_saved_plan`: ninguna fila de plan autorizada; revisar ficha/historial.
2. `no_plan_in_window`: última fecha anterior al comienzo de la ventana ya existente; mostrar fecha y días, revisar historial antes de decidir si preparar otro plan.
3. `plan_date_missing`: existen filas pero todas carecen de fecha; no reinterpretar NULL como ausencia de plan ni fecha actual.
4. `membership_date_passed`: fecha de fin administrativa anterior a la consulta; revisar esa fecha, sin afirmar impago ni ofrecer cobrar/activar.

Un cliente puede tener varias causas, se muestra una vez. Desempate estable por fecha de último plan ascendente (NULL primero) y id_cliente ascendente. Una fecha de plan exactamente en el límite sí pertenece a la ventana. Fechas de membresía naive conservan la comparación UTC administrativa anterior; se muestran como registradas y no se transforman en evidencia de facturación. No se añaden umbrales comerciales ni gracia.

Hechos medibles y límites

`metrics` sólo cubre planes autorizados y clientes activos/no borrados en la ventana:

- `plans_saved`: filas de PlanGenerado guardadas. No equivale a generación terminada, PDF, asignación o entrega.
- `generation_operations_completed`: además existe ledger GymGenerationReservation propio con status completed y persisted_at. No se infiere un ACK del destinatario ni entrega.
- `pdf_metadata_ready`: descriptor StoredObject propio de kind plan_pdf, MIME PDF y status ready asociado al plan. No se leen/verifican bytes en esta consulta; descargar mantiene su verificación autorizada existente.

No se atribuyen esos totales al dashboard. La prueba de acción verificable cambia una fecha mediante el PUT real existente, recarga y constata que desaparece la causa administrativa, sin inventar pago. «Abrir clientes» sólo navega; «Revisar cliente y preparar plan» abre el wizard por id sin generar automáticamente. No se marca contacto hecho, plan recibido ni checklist completado por clic. No hay analytics/PII en logs ni DTO/cursos/eventos en localStorage.

Pendiente para cumplir R23 completo: asignación persistida con responsable real y contrato de eventos/resultados atribuibles (actor, propósito, idempotencia, estado, autorización y retención). Se propone al coordinador como aditivo posterior a esquema 30; no se crea migración 31 ni se recicla AuditLog sin ese contrato. Cobros de clientes no están disponibles. Tampoco se sustituye por facturas de la suscripción SaaS del gimnasio.

Estados y sesión

Consulta inicial, vacío confirmado, lista limitada, error y reintento son distintos. Un error recuperable conserva filas y hora previas, avisando que no se actualizaron; no muestra cero como éxito. Un cambio de sesión descarta inmediatamente lista/contadores/estado y deshabilita controles hasta reabrir. El consumidor usa contexto de revisión + id/role/team/session_version antes/después de cada await, antes de DTO/DOM y antes de navegar; también escucha storage, evento central y pagehide/pageshow restaurada. El emisor no convierte dos claves legacy en almacenamiento atómico entre pestañas o reload. No se toca el perfil/diario/planes personales.

503 de consulta es genérico `followup_unavailable`, sin texto SQL ni datos, con no-store/no-referrer. El handler HTTPException web anterior descarta headers; esta ruta devuelve su 503 directamente sin cambiar handlers globales. El framework conserva su 401/403/422/405; no se promete no-referrer global para esos errores ni se altera CSP.

Verificación de autor

53 HTTP dirigidas (38 nuevas y 15 estadísticas anteriores), 20 VM del nuevo consumidor/helper, 2 PostgreSQL con UUID propio migrado head28, rol restringido y FORCE RLS; cero DML en lecturas observadas y pool público sin cartera. Esas cifras no se suman a los 74 de transporte ni a los 11 del emisor como funcionalidad R23 adicional. El emisor e8 todavía tiene un bloqueo independiente de expiración/reentrada: no se presenta este browser como aceptación de ese flujo; su corrección y revisión van aparte.

Chrome de autor: ocho grupos, cinco capturas, viewport 320/390/1440, teclado, axe AA del bloque nuevo sin hallazgos, sin desborde ni pageerrors. Autenticación por contraseña, API, tenant y corrección de fecha son reales sobre UUID PostgreSQL nuevo y migrado a `20261019_account_recovery` (head28 de esta rama). El 503 y la retención temporal de una respuesta real son dobles de transporte explícitos. La respuesta retenida no publica filas tras sustituir cuenta; saveTokens descarta filas/contadores visibles inmediatamente. Los 26 hashes startup/start/end de la corrida `run-fresh-final` coinciden. La fixture cerró normalmente y eliminó sólo su UUID; puerto 8795 libre, Chrome de autor cerrado.

Se preservan intentos anteriores sin contarlos como aprobación final: colisión CSS `{#`/comentario Jinja (500), pool=1 de la primera fixture de integración que no soportaba concurrencia del navegador, inyección inline de axe bloqueada correctamente por CSP (harness ahora usa DevTools, sin debilitar CSP), desborde de hero legado a 320 corregido con CSS local y un replay indebido sobre fixture ya modificada por el PUT (3 vs 4 filas). El gate final usa fixture fresca, fuentes quietas y directorio de salida nuevo. Los cuerpos anteriores relevantes quedan preservados; no se sobrescriben pruebas históricas.

No se afirma Actions/Linux, escritorio, producción ni validación de usuarios reales. QA/seguridad posteriores siguen pendientes.

Excepción acotada de diff --check: `r23-directed-after.xml` conserva un espacio que pytest emitió en el diff del fallo histórico de headers. Los proofs anteriores se conservan byte por byte; no se recortan para cambiar el resultado de una comprobación de whitespace. Producto y tests nuevos pasan su comprobación.

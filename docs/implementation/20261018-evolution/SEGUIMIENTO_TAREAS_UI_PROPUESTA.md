# R23: tareas de seguimiento, propuesta UI para wire34

Estado: propuesta revisable, no contrato backend firmado ni API34 implementada.
Base de autoría UI: `a02a9ac04e0c619f6754bc86d89680d1a6bf95a0`, worktree
`F:/mb-followup-actions-ui-20261019`. La UI Google33 queda intacta. No se han
iniciado Chrome, servicios ni PostgreSQL y no se copian dependencias.

## Criterio y hechos actuales

Criterio exacto R23, roadmap2026-10-18:
«Extender dashboard existente: lista priorizada por causa, próximo paso y
responsable; distinguir cobro real de fecha de membresía; acciones medibles».
UX-12 exige distinguir fallo de vacío; UX-17 exige llamar a la acción por lo que
hace y medir hechos reales, sin atribuir entrega a guardar/exportar un plan.

`GET /api/estadisticas/seguimiento` actual exige `read:stats` y `read:cliente` y
contexto profesional persistido. Sólo usa Session readonly. Clasifica causas
operativas existentes: `no_saved_plan`, `no_plan_in_window`,
`plan_date_missing`, `membership_date_passed`; orden1/2/3/4 respectivamente.
La ventana usa PERIODO_MES_DIAS existente como estadística de actividad, no
caducidad nutricional. El DTO devuelve limit y has_more, sin cursor para avanzar;
responsible es siempre null y responsibility es not_recorded.

Los conteos son planes guardados, reservas de generación completed con persisted_at
y metadatos de objeto PDF ready. Ninguno prueba asignación, contacto, entrega,
trabajo humano, renovación o cobro. `Cliente.fecha_fin_suscripcion` es una fecha
administrativa y nunca es evidencia de impago. No hay tareas durables ni eventos
atribuibles de seguimiento en el modelo actual. AuditLog no contiene actor propio
ni contrato CAS de tarea y no debe convertirse en sustituto improvisado.

## Recorrido propuesto

El panel de candidatos del dashboard conserva los hechos y su prioridad. Añade
«Preparar tarea» sólo cuando una capability del servidor lo permita; no hay POST
por cargar, filtrar, abrir ficha o generar un plan. Una tarea requiere elegir
causa mostrada, próximo paso de una lista cerrada y responsable o «Sin asignar».
Antes de guardar se presenta un resumen de la intención; el servidor vuelve a
validar cliente y causa. No se permite texto libre sanitario ni mensaje al socio.

Una vista `/seguimiento` permite consultar tareas propias/asignadas sin cargar
estadísticas globales. OWNER/ADMIN puede gestionar el ámbito del gimnasio;
NUTRIOLOGO sólo ve las tareas asignadas y puede marcarlas completadas si existe
un permiso dedicado. VIEWER, personal, OWNER ambiguo y roles desconocidos no
adquieren autoridad. La UI se basa en capabilities y restricciones de cada tarea;
las etiquetas de rol o el tipo cacheado no conceden acceso.

Cada tarjeta muestra cliente permitido, causa/fuente/fecha de observación,
prioridad operativa, próximo paso, estado, responsable actual y última edición.
Un responsable retirado se muestra como «Ya no disponible» sólo si el servidor
devuelve ese estado, sin buscar contactos ni reasignar por su cuenta. OWNER/ADMIN
puede reasignar mediante otra confirmación. Las tareas terminales conservan su
historia y no se reabren implícitamente por persistir la causa.

«Marcar revisión completada» registra una declaración explícita de la persona que
actúa. El resumen aclara: «No envía mensajes ni confirma entrega, cobro o renovación».
Cancelar requiere confirmación y motivo cerrado, sin borrar la historia. Abrir una
ficha sólo navega; no completa ni cuenta una tarea. No hay CTA de pago.

## Wire propuesto, sujeto a firma backend/ROOT

Namespace separado de `/estadisticas`: evita añadir read:stats a Nutri. Nombres
y DTO siguientes son propuesta, todavía no consumidor ni aceptación HTTP34.

| Ruta propuesta | Finalidad y mínimo necesario |
| --- | --- |
| GET `/api/seguimiento/contexto` | as_of, capacidades del actor y scope `gym` o `assigned`; enums/catálogo de pasos permitidos; sin estadísticas globales para assigned |
| GET `/api/seguimiento/responsables?limit=20&after=...` | Sólo gestores; proyección activa del mismo gym `{id,display_name,role}`, next_after; sin email/contacto |
| GET `/api/seguimiento/tareas?status=open&limit=50&after=...` | items, next_after, as_of, scope; filtros cerrados y limit bounded; asignadas del actor en SQL cuando corresponda |
| GET `/api/seguimiento/tareas/{id}` | Estado fresco autorizado, versión y capabilities por tarea, para consulta explícita tras conflicto/incertidumbre |
| POST `/api/seguimiento/tareas` | Cliente/causa/paso/responsable observado, confirmación explícita; actor/gym/fechas y snapshots mínimos los determina servidor |
| PATCH `/api/seguimiento/tareas/{id}` | expected_version + cambio cerrado de paso/responsable; no body merge arbitrario ni estado terminal genérico |
| POST `/api/seguimiento/tareas/{id}/completar` | expected_version + resultado enum compatible con paso + confirm:true; actor y timestamp servidor |
| POST `/api/seguimiento/tareas/{id}/cancelar` | expected_version + motivo enum + confirm:true; sólo gestor, sin borrado |
| GET `/api/seguimiento/tareas/{id}/historial?limit=20&after=...` | Eventos propios del ámbito autorizado, cursor, acción/fecha y actor mínimo permitido; sin cuerpo sanitario libre |
| GET `/api/seguimiento/metricas` | Periodo/scope/fuente/contadores calculados de tareas y eventos durables autorizados; sin inferencia de éxito comercial |

Proyección de tarea propuesta:

```text
id, version, client{id,display_name}, cause, priority,
source{observed_at,last_plan_at?,membership_end?}, next_step,
responsible:null|{id,display_name,eligible}, status:open|completed|cancelled,
created_at, updated_at, completed_at?, capabilities{edit,complete,cancel,history}
```

No incluir notas, diagnósticos, pagos supuestos, email o perfil personal. Los campos
de fuente y prioridad son descriptivos de esa consulta; no conceden autoridad ni
son prueba de una fuente todavía activa. La autorización siempre revalida el doble
dueño, softdelete, identidad/SV/padre/rol/pertenencia activos y permisos persistidos.

Pasos sugeridos, sin nuevos umbrales:

| Enum propuesto | Mensaje |
| --- | --- |
| review_client_record | Revisar ficha del cliente |
| review_plan_history | Revisar historial de planes |
| review_membership_date | Revisar fecha administrativa de membresía |

Completado sugerido: `review_recorded` declara revisión por quien pulsa; no prueba
resultado médico ni comunicación. Cancelación sugerida: `created_in_error`,
`no_longer_applicable`, `duplicate`. Backend/ROOT deciden conjuntos exactos y reglas
por paso/causa; no se escribirá un consumer dependiente antes de fijarlos.

## Concurrencia, errores y mensajes

Responsable se elige de una página reciente del servidor; no se preselecciona por
nombre, correo, rol heurístico ni primera opción. Cambiar asignación no cambia
pertenencia ni permisos. CAS usa id+version observados, con capacidades revalidadas
bajo lock; la UI captura esa intención en RAM y bloquea doble clic antes de awaits.

409: «La tarea cambió. Tu cambio no se aplicó. Consulta su estado antes de decidir»
sólo si el código confirma rollback. 503/timeout/ACK no verificable: «No pudimos
confirmar el resultado. El cambio puede haberse guardado. No lo repetiremos. Consulta
el estado explícitamente». Nunca afirmar rollback por sólo status. No auto retry,
readback o nueva intención mutante tras resultado incierto. La lectura manual no
afirma quién realizó un cambio si no lo acredita un evento del servidor.

Errores propuestos: version_conflict, assignee_unavailable, task_unavailable,
invalid_input, forbidden, unconfirmed/unavailable. Deben fijarse códigos y status
exactos en wire34. Se distingue vacío confirmado, error de lectura, sesión cambiada,
no permitido, guardando y guardado por ACK tipado. Un error refrescando conserva
filas anteriores con fecha y aviso, pero no habilita acciones sobre permisos caducos.

Cada solicitud/render/control valida contexto persistido antes/después de cada await.
Una revisión/sujeto/rol/equipo/SV distintos, Storage no confiable, logout, pagehide o
evento síncrono limpia filas, métricas, borrador, selección y handles. No usar Storage,
URLs o analítica para clientes, responsables, cursores ni claves de operación.
El helper Api.followup será cerrado a rutas/métodos y cuerpos del wire firmado;
las mutaciones usarán el transporte cercado sin refresh/replay automático.

## Métricas y accesibilidad

Separar «Tareas abiertas / sin asignar» (estado actual) de «Tareas creadas / revisiones
marcadas completadas / cancelaciones / reasignaciones guardadas» (eventos del periodo).
Cada contador necesita rango, scope y fuente servidor. Cero sólo tras lectura válida;
un error nunca es cero. No porcentajes de retención, comparaciones causales, contadores
por clic, píxeles, envíos ni eventos con PII/salud. Las cifras propias de Nutri, si se
autorizan, se limitan a sus tareas; no se filtran totales globales mediante metadatos.

Tarjetas legibles en320/390/768/1440; etiquetas y listas cerradas, sin tablas comprimidas.
Confirmaciones en formulario accesible, foco inicial/título/cancelar y regreso al control
que abrió; región status para guardado y alert para error/conflicto. No mover foco de quien
ya navegó mientras esperaba. Labels no sustituidos por placeholders, targets44px, fuente
normal y contraste comprobable. Error no borra la intención salvo contexto inválido.

## Decisiones que ROOT/backend deben fijar antes de consumidor

1. Rutas/DTO/enums/codes/capabilities exactos y permisos dedicados; acceso SSR/enlaces
   de `/seguimiento` desde dashboard y espacio profesional, sin ampliar stats.
2. Creación y unicidad: una tarea abierta por cliente+causa, cómo resolver ACK perdido
   antes de volver a crear y si se usa una clave idempotente durable. No inventar esa
   garantía sólo en el cliente. Reaparición/reapertura debe ser intención nueva explícita.
3. Orden estable/cursor de tareas y eventos; límite por defecto/máximo; qué sucede con
   inserciones, softdelete, tarea terminal, fuente/cliente inactivo o responsable retirado.
4. Semántica precisa de completado/outcome y cancelación; qué hecho registra cada
   evento, campos mínimos de actor visibles, periodo y fuente de métricas.
5. Si se limita comercialmente, derecho canónico explícito vigente del servidor. No
   asumir tier/cupo/gracia ni añadir paywall a lectura sin contrato.

Ownership UI propuesto: `web/templates/dashboard.html`, módulo
`web/static/js/dashboard-seguimiento.js` focal, nuevo módulo/estilos/plantilla de tareas,
`Api.followup` cerrado en api.js y pruebas UI propias. El enlace y SSR/espacio profesional
se coordinarán al firmar rutas. No tocar backend/modelos/DDL/CI ni contrato global.

Mientras no exista wire34 firmado sólo se preparan estados/fixtures de presentación
offline con procedencia explícita. No se presenta un doble como API/HTTP/PG/browser real
ni se considera R23 completo por esta propuesta o por disponer de una pantalla.

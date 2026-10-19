# R12 / UX-07: inventario y contrato propuesto, revisión previa a implementación

Fecha: 2026-10-19. Base exclusiva: `7cf4e6c996708f580054a798406ccdc3336a0fa6`.
Worktree: `F:\MetodoBaseWeb-member-link-20261019`, rama
`implementation/member-client-link-20261019`.

**Estado: propuesta; sin API, cambios de modelo, DDL, correo, conexión a BD ni
operación externa.** La revisión29 no está autorizada por este documento.
Los hechos de código y la propuesta se distinguen expresamente.

## 1. Recomendación

Añadir tres entidades: una invitación para un cliente concreto, un vínculo
pendiente/aceptado con una cuenta y una publicación inmutable destinada a ese
vínculo. Admitir invitar antes del registro: el destinatario crea su cuenta por
el registro normal y acepta **la misma invitación** desde una sesión válida y
con el token recibido en su correo. El profesional nunca recibe ese token.

La prueba combina cuenta autenticada, correo persistido canónico coincidente y
posesión del token específico. La coincidencia de correo, por sí sola, no crea
una relación. Tampoco se escribe una marca global de `email_verified`.

La publicación materializa únicamente el menú/meta autorizados y el descriptor
exacto de su PDF privado. El socio los lee bajo su propio `user.id`; no hay
sesión ejecutada como el gimnasio ni se amplían las políticas de lectura de
Cliente, PlanGenerado, ClientProgress o StoredObject. El perfil/diario personal,
roles, equipo, cuotas, planes y pagos existentes se conservan separados.

La primera entrega propuesta de R12 es el vínculo y la lectura del plan
explícitamente publicado. Compartir diario/mediciones requiere permisos y
contrato adicionales: no se concede acceso por aceptar el vínculo. La sección
9 identifica la integración pendiente de seguimiento, sin atribuirla a una
función existente ni declarar completo el piloto R12/R14/R25.

## 2. Inventario comprobable

Leídos R12 y UX-07 en arquitectura, roadmap, prompt integral e informe UX;
DECISIONES, AISLAMIENTO, EQUIPO, RECUPERACION_CUENTA y matriz R04, además del
código referido abajo. No se encontró un ADR de identidad independiente: las
decisiones vigentes están en DECISIONES y la matriz R04.

La sonda de AST/archivos `backend-r12-inventory_probe.py` no importa aplicación,
SQLAlchemy ni SDK. Resultado: **16 comprobaciones estructurales, 99 fuentes
idénticas antes/después**, cero conexiones o llamadas a proveedores. El JSON
`backend-r12-inventory-source.json` contiene rutas, líneas de endpoints y SHA256.
Esto es una línea base estructural, no una prueba funcional o de seguridad R12.

| Estado actual | Evidencia en la base | Implicación para R12 |
|---|---|---|
| Head único `20261019_account_recovery`; 26 tablas de negocio, 20 familias RLS y 6 tablas de control explícitas | `schema_control.py:12`, `models.py`, `tenant_policy.py:9` | Revisión28 y sus fixtures permanecen históricos. No confundir revisión28 con número de tablas. |
| No ClientAccountLink, invitación de cliente ni publicación del socio | clases de `models.py`; inventario AST | No hay una relación que pueda habilitarse sólo con UI. |
| Usuario mantiene `team_gym_id`, invitación profesional y reset, pero no verificación persistida de correo | `models.py:50`, `models.py:84`, `models.py:99`, `models.py:109` | No usar email del JWT, registro o éxito de recuperación como verificación global. |
| Google comprueba `email_verified == "true"` durante login, sin guardar ese atributo | `routes/auth.py:126` | R12 no puede inferir después que una sesión cualquiera pasó esa comprobación. |
| Correo normalizado mediante `strip().lower()`; no casefold ni alias de proveedor | `account_values.py:4` | Reutilizar la semántica; nunca unir cuentas por alias. |
| Invitación profesional crea Usuario inactivo/equipo/rol; rechaza cuenta existente y devuelve bearer al emisor | `team_invitation_service.py:92`, `:133`, `:145` | No reutilizar su token, consumo ni alta para vincular socios. El emisor que conoce el bearer no prueba recepción por el destinatario. |
| Identidad canónica relee activo, rol, equipo y SV; R12 debe además exigir `deleted_at IS NULL` expresamente | `auth.py:435`, `:572` | No ampliar autenticación global en este lote; comprobar la identidad persistida en cada operación nueva. |
| `/api/usuario/*` usa ID de cuenta; equipo profesional usa su asociación persistida | `middleware/tenant.py:47`, `auth_deps.py:80` | Nuevas rutas de socio deben estar bajo el espacio propio, sin seleccionar gym mediante header/body. |
| Session y ambient distintos son rechazados | `tenant_context.py:28`, `:64`, `:88` | No relajar el rechazo, limpiar el contexto ni implementar un run-as gym para lecturas del socio. |
| Cliente propio y Cliente del gimnasio son filas diferentes | `usuario.py:48`, `models.py:173` | No mover `Cliente.gym_id`, ni copiar Cliente/planes por email. |
| FK de Plan/Progress a Cliente es actualmente simple; un Plan legado puede mezclar dueño A con Cliente B | `models.py:228`, `:525`; `test_individual_publication_security_review.py` | Nuevas referencias deben comprobar doble dueño por FK compuesta, no sólo confiar en Plan.gym_id. |
| Generar persiste plan/PDF; no existe estado profesional de publicación para socios | `plan_generation.py`, `repository.py:199`, `routes/planes.py:58` | Generar otro plan no debe entregarlo automáticamente. |
| PDF exacto valida Plan JOIN Cliente, ambos vivos; StoredObject exige ready/kind/owner/tamaño/SHA/backend | `plan_documents.py:20`, `private_objects.py:63`, `storage/objects.py:62` | Preservar ese contrato. No usar el endpoint profesional ni abrir un endpoint genérico de objetos para el socio. |
| ClientProgress sólo tiene medidas/fecha/notas; no se localizaron constructores en rutas de escritura actuales | `models.py:525`; sonda AST | No convertirlo en diario ni exponer sus notas mediante un vínculo. |
| Diario27 sólo resuelve fuente Plan propia y guarda snapshots personales | `personal_diary_service.py:101`, `personal_diary_persistence.py:34` | Un plan del gym no debe aparentar gym_id=user.id para entrar en ese contrato. |
| Export excluye cartera profesional y vínculos de socio sin verificar; OWNER ambiguo sigue fuera del espacio personal | `privacy_export.py:183`, `:216`; `DECISIONES.md:24` | No adoptar la cartera OWNER ni cambiar roles para hacer funcionar R12. |
| Firma estructural v1 no captura triggers/funciones nuevas; firma de seguridad v1 sólo contempla políticas y helper set_tenant | `alembic/schema_contract_v1.py`, `security_contract_v1.py` | R12 necesita vocabulario adicional versionado para comprobar sus invalidadores; no editar v1 ni regenerar targets previos. |

Los estados narrativos de ARQUITECTURA_ACTUAL/RECUPERACION_CUENTA en esta base
van por detrás del head real. Este inventario usa Git/código28 y no reescribe
los documentos del coordinador.

## 3. Identidades y permisos propuestos

El emisor debe ser propietario profesional persistido válido o miembro
profesional activo de ese propietario, con capacidad expresa. Resolver el gym
desde la identidad persistida; cargar Cliente por gym+id y no borrado/activo.
`tipo='usuario'` o un rol OWNER aislado no acreditan ser dueño profesional.

La recomendación conservadora de elegibilidad es cuenta activa/no borrada, sin
invitación profesional pendiente, rol persistido válido noOWNER y espacio
individual o pertenencia profesional válida. Un miembro profesional conserva
su equipo; aceptar como socio no modifica ese equipo. Para OWNER de gym y
OWNER/tipoUsuario ambiguo propongo `member_context_requires_review`, sin adoptar
cartera ni alterar sus rutas anteriores de generación. **Esta elegibilidad de
la función nueva requiere decisión de root:** decisión18 ya protege el diario
y export personal, pero no resuelve por sí sola si un OWNER puede aceptar un
vínculo limitado al cliente externo sin clasificar su cartera. No presento esa
restricción nueva como permiso existente. Si se autoriza ese caso, la cuenta
conservaría su rol y el diario/export ambiguos seguirían sin adopción.

| Acción nueva | Capacidades propuestas, sujetas a revisión |
|---|---|
| Invitar, reenviar, revocar por gimnasio | OWNER/ADMIN profesional válido de ese gym; no VIEWER/NUTRIOLOGO |
| Publicar/retirar plan | OWNER/ADMIN/NUTRIOLOGO profesional válido, coherente con crear/exportar plan; no VIEWER |
| Consultar estado mínimo del vínculo para el cliente | OWNER/ADMIN/NUTRIOLOGO profesional válido; sin datos personales de la cuenta |
| Inspeccionar/aceptar invitación | Sólo aceptante autenticado y prueba específica de destinatario |
| Listar vínculos/leer publicación/PDF | Sólo cuenta persistida del vínculo activo; autorización por recurso |
| Desvincularse | Titular del vínculo, sin revocar su cuenta ni sesiones personales |
| Cartera, equipo, billing, generación profesional, progreso personal | Ningún permiso nuevo por R12 |

Añadir capacidades para estos recursos, sin roles nuevos. No reutilizar el
paywall `can_multi_user` de equipo: no existe en el catálogo un precio o cupo
de socios que autorice aplicarlo aquí. Tampoco equiparar membresía del cliente,
licencia SaaS y suscripción individual.

Unicidad recomendada: un vínculo activo por cliente; un cliente activo por
cuenta dentro de cada gym; una misma cuenta puede aceptar vínculos explícitos
en gimnasios diferentes. Cambiar destinatario o sustituir cuenta exige revocar
el vínculo previo, crear uno nuevo y publicar para el nuevo vínculo. Nunca
resucitar un vínculo revocado, transferir su user_id ni heredar automáticamente
la publicación del destinatario anterior. No hay backfill de vínculos por
email, proximidad, fecha, tipo, suscripción o número de clientes.

## 4. Modelo29 propuesto

Tres tablas nuevas: 29 tablas de negocio/23 familias RLS si se aprueba esta
partición; las seis tablas de control actuales no se amplían. Todos los
instantes nuevos usan UTCDateTime explícito y reloj aware UTC. Versiones
positivas hasta INT32_MAX, sin wrap; desbordamiento requiere revisión.

| Entidad | Datos mínimos y restricciones |
|---|---|
| `ClientAccountLink` / `client_account_links` | UUID36; gym_id; client_id; user_id nullable mientras pending; status pending/active/revoked; version; created_at/updated_at/accepted_at/revoked_at; etiquetas públicas del gym y cliente acotadas al emitir. FK RESTRICT gym→Usuario y compuesta (gym_id,client_id)→Cliente; FK RESTRICT user→Usuario. UNIQUE(gym_id,client_id,id) para referencias. Parciales: sólo un vínculo no revocado (pending o active) por cliente; sólo un active por (gym,user). Active exige user y accepted_at; pending exige ambos NULL; revocado conserva procedencia. |
| `ClientLinkInvitation` / `client_link_invitations` | UUID36; gym_id/client_id/link_id exactos; recipient_email canónico explícito; token_hash64 único con propósito; expires_at; status pending/consumed/revoked; issued_by; consumed_by nullable; version; created/updated/consumed/revoked; request_key128 y payload_hash64 de emisión, UNIQUE(gym_id,request_key). FK compuesta RESTRICT al link y FK RESTRICT a cuentas. Un registro de invitación por link; reenvío rota hash/versión del pending sin cambiar destinatario. Consumo registra el user exacto; nunca guarda token plano. |
| `ClientPlanPublication` / `client_plan_publications` | UUID36; gym_id/client_id/link_id; source_plan_id; schema_version1; publication_version; status published/withdrawn; published_by/at, withdrawn_at; menú/meta conocidos serializados y SHA; descriptor PDF nullable: source_object_id32, backend, key, content_type, byte_size, sha256. FK RESTRICT compuesta al link, a Cliente y (gym,client,plan) a Plan; FK compuesta gym/object a StoredObject. Sólo una published por link. JSON, contenido/descriptor y procedencia inmutables; retirar no los reescribe. Ninguna ruta devuelve key/backend/path al navegador. |

Las parejas/triples de FK requieren UNIQUE adicionales en Cliente
`(gym_id,id_cliente)` y Plan `(gym_id,id_cliente,id)`; se agregan sólo en29.
La unicidad global previa de sus IDs hace compatibles esas claves sin unir
filas. Un Plan legado mezclado no puede convertirse en publicación: su Cliente
no satisface ambas referencias compuestas. RESTRICT no es política de retención;
significa que no hay un borrado automático de esta asociación y que un futuro
workflow de supresión deberá resolverla explícitamente.

El link **pending se crea al emitir**, con user_id NULL, bajo autorización gym
y bloqueo de Cliente activo/no borrado. Esto acredita disponibilidad sin que el
aceptante consulte Cliente. La aceptación sólo puede realizar la transición
pending→active del mismo link. La disponibilidad posterior se conserva mediante
invalidación transaccional, no mediante una copia de un flag que quede sin
mantenimiento.

## 5. RLS y capacidad de invitación

Las 20 políticas previas se conservan. Las tres tablas nuevas tienen ENABLE y
FORCE; políticas por operación, no una política ALL permisiva común.

| Tabla | SELECT | INSERT/UPDATE/DELETE |
|---|---|---|
| links | Gym propio, titular user_id propio, o el único pending demostrado por una invitación/digest válido | Gym sólo crea pending sin usuario; aceptación propia sólo pending→active con invitación consumida en la misma TX; gym/titular sólo pueden revocar. Identificadores y sujeto ya aceptado inmutables. No DELETE ordinario. |
| invitations | Gym propio; o capacidad por digest + sujeto autenticado/persistido válido y correo coincidente | Gym emite/rota/revoca pending; el destinatario probado consume por CAS. No asignación de destinatario por profesional ni escritura de filas ajenas. No DELETE ordinario. |
| publications | Gym propio; o publicación vigente cuyo link exacto está active y cuyo user_id es el tenant personal actual | Sólo gym publica/retira. Titular no puede cambiar contenido, origen, descriptor o estado. No DELETE ordinario. |

La comprobación de destinatario en la política consulta únicamente Usuario por
ID propio (control de identidad existente). La política de links puede
consultar invitations; la de invitations no consulta links, evitando recursión.
Publication puede consultar links; links no consulta publication. La consulta
del socio revalida además cuenta/propietario del gym activos y no borrados;
el estado o el rol del JWT no reemplazan esas lecturas.

La única capacidad adicional es `app.client_invitation_digest`:

1. Solicitar sesión autenticada bajo user.id; validar token ASCII URL-safe de
   exactamente43 caracteres y cuerpo acotado. El hash64 almacenado no es input
   admitido. `SHA256('client-account-invite-v1:' + token)` separa propósitos de
   R11 y R16. El usuario, gym, cliente y rol no vienen del body de aceptación.
2. Tras autobegin, comprobar que Session/ambient corresponden a ese actor y
   ejecutar `set_config(..., :digest, true)` parametrizado. No modificar
   `app.current_tenant`, no context vacío forzado, no cabecera de contexto.
3. Una política permite únicamente la fila con ese digest y destinatario
   coherente con Usuario persistido. El servicio no devuelve nombre de gym,
   cliente, destinatario ni estado antes de validar la prueba completa.
4. Limpiar el propósito al principio de **toda** transacción, incluidas Session
   y Connection directas, y restaurar/cerrar sin commit en lecturas. Cualquier
   fallo de instalación impide la consulta. Rollback/commit borra SET LOCAL;
   el hook inicial también pisa un valor session-level residual de pool.
5. La capacidad no concede SELECT/UPDATE de Cliente, Plan, objetos, diario o
   invitaciones diferentes. No función SECURITY DEFINER, rol BYPASSRLS ni
   endpoint de consulta global. El servicio de mail no recibe una Session ni
   propaga el ContextVar de un request.

Las tres familias no se agregan ciegamente al generador ALL de TENANT_COLUMNS:
se describen en un grupo29 específico con sus políticas por operación y el
conteo total de familias explícito. El generador histórico de las20 familias
no puede sobrescribir estas reglas personal/gym/destinatario.

El correo se normaliza con la función compartida; no se toma del JWT para
verificar destinatario. Una representación histórica/canónica ambigua de
cuentas requiere revisión, sin merge ni elección por primera fila. La cuenta
que acepta se fija explícitamente por su ID autenticado sólo al consumir.

## 6. Triggers estrechos, transacciones y carreras

Todos los triggers nuevos son invoker, identificadores constantes y schema
calificado, search_path fijo; sin SQL dinámico, lectura global o función pública
que devuelva Cliente/Plan. Sólo afectan las tres tablas nuevas relacionadas con
la fila fuente. El rol app sigue sin privilegio de DDL ni pertenencia al dueño.

| Fuente/transición | Efecto técnico propuesto en la misma TX |
|---|---|
| Insert link por gym | FK/dueño y Cliente activo/no borrado comprobados bajo contexto gym y bloqueo; sólo pending/user NULL. No consulta original desde aceptación. |
| Insert publication por gym | Repetir referencia exacta Plan/Cliente/link y, si existe PDF, igualdad entre source_object_id y Plan.pdf_object_id más ready/kind/dimensiones/descriptor de StoredObject. El trigger sólo lee esas filas bajo gym; el endpoint no acepta descriptor ni JSON de publicación suministrados por UI. |
| Cliente activo→inactivo o deleted_at noNULL | Revocar links pending/active, invitaciones pending y retirar proyecciones de ese cliente. Las lecturas/historia profesional previas conservan sus reglas; sólo se corta la entrega nueva R12. |
| Cliente hard-delete/cambio de identidad | RESTRICT impide romper referencias; no mover filas, cascada de bytes ni adopción. |
| Plan fuente borrado/cambiado en sitio | Retirar proyecciones de ese Plan. Generar otro Plan nuevo no modifica la publicación anterior; cambios de contador/ultimo_plan de Cliente no son invalidación. |
| StoredObject fuente cambia descriptor/backend/ready | Retirar proyecciones que dependen de ese objeto; no copiar una referencia nueva o recurrir a legacy. DELETE protegido por FK RESTRICT. |
| link ya aceptado | No se permite cambiar gym/client/user, ni revocado→active. Nueva invitación requiere nuevo link. Revocación corta SELECT de publicaciones por el predicado del link aunque el titular no tenga UPDATE sobre publication. |

**Aceptación contra baja de cliente:** baja mantiene el bloqueo de su Cliente y
actualiza los links en el trigger; aceptación bloquea/relee el link, sin leer
Cliente bajo tenant personal. Si la baja confirma primero, el link ya está
revocado. Si aceptación tiene el bloqueo primero, puede confirmar; la baja
espera y revoca antes de confirmar. No queda un vínculo activo creado después
de una baja ya confirmada. El estado pending certificado al emitir no sobrevive
a una baja confirmada. Las pruebas deben verificar ambas intercalaciones con
SQL real, incluyendo UPDATE directo y rollback de la baja.

Orden propuesto para la elegibilidad recomendada: propietario gym Usuario primero cuando corresponda; después
cuentas noOWNER requeridas (actor/aceptante, orden estable entre ellas); luego
Cliente en operaciones gym; link; invitación; Plan al publicar; publication.
El aceptante no bloquea/lee Cliente ni Plan. Operaciones que tocan varias filas
de link/publication lo hacen en orden estable de ID. User→Refresh de reset/logout
no se invierte: R12 no modifica Refresh ni SV. Revalidar SV del bearer capturado
después del lock; una sesión revocada no puede aprovechar una comprobación
anterior al bloqueo. Los invalidadores de Cliente/Plan/StoredObject no adquieren
Usuario ni vuelven a bloquear la fuente desde un link. Validar este grafo con
R11/reset/revocación real antes de aprobar29; es una obligación de prueba, no
una afirmación de ausencia de deadlocks.

Cada mutación tiene una sola Session y un solo commit dueño del servicio;
dependencia local sin autocommit final (igual criterio que R14). GET/info sólo
SELECT/SET LOCAL, sin commit ni negocio DML. Se reevalúa caducidad **después**
de adquirir locks, con reloj aware UTC y CAS contra estado/hash/versión reales.

Consumo: pending+hash+destinatario+disponibilidad→consumed y link→active en una
TX. Dos consumidores tienen un solo ganador. SV/rol/team/perfil no cambian;
no auto-login ni nueva emisión de tokens. Replay no crea un segundo vínculo.
ACK de commit incierto:503 `member_link_reconciliation_required`, sin reenvío,
deshacer ni reasignar automáticamente. El titular consulta sus vínculos para
resolver el resultado. Rollback visible; errores técnicos sólo clase en logs.

## 7. Publicación y PDF

Publicar es una acción explícita con Plan ID y versión esperada del link.
Puede prepararse para un pending o active del mismo cliente; sólo active lo
expone al destinatario. Reinvitar tras revocación crea otro link, por lo que no
hereda publicaciones del anterior. Un reemplazo retira la publicación anterior
y agrega una nueva, atómicamente; no reescribe el snapshot anterior.

El publicador, bajo gym persistido, comprueba Plan JOIN Cliente con doble dueño,
cliente activo y ambos no borrados, link exacto y fuente coherente. Lee JSON
persistido con presupuesto previo al parse (propuesta256KiB UTF-8), estructura
conocida de cuatro comidas, números finitos, límites de opciones/alimentos y
respuesta máxima512KiB. Rechazo íntegro ante exceso/corrupción; sin truncar,
recalcular un menú diferente, companion file ni campos libres de cliente/notas.
Congela contenido/meta conocidos y SHA de la representación canónica.

Si Plan tiene pdf_object_id, comprobar ready+kind plan_pdf+owner+backend y copiar
únicamente ese descriptor. Un ref presente inválido impide publicar: no se
omite ni sustituye. Si sólo hay una ruta PDF legacy, no se copia/publica por
heurística: podrá proponerse menú válido con PDF no disponible y motivo
`legacy_requires_review`, o requerir migración legacy explícita antes de
publicar PDF. Esta elección de presentación requiere aprobación; ningún caso
abre la ruta antigua al socio. Nuevos planes canónicos conservan PDF exacto.

La descarga nueva recibe **link_id y publication_id**, nunca object_id, key,
path, gym_id o un Plan arbitrario. Bajo user.id bloquea/revalida el link y la
publicación exactos; construye el ObjectDescriptor exclusivamente desde esa
proyección validada, comprueba backend configurado/kind/tamaño/SHA y usa el
adaptador privado con el owner persistido de esa capacidad. Eso no habilita
StoredObject ni invoca el router PDF profesional. No URL pública ni presignada,
PUT, copia de bytes, fallback de backend o documento más reciente.

El bloqueo de autorización se mantiene durante la lectura acotada. Una lectura
autorizada antes de revocar puede terminar mientras la revocación espera;
después de confirmar revocación toda lectura nueva falla. Si se retira/cambia
la publicación entre una vista y su botón, la descarga exacta falla404, nunca
devuelve el PDF nuevo silenciosamente. Cuerpo/chunk y storage externos siguen
sus límites; no se promete cancelación de bytes ya entregados.

## 8. Rutas y contrato UI propuestos

Nombres sujetos a revisión antes de que frontend se acople. Web/API montan los
servicios compartidos; no UI, api.js o historial existente en esta fase.

| Ruta | Entrada/resultado/autoridad |
|---|---|
| POST `/api/clientes/{client_id}/vinculacion/invitaciones` | Profesional; `{recipient_email}` y request key de reintento; crea link pending e invitación.202 con IDs opacos, estado, expiry, `delivery_status:not_confirmed`; jamás bearer/hash/enlace. Reintento exacto no manda dos correos; hash de payload distinto con misma clave409. |
| POST `/api/clientes/{client_id}/vinculacion/invitaciones/{invitation_id}/reenviar` | Profesional, versión esperada; rota token pendiente y caducidad, invalida anterior. No retarget por cambio de Cliente.email. |
| GET `/api/clientes/{client_id}/vinculacion` | Estado mínimo/paginado del cliente del gym; no existencia global de una cuenta ni su cartera. |
| DELETE `/api/clientes/{client_id}/vinculacion/{link_id}` | Profesional; CAS versión; revoca, no borra cuenta ni datos personales. |
| POST `/api/clientes/{client_id}/vinculacion/{link_id}/publicaciones` | Profesional publica `{plan_id,expected_link_version,expected_publication_version}`; sólo ese cliente/plan y link. |
| DELETE `/api/clientes/{client_id}/vinculacion/{link_id}/publicaciones/{publication_id}` | Retira por versión; no borra fuente ni bytes. |
| POST `/api/usuario/vinculaciones/invitacion` | Token en body, sesión propia; lectura sin consumo. Sólo después de verificar destinatario muestra contexto/estado/caducidad/versión. |
| POST `/api/usuario/vinculaciones/aceptar` | `{token,expected_version,confirm:true}`; cuenta+correo+proof, sin password/user/gym/client/role.200 link activo; no login automático. |
| GET `/api/usuario/vinculos` | Vínculos de su ID, paginación keyset, máximo100 por página. Contextos explícitos y capabilities; sin adoptar otro Cliente. |
| GET `/api/usuario/vinculos/{link_id}/plan` | Publicación vigente o `publication:null` si todavía no se publicó. Sólo link activo propio. |
| GET `/api/usuario/vinculos/{link_id}/publicaciones/{publication_id}/pdf` | PDF privado exacto;404 uniforme para ajeno/retirado/inaccesible. |
| DELETE `/api/usuario/vinculos/{link_id}` | Titular; versión esperada, revoca únicamente esta relación; sesiones/diario/perfil conservados. |

Ejemplo de lectura de socio:

```json
{
  "context": {"kind":"gym_member","link_id":"<uuid>","gym_name":"Gym sintético","client_display_name":"Socio sintético"},
  "link": {"status":"active","version":2},
  "capabilities": {"read_published_plan":true,"download_published_pdf":true,"share_personal_diary":false,"read_shared_progress":false,"manage_clients":false,"manage_team":false},
  "publication": {"id":"<uuid>","version":1,"source_plan_id":41,"published_at":"2026-10-19T18:00:00+00:00","plan_schema_version":1,"plan":{},"meta":{},"pdf_url":"/api/usuario/vinculos/<link>/publicaciones/<publication>/pdf"}
}
```

`plan:{}` arriba sólo abrevia el ejemplo; una publicación real no acepta un menú
vacío/corrupto como válido. Las etiquetas proceden de datos autorizados del gym
al emitir/publicar y no de una consulta personal de Cliente/GymProfile.

Errores públicos propuestos:401 `member_identity_unavailable`;404 uniforme
`member_link_unavailable`/`member_publication_unavailable`;404
`member_invitation_unavailable` para token/sujeto no acreditado;410
`member_invitation_expired` y409 `member_invitation_consumed` sólo al destinatario
ya probado;409 `member_link_conflict`/`member_version_conflict`/`member_context_requires_review`;
413 cuerpo;422 DTO;429 límite;503 servicio/config/ACK incierto. No devolver
destinatario ni existencia de cuenta a un token/sesión incorrectos.

Configurar origen first-party desde BASE_URL validado, no Host/Referer/redirect
arbitrario. Página nueva `/auth/accept-client-link#token=...`: quitar fragmento
antes de cualquier I/O, token sólo memoria; no query, logs, analytics,
local/sessionStorage ni return_to con bearer. GET no consume. Usuario nuevo
puede completar registro normal y volver al mismo enlace de correo; si la
página se recarga sin token, se vuelve a abrir el enlace original vigente, no
se fabrica una asociación por cuenta/email. Login/registro no convierten un
link en activo automáticamente.

Todas las respuestas nuevas, incluidos405/404/429/parse, no-store y no-referrer;
CSP first-party fija para la página, sin confiar en CSP de downstream ni CDN.
Stream limitado antes de JSON/Pydantic, propuesta16KiB; extra fields y claves
duplicadas rechazadas. Rate limit sensible fail-closed con IP+actor+destinatario
o token HMAC, sin emails/tokens en Redis. Añadir paths reales a límites y
redacción existentes, sin cambio global del login o recuperación.

Token256bits, hash con propósito, propuesta de caducidad7 días reutilizando el
límite técnico de invitación existente; caducar no revoca un vínculo aceptado.
Emisión confirma DB antes del intento de correo y libera conexión antes del
SDK. Transporte admitido en capacidad acotada, contexto nuevo; ausencia de
configuración503 antes de crear estado. Mail a destinatario explícito aun si
todavía no hay cuenta; mismo flujo/resultado sin consultar existencia al emitir.
ACK sólo significa aceptación del proveedor, nunca entrega o destinatario
verificado. Cola/proceso o ACK incierto dejan pending y estado not_confirmed;
no borrar ni reasociar, reenvío explícito rota el token. No prometer outbox
durable ni envío una sola vez; sí un único consumo y efecto de vínculo.

## 9. Diario, progreso, exportación y límites de alcance

R12 no cambia el Cliente propio, los planes de generación personal ni
personal_diary_days. El usuario puede seguir usando su diario personal; no
importar claves legacy ni duplicar su historia en un gym. ClientProgress del
gym y diario personal no son intercambiables. En este primer permiso de
vinculación, `share_personal_diary` y `read_shared_progress` son false, sin
un flag de consent dado por defecto ni ruta que aparente acceso existente.

Para registrar consumo desde el menú del gym hace falta una extensión R14
explícita con `source_publication_id` autorizado, propietario user.id y contexto
del vínculo; el lector personal actual lo rechaza correctamente. No simular
un Plan con gym_id=user.id ni reutilizar índices de opciones de otro plan.
Debe acordarse si ese contexto tiene diario separado por link/fecha o un DTO
de fuentes múltiples dentro del diario propio antes de añadir persistencia.
Compartición con profesionales exige consentimiento separado por conjuntos,
alcance/fechas y retirada; R25 y políticas de conservación siguen abiertos.

Exportación actual mantiene intacta la barrera de cartera OWNER. Proponer una
sección R12 paginada de asociaciones/consentimiento propios y publicaciones que
siguen autorizadas; nunca perfiles/notas/historial completo del gym. No ampliar
`personal_space_supported` por tener un vínculo. Cualquier nuevo conjunto y su
presupuesto/cursor deben componerse explícitamente con frontend export, sin
alterar los seis conjuntos actuales ni afirmar export de contenido revocado.

## 10. Migración, firma y compatibilidad

Nombre tentativo `20261019_client_account_links`, down_revision
`20261019_account_recovery`; upgrade exige huella exacta28 antes de DDL. Nuevos
modelos/constraints/índices/políticas/triggers y target29 SQLite/PG; ninguna
historia se asocia automáticamente. Vacío→29 y snapshot28 poblado→29 producen
misma estructura/seguridad, con filas28 intactas y tablas nuevas vacías.

No modificar `schema_contract_v1.py`, `security_contract_v1.py` ni SQL/targets
22..28. Añadir contrato opcional29 de funciones/triggers (nombres, tablas,
definiciones normalizadas, enabled, invoker/security-definer, search_path y
permisos) y comprobarlo en startup/restore. RLS/función alterada, trigger
deshabilitado o invalidación faltante impide servir. Las firmas previas siguen
comparándose mediante sus vocabularios previos. SQLite necesita triggers
equivalentes y foreign_key_check tras batch, sin bajar FK silenciosamente.

Históricos sensibles al head nuevo detectados en lectura: runtime28 por
defecto en `integration_account_recovery_migrations.py:45` y
`integration_recovery28_restore_review.py:225`; su restore además inicia
factories28 reales en helpers. No se cambiaron. Antes de implementación se
acordará pin de revisión exacto donde su criterio era28 y ejecución de restore28
en snapshot28 inmutable; nuevo restore29 conserva todos sus datos/criterios y
añade R12 para ejecutar factories29. No habilitar factory29 sobre una BD28 ni
alterar asserts/filas para hacer pasar el histórico. CI nuevo queda a cargo del
coordinador después de aceptar el contrato.

No create_all/stamp/fallback migratorio. Upgrade repetido sin cambios, fallo
intermedio rollback de filas/DDL/revisión, prueba SQLite y PG UUID app/migrador
restringidos. Downgrade destructivo rechazado; rollback de aplicación requiere
retirar tráfico/versión compatible y restore verificado, sin inventar TTL de
retención ni borrar datos nuevos.

## 11. Matriz de aceptación obligatoria antes de integrar29

Cada caso usa cuentas sintéticas; sin correo/proveedor real. Baseline funcional
rojo de rutas ausentes se registrará después de aprobación del contrato, sin
atribuirla a pruebas aún no ejecutadas. PG en DB UUID propia con app
NOSUPERUSER/NOBYPASSRLS/sin DDLowner y migrador separado; no activar en BD
compartida ni producción.

| Área | Casos/resultado verificable |
|---|---|
| Registro y recepción | Invitar sin cuenta→registro real VIEWER→mismo token aceptado; cuenta existente conserva ID/Cliente/planes/diario/team/role/password/SV/refresh. No autologin. Una mera coincidencia de email no crea link. |
| Destinatario | JWT/email falseado, usuario distinto con token, token sin sesión, email no canónico/ambigüedad histórica, inactivo/borrado/invitación profesional pendiente, OWNER ambiguo: no link ni datos de gym antes de prueba completa. Google login no omite token específico. |
| Tokens | R11/R16 token/hash cruzado, digest64 como bearer, padding/Unicode/tamaño, vencido después de esperar lock, consumido, revocado, reenviado y payload extra: rechazo; nuevo token funciona una vez. Emisor nunca ve bearer/link/hash ni en respuesta/error/audit. |
| Dos gyms y perfiles | A/B con clientes/plans/objetos distintos; profesional de B con cuenta personal vinculada A ve sólo proyección A y su propio diario, no cartera A ni cliente B ajeno. UI gym/client/header no cambia autoridad. Rol/equipo no se añaden. |
| FK/procedencia | Link de Cliente ajeno y publicación Plan A/Cliente B legado rechazados por restricciones/servicio; ningún snapshot/PDF se publica. Reasignar gym/client/user o resucitar revocado falla aun mediante DML directo. |
| RLS base | Sin tenant ni propósito:0 de nuevas tablas. Con user correcto sin token: no pending ajenos. Con capacidad: sólo invitación exacta+link pending y destinatario propio. Cliente/Plan/StoredObject/Diary mantienen su matriz anterior, incluida Connection/Session directa. |
| Pool/capacidad | Pool1 A→commit/rollback/error→B y sesión sin auth: no heredan digest. Valor session-level antiguo es pisado. SET LOCAL falla: ninguna consulta de negocio. Ningún helper cambia current_tenant. |
| Consumo concurrente | Dos procesos mismo bearer/cuenta y dos cuentas competidoras: un único CAS/active, segundo rechazo estable; diferentes keys no eluden unicidad cliente/cuenta/gym. Commit ACK perdido se resuelve con consulta, sin segundo link/correo automático. |
| Baja vs aceptar | Ambas intercalaciones usando locks reales/pg_blocking_pids; baja por activoFalse y deleted_at (UPDATE directo), más rollback de baja. Tras baja confirmada no pending/active usable, ni publicación legible. |
| Roles y sesiones | Actor pierde capacidad antes de consumir; gym se desactiva; logout/reset gana antes de lock de aceptación; no deadlock con User→Refresh. Member revoke no cambia sus roles, otras relaciones, SV ni diario. |
| Publicación | Generación nueva no publica ni retira la anterior; publish/reemplazar/retirar por versión con un solo current por link; link nuevo no hereda anterior. Tipo/número de fuente no se fabrica por latest. |
| Proyección y límites | JSON corrupto/duplicado/no finito/oversize/opciones/foods; rechazo entero antes de parse/cuerpo completo. No notas/email/credenciales ni rutas en JSON/DTO. Snapshot de menú exacto e inmutable; no fallback a companion file. |
| Invalidadores | Actualizar/borrar fuente Plan, baja Cliente y cambio descriptor/backend/ready de objeto retiran acceso en la misma TX; rollback no retira. Trigger deshabilitado/alterado o función definer impide startup29. No impacto de generar Plan nuevo/actualizar contadores de Cliente. |
| PDF exacto | Dos planes mismo cliente: SHA del publicado, nunca último; mismo object ID de otro owner, tipo incorrecto, pending, tamaño/SHA alterados, backend distinto, objeto missing/legacy:404 sin fallback. Endpoint genérico/profesional sigue sin conceder cartera al socio. |
| Revocación concurrente | Leer+revocar, publicar+revocar y retirar+descargar, ambas órdenes. Una operación ya autorizada puede concluir antes de revocación; toda iniciada tras commit se deniega. No quedar publicación activa hacia un link transferido. |
| Transporte y HTTP | SDK wire from/ACK existente preservado; no cuenta todavía y existente tienen mismo flujo. Disabled/cola llena/fallo/ACK incierto no afirma entrega. Rate failclosed, stream cap, every-method headers, fragment eliminado y registro/login/newaccount browser sin persistir token. |
| Histórico/export | Igualdad de filas/permisos/cuotas/diario28; OWNER conserva barrera; revocar no elimina personal. Export asociaciones propias acotado/paginado, sin cartera/tokens/descriptores; contextos no adoptan historia. |
| Migración/restore | Vacío, snapshot28 poblado, repeat, drift, fallo tras DDL, rollback y FKcheck; restore29 con pending/active/revoked, correo sólo hash, pub actual/retirada y bytes exactos, triggers/roles/pool y lecturas posteriores reales. Históricos28 preservados por revisión. |

Archivos nuevos previstos para pruebas: `test_client_account_links.py`,
`test_member_plan_publications.py`, `test_client_link_invitation_boundaries.py`,
`integration_client_account_links_postgres.py`,
`integration_client_link_migrations.py` y
`integration_client_link_restore_review.py`. QA/seguridad definirán rutas
propias distintas para canarios independientes; todavía no se han creado.

## 12. Alcance de edición que se solicitará al aprobar contrato

Propiedad nueva backend: router/schemas/service R12, modelos29, migración única,
targets/fixtures29, pruebas/evidencia propias. Integraciones pequeñas a acordar:
hook de propósito SQL en tenant_context, capacidades en permissions, gate
opcional de firma29 en schema_control, montaje factories, rate-limit paths,
redacción/headers de página nueva y template mail que preserve ACK del SDK.
Nada de api.js/UI/landing/historial/catálogo/ledger/cuotas actuales.

Antes de autoría, root/seguridad deben revisar expresamente: GUC exclusivo29 y
grafo de políticas; pending-link certificado e invalidadores bajo RLS invoker;
orden de locks; descriptor PDF exacto sin acceso general; unicidades/roles/TTL;
tratamiento honesto de PDF legacy; y separación del siguiente diario/progreso.
No son decisiones de precio, permiso del usuario u operación en vivo.

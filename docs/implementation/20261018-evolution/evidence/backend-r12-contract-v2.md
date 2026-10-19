# R12 / UX-07: contrato v2 tras objeciones de seguridad, previo a29

Fecha: 2026-10-19. Base exclusiva: `7cf4e6c996708f580054a798406ccdc3336a0fa6`.
Worktree: `F:\MetodoBaseWeb-member-link-20261019`, rama
`implementation/member-client-link-20261019`.

**Estado: propuesta; sin API, cambios de modelo, DDL, correo, conexión a BD ni
operación externa.** La revisión29 no está autorizada por este documento.
Los hechos de código y la propuesta se distinguen expresamente.

La preimagen no se sobrescribe: contrato original SHA256
`6f53ad95743411e309dd6078f6f6d18d28f4c32f1cee64187799c458ef77aed9`, freeze original
`6232f3d400ae5dc42430e3cf65871e585bd24961b34bdbb8ea5bdd09f2857bcc`, cuatro archivos
RAW preservados en commit de evidencia `6e2b84c` y ZIP privado independiente.
Las99 dependencias de aquella línea base permanecen intactas. V2 es un archivo
nuevo; no se volvió a ejecutar la sonda ni se ejecutó PostgreSQL. Sección13
responde las cuatro objeciones y fija pruebas aún pendientes de implementación.

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

El aceptante debe ser cuenta activa/no borrada, sin invitación profesional
pendiente y con identidad/rol persistidos válidos. Se admite cuenta personal,
miembro profesional válido y, por decisión expresa de coordinación, un OWNER
profesional legítimo, incluido el caso de otro gimnasio. Este OWNER conserva rol, equipo,
cartera y las barreras existentes de diario/export personal: el vínculo sólo
autoriza el recurso externo. OWNER/tipoUsuario ambiguo permanece fail-closed
con `member_context_requires_review`, sin adoptar cartera ni cambiar sus rutas
anteriores. El caso OWNER de su mismo gym exige igualmente token y prueba
específica; la rama gym de RLS no acredita que sea destinatario. No se añade
una prohibición comercial de ese caso. Un miembro profesional conserva su equipo.

La rama RLS gym propio también es verdadera cuando el socio es OWNER-A. Por
eso **cada consulta de recurso de socio** agrega `link.user_id == actor.id` y
`link.status == 'active'` antes de devolver DTO, menú, PDF o exportación; no
considera suficiente que RLS haya devuelto una fila. Info/aceptación todavía
pending usan en cambio token+correo+actor explícitos, sin aceptar la rama gym
como prueba de destinatario, y sólo devuelven aceptación final para user_id
igual al actor. Sección13 concreta cada transición y la negativa OWNER-A/B.

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
| `ClientAccountLink` / `client_account_links` | UUID36; gym_id; client_id; user_id nullable mientras pending; status pending/active/revoked; version; created_at/updated_at/accepted_at/revoked_at; etiquetas públicas del gym y cliente acotadas al emitir. FK RESTRICT gym→Usuario y compuesta (gym_id,client_id)→Cliente; FK RESTRICT user→Usuario. UNIQUE(gym_id,client_id,id) para referencias y UNIQUE(id,gym_id,client_id,user_id) como testigo de aceptación. Parciales: sólo un vínculo no revocado (pending o active) por cliente; sólo un active por (gym,user). Active exige user y accepted_at; pending exige ambos NULL; revocado conserva procedencia. |
| `ClientLinkInvitation` / `client_link_invitations` | UUID36; gym_id/client_id/link_id exactos; recipient_email canónico explícito; token_hash64 único con propósito; expires_at; status pending/consumed/revoked; issued_by; consumed_by nullable; version; created/updated/consumed/revoked; request_key128 y payload_hash64 de emisión, UNIQUE(gym_id,request_key). FK compuesta RESTRICT al link y FK RESTRICT a cuentas. Además FK diferida NO ACTION (link_id,gym_id,client_id,consumed_by)→Link(id,gym_id,client_id,user_id): consumed no puede confirmar sin usuario coincidente en Link. Un registro de invitación por link; reenvío rota hash/versión del pending sin cambiar destinatario. Consumo registra el user exacto; nunca guarda token plano. |
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
| publications | Gym propio; o publicación vigente cuyo link exacto está active y cuyo user_id es el tenant personal actual | INSERT/UPDATE de negocio sólo gym. UPDATE USING incluye destinatario acotado exclusivamente para SELECT FOR UPDATE/SHARE; su WITH CHECK es false. No permite DML de socio ni DELETE. Trigger de inmutabilidad también impide convertir una fila ajena en gym propio. |

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
| Cliente hard-delete/cambio de identidad | Con referencias R12, RESTRICT rechaza toda la operación; no prometer borrado confirmado con retirada. No mover filas, cascada de bytes ni adopción. |
| Plan fuente deleted_at/cambio de contenido en sitio | Retirar proyecciones de ese Plan en la misma TX. DELETE físico con referencias RESTRICT se rechaza entero; no se borra y retira simultáneamente. Generar otro Plan nuevo no modifica la publicación anterior; cambios de contador/ultimo_plan de Cliente no son invalidación. |
| StoredObject fuente cambia descriptor/backend/ready | Retirar proyecciones que dependen de ese objeto; no copiar una referencia nueva o recurrir a legacy. DELETE físico con referencias RESTRICT se rechaza entero. |
| link ya aceptado | No se permite cambiar gym/client/user, ni revocado→active. Nueva invitación requiere nuevo link. Revocación corta SELECT de publicaciones por el predicado del link aunque el titular no tenga UPDATE sobre publication. |

**Aceptación contra baja de cliente:** baja mantiene el bloqueo de su Cliente y
actualiza los links en el trigger; aceptación bloquea/relee el link, sin leer
Cliente bajo tenant personal. Si la baja confirma primero, el link ya está
revocado. Si aceptación tiene el bloqueo primero, puede confirmar; la baja
espera y revoca antes de confirmar. No queda un vínculo activo creado después
de una baja ya confirmada. El estado pending certificado al emitir no sobrevive
a una baja confirmada. Las pruebas deben verificar ambas intercalaciones con
SQL real, incluyendo UPDATE directo y rollback de la baja.

Orden propuesto por decisión de coordinación: **todos** los Usuario requeridos
en orden total ascendente de Usuario.id, sin partición por rol (gym del recurso,
actor, destinatario y padres profesionales necesarios), con NOWAIT en cada uno;
luego Cliente en operaciones gym; link; invitación si se modifica; Plan al
publicar; **StoredObject exacto**; publication. No bloquear publication antes
de Plan/StoredObject al publicar o reemplazar. Releer identidad y asociaciones
después de los locks; si cambió el conjunto de padres/roles, abortar la TX,
nunca adquirir un propietario nuevo fuera de orden ni cambiar el tenant.
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
Se prohíben transacciones anidadas/savepoints y recuperación parcial en este
servicio: después de cualquier error, rollback completo y error visible. El
proof no se retira antes del commit dueño ni antes de sus guards diferidos.

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
únicamente ese descriptor **después de bloquear y releer Plan y StoredObject**.
El BEFORE INSERT repite la validación exacta y locks en orden canónico, incluso
para INSERT directo: FK gym/object sola no prueba Plan.pdf_object_id. Un ref
presente inválido impide publicar: no se
omite ni sustituye. Si sólo hay una ruta PDF legacy, no se copia/publica por
heurística: podrá proponerse menú válido con PDF no disponible y motivo
`legacy_requires_review`, o requerir migración legacy explícita antes de
publicar PDF. Esta elección de presentación requiere aprobación; ningún caso
abre la ruta antigua al socio. Nuevos planes canónicos conservan PDF exacto.

La descarga nueva recibe **link_id y publication_id**, nunca object_id, key,
path, gym_id o un Plan arbitrario. Bajo user.id bloquea/revalida el link y la
publicación exactos, con filtro SQL `link.user_id=actor.id AND status='active'`
también para OWNER externo y con políticas de lock-only de sección13;
construye el ObjectDescriptor exclusivamente desde esa
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
| GET `/api/usuario/vinculos` | Sólo vínculos active con user_id igual a actor.id, paginación keyset, máximo100 por página. Contextos explícitos y capabilities; sin adoptar otro Cliente. |
| GET `/api/usuario/vinculos/{link_id}/plan` | Publicación vigente o `publication:null` si todavía no se publicó. Sólo link activo propio. |
| GET `/api/usuario/vinculos/{link_id}/publicaciones/{publication_id}/pdf` | PDF privado exacto;404 uniforme para ajeno/retirado/inaccesible. |
| DELETE `/api/usuario/vinculos/{link_id}` | Filtrar titular exacto+active antes de mutar; versión esperada; revoca sólo esta relación. Respuesta sin DTO de cartera/publicación, sesiones/diario/perfil conservados. Ya revocado/ajeno404 uniforme. |

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
La sección nueva se ejecuta independientemente y antes del early return de las
seis personales: OWNER canónico puede exportar metadatos mínimos de sus links
active con user_id propio sin obtener su cartera. No devolver invitaciones,
hashes, descriptores, bytes ni registros de otros destinatarios de su gym.
La extensión de frontend/export es una integración posterior explícita; no se
afirma implementada ni se declara completo el piloto por este documento.

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
comparándose mediante sus vocabularios previos. SQLite necesita invalidadores
e inmutabilidad equivalentes y la FK diferida de aceptación, con
foreign_key_check tras batch, sin bajar FK silenciosamente. No se le atribuye
RLS/GUC de PostgreSQL ni una barrera productiva equivalente: producción sigue
rechazando SQLite. El guard diferido adicional de proof al commit es de PG.

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
| Dos gyms y perfiles | A/B con clientes/plans/objetos distintos; profesional de B con cuenta personal vinculada A ve sólo proyección A y su propio diario, no cartera A ni cliente B ajeno. OWNER legítimo A acepta vínculo externo B; endpoints de socio NO muestran vínculos/publicaciones profesionales de A dirigidos a otros. OWNER/tipoUsuario ambiguo sigue denegado. UI gym/client/header no cambia autoridad. Rol/equipo no se añaden. |
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

## 13. Resolución focal de las cuatro objeciones de seguridad

Esta sección concreta el protocolo de v2. No contiene DDL aplicado ni resultados
PostgreSQL. La semántica documentada distingue USING para bloquear filas de
WITH CHECK para escribirlas; también exige SELECT para RETURNING. Por eso v1
era insuficiente al dejar UPDATE exclusivo del gym sin separar locks.
[CREATE POLICY, PostgreSQL17](https://www.postgresql.org/docs/17/sql-createpolicy.html).

### 13.1 Predicados cerrados y bloqueo de lectura sin DML de destinatario

Notación para expandir en SQL fijo revisado, no funciones de acceso global:

- `T`: current_tenant no vacío; debe coincidir con el actor HTTP verificado en
  rutas de socio. `H`: digest de propósito29 instalado LOCAL en esa TX.
- `A(T)`: Usuario persistido activo/no borrado, rol y contexto válidos según
  sección3, sin invitación profesional pendiente. El servicio compara además
  SV del bearer capturado contra la fila bloqueada; RLS no sustituye ese control.
- `G(r)`: r.gym_id=T y propietario gym persistido canónico/activo/no borrado.
  Un miembro profesional trabaja bajo el gym persistido con RBAC de servicio;
  este predicado no afirma identificar a ese miembro mediante T.
- `E(i)`: A(T), H no vacío, i.token_hash=H, i.recipient_email igual al correo
  canónico persistido del actor; si i.status=consumed, también i.consumed_by=T.
  **E no depende de expiry ni se limita a pending.** Sirve para inspeccionar
  estado al destinatario probado y para conservar visibilidad tras consumo.
- `C(i)`: E(i), estado consumed, consumed_by=T y consumed_at noNULL/menor que
  expires_at. El trigger fija consumed_at con reloj posterior al lock; C no
  autoriza transiciones por sí solo ni comprueba que el commit sea anterior
  al vencimiento.
- `P(l)`: A(T), l.user_id=T y l.status=active. En el reader también se exige
  propietario del gym vigente. `R(p)`: p.status=published y existe el link exacto
  con mismo gym/client y P(l). Las políticas de publication sólo dependen de
  links; nunca de Cliente/Plan/StoredObject.

No se usa una política ALL en las nuevas familias. Para publications:

| Operación/política | USING | WITH CHECK |
|---|---|---|
| SELECT | G(p) OR R(p) | No aplica |
| INSERT profesional | No aplica | G(p), más guard de origen del BEFORE INSERT |
| UPDATE profesional | G(p) | G(p) |
| UPDATE lock-only de destinatario | R(p) | **false**, explícito, sin heredar USING |
| DELETE ordinario | false | No aplica |

El reader consulta link.user_id=actor.id, link.status=active, publication.link_id
y publication.id/status exactos **aunque G sea true**. Bloquea Link primero,
publication después, mediante FOR SHARE; ambos tienen SELECT y UPDATE-USING
acotados. El socio no necesita un UPDATE de negocio para adquirir el lock.
El mecanismo sigue pendiente de verificar contra PG17 real: el caso positivo
de lock debe devolver1 fila y los UPDATE de negocio deben fallar/retornar0 sin
modificar nada. No se cambiará WITH CHECK a true para hacer pasar el positivo.

Las políticas permisivas se combinan por OR. Por ello WITH CHECK false del
reader no reemplaza los guards de inmutabilidad: mover gym_id/link/origen a un
valor propio para satisfacer la otra política debe fallar en BEFORE UPDATE.
No-op UPDATE, contenido, estado, versión y descriptor de una publicación de
gym ajeno siguen prohibidos al destinatario. Un OWNER conserva, por separado,
su autoridad profesional legítima sobre filas de su propio gym; eso no hace
válido su acceso como destinatario a los links de otras cuentas.

### 13.2 Consumo único: imágenes de fila y visibilidad durante la TX

Políticas de invitation sin lectura de links; así el grafo RLS permanece
links→invitations→Usuario, sin un camino inverso:

| Invitation | USING | WITH CHECK / guard |
|---|---|---|
| SELECT | G(i) OR E(i), para pending/consumed/revoked | No depende de expiry actual |
| UPDATE | G(i) OR E(i) | Rama gym sólo pending/revoked con consumed_by y consumed_at NULL; rama receptor sólo C(i). BEFORE UPDATE restringe transiciones OLD→NEW aun si G pasa. |
| INSERT | No aplica | G(i), pending y campos de consumo NULL; destinatario/link/hash/expiry coherentes |
| DELETE | false | Ningún borrado ordinario |

Para Link, la rama SELECT/UPDATE-USING de pending admite la invitación exacta
con E tanto pending como **recién consumed por el mismo actor**; no pregunta
sólo si la invitación sigue pendiente. Link SELECT también admite G o user_id
propio. WITH CHECK de primera activación exige NEW.user_id=T, accepted_at igual
a consumed_at y la invitación exacta C (mismos link/gym/client), además de
campos inmutables. La rama profesional no puede activar ni reasignar user_id:
el guard OLD/NEW exige C en **toda** pending→active, aunque G sea true. Sólo
revocar es un cambio posterior permitido al titular; revocado nunca se reactiva.

Secuencia única, con Session/commit propiedad del servicio y sin savepoint:

| Paso | Invitación visible | Link visible | Resultado requerido |
|---|---|---|---|
| 0. Auth, proof, locks Usuario→Link→Invitation, reload | pending, consumed_by=NULL, E true | pending, user_id=NULL, vía E | Verificar SV, origen, versión, destinatario y disponibilidad antes de tocar estado |
| 1. UPDATE Invitation WHERE pending/hash/version | NEW consumed, consumed_by=T, consumed_at fijado por trigger | Aún pending; E de la invitación consumed sigue siendo true | RETURNING devuelve exactamente1 fila; no desaparece por SELECT ni WITH CHECK |
| 2. UPDATE Link WHERE pending/user NULL/version | consumed exacta, visible bajo E/C | NEW active, user_id=T, accepted_at igual al returned consumed_at | RETURNING exactamente1 fila; no puede usar el consumed_by de otro actor |
| 3. Commit dueño | consumed | active propio, o revocado conservando aceptación si hubo revocación explícita dentro de la misma TX | FK diferida y guards diferidos válidos; ningún estado parcial confirmado |

En pasos1/2,0 filas o error aborta la TX completa. Un replay, un hash de otro
propósito o un resend que ganó el CAS no adopta el link de una lectura anterior.
El servicio no acepta Usuario/cliente/gym/consumed_at desde el navegador.

Guard de toda transición a consumed, incluso SQL directo profesional: OLD debe
ser pending y NEW conservar link/gym/client/recipient/hash; E debe ser válido y
consumed_by=T. **El trigger siempre lo exige, sin excepción por G.** Después
del lock usa clock_timestamp convertido a UTC y comprueba expiry estrictamente
posterior; fija consumed_at él mismo. Un consumed_at provisto por SQL/HTTP no
puede retrofechar la decisión. No usar now()/CURRENT_TIMESTAMP de inicio de TX
ni un statement_timestamp previo a esperar el lock.

El corte temporal es la decisión de consumo después del lock. Una decisión
válida puede confirmar después de expires_at. El guard diferido verifica la
procedencia/igualdad de consumed_at, sin convertir la demora del commit en una
regla de vencimiento nueva. Info puede describir expired/consumed sólo después
de E; inspección no consume ni autoriza un consumo vencido.

Defensa de estado final, adicional a los dos UPDATE del servicio:

1. UNIQUE Link(id,gym_id,client_id,user_id), con user NULL obligatorio en pending.
2. FK Invitation(link_id,gym_id,client_id,consumed_by)→esa clave Link,
   **NO ACTION DEFERRABLE INITIALLY DEFERRED**; consumed exige consumed_by
   noNULL. Un consumed con link pending/user NULL no puede confirmar. Esta FK
   adicional no cambia los RESTRICT de entidades/objetos.
3. BEFORE Link pending→active exige invitación consumed exacta y mismo actor;
   campos aceptados/identidades son inmutables después. Invitation consumed es
   terminal e inmutable y no puede borrarse ordinariamente. Así una posterior
   revocación conserva el testigo; no puede dejar link activo sin su invitación.
4. PG añade guards diferidos en consumo/primera activación: comprueban filas
   actuales, misma asociación/usuario/accepted_at, y proof E/C de esta TX. Fila
   no visible/ausente se trata como fallo, nunca como comprobación omitida.
   active o revoked con aceptación conservada satisface el testigo; pending no.
5. H sigue válido hasta terminar commit y sus guards. No se limpia al salir de
   un bloque anterior al commit; commit/rollback lo retira y la siguiente TX
   vuelve a instalar vacío. Revocaciones futuras no registran un nuevo evento
   de consumo ni necesitan un token viejo: inmutabilidad+FK preservan el enlace.

SQLite reproduce la FK diferida y los guards de asociación/inmutabilidad;
no se le atribuye proof RLS/GUC ni guard PG de commit. Sus pruebas de servicio
verifican auth/token; la barrera SQL de producción se ensaya en PostgreSQL.
Ni runtime ni código migrador autorizado deshabilitan FK/triggers para pasar.

SET LOCAL también puede perderse al volver a un savepoint anterior. Por eso el
servicio posee una TX raíz nueva, rechaza nesting, y cualquier error obliga a
rollback completo sin retry parcial. PG debe demostrar además que retirar H o
rollback a un savepoint previo al proof impide confirmar consumo/activación.
[SET, PostgreSQL17](https://www.postgresql.org/docs/17/sql-set.html).

### 13.3 Lock de StoredObject, origen exacto e intercalaciones de publicación

El grafo completo es Usuario (ID total, NOWAIT)→Cliente→Link→Invitation cuando
corresponda→Plan fuente→StoredObject fuente→Publication. Adquirir en sentencias
separadas, no confiar en el orden de locks de un JOIN. Publisher y BEFORE INSERT
siguen ese orden. El trigger vuelve a validar aun si el servicio precargó filas;
ningún atributo de un objeto sin lock alimenta el INSERT final.

Con Plan bloqueado/releído, tomar exclusivamente Plan.pdf_object_id. Si noNULL,
bloquear/releer StoredObject por (gym_id,id) y exigir ready, kind plan_pdf,
backend configurado, content_type PDF y **todo** el descriptor exacto:
id/owner/key/content_type/byte_size/sha256/backend. Compararlo con NEW; no copiar
valores que UI o una lectura anterior sugirió. Object id NULL sólo es válido
cuando la fuente Plan carece realmente de ref; no sirve para ocultar un ref
presente inválido. La FK gym/object es necesaria, pero no suficiente.

INSERT directo con PlanA y PDF de otro Plan/Cliente del mismo gym debe fallar
antes de persistir: AFTER/FK de mismo gym no basta para ese caso. Tampoco valen
descriptor alterado de ese mismo objeto, pending, tipo distinto o backend
distinto. El guard sólo lee fuentes bajo gym autorizado durante INSERT; los
invalidadores nunca vuelven a adquirir Plan/Link/Cliente desde Publication.

| Intercalación | Locks y resultado exigido en prueba real |
|---|---|
| Mutador gana primero | Publicador espera/toma Plan/StoredObject después, relee su estado actual y rechaza ready/backend/origen inválido. No puede INSERTar el descriptor precargado que ya fue invalidado. Si el estado nuevo fuese válido, sólo podrá usar el nuevo snapshot coherente, nunca el anterior. |
| Publicador gana primero | Mantiene Plan y StoredObject hasta INSERT+commit. Mutador espera el lock de fuente; al continuar ejecuta invalidación en una sentencia nueva que debe alcanzar la publicación recién confirmada. Después de su commit no queda R(p) legible. Rollback del mutador conserva la publicación. |

Un reader PDF sólo toma Usuario→Link→Publication bajo user.id; nunca vuelve a
Plan/StoredObject. Sus locks FOR SHARE sobre link/publication duran la lectura
acotada. Un invalidador mantiene la fuente→Publication; no pide Link ni Usuario
desde esa publication. La baja de Cliente toma Cliente→Link→Invitation→Publication,
sin volver a tomar Usuario. Estas direcciones evitan introducir el ciclo
Publication→StoredObject frente al mutador StoredObject→Publication.

Deleted_at de fuente se diferencia de DELETE físico: soft-delete retira/revoca
en la TX; con refs RESTRICT el DELETE físico se rechaza entero. No afirmar que
el DELETE confirmó dejando sólo snapshots. El documento/descriptor del socio
jamás habilita el router profesional o una descarga genérica de StoredObject.

### 13.4 Precondición MVCC explícita y compatibilidad a comprobar

La invalidación posterior a un lock debe observar publicaciones confirmadas
mientras esperaba. El protocolo exige **READ COMMITTED** en mutaciones R12 y
en cambios invalidantes de fuentes. El guard no puede depender de
EXISTS(publication), porque un snapshot anterior podría ocultar precisamente
la publicación nueva. Funciones invoker de invalidación serán VOLATILE y harán
la invalidación después del lock en una sentencia nueva; no se afirma que esa
declaración supere un snapshot REPEATABLE READ. La semántica de snapshots de
funciones fundamenta esta precondición, no sustituye el canario concurrente.
[Volatilidad, PostgreSQL17](https://www.postgresql.org/docs/17/xfunc-volatility.html).

El guard debe rechazar incondicionalmente aislamiento distinto de RC cuando
ocurra uno de estos cambios, incluso si no ve filas R12 en ese snapshot:

- Cliente: activo pasa a false, deleted_at pasa a noNULL o identidad cambia.
- Plan: cambio real de cualquier columna de negocio/identidad/deleted_at de la
  fila fuente, no un UPDATE sin cambio de valores.
- StoredObject: cambio de id/gym/kind/key/content_type/byte_size/sha256/backend/status;
  no sólo de created_at/updated_at.

No bloquear SELECT, inventario legacy RR READ ONLY, UPDATE de contadores o
ultimo_plan de Cliente, ni no-ops. La precondición **sí restringe** esos cambios
invalidantes bajo RR/SERIALIZABLE aun sin vínculos visibles; no se presenta como
sin impacto universal. engine.init_db hereda aislamiento del servidor/rol; por
eso la aceptación29 necesita observar el modo real sin credenciales, comprobar
RC en conexiones runtime y ensayar flujos actuales. No se cambia silenciosamente
la configuración de servidor ni se reinterpreta un snapshot histórico.

R12 verifica el aislamiento después de begin y antes de efectos; otro modo
produce503 `member_isolation_unavailable`. Guards de fuente rechazan el cambio
incompatible; la ruta sanea el error. Antes de aceptar29 debe quedar demostrado
que flujos actuales de mutación operan RC y que la herramienta de inventario
RR READ ONLY conserva su contrato. Esta compatibilidad y el alcance del guard
requieren aprobación root/seguridad y ejecución real; hoy son propuesta.

### 13.5 Usuario global, R11 legacy y autorización OWNER por endpoint

Todo Usuario requerido se determina antes de los locks: recurso, actor,
destinatario, padres persistidos de team y OWNER legítimos correspondientes.
Deduplicar IDs y bloquear en orden total Usuario.id ascendente, **NOWAIT en
todos**. Releer rol/team/activo/deleted/SV y verificar que el conjunto no cambió;
si cambió, rollback completo/conflicto. No adquirir un User nuevo una vez
empezados Cliente/Link/Plan/objeto/publication. Nada de ordenar owners primero.

NOWAIT es parte del protocolo compatible con R11 existente, que toma gym
Usuario→Subscription→target Usuario y no siempre sigue ID. R12 no esperará
por ese User posterior reteniendo otro: contención produce rollback íntegro
y409 `member_operation_busy`, sin reintento parcial interno ni detalles SQL.
Reset/logout conservan User→Refresh, que R12 no invierte ni escribe. Lecturas
pueden usar FOR SHARE NOWAIT y mutaciones FOR UPDATE NOWAIT para User;
la elección exacta debe demostrar bloqueo de SV/roles en PG. Los locks de
recursos posteriores pueden esperar, pero nunca vuelven a pedir un User.

Owner-A y Owner-B aceptando invitaciones cruzadas adquieren exactamente los
mismos User en el mismo orden; no B→A versus A→B. Prueba adicional retiene
realmente R11 gym→Subscription→target mientras R12 obtuvo primero un target de
ID menor: R12 debe devolver conflicto y liberar, no esperar formando ciclo.
No se afirma que el código legacy se haya armonizado o que ya pasaran canarios.

Autorización que cada servicio/ruta debe repetir además de RLS:

| Endpoint de socio | Predicado obligatorio antes de DTO/efecto |
|---|---|
| List links, plan, PDF y sección R12 de export | Link.user_id=actor.id y status=active; publication exacta+published cuando aplica; actor persistido/SV actuales. No aceptar G como alternativa. |
| Revoke propio | Link.user_id=actor.id y active, versión; respuesta sin DTO de cartera. Revocado o ajeno404 uniforme. |
| Info/aceptación pending | Hash de propósito+email canónico persistido+actor elegible explícitos; nunca basta G. Link.id/gym/client derivan de esa invitación validada, no de UI. |
| Resultado de aceptación | Tras CAS/RETURNING, Link.user_id=actor.id y active; no readback por mero link_id visible al gym. |

Canario mínimo: OWNER-A recibe/acepta B conservando identidad profesional A.
List/plan/PDF/revoke/export como socio no pueden devolver publicaciones/links de
A dirigidos a cuentas C/D aunque RLS G los deje ver como profesional. Añadir
OWNER propio con prueba completa positiva y negativas sin token/correo/actor;
tipoUsuario/OWNER ambiguo permanece review. No cambiar rol ni adoptar Cliente
personal para hacer pasar ninguno de los casos.

Si entra export R12, su sección propia se calcula con ese filtro **antes o de
forma independiente** del early return personal=false. Las seis personales
permanecen vacías/excluidas para OWNER según contrato anterior. Que posea un
vínculo no vuelve verdadero personal_space_supported ni incluye su cartera.

### 13.6 Pruebas focales nuevas obligatorias, todas pendientes

1. SELECT FOR SHARE y FOR UPDATE de destinatario legítimo obtienen1 publicación;
   UPDATE no-op/estado/versión/JSON/descriptor y DELETE no cambian nada. Mover
   gym/link/source para satisfacer la política profesional falla por guard.
2. RETURNING real devuelve1 invitación consumed y1 link active en esa secuencia;
   SELECT de ambas imágenes funciona en la misma TX y RLS sigue acíclico.
3. SQL directo gym→consumed en nombre de otro, sin proof o con propósito/hash
   incorrectos, falla aunque G=true. Ningún fake consumed_at retrofecha expiry.
4. Entre ambos UPDATE: excepción, rollback,0 filas, cambio de versión y fallo
   de commit; nunca consumed+pending ni active con otra cuenta confirmado.
5. FK diferida detecta consumed+user NULL/pending; guards rechazan active sin
   consumed exacto. Retirar GUC antes del commit o volver a savepoint previo
   falla cerrado; futuras revocaciones sin bearer conservan el testigo.
6. Token vence mientras espera lock: consume denegado. Consumo autorizado antes
   de expiry y commit después puede confirmar sin inventar una segunda fecha.
7. SourceObject mutador-primero y publicador-primero con procesos/locks reales,
   descriptor reloaded y visibilidad de nueva publicación en el invalidador;
   UPDATE rollback conserva la asociación. Repetir cambio Plan fuente.
8. INSERT directo PlanA+objeto de otro Plan/Cliente del mismo gym; mismo objeto
   con descriptor falso; NULL para omitir un ref presente: todos rechazados.
9. Source invalidation bajo RR/SERIALIZABLE, incluso snapshot anterior sin
   publicación visible: rechazo. RC positivo y RR READ ONLY de inventario
   positivo; no-op/counters no disparan el guard. Sin claims de aislamiento OS.
10. OWNER-A↔OWNER-B, OWNER propio, R11 con orden legacy retenido, reset/logout:
    éxito o conflicto visible acotado, jamás deadlock ni par de derechos obsoleto.
11. OWNER-A miembro B contra links de otros destinatarios de A: negativa en cada
    endpoint/DTO/PDF/revoke/export; lectura profesional de A conserva sus reglas.
12. Soft-delete retira/revoca; DELETE físico RESTRICT rechaza entero. Restore29
    conserva policies/funciones/triggers/FK diferida y demuestra las lecturas
    posteriores; ningún test histórico28 se regenera o declara green por lectura.

Estas pruebas constituyen los primeros probes DB que se ejecutarán durante la
fase de implementación/constraints, sólo después de aprobar v2. No se ejecutó
ninguno en la elaboración de este documento.

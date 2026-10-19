# R12 API: contrato de consumidor v1

Adenda de implementación al contrato v2 RAW3c28ccd2. El núcleo29 está en
ad712416; todavía no tiene aceptación independiente ni integración MAIN. Las
rutas siguientes ya se ejercitaron en ambas factories con migraciones reales
SQLite/PostgreSQL y autenticación real. Correo: doble local, sin entrega real.
No autoriza a montar una UI contra un servicio WIP sin su freeze posterior.

Todas las rutas requieren sesión vigente. El backend relee actor, SV, rol y
pertenencia; no toma gym/user/role/email autenticado desde el cuerpo ni amplía
el espacio personal. OWNER profesional canónico puede ser destinatario de su
propio gym u otro. OWNER tipo usuario ambiguo:409
`member_context_requires_review`. No adoptar perfil ni cambiar generación.

## Profesional

Base: `/api/clientes/{client_id}/vinculacion`. client_id pertenece al gym
persistido del profesional. IDs link/invitation/publication son UUID36 opacos.
Se conservan exactamente las versiones devueltas, sin sumarlas en el cliente.

- POST `/invitaciones`: `{recipient_email,request_key}`. request_key ASCII
  1..128 `[A-Za-z0-9_.:-]`; una clave nueva por intención. Reintento exacto
  recupera el estado y no reenvía; payload distinto con misma clave:409
  `member_request_key_conflict`. Antes de registro es válido invitar un correo.
- POST `/invitaciones/{invitation_id}/reenviar`: `{expected_version}` de la
  invitación. Sólo pending (incluye expiradas); rota bearer/expiry, misma
  dirección; no cambiar destinatario desde este formulario.
- DELETE `/{link_id}`: JSON `{expected_version}` del link. Revoca la relación;
  conserva identidad, equipo, SV, diario, planes y datos personales.
- POST `/{link_id}/publicaciones`: `{plan_id,expected_link_version,
  expected_publication_version}`. La última es0 si no hay publicación vigente,
  o su `publication.version`. Fuente siempre Plan del mismo cliente/gym.
- DELETE `/{link_id}/publicaciones/{publication_id}`: JSON
  `{expected_version}` de publicación. Retira, no borra fuente/bytes.
- GET base: `?limit=100&after=<linkUUID>`; limit1..100; cursor opaco validado
  UUID, nunca offset. Leer `next_after:null` como fin. Una sola consulta JOIN
  para los registros y su invitación/publicación vigente, sin N+1.

Issue/reenvío devuelven202 con esta forma (la invitación y el link tienen
versiones independientes):

```json
{"invitation_id":"<uuid>","link_id":"<uuid>","status":"pending","link_status":"pending","version":1,"link_version":1,"expires_at":"2026-10-26T18:00:00+00:00","delivery_status":"not_confirmed"}
```

No token/hash/URL/correo/recipient_user_id en respuesta, errores o auditoría.
La aceptación por SDK no acredita entrega y la cola del proceso no es durable.
La metadata pending se confirma antes de admitir el trabajo de correo. Un
resultado incierto no reenvía ni rota automáticamente: consultar estado.

GET estado profesional:

```json
{"client_id":"<client>","capabilities":{"issue_invitation":true,"rotate_invitation":true,"revoke_link":true,"publish_plan":true,"withdraw_publication":true},"items":[{"link_id":"<uuid>","status":"active","version":2,"accepted_at":"2026-10-19T18:00:00+00:00","revoked_at":null,"invitation_id":"<uuid>","invitation_status":"consumed","invitation_version":2,"expires_at":"2026-10-26T18:00:00+00:00","publication":{"id":"<uuid>","version":1,"source_plan_id":41,"published_at":"2026-10-19T18:00:00+00:00","download_published_pdf":true}}],"next_after":null}
```

`invitation_status` es pending/expired/consumed/revoked, calculado con reloj
servidor; link status es pending/active/revoked. publication puede ser null.
Capabilities son límites de autoridad/cliente activo, no garantía de que el
recurso siga vigente al hacer clic. OWNER/ADMIN emiten/rotan/revocan;
OWNER/ADMIN/NUTRIOLOGO leen estado/publican/retiran. VIEWER no obtiene esos
permisos. La UI usa capabilities; no se añaden permisos de cartera a auth/me.

Publicar devuelve200:

```json
{"publication_id":"<uuid>","version":1,"link_id":"<uuid>","link_version":2,"source_plan_id":41,"published_at":"2026-10-19T18:00:00+00:00","download_published_pdf":true}
```

Con menú legacy válido sin objectref: false y
`pdf_unavailable_reason:"legacy_requires_review"`. Ref presente inválida:
rechazo íntegro409 `member_source_unavailable`; nunca fallback legacy.
Retirar devuelve `{publication_id,status:"withdrawn",version}`. Revocar
devuelve `{link_id,status:"revoked",version}`.

## Destinatario

Página de UI: `/auth/accept-client-link#token=<43 ASCII>`. Bootstrap nonce
first-party al principio del head retira fragmento antes de scripts/CSS; token
sólo memoria, sin Storage/logs/DOM serializado ni query/return_to. Usuario nuevo
puede registrarse normalmente y volver al mismo enlace del correo. No se
demuestra email_verified general, sólo esta relación/propósito.

- POST `/api/usuario/vinculaciones/invitacion`: `{token}`. GET no consume.
  Token+sesión+correo persistido exacto antes de mostrar contexto.
- POST `/api/usuario/vinculaciones/aceptar`:
  `{token,expected_version,confirm:true}`. expected_version de invitación.
  confirm:false, campos extra/IDs/roles:422. No autologin ni nueva sesión.
- GET `/api/usuario/vinculos`: `limit`1..100/`after`linkUUID, items/next_after.
- GET `/api/usuario/vinculos/{link_id}/plan`: publicación vigente o null.
- GET `/api/usuario/vinculos/{link_id}/publicaciones/{publication_id}/pdf`:
  bytes application/pdf exactos de esa capacidad. Tras retirada/reemplazo404;
  nunca descarga el nuevo plan silenciosamente.
- DELETE `/api/usuario/vinculos/{link_id}`: JSON `{expected_version}` de link.
  Sólo relación active propia. Funciona aunque fuente owner esté inactivo;
  esto no habilita lectura/publicación. Ajeno/ya revocado404 uniforme.

Info:

```json
{"status":"pending","version":1,"expires_at":"2026-10-26T18:00:00+00:00","link_id":"<uuid>","context":{"kind":"gym_member","gym_name":"Gym sintético","client_display_name":"Socio sintético"},"can_accept":true}
```

Accept200:

```json
{"link_id":"<uuid>","status":"active","version":2,"context":{"kind":"gym_member","gym_name":"Gym sintético","client_display_name":"Socio sintético"}}
```

Lista:

```json
{"items":[{"context":{"kind":"gym_member","link_id":"<uuid>","gym_name":"Gym sintético","client_display_name":"Socio sintético"},"link_id":"<uuid>","status":"active","version":2,"capabilities":{"read_published_plan":true,"revoke_link":true,"share_personal_diary":false,"read_shared_progress":false,"manage_clients":false,"manage_team":false}}],"next_after":null}
```

Sólo links active del actor exacto y fuente elegible en la lista de lectura;
si fuente owner deja de ser elegible, no se muestra menú ni se concede otra
cartera. Un link conocido puede retirarse con DELETE propio/version. No se
promete listar contextos suspendidos ni recuperarlos desde almacenamiento UI.

Reader200 conserva la forma de ejemplo completo de v2: context, link
`{status,version}`, capabilities, publication. Publication:
`{id,version,source_plan_id,published_at,plan_schema_version:1,plan,meta,pdf_url}`.
plan son las cuatro comidas conocidas; meta contiene exactamente tmb,
get_total,kcal_objetivo,kcal_real,proteina_g,carbs_g,grasa_g,objetivo,
nivel_actividad,tipo_plan; null conserva ausencia, no inventa cero. Comidas
fijas/opciones mantienen la forma persistida saneada, sin notas ni paths.
publication:null no fabrica menú. PDF ausente añade motivo legacy; capability
download false. `share_personal_diary` y `read_shared_progress` siempre false.

## Fronteras y errores

JSON16KiB leído por stream antes del parser; extra/duplicados/NaN/tipos inválidos
se rechazan íntegros. Response512KiB; fuente/proyección256KiB y límites de
estructura publicados en el contrato canónico. DELETE también usa JSON.
Todas las respuestas de paths exactos, incluso405/404/429, no-store y
no-referrer. La página accept tiene CSP fija first-party con nonce; no confía
en CSP arbitraria del handler ni habilita terceros.

Errores `detail:{code,message}`:401 identidad,403 permiso/contexto,404
member_link_unavailable/member_invitation_unavailable/member_publication_unavailable,
409 member_version_conflict/member_request_key_conflict/member_link_conflict/
member_context_changed/member_context_requires_review/member_state_requires_review/
member_version_overflow/member_operation_busy/member_source_unavailable/
member_publication_requires_review/member_invitation_consumed;
410 member_invitation_expired;413 member_body_limit/member_response_limit;
415/422 member_invalid_input;429 member_rate_limited;503 member_mail_unavailable/
member_service_unavailable/member_isolation_unavailable/member_transaction_unavailable/
member_link_reconciliation_required. Expired/consumed sólo tras prueba exacta.
Errores auth/limiter existentes pueden tener su formato previo: no inferir
éxito, CAS o destinatario de un status genérico.

Cuotas técnicas por900s (IP y actor HMAC): issue/resend10, inspect60, accept20,
revoke30, publish/withdraw60, read240. Issue también recipient HMAC5; proof
HMAC30 inspect/10accept. Fallo Redis sensible503; producción sin Redis no
ejecuta operación. Ninguna key contiene bearer/correo/ID en claro.

Export servidor añade `member_links:{records,next_after}` con cursor query
`after_member_link` UUID y presupuesto propio131072 bytes dentro del total de
siete conjuntos. Sólo metadata de links active propios y publicación vigente,
sin invitación/hash/descriptor/bytes/cartera; sección independiente antes de
la barrera personal OWNER intacta. Integración del controlador UI de export
queda explícita para su propia tarea, no se simula completada aquí.

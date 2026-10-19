# R12 API: delta de observación exacta y exportación de vínculos

Esta adenda conserva íntegro el contrato de consumidor v1
`backend-r12-api-contract-v1.md`, RAW SHA256
`407eedd99955b33d8d267ac8421b1cac4ad674f65c38f0c12afca1dd9617499a`.
No cambia el núcleo SQL, el esquema29, los targets históricos ni la autoridad
de destinatario. Describe el contrato final del consumidor antes de su ensayo
HTTP independiente; los resultados del autor no son aceptación independiente.

## Publicación: identidad y versión observadas

POST `/api/clientes/{client_id}/vinculacion/{link_id}/publicaciones` requiere
los cuatro campos, sin otros campos:

```json
{"plan_id":41,"expected_link_version":2,"expected_publication_id":null,"expected_publication_version":0}
```

Este cuerpo sólo crea cuando no hay publicación vigente. Para reemplazar,
la UI conserva el ID y la versión de la publicación que leyó:

```json
{"plan_id":42,"expected_link_version":2,"expected_publication_id":"a0000000-0000-0000-0000-000000000001","expected_publication_version":1}
```

`expected_publication_id` es obligatorio, aun cuando sea null. Null exige
versión0; una identidad exige versión1..2147483647 y UUID36 ASCII minúsculo
con la forma canónica de los IDs devueltos. Omisión, booleanos, coerciones,
UUID inválido o pares mixtos se rechazan íntegros con422
`member_invalid_input`. El cuerpo antiguo de tres campos ya no es válido.

El servicio bloquea el recurso vigente y compara ambos valores antes de
retirarlo o insertar otro. Una foto vieja devuelve409
`member_version_conflict`, aunque ambas publicaciones tengan versión1.
El conflicto no retira ni sustituye la publicación actual. Cada publicación
nueva conserva ID nuevo y versión1; la retirada incrementa la versión de
esa fila histórica. No se inventa una secuencia global ni se cambia el core.

Tras503 de commit incierto, no asumir ausencia ni sustituir el ID observado
por uno obtenido silenciosamente. Consultar el estado autorizado, mostrar la
foto actual y pedir una nueva intención de reemplazo con ese ID y versión.
Un reintento basado en ausencia anterior o en el ID ya retirado devuelve409.
La descarga de una publicación retirada nunca sirve el PDF nuevo.

## Exportación: séptimo conjunto independiente

GET `/api/usuario/privacidad/exportar` mantiene los seis conjuntos personales
y añade siempre:

```json
{"member_links":{"records":[{"id":"a0000000-0000-0000-0000-000000000001","status":"active","version":2,"gym_name":"Gym sintético","client_display_name":"Socio sintético","accepted_at":"2026-10-19T18:00:00+00:00","publication":{"id":"b0000000-0000-0000-0000-000000000002","version":1,"published_at":"2026-10-19T18:05:00+00:00"}}],"next_after":null}}
```

`publication` también puede ser null. `id` del registro identifica el link.
El cursor query es `after_member_link=<UUID36>`; orden ascendente por ID,
keyset y límite existente1..200, sin offset ni cursor compartido con los otros
seis conjuntos. `next_after:null` indica fin. Las páginas son lecturas vivas,
no un snapshot inmutable entre solicitudes.

`format_version` permanece1 por adición. El scope declara:

```json
{"coverage":"account_persisted_personal_space_and_active_member_link_metadata","member_links":"active_recipient_metadata_only"}
```

Sólo se exporta metadata de links active dirigidos al actor canónico y cuyo
gym sigue canónico, con publicación vigente si existe. No se incluyen correo
de invitación, token, digest, estado de entrega, descriptor, menú, PDF, cartera
profesional ni datos personales de otro sujeto. La revocación o inelegibilidad
del origen excluyen ese registro de esta sección de lectura; no prometemos
historial de vínculos revocados dentro de este primer contrato.

El conjunto se calcula antes de la barrera personal OWNER y no la amplía.
Un OWNER profesional legítimo puede exportar sus vínculos como destinatario
con `scope.personal_space:false`; los seis conjuntos personales siguen vacíos.
OWNER tipo usuario ambiguo no adquiere cartera ni asociación automática.

Presupuesto UTF8 de cada sección131072 bytes y total933888 bytes
(`7*131072+16384`). Un registro único excesivo produce413 íntegro. Cuando
existe otra página, se devuelve un cursor, sin truncar campos del registro.
El consumidor debe validar siete secciones, cursores y cobertura; una UI que
sólo reconoce seis conjuntos no acredita composición completa de R12/R25.

## Límites preservados

Las páginas y controles UI se revisan en su rama. El API no incorpora páginas
ni almacenamiento del bearer en el navegador. Se conserva la limitación v1:
la lista de lectura sólo muestra fuentes elegibles; un link propio conocido
puede revocarse aunque el owner de origen esté inactivo, sin abrir su menú.
No se promete descubrir contextos suspendidos ni recuperarlos de Storage.
La prueba de correo sigue siendo específica de esta invitación, con transporte
local sintético; aceptación SDK no demuestra entrega real.

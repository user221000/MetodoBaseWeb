# R12 core29: revisión independiente bloqueada sobre ad712416

**Resultado: no aceptar el núcleo29 actual.** Se ejecutaron21 canarios propios contra una migración29 real y rol app restringido:18 verdes,3 rojos,0 errores/skip. Los tres rojos corresponden a dos defectos de predicado/guard; no se afirma una fuga HTTP ni aceptación sin haber poseído el token inicial. QA ejecuta su replay55 y DDL/otros canarios por separado; estas cifras no se suman como cobertura disjunta ni sustituyen la revisión futura de API/PDF/mail/restore.

La copia independiente F:/mb-r12-sec29 permanece en ad71241628021941ed927b066d2d6e8e72ddef2c; no se ejecutó el WT de backend con servicios WIP. Creada con core.autocrlf=false y core.longpaths=true. Se contrastaron ZIP RAW23+freeze y receipt de cada RAW/blob; los dos logs y tres módulos históricos modificados tienen sólo CRLF→LF entre RAW y Git. Las pruebas usan los bytes Git LF, sin atribuir identidad RAW a esos cinco archivos. El archivo exacto del autor permanece conservado. Los96 históricos no modificados coinciden con el contenido Git anterior; los99 originales RAW eran CRLF. Targets22–28/vocabulariosv1 no se editaron.

## Rojos de lectura con OWNER no canónico

Nodes inmutables:

- test_noncanonical_owner_parent_cannot_keep_recipient_publication[resource_owner]
- test_noncanonical_owner_parent_cannot_keep_recipient_publication[actor_parent]

Preparación: emitir, aceptar y publicar una fuente/PDF sintéticos válidos; el destinatario puede leer exactamente1 publicación. Después, mediante la conexión administrativa del fixture, fijar team_gym_id de OWNER-A a OWNER-B. La primera variante prueba un destinatario personal de un recurso de A; la segunda un destinatario profesional cuyo padre es A y cuyo recurso pertenece a B.

En ambos casos r12_canonical_gym(A) devuelve false, pero el rol app del destinatario sigue seleccionando1 publicación. La primera omisión está en r12_recipient: comprueba tipo/role/activo/deleted del dueño sin team_gym_id IS NULL. La segunda está en la rama de parent de r12_actor_valid con la misma omisión. No se cambió role/gym del vínculo, descriptor o fuente. El fallo es del contrato de elegibilidad de lectura en RLS; no se ejercitó una ruta HTTP ni una descarga real.

Corrección que debe revisar el autor: aplicar la misma definición de propietario canónico a los predicados de dueño y padre profesional, sin volver a exigir login elegible para Gscope/invalidation/revoke/withdraw. Los contratos de OWNER propio y externo legítimo deben conservarse.

## Rojo de proof retirado antes de commit para OWNER propio

Node inmutable: test_owner_own_acceptance_commit_requires_current_purpose[empty].

Preparación: OWNER canónico recibe su propia invitación y la consume/activa con el token correcto; antes de commit se fija app.client_invitation_digest vacío. Se esperaba rechazo del commit; éste confirma sin excepción. Los controles [wrong_purpose] y [valid] pasan: un propósito incorrecto falla y uno correcto confirma.

El código del guard diferido usa NOT r12_proof(invitation). Con digest vacío, el predicado de igualdad con NULLIF produce SQL UNKNOWN; NOT UNKNOWN no es true y un IF PL/pgSQL no entra por ese valor. En este recorrido la rama G mantiene visible la invitación, de modo que NOT FOUND tampoco produce rechazo. Ésta es la explicación de código del commit observado. No se afirma que se pudiera crear la aceptación sin proof inicial; se demuestra que el requisito de conservarlo hasta el commit no se impone en este caso.

Corrección que debe revisar el autor: fallo cerrado ante cualquier resultado distinto de true en todos los guards pertinentes, incluidos proof y postimágenes; auditar NULL explícitamente sin aflojar los CHECK/FK ni las políticas. Repetir los mismos nodes y controles sobre un nuevo freeze selectivo core+target29; preservar ad712416 y los RAW rojos.

## Controles propios verdes

- Seis casos de pool1 con valor de propósito session-level residual, mismo backend PID y actor A→B→A→sin contexto: Connection y Session, cada uno tras commit/rollback/error. Sólo hook real del producto; no se añadió el clear_proof extra del helper make_app del autor.
- Dos fallos inyectados al instalar el propósito en begin: la query de negocio no llega a enviarse, tanto Connection como Session.
- Seis variantes de DML tras lectura bloqueada FOR NO KEY UPDATE: no-op, withdraw mediante CTE/RETURNING, metadatos, traslado de gym, traslado de Plan y DELETE. Ninguna modifica la publicación.
- FK diferida forzada IMMEDIATE entre consumed y active:23503, TX abortada25P02 y rollback íntegro a pending/pending.
- Revocación posterior por titular sin bearer previo: conserva recibo consumed/sujeto/accepted_at e impide leer la publicación. Este criterio también fue ejercitado por QA; no se presenta como cobertura disjunta.
- Dos controles de OWNER propio con proof válido o propósito incorrecto, descritos arriba.

El examen estático cubrió las tres familias nuevas, sus claves compuestas y guardas, dominio de token, proyección de cuatro comidas/campos meta, descriptor exacto, RC/invalidation y orden de locks/NOWAIT. Los canarios concurrentes, de descriptor, JSON esperado independiente, OWNER own/external y preservación20→23 están coordinados con QA; no se repitieron sus55. El commit selectivo no contiene servicios/rutas R12: filtros explícitos de usuario por endpoint, cuerpo/headers/mail/ACK y reader PDF completo siguen pendientes de autoría y revisión, sin aceptación inferida.

## Fuentes, datos y reproducción

Driver exacto SHA256 a51dde94ef7e2a7197c063ceb0b37c95d030c6cf05279bc8f3e0b2ad237fffdb. Todas sus aserciones y negativos quedan congelados. Los5 iniciales y16 restantes usaron bases UUID distintas, ambas eliminadas por nombre exacto registrado. No se tocaron DB ajenas, roles del clúster, proveedores, correo real, usuario real ni producto MAIN.

El launcher original está preservado; run_review_source.py es variante de configuración que sólo sustituye la constante WT por R12_REVIEW_SOURCE_ROOT. El driver no cambia. Copiar ambos a Temp con sus nombres originales antes de ejecutarlos; el driver escribe sólo evidencia/registro de su DB en el directorio que lo contiene. Las credenciales loopback se leen sólo en el child desde el JSON privado; no se incluyen en repo, comandos ni salida. El revisor debe elegir un sufijo/directorio nuevo para cada replay, sin sobrescribir resultados.

Los21 resultados originales, XML/log, fotos RAW y Git, mapa privado3342 fuentes y errores de captura están en el ZIP privado referenciado por source.json. Los errores iniciales de captura compararon RAW CRLF con Git LF y un metadato de igualdad fue corregido con preimagen conservada; ocurrieron antes de app/DB. Dos lecturas auxiliares usaron rutas/cwd equivocados y se corrigieron; no son rojos de producto. No se alteraron criterios históricos para corregir esos errores de harness.

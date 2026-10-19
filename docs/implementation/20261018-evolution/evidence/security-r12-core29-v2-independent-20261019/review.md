# R12 core29 V2: aceptación independiente acotada

Se aceptan las correcciones de predicados/NULL del commit1aacbcb5e9d0a1ba0b2a08d5c3650e4bd9ff7ce6 sobre ad712416 para continuar la evolución aislada del núcleo. El mismo driver independiente a51dde94ef7e2a7197c063ceb0b37c95d030c6cf05279bc8f3e0b2ad237fffdb pasa21/21, sin editar aserciones, negativos, fixtures o helpers del driver. Los tres rojos previos se conservan: V1 sigue18 verdes/3 rojos. Esta aceptación no cubre API, reader PDF/HTTP, correo, UI, restore, casts de PostgreSQL, ni integra29 en MAIN.

Se creó una copia nueva F:/mb-r12-s2 con core.autocrlf=false/core.longpaths=true; no se ejecutó el WT del autor con API WIP. Se fotografiaron las3354 fuentes Git y paquetes antes de importar la aplicación/abrir DB y se comparan al cierre. El launcher SOURCE_ROOT2caf371a también permanece exacto; sólo se configuró su raíz para el nuevo checkout.

## Delta revisado

El commit tiene15 paths: producto exclusivamente member_link_policy_v1.py, member_link_projection_v1.py y target PostgreSQL29. Se revisó el diff completo de ambos módulos. Los31 checks negativos de helpers pasan a IS NOT TRUE (12 en guards/policy,19 en proyección). Las salidas scope/proof/pending/consumed/recipient hacen COALESCE(false); EXISTS/FOUND siguen siendo booleanos totales. Los argumentos SQL NULL de JSON/depth/arrays/flags tienen rechazo explícito y require_rc usa IS DISTINCT FROM. No queda NOT public.r12_ en esos módulos. Esto es una auditoría del vocabulario concreto, no una demostración de exhaustividad de todas las entradas o futuras funciones.

El destinatario reutiliza r12_canonical_gym y el padre profesional exige tipo gym/OWNER, team_gym_id NULL, activo, deleted_at NULL e invitation_token NULL. Canonical/lock usan la misma condición. Gscope se mantiene como propiedad de gym_id=T: no se añadió elegibilidad de login a revocación, invalidación o withdraw. No se añadieron locks de Usuario a invalidadores ni se cambió el grafo de locks.

El target29 conserva las mismas secciones de estructura y tenant_security, además de triggers y todos los atributos de las funciones. Sólo18 cuerpos de función difieren en member_link_security. Los targets22–28, target SQLite29, modelos, DDL y20 políticas históricas no forman parte del delta. No se incluyen los dos casts que backend ensaya para pg_dump/restore.

## Replay del driver original

Los21 criterios pasan con rol PostgreSQL app restringido y base UUID propia. En las dos variantes de OWNER/padre no canónico, el predicado canónico sigue devolviendo false y ahora el destinatario ve0 publicaciones. El OWNER que consume una invitación propia y retira el propósito antes del commit recibe rechazo; los controles de propósito incorrecto y proof válido conservan sus resultados. Ninguna aserción se adaptó al fix.

También permanecen verdes los controles de hook GUC real para Connection/Session/pool tras commit/rollback/error, fallo al instalar propósito antes de query de negocio, locks de lectura con seis DML denegados, FK diferida/aborto completo y revocación futura del titular sin bearer anterior. No se volvió a correr55 ni la batería del autor. No se añadieron pruebas nuevas ni se intentó ampliar el alcance a servicios o blancos externos.

## Procedencia y límites

El ZIP del autor54ed0078 contiene14 fuentes RAW, no el freeze. Se contrastó cada fuente con su SHA; siete artefactos documentales tienen sólo CRLF→LF respecto de Git. Los tres productos del delta coinciden RAW/Git. El freeze tiene SHA RAW0decfcce y blob/checkout LF21d2fc4b. Su versión CRLF se reconstruyó desde el blob LF y se validó contra la SHA RAW completa suministrada; se etiqueta expresamente como reconstrucción, no como extracción del ZIP. La primera captura asumió que el freeze estaba dentro del ZIP y produjo KeyError antes de app/DB; el script original se conserva. No fue un rojo de producto ni motivó cambios en el driver.

Los registros, SQL/XML/log, fotos nuevas, paquete de dependencias y evidencia de DROP exacto quedan en el ZIP privado indicado en source.json. No se usaron correo/proveedores ni usuarios reales; credenciales sólo en el child desde el JSON privado y no impresas. No se modificó producto ni prueba del autor. El before V1 y sus hashes permanecen inmutables. La revisión permite continuar con los gates de núcleo/composición que coordine root; API/restore requieren su aceptación propia.

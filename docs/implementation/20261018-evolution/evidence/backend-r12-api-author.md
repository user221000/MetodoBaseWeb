# R12 API y restauración29: entrega de autor

Base de este lote: eef4c43, tras el core ad712, la corrección NULL/OWNER
1aac y los cuatro casts equivalentes6ec. No cambia el core, estructuras,
targets, veinte políticas anteriores, ledger, cuotas, precios ni perfil
personal. La revisión histórica28 quedó en el commit separado eef4c43:
una keyword de revisión explícita; el rechazo default sobre27 sigue intacto.

## Resultado implementado

Invitación anterior al registro, por cuenta profesional persistida y cliente
propio; token hash de propósito, un uso, caducidad y consentimiento explícito.
El emisor recibe estado e IDs opacos, nunca bearer, hash, URL, cuenta destino
ni confirmación de entrega. Reintento exacto no reenvía ni rota. Pending se
confirma antes de admitir correo en cola; el transporte del ensayo fue local.

Actor y asociación se releen, incluidos SV, roles y conjunto de Usuario bajo
orden total/NOWAIT. Cada ruta de destinatario exige user_id del actor exacto,
incluso OWNER legítimo propio o externo. OWNER tipo usuario ambiguo falla
cerrado. No se adopta Cliente personal ni se cambia equipo, roles o SV.
Revocar relación propia conserva identidad y datos personales; puede hacerse
con origen inactivo sin habilitar su lectura. La lista de lectura sólo ofrece
orígenes elegibles; no promete descubrir contextos suspendidos.

Publicación explícita de menú/meta derivados de fuente autorizada y descriptor
PDF exacto bajo locks. El destinatario no obtiene SELECT de Cliente/Plan/Objeto
fuente ni una capacidad del router general. Fuente legacy válida sin objectref
puede mostrar menú con motivo legacy_requires_review; una ref inválida rechaza
todo. PDF exacto privado: reemplazo/retirada devuelve404 al ID viejo, sin fallback
ni adopción silenciosa del archivo nuevo. Progreso y diario compartidos siguen
false: no se afirma que exista ese canal.

CAS final de publicación exige expected_publication_id obligatorio nullable y
versión observada. Crear: null/0; reemplazar: UUID/versión positiva. Omisión,
coerciones, booleanos o pares mixtos422. ID/versión distintos del vigente409
antes de retirar o insertar. Se conservan ambas reproducciones reales: SQLite
y PG permitían un segundo reemplazo basado en la misma foto de versión1.
RAW producto anterior46b8437a y driver/rojos c62ff5cc permanecen en Temp; el
driver conserva las mismas aserciones. Su adaptación previa fue sólo de DTO:
validó los tres campos existentes y añadió el nuevo ID en un namespace para
probar el servicio, sin afirmar que HTTP anterior aceptaba ese cuarto campo.

Commit/rollback inciertos dan503 visible y logs con clase técnica, sin SQL ni
parámetros. No se devuelven mensajes de correo antes del commit confirmado.
Tras ACK perdido de publicación, la fila real se conserva; reintento basado
en ausencia409 y una lectura explícita permite nueva intención con foto exacta.
Sesión local sin finalizer de autocommit: lecturas sin DML/commit y una sola
transacción/commit por mutación, sin segundo éxito seguido de commit final.

Parser stream16KiB antes de JSON/DTO; JSON duplicado, no finito, extra, tipo o
profundidad inválidos se rechaza íntegro. Menú/proyección256KiB y respuesta
512KiB con estructura conocida. Headers finales exactos no-store/no-referrer
incluyen404/405; CSP fija nonce/first-party sólo en la página accept, sin confiar
en CSP arbitraria del handler. Limiters sensibles fail closed y claves HMAC,
sin datos de actor/correo/token en claro. Producción sin Redis no ejecuta.

Exportación añade member_links como séptimo conjunto acotado por actor,
independiente de la barrera personal OWNER intacta. Sólo metadata active de
origen elegible; sin invitación, menú, descriptor, bytes ni cartera. Cursores y
budgets exactos están en la adenda98be0cae. Frontend ha coordinado export7
4e192d2 y CAS fff5fb0 con VM propias; aún no se atribuye HTTP/browser29.

## Evidencia de autor

- Baseline de rutas:4rojos404, luego mismas4verdes; driver original preservado.
- Gate previo a CAS:276 passed/2skipped en119.69s,609fuentes/81distribuciones
  quietas. Incluye servicios y HTTP reales en ambos motores y factories,
  registro real, worker nutrición/PDF real, privacidad, middleware, recuperación,
  ACK/logout, SDK y Redis. No es un ensayo de rendimiento.
- CAS:2rojos reales SQLite/PG antes;20focales verdes después, incluidos parser,
  multireemplazo y ACK perdido después de commit real.
- Gate final tras CAS:141passed/2skipped en114.12s. Los2skips son variantes
  SQLite de interleavings sólo PG; sus versiones PG sí se ejecutan.610fuentes
  y81distribuciones estables antes/después de API y restauración.
- Restauración completa29:1passed/27.40s con snapshot de filas/esquema/bytes,
  ledger26, diario27 y recuperación28 conservados; fuente29 poblada,6links,
  invitaciones pending/consumed/revoked,3publicaciones vigentes y2retiradas,
 5PDF/descriptores, OWNER propio/externo y ajeno. Funciones/triggers/invoker/
  búsqueda fija/FK diferida/23familias FORCE verificadas tras restore bajo rol
  app NOSUPER/NOBYPASS/noowner, más lectura real de ambas factories. Los2UUID
  exactos creados por el fixture quedaron ausentes al cerrar, con registro.
- Ruff F/E9 pasa en los9módulos nuevos y7tests/helper nuevos. El driver baseline
  de4rojos no se reformatea ni se corrige su import previo no usado; sigue
  pasando funcionalmente. Las6integraciones existentes se ejercitan por HTTP.

## Separación de aceptación y límites

El core1aac tuvo21criterios de seguridad independientes verdes para NULL/OWNER;
eso no acepta automáticamente los casts6ec, este API, restauración o UI.
Este lote es evidencia de autor para revisión QA/seguridad posterior. Ninguna
prueba utiliza correo real, proveedor real, despliegue ni base de producción.
No se atribuyen SLO, RPO/RTO ni entrega de correo al tiempo del ensayo.

El historial22–28 y sus SQL/targets siguen inmutables. El único test histórico
modificado, aprobado y separado, es el pin28 de eef4c43. El restore29 nuevo
reutiliza los helpers históricos y añade sus filas/criterios propios; no retargetea
los restores27/28. Respecto al overlay de6ec, el helper29 sólo añade la identidad
observada al DTO de publicación; el cuerpo y las aserciones de restore quedan.
La propuesta v2 RAW3c28 y API v1 RAW407 se conservan sin sobrescribir; la nueva
adenda v2 es98be0cae. No se aplica revisión30 ni se integra nada en MAIN aquí.

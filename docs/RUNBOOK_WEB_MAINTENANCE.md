# Mantenimiento y drenaje del servicio web

Este control es optativo y compartido por las factories web/API. Su presencia
en código no acredita una ventana productiva ni un respaldo consistente.
Aplicar el [runbook de migración](RUNBOOK_DB_MIGRATION.md) y ensayar el mismo
artefacto antes de intervenir producción.

## Configuración privada

Sin `METODOBASE_MAINTENANCE_FILE` el middleware no publica diagnóstico y
conserva el transporte actual. Con ruta configurada, archivo ausente,
ilegible, no regular o inválido bloquea HTTP con503, incluidos health, y
omite trabajos protegidos. Nunca borrar el archivo para reabrir tráfico.

En Railway el preflight del1 de noviembre encontró `/data` sin mount
persistente. No asumir que un archivo sobreviva al despliegue. La ruta
operativa propuesta es `/tmp/metodobase-operations/maintenance.json`, fuera
de los objetos de clientes. Su directorio privado requiere0700 y el
archivo0600, propiedad del usuario del proceso. El entrypoint instala cada
arranque desde el secreto `METODOBASE_MAINTENANCE_BOOTSTRAP` antes de iniciar
el servidor y retira esa variable del entorno del worker. La credencial
migradora se retira antes de ejecutar el bootstrap.

Configurar ambas variables juntas desde el mecanismo privado del proveedor.
Una pareja incompleta o una semilla inválida impide arrancar el servidor.
El documento UTF-8, máximo4096 bytes, tiene exactamente estas claves:

```text
{"version":1,"active":true,"token":"<64 caracteres hexadecimales>",
 "operation":"<UUID canónico minúsculo con guiones>"}
```

Generar token y operación en un proceso protegido. No registrar el token ni
el JSON en Git, argumentos, URLs, logs, capturas o recibos abiertos. No usar
una clave de ejemplo. Mantener token y operación durante la intervención.
`version` es entero1 y `active` es booleano, sin coerciones. Claves duplicadas
o adicionales se rechazan.

Crear un documento válido `active=false` antes de activar el control en una
portadora compatible con el esquema actual. Para pausar, mantener una
semilla del proveedor `active=true` y reemplazar el archivo con el mismo
documento activo de forma atómica en su mismo directorio. No truncar/escribir
en sitio. Ensayar el orden real de cambios del proveedor: no suponer que
editar una variable carece de despliegue automático. Un reinicio instala
la semilla vigente; cambiar únicamente el archivo no modifica esa autoridad.

## Qué cuenta el drenaje

El contador HTTP vive hasta terminar `await app`, incluidas tareas Starlette
en segundo plano, streaming y finalizadores. Las solicitudes admitidas antes
de pausar terminan normalmente; no se matan ni cancelan para simular drenaje.

Los trabajos de limpieza inicial/periódica y mantenimiento de autenticación
usan el mismo `MaintenanceGate`. `init_auth` siempre configura claves y
expiraciones; omite sólo sus escrituras cuando no recibe admisión.

Los dispatchers de recuperación e invitaciones registran probes de sólo
lectura que capturan sus instancias exactas. La clave de registro incluye la
identidad del objeto, sin datos personales; registrar de nuevo el mismo
objeto no duplica su contador. Sus `pending` cubren cola y
ejecución hasta el `finally` de finalización, incluida cancelación. El probe
permanece después de `close(wait=False)`, incluso si otro lifespan instala
un dispatcher nuevo en `app.state` mientras el anterior termina.
Los tres enqueue actuales nacen dentro de HTTP contado y sus operaciones no
encolan otros trabajos. Auditar esa propiedad si se añaden ejecutores o
callers. No se cambia la semántica de esos dispatchers.

Lifespan y demás scopes no HTTP pasan normalmente. Este control no detiene
scripts, workers externos, cron, escrituras manuales ni procesos antiguos.
Inventariarlos y drenarlos por su procedimiento autorizado. Los handlers
actuales de `/health` y `/health/ready` hacen `SELECT1`; comprobar que sigan
sin escrituras al cambiar su stack.

## Diagnóstico y comprobación por proceso

Usar sólo `GET /__metodobase_maintenance`, con un único header privado
`X-Metodobase-Maintenance`. El cliente debe leer la clave del archivo
protegido hacia memoria, sin ponerla en argumentos ni imprimir cabeceras.
Clave incorrecta/ausente/duplicada o método distinto devuelven404 no-store.

El diagnóstico autorizado devuelve `active`, `active_requests`,
`active_jobs`, `pid`, `operation` y `drained`. `active_jobs` suma trabajos
protegidos y las dos colas reales. Un probe que falla o devuelve un valor
inválido produce diagnóstico503 y no declara drenaje.

La evidencia requiere simultáneamente `active=true`, ambos contadores0,
`drained=true` y la operación esperada. El contador es local al proceso.
Identificar workers, réplicas y todos sus PIDs: una respuesta del balanceador
no prueba haber observado cada uno. Si no se puede consultar cada proceso,
usar sólo un worker/réplica verificado o mantener bloqueada la intervención.
Los health permitidos también cuentan durante su ejecución.

Con archivo válido activo sólo se permiten los health GET/HEAD exactos y
el diagnóstico autenticado. Con archivo inválido o ausente los health también
reciben503. No se falsifica la disponibilidad de BD ni se añade un plazo
supuesto para declarar cero.

## Respaldo, cambio de versión y reapertura

Mantener semilla y archivo activos, todos los procesos drenados y escritores
externos detenidos durante el respaldo coordinado y el restore ensayado del
runbook. No se sustituyen validaciones de objetos, custodia, roles o RLS.

La candidata siguiente debe arrancar con su semilla activa y reproducir el
control en su filesystem nuevo. Ensayar previamente este cruce de contenedor
con `active=true` y repetir el diagnóstico en todos los procesos nuevos.

Sólo tras las validaciones y decisión operativa de reapertura, cambiar de
forma coordinada semilla y archivo a `active=false` mediante reemplazo
atómico. Verificar funcionamiento y nueva admisión de trabajos. Una variable
sin configurar conserva comportamiento normal; no usar su retirada como
sustituto de la reapertura explícita de una ventana en curso.

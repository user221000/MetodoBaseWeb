# Respaldo remoto con el plan actual

El plan de Railway se conserva. El rechazo observado de snapshots nativos exige Pro para esa función; no impide preparar un respaldo propio. La documentación oficial admite un [servicio cron](https://docs.railway.com/cron-jobs) que ejecuta una tarea y termina. La ejecución consume CPU, memoria y transferencia del [plan existente](https://docs.railway.com/pricing/plans); no se promete coste cero. Los [buckets](https://docs.railway.com/storage-buckets/billing) tienen consumo de almacenamiento. No se contrató otro plan ni se activó un servicio.

## Implementación disponible

`scripts/backup_daily.py` captura PostgreSQL o SQLite y, cuando se indica, un árbol local de objetos. Produce artefactos AES-256-GCM y manifiesto autenticado. El sucesor `scripts/backup_remote.py` publica esa copia existente en un prefijo privado dedicado y permite recuperarla en una cuarentena nueva:

- Verifica el manifiesto y descifra/verifica los artefactos antes de publicar. También cifra el manifiesto, que puede contener rutas sensibles.
- Comprueba política y ACL privadas. Usa `If-None-Match: *`; nunca sobrescribe ni elimina un objeto remoto existente. Un conflicto se acepta sólo al comprobar sus bytes o el contenido del manifiesto cifrado.
- Lee todos los objetos publicados y compara tamaño y SHA-256. Publica al final `complete.json`, autenticado con la clave de respaldo. Una carga parcial sin ese índice no es un respaldo completo; reintentar conserva los bytes existentes.
- La recuperación exige MAC, límites, nombres, hashes y cifrado válidos. Sólo escribe en una cuarentena nueva; no restaura PostgreSQL, inicia la aplicación, manda correo ni permite servir datos.
- El recibo declara las familias incluidas. Un respaldo de base sin objetos indica `not_included`. No se acredita coherencia entre SQL y objetos ni un registro de supresiones por publicar archivos. No existe retención destructiva implícita.

Las pruebas usan SQLite y almacenamiento aislados. Su resultado no acredita PostgreSQL remoto, S3 del proveedor, una agenda activa ni recepción de alertas; cada operación externa requiere un recibo propio.

## Preparación del servicio periódico

El servicio de respaldo debe tener una imagen propia revisada con **cliente PostgreSQL 18 compatible con el servidor 18.6**, Python y las dependencias fijadas. La imagen web actual no acredita ese cliente: `libpq` no equivale a `pg_dump`. No reutilizar un cliente17 contra servidor18 ni modificar el proceso web para ejecutar un bucle permanente de respaldo.

Las variables de ese servicio, por el canal de secretos del proveedor, son:

| Variable | Uso |
|---|---|
| `BACKUP_DATABASE_URL` | Acceso sólo para captura; credenciales en entorno, nunca argumentos/logs |
| `BACKUP_ENCRYPTION_KEY` | Base64 de32 bytes aleatorios; copia recuperable custodiada fuera del bucket y del servicio |
| `BACKUP_S3_ENDPOINT`, `BACKUP_S3_REGION` | Endpoint HTTPS explícito y región |
| `BACKUP_S3_BUCKET`, `BACKUP_S3_ACCESS_KEY`, `BACKUP_S3_SECRET_KEY` | Destino privado, idealmente credencial limitada al prefijo de respaldos |

No copiar automáticamente secretos del servicio web a otro proveedor. Usar claves distintas para cifrado y almacenamiento. El bucket existente tiene política privada y ACL sin grants públicos en la lectura del3 de noviembre; no se observó versionado. El mismo bucket/cuenta/credencial no constituye custodia independiente ni protección contra borrado por una cuenta comprometida.

El job debe ejecutar: captura consistente SQL → captura/verificación de todos los objetos referenciados por esa instantánea → cifrado/verificación local → publicación remota → lectura y verificación → recibo de éxito → cierre de conexiones y salida0. Ante cualquier error debe salir distinto de0. Se exige tiempo máximo y alarma de falta de ejecución; Railway omite el siguiente cron si el anterior continúa activo. El cron usa UTC y no garantiza precisión al minuto. No hay calendario activado en este cambio.

Publicar una copia cifrada ya existente, suministrando secretos sólo en entorno:

```powershell
python -B -X utf8 -m scripts.backup_remote publish --manifest E:/ruta-privada/snapshot-manifest.json --prefix backups/metodobase --max-bytes 536870912
```

Recuperar una instantánea completada a un directorio nuevo bajo una raíz privada:

```powershell
python -B -X utf8 -m scripts.backup_remote fetch --snapshot IDENTIFICADOR_REAL --output E:/cuarentena-privada/nueva --prefix backups/metodobase --max-bytes 536870912
```

Los identificadores se obtienen del recibo real. Linux crea la cuarentena con modo0700; en Windows se exige raíz con ACL privada del operador/SYSTEM antes de ejecutar. El temporario del proceso también debe estar en almacenamiento privado. Los recibos de fallo sólo emiten una categoría fija, sin excepciones del proveedor, URLs, nombres de objetos del cliente ni secretos.

## Condiciones que permanecen abiertas

La captura periódica PostgreSQL18+objetosS3 coherentes, imagen del job, clave custodiada, destino independiente, calendario, política de retención y vigilancia todavía necesitan implementación/aceptación y ensayo real. Las pruebas previas de recuperación SQL44tablas/286filas y tres objetos son evidencia separada; no recuperan las40referencias históricas sin bytes. La publicación remota añade transporte recuperable, no reemplaza esos contratos.

Soporte principal/suplente, canal, RPO y RTO permanecen **pendientes por decisión del usuario**. No se deduce una garantía de pérdida/tiempo de una agenda propuesta o ensayo exitoso. Tampoco un `SENTRY_DSN` demuestra reglas o recepción de una alarma. Antes de servir una restauración se necesita aplicar el registro externo autenticado y fresco de supresiones y validar esquema, roles, RLS, cuotas, pagos y referencias; la cuarentena no autoriza promoción.

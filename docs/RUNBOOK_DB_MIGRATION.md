# Runbook: migración de la base del servicio web

Procedimiento preparatorio para PostgreSQL. Fecha, responsable, ventana, destinos y versión a promover deben completarse y aprobarse antes de intervenir un entorno real. No se ha ejecutado una migración productiva mediante este documento. Los ensayos locales no sustituyen la aceptación de staging ni el rollback probado.

Contratos: [aislamiento y roles](implementation/20261018-evolution/AISLAMIENTO.md), [backup y restore](implementation/20261018-evolution/BACKUP_RESTORE.md), [privacidad](implementation/20261018-evolution/PRIVACIDAD.md) y [estado de preparación](implementation/20261018-evolution/PREPARACION_PRODUCCION_20261029.md). El alcance es exclusivamente el servicio web.

## 1. Preparación y condiciones para iniciar

- Registrar el commit y el digest de la imagen candidata, la revisión de esquema que esa versión exige y la versión anterior compatible. Promover el mismo artefacto ensayado; no usar una cifra histórica de tests como aceptación de CI actual.
- Inventariar base, esquema, revisión Alembic, ownership, roles, membresías, políticas RLS y referencias de documentos/logos. Una base existente sin versión, una política desconocida o una colisión histórica requieren reconciliación revisada; no se corrigen con `stamp`, creación ORM de tablas o DDL improvisado.
- Ensayar en staging la actualización desde el estado inventariado y desde una base vacía. El plan debe incluir restore real en destino aislado, comprobaciones de acceso y una vuelta atrás compatible antes de fijar la ventana productiva.
- Acordar responsable, canal de incidencias, ventana y criterios de interrupción/reapertura con operación. Registrar los tiempos y el punto recuperado del ensayo; no se presuponen duración, RPO/RTO, retención o umbrales de error.
- Confirmar que se dispone de las fuentes completas, manifiesto verificable, custodia y recuperación de claves fuera del backup, y procedimiento revisado para los objetos y las supresiones de privacidad. Si falta una de estas condiciones, no se inicia la migración.

## 2. Roles, destinos y secretos

`DATABASE_URL` identifica el rol de aplicación: sin superusuario, sin BYPASSRLS y sin pertenencia directa o indirecta a un propietario de tablas; sólo los permisos de aplicación revisados. `MIGRATOR_DATABASE_URL` identifica un rol distinto, autorizado para las migraciones. En producción ambas URLs deben indicar explícitamente el mismo host, puerto efectivo y base, con usuarios diferentes. Sólo se permiten las opciones TLS revisadas; no overrides de autoridad mediante query, service u options.

La credencial migradora se limita al proceso de migración. El [entrypoint](../entrypoint.sh) la retira antes de iniciar el servidor. El respaldo completo bajo FORCE RLS necesita un rol de backup autorizado para leer todas las tablas; el rol app no sustituye ese rol y no recibe bypass para facilitar el backup. La restauración usa su destino aislado y los permisos revisados para recuperarlo; después se verifica el acceso con el rol app restringido.

Confirmar explícitamente `METODOBASE_ENV=production` tanto en el proceso de migración como en el runtime. El valor omitido es `development`; no omitirlo ni usar ese modo para eludir las comprobaciones productivas de destinos y roles.

Suministrar las URLs y `BACKUP_ENCRYPTION_KEY` mediante el mecanismo seguro del entorno, limitado al proceso que las necesita. La clave de backup es base64 de 32 bytes aleatorios. Comprobar presencia y destino sin imprimir valores: no volcar URLs, claves o el entorno en terminal, logs, tickets o capturas. No incluir credenciales en argumentos. Guardar sólo resultados saneados y referencias a recibos protegidos.

## 3. Ventana y respaldo consistente antes de migrar

1. Aplicar el control de mantenimiento que exista y se haya ensayado en la plataforma. Detener nuevas escrituras y drenar las peticiones, workers, generación de planes y demás escritores de BD/objetos, incluidos procesos antiguos. No se presupone que una variable de mantenimiento o un comando de servicio concretos estén implementados.
2. Verificar la quiescencia y mantenerla durante el respaldo coordinado de BD y objetos y el cambio de versión. El snapshot de PostgreSQL y el filesystem son recursos separados: no se da por atómico su respaldo conjunto.
3. Usar la entrada existente `scripts/backup_daily.py` con `--database-env BACKUP_DATABASE_URL`, `--expected-database`, `--pg-bin`, `--objects` y `--output` explícitos y registrados en el ensayo. Los valores dependen del entorno aprobado; las rutas locales de trabajo y evidencia permanecen en E/F.
4. El respaldo PostgreSQL usa `pg_dump` custom con `--no-owner --no-acl`; sus credenciales viajan por entorno libpq. Seleccionar binarios compatibles con el servidor, sin asumir que una instalación local determina la versión productiva. No usar el modo plaintext de pruebas.
5. Exigir salida correcta, manifiesto final, cifrado/autenticación y hashes válidos. Ejecutar la operación existente `scripts/backup_restore.py verify` con su `--manifest`. Conservar copia y clave recuperables según la custodia acordada. Una lista de archivos o un dump legible no prueban un restore completo.
6. Confirmar el ensayo de restauración del respaldo que cubre la intervención: destino de BD nuevo/vacío y destino de objetos vacío, schema/revisión, relaciones, checksums y autorización comprobados. Un bucket externo requiere su adaptador/inventario y ensayo propios; no queda cubierto por `--objects` local.

## 4. Migración bloqueante

El comando vigente es:

```text
python db_bootstrap.py
```

[railway.toml](../railway.toml) lo configura como `preDeployCommand`; fuera de Railway lo invoca el entrypoint antes de servir. No ejecutar un segundo mecanismo de dual-write o scripts archivados como sustituto de esta ruta. El comando usa una conexión propia del migrador, aplica Alembic hasta el head revisado de la candidata y verifica el contrato estructural. Un fallo devuelve un código bloqueante: mantener mantenimiento y no arrancar una versión que rechace el esquema.

Una base existente sin versión se rechaza por defecto. `--adopt-verified-legacy` no es un paso rutinario: exige revisión previa de la firma histórica exacta y ensayo de la adopción; no convierte un esquema desconocido en válido. `--revision` se reserva al ensayo histórico revisado, no a saltar el contrato de la versión que se va a servir.

## 5. Validación y reapertura controlada

- Confirmar el head y contrato actuales, índices/restricciones, políticas ENABLE/FORCE y ownership. No desactivar RLS ni relajar las guardas de startup para conseguir que arranque.
- Iniciar la misma imagen validada con el rol app y comprobar `/health/ready`, sin mostrar secretos. El entorno debe aceptar sus guardas de esquema y aislamiento; el usuario de migración no queda disponible al servidor.
- Completar los recorridos acordados en staging: dos tenants aislados, permisos/revocación, generación y lectura autorizada de PDF/logo y referencias/checksums. La validación de cobros se realiza en sandbox, no creando cargos reales como smoke test.
- Reabrir tráfico y escritores únicamente conforme al plan aprobado y observar errores y efectos externos con los criterios acordados. Revalidar el calendario real de backups, custodia y alertas: este runbook no configura cron ni servicios del proveedor.

## 6. Interrupción y rollback ensayado

Ante fallo, conservar mantenimiento, fuentes y recibos saneados; registrar el punto alcanzado sin exponer datos personales. Una versión anterior sólo puede volver a servir si su compatibilidad con el esquema resultante fue comprobada. No se usan downgrade destructivo, desactivación de RLS ni fallback a archivos SQLite para recuperar producción.

Si se requiere restaurar datos del servicio, usar como único coordinador el recorrido autenticado `restore_with_suppressions` de [restauración en cuarentena](../web/services/privacy_suppression.py). Este coordinador ejecuta internamente la recuperación de bytes y exige un destino de BD nuevo/vacío y objetos vacíos: no ejecutar primero la CLI de restore sobre ese mismo destino. No sobrescribir una base en servicio, usar `--clean` o borrar datos para hacer pasar la comprobación de destino vacío.

Para un ensayo aislado limitado a recuperación de bytes, la CLI existente es `scripts/backup_restore.py restore` y el destino se selecciona explícitamente con `--database-env RESTORE_DATABASE_URL`, además de `--manifest`, `--expected-database`, `--pg-bin` y `--objects` según el contrato de backup. Sin ese flag, la CLI utiliza `BACKUP_DATABASE_URL` por defecto; nombrar otra variable no la selecciona. Ese ensayo no aplica supresiones ni autoriza reapertura.

La recuperación de bytes no autoriza reabrir acceso. El coordinador exige cuarentena, política y registro externos autenticados, y el binding del destino, migración y sesiones para aplicar las supresiones vigentes. No se inventa una CLI para ese coordinador ni una política de conservación. Si su autoridad/custodia o procedimiento operativo no están disponibles, el destino permanece aislado.

Volver a comprobar esquema, objetos/referencias, rol app, aislamiento, estado de privacidad y readiness de la versión elegida antes de la conmutación aprobada. Si falla la promoción de objetos después de recuperar la BD, el restore sigue fallido y el destino aislado. Registrar el tiempo y el punto de datos realmente recuperados, sin convertir el ensayo en una promesa de disponibilidad o RPO/RTO.

## 7. SQLite legado: sólo histórico y ensayo aislado

Los antiguos pasos de dual-write, cambios `DB_MIGRATION_PHASE`, scripts archivados, copia manual de `.db` y restauración sobre archivos activos no forman parte del despliegue PostgreSQL actual. No se cambia de tenant por defecto ni se adoptan datos reales mediante este documento.

Para una fuente SQLite histórica explícita, conservar su procedencia y ensayar fuera del servicio; el backup actual usa la API online de SQLite y `integrity_check`, con coordinación de escritores cuando deba cubrir también objetos. No copiar un archivo activo como respaldo consistente ni archivar/eliminar el original sin política y autorización propias. La migración o asignación de datos históricos exige su procedimiento revisado independiente.

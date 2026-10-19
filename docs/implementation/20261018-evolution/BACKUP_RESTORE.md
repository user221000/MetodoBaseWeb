# Respaldo y restauración: contrato actual

Implementación local: `scripts/backup_restore.py` y entrada diaria `scripts/backup_daily.py`. No se configuró un cron ni se alteraron backups Railway. No hay una política de retención o RPO/RTO acordada; el operador debe definirlas. Los objetivos históricos de 24 horas y 4 horas siguen siendo propuestas, no capacidades demostradas.

El respaldo requiere fuentes explícitas, un nombre de base esperado y `BACKUP_ENCRYPTION_KEY` en el entorno del proceso. La clave es base64 de 32 bytes aleatorios, gestionada y recuperable fuera de la copia. No registrar la clave ni la URL. El código usa AES-256-GCM mediante cryptography, verifica el descifrado y guarda SHA-256 de cada artefacto. El manifiesto se escribe al final; sin fuente o ante fallo no se anuncia éxito. La retención no borra copias por una política inventada.

PostgreSQL usa `pg_dump` custom, `--no-owner --no-acl`, y comprueba que `pg_restore --list` puede leerlo. Las credenciales se transmiten por entorno libpq, nunca argumentos. El binario debe ser compatible con la versión del servidor; el ensayo local usa PostgreSQL 17.11. SQLite usa la API online de backup y `integrity_check`; no copia un archivo activo sin coordinación. Los documentos/logos locales se incluyen mediante `--objects`, con rutas y checksums por objeto. Un bucket externo requiere su propio adaptador/inventario y ensayo antes de cerrar R08.

Ejemplo sin secretos (las variables se suministran desde un gestor seguro):

```powershell
python scripts/backup_daily.py --database-env BACKUP_DATABASE_URL --expected-database metodobase_test_source --pg-bin 'C:\Program Files\PostgreSQL\17\bin' --objects C:\isolated\objects --output C:\isolated\backups
python scripts/backup_restore.py verify --manifest C:\isolated\backups\SNAPSHOT-manifest.json
python scripts/backup_restore.py restore --manifest C:\isolated\backups\SNAPSHOT-manifest.json --database-env RESTORE_DATABASE_URL --expected-database metodobase_test_restore --pg-bin 'C:\Program Files\PostgreSQL\17\bin' --objects C:\isolated\restored-objects
```

Restaurar requiere una base vacía y un destino de objetos vacío. No usa `DROP`, `--clean` ni sobreescribe SQLite. Verifica y prepara los objetos antes de restaurar PostgreSQL en una transacción. PostgreSQL y filesystem son recursos separados: un fallo al promover objetos después de restaurar BD se reporta como fallo; el operador debe conservar el entorno aislado, corregirlo y volver a comprobar referencias antes de servir tráfico. Restaurar en un entorno nuevo es el mecanismo de recuperación; no se utiliza downgrade destructivo para borrar datos durables.

Comprobar después: Alembic/head y schema, usuarios/relaciones sintéticas, restricciones e índices, referencias y checksums de PDF/logo, autorización con el rol de aplicación y arranque de la misma imagen. Medir tiempo y punto de datos recuperado; un dump legible no demuestra un restore completo. QA conserva evidencia independiente en `evidence/`; la prueba de cinco casos unitarios sólo cubre SQLite/objetos/cifrado/fallos.

`--allow-plaintext-local-test` se admite exclusivamente para ensayos. Para PostgreSQL exige loopback y nombre `metodobase_test_*`. No debe usarse como política productiva. La revisión de seguridad, el restore PostgreSQL completo y los backups nativos/objetos reales siguen abiertos hasta obtener evidencia.

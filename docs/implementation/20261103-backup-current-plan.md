# Respaldo periódico con el plan actual

Se conserva Railway Hobby. La lectura autenticada del 3 de noviembre de 2026 a las 15:22 UTC observó tres instancias y **ningún cron activo**. La [tabla oficial](https://railway.com/pricing) admite 50 cron por proyecto Hobby: esta alternativa no exige Pro. Su ejecución y almacenamiento consumen recursos del plan; no se promete coste adicional cero.

El candidato incorpora una receta de imagen separada, un lock de once distribuciones, un arranque que verifica recibos y un contrato **inactivo**. No se creó un servicio, una clave, un rol, una agenda ni una alarma. La imagen final todavía necesita construcción Linux, SBOM/SCA y revisión independiente. El anterior artefacto web tenía veinte CVE High únicas en su SCA; una ejecución sintética correcta no acepta la seguridad de esta nueva imagen.

## Archivos y ejecución

`Dockerfile.backup` fija Linux/amd64 y la base CPython 3.12.16 por digest. Conserva la comprobación de CA, liblzma 5.8.1-1+deb13u2 y la reconstrucción revisada de ambos módulos XML con Expat 2.10. El cliente PostgreSQL es 18.6 y psycopg2 2.9.13 se compila con libpq18. No incluye el servidor PostgreSQL, el servidor web ni el árbol completo de la aplicación.

`requirements-backup.lock` fija once distribuciones y sus hashes: boto3, botocore, jmespath, s3transfer, urllib3, python-dateutil, six, cryptography, cffi, pycparser y psycopg2. La receta instala los binarios fijados sin resolver dependencias adicionales; construye psycopg2 desde su fuente autenticada y comprueba el inventario final exacto. Los paquetes Debian se resuelven desde el snapshot firmado y fijado del 3 de noviembre; los cuatro paquetes PGDG tienen versión, longitud y SHA256 seleccionados de metadata previamente autenticada. Se conservan inventarios y procedencia, incluida Perl como dependencia del cliente; no se oculta metadata a SCA.

El Dockerfile sólo copia los trece archivos de imports enumerados en `deploy/backup-service.contract.json`. El destino final usa usuario 10001, no instala paquetes al arrancar, no abre HTTP ni lleva un volumen persistente. Los límites CPU/RAM siguen sin fijar hasta medir el artefacto en los máximos de captura.

Construcción candidata en un runner Linux con BuildKit, usando fuentes congeladas sin secretos:

```sh
docker build --platform linux/amd64 -f Dockerfile.backup --target backup \
  --iidfile backup-image.id -t metodobase-backup:candidate .
docker run --rm --entrypoint /usr/lib/postgresql/18/bin/pg_dump metodobase-backup:candidate --version
docker run --rm --entrypoint /usr/lib/postgresql/18/bin/pg_restore metodobase-backup:candidate --version
```

El daemon Docker local no estuvo disponible en la comprobación de autoría; no se intentó iniciarlo ni instalar herramientas compartidas. Las comprobaciones de la receta no sustituyen un build terminado. Root mantiene la propiedad del workflow y debe unir imagen/digest, SBOM completo, SCA, pruebas Linux y aceptación independiente en un recibo de CI.

El nuevo módulo `scripts.backup_service_entrypoint` exige identidad explícita. Ejemplo de argumentos para un entorno **sintético**; los valores productivos se seleccionan sólo después de verificar origen y revisión:

```sh
python -B -X utf8 -m scripts.backup_service_entrypoint \
  --expected-database synthetic_backup \
  --expected-revision 20261031_gym_equipment \
  --pg-bin /usr/lib/postgresql/18/bin --work-root /tmp \
  --timeout-seconds 900 --capture-timeout-seconds 300
```

La otra revisión admitida es `20261102_payment_refund_facts`. No se descubre automáticamente el head ni se migra el origen. Un nombre/revisión inválido falla antes de ejecutar el job. Linux usa una frontera nueva 0700 bajo `/tmp`, umask 077 y temporales privados; las pruebas locales de archivos sólo admiten E/F. El arranque operativo exige Linux.

El wrapper llama al `backup_job.run_job` existente. Ese job crea y supervisa su proceso worker, limita el tiempo y verifica el cierre de su grupo propio; el wrapper no introduce un segundo supervisor. Después vuelve a autenticar el recibo final, lo liga al nonce/configuración de la solicitud privada y coteja la evidencia de supervisión y la respuesta retornada. Un retorno 0 o un mensaje en stdout no basta para acreditar respaldo.

| Salida | Significado |
|---|---|
| 0 | Recibo autenticado de cobertura actual completa, publicación, readback y cierre verificados |
| 2 | Contingencia autenticada parcial por referencias históricas sin bytes, con contadores exactos; permanece parcial |
| 1 | Fallo, timeout, recibo ausente/truncado/alterado, identidad distinta o cierre sin verificar |

La salida pública sólo informa estado, contadores y controles verificados. No refleja excepciones, argumentos privados, claves, URLs de acceso ni nombres de objetos. Expresa que la agenda y recepción de alarma **no están acreditadas**. Mantiene cero borrados por retención y no autoriza servir una restauración.

## Flujo y permisos

La captura utiliza un snapshot exportado PostgreSQL 18 de sólo lectura y los descriptores inmutables de objetos de esa misma instantánea. Cifra SQL y objetos, publica condicionalmente, recupera los bytes publicados a una cuarentena nueva y autentica su coincidencia. El índice remoto conserva la afirmación limitada de transporte `not_attested`; el recibo del job acredita lo que éste verificó, sin inventar captura de roles globales o registro de supresiones.

| Secreto de entorno | Permiso y custodia requeridos |
|---|---|
| `BACKUP_DATABASE_URL` | Conexión privada preferida; rol dedicado CONNECT/USAGE/SELECT de tablas y secuencias con BYPASSRLS para visibilidad completa. Sin superuser, escritura, CREATEDB/CREATEROLE/REPLICATION; no reutilizar el rol web |
| `OBJECT_STORAGE_S3_*` | GetObject de objetos fuente registrados; credencial de lectura separada cuando lo permita el proveedor |
| `BACKUP_S3_*` | GetObject y PutObject condicional en prefijo `backups/metodobase`; GetBucketPolicyStatus/GetBucketAcl. Sin DeleteObject o administración |
| `BACKUP_ENCRYPTION_KEY` | Base64 de 32 bytes aleatorios; clave distinta de S3 y copia recuperable fuera del bucket y del servicio |

Las claves sólo entran por el entorno del servicio: no argumentos, build args, logs, Git o chat. La receta y estas pruebas no generan claves productivas ni conceden permisos. Las concesiones del rol deben comprobarse con captura positiva y rechazos de escritura; añadir tablas futuras exige revisar su cobertura.

La lectura del bucket del 3 de noviembre verificó política/ACL privadas y no observó versionado. Un prefijo separado en el mismo bucket/cuenta no demuestra protección ante compromiso o borrado de esa cuenta. La custodia independiente sigue siendo un límite explícito.

## Contrato inactivo, alarma y cierre

`deploy/backup-service.contract.json` es un contrato de revisión, **no un archivo que Railway aplique**. Propone un servicio separado, una réplica, reinicio `NEVER` y horario diario 08:17 UTC (`17 8 * * *`), todavía desactivado. El intervalo inicial es una decisión técnica para medir coste y duración; **no es un compromiso RPO**.

La documentación de [cron Railway](https://docs.railway.com/cron-jobs) exige que la tarea termine, usa UTC, admite intervalos de al menos cinco minutos y omite la siguiente ejecución si la anterior sigue activa. El horario puede retrasarse. La configuración futura debe usar API/IaC revisada y limitarse al nuevo servicio: [Railway ya no permite `railway.toml/json` en servicios nuevos](https://docs.railway.com/infrastructure-as-code); los legacy dejan de leerlos el 1 de diciembre. Este cambio no migra ni configura el servicio web.

La alarma debe detectar fallo, estado parcial, ausencia de inicio y ausencia de final verificado. Se propone tolerancia inicial de 60 minutos tras la ventana, por validar. **No hay emisor ni entrega de monitor implementados aquí.** `SENTRY_DSN`, los logs y una salida distinta de 0 no acreditan reglas, destinatario o recepción. Se necesita monitor independiente del job y un ensayo real con receptor autorizado; no se envían mensajes desde estas pruebas.

Antes de declarar respaldo periódico funcional:

1. Construir y revisar el digest final con SBOM/SCA completo, librerías enlazadas, CA, inventario Python y cierre de imports.
2. Ejecutar las pruebas del wrapper y las pruebas reales existentes de supervisor Linux y captura/restauración PostgreSQL 18.6 para ambas revisiones; medir memoria, disco y tiempo en los límites configurados.
3. Verificar rol, destino, permisos y recuperación de clave desde su copia externa. Hacer captura/publicación/fetch autorizados y restauración aislada.
4. Verificar monitor y receptor; configurar sólo el nuevo servicio, leer de vuelta la agenda y observar al menos dos ventanas reales. No activar con gates de imagen, permisos o recuperación abiertos.

El ensayo aislado no promueve la cuarentena a producción. Antes de servir datos restaurados siguen siendo necesarios esquema, roles/RLS, cuotas, pagos, objetos y el registro externo autenticado y fresco de supresiones. Las referencias históricas sin bytes permanecen descubiertas: una copia nueva no recrea su contenido.

Responsables principal/suplente, canal de soporte, RPO y RTO permanecen **pendientes por decisión del usuario**. No se derivan del intervalo, timeout o resultado de una prueba. La futura retención destructiva también requiere una política concreta; este candidato no borra copias.

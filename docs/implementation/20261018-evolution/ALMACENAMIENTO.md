# R07: documentos privados y transición histórica

## Integración local posterior

El candidato conecta generación, lectura y branding con `web/storage`. El destino operativo todavía debe seleccionarse y verificarse. No hay bucket aprovisionado, prueba de reemplazo de contenedor ni publicación en producción. La UI de logos y el inventario histórico se revisan como sublotes separados; este documento no cierra todo R07.

`20261018_stored_objects`, integrado en74d66e8, añade la tabla25 y familia19 con ENABLE/FORCE RLS. Conserva targets/fixtures anteriores. `StoredObject` guarda UUID hex32, propietario, kind, key única, tipo, tamaño, SHA256, backend, pending/ready y dos instantes UTC. Plan y perfil tienen referencias nullable con FK compuesta de propietario y RESTRICT. Ninguna ruta histórica se convierte automáticamente ni se eliminan bytes mediante CASCADE.

`publish_pending_object` confirma la intención antes de PUT y cierra esa sesión antes del I/O. Después, el consumidor confirma ready y referencia de plan/perfil en una misma transacción. Un fallo de PUT puede haber publicado bytes: queda pending, sin asumir ausencia, borrar ni seleccionar otro destino. Fallar después de PUT y antes del commit revierte ready/referencia/plan/marcador de cuota; los bytes quedan para reconciliación. Una publicación confirmada no se reembolsa por perder respuesta. Reintentos/retención corresponden a R28/R31.

La aplicación autoriza con identidad persistida y doble propiedad plan/cliente; exige metadatos del mismo dueño, kind esperado, ready y backend seleccionado. El adaptador comprueba tamaño/SHA256. Conocer ID/key no concede acceso. Una referencia privada es autoritativa: si falla, nunca se sustituye por bytes legacy ni por otro plan.

### Configuración obligatoria

Ambos factories fallan antes de usar la base si la configuración no es válida. [.env.example](../../../.env.example) deja la elección vacía. No mezclar valores S3 con local ni configurar raíz de fallback para S3. Pruebas borran variables AWS/S3/OBJECT heredadas y usan raíz temporal privada por worker.

| Variable | Uso |
|---|---|
| `OBJECT_STORAGE_BACKEND` | `local` o `s3`, obligatorio |
| `OBJECT_STORAGE_LOCAL_ROOT` | Raíz absoluta privada; sólo local |
| `OBJECT_STORAGE_S3_BUCKET` / `OBJECT_STORAGE_S3_REGION` | Bucket existente y región; sólo S3 |
| `OBJECT_STORAGE_S3_ENDPOINT` | Opcional HTTPS sin credenciales/path/query; HTTP sólo loopback de desarrollo |
| `OBJECT_STORAGE_S3_ACCESS_KEY` / `OBJECT_STORAGE_S3_SECRET_KEY` | Credenciales explícitas, fuera de logs/repr |
| `OBJECT_STORAGE_S3_SESSION_TOKEN` | Credencial temporal opcional |

No se consultan perfiles/credential_process ni credenciales/endpoints heredados. S3 fija firma S3v4, conexión3s/lectura10s, dos intentos totales y endpoint overrides desactivados. No descubre/crea buckets. Local necesita montaje/permisos, backup y ensayo de sustitución para producción; reabrir adaptador en el mismo host sólo prueba reconstrucción de proceso. El contenedor de CI recibe destino local explícito para su ensayo, sin acreditar un volumen productivo.

### Consumidores y recuperación

La revisión posterior reprodujo tres herencias no autorizadas del SDK: AWS_CA_BUNDLE y proxies HTTP/HTTPS. Ahora el cliente fija verify=True y proxies vacíos.48 casos independientes (ocho composición/transporte y40 SDK/config previos) comprueban también factories web/API con local/S3 construido sin I/O remoto. No se añade soporte implícito de proxy ni CA personalizada.

El worker común renderiza PDF/logo privado en workspace temporal; publica PDF y guarda JSON/cuota/referencia en una transacción, retirando scratch. Respuestas nuevas llevan plan_id/pdf_url, sin paths físicos. Historial usa tiene_pdf/pdf_url; el flag indica referencia y no es una sonda remota de integridad. Los resultados idempotentes históricos se conservan sin reescribir el ledger. Descargas por ID y compatibilidad de último PDF comparten el límite autorizado. La ruta personal rechaza ID explícito cero/negativo/fuera de entero32; sólo omitirlo elige último.

GET `/api/gym/logo` requiere Bearer. Upload limita lectura/resultado a2MiB, decodifica PNG/JPEG/WebP, rechaza animación/superficies mayores de16MP y re-encodea sin EXIF/metadata fuente. Confirma ready y referencia antes de responder; sustitución incierta conserva logo previo y pending nuevo. No borra versiones/legacy. La UI privada requiere Blob autenticado, limpieza por cuenta/página y ningún fallback si hay referencia privada; su gate está separado.

La notificación existente lee PDF bajo tenant explícito y entrega bytes al helper de correo, sin reabrir rutas del DTO. Bytes válidos preceden al argumento legacy y usan nombre constante; inválidos no envían ni hacen fallback. Sigue best-effort, sin outbox durable, entrega real ni validación del límite efectivo del proveedor.

El lector legacy conserva raíz privada/límites/cabecera/rechazo de symlink. No acredita SHA histórico ni procedencia: los nombres antiguos pudieron colisionar. Una fila y un archivo no reconstruyen su contenido original. El inventario readonly en preparación detecta duplicados/mezclas/cambios/ausencias y exige revisión, sin escoger ganador ni migrar/borrar por intuición. El cálculo nutricional que consulta JSON histórico se mantiene separado y requiere R33.

Backup local toma primero snapshot DB y después archivos. Los bytes de referencias nuevas ready ya existían al confirmar DB y son inmutables; conservarlos sin GC forma parte del contrato. Restore25 verifica25 tablas,19 familias FORCE, cuatro metadatos (PDF/logo ready, pending huérfano y dueño ajeno), dos archivos legacy, relaciones, secuencias y SHA/tamaños. Reconstruye rol app/adaptador y aislamiento. No acredita bucket/versiones remotos, carga concurrente, RPO/RTO comercial ni retención.

Evidencia: DDL25 tiene18 QA más28 del coordinador en dos gates (12 migración,10 startup,6 contrato24), con fuentes/contratos estables. Consumidores tienen120 autor,16 worker/cuota y14 independientes de backend, incluidos cinco PG con rol restringido/pool1/core/PDF reales y un caso personal de ID. No sumar como suite final única. Véanse `storage25-root-review.json`, `storage25-ddl-independent-source.json` y `backend-r07-consumers-review-source.json` en evidence.

Los locks web/test Linux/Windows añaden seis dependencias SDK sin cambiar versiones previas. Instalación candidata con hashes y SDK/config probados; SBOM/SCA de resolución54 Linux/53 Windows sin vulnerabilidades conocidas al corte en `evidence/private-runtime-dependency-review.json`. No son SBOM/SCA ni ejecución de imagen. Quedan UI/CI/candidato final, migración histórica con procedencia/CAS, reconciliación y destino real/IAM/backup/sustitución de contenedor. No se compraron recursos ni subieron archivos reales.

Seguimiento independiente final del lote: tres casos API de equipo corrigieron una dependencia owner-only que impedía llegar a RBAC; nutriólogo usa cliente/cuota del owner, VIEWER no genera y ambos descargan su PDF autorizado. Browser25 pasó10 grupos/6 pantallas con44 fuentes estables, imágenes Blob realmente decodificadas y dos PDFs reales con logo privado; descarga histórica exacta y descarte tras cambio de sesión. CSP sólo permite blob en img-src. Sigue abierta una carrera distinta de refresh401 encontrada después de esos flujos; no se presenta este hito como aprobación de release.

## Antecedentes aceptados hasta9b97068

Los párrafos siguientes conservan el alcance de la preparación inicial, anterior al cutover descrito arriba. Sus referencias a consumidores/metadatos pendientes corresponden a aquel hito.

`web/storage/objects.py` define descriptor inmutable y puerto; los adaptadores de volumen local y S3 compatible exigen propietario explícito. Las claves opacas se generan en servidor, contienen un namespace derivado del dueño y no aceptan paths. Tipo, tamaño, asociación y SHA256 se validan antes de acceso; leer devuelve bytes acotados e íntegros. La aplicación aún debe autorizar la fila de metadatos con el principal persistido antes de invocar el puerto. Una clave conocida no es credencial.

Volumen local es transición de una réplica con raíz absoluta privada, montada y respaldada explícitamente. Publica por hard link exclusivo después de fsync de los bytes y rechaza symlinks estáticos. No demuestra aislamiento frente a un proceso hostil que ya puede modificar esa raíz. Un fallo después de publicar y antes de limpiar puede dejar objeto y temporal privado: el consumidor conserva descriptor/intención, comprueba el resultado y reintenta/reconcilia. No debe asumir que toda excepción significa que no se publicó nada ni cambiar referencias DB sin confirmación.

S3 recibe un cliente SDK ya configurado y bucket privado; no descubre credenciales ni crea recursos. PUT condicional evita sobrescritura y una repetición verifica bytes existentes. Los fallos del SDK se traducen sin mostrar URLs/credenciales ni escribir en un fallback local. Contratos consultados: [PutObject](https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/put_object.html) y [GetObject](https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/get_object.html). Se probó el modelo real del SDK boto3/botocore1.43.114 con Stubber; no un proveedor remoto.

Revisión independiente de frontend_finish: **33 aprobadas y una omitida en1.51s**, fuente y límites en `evidence/r07-storage-frontend-independent-source.json`. La omisión es creación de symlinks no autorizada por el host Windows; Linux debe ejercitar esa frontera. Se corrigió un TypeError por descriptor corrupto y se añadió el caso de fallo de limpieza posterior a publicación. El primer ensayo de autor tuvo un identificador pytest enorme; su causa/hash se conserva y no se cuenta como fallo del producto.

SDK de pruebas separado: `C:\Users\Consu\AppData\Local\Temp\metodobase-storage-sdk-20261018`, Python3.12.13, pytest9.0.2, boto3/botocore1.43.114. La ejecución explícita usa `--noconftest` porque estos contratos no requieren fixtures DB. El runner bloquea conexiones externas; el cliente Stubber usa endpoint loopback y credenciales sintéticas. No se alteró el venv web candidato ni se agregó todavía el SDK a sus locks.

## Composición explícita revisada

`web/storage/configuration.py` construye el adaptador a partir de un contrato tipado, sin leer credenciales ni escoger destino por su cuenta. Volumen exige raíz absoluta fuera de las rutas públicas; S3 exige bucket/región/credenciales explícitos. El endpoint admite HTTPS; HTTP sólo sirve para loopback de desarrollo. Se rechazan credenciales, rutas, query y fragmento en el endpoint. Ni las claves ni un endpoint inválido aparecen en el repr del contrato.

El cliente fija firma S3v4, timeout de conexión3s/lectura10s y dos intentos totales, e ignora overrides de endpoint del entorno. Las [opciones de Config](https://docs.aws.amazon.com/botocore/latest/reference/config.html) y su [precedencia](https://docs.aws.amazon.com/boto3/latest/guide/configuration.html) se contrastaron con la documentación1.43.114. Las pruebas usan el SDK real sin red y comprueban que perfiles, session tokens, credential_process y endpoints heredados no sustituyen la configuración explícita. Un fallo no crea un fallback local.

Revisión independiente de seguridad:32 aprobadas (27 autor y5 adicionales), fuentes estables en `evidence/security-storage-configuration-source.json`. Dos expectativas iniciales del harness confundían un atributo interno no conservado por el SDK y el endpoint regional AWS; se corrigieron para comprobar destino y credenciales efectivos, conservando `storage-configuration-harness-before.xml`. El factory aún no está conectado a Settings/startup ni a las rutas del producto; el SDK sigue en el venv de prueba separado.

Pendientes de implementación: tabla `stored_objects` y RLS posterior a cuota B2B, conexión de configuración al runtime, locks/SCA al incorporar SDK, generación/descarga/PDF/logo/correo por el puerto, inventario/migración de referencias históricas con fallos probados y respaldo de objetos. Pendientes externos: proveedor o volumen seleccionado, bucket privado/permisos, reemplazo real de contenedor y política de conservación/borrado aprobada. Los adaptadores no cambian todavía ninguna ruta del producto ni acreditan persistencia operativa. No se compraron recursos ni se subieron archivos reales.

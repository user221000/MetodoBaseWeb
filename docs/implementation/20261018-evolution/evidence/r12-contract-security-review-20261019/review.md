# Revisión independiente R12: contrato previo a schema29

Conclusión: el diseño v2 es aceptable para autoría y pruebas locales aisladas con su huella final contrastada. Esta revisión no acepta una migración29, implementación, política RLS o comportamiento concurrente que todavía no existen. No se conectó una base de datos ni se importó la aplicación; no hubo correo, proveedores o cambios de producto.

La preimagen original se conserva sin reescribir. Los 99 archivos de su inventario fueron copiados con sus bytes originales a un directorio privado y contrastados independientemente por AST y huellas. Se observaron 26 tablas de negocio, 20 familias tenant y 6 tablas de control, sin las tres entidades R12 y con head único `20261019_account_recovery`. Esto es una comprobación estructural, no una batería funcional verde de R12.

## Objeciones de diseño y disposición en v2

| Riesgo concreto detectado en la propuesta original | Disposición exigida y concretada por v2 | Estado de verificación |
|---|---|---|
| El destinatario podía leer una publicación pero carecía de UPDATE-USING para adquirir su lock. | SELECT y UPDATE-USING de destinatario acotados a publicación/link propios vigentes; WITH CHECK false y guards de inmutabilidad. El OWNER conserva su autoridad profesional separada. | Semántica de PostgreSQL revisada; lock positivo y DML negativo pendientes de PG real. |
| Consumir primero la invitación podía ocultarla o esconder el link pending antes del segundo UPDATE/RETURNING. | E sigue visible tras consumed por el mismo actor; expiry autoriza la transición, no visibilidad. Link pending admite esa imagen recién consumida y su primera activación exige C exacta. Guards obligatorios incluso cuando la rama gym es true. | Protocolo y predicados revisados; CAS/RETURNING, fallos y estados finales pendientes de implementar/probar. |
| Dos escrituras del servicio por sí solas no impedían confirmar consumed+pending o una aceptación atribuida a otra cuenta. | FK compuesta diferida sobre consumed_by y Link.user_id; consumed exige sujeto noNULL, activación inmediata exige recibo exacto, identidades inmutables; guards PG diferidos conservan proof hasta commit. TX raíz propia, rollback completo y sin reintento parcial. | Diseño concreto; equivalencia SQLite y controles PG pendientes. No se atribuye RLS a SQLite. |
| Copiar descriptor PDF sin bloquear StoredObject permitía insertar una proyección obsoleta después de invalidación. Una FK del mismo gym no probaba que fuese el PDF de ese Plan. | Plan → StoredObject → Publication, relectura exacta bajo lock y BEFORE INSERT invoker que exige Plan.pdf_object_id y descriptor íntegro. Ref presente inválida no se degrada a NULL. | Intercalaciones y SQL directo de descriptor ajeno pendientes de PG. |
| Un mutador que esperó al publisher podía no ver su publicación bajo snapshot antiguo. | READ COMMITTED obligatorio para publicación e invalidaciones relevantes; rechazo de otro aislamiento incondicional, sin consultar EXISTS desde el snapshot. Invalidación en SQL posterior al lock; VOLATILE no se presenta como solución a RR. | Compatibilidad estática revisada, valor runtime/default real no observado. Carreras RC y rechazo RR/SERIALIZABLE pendientes. |
| OWNER-A tiene rama gym válida para filas de A dirigidas a otras cuentas, aunque use una ruta de destinatario. | Cada endpoint/DTO/PDF/revoke/export de destinatario añade user_id=actor.id y active, nunca G como alternativa. OWNER legítimo propio o externo requiere proof exacta y conserva rol, cartera y barreras personales. | Diseño revisado; canarios de cada endpoint pendientes. No se inventa una prohibición comercial de OWNER propio. |
| Aceptaciones OWNER cruzadas o el orden legacy R11 podían formar un ciclo Usuario→Usuario. | Todos los Usuario requeridos deduplicados por ID total, NOWAIT en cada uno antes de recursos; revalidación del conjunto/rol/SV; contención produce rollback íntegro y 409 member_operation_busy. Ningún Usuario nuevo después de recursos. | Argumento de orden revisado; R11 bloqueado, reset/logout y casos cruzados pendientes de PG real. |

No se ejecutaron negativos funcionales contra un schema29 inexistente. Estos son contraejemplos de diseño que motivaron v2, no vulnerabilidades reproducidas de una implementación29 ni pruebas rojas de producto.

## Compatibilidad y límites que permanecen explícitos

`engine.init_db` no fija aislamiento; hereda servidor/rol/driver. La búsqueda estática en `web` y `api` sólo encontró un override REPEATABLE READ en `legacy_object_inventory.readonly_inventory_connection`, seguido de READ ONLY y rollback. Esta lectura no demuestra el default de producción o del servidor de QA. Las futuras pruebas deben observar RC sin imprimir URLs/credenciales, conservar inventario RR READ ONLY y flujos actuales de mutación, y rechazar escrituras invalidantes RR aun si su snapshot no ve publicaciones R12. No se modifica silenciosamente configuración del servidor.

El nuevo digest GUC queda limitado a invitación/link pendiente, sin run-as, cambios de tenant ni lectura de Cliente/Plan/StoredObject por destinatario. Debe instalarse vacío al inicio de toda TX de Session/Connection, permanecer hasta los guards del commit y limpiarse por fin de TX; los canarios de pool y savepoint todavía son obligatorios. Las 20 políticas históricas y los vocabularios/targets anteriores permanecen inmutables; schema29 requiere firma adicional de triggers/funciones y restore propio.

La publicación es explícita e inmutable. Generar otro plan no publica automáticamente. Un PDF legacy sin referencia canónica sólo puede dar un menú sin descarga; una referencia presente inválida rechaza la publicación completa. Soft-delete invalida/revoca en la TX, mientras DELETE físico con RESTRICT se rechaza entero. No se inventa retención, borrado histórico ni recuperación de contenido retirado.

La invitación llega al destinatario incluso antes de registrar su cuenta y requiere luego sesión más correo persistido canónico más token. El emisor no recibe bearer; correo, alias o Google login por sí solos no enlazan. El ACK sólo significa aceptación del proveedor. R14/R25, diario compartido, consentimiento y composición frontend/export continúan como integraciones expresamente pendientes; este diseño no completa todo el piloto R12.

## Gates exigidos antes de aceptar la implementación

Ejecutar los casos de la sección13.6 de v2 y la matriz de aceptación11 en bases UUID propias con rol app restringido: locks de lectura y DML denegado, RETURNING y postimágenes, SQL gym sin proof, rollback/commit incierto, FK/guards diferidos y GUC retirado, expiry después de espera, ambas carreras de Plan/StoredObject con invalidación, referencias PDF falsas, RC frente a RR y no-ops, OWNER propio/cruzado, R11/reset/logout, baja/soft-delete y restore29. Agregar pruebas HTTP de registro real antes de aceptación, límites, no enumeración, no logs de bearer/PII y headers de todos los métodos; el frontend tendrá revisión separada. No se sustituyen por las comprobaciones de AST de esta revisión.

## Semántica primaria consultada

PostgreSQL distingue USING de WITH CHECK y aplica SELECT/UPDATE-USING a los locks; RETURNING exige visibilidad de la nueva fila. Las políticas permisivas de una operación se combinan por OR. [CREATE POLICY](https://www.postgresql.org/docs/18/sql-createpolicy.html).

SET LOCAL tiene alcance de transacción; un rollback a savepoint puede revertir la instalación y un valor anterior de sesión vuelve a quedar vigente al terminar la TX. [SET](https://www.postgresql.org/docs/18/sql-set.html).

Los triggers de constraint pueden diferirse al fin de la transacción. Esto hace necesario mantener proof hasta el commit y tratar filas ausentes/invisibles como fallo. [Trigger definition](https://www.postgresql.org/docs/18/trigger-definition.html).

El reloj actual difiere del comienzo de transacción o sentencia; el corte de expiry debe ocurrir después de adquirir el lock. [Date/time functions](https://www.postgresql.org/docs/18/functions-datetime.html).

La volatilidad afecta el snapshot usado por SQL dentro de funciones, sin justificar ignorar el aislamiento de la transacción. [Function volatility](https://www.postgresql.org/docs/18/xfunc-volatility.html).

## Freeze revisado

Contrato v2 RAW SHA256 `3c28ccd2b784cbc028492ad5cb0ea427d74c3f488c241e7f57a24ecb14ff7a03`. Freeze RAW SHA256 `a98c158644e3b6b75f50382c1935f6cbd4e734116066512d4fa2a4d84a5f83bf`. HEAD de evidencia al cierre: `6e2b84c43ea418e892a558f55ad5dd88e21e00e3`. Las 99 dependencias originales conservan el agregado `b9eb4ef668768ed82e43c76c5873349ff3f381381c6bf22c454432ad297418c2`. Se añadió una dependencia estática separada (inventario legacy); no se atribuye al inventario99 del autor. El ZIP RAW del autor fue contrastado contra nuestras cuatro preimágenes; los dos JSON de Git normalizados a LF se distinguen de sus bytes RAW CRLF. La decisión es aceptar el diseño para autoría aislada, sin bloqueos documentales remanentes y sin aceptación runtime.

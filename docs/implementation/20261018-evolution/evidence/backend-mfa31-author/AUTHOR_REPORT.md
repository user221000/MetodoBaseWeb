# R32 / revisión31: candidato de autor aislado

Base30: `3c764d8486eb111f1dfa0ff2f238dd2ab0308792`. El commit R01/SEC11 `5316644608a09632a9997c25d50b1da3486ffc1b` es previo y separado: valida retornos del portal antes del circuito compartido. No cambia migraciones ni permisos. Este lote MFA requiere esa función compartida en su registro de acciones.

Se implementaron TOTP RFC6238, cifrado AES-256-GCM con clave separada explícita, alta y reemplazo con primaria fresca, kit recovery de128bits/un uso, login con challenge sin emitir sesión prematuramente, revocación de sesiones/SV, recuperación de contraseña que conserva MFA y grants de un uso ligados a operación/recurso/body/key/access/SV/generación. La verificación reciente conserva su instante original y nunca se prolonga por grant/refresh/consulta. El contrato UI estable es `../backend-mfa31-wire-contract.md` SHA256 `ad9ed0c62d2b367f6224ff3339998f1621a0537cf9efb5082bcf1d5e032cda2e`.

`app.mfa_actor` sólo abre los secretos del actor persistido. Se instala LOCAL tras identidad/locks, se vacía en BEGIN y no suplanta el tenant profesional. Las políticas nuevas son ENABLE/FORCE; no se reescriben las20 políticasv1, las de vínculos29 ni targets22–30. Las tres tablas nuevas llevan el esquema a32tablas de negocio y25familias protegidas (authorizations es control plane acotado). El startup existente verifica ownership sobre TODAS las tablas de Base, incluidas las nuevas. No hay roles SQL globales, HBA, proveedores o producción nuevos.

Las respuestas se capturan como primitivas antes del commit y sólo se devuelven tras ACK. Falta de confirmación devuelve503 opaco sin seeds/códigos/tokens/grants. El consumo de grant pertenece a la transacción de negocio/intención. El adaptador no realiza un segundo autocommit finalizador. El pool real de una conexión no necesita una Session secundaria para validar el acceso.

## Evidencia por tanda, sin sumar duplicados ni afirmar una suite final única

| Tanda | Resultado | Alcance |
|---|---|---|
| crypto inicial |22 verdes|Vectores RFC4226/6238 y AEAD propietario/generación/key|
| recent-google-path-after |61 verdes/2 rojos|Dos fábricas; vigencia original/copia/fecha/tipo/SV/generación/expiración, primaria Google, retorno. Dos rojos403 esperado vs503 por orden configuración/factor|
| unenrolled-config-after |2 verdes|Mismos dos casos403 después de reparar ese orden|
| pg-witness-services-ddl |17 verdes|Doce casos de servicio/HTTP/replay concurrente y cinco DDL PG con el testigo durable|
| lifecycle-asgi-business-after |40 verdes/6 fallos/2 casos con error|Los fallos/errores ASGI suceden antes del request por fixture; el resto incluye reemplazo/kit/revocar/SV, primaria, Google y ACK negocio, más cinco DDL SQLite|
| asgi-harness-after |17 verdes|Mismas aserciones ASGI tras corregir sólo harness|
| ddl31-final-after |10 verdes|Cinco criterios por SQLite y PG tras CAST final: vacío/poblado, repetición, downgrade, drift y rollback DDL|
| restore31-order-after |1 verde|Restore cifrado real, dos UUID,32tablas, firmas/RLS/índice, filas y objetos, histórico26–30 y MFA poblado|
| portal-sequence-after (R01 separado) |13 verdes|Inválidos→válidos sin resets del circuito y puerto SDK sintético|

La tanda17 de servicios fue anterior al cambio puramente representacional del CHECK31. Tras ese cambio se repitieron únicamente DDL y restore, como acordó el coordinador; no se presenta una repetición de servicios inexistente. Las fuentes y los89paquetes permanecieron iguales antes/después dentro de cada tanda mencionada. AST/F821/E9 y Bandit de producto nuevo no reportaron incidencias. Los resultados no incluyen MFA UI/browser ni aceptación independiente QA/SEC.

## Rojos conservados y causalidad

- `primary-before`: portal con sólo primaria aceptaba200 en ambas factories donde se requiere403.
- `pg-first`: cinco DDL verdes y doce fallos reales por lectura ORM lazy tras commit; el BEGIN vació correctamente la capacidad y RLS denegó. Se capturan primitivas antes del ACK, sin cambiar `expire_on_commit=True` de los tests.
- `pg-services-after`: tres verdes, siete fallos reales por Session secundaria del verificador con pool1 y dos fallos de harness spawn sin guard main. Se conserva launcher inicial; el verificador ahora usa MAC/contexto contra la identidad ya bloqueada. Los mismos servicios/replays posteriores pasan.
- Google: cuatro rechazos esperados faltaban cuando se confiaba en token recién emitido sin `auth_time` fresco. Se conservan antes y preimágenes. No se hicieron llamadas reales.
- ASGI: seis `AttributeError` por intentar parchear un flag en Settings aunque pertenece al módulo; dos setup errors por nodeid de32769bytes en Windows. `asgi-harness-causality.json` verifica SHA de la preimagen recuperada e igualdad de sus11asserts. No se atribuyen a producto.
- Restore31: primer intento conservaba cardinalidad23 del test30 y necesitaba incluir las dos familias nuevas. Dos intentos siguientes detectaron deriva real de un CHECK array al pasar por pg_dump/restore. CAST de literales solo no bastó porque PG volvía a coercionar según la columna varchar; CAST explícito de ambas columnas y literales TEXT estabiliza el mismo conjunto permitido. Se conservan todas las preimágenes31 y diffs; normalizadorv1 y22–30 intactos.
- Los intentos siguientes de restore exponen supuestos de la fixture nueva: ocho/cuatro refresh históricos frente a los tres MFA nuevos, una clave `id` donde la PK es `jti`, y un snapshot global situado después del cambio de contraseña legítimo del helper28. Se conserva cada salida. El nuevo helper31 copia las36asserts28 intactas, sólo limita el SELECT inicial a sus sujetos originales; no oculta las filas MFA del snapshot completo. El checkpoint MFA exacto se realiza antes del flujo HTTP28 que modifica legítimamente tablas auth.

`restore31-preservation-complete.json` acredita inversa texto/AST de los61asserts del test30 completo. `recovery28-current31-preservation.json` acredita inversa exacta de la copia de helper28 salvo un predicado a sus cuatro sujetos originales. Los archivos originales de30 y28 permanecen byteexactos. No se reduce ningún criterio histórico para admitir31.

## Restore poblado y recursos

Se restauraron tres factores activos para dos propietarios y un miembro, un reemplazo pending cifrado,24hashes recovery/cuatro usados, challenges/proofs/grants consumidos y no consumidos, con testigo reciente. Las semillas descifran sólo con la clave independiente/AAD original; no aparecen seeds, bearers, kits o tokens firmados en filas físicas. FORCE RLS aísla actor/tenant, actor ausente ve cero secretos, cambio de propietario se rechaza42501, challenges/grants consumidos se rechazan y un grant no usado se valida y revierte preservando filas completas.

Último restore: `metodobase_test_backup_8015db621605` y `metodobase_test_restore_8015db621605`, ambas ausentes por consulta explícita posterior en el recibo correspondiente. Los17 UUID de la tanda causal y los cinco PG del último DDL tienen recibos de creación PID/nombre/fecha y cierre/ausencia. Las tandas de restore fallidas también retiraron sus dos recursos exactos. No quedan pruebas/conexiones PG ni procesos propios de esta ola activos.

Eso NO es un cierre global del cluster. Permanecen cuatro candidatos de spawn anteriores SIN atribución suficiente: `metodobase_test_migrations_9a73e1b22ae0`, `metodobase_test_migrations_a5af7e53bc80`, `metodobase_test_migrations_77c0f33c1ffa`, `metodobase_test_migrations_4ed552798c78`. No se borraron ni se consultaron sus tablas. Inventarios/ventanas privadas están retenidos en Temp y root conoce ese límite. Otras bases/sesiones ajenas no se tocaron.

RAW privados se retienen con SHA. El prefix público tiene `* -text` desde su creación; los logs publicados son una proyección saneada con SHA RAW/publicado. El filtro conservador también puede sustituir nombres técnicos que coincidan con el formato22caracteres de recovery; no se afirma que tales coincidencias sean credenciales reales. Cada formato y sus bytes se preservan: no se normalizan evidencias para que pasen un hash. Código fuente normal distingue RAW de GitLF.

## Límites de aceptación

Pendientes UI, composición con MAIN/R24, QA y seguridad independientes, secretos/clave/backup operativos, transporte Google/Redis distribuido y entrega de correo reales. Los cambios de factor tienen auditoría persistida; este lote no conecta avisos de cambio de factor al correo y no acredita ese control ASVS. No hay un procedimiento administrativo real para recuperar ambos factores perdidos; se rechaza sin bypass. Las carreras simultáneas contra todos los canales reset/logout y la matriz de revisión independiente siguen pendientes: las pruebas de autor incluyen replay concurrente y revalidación tras cambios, no se afirma una carrera no ejecutada. No se declara despliegue, certificación ASVS/AAL2 ni resistencia al phishing de TOTP.

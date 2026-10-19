# Cambios de comportamiento

Commit `166038f88b211c52f0d149ce550880795361707c`, lote A1 local:

- Pro ya no se concede mediante POST de preferencias, suscripción incompleta ni redirect. Compra persistida antes del proveedor, conciliación Stripe/MP compartida y cuota individual reservada con idempotencia; callbacks viejos no revocan otra compra vigente. Compras históricas sin mapping y sandbox real siguen abiertos.
- Identidad consistente en contraseña/Google/refresh, roles/tenant persistidos, permisos desconocidos denegados y VIEWER sin alta. Logout incrementa versión de sesión; se retiró mantenimiento público. Tokens legacy tienen transición explícita; no hubo cierre de sesiones reales.
- DTOs comunes rechazan rangos inválidos y NaN/infinito. Exclusiones no dependen del pago, catálogo por solicitud inmutable llega a selectores/ajustes y valida resultado antes del PDF. Notas libres no se presentan como garantías clínicas; etiquetas históricas se representan como texto.
- Plan JSON y plan_id exacto se persisten junto con contadores. Tests ya no heredan destinos reales ni silencian preparación; fixtures/orden/UTF-8 y permisos Windows corregidos. Tres tests HTML pasan por la app SaaS real.
- Backup sin fuente falla; respaldo cifrado y manifiesto autenticado preceden restore a destino vacío. En R08 falta recuperar el esquema candidato/objetos históricos y verificar backups nativos.
- Fuente de catálogo compartida inicial, Free 10 aprobado, locks separados por OS con hashes; tzdata explícita evita fallos de zona horaria que el venv histórico ocultaba. Soporte desktop se mantiene; la resolución y pruebas GUI candidatas aún tienen su gate propio.

Gate congelado: 207 aprobadas, cero omisiones, 42.753 s; revisiones independientes enlazadas en VALIDACION/QA_R05. El commit no cierra por sí solo R01/R02/R05/R06/R08/R09/R10/R18/R19/R33.

Seguimiento abierto después de A1: carrera de GET al crear/resetear cuota; cuotas B2B y multiproceso; FeatureGate aceptaba moroso/expirado (tres regresiones reproducidas y corrección local en revisión); esquema/migraciones; compra y portal frontend, accesibilidad y diario persistente.

Compatibilidad prevista: parámetros opcionales del catálogo para consumidores desktop/legacy, precios sin cambios arbitrarios, tokens previos bajo transición explícita y migración aditiva. El estado final debe contrastarse con los contratos implementados antes de release.

## Hitos integrados posteriores a A1

- `af177b1` unifica catálogo y derechos efectivos: Free10 clientes, un plan por cliente/día y diez por gimnasio/día según las tres decisiones del usuario; desktop sigue soportado. Estados/expiración se resuelven de manera central. El catálogo no reemplaza las reservas atómicas B2B que siguen en revisión.
- `c769667` impide que un GET concurrente vuelva a crear/resetear cuota individual mientras otro proceso reserva el último crédito. Tres casos PostgreSQL multiproceso verifican el recorrido.
- `e8a6806` sustituye DDL/fallback de arranque por migración explícita, firma estructural y fallo no cero. R03 conserva su contrato de22 tablas y restore completo. `f325fc4` prepara asociaciones de proveedor y activaciones emitidas en un contrato nuevo de23 tablas, sin reinterpretar compras o licencias huérfanas.
- `501ceaa` activa17 familias RLS en bases de prueba, contexto por transacción y startup que rechaza privilegios de propietario/SUPER/BYPASS. Migrador y aplicación usan usuarios distintos; el servidor no hereda la credencial migradora. No se cambiaron roles ni políticas productivas. [Contrato](AISLAMIENTO.md).
- `b03e20a` conecta equipo e invitaciones con autoridad comercial persistida, token de un uso, CAS de roles y revocación de sesiones. Una expulsión conserva el espacio personal. Se mantiene compatibilidad acotada de enlaces históricos; cuentas con correo ya existente requieren el flujo de consentimiento aún pendiente. `19298e7` aclara el parseo JS y repite siete recorridos reales. [Contrato](EQUIPO.md).
- `4d03300`/`501ceaa` exigen propietario y licencia emitida vigente para activar hardware; el prefijo no concede derechos. Se impide sobrescribir hardware ajeno y se conserva el vencimiento emitido, también con sesiones PostgreSQL en México. La caché online exige licencia local verificable. [Alcance pendiente desktop](LICENCIAS.md).
- `0a0b6d4` hace atómico INCR/TTL Redis y acota fallos: las acciones sensibles fallan antes del handler si no hay limitador; lecturas/logout tienen degradación local limitada. La prueba con Redis real queda en CI, pendiente de ejecución. [Contrato](REDIS.md).
- `c45a71c` conecta compra/portal/estado de suscripción y corrige móvil/teclado con evidencia acotada; R11 añade recorridos completos auth/API/SQLite. No se atribuye entrega de correo ni lector de pantalla a esas pruebas.
- `abc896f` añade objetos privados inmutables con namespace de propietario, integridad y lectura acotada en volumen/S3 compatible. Todavía no cambia las rutas PDF/logo. [Contrato y límites](ALMACENAMIENTO.md).
- `9a53215` añade normalización de parámetros UTC sin cambiar tipos físicos ni datos históricos.32 pruebas independientes distinguen la corrección del desfase del driver. Aún sin adopción en modelos. [Contrato](UTC_DATETIME.md).

`9b97068` añade factory R07 con configuración explícita,32 pruebas independientes y sin descubrimiento de credenciales/endpoints ni fallback. `822de09` conecta Docker al lock con hashes y alinea manifest desktop con los targets ensayados; la revisión estática independiente no ejecuta la imagen.

`b81cfc1` integra reserva profesional antes de CPU, capacidad de clientes bajo lock de cuenta y ledger24 con RLS. Un retry con la misma clave/contenido devuelve la respuesta guardada; publicación y consumo no se compensan al perder respuesta o borrar FK. El helper de compensación protege también rollback y responde503 de reconciliación si no puede confirmar liberación, sin parámetros SQL en logs. Los nombres PDF son UUID y el worker está compartido entre web/API. [Contrato y pendientes UI/worker](B2B_CUOTAS.md).

`dbb6af5` integra exportación personal readonly en ambos factories y perfil, con descarga acotada por partes, manifiesto, sin datos de la cartera profesional ni persistencia de exportación en navegador. También contiene excepciones globales/alertas automáticas: sólo clase/contador/verbo HTTP reconocido, sin traceback, SQL ni metadata libre. No sustituye el workflow de borrado/retención ni sanea todos los sinks. [Alcance](PRIVACIDAD.md).

`e3039c2` incorpora gates y evidencia independiente:1621 aprobadas serial y con dos workers/orden mezclado, con387 Python/deps y55 frontend estables. Una omisión de symlink Windows queda explícita. La suite conserva sus límites de SQLite/dobles; las integraciones PG/restore y browser tienen gates separados. Las evidencias de cada hito se conservan por fuente/entorno. Ninguno de estos commits se publicó ni se desplegó.

`5bb5395` adopta UTC en52 columnas de instantes: un datetime con offset se convierte a UTC antes de escribir en TIMESTAMP sin zona. Se conservan dos fechas civiles y todos los resultados históricos. El cambio evita el desfase y vencimiento prematuro reproducidos bajo México; no modifica esquema ni intenta reparar historia.

`4e22852` añade contratos preparatorios del diario con35 pruebas, sin API/persistencia; `bc6804c` prepara IaC con SDK fijado, preservación de variables y guardas de destino/digest. La definición bloquea apply y necesita adopción/import real y prueba del loader/árbol final antes de aplicarse.

`31ad545` permite descargar el PDF exacto de un plan y conserva no-referrer en respuestas privadas; corrige el override global reproducido también en exportación. `93a9e1d` limita logs y telemetría de autenticación/correo a categorías, preserva auditoría local y añade adjunto PDF autorizado por bytes sin abrir archivos en ese camino. Storage25 y correcciones nuevas del wizard permanecen WIP en revisión.

## Checkpoint 0459b0f — Documentos privados y UI revisados

ddaf71a integra UI B2B idempotente, modal y descarte de respuesta al cambiar sesión sobre evidencia snapshot24.74d66e8 integra esquema25 con StoredObject y dos referencias nullable;0459b0f integra publicación/lectura privada, branding, configuración explícita en ambas factories y dependencias fijadas. El PDF exacto y el adjunto por bytes conservan sus lotes previos. Los objetos históricos mantienen referencia nula sin backfill, y un error de proveedor no elige otro backend. Restore25 y recorridos navegador tienen gates independientes. Ninguna infraestructura externa fue creada.

Hallazgos abiertos: SEC02 confirmado con dos casos rojos de refresh en memoria; riesgo individual postcommit deducido, en reproducción. Inventario histórico readonly y corrección cleanup en curso. No se ejecutó una suite completa del head nuevo ni scan posterior a b20e071.

## Checkpoint integrado26 / sesiones / CI

`bd6b067` integra inventario histórico readonly sin apply ni atribución de procedencia; `0e8cd42` compara expiración Float por epoch, conserva UTC de auditoría y hace visibles errores de cleanup mediante exit1 sin parámetros sensibles. Parámetros30/90 existentes, sin scheduler o política legal nueva.

`34d8fb1` publica Plan/objeto ready/consumo individual y marcador en una transacción; conserva consumo tras respuesta perdida o FKNULL. Captura periodo de suscripción bajo lock y filtra Plan/Cliente por mismo dueño y soft-delete. Legacy ambiguo no se reembolsa ni se enlaza por tiempo. El protocolo nuevo requiere drenar workers antiguos al migrar; no se aplicó live.

`754d56d` vincula refresh/reintentos/lecturas al contexto de sesión inicial y comparte una promesa que siempre resuelve sus consumidores. Fallos parciales de Storage bloquean I/O hasta guardar o limpiar completamente el par.74 VM independientes y navegador actual aceptan esta contención por instancia; reload/cross-tab y otros escritores siguen abiertos. El candidato histórico275 se preservó por SHA exacto en copia, sin inventar commit.

`6d33b9e` exige reportes Node tipados/no vacíos,17 JUnit PG y cinco fixtures navegador con logs diferenciados. QA actual36 grupos/19 pantallas más3 Storage; serial1813/1skip Windows, n2shuffle1813/1skip en133.73s,519 fuentes y89 paquetes estables. No se ejecutó Actions, imagen Linux ni Redis real. Desktop41ad55f y UI individual se desarrollan en worktrees separados y aún no integrados.

## Checkpoint local 19 de octubre: UI, disponibilidad y procedencia

Integrados c11256a (UI personal40fd2af),0fa124e (SEC037321d3b) y desktop3930398/171a8f0/9f3f32e. Estadísticas ba4deb4 ya tiene QA independiente0e4bc07. Evidencias del autor y de QA se mantienen separadas, incluida reproducción de400 tras commit, HTML con CSP activa, source flags y controles binarios/CR aislado.

La receta desktop exige bytes exactos para controles ASCII/DEL/CR aislado; ESC es conservador aunque Git lo considere texto. La primera compilación9f3f32e rechazó un log ANSI convertido por autocrlf antes de Analysis; fuentes estables y diagnóstico preservados. Se ensaya el mismo commit en checkout LF sin cambiar configuración Git. Todavía sin artefacto aceptado, Inno, firma o publicación.

CI incorpora operación personal18+2 y sexta fixture15/8pantallas con formatos tipados de reporte. QA encontró que dos tests batch Windows se colectarían con skip en webUbuntu: ahora se enrutan explícitamente al targetWindows y se excluyen por nombre en la recetaLinux; tests portables se mantienen en ambos targets desktop. Guard exige los dosJUnit no vacíos y sin skips/fallos/errores.91 canarios del guard y9 del nuevo routing aceptados independientemente, sin ejecución remota.

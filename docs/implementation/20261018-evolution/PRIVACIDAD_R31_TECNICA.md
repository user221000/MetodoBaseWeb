# R31: solicitudes, cierre y disposición por categoría

Fuente aislada posterior a revisión38. Trabajo exclusivo del servicio web;
ninguna prueba, migración, consulta SQL o navegador se ejecutó en esta preparación.
Los targets39 SQLite/PostgreSQL están pendientes de captura real Root. No hay
targets sintetizados, create_all, stamp ni reparación automática de esquema.

La solicitud propia se guarda con clave UUID idempotente, sujeto persistido y
versión CAS. Su UUID no autoriza lecturas. El cierre es otra operación, con DTO
cerrado y confirmación de intención close_account. Reutiliza la prueba persistida
purpose=reauth, su acceso exacto, SV, generación y TTL; exige el factor vigente
cuando existe. El consumidor interno permite sólo password y privacy, con
presupuestos de factor distintos. El wrapper de contraseña conserva su firma y
secuencia original; no se amplía el CHECK login/reauth/action ni se emite un grant.

Los locks Usuario globales preceden a solicitud y refresh. Cerrar cuenta confirma
en una transacción la prueba, el comprobante durable y sus categorías, SV+1,
revocación de refresh, activo=false y limpieza de pruebas pendientes. Mantiene la
fila Usuario y los factores activos, sin cambiar correo, cancelar suscripciones
o tocar terceros. El cierre de acceso no acredita borrado integral. Tras el
cierre, los tokens previos no sirven para consultar el estado: queda la consulta
operativa autorizada y el recibo inicial.

OWNER, tipo profesional/administrativo, pertenencia profesional y obligaciones
de equipo, suscripción, pago o intención sin resolver bloquean el cierre. No se
adopta una cartera ni se interpreta el fin de acceso como cancelación de pagos.
La política productiva aún no está configurada: sin proveedor explícito, la
solicitud permanece bloqueada. No hay una política permisiva predeterminada.

PrivacyPolicy exige ID, versión, digest, inventario completo de tablas, decisión
explícita por categoría, ventana de vigencia y revisión de holds. Esa ventana es
vigencia de una versión técnica, no un plazo legal de retención. Un inventario
nuevo, desconocido, hold pendiente o política caducada impide ejecutar. El sistema
no inventa plazos, bases jurídicas ni autorización de encargados.

El ejecutor hace DELETE reales y acotados de personal_diary_days con user_id exacto
y client_progress con gym_id propio y Cliente propio al mismo tiempo. Cada lote
borra como máximo200 filas por categoría. Conserva rows ajenas y relaciones
ambiguas; estas últimas quedan bloqueadas. FK o restricciones append-only no se
deshabilitan y generan resultado bloqueado. Los dos ledgers39 preservan identidad,
versiones y resultados; no sustituyen a una auditoría por notificaciones o tareas.
Repetir un lote ya aplicado conserva su resultado y no suma filas borradas.

Las demás categorías se conservan como blocked, retained_by_policy o
pending_confirmation. El ledger38, consentimientos, R12, seguimiento,
notificaciones y sus triggers/FK permanecen intactos. Las categorías retenidas o
externas pendientes impiden declarar completed integral. La salida distingue
account_closed, estado global y estado de cada categoría.

El export nuevo es una colección independiente y paginada de hechos propios de
contexto personal. Usa campos tipados permitidos, fuente personal verificable,
cursor exacto sin normalizar, límite200 y presupuesto128KiB. Conserva el contrato,
los cursores y los presupuestos del export anterior. No abre la cartera OWNER ni
reclasifica filas históricas. La UI permite solicitud/consulta, descargar páginas
de hechos y preparar el cierre con confirmación explícita, reautenticación
primaria y el factor actual. Conserva los estilos y la paleta existentes y no
altera PPL. La política ausente conserva la cuenta abierta y requiere revisión.
Un cierre confirmado SV+1 retira la sesión y muestra sólo el recibo mínimo ligado
a su boundary, sin otra consulta /me, refresh ni reintento. Un resultado ambiguo
retira la sesión local sin afirmar cierre en servidor ni borrado integral.

La vista ?operacion=privacidad en las mismas rutas de seguridad omite el widget
de contraseña y reserva a privacidad una sola inicialización GIS. La identidad
Google pasa por el consumidor reauth existente; no crea grants ni cambia sus
controles de frescura. El intento opaco liga sesión, solicitud, versión,
confirmación y factor; editar, cancelar o cambiar sesión descarta el callback.
El recibo se reinserta en main tras la limpieza del session shell y una cuenta
posterior lo retira. Estas conductas están implementadas en fuente y preparadas
para pruebas; aún no hay ejecución Node, proveedor real o navegador nativo39.

El CLI scripts/privacy_disposition.py permite inspección propia operativa y un
lote apply con sujeto/solicitud, CAS, destino exacto, política firmada y clave de
autenticación independiente explícitos. No programa jobs ni activa servicios.
No se ha ejecutado contra datos reales ni ha leído la clave de custodia backup.

El wrapper restore_with_suppressions mantiene restore_backup original como
recuperación de bytes. Antes exige un gate real de aislamiento suministrado por
el operador y un registro externo autenticado, versionado, con generación mínima,
watermark requerido, edad máxima y reloj vivo explícitos. Ausencia, antigüedad,
firma inválida, duplicados o fallo dejan cuarentena. Migra/verifica el destino
aislado, vuelve a desactivar sujetos cerrados, revoca sesiones viejas y aplica los
borrados admitidos. Comprueba de nuevo la autoridad al finalizar. Nunca habilita
acceso automáticamente y conserva quarantine_required=true. Un marcador de
archivo no se presenta como prueba de aislamiento de red.

encode_registry produce el payload autenticado de un registro completo explícito;
el almacenamiento externo, su CAS/antirollback durable, custodia y publicación de
watermarks completos siguen requiriendo integración operativa real. El lector
exige esa autoridad externa y nunca la infiere de un snapshot anterior o de una
sola solicitud. Las pruebas preparadas usan claves y políticas sintéticas, sin
atribuirles validez jurídica o custodia productiva.

Validaciones preparadas: transacciones/proof y fallo de commit, presupuesto MFA
privacy separado, regresiones literales de contraseña, aislamiento de terceros,
DELETE reales e idempotencia, propiedad ambigua, HTTP de ambas factories, export
personal, política fail-closed y restore cifrado SQLite desde snapshot previo al
cierre. Falta coleccionar/ejecutar, peer independiente, PostgreSQL funcional,
captura39 genuina, navegador/Node y regresiones amplias de la fuente final.

México es el mercado inicial. Los14 datos comerciales/jurídicos y las revisiones
profesionales siguen externos y sin inventarse. Esta implementación no declara
cumplimiento jurídico, borrado de todos los datos, RPO/RTO, eliminación externa o
autorización para publicar/desplegar.

Revisión child: el destino restaurado se verifica mediante archivo SQLite real
o endpoint/DB/OID/generación PostgreSQL observados. La conexión de migración y
cada Session de supresión deben corresponder al mismo destino antes de acceder a
filas; no hay callback libre que elija otra base. El gate recibe también ese
destino explícito. El CLI y el consumidor de restore ejecutan el verificador de
rol sobre su conexión efectiva, sin owner/superuser. La limpieza MFA liga el actor
autorizado de la supresión. Categorías antes marcadas deleted se consultan de
nuevo y suprimen las filas propias reaparecidas. Un fallo del flush previo al
savepoint propaga a rollback del llamador y no se etiqueta como hold de categoría.
PostgreSQL requiere endpoint numérico/localhost y puerto explícito para este
binding inicial; DNS/proxies aún requieren integración revisada y quedan cerrados.

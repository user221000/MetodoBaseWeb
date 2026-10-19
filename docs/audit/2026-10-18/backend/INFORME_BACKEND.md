# Auditoría de backend arquitectura y seguridad de MetodoBase

Fecha: 18 de octubre de 2026. La prioridad inmediata es asegurar cobros, permisos, aislamiento y persistencia antes de ampliar la captación de gimnasios. Hay controles útiles implementados, pero varias rutas evitan esos controles y la configuración real de PostgreSQL no aplica el aislamiento RLS descrito en el repositorio.

La revisión combina lectura de código, diez reproducciones en SQLite efímera y consultas de catálogo de PostgreSQL de producción en una transacción de solo lectura. No se consultaron registros de negocio, contraseñas, tokens de usuarios ni información de clientes. No se ejecutaron compras, cambios de cuenta, migraciones ni pruebas de ataque contra producción. Los identificadores P0/P1/P2 expresan prioridad de producto y remediación; no son puntuaciones CVSS ni una certificación de cumplimiento.

## Evidencia verificable

- [Reproducciones locales](reproduce_security_findings.py) y [resultados JSON](local-reproduction-results.json). Python 3.12.13; FastAPI/TestClient, SQLite en memoria y red externa bloqueada. Se montaron los routers pertinentes, sin modificar sus funciones. Dos casos reemplazan exclusivamente la llamada al proveedor o al generador CPU/PDF para observar el control de acceso y la persistencia.
- [Catálogo de producción saneado](production-metadata.json) y [script de consulta](read_production_metadata.py). Railway joyful-quietude, entorno production. Se leyeron únicamente versión, rol, límite de conexiones, banderas/políticas RLS, constraints de subscriptions y existencia de alembic_version. Las URLs de conexión se mantuvieron en memoria y no se guardaron ni imprimieron.
- [Resumen SCA del lock](pip-audit-lock-summary.json). `pip-audit --no-deps --disable-pip -r requirements_web.lock --format json`. No equivale al inventario de paquetes instalado en Railway.
- [Prueba aislada de exclusiones](probe_food_exclusions.py) y [resultado](food-exclusions-probe.json). Ejecuta mediante AST el bucle original con un catálogo sintético, sin importar la aplicación ni generar planes finales.

La inspección del catálogo devuelve PostgreSQL 18.6, `max_connections=500`, rol `postgres` con `rolsuper=true` y `rolbypassrls=true`. La configuración DATABASE_URL de la aplicación usa ese mismo usuario y nombre de base. Las veinte tablas públicas tienen RLS desactivado, no hay políticas y no existe `public.alembic_version`.

## Hallazgos que bloquean crecimiento o cobros confiables

### B01 P0 Activar Pro sin pago y antes de confirmar Stripe

`web/routes/usuario.py:543` admite `POST /api/usuario/suscripcion` con `{"plan":"pro"}` y persiste el plan, el límite y `status=active` sin intervención de un proveedor. Reproducción local: HTTP 200 y Pro habilitado. `usuario_stripe_subscribe` en la línea 619 hace lo mismo tras crear una suscripción que puede estar `incomplete`. `usuario_confirm_subscription` en la línea 659 activa Pro incluso cuando el servicio devuelve `activated=False`: también reproducido.

Aceptación: un usuario no puede adquirir derechos de pago mediante un cambio de preferencias. Los derechos se actualizan desde un servicio único tras confirmar identidad del cliente, precio/moneda, estado del proveedor y período pagado. Tarjeta rechazada, autenticación pendiente o `activated=False` conservan el plan gratuito. Los escenarios deben pasar por API con proveedor de pruebas y webhooks firmados.

### B02 P1 El plan Pro pagado no cabe en el esquema de suscripciones

`web/constants.py` define `pro_usuario`; `web/services/stripe_service.py:286` confirma esa compra mediante `activate_subscription`. `web/database/models.py:336` restringe `Subscription.plan` a free, standard, gym_comercial y clinica. El catálogo de PostgreSQL confirma el mismo constraint en producción. Reproducción local: `activate_subscription(..., "pro_usuario")` produce IntegrityError. Un cobro correcto puede terminar sin activación fiable.

Aceptación: separar explícitamente suscripciones B2B y B2C o usar un modelo común consistente. Pruebas de compra, renovación, cancelación, reembolso y pago fallido actualizan el derecho correcto para ambos tipos de cuenta. Ningún cobro queda sin reconciliación por una restricción del esquema.

### B03 P1 La generación individual no aplica ni registra la cuota mensual

`web/routes/usuario.py:310` genera sin consultar `UserSubscription`, comprobar `max_planes_mes` o incrementar `planes_usados_mes`. Reproducción con Starter agotado 1/1: HTTP 200, generador invocado y contador intacto. La interfaz puede mostrar un límite que el servidor no impone.

Aceptación: reservar cuota de forma atómica antes de generar, devolverla cuando el trabajo falle según la política definida, consumirla una sola vez ante reintentos y usar la zona/período del producto. Dos solicitudes simultáneas con un crédito restante producen como máximo un trabajo aceptado.

### B04 P1 PostgreSQL opera sin RLS ni control de migraciones y la app usa superusuario

Producción: todas las banderas RLS son falsas, políticas vacías y ausencia de alembic_version. La app está configurada con el rol postgres superusuario/BYPASSRLS. Un filtro `gym_id` omitido en código no tendría una segunda barrera de base de datos; esto no demuestra que hoy exista acceso cruzado explotable.

El código contribuye al problema: `db_bootstrap.py:56` hace create_all y, en una base nueva, `:80` hace stamp(head), sin ejecutar las políticas o backfills de las migraciones. `:117` oculta errores de upgrade. `web/main_web.py:160` vuelve a crear tablas en startup y la revisión de versión solo emite advertencias. El hook Railway se revisa en el informe principal de infraestructura.

Aceptación: inventariar y reconciliar el esquema existente con un plan de migración probado en un clon, backup y restauración verificada. Ejecutar migraciones con un rol separado; la app usa NOSUPERUSER/NOBYPASSRLS y permisos mínimos. Una base vacía llega a head ejecutando migraciones, incluidos datos y políticas; cualquier error aborta el despliegue. No ejecutar stamp indiscriminadamente sobre producción.

### B05 P1 Habilitar RLS exige reparar primero el contexto de todas las sesiones

`web/database/engine.py:128` instala tenant solo en get_db/get_db_readonly y solo al principio de la transacción. `web/middleware/tenant.py:61` ignora usuarios individuales sin equipo. `web/routes/planes.py:88` y `:293` abren SASession directamente; webhooks en `web/routes/billing.py:301` y `:505` abren SessionLocal sin tenant. Los commits internos terminan el SET LOCAL y la siguiente transacción de esa sesión no lo reinstala. Activar FORCE RLS con un rol restringido puede romper generación, perfil individual, cobros y otras lecturas.

Aceptación: una fábrica de sesiones/unidad de trabajo instala el tenant validado en cada transacción, también en workers. El consumidor de webhooks resuelve el tenant desde un identificador de proveedor confiable y usa un permiso explícito. Pruebas reales PostgreSQL con dos gimnasios, miembros, cuenta individual y usuario sin tenant verifican denegación cruzada y funcionamiento completo, incluidos commits internos y devolución de conexiones al pool.

### B06 P1 La identidad de equipo se pierde al entrar y refrescar

`web/auth.py:238` consulta ya la misma tabla usuarios que el supuesto fallback de equipo. Construye el rol a partir de tipo y omite team_gym_id; por ello el fallback de `web/routes/auth.py:95` queda sin uso para credenciales válidas. `_get_user_by_id` en `web/auth.py:543` repite la pérdida al refrescar. Reproducido: ambos flujos devuelven viewer sin asociación. Google en `web/routes/auth.py:217` también infiere owner para cualquier tipo usuario y omite la membresía. Registro, contraseña, Google e invitación no producen la misma identidad.

Aceptación: una sola función transforma el usuario persistido en identidad autenticada; conserva rol y membresía validados y distingue cuenta individual de miembro. Login, OAuth, invitación y refresh entregan los mismos permisos. Cambiar rol o quitar acceso surte efecto según una política de revocación explícita.

### B07 P1 Un VIEWER puede crear clientes

`web/routes/clientes.py:72` depende de check_daily_registration_limit, pero ni la ruta ni esa dependencia verifican `create,cliente`. La tabla de permisos niega esa acción a viewer. Reproducción local: token viewer con team_gym_id válido crea un cliente del gimnasio con HTTP 201, aunque has_permission devuelve false.

Aceptación: permisos obligatorios por ruta o caso de uso, además de cuotas. Matriz API por rol y recurso: viewer solo lee; no crea, actualiza, elimina ni elude restricciones a través de rutas individuales. Validar también la propiedad del recurso en cada caso de uso.

### B08 P1 Los accesos emitidos sobreviven a logout desactivación y cambios de rol

`web/auth.py:420` verifica firma, tipo y expiración sin revisar estado del usuario o versión de sesión. Logout revoca refresh, pero el access sigue válido. `config/settings.py:63` permite siete días de access con remember_me; Google activa remember_me siempre. Reproducción: el access del owner sigue válido tras desactivar su fila y revocar refresh. Miembros expulsados pueden conservar permisos del token anterior hasta la expiración.

Aceptación: access breve también al recordar sesión, refresh rotativo revocable y una versión de sesión/estado del usuario consultada con caché de invalidación controlada. La prueba API de usuario borrado/desactivado o rol reducido debe fallar dentro de un SLA definido. No basta con vaciar localStorage del navegador que ejecutó logout.

### B09 P1 Perfil individual sin límites de validación y notas fuera del generador

`web/routes/usuario.py:34` acepta números sin rangos; update_perfil solo valida algunas enumeraciones. Reproducción: edad -5, peso -80, estatura 0 y grasa 150 persisten con HTTP 200. El flujo gym sí usa límites Pydantic en api/schemas.py. La reconstrucción del cliente en `web/routes/planes.py:96` omite notas, aunque la UI invita a registrar condiciones especiales; los detalles de esa promesa se describen en el informe UX.

Aceptación: los dos portales comparten validadores de dominio con rangos coherentes y rechazo de NaN/infinito. Reglas de restricciones, alergias e información clínica deben tener un contrato estructurado y verificable; la UI no debe prometer que un texto libre modifica el plan si el motor no lo consume. Validación profesional de seguridad nutricional antes de promocionar usos clínicos.

## Hallazgos adicionales y deuda operativa

| ID | Prioridad | Evidencia y efecto | Criterio de aceptación |
|---|---|---|---|
| B10 | P1 | `scripts/backup_daily.py:44` respalda únicamente archivos SQLite; no PostgreSQL. Si todos faltan, el script sale exitosamente. No incluye PDFs/logos. | Respaldo PostgreSQL y objetos, retención cifrada, fallos alertados; restauración en entorno aislado medida contra RPO/RTO acordados. Verificar backups Railway existentes antes de concluir ausencia de respaldos del proveedor. |
| B11 | P1 | PDFs en CARPETA_PLANES y logos en web/static/uploads. Sin almacenamiento duradero de aplicación confirmado por revisión Railway del equipo. Las rutas de descarga exigen archivos en disco. | Objetos privados durables con autorización por tenant y descarga firmada o streaming; prueba de descarga del mismo PDF tras redeploy y desde cualquier worker/replica. Logo y plan sobreviven al despliegue. |
| B12 | P1 | `web/rate_limiter_redis.py:74` permite toda solicitud ante fallo Redis. Logs de producción inspeccionados por el equipo contienen este fallback. Dependency de login usa otro limitador en memoria. | Fallback local acotado y alertas de degradación; protección por cuenta/IP distribuida en login, refresh e invitación; pruebas con Redis caído y cuatro workers. No cerrar toda la aplicación por una falla de caché. |
| B13 | P2 | `web/routes/billing.py:484,533` responde HTTP 200 a fallos MercadoPago, perdiendo el mecanismo de reintento. Firma usa data.id de query pero procesa id de body sin exigir igualdad; no valida antigüedad. MP no estaba configurado en producción en esta revisión. | Autenticar y vincular el evento completo, validar replay, conservar inbox duradero; responder reintentable ante fallo temporal; reconciliación periódica. |
| B14 | P2 | `subscription_service.py:77` usa cadena vacía como stripe_subscription_id para pagos MP, sobre columna unique. Reproducido: el segundo destinatario MP falla IntegrityError. | IDs ausentes como NULL, claves del proveedor separadas y constraint único apropiado; dos compras MP independientes completan sin colisión. |
| B15 | P1 | Stripe gestiona Subscription, mientras rutas individuales mantienen UserSubscription. Cancelación/pago fallido en `stripe_service.py:576,621` no actualizan UserSubscription. checkout.completed activa sin comprobar payment_status ni diferidos. | Estado canónico de derechos por sujeto; eventos duplicados, fuera de orden, retrasados y pagos diferidos convergen al estado actual del proveedor; no acceso de pago después de cancelación/impago fuera de la política. |
| B16 | P2 | `stripe_service.py:208` crea Customer antes de la llamada idempotente Subscription.create; un fallo/reintento puede dejar objetos huérfanos. ID de suscripción se deriva de gym/plan/payment_method y no de intención de compra persistida. | Persistir intención y claves idempotentes por operación; reintentar sin duplicar Customer/cobro, conservar estados recuperables y reconciliar fallos DB posteriores al proveedor. |
| B17 | P2 | `web/routes/planes.py:53` usa locks por proceso y generación con to_thread; cuotas se consultan antes del lock. Cuatro workers no comparten locks ni límites transaccionales. | Reserva atómica de cuota, idempotencia por solicitud, jobs con estado/reintentos y límites CPU; prueba concurrente de último crédito y mismo cliente entre workers. |
| B18 | P2 | `repository.py:520` crea defaults de membresías al leer si la lista está vacía, sin uniqueness de plantilla. QA UX observó diez planes tras lecturas concurrentes. | Crear defaults en onboarding transaccional con unique(gym_id,template_key) y upsert; lecturas paralelas nunca duplican. |
| B19 | P2 | Registro exige doce caracteres (`auth.py:202`) e invitación seis (`team.py:585`); invitaciones DateTime sin timezone se comparan con UTC aware (`:578,658`). Faltan rutas de recuperar contraseña, verificación de email, cambiar credenciales y MFA utilizable. | Política común, bloqueo de contraseñas comprometidas, flujos de recuperación/verificación seguros; MFA/passkeys al menos para owners; invitación probada en PostgreSQL y SQLite con tiempo UTC coherente. |
| B20 | P2 | `auth.py` usa formato HMAC propio sin versión de clave, issuer/audience o inventario de sesiones; `routes/auth.py:378` expone mantenimiento de tipo mediante el mismo secreto de firma. Tokens refresh/access están en localStorage. | Preferir sesiones o biblioteca de tokens revisada; rotación de claves y audiencias verificadas; eliminar endpoint de emergencia del runtime público o convertirlo en operación administrativa con identidad/MFA y auditoría. Reducir exposición de tokens y verificar XSS en todos los sinks. No se confirmó un exploit XSS en esta revisión. |
| B21 | P1 | Docker instala requirements_web.txt con rangos flotantes; lock difiere de txt (adaptador PostgreSQL distinto; faltan paquetes web). SCA del lock: 68 registros, 37 advisories distintos en siete paquetes. | Lock actualizado compatible Linux/Python3.12 con hashes, build que lo usa, SBOM y scan de imagen final y dependencias; tratar exposición por alcance real. No atribuir resultados del lock a paquetes de producción sin inventario instalado. |
| B22 | P2 | ClienteUpdate difiere de Create; PerfilUpdate duplica reglas; manejo de excepciones en clientes y planes devuelve str(exc). `has_permission` otorga a owner permisos no definidos. | DTOs comunes, errores de dominio con código público estable/request_id, detalles internos solo en logs saneados; denegar acciones no registradas a todos los roles. |

### B23 P1 El filtrado conserva una categoría totalmente excluida y modifica catálogos compartidos

`web/routes/planes.py:166` calcula la lista filtrada, pero `:168` solo reemplaza los elementos cuando esa lista no está vacía. Al excluir todos los alimentos de una categoría, conserva íntegra la lista original. La prueba aislada ejecuta ese mismo nodo del AST: ambos elementos sintéticos excluidos permanecen disponibles. Esta evidencia confirma el fallo del filtrado; no demuestra qué alimento devolverá un plan final ni un efecto clínico.

Existe además un riesgo de concurrencia inferido del código: `:152` solo toma `_categorias_lock` para solicitudes con exclusiones, mientras `:179` modifica referencias globales CATEGORIAS de varios módulos. Una generación sin exclusiones no espera ese lock y puede leer el catálogo temporal de otra solicitud; `core/generador_opciones.py:235` consulta esas referencias durante la selección. No se ejecutó una reproducción concurrente completa ni se probó contra producción.

Aceptación: pasar un catálogo inmutable por solicitud/caso de uso a todos los selectores, sin modificar globals. Si las exclusiones dejan sin alternativas una categoría requerida, devolver un error de dominio claro o una sustitución explícitamente validada; nunca restaurar silenciosamente alimentos excluidos. Pruebas de exclusión total, parcial y generación simultánea con restricciones distintas deben verificar resultados independientes y ausencia de alimentos prohibidos. Vincular este criterio al trabajo de garantías del motor R33 del roadmap principal.

## Arquitectura actual y cambio incremental

El servidor publicado entra por `web/main_web.py`; registra routers, middleware y persistencia SQLAlchemy. Los routers realizan simultáneamente autorización, reglas de suscripción, consultas, commits, llamadas a Stripe/MercadoPago y transformaciones de presentación. `web/database/repository.py` aplica filtros gym_id en los accesos examinados; esa es hoy la barrera efectiva del tenant.

El cálculo nutricional vive en core y parte del catálogo/persistencia histórica en src. Hay servicios de core y repositorios orientados a la migración gradual, pero el flujo web invoca constructores y exportadores directamente desde la ruta de generación, cambia referencias globales CATEGORIAS y maneja archivos y sesiones propias. Los reexports `web/schemas.py` y `web/dependencies.py` siguen importando api, por lo que no eliminan la dependencia; sus comentarios dan una impresión de desacoplamiento mayor que la existente. Coexisten `api/app.py`, desktop y web, además de documentación que aún describe bases separadas aunque `web/auth.py` ya usa el engine compartido.

Conviene mantener un monolito modular. Extraer casos de uso sin rehacer el motor ni dividir prematuramente en microservicios:

| Módulo | Contrato de aplicación | Adaptadores |
|---|---|---|
| Identidad y equipos | Identidad válida, sesiones, membresías y permisos por tenant | PostgreSQL, OAuth, email y autenticación fuerte |
| Clientes y progreso | CRUD, vínculo usuario-cliente-gym, historial y consentimiento | Repositorios PostgreSQL y DTO HTTP |
| Nutrición | Perfil validado, restricciones, GeneratePlan y resultado versionado | Motor core puro, catálogo versionado, cola, PDF y storage |
| Cobros y derechos | Crear intención, reconciliar proveedor, calcular acceso y reservar cuota | Stripe/MP, inbox/outbox y repositorio transaccional |
| Operación | Estado de jobs, auditoría, métricas, respaldos y salud | Redis, telemetría, Railway y almacenamiento de objetos |

Los routers deben traducir HTTP a casos de uso y sus resultados. Una unidad de trabajo controla transacciones y contexto tenant; los repositorios reciben un tenant explícito. El dominio no importa FastAPI, SQLAlchemy, directorios del servidor ni SDKs de pago. Core devuelve datos y metadatos de cálculo; el worker produce objetos/PDF. Eventos de cobro entran primero a un inbox duradero y los correos se envían mediante outbox tras confirmar la transacción.

El modelo de tenant debe dejar de hacer del owner la identidad del gimnasio: entidad Gym/Organization y Membership con rol, más enlace Client.user_id opcional y acceso por membresía verificable. La cuenta individual puede tener un espacio personal sin convertirse en miembro empresarial por compartir tipo usuario. Esto permite transferencia de propiedad, varias sedes y un cliente vinculado a su gimnasio, capacidades que hoy no están expresadas correctamente.

## Roadmap técnico propuesto

Estimaciones orientativas para un equipo pequeño con backend, QA y apoyo DevOps; no son compromisos de calendario. Priorizar criterios de salida y cambios revisables sobre una reescritura extensa.

1. **Contención y cobros, días 1 a 5.** Cerrar B01, B02, B03 y B07; corregir identidad de equipo B06 y duración/revocación B08. Pruebas API negativas obligatorias para permisos y cobros. Crear reconciliación de compras afectadas usando datos autorizados por el equipo, sin modificar suscripciones automáticamente desde la auditoría.
2. **Datos y despliegue, semanas 1 y 2.** Verificar backup/restauración antes de cambiar esquema. Reconciliar historial Alembic, defaults Enum y restricciones con PostgreSQL real; hacer que migraciones aborten ante fallo. Separar rol migrator/app y corregir contexto por transacción antes de introducir RLS. Mover objetos a storage duradero.
3. **Derechos y trabajos confiables, semanas 3 y 4.** Servicio canónico de suscripción/cuota B2B y B2C, inbox/outbox, reintentos y jobs con idempotencia. Integración Stripe en sandbox con tarjetas fallidas, autenticación pendiente, cancelaciones, duplicados y eventos fuera de orden. Protección distribuida frente a abuso y prueba de carga con cuatro workers.
4. **Producto conectado y arquitectura, semanas 5 a 8.** Modelo gimnasio/membresía/vínculo cliente, onboarding con defaults idempotentes, historial de progreso y adherencia, recuperación de cuenta y MFA owner. Extraer casos de uso gradualmente, compartir DTO/validadores, documentar contratos, migraciones y decisiones de arquitectura. Revisar validez profesional de funciones nutricionales anunciadas.
5. **Operación continua.** SLO y alertas accionables: disponibilidad, latencia p95, fallos de generación, pago sin derecho, retraso webhook, backlog y restauros. Dependencias/imagen escaneadas por cambio; prueba periódica de aislamiento PostgreSQL, restauración y navegación de los dos portales. Retención, consentimiento, exportación y eliminación de datos requieren políticas y flujo de producto definidos.

## Referencias de seguridad vigentes consultadas

[OWASP ASVS 5.0.0](https://owasp.org/projects/asvs) sirve como matriz de verificación; se propone un objetivo L2 adaptado a datos personales y funciones del producto, con evidencia por requisito. Esto es un objetivo de trabajo, no una declaración de cumplimiento.

[NIST SP 800-63B-4](https://pages.nist.gov/800-63-4/sp800-63b.html) aporta criterios de autenticación, recuperación y gestión de sesiones. Usarlo como referencia técnica para un SaaS no convierte automáticamente sus reglas en una obligación legal del producto.

El advisory primario de [Starlette GHSA-86qp-5c8j-p5mr](https://github.com/Kludex/starlette/security/advisories/GHSA-86qp-5c8j-p5mr) confirma un problema de Host/path para versiones hasta 1.0.0, la fijada en el lock, corregido en 1.0.1. El advisory de [python-multipart GHSA-mj87-hwqh-73pj](https://github.com/Kludex/python-multipart/security/advisories/GHSA-mj87-hwqh-73pj) documenta consumo excesivo de CPU antes de 0.0.26; el lock fija 0.0.22. Se verificaron esas fuentes primarias como ejemplos relevantes; el resto del resumen SCA requiere triage por alcanzabilidad y versión instalada.

## Límites materiales

La revisión estática y las reproducciones no cubren cada rama ni sustituyen una prueba de penetración autenticada en staging. La consulta de producción confirma esquema/roles, sin evaluar contenido o accesibilidad cruzada real. No se inspeccionó el inventario de paquetes dentro del contenedor, el panel Stripe, respaldos del proveedor ni una restauración real. Esas comprobaciones quedan como criterios concretos de salida del roadmap, no como controles que se presuman presentes o ausentes.

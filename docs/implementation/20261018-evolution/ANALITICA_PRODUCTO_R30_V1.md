# Analítica de hechos observados R30 v1

Implementación aislada desde `5efd3962ec9529e901273533d17ff1b19f0f1f39`
(runtime503), autorizada técnicamente por ROOT sobre la propuesta
`bc394f7c5ac01c57a669c867e36e4207995ae53991c710bb3e83de625a4220c8`.
El estado original de esa propuesta se conserva: el recibo de autorización no
reescribe sus bytes ni acredita aprobación comercial o un piloto.

## API y autoridad

`GET /api/analytics/producto?context=gym|personal`, también slash exacto.
No hay interfaz nueva, collector, esquema, rol de reporte global ni envío.
`context` es obligatorio. `from` y `through` se aceptan juntos como fechas
civiles ISO; `from` debe ser lunes. Máximo 91 días inclusivos y 13 semanas,
sin fechas futuras respecto de `America/Mexico_City`. Por defecto, desde el
lunes de tres semanas antes hasta hoy. Se rechazan parámetros desconocidos o
repetidos, incluidos selectores de usuario, gimnasio y perfil.

La dependencia de sesión real permanece intacta. El lector vuelve a consultar
los ocho campos de elegibilidad persistidos: id, tipo, rol, pertenencia de equipo,
activo, borrado, invitación y session_version. Compara exactamente el sujeto,
tipo, rol, equipo y SV del principal; admite SV entero 0..2147483647, no bool.
Una invitación no NULL, incluso cadena vacía, deniega. No crea un perfil.

| Contexto | Autoridad |
| --- | --- |
| gym | OWNER canónico de tipo gym sin parent, o ADMIN de equipo con parent canónico activo y permiso existente `read analytics` |
| personal | Espacio propio no OWNER: tipo usuario o miembro profesional válido; sólo su ledger individual |

Nutriólogo y VIEWER nunca obtienen estadísticas del gimnasio por esta ruta.
Su espacio personal no usa el ledger del gym para atribuirles actividad.
OWNER/usuario ambiguo no obtiene adopción de cartera ni reporte personal.

## Hechos y respuesta

El ejemplo completo en `evidence/backend-r30-product-analytics-20261021/example.synthetic.json`
es sintético. Nunca es una medición de clientes reales.

La respuesta contiene `version`, `definition_version`, `definition_hash`,
`scope`, `unit`, `period`, `snapshot`, `preparation_as_of`, `weekly`, `cohort`,
`coverage`, `business_baseline` y `result_hash`. No publica IDs, nombres,
contactos, notas, alimentos, salud, JSON de planes ni claves de petición.

| Hecho | Fuente y significado |
| --- | --- |
| saved_publications gym | Reserva B2B propia con persisted_at y estado reserved/completed; incluye save durable cuyo ACK final falló |
| saved_publications personal | Reserva propia protocolo1, completed y persisted_at; no reconstruye legacy0 |
| preparation_as_of | EXISTS de Cliente activo/no borrado propio y Plan no borrado con ambos dueños coherentes; estado actual, no onboarding primero de toda la vida |
| link_acceptances | Aceptación R12 propia coherente con invitación consumida por el mismo destinatario y su instante, no acceso actual ni lectura |
| plan_assignments_published/withdrawn | Asignación explícita con link/client/Plan exactos; estado observado actual agrupado por published_at, no eventos de lectura o fecha de retiro |

Cuando un marcador perdió Plan por SET NULL, conserva el hecho durable. Si la
referencia aún existe, se exige Plan/Cliente del mismo dueño; no se usa un Plan
manual como publicación del generador. R12 no carga la proyección del menú,
descriptor PDF, etiquetas ni email. No llama `obtener_estadisticas`, diario,
medidas, pagos, auditoría de autenticación ni resumen de métricas R17.
El middleware R17 puede medir la petición normalmente; no es una fuente de
actividad de este reporte.

Cada fuente usa LIMIT10001; superar 10000 rechaza el reporte entero con 413.
No hay truncado silencioso. Máximo de respuesta 65536 bytes UTF8. Las semanas
son lunes civiles de México y sólo completas cuando terminó toda la semana
dentro del límite observado. Los hechos se limitan por as_of y por el inicio
exclusivo del día siguiente a through. El estado de preparación es el del
snapshot de lectura, no una reconstrucción histórica al final de through.

El ancla es el primer timestamp retenido válido hasta ese corte, independiente
de from. `first_observed_publication` no significa first-ever ni registro.
La unidad es un workspace o una cuenta personal propia: población 0/1.
`observed_repeat_publication_d7` observa [ancla+7d, ancla+14d), y d30 observa
[ancla+30d, ancla+37d), con días UTC transcurridos. Antes de madurar toda la
ventana, numerador y ratio son NULL; no se convierte inmadurez en cero.
No se llama retención de personas, ingesta, adherencia o efecto de un email.

Coverage estable declara historia retenida, legacy no reconstruido, demo sin
clasificación persistida, first_open no instrumentado, entrega no medida y
cohortes globales fuera de alcance. No existe un flag que haga datos demo reales.

## Snapshot y fallos

Una nueva Session propia nace en contexto neutral; no se retaguea una Session
ambiental. Tras recargar identidad se vincula únicamente el sujeto verificado.
En PostgreSQL se piden REPEATABLE READ y READ ONLY antes de autobegin y de los
hooks GUC existentes. Se verifica el modo. SQLite usa BEGIN explícito; no se
afirma que equivalga a un control DB de sólo lectura. Se prueba ausencia de DML.
Una única conexión sirve para autoridad y hechos. La autoridad es válida al
snapshot, sin promesa de revocación instantánea posterior a su apertura.

El resultado no sale hasta rollback y close confirmados. Fallos de cleanup
invalidan sólo la Session propia y devuelven 503. Si close e invalidate fallan
juntos puede quedar un checkout: no se oculta el límite ni se dispone el engine
global. El contexto ambiental siempre se restaura. Los logs propios sólo dan
clase técnica; no cuerpos, identificadores, SQL, tokens o contactos.

| Estado | Código |
| --- | --- |
| 401 | analytics_identity_unavailable, o el contrato existente de autenticación |
| 403 | analytics_context_forbidden; un POST SaaS sin bearer puede recibir CSRF403 previo |
| 413 | analytics_volume_limit, rechazo íntegro |
| 422 | analytics_invalid_input |
| 503 | analytics_unavailable, mensaje opaco sin reintento automático |

Las consultas inválidas fallan antes de Session/SQL del lector R30 y sin
estadísticas de producto. TenantMiddleware puede validar la autenticación y
leer antes del router: **no se afirma cero SQL en toda la aplicación**. No se
agregó middleware de admisión ni se cambió autenticación general.

La frontera privada cubre sólo la ruta exacta y slash, todos los estados y
métodos, con no-store/no-referrer y CSP first-party fija. Errores internos del
lector son 503 opacos; una excepción exterior usa el 500 genérico existente de
la factory. Vecinos, GIS y otras familias conservan su contrato.

## Baseline y procedencia

`web/product_analytics_baseline.py` sólo genera bytes puros: no abre archivos,
consulta SQL, obtiene autoridad ni combina reportes. El llamador debe obtener
un resultado autorizado y elegir destino privado con creación exclusiva.
El artefacto incluye el diccionario canónico, hashes, as_of y cobertura fijados,
se declara unreviewed, business_baseline_established=false y targets=NULL.
La validación y los hashes no prueban origen ni convierten datos sintéticos en
baseline de negocio. No se implementó un importador, CLI ni autenticidad firmada.

`snapshot.schema_revision` se lee del esquema real y exige el head vigente.
No existe configuración vigente de build SHA utilizable: source_revision es
NULL con estado unavailable. El dominio permite un build reportado de 40 hex
minúsculas, rotulado reported_by_build; no se ejecuta Git por request ni se
hardcodea d568 o el commit de esta implementación como atestación.

## Alcance de aceptación

Pruebas de autor: dominio y SQLite migrado37, HTTP real de ambas factories,
password/MFA reales en setup, fixtures aisladas y proveedores cerrados. El
recibo final enumera los IDs efectivos, fallos de canarios propios y correcciones.
No se ejecutó PostgreSQL, Chrome, Redis, VM, n2, datos reales ni envíos.
La revisión independiente SEC y la composición por ROOT son posteriores.

El sello público final es `manifest-v2.json`; incluye el manifiesto inicial
inmutable y ambos drivers de sellado. El primer intento del sellador falló en
su inversa (contaba `if` dentro de `elif`), sin cambio de producto ni repetición
de tests. La proyección parcial quedó privada. `diff --check` de producto,
tests y documento es limpio; el diff completo también informa whitespace de
preimágenes/launchers RAW preservados. El `diff_check: PASS` del recibo de
publicación se refiere al código previo a incorporar esas preimágenes, no
declara limpieza del whitespace histórico RAW.

Este incremento no cierra R30 completo: faltan medición real autorizada,
cohortes poblacionales cuando se acuerde autoridad, entrevistas externas,
baseline real antes de objetivos y decisiones humanas de cada experimento.

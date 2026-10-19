# Operación y seguridad de MetodoBase

Fecha de revisión: 18 de octubre de 2026, zona America/Mexico_City. Este informe describe el servicio `MetodoBaseWeb` de `joyful-quietude`, su PostgreSQL y los archivos de despliegue del repositorio. La aplicación estaba disponible durante la revisión; su disponibilidad no demuestra aislamiento entre gimnasios, restaurabilidad ni corrección de cobros.

## Evidencia de producción

Se utilizó Railway CLI 5.59.0 autenticada, con selección explícita de proyecto, entorno y servicio. Se consultaron estado, metadatos de despliegues, presencia de configuración, métricas y una muestra de logs. Las variables secretas se procesaron en memoria y sólo se guardaron indicadores de presencia. La consulta SQL de catálogo se hizo en transacción de sólo lectura, con tiempo límite y cierre mediante rollback; no se consultaron registros de negocio.

| Componente | Resultado observado |
|---|---|
| Proyecto y entorno | `joyful-quietude`, únicamente `production` en el listado consultado |
| URL | https://metodobase.up.railway.app |
| Fuente | `user221000/MetodoBaseWeb`, rama `main` |
| Commit del servicio | `daa25efbf51d154710bad625025b345fa9ec9252` |
| Despliegue web | `28cc3eab-e9bd-4742-ab4d-c75ff954db6f`, estado `SUCCESS`, creado el 13 de agosto de 2026 |
| Topología | Una réplica web en `us-west2`; PostgreSQL con volumen |
| Archivos web | Ningún volumen montado; cero buckets en el proyecto consultado |
| PostgreSQL | 18.6; 20 tablas en `public`; `max_connections=500` |
| Privilegios | El usuario configurado por la aplicación es `postgres`, con superusuario y `BYPASSRLS` |
| RLS | Todas las 20 tablas sin RLS habilitado ni forzado; catálogo `pg_policies` vacío |
| Migraciones | No existe `public.alembic_version`; `preDeployCommand=null` en el despliegue efectivo |
| Salud HTTP | `/health` y `/health/ready` respondieron 200; readiness indicó `ready=true` |
| Páginas públicas | `/`, `/login-gym`, `/login-usuario` y `/registro` respondieron 200 |
| Cabeceras públicas | HSTS, protección de frames y CSP con nonce presentes en `/` |
| Correo | `RESEND_API_KEY` ausente en variables del servicio; el código omite el envío sin esa clave |
| Pagos | Stripe con clave de modo live y secretos/precios presentes; no se procesaron cargos |
| Observabilidad y Redis | DSN y URL presentes; su presencia no valida entrega ni disponibilidad |

Evidencias: [estado saneado](evidence/railway-summary.json), [presencia y flags](evidence/railway-config-presence.json), [HTTP público](evidence/public-http.json) y el informe de backend para la consulta del catálogo PostgreSQL.

## Riesgos de operación

### OPS01 Migraciones ausentes del despliegue efectivo

**Prioridad P0. Confirmado en configuración, despliegue y catálogo.** `railway.toml:10` declara `releaseCommand`. La documentación y el esquema actuales de Railway utilizan `preDeployCommand`. El manifiesto efectivo no contiene un comando previo al despliegue. Además, `entrypoint.sh:13` omite Alembic cuando existe `RAILWAY_ENVIRONMENT`.

El catálogo de producción sin `alembic_version` demuestra que no se está gestionando allí el esquema mediante el seguimiento esperado de Alembic. No se debe deducir que toda migración del repositorio puede ejecutarse sobre esa base sin preparación: parte del esquema ya existe.

**Acción:** inventariar tablas, columnas, índices y restricciones; reconciliar el esquema existente en una copia de staging; establecer una revisión inicial verificada; corregir el hook y ejecutar futuras migraciones antes del arranque. Ante fallo, detener el despliegue. No usar `stamp head` para ocultar diferencias. El bootstrap de base nueva también necesita revisión: `create_all` seguido de `stamp` puede omitir políticas y otras operaciones que sólo viven en migraciones.

**Aceptación:** base vacía y copia del esquema actual alcanzan la misma revisión y restricciones mediante un procedimiento reproducible; Alembic reporta un único head; el despliegue fallido por migración no recibe tráfico. Fuente: [configuración de Railway](https://docs.railway.com/config-as-code/reference) y [comando previo al despliegue](https://docs.railway.com/deployments/pre-deploy-command).

### OPS02 Aislamiento de datos sin defensa en PostgreSQL

**Prioridad P0. Configuración real confirmada.** No hay políticas RLS y la aplicación usa un rol con privilegios que las eludiría. Esto no prueba una filtración existente: implica que cualquier filtro de tenant omitido en la aplicación puede alcanzar otros gimnasios sin una segunda barrera en la base.

**Acción:** separar rol migrador y rol de aplicación `NOSUPERUSER NOBYPASSRLS`; definir el alcance de usuario individual y miembro de equipo; hacer que todas las sesiones establezcan contexto de tenant por transacción, incluidos trabajos y generación en segundo plano. Corregir primero las sesiones que no reciben contexto; luego activar y probar RLS gradualmente. Encender RLS directamente puede romper rutas legítimas.

**Aceptación:** pruebas reales de PostgreSQL con dos gimnasios y un rol restringido verifican lectura, alta, actualización, borrado, exportación, tareas y reutilización de conexiones; un contexto ausente o incorrecto falla cerrado. Deben cubrirse tablas de clientes, planes, suscripciones, pagos y las nuevas tablas que contengan pertenencia a un gimnasio.

### OPS03 Archivos de clientes y branding en almacenamiento efímero

**Prioridad P1. Ruta y topología confirmadas.** `web/routes/gym_profile.py:30` guarda logos bajo `/app/web/static/uploads/logos`; `web/routes/planes.py:149` y siguientes escriben planes en directorios locales. El contenedor define `/data`, pero el servicio web no tiene volumen montado. Crear ese directorio en Docker no lo vuelve persistente.

**Acción:** mover logos y documentos a un puerto de almacenamiento con un adaptador de object storage, metadatos en PostgreSQL y descargas autorizadas o URLs de duración limitada. Un volumen puede servir como transición para una sola réplica, con inventario y respaldo explícitos; no resuelve por sí solo despliegues distribuidos.

**Aceptación:** un logo y un plan de prueba sobreviven a reemplazar el contenedor; usuario y gimnasio ajenos no pueden descargarlos; existe política de retención y borrado. El alcance exacto de los PDFs recuperables desde datos JSON debe verificarse antes de migrar archivos históricos.

### OPS04 El script de backup no protege PostgreSQL

**Prioridad P1. Confirmado en código; política nativa del proveedor pendiente de inspección específica.** `scripts/backup_daily.py:46` enumera archivos SQLite, y su salida puede ser exitosa si todos se omiten. No implementa dump de PostgreSQL ni respaldo de objetos. No se encontró un servicio o cron de backup en la topología consultada. Esto no demuestra que Railway no tenga snapshots configurados por otros mecanismos.

**Acción:** verificar backups nativos, documentar retención y restauración; añadir respaldo independiente cifrado según riesgo, monitorizar edad y resultado y ensayar la restauración en un entorno aislado. El script debe fallar si no respaldó ninguna fuente esperada.

**Aceptación propuesta:** RPO de 24 horas y RTO de 4 horas como objetivos iniciales a validar con el negocio; ensayo fechado que restaure esquema, usuarios, relaciones y referencias a objetos. Estos tiempos son metas propuestas, no capacidades actuales.

### OPS05 Protección Redis degrada permitiendo solicitudes

**Prioridad P1. Comportamiento de código e incidente histórico observados.** `web/rate_limiter_redis.py:74` deja pasar solicitudes cuando Redis falla. Una consulta de hasta 80 líneas filtradas devolvió 39 registros, de los cuales 30 contenían `Redis rate limiter unavailable, allowing request`; el último de esos registros era del 15 de octubre. Una muestra posterior de la última hora devolvió 17 líneas, sin ese mensaje. No se afirma una caída permanente de Redis ni se intentó provocar un ataque de fuerza bruta.

**Acción:** alarma y métrica de degradación; política distinta para login, refresh y generación costosa; fallback limitado o rechazo temporal en rutas sensibles. La expiración Redis se reinicia en cada petición (`:42`), por lo que también debe definirse y probarse la semántica de la ventana.

**Aceptación:** pérdida de Redis simulada en staging no deja autenticación o generación sin límites; recuperación comprobada; alerta verificable y sin secretos.

### OPS06 Correo transaccional deshabilitado

**Prioridad P1 para activación y recuperación.** Sin `RESEND_API_KEY`, `web/services/email_service.py:43` omite envíos. Las rutas de bienvenida e invitación pueden existir sin que el usuario reciba un correo. Tampoco se encontró un recorrido completo de recuperación de contraseña en las rutas revisadas.

**Acción:** configurar remitente y dominio verificado en el proveedor seleccionado, observar entregas/rebotes y añadir recuperación segura con token de un uso y caducidad. Ocultar o corregir promesas que todavía no tengan recorrido funcional.

**Aceptación:** usuario de prueba recibe y completa invitación y recuperación; los tokens expiran y no se reutilizan; respuestas no facilitan enumeración; correos no se envían desde pruebas automatizadas ordinarias.

### OPS07 Despliegues difíciles de reproducir y sin staging

**Prioridad P1.** Docker instala `requirements_web.txt` con rangos abiertos; el lock histórico no es su fuente de instalación y tiene diferencias. Sólo se observó el entorno `production`. No se construyó ni desplegó una imagen durante esta auditoría.

**Acción:** resolver y fijar dependencias para Linux/Python de producción, ejecutar SCA sobre esa resolución y sobre la imagen, generar SBOM, publicar la imagen por digest y promover el mismo artefacto de staging a producción. Separar dependencias desktop, web, pruebas y herramientas de agentes.

**Aceptación:** un commit produce un artefacto identificable; pruebas y escaneo bloquean vulnerabilidades aplicables por encima del umbral acordado; rollback ensayado sin modificar destructivamente el esquema.

## Capacidad y observabilidad

Una muestra de una hora mostró aproximadamente 594 MB de memoria media, 599 MB máximos y 0.008 vCPU medios para el servicio web. No es un benchmark ni una prueba de carga; no permite inferir cuántos clientes simultáneos soportará. La consulta de siete días falló por el límite de puntos de la CLI y no se usa como evidencia.

Con `WEB_WORKERS=4`, `DB_POOL_SIZE=20` y overflow por defecto de 10, el techo teórico del pool web es 120 conexiones; PostgreSQL informó 500 máximas. No hay evidencia aquí de saturación. La decisión sobre tamaño de pools debe considerar memoria PostgreSQL, trabajos, migraciones y pruebas de carga antes de subir workers.

Añadir medición por flujo: errores de login, acceso denegado por tenant, latencia p50/p95/p99, cola y tiempo de generación/PDF, pool, degradación Redis, demora y reintentos de webhooks, desajustes de suscripción, edad del último backup y entrega de correo. Las métricas deben incluir identificadores internos adecuados sin nombres, correos, condiciones médicas ni tokens.

## Base de verificación de seguridad para 2026

Se propone verificar controles y guardar evidencia con versiones explícitas. No se emite una certificación ni se presenta un único supuesto estándar llamado «seguridad 2026».

| Referencia | Uso propuesto en MetodoBase |
|---|---|
| [OWASP ASVS 5.0.0](https://owasp.org/projects/asvs) | Matriz de requisitos seleccionados con objetivo L2: autenticación, sesiones, autorización, datos y configuración |
| [OWASP API Security Top 10 2023](https://api-security.owasp.org/editions/2023/en/0x11-t10/) | Casos de abuso de objetos, propiedades, funciones, cuotas y flujos comerciales |
| [NIST SSDF 1.1](https://csrc.nist.gov/pubs/sp/800/218/final) | Responsables, desarrollo seguro, artefactos, dependencias y respuesta a vulnerabilidades |
| [NIST SP 800-63B revisión 4](https://pages.nist.gov/800-63-4/sp800-63b.html) | Referencia para ciclo de vida de autenticadores, recuperación y sesiones; MFA/passkeys para roles privilegiados según riesgo |
| [WCAG 2.2](https://www.w3.org/TR/WCAG22/) | Objetivo AA de accesibilidad para recorridos completos; auditoría automática más teclado y tecnologías de asistencia |
| [Stripe webhooks](https://docs.stripe.com/webhooks) | Firma sobre cuerpo original, idempotencia y tratamiento seguro de entregas repetidas y asíncronas |

Para cada control registrar requisito y versión, amenaza, implementación, prueba, evidencia, responsable y próxima revisión. La evaluación de privacidad debe inventariar peso, medidas, notas de salud y contactos, sus finalidades y conservación; el alcance legal concreto de México requiere validación especializada. Incorporar consentimiento cuando corresponda, exportación/borrado, minimización y permisos de soporte. Evitar etiquetar planes como aptos para una condición médica a partir de notas que el generador no interpreta.

## Criterio de salida de la fase de estabilización

Los bypass de cobro y permisos del informe backend tienen regresiones; staging usa migraciones verificadas y rol restringido; dos gimnasios no comparten registros ni archivos; un restore se completa; CI web y PostgreSQL pasa y bloquea fallos materiales; el mismo artefacto se promueve con rollback probado. Después puede ampliarse captación de pago con un nivel de riesgo conocido y revisado.

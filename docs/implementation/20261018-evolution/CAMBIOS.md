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

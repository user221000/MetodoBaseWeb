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

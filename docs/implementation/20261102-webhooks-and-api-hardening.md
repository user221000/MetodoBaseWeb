# Webhooks, historial y transporte web — 2 de noviembre de 2026

## Continuidad y alcance

El hotfix `6cdbc58c329db960db9aea5d34a0913a98a876e0` está publicado en el despliegue `8e419abd-b127-4274-9cb1-1e8f849d458e`. El usuario confirmó «Sí, ya pude ingresar» después de recargar e iniciar un nuevo intento Google. La incidencia de acceso por código queda resuelta y confirmada por el afectado; no se conservan códigos o credenciales. Los recibos anteriores que aún indicaban aceptación humana pendiente conservan su momento histórico.

Este segundo corte corrige los defectos de pagos y transporte encontrados al ampliar la auditoría. No cambia precios, cuotas, tablas, esquema, permisos, reglas de MFA o dependencias instaladas. Producción continúa en esquema 40. La configuración remota Stripe se verifica por separado, después de publicar el código aceptado.

## Stripe: eventos actuales y autoridad financiera

La lectura autorizada de Stripe encontró un endpoint activo, versión `2026-03-25.dahlia`, con seis tipos de evento. Incluía `invoice.paid`, que el código no procesaba, y no incluía los callbacks esperados de éxito/fallo de factura, actualización/baja de suscripción y reembolso. Los cuatro precios de pago sí coincidían con el catálogo: Standard159, Gym479, Clínica979 y Pro79 MXN mensuales. La consulta de eventos `invoice.paid` no devolvió muestras; eso no demuestra ausencia histórica fuera de la consulta o retención.

Se admite `invoice.paid` junto a los eventos de factura existentes. El evento sólo identifica el recurso: se consulta la factura actual y se valida su cuenta, suscripción, modo, moneda, importe, pago y cargo capturado. La reconciliación usa la versión SDK existente `2024-06-20`; no se migra el SDK o Elements a Dahlia. El helper existente ya aceptaba referencias de suscripción antiguas y la estructura `parent.subscription_details.subscription`.

Un snapshot antiguo no registra por sí solo un pago exitoso ni concede acceso. Las lecturas fallidas o identidades incompatibles mantienen rollback y respuesta reintentable, sin dejar el inbox marcado como completado. La reentrega válida conserva idempotencia. Las entradas API y Web de Stripe comparten ahora el handler canónico y los mismos estados de error. `invoice_payment.paid` y `payment_intent.*` conservados en la configuración no se convierten en pruebas alternativas de financiación.

El historial también tenía un defecto observado: tras un reembolso completo, el acceso bajaba pero el pago seguía indicando éxito. Ahora se registra `refunded` sólo con cargo/factura actuales y un pago propio que coincida en identidad, importe y moneda. El reembolso de una factura anterior no cancela una renovación posterior válida; un evento de factura posterior no sobreescribe un reembolso terminal. No se inventan pagos históricos si no existe un registro propio. Los parciales conservan el importe bruto y la política de acceso existente; falta modelar contraasientos/importes netos y su presentación específica.

## Cuerpos de webhook y caché

Las seis superficies de webhook —cuatro de API y dos de Web, con aliases incluidos— usan un lector compartido que cuenta los bytes del stream. Conserva exactamente los bytes firmados. Un cuerpo excesivo produce 413; cabeceras de longitud ambiguas, incompatibles o recepción incompleta producen 400. `Content-Length` es sólo un dato de admisión, no sustituye el contador real. Los rechazos ocurren antes de proveedor o persistencia de negocio.

`WEBHOOK_MAX_BODY_BYTES` es opcional: predeterminado 2 MiB (2097152), mínimo 64 KiB y máximo 8 MiB. La aplicación rechaza una configuración fuera de esos límites. El límite no demuestra un máximo universal del proveedor: cualquier ajuste debe basarse en recibos de tamaño legítimo y revisión operativa. No se registran payloads o firmas en la telemetría.

Las factories comparten el algoritmo de versión de recursos ya usado por Web: bytes JS/CSS en el mismo orden y MD5 como clave de caché, sin uso criptográfico. API dejaba esa versión vacía cuando arrancaba sola. Los procesos aislados prueban ahora la misma versión y parejas SDK/controlador coherentes. Sólo las tres entradas de acceso y registro añaden `Cache-Control: no-store`; se mantienen contexto y nonce CSP.

## Verificación independiente

Las reproducciones rojas quedan conservadas: evento ignorado, ledger basado en snapshot, ausencia de límites y refund mostrado como éxito. El cierre financiero independiente ejecuta 103 casos HTTP/ASGI con SQLAlchemy y firmas de SDK/HMAC; incluye cuerpos por chunks, límite exacto y exceso, seis superficies, tres entradas Stripe, identidad, modo, importes, reintento, duplicación, refund completo/parcial y objetos nativos del SDK. Son proveedores controlados, no pagos externos.

La campaña PostgreSQL usa clusters propios, migraciones reales al head actual y rol restringido con FORCE RLS. Los recibos finales identifican sus casos, conexiones físicas y cierre de procesos. Las pruebas de esquema 39 históricas se conservan: un companion de privacidad en esquema 40 ejecuta las mismas assertions sin relajar la admisión del servicio. No se transforma un error de preparación histórico en un PASS de aquella ejecución.

La matriz cubre 184 operaciones API y 203 Web: 387 filas por factory, 209 pares método/ruta distintos. Las 638 solicitudes de admisión prueban rechazo o lectura pública, sin mutaciones en la base; no certifican por sí solas todos los casos de negocio o IDOR con actor válido. El documento final de auditoría separa esos límites, las regresiones de dominio y los pendientes comerciales.

## Operación, publicación y recuperación

Operación preparó un cambio aditivo revisado de 6 a 11 eventos en el endpoint Stripe existente: añade `invoice.payment_succeeded`, `invoice.payment_failed`, `customer.subscription.updated`, `customer.subscription.deleted` y `charge.refunded`, conservando los seis actuales, URL, estado, versión API, metadata y secreto. El aplicador exige fuente publicada, deployment SUCCESS y comprobación runtime reciente. Hace una sola escritura de `enabled_events` y lectura posterior incluso ante timeout, sin repetir a ciegas o revertir automáticamente.

El código se publica antes de ampliar los eventos remotos. Los recibos posteriores registran commit/imagen, `/health/ready`, fuentes exactas y readback Stripe. No se hacen cobros, reenvíos de eventos live, borrados de inbox o backfills automáticos para probar. Los eventos antiguos ignorados siguen deduplicados: B13 puede conciliar derechos actuales con manifiesto privado y proveedor autoritativo, pero no reconstruye por sí solo el ledger perdido. Los afectados, si existen, requieren diagnóstico y reparación acotada separados.

Recuperación: volver expresamente al commit/imagen del hotfix de acceso si falla esta publicación, conservando las fuentes locales y evidencias. La lista previa de eventos se conserva en el preflight para una decisión operativa explícita; no se borra historial financiero ni se restablecen cuentas al cambiar una versión.

## Evidencias y pendientes

Root coordina en `E:/MetodoBaseWorkspace/evidence/production-auth-audit-20261101-20261102T0500-root/`. Backend: `stripe-contract-20261102-5bde1475b02147baac1f18829d5f5236/` y `stripe-refund-ledger-20261102-5919da043796498084f2babf3d8b8ac6/`. QA: `incident-qa-20261101-c0fcf18a/phase2-20261102-05e57f94/`. Seguridad: `phase2-security-20261102-bfd6538c/`. Caché: `static-factory-parity-20261102-6c347564de3f4a8197b3a7cb81e74fcc/`. Operación: `incident-operations-20261102-666087a6da2c40be932abfa1092f9a38/`.

El CI del contrato de acceso ya pasó en GitHub con Node24. Los controles generales siguen pendientes: identidad Dockerfile, selectores PostgreSQL de esquema 39 y cuatro ubicaciones Gitleaks sin clasificación finita vigente. Seguridad verificó que esas cuatro ubicaciones anteriores al hotfix son una huella GPG pública y fixtures sintéticos; no son credenciales reales, y no se modifican allowlists o controles para fingir CI verde. Queda el ciclo real sandbox de proveedor, Mercado Pago está sin configurar, y recuperación/observabilidad/cobertura funcional completa conservan tareas con criterios propios. El informe de auditoría final detalla responsables y evidencias.

Referencias oficiales consultadas en esta ejecución: [Stripe Webhooks](https://docs.stripe.com/webhooks), [eventos Stripe](https://docs.stripe.com/api/events/types), [actualizar un endpoint](https://docs.stripe.com/api/webhook_endpoints/update), [Mercado Pago Webhooks](https://www.mercadopago.com.mx/developers/es/docs/your-integrations/notifications/webhooks). Se preservan autenticidad, cuerpo original, reintentos y conciliación por estado actual; no se equiparan fixtures con un ciclo externo aceptado.

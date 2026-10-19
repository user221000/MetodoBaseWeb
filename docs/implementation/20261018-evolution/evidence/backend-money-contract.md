# Contrato local de cobros y cuota: lote de contención

Estado: código local revisado, sin despliegue ni operaciones sobre proveedores. Regresiones iniciales: ocho casos fallaron antes de la corrección (`backend-before.log`). Gate del autor: **96 passed** en `backend-final-money.log`. Seguridad ejecutó su gate independiente de 97 casos y registró los archivos revisados en `security-money-source.json`; QA conserva su propio resultado. Las huellas del conjunto de backend están en `backend-money-hashes.json`.

## Comportamiento implementado

`POST /api/usuario/suscripcion` conserva compatibilidad de ruta, pero devuelve 409 al intentar conceder Pro o cancelar un cargo mediante preferencias. Los redirects sólo llevan al usuario a consultar su estado. `stripe-subscribe` crea el pago pendiente y `confirm-subscription` consulta evidencia del proveedor; esas rutas no escriben derechos por su cuenta.

`POST /api/usuario/checkout` acepta `success_url`/`cancel_url` relativos de `/mi-suscripcion` y devuelve `session_id`, `url`, `purchase_intent_id`. `POST /api/usuario/billing-portal` acepta `return_url` relativo y devuelve `url` del portal de la suscripción propia. B2B conserva `/api/billing/checkout` y `/api/billing/portal`. Las claves antiguas `payment_link_pro`/`payment_links` se devuelven vacías: un Payment Link estático no crea una intención asociada a la cuenta. Frontend debe iniciar checkout o Elements con el backend. Las compras históricas sin correspondencia permanecen pendientes de conciliación explícita, sin modificar derechos reales por este trabajo local.

Las creaciones de compra y generación admiten `Idempotency-Key`, máximo 128 caracteres, acotada a la cuenta autenticada. `PurchaseIntent` se confirma en la base antes de Customer/Subscription/Checkout/Preference. Stripe recibe claves distintas por operación de esa intención; la referencia del proveedor se persiste después. No se guardan secretos de tarjeta ni `client_secret` en la intención. Un cambio de plan reutilizando la misma clave se rechaza.

Stripe verifica identidad, producto/precio, importe MXN mensual, estado activo, factura pagada y cargo capturado, del cliente esperado y sin reembolso. Evidencia incompleta no concede acceso. Cada evento obtiene el estado actual del proveedor bajo lock del sujeto y vuelve a leer la correspondencia persistida: eventos antiguos, repetidos o de una suscripción reemplazada no cancelan la compra nueva. Una suscripción financiada por MP no es modificada por eventos Stripe anteriores. La proyección individual usa cinco planes para Pro pagado y Starter cuando el estado deja de otorgar Pro; no se inventó un periodo de gracia.

MercadoPago usa un adaptador compartido por SaaS, individuo y API legacy. Verifica HMAC de `data.id` de query, `x-request-id` y `ts`; exige igualdad con el ID del body y una ventana local de cinco minutos. Un inbox persistido rechaza efectos repetidos. El estado se consulta de nuevo bajo lock y se valida intención, recurso, importe y moneda. Las aprobaciones antiguas se registran para conciliación sin desplazar el periodo más nuevo. Reembolsos/contracargos sólo afectan el pago que financia la suscripción vigente. Fallos temporales devuelven 503 para conservar reintentos.

La cuota individual se reserva en una transacción corta con lock de la fila de cuenta, incremento condicional y clave única. Un crédito acepta como máximo una solicitud; el fallo CPU/PDF/storage devuelve ese mismo crédito una vez. Los reintentos terminados devuelven el `plan_id` exacto y no llaman al generador. La cuota mensual usa `America/Mexico_City`. Un proceso interrumpido conserva su reserva para reconciliación; no inicia silenciosamente otro trabajo.

La presencia/ausencia de claves Stripe o MP nunca concede Clínica. B2B obtiene derechos de suscripciones persistidas con periodo válido o Free. Las exclusiones alimentarias se aplican independientemente del plan comercial. Los errores de proveedor se traducen a mensajes estables y referencias; los logs contienen clase y referencia, sin texto de excepción/SQL ni traceback de parámetros.

## Versión del proveedor adoptada

El adaptador conserva explícitamente **Stripe API 2024-06-20** para el contrato Elements existente. El [cambio Basil de 2025-03-31](https://docs.stripe.com/changelog/basil/2025-03-31/add-support-for-multiple-partial-payments-on-invoices) retiró `Invoice.payment_intent`, `charge` y `paid`; actualizar SDK sin adaptar el contrato no demuestra compatibilidad. La migración a Invoice Payments requiere su prueba sandbox. No se cambió la versión de ningún webhook configurado en una cuenta externa.

Fuentes consultadas: [versionado Stripe](https://docs.stripe.com/api/versioning), [webhooks de suscripciones](https://docs.stripe.com/billing/subscriptions/webhooks), [objeto Charge en la versión adoptada](https://docs.stripe.com/api/charges/object?api-version=2024-06-20), [firma y recepción de MercadoPago](https://www.mercadopago.com.mx/developers/en/docs/your-integrations/notifications/webhooks).

## Límites que conservan estado abierto

- Compra/renovación/cancelación real en sandbox, recepción de firmas reales y SDK contra la versión adoptada: requiere credenciales de prueba configuradas. Las pruebas actuales usan dobles en la frontera del proveedor y persistencia real local.
- Migración PostgreSQL y concurrencia de múltiples procesos: QA prepara cluster sintético; R03/R04 deben cerrar su evidencia antes de release.
- Cuota/reserva atómica B2B de generación y altas: la contención individual no cierra B17 ni todo R01.
- Interrupción durable de worker, reserva con resultado todavía no enlazado, reconciliación periódica y retención de idempotencia del proveedor: R28 permanece abierto. No se afirma que un mock resuelva pérdida de procesos.
- Actualización de precios/cupones/periodos por portal, gracia, impuestos y reembolsos parciales necesitan el contrato comercial aplicable y pruebas; no se deducen de tests.
- Reconciliación de compras históricas, derechos previos sin proveedor, políticas de privacidad/retención y activación en producción siguen abiertas. No se ejecutaron cargos, correo, cambios de clientes ni migraciones live.

La migración `20261018_billing_integrity` añade campos/tablas, amplía el plan B2C y normaliza IDs vacíos y enums. El rollback se niega a borrar registros financieros/durables; después de uso requiere restauración verificada. Debe aplicarse después de reconciliar la historia Alembic en R03, sin `create_all`/`stamp head` como sustituto de esa reconciliación.

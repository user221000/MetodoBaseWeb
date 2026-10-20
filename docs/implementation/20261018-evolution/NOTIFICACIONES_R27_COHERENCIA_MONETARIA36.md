# Coherencia monetaria de observaciones R27 (SEC25)

Este cambio pertenece al candidato web36, pendiente de revisión independiente
e integración en MAIN. No modifica cobros, derechos ni el esquema de datos.

Una factura Stripe sólo aporta autoridad de recordatorio cuando sus cantidades
son enteros acotados en unidades menores y `amount_due = amount_paid +
amount_remaining`. El estado `paid` y el booleano original `paid` deben coincidir.
La lectura conserva el booleano del proveedor antes de combinarlo con el estado:
un `paid=true/status=open` no se convierte en un hecho de impago.

La [referencia oficial de Invoice](https://docs.stripe.com/api/invoices/object),
consultada el20 de octubre de2026, describe `amount_remaining` como la diferencia
entre importe debido y pagado, y separa `amount_overpaid`. Los casos no modelados,
incluido un sobrepago, permanecen sin confirmar. No se infieren importes, no se
normaliza un booleano ambiguo y no se inventan hechos financieros. MercadoPago
conserva su contrato de pago único y no adquiere semántica de factura vencida.

El dominio aplica la misma comprobación a los hechos persistidos antes de
declarar elegibilidad. La observación inválida inicial no crea un hecho;
si existía un hecho válido previo, el mecanismo vigente lo sustituye por un
marcador duradero `unknown` y devuelve503 después de confirmar ese commit.
El marcador conserva las cantidades previamente verificadas y retira autoridad
de cola/envío; nunca sustituye la conciliación de suscripciones.

La regresión pura nueva reproduce14 fallos y2 controles antes del cambio.
Tras la corrección pasan44 casos de dominio/transporte, incluidos los16 nuevos.
El test previo de fingerprint conserva su aserción: su fixture ahora representa
un pago parcial coherente (`paid=5000, remaining=5000`), en lugar de un saldo
matemáticamente contradictorio. Su preimagen RAW se conserva. El canario HTTP
independiente original permanece intacto; su repetición y los controles de
supersesión duradera corresponden al peer de seguridad.

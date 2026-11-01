# Confirmación por correo antes de contratar un plan

Al elegir un plan de pago, la web pide un código de seis cifras enviado al correo registrado en la cuenta. Se aplica a Standard, Gym Comercial, Clínica y Pro personal, mediante Stripe o Mercado Pago, y al acceso a los portales de Stripe donde se puede cambiar de plan. No se toma el destinatario de un campo enviado por el navegador. Las renovaciones que ya gestiona el proveedor conservan su funcionamiento.

El diálogo compartido muestra el correo parcialmente oculto, permite pegar el código, reenviarlo después de 60 segundos o cancelar. Conserva el foco y funciona en móvil. Cancelar, cambiar de cuenta, cerrar la página o perder la sesión descarta la autorización local y evita redirecciones tardías. El proveedor se abre únicamente después de confirmar el código; la activación del plan sigue dependiendo de la evidencia de pago del proveedor.

## Autoridad y límites

El código vence a los diez minutos y admite cinco intentos. Las solicitudes y verificaciones tienen además presupuestos por cuenta e IP. Redis guarda estados firmados y digests HMAC, sin almacenar el código o el correo en texto. Un envío sólo queda utilizable tras la aceptación identificada del proveedor de correo. No hay autorización alternativa en memoria si Redis o el correo fallan.

La confirmación produce una autorización opaca de cinco minutos, ligada a la cuenta, versión de sesión, contacto, correo, access token exacto, rol, pertenencia, plan, acción y catálogo de precios. Se vuelven a leer los datos persistidos al solicitar, verificar e iniciar la compra. El cambio de correo, cierre de cuenta, revocación, cambio de precio o cambio de acceso invalida el intento anterior. El código de una compra no confirma otra cuenta, plan o proveedor.

Los diez puntos de entrada manuales —ocho compras y dos portales— comprueban la autorización en el servidor antes de llamar al proveedor. La cabecera `X-Billing-Email-Grant` queda fuera del DTO de compra para conservar el vínculo exacto de MFA existente. El segundo factor del negocio sigue vigente. Los miembros del equipo conservan su plan personal propio; no usan los datos o correo del dueño.

La autorización se consume atómicamente. Sólo se admite repetir una compra con la misma clave de idempotencia y el mismo método, ruta, cuerpo y cuenta; no habilita una intención nueva. Los portales se consumen una sola vez. El navegador no repite automáticamente una compra ante una respuesta de pago incierta. Los webhooks, la conciliación y la confirmación de pagos conservan su autoridad propia y no aceptan el código como evidencia de pago.

## API y persistencia

- `POST /api/billing/email-verification/request`: acción y plan permitidos, sin destinatario editable.
- `POST /api/billing/email-verification/verify`: misma acción y plan, challenge opaco y código ASCII de seis cifras.
- Ambas entradas usan JSON estricto de hasta 4 KiB, rechazan campos extra, claves duplicadas y valores no finitos, y publican respuestas privadas sin caché. No devuelven el código.

No se añaden tablas, columnas, roles o políticas RLS para esta función. La publicación se coordina con el inventario de máquinas, cuya migración aditiva 39→40 tiene su respaldo y ventana propios. El usuario autorizó ejecutar esa ventana ahora; los archivos históricos ausentes se documentan sin borrar sus referencias.

## Verificación y evidencia

Evidencia: `E:/MetodoBaseWorkspace/evidence/billing-email-verification-20261101-0bd1189954fb4540b80d9f1b0363b137/`. Los recibos identifican la fuente y fase exactas; no se suman pruebas repetidas como criterios nuevos ni se atribuye una aceptación de esquema 39 al esquema 40.

El autor verificó 39 casos del servicio y 40 de identidad/entrada con JWT reales y SQLite propia. El transporte del navegador conserva 25 controles nuevos y 74 regresiones de sesión y seguridad de cuenta; la revisión visual comprende las dos vistas a 320, 390 y 1365 px. La revisión independiente ejecuta las operaciones Lua en Redis propio con autenticación y ambas factories HTTP con cuentas sintéticas. Se conservan los intentos rechazados y las correcciones de harness junto a sus sucesores.

Las regresiones de cobro conservan la comprobación de que pagos incompletos no conceden Pro, los reembolsos y cancelaciones no revocan compras nuevas, la cuota no se duplica y los fallos del proveedor no se filtran. Dos fixtures históricas que iniciaban una suscripción sin verificación se cubren por los escenarios nuevos de admisión y la regresión aislada de traducción de fallos; no se presentan como un flujo autenticado completo. Se corrigió la fecha de una fixture de cuota: usaba mes UTC en la madrugada del primer día, aunque el producto opera con el mes de Ciudad de México. Las aserciones de rechazo y ausencia de generación se mantienen.

No se enviaron códigos a clientes ni se realizaron cargos para probar la función. Las respuestas de correo y pago se interceptan en pruebas. La aceptación del correo no garantiza su llegada a la bandeja. Los recibos finales de migración, publicación y smoke del dominio se añaden a la evidencia al cerrar el despliegue.

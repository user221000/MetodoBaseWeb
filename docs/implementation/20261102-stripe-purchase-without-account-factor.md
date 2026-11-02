# Contratación Stripe sin activar un factor de cuenta

El usuario solicita que contratar desde el panel de un gimnasio o clínica tenga el mismo requisito de seguridad de cuenta que el espacio individual: la operación no debe bloquearse con «Activa un factor en la seguridad de tu cuenta antes de continuar».

## Recorridos afectados

Las entradas de Stripe de negocio dejan de exigir alta de autenticador o un grant MFA adicional: Checkout, suscripción con Elements, confirmación posterior al pago, portal y el alias de Checkout de la factory API. El portal está incluido porque elegir otro plan cuando ya existe una suscripción Stripe abre ese portal; conservar allí el requisito repetiría el bloqueo observado. Las rutas y DTO se conservan.

El navegador mantiene la verificación del correo de contacto que ya utiliza el espacio individual. Si el contacto vigente está confirmado, no pide otro código. Conserva el contexto de cuenta y acceso durante la solicitud, la clave de idempotencia y el bloqueo de reintentos ante resultados inciertos. Confirmar una suscripción conserva un único acceso durante la petición, sin refrescar y reenviar automáticamente una operación financiera.

## Autoridad que se conserva

Cada entrada Stripe vuelve a leer y bloquear al actor actual, comprueba el Bearer firmado y su versión, emisor, audiencia, vigencia y contexto de equipo, y exige dueño de negocio vigente sin pertenencia a otro equipo. No basta la cookie de refresco ni un rol suministrado por el cliente. La confirmación conserva además la vinculación entre cuenta y suscripción en el servicio del proveedor. Los callbacks y las consultas autoritativas de pago no cambian; volver desde Stripe por sí solo no activa un plan.

La gestión del equipo, Mercado Pago, inicio de sesión con MFA ya activado y configuración de seguridad de cuenta conservan sus requisitos. Los registros de acciones MFA de Stripe permanecen para compatibilidad con clientes anteriores; las rutas de pago ya no requieren ni usan esos grants como autoridad para pagar. El portal confirma la transacción local antes de devolver una capacidad externa y conserva el rechazo de un commit incierto.

La autenticación bancaria de una tarjeta puede seguir siendo solicitada por Stripe o el emisor. Es un paso distinto del requisito de configurar un factor en Método Base. Referencias oficiales: [Stripe Checkout](https://docs.stripe.com/payments/checkout) y [3D Secure](https://docs.stripe.com/payments/3d-secure). No se modifican claves, configuración del proveedor, precios, cuotas, esquema o dependencias.

## Validación y publicación

Las reproducciones antes/después, contratos del SDK, pruebas HTTP de identidad y revisión independiente de seguridad se registran con hashes de la fuente. Los proveedores se controlan en pruebas: no se hacen cobros, correos de prueba, cuentas reales o replay de eventos productivos. Las pruebas del navegador verifican la elección inicial y el cambio de plan existente, sin mostrar el diálogo de alta MFA.

El gate final del autor pasa 113 casos, incluidos 22 nuevos sobre intención duradera, idempotencia y confirmación. Seguridad independiente pasa 134; QA independiente pasa diez HTTP y ocho recorridos de Chromium con login, cookie, JWT, SSR, SQLAlchemy y rutas reales a 320/1440. Sólo se controlan SDK Stripe y navegación final al proveedor. El navegador y servidor propios se cierran normalmente. El repositorio conserva las pruebas HTTP portables; el harness Windows se conserva por separado con recibo de extracción sin cambios de AST. Dos líneas vacías al final del peer se normalizan con preimagen y comprobación AST, sin cambiar criterios.

Frontend pasa 22 contratos nuevos, 39 de verificación de correo y siete del propósito de Google; sus diez recorridos SSR con transporte interceptado son un gate distinto del HTTP real de QA. Root pasa 57 controles del transporte actual. Los conjuntos solapados no se suman. Las suites JavaScript históricas y sus companions conservan los mismos fallos que la base `b10ab884`; no se presentan como aprobadas. Los intentos rechazados por preparación de datos o entorno del instrumento conservan sus RAW y fuentes originales.

Un job independiente `stripe-purchase-transport` ejecuta los 22 contratos nuevos y los 39 de correo en Node24; el agregado `ci-success` lo requiere. No se deshabilitan los controles generales de calidad o secretos. El resultado Linux y la observación productiva corresponden a los recibos posteriores de la publicación.

Los contratos activos que utilizaban una compra Stripe para probar la obligatoriedad MFA se adaptan a la política solicitada, conservando los criterios de sesión, aislamiento, un solo uso y errores inciertos en los recorridos que siguen protegidos. Los recibos históricos y el informe de auditoría anterior conservan su fecha y alcance. Este cambio no cierra el ciclo sandbox externo ni los pendientes generales de CI, recuperación o contabilidad parcial.

El corte parte de `b10ab884fca9d5b6667aafc6d30c509d7e08b9a6` en un worktree aislado. Root conserva 704 fuentes locales originales y el backlog vigente antes de publicar. Commit, imagen, despliegue, comprobación pública y fuentes de runtime se enlazan en los recibos de `E:/MetodoBaseWorkspace/evidence/stripe-purchase-no-factor-root-20261102T072621Z/`. La publicación usa sólo rutas explícitas revisadas y conserva las preimágenes al sincronizar el repositorio activo.

# Seguridad de cuenta y confirmación del contacto — 1 de noviembre de 2026

Cambio preparado y revisado para el servicio web. Este documento describe el candidato local; no acredita su despliegue. Complementa el [contrato inicial de correo para compras](20261101-billing-email-verification.md), cuyo requisito de repetir el código se sustituye por la comprobación persistida del contacto vigente.

## Comportamiento e interfaz

«Seguridad de mi cuenta» adopta la presentación clara y verde del panel, con etiquetas, campos y acciones adaptables a móvil. Distingue dos estados: correo confirmado y autenticador activo. Explica cómo confirmar la identidad, configurar el autenticador y volver a Suscripción. Configurar la seguridad no activa un plan ni acredita un pago.

La reautenticación con contraseña conserva el factor vigente cuando corresponde; sus errores distinguen contraseña e identidad de un código del autenticador incorrecto. La semilla manual y los ocho códigos de recuperación se muestran únicamente en sus regiones explícitas, sin almacenarlos en atributos, URL, Storage o registros. Confirmar el nuevo autenticador requiere un TOTP válido; después se presenta el kit una vez y se indica volver a iniciar sesión. Permanecen visibles «Recuperar acceso» (`/auth/reset-password`) y «Gestionar Google» (`/cuenta/google`).

## Correo confirmado y compras

Las verificaciones satisfactorias por código de compra o por acceso Google guardan la confirmación del contacto actual y su versión. En el acceso Google sólo se confirma ese contacto cuando coincide con el correo del proveedor. No se infiere retroactivamente una confirmación de identidades antiguas ni de eventos de auditoría.

`POST /api/billing/email-verification/request` devuelve exactamente `{"email_verification_required":false,"email_verified":true}` cuando el contacto actual ya está confirmado. En esta rama no envía correo, crea challenge ni emite una autorización de correo. El frontend acepta la unión estricta, omite el diálogo y la cabecera `X-Billing-Email-Grant`, y continúa la operación protegida. Para contactos pendientes mantiene el código previo y adopta el challenge inicial sin solicitar un segundo envío.

El servidor vuelve a comprobar el contacto persistido bajo bloqueo antes de comprar. Si se presenta una autorización de correo, conserva su vínculo con cuerpo, acción y clave exactos. MFA, permisos, aislamiento de cuenta, intención de pago y evidencia del proveedor siguen siendo obligatorios. Cada destinatario procede del contacto actual de su propia cuenta; el navegador no elige una dirección común. Cambiar de contacto o de identidad invalida las pruebas anteriores.

## Google y prueba reciente para seguridad

La nueva ruta permite reautenticar la identidad primaria mediante un JWT básico de Google **ya vinculado** y un código de correo nuevo. No requiere fabricar `auth_time`; la ruta antigua de reautenticación Google sigue rechazando credenciales sin esa frescura. No se vinculan cuentas legadas por coincidencia de correo.

- `POST /api/auth/mfa/google-email/request`, cuerpo exacto `{google_credential}`: HTTP 202 con challenge opaco, vencimiento, correo oculto y espera de 60 segundos.
- `POST /api/auth/mfa/google-email/verify`, cuerpo exacto `{challenge,code}`: devuelve la autorización opaca de reautenticación existente. El challenge dura 300 segundos y admite cinco intentos.

El estado queda ligado a identidad Google, cuenta, acceso, sesión, contacto y generación del factor. El código es necesario aunque el contacto esté confirmado: acredita una acción reciente de seguridad. Su consumo confirma también el contacto bajo la misma transacción. Esta prueba no habilita el autenticador, inicia sesión ni autoriza un pago por sí sola. Si existe factor, sigue siendo necesario para sustituirlo o revocarlo. Cancelación, caducidad, fallo del correo y cambio de cuenta descartan el intento; no se reutiliza la credencial Google para reenvíos automáticos.

## Registro manual

El formulario incorpora etiquetas, ayuda, foco y mensajes por campo para nombres, correo y confirmación de contraseña. Respeta nombres de hasta 150 caracteres, límites de transporte del correo y contraseñas nuevas de al menos 15 caracteres y hasta 72 bytes UTF-8. El servidor conserva su autoridad y política de contraseñas. Los registros privados sólo añaden motivos categóricos permitidos, sin correo, contraseña ni cuerpo de solicitud; la respuesta pública sigue siendo genérica.

Se observaron respuestas 400 productivas, pero **no se ha demostrado su causa**. La mejora de validación y diagnóstico no permite atribuirlas a una contraseña, correo existente u otro dato concreto.

El registro manual admite correos válidos sin una lista exclusiva de proveedores. Por petición explícita se comprobaron 18 altas e inicios de sesión HTTP (negocio/personal) con Gmail, Outlook, Hotmail, Live, iCloud, me.com, mac.com, Apple private relay y un dominio corporativo sintético. Cada caso conserva su correo normalizado y dirige bienvenida y OTP de compra a esa misma dirección. Los transportes están interceptados: la aceptación del formato no acredita entrega de un proveedor ni las reglas de reenvío de Apple private relay. No se añade inicio de sesión con Apple o Microsoft por este ajuste.

## Verificación y recibos

Los conjuntos se solapan y no se suman como cobertura global. Los recibos conservan hashes, intentos previos y alcance:

| Responsable y alcance | Resultado | Recibo en `E:/MetodoBaseWorkspace/evidence/` |
| --- | --- | --- |
| Autor backend: persistencia, rama ya confirmada y destinatarios A/B | 161 PASS | `billing-code-20261101-author-770870de4c604606896d62d71faf525f/author-summary.json` |
| QA independiente: nueva ruta de seguridad; contacto y compras; Lua en Redis propio | 35 y 20 PASS; Redis cerrado normalmente, cero claves finales | `billing-code-20261101-qa-59ade630a88e44fda342fbdc3abb4ec4/qa-summary.json` |
| Autor frontend: API de compras, API Google/correo, páginas y componente Chromium | 39, 13, 8 y 17 PASS respectivamente | `account-security-ui-20261101-7fd39b6e/author-summary.json` |
| Revisión independiente del frontend final | 39 y 13 casos API; 17 casos Chromium, ocho capturas, 320/390/768/1440 px, sin desbordamiento ni hallazgos axe A/AA | `billing-code-20261101-root/ui-independent-summary.json` |
| Registro y revisión final de fuentes | 62 pruebas backend PASS; revisión de 26 casos de navegador satisfactorios y hashes finales | `billing-code-20261101-root/registration-final.xml` y `final-ui-registration-review.json` |

La prueba heredada `mfa_state.cjs` usa una fixture anterior a las cookies: conserva 4/30 PASS tanto con HEAD como con el candidato, con resultados idénticos. Se preserva como limitación, no como aceptación nueva. Las pruebas actuales usan SQLite aislada, identidades/JWKS y correo/pago simulados; QA añade TOTP real, ambas factories y Redis propio. No acreditan PostgreSQL/RLS, carga, entrega a bandejas reales, Google real ni cobros productivos. La aceptación del proveedor de correo no demuestra llegada al buzón; no se ha probado una avería de transporte como causa de la incidencia inicial.

## Pendientes del corte

Root completó la corrección de `STRIPE_PRICE_STANDARD` y `STRIPE_PRICE_CLINICA`: las referencias observadas respondían 404 y ahora apuntan a los Prices activos existentes de 15900 y 97900 centavos MXN/mes, respectivamente. La lectura posterior confirmó que sólo cambiaron esas dos variables. La operación usó `--skip-deploys`, sin despliegue automático, nuevos productos, precios ni cargos; Gym y Pro conservaron sus referencias correctas. Recibo: `E:/MetodoBaseWorkspace/evidence/billing-code-20261101-root/stripe-reference-correction-9f170df412a54e5393ebfccc57e51d79.json`. El candidato continúa sin desplegar.

Quedan la publicación y la comprobación pública posterior. Este corte no declara despliegue, acceso a cuentas productivas, envíos a clientes ni cobros como parte de su aceptación. No modifica los pendientes globales ni la documentación histórica.

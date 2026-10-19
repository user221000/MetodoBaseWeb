# R32: contrato backend31 (autoría aislada)

Base: `3c764d8486eb111f1dfa0ff2f238dd2ab0308792`. Este documento describe decisiones y criterios pendientes de ejecución, no una aceptación de MFA. R32 exige alta, desafío, recuperación, revocación y step-up de equipo/facturación; B19/B20 no exigen implementar simultáneamente passkeys y TOTP.

## Factor y adopción

TOTP RFC6238/HOTP RFC4226, HMAC-SHA1, semilla aleatoria de 160 bits, seis cifras, intervalo30s y sólo contador actual. Una aceptación registra el contador bajo lock de cuenta: nunca se acepta dos veces el mismo intervalo, incluso entre login y step-up. La falta de tolerancia adicional de reloj es explícita; el UI mostrará la necesidad de sincronizar el dispositivo. No se almacena un dispositivo o navegador como autoridad.

La semilla se cifra AES-256-GCM con nonce aleatorio, AAD que fija usuario/generación/propósito y `MFA_ENCRYPTION_KEY` propia (base64url de32bytes, sin derivación/default de WEB_SECRET_KEY). Configuración ausente/inválida bloquea MFA; producción rechaza startup sin key. Cambiar o perder la key no desactiva factores ni devuelve plaintext. Rotación criptográfica operativa requiere conservar la key anterior y un procedimiento separado verificado; no hay fallback.

Owner profesional canónico y admin de equipo sin factor conservan login/lectura/recuperación/enrolamiento, pero cambios privilegiados responden403 `mfa_enrollment_required`. Cuentas personales pueden enrolar sin ganar permisos profesionales. OWNER/tipoUsuario ambiguo no recibe autoridad nueva. No cambian roles, pertenencias ni la cartera personal.

## Estado31

Tres tablas nuevas, sin columnas Usuario ni backfill de asociaciones:

- `mfa_credentials`: una fila por user_id, semilla activa/pending cifrada, generación, expiración pending, último contador, enabled_at y presupuestos de intentos por propósito. ENABLE/FORCE RLS personal `user_id=current_tenant`.
- `mfa_recovery_codes`: hash SHA256 con prefijo de propósito de códigos CSPRNG de128bits, generación, used_at; propietario con ENABLE/FORCE RLS. Ocho códigos iniciales, elección técnica del kit, no cupo comercial. Se muestran una vez y regeneración invalida el kit anterior.
- `mfa_authorizations`: control plane mínimo como RefreshToken: digest de bearer aleatorio256bits, user_id/SV/generación, propósito login/reauth/action, expiración, consumed_at, binding del access y acción/recurso/body. Sólo consultas por digest+propósito+actor verificado; no API de listado ni datos nutricionales. Su acceso público sólo sigue una prueba primaria ya validada o un bearer opaco. No se afirma RLS universal.

Revisión31 conserva targets22–30 y las20 políticasv1/guards R12 exactos, añade target SQLite/PG propio y requiere estructura, flags/policies e índice30 exactos. Downgrade sólo sin estado MFA: con factor/códigos/authorizations presentes aborta en lugar de eliminar autoridad de seguridad. Upgrades y fallos transaccionales conservan filas anteriores.

## Flujos y transacciones

Contraseña y Google verificados mantienen su identidad persistida. Con factor activo, login devuelve202 `mfa_required` con challenge opaco (5min), sin access/refresh. Verificación de TOTP o código recovery consume challenge/factor y crea refresh en la MISMA transacción; access+refresh mantienen formato payload.HMAChex64 de dos partes. Sólo después de COMMIT confirmado se devuelven tokens. Refresh conserva evidencia MFA y jamás eleva un refresh sin evidencia sobre factor activado; SV invalida pares anteriores.

Alta exige reautenticación primaria reciente ligada al access exacto. Para Google se valida nuevamente la credencial contra el proveedor ya configurado y se compara sujeto/correo canónico persistido; pruebas usan transporte sintético. Pending dura10min; seed/otpauth se entregan una vez en respuesta no-store. Confirmar OTP activa factor, revoca refresh y aumenta SV; devuelve kit recovery una vez y pide nuevo login. Reemplazo, regeneración del kit y revocación requieren primaria fresca más factor válido. Password reset28 sólo cambia contraseña/SV/refresh: conserva MFA. Recovery de MFA usa contraseña/Google más código guardado de un uso; no usa correo como segundo factor. Si se pierden todos los factores/códigos no existe bypass local: intervención con prueba equivalente pendiente, sin fingir un operador real.

Cuenta y todos los Usuario requeridos se bloquean en orden total ID con NOWAIT antes de recursos; revalidación de activo/deleted/SV/rol/equipo y parent canónico bajo esos locks. Contención revierte entero y409 `mfa_busy`, sin retry parcial. Orden posterior: credencial/código/authorization, RefreshToken y recursos existentes. No se vuelve a adquirir Usuario después de recursos. Transacciones propias sin finalizer autocommit adicional. ACK incierto/rollback incierto devuelve503 opaco; nunca entrega seed/códigos/tokens antes del COMMIT.

Intentos de contraseña/OTP/recovery se presupuestan por actor+propósito en DB bajo lock, sin reset por challenge nuevo, además de IP en limiter existente. Diez fallos/ventana5min y máximo cinco fallos por challenge, técnicos; sin bloqueo permanente ni cambio de cuenta. Redis configurado fallido rechaza antes de trabajo; en producción Redis obligatorio para admisión sensible. No se depende sólo de memoria por worker.

## Step-up: matriz exacta

Grant aleatorio256bits,5min, un uso, liga user_id+SV+generación+SHA256 del access firmado EXACTO+gym derivado del principal+acción+recurso+SHA256 del DTO canónico (incluye Idempotency-Key cuando exista). Un grant de otro access, método, recurso, body, tenant o acción no sirve. Emitir y consumir revalidan RBAC vigente y pertenencia; el grant nunca concede un rol.

| Acción | Rutas protegidas | Recurso / contenido ligado |
|---|---|---|
| team.invite | POST /api/gym/team/invite | gym canónico + DTO completo |
| team.resend | POST /api/gym/team/{id}/resend-invite | target persistido del gym |
| team.role | PATCH /api/gym/team/{id}/role | target + rol DTO |
| team.remove | DELETE /api/gym/team/{id} | target persistido del gym |
| billing.checkout | POST /api/billing/checkout y /api/pagos/stripe/session | ruta exacta + DTO + key |
| billing.subscribe | POST /api/billing/stripe/subscribe | DTO + key |
| billing.confirm | POST /api/billing/confirm-subscription | subscription_id DTO |
| billing.portal | POST /api/billing/portal | return_url DTO |
| billing.mp | POST /api/billing/mp/preference y /api/pagos/mp/preference | ruta exacta + DTO + key |

Rutas individuales de compra, lectores y callbacks firmados siguen su autoridad actual; no se fuerza interacción MFA a webhooks/jobs. Grant de equipo se consume en la misma transacción que la mutación. Para puerto externo de pago se persiste consumo antes de salir a proveedor (junto con intención cuando existe); fallo o ACK incierto no hace reutilizable el grant ni afirma cobro. Reintento pide step-up nuevo y conserva idempotencia financiera existente.

## API / UI prevista

`GET /api/auth/mfa/status`: enabled, pending, recovery_codes_remaining, required_for_privileged_actions, métodos/límites técnicos; sin seed/hashes. `POST /reauth` (password o google_credential) devuelve proof5min ligado a access. `POST /enroll` consume proof, devuelve enrollment_id, secret/otpauth una vez y expires_at; `POST /enroll/confirm` enrollment_id+code devuelve codes una vez y reauthenticate=true. `POST /login/verify` challenge+code o recovery_code devuelve par sólo tras commit. `POST /step-up` {method,path,body,idempotency_key,code|recovery_code} devuelve grant+expires_at; la operación lleva `X-MFA-Grant`. `POST /recovery-codes/regenerate` y `POST /revoke` exigen reauth proof y factor. JSON estricto, tamaños limitados por lectura stream antes de parseo, exactamente una prueba de factor, secretos nunca query/URL/Storage/log. Respuestas y errores MFA usan no-store/no-referrer y protección first-party final en ambas factories, incluidos405/429/503/500.

Pruebas pendientes: RFC vectors; baseline primary-only→rechazo; dos factories; PG app NOSUPER/NOBYPASS/noowner, dos tenants, FORCE/pool; carreras OTP/código/step-up/SV/equipo; rollback y ACK perdido; migración30→31 vacío/poblado/drift/repeat/downgrade; restore31 propio; UI/QA/SEC independientes posteriores. No envío, pago, infraestructura ni claves reales.

Fuentes primarias: [RFC6238](https://www.rfc-editor.org/rfc/rfc6238.html), [RFC4226](https://www.rfc-editor.org/rfc/rfc4226.html), [ASVS5.0.0 V6](https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x15-V6-Authentication.md), [NIST800-63B-4](https://pages.nist.gov/800-63-4/sp800-63b.html). TOTP no es resistente al phishing: no se declara cumplimiento AAL2 completo ni certificación ASVS. Passkeys son una mejora futura, sin atribuirlas a esta implementación.

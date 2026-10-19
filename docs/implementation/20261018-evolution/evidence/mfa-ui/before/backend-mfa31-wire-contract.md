# R32 wire v1 para UI (backend31 aislado)

Contrato consumidor estable de esta ola. Describe interfaces implementadas, no aceptación independiente ni producción. Backend sigue en `F:/mb-mfa31-20261019`, base `3c764d8486eb111f1dfa0ff2f238dd2ab0308792`; aún no se copia WIP a otro worktree. UI coordinará composición después del freeze. La propuesta original y las adendas de contexto/testigo permanecen históricas.

## Transporte e identidad

Ambas factories montan las mismas rutas `/api/auth/mfa/*`. Los endpoints autenticados usan `Authorization: Bearer <access>` vigente; `login/verify` es público y sólo acepta su challenge opaco previamente emitido después de una primaria válida. El backend resuelve actor, rol, pertenencia, SV y generación persistidos en cada operación. Nunca enviar `gym_id`, actor, SV, generación, `amr` ni `mfa_at` como autoridad de un DTO. Los tokens existentes son DOS partes `payload.HMAChex64`, no JWT de tres partes.

Los POST MFA leen como máximo32768bytes de stream antes de JSON/validación. JSON estricto: extras, duplicados, valores no finitos, números en lugar de strings y dos pruebas de factor simultáneas se rechazan íntegros. `code` son seis cifras ASCII; `recovery_code` son22caracteres base64url; challenge/reauth/grant son43caracteres base64url; enrollment_id son32hex minúsculas. Son ejemplos sintéticos los marcadores `<...>` siguientes, no valores utilizables.

Todas las respuestas de la familia MFA (éxito/error, incluidos405/429/503/500) finalizan con `Cache-Control: no-store`, `Referrer-Policy: no-referrer` y CSP first-party fija. No enviar secretos en query, fragmento, logs, analytics, atributos DOM serializables, LocalStorage o SessionStorage. Challenge/proof/grant/seed/códigos permanecen sólo en memoria de la vista y se descartan al salir/cambiar sesión. El acceso normal que emite el backend sigue el gestor central de sesión existente. No implementar MFA con flags locales.

## Login de contraseña y Google

`POST /api/auth/login` conserva `{email,password,remember_me}` y `POST /api/auth/google` conserva su DTO actual. Primaria válida SIN factor:200 con `{mfa_required:false,token,refresh_token,tipo,role,team_gym_id,nombre,email}`. Con factor:202 exclusivamente:

```json
{"mfa_required":true,"challenge":"<bearer43>","expires_at":"<UTC ISO8601>","methods":["totp","recovery_code"]}
```

Un202 no inicia sesión, no permite navegación autenticada y no trae access/refresh. La UI conserva el challenge en memoria, pide TOTP o un código recovery, y envía uno de:

```json
{"challenge":"<bearer43>","code":"123456"}
```

```json
{"challenge":"<bearer43>","recovery_code":"<recovery22>"}
```

`POST /api/auth/mfa/login/verify` devuelve200 `{token,refresh_token,tipo,role,team_gym_id,nombre,email}` sólo después de confirmar el commit. Challenge expira a5min y es un uso; un código recovery también es un uso. TOTP de30s sólo admite contador actual y no se reutiliza entre propósitos. La UI permite cambiar de método sin crear autoridad nueva. Contraseña recuperada por R16 NO desactiva MFA.

## Estado y reautenticación primaria

`GET /api/auth/mfa/status` (sin DML ni recuperación de secretos):

```json
{"enabled":false,"pending":false,"recovery_codes_remaining":0,"methods":["totp","recovery_code"],"required_for_privileged_actions":true,"totp_period_seconds":30,"challenge_lifetime_seconds":300}
```

`required_for_privileged_actions` describe la exigencia del rol privilegiado, no concede permiso profesional. OWNER/tipoUsuario ambiguo no obtiene cartera ni acción profesional por esa bandera. El registro/RBAC persistidos siguen siendo autoridad.

`POST /api/auth/mfa/reauth` exige exactamente `{password:"..."}` o `{google_credential:"..."}` y devuelve200 `{reauthentication_token:"<bearer43>",expires_at:"<UTC>"}`. Proof un uso, ligado al acceso exacto. Un refresh nuevo o access recién emitido no sirve como primaria fresca.

Google: usar el proveedor ya configurado y solicitar metadata esencial `auth_time, amr` junto con una autenticación real reciente. Backend verifica `auth_time` del proveedor, su edad `<300s` y correo canónico igual al Usuario persistido. `iat` no sustituye `auth_time`. Credencial sin metadata/antigua/futura se rechaza403 `mfa_primary_reauthentication_required`; UI vuelve a ofrecer autenticación del proveedor o contraseña. No fabricar timestamps, correos ni proof localmente. La configuración/experiencia Google real requiere verificación externa posterior.

## Alta, reemplazo, kit y revocación

`POST /api/auth/mfa/enroll` inicialmente `{reauthentication_token:"<bearer43>"}`. Si YA hay factor, añadir exactamente `code` O `recovery_code` vigente. Nunca basta MFA reciente ni una primaria sola para reemplazarlo. Respuesta200 una vez:

```json
{"enrollment_id":"<hex32>","secret":"<base32>","otpauth_uri":"<otpauth URI>","expires_at":"<UTC>","shown_once":true}
```

Pending expira a10min. Mostrar semilla/QR localmente en esa vista, sin servicio de QR externo ni persistirla. `GET status` nunca repite seed/URI. Si se pierde la respuesta, iniciar otro flujo primaria/enroll; no asumir que se recibió el secreto. No se cambian aún los permisos del factor activo mientras sólo existe pending.

`POST /api/auth/mfa/enroll/confirm` con `{enrollment_id:"<hex32>",code:"123456"}` devuelve200:

```json
{"success":true,"enabled":true,"recovery_codes":["<8 códigos distintos mostrados una vez>"],"shown_once":true,"reauthenticate":true}
```

Confirmación aumenta SV, revoca refresh y activa nueva generación atómicamente. Limpiar sesión y pedir login completo otra vez. El OTP de confirmación ya está consumido; no volver a ofrecerlo como otro evento de autenticación. Se puede esperar el siguiente intervalo o utilizar un código recovery no usado.

`POST /api/auth/mfa/recovery-codes/regenerate` exige `{reauthentication_token,code}` O `{reauthentication_token,recovery_code}`. Respuesta200 `{success:true,recovery_codes:[...8],shown_once:true,reauthenticate:true}`; sustituye kit anterior y revoca sesiones. `POST /api/auth/mfa/revoke` tiene el mismo body y devuelve `{success:true,enabled:false,reauthenticate:true}`; no concede excepción para mutaciones privilegiadas futuras, que volverán a pedir enrolamiento.

Cambios de factor/kit/revocación causan evento de sesión invalidada en UI: detener tareas/vistas pendientes y limpiar challenge/proof/grant/secretos de memoria, además del cierre central. No convertir un503 en cierre confirmado ni éxito: puede haberse confirmado la mutación y perdido el ACK. Si se pierden todos los factores/códigos, no hay bypass de correo ni operador simulado; intervención segura externa pendiente.

## Step-up por operación

`POST /api/auth/mfa/step-up` autenticado recibe:

```json
{"method":"POST","path":"/api/billing/portal","body":{"return_url":"/dashboard"}}
```

Campos opcionales: `idempotency_key` string ASCII de1..128 sólo en checkout/subscribe/MP; `code` O `recovery_code`. Sin factor en el body se usa una verificación MFA reciente válida para ese acceso. Si ya venció, se responde403 `mfa_fresh_verification_required`: conservar la operación que el usuario observó, pedir una prueba nueva y solicitar otro grant para ese mismo body. No cambiar recurso/body automáticamente.

Respuesta200:

```json
{"grant":"<bearer43>","expires_at":"<UTC>","action":"billing.portal","method":"POST","path":"/api/billing/portal","single_use":true}
```

Consumir añadiendo `X-MFA-Grant: <bearer43>` a ESA petición, con mismo access exacto, método, path, DTO y `Idempotency-Key` cuando se emitió. DTO se normaliza con los defaults de su esquema real; no se permiten extras en el body del grant. Registro cerrado de nueve acciones (las rutas legacy son aliases ligados por separado):

| Acción | Método/ruta | Body |
|---|---|---|
| team.invite | POST `/api/gym/team/invite` | DTO TeamInviteRequest existente completo |
| team.resend | POST `/api/gym/team/{id}/resend-invite` | `{}` |
| team.role | PATCH `/api/gym/team/{id}/role` | UpdateRoleRequest existente |
| team.remove | DELETE `/api/gym/team/{id}` | `{}` |
| billing.checkout | POST `/api/billing/checkout`, `/api/pagos/stripe/session` | DTO real de la ruta exacta |
| billing.subscribe | POST `/api/billing/stripe/subscribe` | StripeSubscribeRequest existente |
| billing.confirm | POST `/api/billing/confirm-subscription` | `{subscription_id}` |
| billing.portal | POST `/api/billing/portal` | `{return_url}` relativo, leading `/` único |
| billing.mp | POST `/api/billing/mp/preference`, `/api/pagos/mp/preference` | DTO real de la ruta exacta |

Cada grant fija actor/SV/generación/acceso/tenant profesional derivado/acción/recurso/body/key. No amplía permisos. Un owner puede mutar sólo su contexto profesional autorizado; admin sigue sus permisos existentes y no recibe cobro-owner. Rutas individuales de pago, lecturas y callbacks firmados mantienen su autoridad anterior; no se exige MFA interactivo a webhooks/jobs.

La verificación reciente dura5min desde el factor ORIGINAL. Emitir/consultar/consumir otro grant NO extiende esa hora; vencimiento `min(factor_original+300s,access.exp)`. Un testigo posterior de factor está ligado al hash de ESE access y no se copia al refresh. Cada grant es un uso aunque comparta el instante original. Body que cambió, otro acceso o CAS/recurso diferente exigen grant nuevo y revalidación normal.

## Errores y recuperación de la vista

Forma normal `{detail:{code,message}}`; nunca reflejar el body técnico completo o secretos en consola/telemetría. Errores de autenticación heredados pueden conservar su detail string; un código no reconocido no se clasifica como éxito ni MFA confirmado.

| HTTP | Códigos MFA |
|---|---|
|400|`mfa_proof_unavailable`, `mfa_verification_failed`, `mfa_enrollment_unavailable`, `mfa_action_invalid` para retorno de portal inválido|
|401|`mfa_identity_unavailable`|
|403|`mfa_enrollment_required`, `mfa_step_up_required`, `mfa_fresh_verification_required`, `mfa_primary_reauthentication_required`, `mfa_action_forbidden`, `mfa_action_mismatch`|
|409|`mfa_busy`, `mfa_grant_consumed`, `mfa_transaction_unavailable`|
|413|`mfa_input_too_large`|
|422|`mfa_invalid_input`, `mfa_action_invalid`|
|429|`mfa_throttled` + Retry-After cuando lo aporta el limiter|
|503|`mfa_service_unavailable`, `mfa_unconfirmed` (o degradación sensible heredada del limiter)|

No reutilizar a ciegas un grant tras timeout/503: reconsultar estado/resultado de negocio, preservar su idempotencia y obtener autorización nueva si procede. No afirmar rollback ni operación confirmada. Los límites por actor/propósito se mantienen en DB, además de admisión IP/distribuida; crear otro challenge no resetea intentos. No hay bloqueo permanente ni cambios automáticos de rol/cartera.

Pendientes de esta ola: UI, pruebas browser, aceptación QA/SEC, restore31 y operación segura de clave/proveedor. Ningún envío o cobro real se atribuye a estas pruebas locales. TOTP no es resistente al phishing y no certifica AAL2/ASVS completo.

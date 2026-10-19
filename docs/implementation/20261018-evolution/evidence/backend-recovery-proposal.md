# R16: propuesta revisable, sin API ni DDL nuevos

Worktree `F:/MetodoBaseWeb-recovery-20261019`, rama `implementation/account-recovery-20261019`. Base de inspección423296f; único cambio de producto incorporado es el cherry-pick autorizado169241a del coordinador, que aquí esddedfb6. No se editaron modelos, routers, correo ni pruebas del coordinador. Las pruebas nuevas son propias y no realizan envíos.

## Evidencia y alcance

R16/UX-15/B19 describen recuperación inexistente y gestión de credenciales incompleta. En el informe de operación, correo es **OPS06**; OPS07 cubre reproducibilidad/despliegue. Se conservan ambos identificadores sin renumerarlos. Esta propuesta incorpora recuperación por correo y su operación local; no certifica verificación general de emails, recuperación MFA, dominio o entrega real.

`tests/test_account_recovery_contract_before.py` reproduce cinco fallos404: request/confirm en las dos factories y formulario web. El control comprueba que contraseña, rol, tipo, pertenencia, activo, cartera y refresh existentes no cambian. La tanda inicial dio5 failed/1 passed en7.23s. La segunda fija explícitamente API key y origen sintéticos con transporte prohibido, preservando el primer artefacto; también da5 failed/1 passed. Son capacidades ausentes, no una enumeración observada ni un incidente live.

`tests/test_account_recovery_inspection.py` demuestra que `straße@example.invalid` y `strasse@example.invalid` son dos cuentas distintas bajo la semántica actual de identidad, pero comparten bucket por el casefold del limiter. El nombre sensible no se envía a Redis: el probe captura únicamente claves HMAC sintéticas.

Referencias primarias leídas el2026-10-19: [OWASP Forgot Password](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html) recomienda respuesta pública uniforme, limitación, aleatoriedad/un uso/caducidad, origen confiable y revocación de sesiones sin autologin; [Resend Send Email](https://resend.com/docs/api-reference/emails/send-email) documenta `from`, respuesta con `id` e idempotencia del envío. Las decisiones y límites siguientes son propuestas específicas para este repositorio, no una certificación por esas fuentes.

## Almacenamiento recomendado: autoridad existente Usuario

Añadir sólo tres columnas nullable a `usuarios`:

| Campo propuesto | Semántica |
| --- | --- |
| `password_reset_hash` VARCHAR64 UNIQUE | SHA256 con dominio `password-reset-v1:` de un token generado con `secrets.token_urlsafe(32)`;43 caracteres URL-safe/256bits; nunca bearer en claro |
| `password_reset_expires_at` UTCDateTime | Vencimiento técnico propuesto30min desde emisión; comparación UTC aware y persistencia tipada UTC-naive existente |
| `password_reset_session_version` Integer | Versión persistida de sesiones al emitir; logout/revocación posterior invalida el enlace aunque siga su hash |

CHECK exige los tres NULL o los tres presentes, digest de longitud64 y versión no negativa. Borrarlos juntos al consumir demuestra un uso sin inventar una fecha used_at. No se reutilizan tokens de acceso, refresh o invitación, ni se acepta su digest como bearer. Las cuentas actuales comienzan con tres NULL, sin inferir enlaces ni modificar sus credenciales.

`usuarios` ya es control plane de auth y lookup público por email/digest; se reutiliza esa autoridad y su índice, sin nueva tabla, función SECURITY DEFINER, bypassRLS o acceso global a cartera. Las consultas nuevas son sólo de auth metadata. Tras verificar el bearer se obtiene su sujeto persistido y se valida contexto compatible; un email del body nunca autoriza binding. La composición API debe excluir explícitamente sólo el prefijo público nuevo del tenant ambiental, como ya hace web con auth. El cliente público no envía Authorization; pruebas negativas cubrirán Bearer de otra cuenta para impedir que se convierta en autoridad.

La recuperación admite el mismo principal activo con rol/tipo válidos y pertenencia vigente; excluye inactive/deleted, invitaciones pendientes y roles desconocidos. Un OWNER puede recuperar su credencial sin adquirir espacio personal ni reinterpretar cartera; tampoco cambia rol/tipo/equipo/Cliente/Plan/cuotas. No existe marcador persistido que distinga Google-only de password: no se infiere por aspecto del hash. El enlace demuestra control del email primario ya almacenado y sólo permite cambiar contraseña de esa misma cuenta; cualquier política SSO-only futura requiere metadata explícita. No modifica MFA ni se presenta como recuperación de factores.

## Correo canónico y contraseñas

Extraer un helper compartido `normalize_account_email = strip().lower()`, conservando exactamente la semántica de registro/login/Google/invitación. Usarlo también para las claves HMAC del limiter. No casefold, NFKC, equivalencia de puntos/plus/Gmail ni búsqueda case-insensitive que elija una cuenta entre dos. Validar controles/longitud/formato antes del lookup, sin migrar emails históricos ni fusionar identidades. Entregar siempre a `Usuario.email`, nunca a un destinatario alterno aportado por el caller.

Política común para credenciales nuevas: mínimo12 caracteres existente y máximo72bytes UTF-8 por bcrypt4.3.0; rechazar íntegramente el exceso, no truncarlo. Confirmación de contraseña debe coincidir. Reutilizar esta validación en registro/invitación al autorizar su alcance, sin cambiar la verificación de contraseñas actuales ni forzar resets. No afirmar que esto implementa una lista de contraseñas comprometidas o todo B19/MFA.

## Contrato público y envío sin enumeración

`POST /api/auth/password-reset/request {email}` responde202 idéntico para cuenta elegible/desconocida/inactiva/invitada y para outcomes posteriores del transport:

```json
{"code":"password_reset_request_received","message":"Si la cuenta puede recuperarse, se intentara enviar un enlace."}
```

El foreground sólo valida un body JSON de hasta4KiB leyendo stream antes de parse, configuración global, límites y admisión universal. No consulta cuentas ni espera al SDK. Propongo dispatcher por proceso con2 workers/32 trabajos admitidos, acotando los pendientes también: una tarea por solicitud sintácticamente válida, independientemente de existencia. El handler no inspecciona el Future ni espera lookup/SMTP/SDK, tampoco usa BackgroundTasks que mantenga la finalización ASGI ligada al envío. Saturación da503 global, antes de saber si existe la cuenta.

El worker usa Session propia. Busca la cuenta elegible, bloquea Usuario y refresca estado, genera bearer y commitea hash/vencimiento/sv antes de enviar. Cierra Session y libera lock/conexión antes del SDK. Cada emisión posterior reemplaza el enlace anterior; los límites por cuenta reducen abuso, pero sólo el último enlace emitido permanece válido. **Pedir recuperación nunca cambia contraseña/activo/sv ni revoca sesiones existentes.** El email explica la rotación sin prometer que el último recibido sea el último emitido.

Sin API key u origen válido, request da503 uniforme antes de lookup/admisión. En producción recomiendo que recuperación requiera Redis configurado; su ausencia/caída da503 sólo a este nuevo recorrido, sin bloquear el login actual. Testing/desarrollo permiten el store acotado local explícito. Límites técnicos iniciales propuestos: request5/900s por IP y3/900s por email HMAC; confirm10/900s por IP y bucket HMAC del token. Todos se comprueban antes de lookup/bcrypt, con namespaces independientes de login. Recuperación no deja de limitar por desactivar el flag en producción. El parser nuevo no llama al dependency actual que lee request.json() completo antes del cap.

La emisión y la recepción202 no constituyen una outbox durable. La cola contiene sólo email normalizado en memoria; el bearer sólo vive en el job y payload del transport, nunca en DB/jobs persistidos/logs. Un crash puede perder una solicitud o dejar un enlace confirmado en DB pero no enviado; el usuario solicita otro. No se finge reintento durable ni se persiste correo/token en claro para lograrlo. Generalizar outbox cifrada/retención sigue en R28, con contrato separado.

El adapter de correo del coordinador ahora retornaTrue sólo con ACKid válido, que significa **accepted**, no delivered. False, excepción, timeout o respuesta incierta se cuentan internamente comounconfirmed y no cambian202. Tampoco se revierte el digest tras un timeout: el correo pudo aceptarse. Sin ACK del commit de emisión no se llama al proveedor. El SDK local tiene timeout30s; no se añade otro cliente/API key global. El template nuevo debe escapar nombres/link, no incluir datos de salud y coordinarse con el dueño de email_service sin editar su lote congelado. Notificación de cambio, sin secretos, sólo después del commit; su fallo no deshace la contraseña.

## Enlace y consumo atómico

Origen exclusivo de configuración `BASE_URL`, validado como origen puro: HTTPS en producción, sin credenciales/path/query/fragment/controles; HTTP sólo loopback en testing/desarrollo. Nunca Host/X-Forwarded-Host/return_url del request. Enlace `/auth/reset-password#token=<bearer>`. Formulario minimalista sin scripts terceros, no-store/no-referrer/nosniff y CSP apropiada; retirar fragmento con history.replaceState inmediatamente y conservarlo sólo en memoria. No query token, GET de consumo, analytics ni localStorage/sessionStorage. Un escáner de correo que haga GET no consume nada.

`POST /api/auth/password-reset/confirm {token,new_password,confirm_password}` es público sin autologin. Input extra se rechaza; JSON/error público nunca refleja contraseña o token. Token inválido/expirado/usado, sujeto ineligible o sv cambiado comparten400 `password_reset_unavailable`; sin estado previo público por email/token. Sólo después de validar bearer se calcula bcrypt fuera del lock largo; después se bloquea Usuario, se recarga y se revalida mediante CAS.

Una Session propia y **un único commit** cambian juntos: password_hash nuevo; session_version+1; refresh del mismo sujeto revocados; tres campos reset aNULL; evento PASSWORD_RESET_COMPLETE mínimo en AuthAuditLog. No llamar `revocar_refresh_tokens_usuario` desde esa TX porque abre/commitea otra Session. Tampoco llamar `log_auth_event(..., db=db)` dentro: hoy commitea aun con Session del caller. Añadir directamente el evento ORM en la unidad de trabajo, sin email/token/password/SQL.

Orden canónico Usuario→RefreshToken. El logout actual hace RefreshToken→Usuario: recomiendo acotarlo a lock Usuario primero preservando su comportamiento y probar reset/logout/refresh concurrentes. La versión capturada en tokens antiguos impide que una rotación tardía se vuelva válida después del reset; no se exige refactor completo de emisión. El overflow de session_version se rechaza sin cambio parcial.

Dos consumidores sólo pueden producir un200; el otro ve400 genérico. Éxito devuelve200 `password_reset_complete` e instrucción de iniciar sesión, sin access/refresh/cookie. Error antes de commit hace rollback. ACK incierto da503 `password_reset_unconfirmed`: **no restaurar la contraseña vieja ni afirmar fallo definitivo**; indicar intentar login normal con la nueva o solicitar otro enlace. Reread separado en pruebas determina si la transacción llegó, sin endpoint público que revele el estado. Las sesiones de otros sujetos y todos los derechos/carteras permanecen iguales.

## Archivos, revisión y gates propuestos

Si se autoriza autoría: nuevo router `web/routes/password_recovery.py`, servicios de recuperación/dispatcher y helper email compartido; montaje en main_web/api; auth.py sólo normalización/política/orden de lock; team/Google sólo helpers acordados; modelos Usuario y migración28 `20261019_account_recovery`, nuevos targets/fixtures por dialecto. Sigue habiendo26 tablas de negocio/20 familiasRLS; el preflight exige exactamente27. No regenerar contratos ni fixtures anteriores. Los tests históricos cuyo criterio exacto es27 se fijan a esa revisión explícita. Coordinar template/puerto correo con root y UI con frontend; no tocar SDK/locks/CI sin asignación.

Antes de freeze: baseline mismo contrato, control registro/login existentes y Unicode sin merge, todos los outcomes de transporte/config/cola comparados públicamente, response ASGI completo mientras SDK sintético bloquea, límites fail-closed y contador sin PII; tokens DB sólo digest y ningún canal de logs/Sentry/URL con bearer/password. SQLite +UUID PG migrado/restringido: expiración/borde UTC-México, dos procesos consumo, emitir/consumir/logout/refresh intercalados, deactivación/invitación entre pasos, sv+refresh+evento atómicos, rollback y ACK real perdido, hash borrado sin reuso y derechos/sesiones ajenas intactos. Migración vacío/27 poblado/rerun/drift/fallo DDL/restore28 con auth metadata y campos NULL, manteniendo27 inmutable. Browser público real después con fragment cleanup, teclado/errores y sin auto-login.

Quedan externos, sin bloquear código local: remitente/dominio y configuración de tracking verificados en proveedor, correo real recibido/rebote observado, recuperación legítima de MFA y política operativa de incidentes. No se contactó a usuarios, proveedor de envío ni SMTP, y no se inició deploy/recurso. La única red utilizada fue lectura de documentación primaria solicitada.

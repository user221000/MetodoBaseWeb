# Incidencia de acceso por correo — 2 de noviembre de 2026

## Causa y corrección

El usuario confirmó que el fallo ocurre después de «Continuar con Google». En el JavaScript publicado `74bcac4837c288d4493f8f7bf5e11e111c881363`, el objeto `Api.mfa` declaraba dos miembros `googleEmailVerify`: el de seguridad sobrescribía al público. El navegador enviaba el código de acceso a `/api/auth/mfa/google-email/verify`, que exige una sesión y una prueba con otro propósito. La lectura del recurso público confirmó la colisión. Los metadatos productivos observados contenían cuatro respuestas 202 al iniciar Google y ocho 403 en la verificación privada, sin llamadas al verificador público en la muestra. Esa muestra no identifica a una persona ni demuestra la entrega de todos los mensajes.

La corrección mínima separa el comando público `loginGoogleEmailVerify`, usado por `MfaLogin`, del comando de seguridad existente. No cambia el endpoint público `/api/auth/google/verify-email` ni convierte una prueba de seguridad en sesión de acceso.

La revisión independiente encontró otro defecto: la admisión del transporte de navegador no incluía los dos POST de seguridad Google+correo que la propia web solicita. Se añaden únicamente esas dos rutas a `COOKIE_POSTS`. Se mantienen origen, cabeceras, JSON, sesión, actor, propósito, contacto, TTL, consumo único, intentos y segundo factor. `PRIMARY` y `REVOKING` permanecen idénticos.

## Contratos REST y prevención

La factory API registraba dos handlers para tres operaciones nutricionales; OpenAPI describía el que no ejecutaba el dispatcher. Se conservan los handlers efectivos de generación/catálogo/PDF y los handlers privados de historial, eliminando sólo las duplicaciones. Las dos factories documentan ahora los DTO y variantes existentes de verificación de compra, conservando el parser estricto de 4 KiB y sus controles de claves duplicadas.

Se añade un contrato con el `api.js` exportado y la máquina `MfaLogin` reales en el mismo entorno de navegador simulado. Tiene watchdog por caso, resumen obligatorio y exactamente siete casos. Se ejecuta en el job independiente `auth-email-transport`, sin dependencias npm, para que no quede omitido por el fallo anterior del pipeline general. No se modifican los pins o aprobaciones de ese pipeline.

## Evidencia de aceptación acotada

- Autor frontend: rojo seis fallos de siete en la base; verde siete de siete, más regresiones separadas 13/55/33. Auditoría AST con herramienta instalada: una colisión previa y cero después en 57 archivos; esa auditoría no se declara gate de CI.
- Autor backend: rojo tres rutas duplicadas y cuatro contratos de body ausentes; 22 contratos HTTP verdes. Inventario final API 184 / Web 203 operaciones HTTP efectivas, sin duplicados. Enumerar rutas no certifica el comportamiento de todas ellas.
- QA independiente: 25 contratos de admisión con las factories completas, cabeceras reales y prueba de actor/origen/replay. El rechazo inicial por contar la cookie CSRF como cookie de sesión se conserva y corrige en el instrumento.
- QA independiente de extremo a extremo: el JavaScript publicado falla contra el backend real. El candidato pasa Chrome → HTTPS → validación criptográfica de JWT/JWKS Google sintético → Redis Lua → correo capturado en RAM → código → cookie de sesión y destino. Se prueban negocio sin MFA y personal con TOTP criptográfico obligatorio. Servidores y Redis propios cierran normalmente; no se contactan Google o buzones reales.
- Seguridad independiente: 90 pruebas focales sin fallos/errores/skips, con 14 fuentes de aplicación estables. No se atribuye aceptación comercial general a esos conjuntos solapados.

Root: `E:/MetodoBaseWorkspace/evidence/production-auth-audit-20261101-20261102T0500-root/`. Autores: `production-auth-frontend-20261101-20261102T0515/` y `production-api-backend-20261101-20261102T0500/`. QA: `incident-qa-20261101-c0fcf18a/`. Seguridad: `incident-security-20261102-9b52b105/`. Operación: `incident-operations-20261102-666087a6da2c40be932abfa1092f9a38/`.

## Publicación, límites y recuperación

El candidato parte del commit productivo 74bcac48 en un worktree aislado. Los cambios locales anteriores de correo/API/pagos del worktree activo conservan su preimagen y se diferencian del lote publicado. No hay dependencias de aplicación, migraciones, cambios de esquema, DNS, claves, variables, precios o cuotas nuevos. El hash de recursos de la factory Web cambia al iniciar y versiona juntos `api.js` y `mfa-login.js`; una pestaña ya abierta debe recargarse y comenzar un intento nuevo.

La publicación requiere comprobar commit/imagen/estado de Railway, `/health/ready` y hashes/versiones de los recursos públicos. La prueba con una identidad Google y buzón reales del usuario se solicita después del despliegue; no se conservan códigos o credenciales y no se atribuye esa recepción a los dobles de prueba.

La auditoría ampliada de todos los módulos, webhooks, operación y pendientes comerciales se entrega por separado después del hotfix. El fallo previo del pipeline general por identidad del Dockerfile sigue abierto: no se declara CI global verde. Recuperación: revertir expresamente el commit del hotfix o volver a la versión/imagen de 74bcac48; conservar el trabajo local y todos los recibos.

## Referencias oficiales

Consulta: 2026-11-02. [MDN: miembros duplicados en objetos](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Object_initializer), [Google: verificar el ID token en servidor](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token), [Redis: ejecución atómica de Lua](https://redis.io/docs/latest/develop/programmability/eval-intro/). Se usan para explicar el defecto y conservar las verificaciones criptográficas/atómicas existentes; no se actualizan las dependencias.

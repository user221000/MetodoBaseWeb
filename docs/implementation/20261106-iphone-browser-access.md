# Acceso desde Safari y Chrome de iPhone

El usuario reportó el mensaje «No pudimos preparar el acceso en este navegador»
en Safari y Chrome de un iPhone 14, modo normal, iOS 26. La fuente publicada
era `265eefec42ddbd60c3469b7f95b61f5306ed2567` (`correcion google`).

La reproducción con WebKit real 27.2 en Windows, perfil de iPhone y sin
credenciales, muestra `Origin: null` en el refresh inicial, respuesta 403 con
`browser_origin_invalid`, rechazo de `Api.session.ready` y el mismo mensaje.
Web Locks, UUID y almacenamiento están disponibles. Este ensayo usa el motor
WebKit, no un iPhone físico; las comprobaciones anteriores con Chromium no
cubrían esta diferencia entre motores.

El cliente combinaba `mode: same-origin` y `referrerPolicy: no-referrer` en los
POST del transporte de sesión y de seguridad de cuenta. El algoritmo de
[Origin del estándar Fetch](https://fetch.spec.whatwg.org/#append-a-request-origin-header)
establece el origen nulo en ese caso. El servidor exige correctamente el
origen canónico y lo rechaza antes de consultar credenciales o mutar tokens.

El ajuste usa `referrerPolicy: strict-origin` en esos dos POST. Permite que el
navegador envíe el origen propio; Referer sólo identifica el origen, sin ruta,
query ni fragmento. Se conservan `mode: same-origin`, credenciales del mismo
origen, redirecciones rechazadas, no-store, coordinación de pestañas, CSRF y
comprobación exacta del origen en el servidor. No se fuerza Origin desde
JavaScript ni se admite un origen nulo, ausente o ajeno.

La comprobación empareja el fallo de la fuente anterior con el comportamiento
corregido y después comprueba la fuente candidata exacta. Los ensayos públicos
se limitan a GET y refresh anónimo sin credenciales; las pruebas de registro,
Google/correo, MFA y seguridad usan transportes sintéticos declarados. No se
crean cuentas productivas, envían códigos ni hacen cargos para comprobarlo.

Antes de publicar pasan 40 casos HTTP/ASGI de admisión y once contratos Node
del cliente real. Los orígenes nulos, ausentes, ajenos y duplicados siguen
rechazados antes de dependencias, handler o cambios de cookie. La comparación
de motores conserva ocho vistas antes/después; la aceptación de la fuente
candidata exacta pasa cuatro vistas WebKit/Chromium, ambas audiencias, con
Google real visible, formulario habilitado y mínimo de siete caracteres.
Pasaron también las regresiones existentes de sesión, transportes, Google,
seguridad y privacidad, con sus recibos separados y sin sumar conjuntos.

Esta corrección da continuidad a la publicación solicitada por el usuario.
Los resultados por motor, contratos Node, guardas HTTP y recibos de commit,
push y deployment se conservan en
`E:/MetodoBaseWorkspace/evidence/iphone-browser-access-20261106/`. El estado
final y los límites de comprobación se registran en `root/final-summary.json`;
no se atribuye una prueba física en el iPhone del usuario.

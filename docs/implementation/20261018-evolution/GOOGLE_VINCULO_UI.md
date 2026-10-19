# Google: vínculo explícito de cuenta

Base de autoría: `2273616eb218adfdd30680e111da50a4599a8c53`, worktree exclusivo
`F:/mb-google-link-ui-20261019`. No se integra backend 33 ni se modifica MAIN.
Wire sintético v1 `45fdbf38cd98d462c88852ab95036ba9e2ce702a2e7116e849f701551c208b5b`
y adenda `462ca784b091fcd42cef6e2f38f3a69e8d48c30a38e68562402cae6959d57985`
se conservan bajo `evidence/google-link-ui/contracts/`. Esos documentos fijan el
consumer; su lectura no acredita aceptación de la API, del proveedor ni de sus políticas.

## Recorrido y alcance

`GET /cuenta/google` monta una página pública sin iniciar sesión ni consultar
automáticamente. Desde ambos accesos, el perfil personal y configuración se
ofrece un enlace estático. El estado de vínculos se consulta sólo por acción
explícita con identidad persistida y contexto opaco del transporte actual.
Cada página sustituye la anterior: máximo20 entradas, cursor emitido exacto,
sin acumular toda la historia. Se muestran estado y fechas, sin sub ni contactos.

La preparación carga el botón oficial de Google sólo cuando se solicita. Su
callback se acepta únicamente tras pulsar ese botón y conservar la correlación
en RAM. Después se pide la contraseña local independiente y, si corresponde,
un factor nuevo. La prueba recibida prepara un intento; confirmar requiere otro
clic tras mostrar el contacto de Google como selección, sin adoptarlo como
contacto local ni identidad de otra cuenta. La desvinculación exige seleccionar
un vínculo de la página, marcar la confirmación visual y aportar prueba nueva.

Los cuatro métodos de `Api.googleLink` tienen rutas y cuerpos cerrados:
`status`, `start`, `confirm`, `unlink`. Delegan en `_mfaRequest` existente y
exigen el mismo access exacto durante la operación. No hay refresh, replay ni
readback automático. Los errores 409/503, el vencimiento o un ACK malformado
descartan el intento; la UI explica que debe consultarse explícitamente antes
de otra intención. No se interpreta un texto localizado como confirmación.

Sólo el ACK tipado de confirm/unlink permite cerrar la sesión: primero se
limpian pruebas, contacto, filas y DOM; después se invoca el cierre central
cercado y se ofrece autenticarse de nuevo. Una sesión reemplazada, incluso
dentro de un listener síncrono, conserva sus credenciales y descarta la vista.
Un fallo de Storage no provoca reparación, borrado adicional ni navegación.
Las pruebas, JWT e intento no se serializan en atributos, URLs, Storage,
capturas ni logs; los campos de contraseña/factor se limpian por propiedad.
Cancelación, cuenta/revisión, evento de Storage y pagehide invalidan la vista.
No se intenta cancelar retroactivamente una mutación ya enviada.

El mensaje `google_link_required` de ambos logins explica el acceso local y el
vínculo explícito. No cambia su máquina202/MFA, guardado de pares, onboarding,
roles ni permisos. El acceso antiguo sólo con Google y sin sub verificable,
la pérdida de todos los factores y la indisponibilidad de contraseña local
siguen limitaciones expresas. No se inventa una vía de recuperación.

## Configuración oficial de Google

Consulta oficial realizada el 2026-10-19:

- [GIS JavaScript, essential_claims](https://developers.google.com/identity/gsi/web/reference/js-reference#essential_claims):
  el campo de `initialize` es una cadena. Esta página envía
  `essential_claims: 'auth_time'`, `auto_select: false`,
  `button_auto_select: false` y `ux_mode: 'popup'`; una prueba DOM verifica esos
  parámetros. La configuración OIDC URI con objeto `claims` no se traslada a GIS.
- [OpenID Connect, claims](https://developers.google.com/identity/openid-connect/reference):
  `auth_time` describe la autenticación, `iat` la emisión. La selección de cuenta
  y el consentimiento no prueban frescura. El consumidor no decodifica el JWT
  para inventar una prueba local; el servidor debe verificarlo y fallar cerrado.
- [OpenID Connect, configuración](https://developers.google.com/identity/openid-connect/openid-connect):
  solicitar el claim requiere su habilitación real. No se cambió ni verificó
  configuración de un proyecto Google; ese gate sigue pendiente.
- [GIS, client ID y CSP](https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid):
  se carga únicamente el script oficial `https://accounts.google.com/gsi/client`.
  La composición backend debe permitir los recursos GIS mínimos sólo en la SSR
  exacta y su slash, con no-store/no-referrer; no se modifica CSP global aquí.

La página aporta únicamente `GOOGLE_CLIENT_ID` público desde Settings existente.
Google real, auth_time habilitado/reciente, ventanas emergentes, CSP compuesta
y compatibilidad del proveedor necesitan validación posterior. No se promete
que Google ofrezca reautenticación reciente en toda sesión.

## Evidencia y reproducción

Los 49 casos nuevos de Node son 10 helperAPI,28 controlador,8 DOM/GIS y3 copy.
Usan transporte, credenciales y respuestas sintéticos en RAM. No son HTTP33,
Google real ni browser. Los 8 casos SSR son HTTP local TestClient de la base 32;
comprueban descubrimiento, montaje en las dos factories, semántica, cliente
público y assets propios. La API 33 todavía no está montada en esta rama.

Comandos desde este worktree, sin modificar dependencias:

```text
node tests/e2e/google_link_api.cjs
node tests/e2e/google_link_state.cjs
node tests/e2e/google_link_dom.cjs
node tests/e2e/google_link_login_review.cjs
python -X utf8 tests/run_isolated.py tests/test_google_link_ui.py tests/test_google_link_ui_contract.py -q --tb=short
```

Regresión dirigida histórica:74 transporte y 74 MFA/login, 148 casos distintos
verdes. Los scripts originales no se editan. `invariants.json` demuestra que
el transporte y la máquina MFA anteriores quedan byte exactos al retirar sólo
las adiciones autorizadas. No se reejecutan los históricos de diario/R24.

Antes conservado: 5 SSR rojos por página/enlaces ausentes; 3 copy rojos con el
mismo driver normalizado; 7 DOM rojos por una referencia incorrecta a Api;
posterior 7/8 por DOM privado aún visible durante el cierre. Se conservan además
dos errores de harness sin atribuirlos a producto: regex inicial de IDs que
confundía data-google-client-id y búsqueda ASCII de la palabra vínculo.
`ssr-config-fixture-before.xml` registra el agregado de una aserción que reveló
un monkeypatch de clase incorrecto: Settings lee la variable de entorno en su
constructor. Se corrigió sólo esa fixture, conservando la aserción del valor.

Los proofs usan RAW con `-text`; `source.json` distinguirá RAW de GitLF y fija
productos, drivers y dependencias. La inversa sólo restaura los siete archivos
compartidos y elimina los cuatro nuevos, sin tocar backend/MFA/R24 protegidos.
Si `git diff --check` detecta espacios de contexto del patch inverso, pertenecen
únicamente a ese artefacto exacto; no se recortan ni se aplican al producto.

No se ejecutaron Chrome, axe, lector de pantalla, PG, proveedor, envíos ni
servicios. El diseño conserva foco, labels, targets y texto, pero la revisión
visual 320/390/768/1440 y las pruebas reales tras composición están pendientes.
El scanner global permanece rojo y no se modifica su criterio ni allowlist;
un resultado acotado de fuentes nuevas no acredita saneamiento del repositorio.

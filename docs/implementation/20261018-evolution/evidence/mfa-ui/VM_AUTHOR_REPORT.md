# MFA UI: freeze de preparación, sin backend31 compuesto

Worktree `F:/mb-mfa-ui-20261019`, base `57335e5b4bcba3c76c97d47e481b526fb52874a6`. Wire RAW `ad9ed0c62d2b367f6224ff3339998f1621a0537cf9efb5082bcf1d5e032cda2e`. Esta etapa usa el código central y los controladores reales con transporte RAM doblado; no acredita HTTP31, SQL/RLS, navegador, teclado nativo, contraste, Google ni entrega de correo.

## Resultado y límites por tanda

- `final-mfa_api.json`: 28/28. Login202 sin par, nueve acciones y dos aliases con método/path/body/key exactos, grant de un uso, ausencia de refresh/replay, cambio de cuenta, rotación propia y callbacks reentrantes.
- `final-mfa_state.json`: 30/30. Challenge explícito, expiración/429/503/cancelación, primaria y factor actuales, semilla pendiente, ocho códigos sólo tras ACK y cierre central exacto, kit efímero que resiste su propio cierre y desaparece ante sesión posterior/pagehide, ACK tardío y Storage parcial. Un acceso ya confirmado ofrece reconsultar su destino sin repetir factor.
- `final-mfa_consumers.json`: 8/8. Equipo y facturación montados en DOM mínimo, limpieza síncrona de datos, DTO observado antes del await, respuesta tardía descartada, consulta explícita tras incertidumbre y misma key de compra. No prueba la estructura del DOM del navegador.
- `final-mfa_prompt.json`: 8/8. Prompt first-party explícito, cancelar/Escape, doble clic, enrollment requerido, 429/503 y cambio de cuenta. El modal nativo, foco real y geometría siguen pendientes de navegador.
- Cuatro suites previas intactas: `auth_refresh` 33, `auth_refresh_storage` 26, `auth_refresh_security_review` 13 y `auth_refresh_race_review` 2, verdes. Se mantienen errores de Storage pegajosos, cola, revisión y protección contra sesión cruzada.
- Regresiones existentes del emisor/expiración: 11 + 3 + 10 verdes en archivos `final-session*`. No se presentan como aceptación independiente nueva.
- `pages-after.log/xml`: 8/8 ASGI sólo router de páginas, sin factory/MFA backend. Configuración pública vacía y adversaria escapada, formularios no anidados e IDs MFA únicos. El único delta Python son dos contextos TemplateResponse con `GOOGLE_CLIENT_ID` público; no secreto ni endpoint MFA nuevo.

## Rojos, errores propios y procedencia

- ZIP inicial RAW de 13 fuentes y cuatro inventarios de atributos/textos anteriores a la edición. Son inventarios estáticos Jinja, no capturas SSR/browser.
- `before/api-wire.json`: 0/4 con API base: los helpers intentaban tratar202 como un par y faltaba la interfaz MFA.
- `consumers-historical-before.json`: 1/8. Se extrajeron exclusivamente los consumidores originales del ZIP inicial, conservando la API candidata como proveedor del evento y transporte. No se atribuye a un runtime anterior completo. Método y SHAs en `consumers-before-method.json`.
- `consumers-first.json`: 7/8 por omisión de `URL` en mi harness. La corrección sólo aporta ese global real; no cambia aserciones ni producto para ocultarlo.
- `prompt-first.json` está vacío: el primer DOM mínimo no fijaba el valor inicial de select y la promesa sin actividad dejó terminar Node. No son casos ejecutados/aceptados. El harness posterior elige el método explícitamente y limita cada caso a tres segundos, para fallar si no concluye.
- `state-destination-before.json`: 28/29. Mi controlador devolvía a primaria cuando fallaba el destino después de guardar el par; preimagen exacta `before/mfa-login-destination-before.js` SHA `bfd239883d845f6811127c0b25e9b3f19949755fc8d4cfbdf5da88675e5d5da0`. Se conserva la sesión confirmada y se permite sólo consulta explícita del destino. No se repite la prueba consumida.
- `pages-before.log/xml`: 4/8 por mi referencia local `_s` inexistente en las dos páginas nuevas. Preimagen `before/pages-public-config-before.py`; el fix instancia Settings como los dos login existentes. No es un defecto atribuido a la base aceptada.
- `transport-first.json`: 32/33 por una validación nueva de audiencia en el helper genérico de login200 incompatible con la fixture histórica sin `tipo`. Se mantuvo compatibilidad del helper y la audiencia se verifica en el controlador nuevo antes de guardar/navegar; `transport-compatible.json` y regresión final conservan los33.

La regla `* -text` se añadió al prefix de evidencia antes de su primer add/commit, después de crear algunos archivos. No se afirma que precediera su creación. El ZIP RAW inicial y los bytes históricos no se normalizaron; los JSON/logs de redirección PowerShell pueden estar codificados UTF16. El manifiesto final distingue RAW de GitLF de código; los proofs usan RAW íntegro.

## Seguridad y siguiente composición

Challenge, primaria, OTP/recovery, seed/URI, grant y kit son RAM y texto en vistas específicas; no query, atributos serializados, Storage, console ni analytics. No se modifica la persistencia legacy del par central, la atomicidad entre pestañas/reload o escritores externos: R10/R31 siguen abiertos. El kit se crea después del cierre local confirmado; errores de almacenamiento no reparan/reescriben credenciales nuevas. No se promete revocación remota adicional a la ACK del endpoint.

El transporte ordinario conserva refresh. MFA y negocio con grant usan acceso exacto, no refresh ni replay; un error no concede permisos ni asigna cartera. Cancelar/carga lazy fallida no ejecutan negocio. Los proveedores y Google reales quedan externos; `essential_claims: "auth_time, amr"` sólo solicita metadata, el backend debe verificarla. TOTP no se presenta como resistente al phishing, AAL2 o recuperación administrativa disponible.

Tras esta freeze, root permite nueva composición propia desde `46dc908dd82edaa369f4d095df5abe7703a60de1` (MAIN eea8 + backend56e810, R01 previo). La API31 no está aceptada y su corrección de key en aliases sigue separada. No se copió código WIP. HTTP/browser esperan composición, fix y ventana del coordinador; sin reinicios, Chrome, PG o proveedores durante este lote.

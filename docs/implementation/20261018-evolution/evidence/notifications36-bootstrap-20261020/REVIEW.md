# Arranque de Recordatorios con Api léxico

Base `cd423ab0961898ce94fd2574cb4d6452cf8338b3`, worktree propio
`F:/mb-notifications-bootstrap-20261020`. Cambio de producto: una línea de
`notifications36.js`, default de mount `root.Api.notifications36` por
`Api.notifications36`. No se crea `window.Api` ni se cambia transporte, sesión,
MFA, autorización, contratos, backend, desktop o registro de hallazgos.

Los scripts clásicos comparten el binding léxico `const Api`, pero éste no es
una propiedad de window. La canaria carga el api.js real mediante el harness
existente y evalúa notifications36 en el mismo realm V8. Comprueba Api presente,
`'Api' in window === false` antes y después, sin options.api y sin inyectar esa
propiedad. Usa DOM mínimo y transporte tipado sintéticos, declarados como dobles.

Antes congelado: seis TypeError (dos contextos por mount directo,
DOMContentLoaded y ready-complete), dos controles de API cerrada verdes. Después:
8/8 con el mismo driver SHA ed3b590d y las mismas aserciones. Se mantienen los
límites de contexto, CAS y cuerpo cerrado antes de transporte. El inicio sólo
hace las cinco lecturas esperadas y no envía, escribe ni refresca automáticamente.

Durante preparación del driver, sus dos pruebas de forma usaron por error
assert.rejects para una validación que lanza de forma síncrona. El primer driver
y su resultado 0/8 se conservan como bootstrap-initial, con esa clasificación.
Se corrigió sólo a assert.throws antes de congelar el RED válido 2/8. No se usó
ese error de harness como fallo de producto ni se alteró el driver congelado
después del cambio de producto. Las pruebas de negocio anteriores están intactas.

Regresión dirigida mantenida: 19 estado + 8 DOM + 9 navegación, 36 criterios. Con
los 8 nuevos son 44; los dos controles API ya están dentro de los 8, no se suman otra
vez. Las suites DOM/nav anteriores usan sus propios seams y no sustituían la
prueba del montaje por defecto. No se han repetido suites amplias ni escenarios
de navegador para convertir este cambio focal en aceptación global.

Reproducción desde el worktree con Node existente:

```text
node tests/e2e/notifications36_bootstrap.cjs
node tests/e2e/notifications36_state.cjs
node tests/e2e/notifications36_dom.cjs
node tests/e2e/notifications36_nav.cjs
```

`run_review.py` guarda stdout/stderr RAW en Temp propio con DACL del usuario
aplicada antes del payload. `after-aggregate.json` publica sólo counters,
receipts y hashes. El scanner acotado de esos RAW conserva configuración real
sin allowlist nueva. El orquestador Python sólo usa stdlib/metadatos, sin importar
producto ni abrir SQL; su entorno antiguo tiene 89 distribuciones observadas.
No se atribuye a las 92 del candidato backend actual. Node, locks y 13 fuentes
observadas quedaron estables durante los replays, sin modificar dependencias.

No se ejecutaron Chrome, PostgreSQL, servidor, proveedor, entrega, cookie real
ni API nativa. R27 y el gate global de secretos siguen abiertos. QA repetirá una
canaria independiente y el recorrido nativo después del cierre de sus recursos.
Las preimágenes se conservaron RAW con -text; la inversa restaura exactamente el
producto de la base y las diferencias de contexto de ese patch se preservan.

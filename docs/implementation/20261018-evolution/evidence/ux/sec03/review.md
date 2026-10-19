# SEC03: datos del drawer interpretados como HTML

El dashboard insertaba `Cliente.nombre` mediante `innerHTML` en `_renderDrawerClients`. Con autenticación y CRUD reales sobre SQLite aislada, el POST aceptó un nombre que contenía un `span`; el GET conservó el nombre normalizado y el drawer creó un elemento `span` real. La lista de actividad en `main.js` mostró ese mismo dato escapado. El contrato HTTP rechaza campos adicionales; el ID se genera como UUID y no se demostró que pudiera imponerse un ID arbitrario mediante esa ruta.

La captura anterior muestra también un SVG con handler local e inerte, sin solicitudes de red. El marcador JavaScript quedó falso y la CSP real con nonce bloqueó su ejecución. La clasificación comprobada es inyección HTML persistida. No se demostró ejecución activa de scripts ni bypass de CSP. El segundo sink, `Error.message`, se reprodujo con un Error sintético introducido expresamente en el límite del renderer; no demuestra que un atacante pueda hacer reflejar ese error desde el backend.

El cambio sólo construye tarjetas con `createElement`, coloca datos mediante `textContent` y asigna el ID con `dataset`. El renderer de error usa también texto literal. Se mantienen las clases, metadatos, estados y delegación de clic. Los nombres almacenados siguen admitiendo el mismo contenido y no se modifica CSP, API, modelos, estadísticas ni otros renderers. R23 general sigue abierto.

## Evidencia

`before-source.json` liga la captura anterior al commit `2f8b7f9617503240432e5f6b981f2730c0c9c30e` y comprueba 20 fuentes estables. Los fallos de preparación originales se conservan separados: la primera solicitud tenía un ID adicional y recibió 422; otra captura observó CSP antes de despachar el evento de prueba. Ninguno se presenta como un fallo del producto corregido. Los drivers anteriores son copias históricas del harness temporal y no constituyen el gate portable actual.

`dashboard-drawer-security-after.json` registra 9 comprobaciones posteriores. El gate utiliza autenticación y CRUD reales para persistencia, anonimato 401 y otra cuenta 404. Los negativos de ID, metadatos y error se identifican como dobles del renderer, porque no se atribuye al HTTP la aceptación de esos valores. Se comprueban texto literal, ausencia de nodos inyectados, metadatos e iniciales, ID opaco y clic delegado, estado vacío, badges y ausencia de errores JavaScript.

La fixture usa su propia SQLite y objetos temporales. Bloquea sockets externos del servidor y solicitudes externas del navegador, sin proveedores, correo real, tokens publicados, valores de localStorage ni nonces de CSP. No utiliza la base del checkout principal ni los cambios WIP de estadísticas. Es una comprobación local con Chromium; QA debe repetir independientemente antes de integrar.

## Repetición por QA

Ejecutar desde este checkout con el entorno candidato ya instalado. Cerrar únicamente la instancia propia de la fixture antes de reiniciarla para que cada pasada tenga una base nueva. El servidor escucha sólo en loopback; los dos usuarios y su contraseña son fixtures sintéticas explícitas, no cuentas reales.

```powershell
& 'C:\Users\Consu\AppData\Local\Temp\metodobase-candidate-web-20261018\Scripts\python.exe' -X utf8 tests/e2e/dashboard_drawer_security_server.py --port 8774 --source-report 'C:\Users\Consu\AppData\Local\Temp\sec03-qa-source.json'
```

En otra consola del mismo checkout:

```powershell
$env:SEC03_PLAYWRIGHT = 'F:\MetodoBaseWeb-execution-20261018\tests\e2e\node_modules\playwright-core'
$env:SEC03_BASE_URL = 'http://127.0.0.1:8774'
node tests/e2e/dashboard_drawer_security.cjs 'C:\Users\Consu\AppData\Local\Temp\sec03-qa-output'
```

El gate emite JSON con `total`, `passed`, `results` y termina con código distinto de cero si falla. El directorio de salida de QA debe ser nuevo y estar fuera de esta evidencia histórica. Las rutas de Chrome y Playwright pueden configurarse con `SEC03_CHROME` y `SEC03_PLAYWRIGHT`. No se instala software ni se usa red durante el gate.

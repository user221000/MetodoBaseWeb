# SEC03: texto no confiable en el drawer

Seguridad reprodujo inyección HTML persistida en un checkout aislado de2f8b7f9: autenticación y POST/GET de cliente reales aceptan y conservan markup en el nombre; `_renderDrawerClients` de dashboard.html lo interpreta como DOM. `main.js` ya muestra el mismo nombre como texto escapado. Cuenta ajena recibe404 y petición anónima401.

El handler SVG sintético fue bloqueado por la CSP vigente: marcador JavaScript falso, una violación CSP y cero errores JS. Se confirma inyección HTML, sin afirmar XSS ejecutable bajo esa política. La interpolación de `e.message` también produjo DOM, pero ese caso utiliza un Error sintético del renderer; no prueba control remoto del texto de un error de backend.

Autoría de seguridad en rama `fix/sec03-drawer-text`, commit7321d3bcdb8c7bb4089a46388c4cc87bc544bed0, aún sin integrar. Sólo cambia `_renderDrawerClients` y el error de `abrirDrawer` para construir elementos y asignar texto/dataset. Conserva validación de nombres, autorización y CSP. Añade fixture/driver propios; nueve comprobaciones browser de autor verdes y22 fuentes estables. Dos errores iniciales de preparación se conservan separados.

QA independiente debe repetir con SQLite/credenciales sintéticas nuevas y guardar evidencia propia antes de aceptar el delta. No modificar la fixture ajena en8773; la fixture de seguridad en8774 tiene dueño/PID documentados por el autor. Ruta de trabajo: `C:/Users/Consu/AppData/Local/Temp/metodobase-r21-independent-20261019-mfkiqc7q/dashboard-xss-checkout`; evidencia versionada en esa rama bajo `docs/implementation/20261018-evolution/evidence/ux/sec03/review.md`. La integración copiará esa evidencia conservando sus fuentes/commit; este documento no sustituye el gate independiente.

La corrección no completa acciones, métricas, sesiones o accesibilidad de todo el dashboardR23 ni sanea todos los renderers de la aplicación.

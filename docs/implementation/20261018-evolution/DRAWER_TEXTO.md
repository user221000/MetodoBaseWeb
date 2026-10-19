# SEC03: texto no confiable en el drawer

Seguridad reprodujo HTML persistido con autenticación y POST/GET reales sobre2f8b7f9. El nombre con markup creaba elementos en _renderDrawerClients; main.js ya lo escapaba. Cuenta ajena404 y anónimo401. El handler SVG fue bloqueado por CSP: marcador JavaScript falso, una violación CSP y cero errores JS. Se confirma HTML, sin afirmar XSS activo. El Error.message sintético sólo acredita el sink del renderer.

Autor7321d3bcdb8c7bb4089a46388c4cc87bc544bed0 integrado como0fa124e. Construcción DOM con textContent/dataset conserva validación, autorización, CSP, clases y delegación. Autor9/9 browser y22 fuentes estables; erratas de preparación preservadas en evidence/ux/sec03/review.md.

QA independiente aceptó12/12 (9 replay+3 propios),0 pageErrors y22 fuentes estables. Usa SQLite/auth/POST/GET/PUT/DELETE reales, clic nativo sobre UUID exacto, GET anónimo401/ajeno404, PUT ajeno404 y anónimo CSRF403 sin mutación. Nombres persistidos quedan como texto; IDs/metadatos arbitrarios y errores son dobles sintéticos de renderer. La primera expectativa QA de401 para PUT anónimo se conserva: el middleware CSRF correcto responde403 antes de auth, y sólo se corrigió esa expectativa del harness.

Manifiesto: [QA independiente](evidence/ux/sec03-independent-7321d3b/sec03-qa-independent-source.json), SHA5be7e8eed9fe57e58d9167ef23114dbefe31043c816b3a5f5b65430047ceec63. QA cerró sólo su fixture8777; no alteró8774 del autor. La aceptación es local y delimitada: no completa R23, otros sinks, sesiones, métricas o accesibilidad de todo el dashboard.

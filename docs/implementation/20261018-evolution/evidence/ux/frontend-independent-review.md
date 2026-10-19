# Revisión QA independiente B2B y R13

Se acepta este lote para integración local dentro de su alcance UI. Las 27 fuentes de `frontend-freeze-source.json` conservaron exactamente sus SHA256 después de las tres corridas independientes; el manifiesto revisado tiene SHA256 `5c6eb98d7d8fd1b86ccf6a93dd2b1e14bed6f61e2c301230efde1018664154a5`. Evidencia: `frontend-independent-source.json`.

Contra el runtime candidato real en loopback 8765, con transportes API/proveedor sintéticos y sin conexiones externas:

- `gym_subscription.cjs`: seis escenarios, incluyendo retorno sin activación, retry con la misma clave, claves separadas Stripe/MP, portal sin checkout duplicado, estados incompletos y usuario sin propiedad; cuatro anchos sin violaciones axe, desborde o errores JS.
- `responsive_accessibility.cjs`: 17 estados de clientes, configuración, historial, diálogos, calendario y accesos. Comprueba teclado, foco, Escape anidado, errores visibles y descarga PDF a 320 px; sin violaciones axe, desborde del documento o errores JS.
- `subscription.cjs`: cinco escenarios personales vuelven a pasar después de los cambios compartidos en API/CSS; cuatro anchos y diálogo sin violaciones axe o errores JS.

Se revisaron el módulo B2B, validación de estado/configuración, destinos HTTPS acotados de proveedores, foco modal y las aserciones de los recorridos. No se encontraron observaciones altas/críticas en este alcance. El estado persistido del backend sigue siendo la autoridad; la UI no concede planes por parámetros de retorno.

Los resultados no prueban cobro sandbox, webhook real, RLS ni uso con tecnología asistiva. Las verificaciones visuales/teclado automatizadas tampoco certifican por sí solas conformidad WCAG completa. Los tres logs independientes conservan sus límites sintéticos explícitos.

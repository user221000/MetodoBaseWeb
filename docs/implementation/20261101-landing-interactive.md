# Landing interactiva y compacta — 1 de noviembre de 2026

El usuario solicita una portada más interactiva, con menos desplazamiento por bloques de texto, tomando como referencia [Gymdesk](https://gymdesk.com/). Se trabaja sobre el commit publicado `9a55b7dd3ec41180f082f6ce70586e6526956330`, en `E:/MetodoBaseWorkspace/releases/landing-interactive-20261101-20261102T0330`. El worktree de ejecución y la publicación anterior se conservan por separado.

## Decisiones de experiencia

Se concentran las funciones en una demostración visual, en lugar de repetirlas en tarjetas, públicos y pasos separados. El visitante puede buscar entre tres nombres ficticios, recorrer Clientes/Plan/Historial/Rutinas, avanzar o retroceder y ampliar la misma demostración en un diálogo. El diálogo conserva el estado y devuelve el foco al control de apertura al cerrar. El recorrido es manual y respeta el control del visitante.

Las suscripciones se exploran por audiencia y modalidad. Por defecto se muestra Free de negocio; se puede elegir otra oferta, pasar al espacio personal o comparar todas las ofertas de la audiencia elegida. Los cupos completos están en detalles desplegables. Sin JavaScript se conservan las seis tarjetas, sus enlaces y los detalles nativos. Los fragmentos públicos de negocio y personal siguen funcionando. Ninguna selección activa una compra.

Se conserva la invitación compacta de registro, con elección de negocio/personal, cierre por sesión y reapertura. Se conservan los accesos existentes, el catálogo, la continuidad de la suscripción elegida y la procedencia del ejemplo nutricional. Los precios y límites se renderizan desde el catálogo vigente; no se duplican en JavaScript.

La demostración identifica sus datos ficticios. Buscar y recorrer sólo cambia la presentación en el navegador: no consulta cuentas, crea planes, guarda clientes, consume cuotas ni contacta proveedores. El resultado ilustrado no se presenta como plan de la persona seleccionada ni como recomendación clínica.

## Referencia y medición

Consulta de Gymdesk: 1 de noviembre de 2026, America/Mexico_City. Se adopta su protagonismo visual del producto, demostración y acción principal. No se copian logotipos, vídeo, imágenes, textos, testimonios, cifras de clientes o condiciones comerciales. Gymdesk también tiene una página extensa; reducir su longitud no es el objetivo de la referencia.

La portada publicada de Método Base se midió con viewport de 844 px de alto, demostración en Clientes, invitación cerrada, movimiento reducido y estado inicial de suscripciones:

| Ancho | Altura anterior | Palabras visibles en main |
| --- | ---: | ---: |
| 320 | 11 377 px | 914 |
| 390 | 10 909 px | 914 |
| 768 | 8 254 px | 919 |
| 1440 | 6 199 px | 919 |

El criterio de aceptación es reducir al menos el 40 % de ambas medidas en los cuatro anchos, con el mismo estado de comparación. El contenido completo continúa disponible a petición; no se fuerza desplazamiento horizontal para consultar ofertas.

La aceptación independiente V3 midió 3 103 / 3 084 / 2 655 / 2 210 px a esos mismos anchos: reducciones del 72.7 / 71.7 / 67.8 / 64.3 %. Las palabras visibles quedaron en 323 / 323 / 327 / 334, un 63.7–64.7 % menos. El criterio se cumple en los cuatro tamaños; no se aplica esa medida a un comparador que el visitante haya abierto expresamente.

## Frontera y verificación

Sólo cambia la plantilla pública, su CSS y JavaScript y los contratos afectados de HTTP y Chromium. No cambia el backend, identidad, correo, pagos, precios, cuotas, variables o esquema. La versión de recursos sigue derivándose automáticamente de sus bytes. Los tests conservan catálogo completo, nonce/CSP, procedencia del extracto, ausencia de escrituras, registro de ambos tipos y navegación por teclado; añaden búsqueda, recorrido, ampliación, selector, comparación y medición de la reducción. El consumidor activo de CI conserva su interfaz de ocho controles y cuatro capturas.

Las fuentes originales pendientes se fijan en `E:/MetodoBaseWorkspace/evidence/landing-interactive-root-20261101-20261102T0345/task-boundary.json`. Referencia y capturas: `E:/MetodoBaseWorkspace/evidence/landing-interactive-reference-20261101-20261102T0330/`. QA independiente: `E:/MetodoBaseWorkspace/evidence/landing-interactive-qa-20261101-20261102T0340/`. Los recibos nuevos distinguirán verificación local, commit/push y despliegue público.

QA final: 24 HTTP, 23 recorridos Chromium y 17 capturas, con 13 hashes estables, navegador cerrado y sin errores JS/CSP, solicitudes externas/inesperadas, desbordamiento o violaciones axe en los estados escaneados. Los rechazos V1/V2 por contraste de textos del plan y de rutinas se conservan. El autor revisó además 56 estados y los colores computados del gradiente; son conjuntos solapados, no cobertura acumulable. El consumidor activo de CI pasó sus ocho controles y cuatro capturas por HTTP local real, con cierre normal del servidor propio.

Limitación de evidencia documentada: un nombre de agregado auxiliar Root V1 se reutilizó al ejecutar V2. Los reportes RAW por ejecución, capturas, stdout/stderr y logs de ambos servidores se conservan separados; los bytes exactos del primer agregado auxiliar no están disponibles. No se reconstruye como si fuera el original. Véase `ci-aggregate-collision-disclosure.json` en la evidencia Root. La ejecución final V3 utiliza un directorio completamente nuevo, conserva su propio agregado y es la evidencia de aceptación.

El CI general conserva el límite previo documentado en `landing-release-independent-20261101-20261102T0250/ci-limitation-summary.json`: la comprobación de identidad de Dockerfile ya falla en la base. No se alteran sus pins, aprobaciones o workflow y no se declara CI global verde por las pruebas acotadas de esta tarea.

La recuperación consiste en revertir expresamente el nuevo commit de esta portada o volver al despliegue previo `288f699e-8f6a-4a9c-84ba-8d1706c4b4fb`; no se deben restaurar o borrar los cambios locales del worktree de ejecución. No se añaden migraciones o dependencias.

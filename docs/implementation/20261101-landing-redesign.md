# Landing principal: demostración y registro — 1 de noviembre de 2026

## Alcance y continuidad

Rediseño solicitado de la portada del servicio web, con referencias de Gymdesk, Mindbody y la captura adjunta del usuario. Se trabaja en `F:/MetodoBaseWeb-execution-20261018`, sobre la base Git `18d855ff` y el candidato local anterior ya revisado. Se conservan sus cambios pendientes y recibos; no se sustituye el worktree por HEAD.

La frontera de este cambio es la plantilla pública, sus estilos y JavaScript, más el hash de versión del recurso en `web/routes/pages.py`. El catálogo comercial, las rutas de identidad y la contratación conservan su autoridad del servidor. No hay migraciones o dependencias nuevas.

Evidencia de esta tarea: `E:/MetodoBaseWorkspace/evidence/landing-redesign-20261101-1793583422952/`. La preimagen de la portada y sus contratos está en `E:/MetodoBaseWorkspace/evidence/landing-redesign-qa-20261101-7f89c2d0/baseline.json`. La continuidad del lote previo queda registrada en `task-boundary.json`.

## Diseño y recorrido

La portada explica primero el trabajo central —clientes, perfiles, planes nutricionales, historial y PDF— y después el espacio personal, las rutinas complementarias y las suscripciones. La navegación enlaza funciones, demostración, suscripciones y preguntas. Se mantiene el logo y la identidad clara/verde de Método Base.

La demostración utiliza HTML/CSS y cuatro vistas: Clientes, Plan, Historial y Rutinas. Son datos ficticios identificados; el desayuno conserva el extracto existente de una generación de prueba. Cambiar de vista no llama APIs privadas, crea cuentas, genera planes, consume cuota o descarga documentos inexistentes. La propuesta de rutinas se describe como temporal e imprimible; el historial mostrado corresponde a planes nutricionales.

La invitación de registro es una tarjeta compacta, sin overlay ni bloqueo del desplazamiento. Aparece al entrar sin mover el foco, permite elegir negocio o personal y continúa a la ruta de registro de esa modalidad. Se puede cerrar y reabrir desde una pestaña. SessionStorage conserva sólo la preferencia de cierre de esa sesión; sus fallos no deben impedir el uso. Los enlaces principales de registro y acceso funcionan también sin JavaScript.

Las tarjetas comerciales continúan leyendo precio, moneda, periodo y todos los límites desde el catálogo vigente. La elección de una suscripción pagada conserva `subscription_plan` al pasar a registro. Registrarse no activa un pago; el ejemplo de la portada no acredita una compra o verificación de correo. Las preguntas explican la diferencia entre plan nutricional, suscripción, bienvenida y OTP.

## Referencias y decisiones

Consulta: **2026-11-01**, America/Mexico_City. Son referencias de experiencia de sus sitios oficiales, sin integrar sus APIs, copiar identidad, cifras comerciales o condiciones.

| Fuente | Criterio aplicado |
| --- | --- |
| [Gymdesk](https://gymdesk.com/) | Beneficio comprensible al inicio, producto visible y acción de demostración próxima al registro. No se adopta su prueba de 30 días ni promesas de soporte. |
| [Mindbody](https://www.mindbodyonline.com/) | Funciones presentadas por uso y separación entre audiencia de negocio y personal. No se importan reservas, asistencia, cobros a socios o resultados de ventas ajenos al servicio. |
| Captura adjunta del usuario, ABC Evo | Navegación clara y composición de presentación junto a una vista del producto; adaptación a la marca y funciones reales de Método Base. |

El catálogo efectivo manda sobre cifras de documentos o capturas históricas. Por ejemplo, Starter personal mantiene el cupo vigente del servidor, no el de una fixture anterior. Los topes cero se explican por dimensión del catálogo, sin prometer capacidad técnica ilimitada.

## Implementación y revisión

Responsables acordados antes de editar:

- `landing_design`: plantilla, CSS y JavaScript de la portada.
- `landing_qa`: contratos HTTP y pruebas Chromium independientes, incluyendo la adaptación del contrato comercial vigente.
- `landing_product`: referencias, exactitud comercial y revisión independiente del contenido.
- Root: versión del recurso JavaScript, adaptación del consumidor vigente de CI, revisión de integración y continuidad documental.

El script es externo, con nonce de la respuesta y versión derivada de sus bytes. No se añaden scripts de terceros o analítica. Los tabs conservan roles, selección y control por teclado; el panel de registro no reemplaza la autenticación ni recoge contraseñas en la portada.

La adaptación de `test_landing_commercial.py` conserva los controles de precios/límites dinámicos, procedencia del ejemplo, ausencia de escrituras y rutas retiradas. Actualiza las expectativas de navegación y de JavaScript a lo solicitado, en lugar de conservar una prohibición anterior de cualquier script. Los recibos y snapshots históricos conservan sus bytes. El driver vigente `tests/e2e/landing.cjs`, invocado por CI, se adapta a la nueva portada conservando su interfaz de ocho controles y cuatro capturas; su preimagen se guarda en la evidencia Root. No se modifica el workflow.

## Verificación del corte

QA independiente: **24 pruebas HTTP PASS** en ambas factories (12 contratos nuevos y 12 comerciales adaptados), sin fallos, errores o skips. Se verifican catálogo dinámico, enlaces, recursos con versión/nonce, procedencia del ejemplo y ausencia de escrituras al consultar la portada. Las nuevas fuentes Python pasan Ruff; Node verifica la sintaxis de los dos drivers y del script de producto.

Chromium independiente: **17 recorridos PASS y 16 capturas** a 320, 390, 768 y 1440 píxeles. Incluyen primera visita, cambio de modalidad, continuidad de las cuatro suscripciones pagadas, demo con teclado, cierre y reapertura por sesión, foco temprano en la pestaña, almacenamiento denegado y navegación sin JavaScript. Las respuestas HTML/CSP proceden de la factory real, servidas al navegador por un harness sin servidor persistente. No hubo errores JS, violaciones CSP, desbordamientos o hallazgos axe A/AA en los estados comprobados de la landing completa y la invitación. Se probaron también ventanas de 320×240 y 390×300. Recibo: `E:/MetodoBaseWorkspace/evidence/landing-redesign-qa-20261101-7f89c2d0/qa-summary.json`; capturas en `browser-final-v2/`. Root inspeccionó tres capturas finales, además de las previsualizaciones del autor.

La revisión detectó y corrigió dos defectos de producto antes de aceptar: contraste insuficiente en dos elementos decorativos del ejemplo y el cierre del registro fuera de una ventana muy baja. El panel ahora tiene altura máxima y desplazamiento interno. También se conserva el intento inicial fallido por una precondición del harness de Escape. Los recibos rechazados siguen disponibles y no se reatribuyen al candidato.

Root ejecutó además el consumidor activo de CI mediante **HTTP real de loopback** sobre SQLite propia y proveedores bloqueados: **8 controles PASS, 4 capturas**, fuentes estables y cierre normal del servidor. El primer intento rechazó seis solicitudes de refresh anónimo que la pantalla de registro ya hacía; el sucesor clasifica únicamente los POST `/api/auth/refresh` originados en esa pantalla y exige que todos respondan 401. Mantiene el rechazo de cualquier otra mutación y de envíos de registro o pago. No se modificó la aplicación para hacer pasar ese control. Recibo: `ci-real-http-summary-v2.json` y `ci-real-http-v2/report.json` dentro de la evidencia Root. No acredita un runner Linux o la ejecución completa de Actions.

Las 20 regresiones Node de continuidad de selección también pasan. Los conjuntos se solapan; no se suman como cobertura global. La revisión comercial independiente confirma las seis tarjetas contra el catálogo y la ausencia de promesas ajenas al servicio: `E:/MetodoBaseWorkspace/evidence/landing-product-20261101-1793583393589/review-final.json`.

Los hashes, diferencias respecto al candidato anterior, recibos y capturas se enlazan en `candidate-manifest.json` y `final-summary.json` de la evidencia Root. Esta validación identifica las fuentes locales; no se infiere publicación del código ni recepción de correo o checkout real.

El resultado local no equivale a despliegue. Este cambio no envía correos, abre checkout ni crea cuentas reales; la recepción de Outlook y los pendientes del lote previo conservan sus evidencias propias.


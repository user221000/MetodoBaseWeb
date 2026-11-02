# Landing: contraste, separación y mensaje — 1 de noviembre de 2026

## Encargo y continuidad

El usuario pide corregir la apariencia demasiado blanca, separar visualmente las secciones y sustituir el mensaje genérico «Tu plan empieza con una buena base» por textos más comerciales. Su captura corresponde a la portada publicada anterior. Este ajuste continúa sobre la nueva landing local con demostración y pestaña de registro, descrita en [el corte anterior](20261101-landing-redesign.md), sin sustituirla por esa captura histórica.

El trabajo se limita a la presentación pública del servicio web. La plantilla conserva las cuatro vistas de demostración, sus identificadores y controles, la invitación compacta de registro y sus destinos. Los precios, periodos, monedas y cupos siguen procediendo del catálogo del servidor. Se mantienen la elección de suscripción durante el registro y la distinción entre un plan nutricional y una suscripción comercial.

## Mensaje elegido

**Planes nutricionales claros. Clientes bien acompañados.**

Es redacción propia: identifica el resultado principal y conecta su organización con el trabajo de quien atiende clientes. La frase se refiere a la presentación y consulta de perfiles, planes e historial; no promete un resultado de salud ni una supervisión automatizada. El subtítulo explica la función concreta: «Organiza perfiles, genera planes nutricionales y consulta el historial y PDF de cada cliente desde el navegador».

La categoría aparece antes del titular: «Gestión de clientes y planes nutricionales». Las acciones principales siguen siendo crear una cuenta gratuita y ver la demostración. El acceso al espacio personal permanece visible y se desarrolla después como una modalidad distinta.

Los títulos posteriores siguen el recorrido real: cada cliente con su perfil, generación a partir de ese perfil e historial del resultado. Se evita presentar las rutinas temporales como historial persistente. La sección de inicio explica cuenta, perfil y generación; la de preguntas diferencia alta, bienvenida, códigos de acceso y contratación. Las suscripciones y sus notas conservan su contenido comercial exacto.

## Referencias consultadas

Consulta de las páginas oficiales: **2026-11-01**, America/Mexico_City. Se usan como referencia editorial y de jerarquía, sin copiar sus lemas, cifras, condiciones o funciones.

| Fuente | Observación e interpretación aplicada a Método Base |
| --- | --- |
| [Gymdesk](https://gymdesk.com/) | Presenta la categoría del producto y un beneficio comprensible cerca de una acción clara. Se aplica esa claridad al trabajo con clientes y planes. No se trasladan sus condiciones de prueba, cancelación o ahorro de tiempo. |
| [Mindbody](https://www.mindbodyonline.com/) | Relaciona las funciones con el trabajo del negocio y ofrece una vía distinta a quienes buscan el servicio personal. Se adapta esa separación al negocio y al perfil personal existentes. No se trasladan sus reservas, calendario ni cifras de ingresos. |
| [NutriAdmin](https://nutriadmin.com/) | Nombra desde el inicio el ámbito nutricional y conecta gestión de clientes con planes. Se aplica esa concreción al subtítulo y al orden de secciones. No se trasladan rapidez de generación, recetas, inteligencia artificial, resultados clínicos o cobros a clientes. |

La aplicación de estos criterios es una decisión de diseño del equipo, no una conclusión cuantitativa de las fuentes. No se afirma haber medido conversión, ahorro, retención, ventas o mejora de salud. Nutrium no se incorpora como referencia verificada: la URL consultada en el trabajo previo no estuvo disponible.

## Separación visual acordada

Se conservan los anchos internos `.wrap` y se añaden bandas de fondo que ocupan todo el ancho de la ventana. La jerarquía se apoya en fondos, límites, espaciado y tarjetas, además de los títulos.

| Bloque | Contenedor acordado | Intención visual |
| --- | --- | --- |
| Presentación y demo | `.hero-band` alrededor de `.wrap.hero` | Verde profundo con texto claro; demostración blanca destacada. |
| Resumen de funciones | `.capabilities-band` alrededor del `.wrap` existente | Franja verde diferenciada que cierra la presentación. |
| Funciones | `.section-band.functions-band` | Fondo claro, tarjetas delimitadas y lectura por pasos. |
| Negocio y personal | `.audience-section.section-band.audience-band` | Verde suave y dos opciones reconocibles. |
| Cómo comenzar | `.section-band.workflow-band` | Banda oscura que marca una pausa en el recorrido. |
| Catálogo de suscripciones | `.section-band.pricing-band` alrededor de `.wrap.pricing-wrap` | Superficie neutra con tarjetas y cuotas legibles. |
| Preguntas | `.section-band.faq-band` | Fondo claro separado del catálogo. |

La cabecera conserva la marca verde y sus accesos; el cambio de color no requiere imágenes, scripts de terceros ni dependencias nuevas. La altura del titular y los espacios en móvil deben permitir alcanzar el registro en el primer tramo de la página. La preferencia de movimiento reducido, el foco visible y el contraste se revisan con la interacción real.

## Responsabilidades y evidencia

- `landing_copy`: plantilla y este documento; preimagen y recibo en `E:/MetodoBaseWorkspace/evidence/landing-contrast-copy-20261101-fc28d479/`.
- `landing_contrast_design`: estilos de la portada, con los contenedores acordados antes de editar.
- `landing_contrast_qa`: revisión independiente de contratos, interacción, contraste y composición en escritorio y móvil.
- Root: integración, consumidor vigente de CI, continuidad del lote y cierre de evidencia.

La verificación de presentación e interacción se ejecuta contra el candidato final estable. Las comprobaciones estáticas del autor comparan identificadores, atributos de interacción, expresiones Jinja, enlaces y contenido comercial con la preimagen. Los resultados de navegador y contratos se registran en el cierre de Root; este texto no acredita por sí solo un despliegue.

Este ajuste no publica el servicio ni realiza altas, envíos de correo o compras reales. La observación anterior de Outlook en Spam conserva su evidencia separada.


## Cierre de validación local

Fuentes finales de aplicación: HTML 33d8b62c9e428b1f171d6e772899d984c0e1959697f941617e06a3f6a4b21a35 y CSS 40c70a82c89b33b2cc1260ca7244a693511e8f529a2196d3a927b06bab727bba. El ajuste sólo cambia estos dos archivos de presentación; JavaScript, catálogo, registro, APIs y controles de seguridad conservan sus bytes del candidato previo.

QA independiente aprobó **24 pruebas HTTP** en ambas factories y **17 recorridos Chromium**. Las capturas cubren 320, 390, 768 y 1440 px, más ventanas horizontales de 320×240 y 390×300. No hubo errores JavaScript, CSP, desbordamientos o hallazgos axe A/AA en los estados comprobados. El suplemento verifica siete bandas a ancho completo y seis superficies distintas; el contraste mínimo del hero es 5.10:1 en el extremo claro del gradiente. También comprueba la invitación automática abierta, su cierre por sesión, el foco y la reapertura en una sesión nueva.

Recibo de QA: E:/MetodoBaseWorkspace/evidence/landing-contrast-qa-20261101-4bb3282d/qa-summary.json. Las 12 capturas principales están en browser-final-v1/; el suplemento tiene sus propias capturas solapadas. No se suman recorridos o imágenes como cobertura global. Root inspeccionó la landing completa de 1440 px y la primera visita móvil de 390 px, además de las previsualizaciones del autor.

Se conserva un rechazo inicial del instrumento que no componía correctamente el fondo semitransparente del chip sobre el gradiente. El instrumento V2 hace esa composición y pasó; no se cambió la aplicación ni se relajaron pruebas para aceptarlo.

Root repitió el consumidor vigente de CI sobre **HTTP real local** con SQLite propia y proveedores bloqueados: ocho controles y cuatro capturas PASS, fuentes estables y cierre normal del servidor. No se modifica el workflow ni el driver de CI en este ajuste. Esta prueba no acredita ejecución global de Actions, Linux o integración productiva.

Evidencia Root: E:/MetodoBaseWorkspace/evidence/landing-contrast-20261101-1793585562406/, incluidos ci-real-http-summary-v2.json, candidate-manifest.json y final-summary.json. La preimagen y los recibos anteriores permanecen intactos. No hubo cuentas, correos, cobros, DDL, configuración productiva, push o despliegue. La publicación del sitio principal conserva su paso operativo propio; el estado del candidato es preparado y probado localmente.

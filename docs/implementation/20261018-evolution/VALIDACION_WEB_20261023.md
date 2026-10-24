# Validación de la candidata web: 23 de octubre de 2026

El trabajo vigente abarca exclusivamente el servicio web. Desktop queda fuera
de desarrollo, pruebas y empaquetado por la instrucción más reciente del usuario;
sus archivos y evidencias históricos se conservan. Las fuentes nuevas, temporales
y evidencias de esta reanudación permanecen en E o F.

La candidata se encuentra en `F:/MetodoBaseWeb-privacy39-20261023`. La base Git
es `878082b242cdfa23e1e4c134f675c12b535a2cd7`; las modificaciones posteriores
se identifican por sus archivos físicos. El corte de 1554 archivos tiene huella
`0e767c82fce03cb1b6c1d6da153a9f8d8c7e1ee425a357c36ccf87443f447041`.
Este corte todavía no está integrado ni desplegado desde el repositorio principal
de ejecución `F:/MetodoBaseWeb-execution-20261018`.

La composición posterior incorpora el comparador de esquema v2, la corrección
del orden de carga de MFA antes de preparar la política de supresión y el campo
obligatorio del factor sintético de las cuatro nuevas regresiones. Tiene1557
archivos y huella
`9b3160df3820c8fd75137b8c5edfe7ccfec5cf2100a6f14fd68005ce57e6a328`.
Sus61 casos funcionales SQLite están aprobados, con los57 anteriores conservados.

Se mantienen las decisiones comerciales: Free permite diez clientes, un plan
por cliente y día, diez planes totales diarios y veinte mensuales. El rediseño
conserva los colores de la landing y el panel de rutinas Push/Pull/Legs ya
implementado. México es el mercado inicial confirmado.

## Cambios de esta reanudación

Se incorporaron los targets de esquema39 obtenidos mediante capturas reales de
SQLite y PostgreSQL. Sus SHA256 son, respectivamente,
`32eedcd44735d0c76af71992c6002ca0eb19b5fc43efcb3a4d005cff0d50cd29` y
`0e939c118403e430856c08fa8455ea86dbd25c9cd7e95ab00f5b87562669b122`.
El testigo PostgreSQL observó 44 tablas ORM, 45 físicas, 35 con FORCE RLS y
el rol de aplicación restringido. La base temporal cerró sin sesiones y su
ausencia se verificó desde una conexión nueva.

La interfaz de privacidad permite registrar y consultar solicitudes, descargar
páginas de hechos personales y preparar el cierre con identidad y factor actual.
La vista dedicada en las rutas existentes evita dos inicializaciones de Google.
El recibo mínimo sobrevive al retiro de la sesión y se oculta ante otra cuenta.

La admisión HTTP reconoce ahora exactamente las nuevas rutas de privacidad,
manteniendo las comprobaciones de origen, marcador, tipo de contenido y bearer.
Los errores reciben las cabeceras privadas existentes. La cookie de renovación
se retira cuando el servidor confirma el cierre y la revocación; una solicitud
bloqueada conserva la sesión. Estos cambios recibieron revisión independiente
de seguridad antes de la validación funcional de la nueva candidata.

Se transfirieron también las correcciones revisadas de CI, contratos HTTP,
control PostgreSQL y fixtures históricos de la tanda38. La transferencia no
reescribe privacidad ni los targets39. Los cambios posteriores de diagnóstico
de restauración permanecen separados.

## Resultados conservados

| Comprobación | Resultado y límite |
|---|---|
| Analítica y procedencia38, SQLite/HTTP | 108 casos aprobados, sin fallos, errores ni omisiones; fuente1522 `1be7e15a…`. El primer resultado102/108 se conserva. |
| Recolector CI33 | Tres casos aprobados con sus aserciones originales. |
| Interfaz de privacidad39 sin navegador | 15 casos del controlador, 19 del transporte API y 14 con elementos DOM simulados: todos aprobados sobre fuente1550 `9dca7b36…`. No equivalen a navegador ni proveedor real. |
| Primera tanda funcional39 | 52 casos exactos: 38 aprobados y 14 fallidos. Se conservan el resultado y las causas; no se reetiqueta como aprobada. |
| Tanda funcional39 corregida | 57 casos exactos: 56 aprobados y un fallo, sin errores ni omisiones, sobre fuente1554 `0e767c82…`. El caso restante expone un autoflush prematuro durante la supresión posterior a restauración; la guarda CAS lo rechaza. Se prepara la corrección sin relajar esa guarda. |
| Ocho vistas HTTP39 | Ocho casos exactos aprobados, sin fallos, errores ni omisiones, sobre la misma fuente1554. La primera ejecución fallida por la fixture se conserva. Son vistas HTTP, sin acreditar interacción en navegador. |
| Comparador de esquema v2 | 56 casos puros exactos aprobados, sin fallos, errores ni omisiones. Incluyen las dos parejas reales de CHECK y negativos estructurales y léxicos. No equivalen a una restauración PostgreSQL. |
| Primera tanda61 | Los57 anteriores pasan; cuatro casos nuevos fallan antes de ejecutar el producto por un factor sintético sin `factor_id` obligatorio. La corrección se limita a esa fixture y conserva las aserciones. |
| Tanda61 final | 61 casos exactos aprobados, sin fallos, errores ni omisiones, sobre fuente1557 `9b3160df…`. Incluyen restauración cifrada real de SQLite, política explícita, supresión propia, guardado, rollback, revocación y centinelas de otra cuenta. No acreditan PostgreSQL ni custodia externa. |
| Restauración PostgreSQL38 | Pendiente. La estructura pasa; el diagnóstico real encuentra una diferencia de representación de casts de array en la misma política `r38_read`, tanto en la firma de tenant como en la de analítica. El resto de ambas firmas permanece literal, incluidos roles, ACL, funciones, triggers y FORCE RLS. Las dos bases temporales cierran normalmente, sin sesiones y con ausencia verificada. El comparador limitado a esas formas supera138 casos puros exactos, sin fallos, errores ni omisiones, incluidos56 anteriores y82 de políticas. Se incorporó a las candidatas38/39; todavía no acredita la restauración real. Los fallos y los targets originales se conservan. |
| Regresión ampliada de seguridad | El resultado516 se conserva como fallido: 284 aprobados, 224 fallidos y ocho errores. Su selección y árbol incompleto no corresponden a la campaña vigente; se prepara un replay completo con las recetas originales, sin excluir criterios. |
| Regresiones afectadas en replay completo | 515 casos exactos aprobados, sin fallos, errores ni omisiones. Corte histórico38 con 1709 fuentes `6903b23a…` y 549 documentos, 2258 archivos completos; no se atribuye a la candidata39. |
| Primera fase histórica R05 | 60 casos reales: tres aprobados y 57 fallidos. El lanzador mantenía en memoria el cargador actual después de materializar la versión congelada. La corrección revisada limpia únicamente los paquetes `scripts` y `tests` antes de la colección; conserva las cápsulas, aserciones y goldens. Las fases de 48 y 15 casos aún no se ejecutaron. |
| Fases históricas R05 corregidas | Tres fases exactas aprobadas:60+48+15=123 casos, sin fallos, errores ni omisiones. Corte histórico38 `c98155a2…` en un replay nuevo de2258 archivos; cápsulas originales estables y cero intentos de procesos o red. El fallo anterior se conserva. No se atribuyen estos123 casos al runtime actual. |
| Restauración PostgreSQL38 con el comparador revisado | El caso original pasa sobre 528 fuentes `2089c1d8…`. Las dos bases temporales cierran, con ausencia comprobada después del proceso; fuentes, roles y 92 paquetes permanecen estables y `pip check` pasa antes y después. El resultado local no acredita custodia externa ni la restauración de privacidad39. |

Las capturas y las tandas web39 verificadas conservaron las fuentes y los92
paquetes, con `pip check` correcto antes y después. Los logs se leyeron y
archivaron tras el cierre de los procesos. Estas evidencias no acreditan
despliegue, pruebas Desktop, entrega de correo, cobros reales o cumplimiento legal.

Los recibos originales y sus hashes se localizan desde
`E:/MetodoBaseWorkspace/migration-20261022/root-continuity-20261023-v46/continuity.json`.
El recibo de aceptación de los48 casos de interfaz es
`E:/MetodoBaseWorkspace/evidence/root-privacy39-node48-acceptance-30269999b4734567b1d4b090c7f9961e/review.private.json`.
La revisión de los57 casos y las ocho vistas, con lectura completa de sus
archivos y comprobación de identidades, se conserva en
`E:/MetodoBaseWorkspace/evidence/root-privacy39-57-and-shell8-review-20261023-v1/review.private.json`
(SHA256 `b01566eeac39b0f2d30125bfc4cacef85c9aacdcbc20aec59396fda5a072e775`).
La composición1557 se conserva en
`E:/MetodoBaseWorkspace/evidence/root-privacy39-v12-v13-application-20261023-v1/application.private.json`
(SHA256 `30532659c0ef70b1b5470a64a3ed7ceb87ced2af4e2a19408270fc90544ca927`).
La continuidad posterior está en
`E:/MetodoBaseWorkspace/migration-20261022/root-continuity-20261023-v47/continuity.json`.
La tanda61 final está en
`E:/MetodoBaseWorkspace/evidence/root-privacy39-web-2da049d46a104357b6e8c1c0f6fe746f/public/summary.json`
(SHA256 `4f5e0eb1d4fe91815b2c668da3e902a0b1ebadf3546a6c4040bada1845bd3951`).
QA verificó de forma independiente sus61 identidades, los36 miembros del
archivo de originales, las fuentes y los92 paquetes estables, con `pip check`
correcto antes y después.

## Trabajo pendiente

1. Mantener la aceptación local de SQLite61 y validar el mismo contrato de
   privacidad sobre PostgreSQL restringido; los resultados originales se conservan.
2. Conservar la restauración PostgreSQL38 aprobada con el comparador revisado
   y sus 138 casos puros, sin relajar autorización, roles, RLS ni cambios
   estructurales reales. Los targets y el formato histórico no se reescriben.
3. Completar las fases funcionales y de restauración PostgreSQL39 con rol
   restringido, aislamiento A/B y cierres naturales verificados.
4. Completar la campaña general de la candidata final. Los515 casos afectados
   y las tres fases históricas123 aprobadas se conservan con su atribución
   a los cortes históricos38 correspondientes.
5. Integrar commits locales revisados, preservar los615 archivos históricos del
   repositorio de ejecución y actualizar de forma conjunta la trazabilidad JSON
   y su vista legible. El registro de167 filas ya se materializó en la candidata39
   junto con31 documentos y evidencias finitas. SEC26 sigue en revisión, sin
   alterar los166 criterios existentes ni los92 identificadores iniciales.
6. Completar las validaciones pendientes de Linux, imagen/SBOM/SCA, Redis,
   arranque, navegador y carga representativa R34 sobre el commit final.

R22, R30, R31 y R34 conservan su alcance obligatorio. Sólo R28 y R35 tienen los
criterios condicionales definidos por el prompt original.

Las decisiones comerciales y jurídicas aún sin respuesta, la custodia externa
de respaldos, las verificaciones de proveedores, el piloto y la revisión
profesional mantienen su estado abierto. No se inventan políticas de retención,
entrevistas, entregas o resultados productivos. La publicación y las mutaciones
de producción requieren su autorización correspondiente y no se ejecutaron.

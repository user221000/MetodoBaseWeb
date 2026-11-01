# Biblioteca y generador Push / Pull / Legs

El panel tenía trece ejercicios y una guía idéntica para todos. Se amplía a 91 variantes de gimnasio: 30 Push, 30 Pull y 31 Legs. Cada registro identifica movimiento, equipo, patrón, músculos, experiencia mínima, unidad, técnica y alternativa. Las variantes comparten una familia cuando corresponde; la referencia de una familia no certifica cada variante ni una rutina individual.

La propuesta contiene tres sesiones de seis, siete u ocho ejercicios cada una. Sus requisitos son actividad habitual, experiencia, objetivo de fuerza general o hipertrofia, equipo disponible, días semanales, tiempo disponible, variante y exclusiones. «Normal» es un alias explícito de «moderada»; se conserva «nula» para perfiles existentes. La actividad habitual no se convierte en experiencia, kilos de carga ni aumento automático de series. Inicial usa una serie; intermedio y avanzado usan dos. La elección de más días repite la división sin multiplicar la dosis de una sesión.

La selección preserva patrones básicos por grupo, limita repeticiones de un patrón y excluye ejercicios no compatibles con equipo o experiencia. Los IDs de una sesión son distintos. Las alternativas respetan equipo, experiencia y exclusiones; no proponen otro ejercicio ya presente ni cambian silenciosamente bilateral/unilateral o segundos/repeticiones. Las exclusiones pueden afectar a máquinas concretas: marcar «máquinas» sólo declara una categoría, no que todo aparato exista en ese gimnasio.

Las variantes 0–9 son deterministas. La biblioteca permite buscar, filtrar por grupo y excluir movimientos. La duración es una estimación editorial visible: calentamiento, preparación, trabajo y pausas entre series; no es tiempo medido. Si falta equipo, movimientos válidos o tiempo, se devuelve un error claro sin fabricar una rutina de menos de seis ejercicios.

Se conserva el calendario de tres a seis días, incluidos consecutivos, con PPL continuo entre semanas. Editar requisitos o cambiar de cliente oculta el resultado anterior e impide imprimirlo como vigente hasta regenerar. La propuesta puede imprimirse; requisitos y selección viven en la página y no se presentan como historial guardado.

## API y procedencia del perfil

Las rutas de rutinas comparten la revalidación persistida del actor y su gimnasio padre, con los mismos límites de espacio y sesión. El catálogo inicial sigue en `GET /api/rutinas/catalogo`. Se añaden:

- `GET /api/rutinas/ejercicios`: biblioteca genérica autenticada.
- `POST /api/rutinas/generar`: vista derivada de requisitos explícitos, con cuerpo acotado a 16 KiB y esquema que rechaza identidad, roles, campos extra y números coaccionados.
- `GET /api/rutinas/clientes`: búsqueda paginada de IDs y nombres de clientes activos del gimnasio autorizado; no teléfonos, correo o perfil corporal.
- `GET /api/rutinas/requisitos`: importa sólo la actividad del cliente autorizado o del perfil propio. Un cliente ajeno, inactivo o borrado no se distingue de uno ausente. No crea perfiles ni adopta clientes del gimnasio como perfil personal; un perfil propio ambiguo tampoco se usa.

La importación se solicita mediante una acción explícita. El cuerpo de generación no contiene nombre ni ID de cliente; sólo opciones de entrenamiento. No se crean tablas ni objetos `PlanGenerado`, no se consumen cuotas nutricionales y no se consultan proveedores externos. VIEWER puede consultar esta previsualización derivada sin adquirir permisos de edición de clientes o planes guardados. Las lecturas cierran su sesión antes de publicar una respuesta; errores inesperados son opacos.

## Fuentes y verificación

Principios generales en [ACSM 2026](https://acsm.org/resistance-training-guidelines-update-2026/), [NSCA](https://www.nsca.com/education/articles/kinetic-select/determination-of-resistance-training-frequency/) y [CDC](https://www.cdc.gov/physical-activity-basics/guidelines/adults.html), técnicas y familias en [NASM](https://www.nasm.org/resource-center/exercise-library). La cantidad de seis a ocho ejercicios es una opción del producto solicitada por el usuario, no un mínimo universal atribuido a estas guías. Tres días PPL no garantizan por sí solos trabajar cada grupo dos veces por semana.

Evidencia: `E:/MetodoBaseWorkspace/evidence/routines-generator-20261031-1ec535ec5e4e4b6a8139dfbffc3c7ab5/`. Gate integrado: 152 PASS, sin fallos, errores u omisiones, con fuente estable. Incluye los 71 casos de catálogo/motor del autor y las regresiones de esquema de entrada, sesión y permisos; no se suman dos veces. Los cinco módulos Node de control, DOM y transporte también pasan. Se amplió el puerto DOM de una prueba histórica para soportar los nuevos controles de equipo; el primer rechazo se conserva, sin eliminar aserciones de seguridad.

Revisión independiente: 190 casos del motor, 48 HTTP en ambas factories con SQLite propia y retorno Python real 0, 104 Node y 67 Chrome PASS. Se comprueban ambas vistas a 320, 390 y 1365 px, ausencia de desbordes y errores de página, filtros, importación mínima, límites, variantes, estados obsoletos, sesiones tardías, impresión y temporizador. Las 451 fuentes de aplicación permanecieron estables. El navegador usa transporte aislado con motor real; las pruebas HTTP usan cuentas sintéticas. No se atribuyen resultados a Google real, PostgreSQL, proveedores o idoneidad individual. Se conservan los rechazos iniciales del harness y las advertencias de proceso, separados de los recibos finales.

Una segunda lectura semántica de los 91 registros no encontró bloqueantes de patrón, equipo o unidades; sus dos recomendaciones menores de redacción quedan registradas en `frontend/catalog-peer-review.json`. El recibo de publicación y las verificaciones del dominio y del motor desplegado se guardan junto a la evidencia después de completar el despliegue.

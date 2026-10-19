# Auditoría integral de MetodoBase

MetodoBase está operativo y tiene una base visual y nutricional aprovechable. La prioridad es estabilizar cobros, autorización, datos y recorridos entre gimnasio y socio antes de ampliar ventas. Los problemas más relevantes no se resuelven con un rediseño general: hay derechos Pro concedidos sin pago, un esquema incompatible con el Pro individual, permisos eludidos y una configuración PostgreSQL sin la defensa RLS que describe parte de la documentación.

Para hacerlo más atractivo, el siguiente ciclo debe permitir que el dueño incorpore y atienda al socio y que éste vea su plan y conserve seguimiento real desde móvil. Hoy el portal individual y la cartera del gimnasio están desconectados, y parte del seguimiento sólo existe en localStorage.

Fecha: **18 de octubre de 2026**, America/Mexico_City. Revisión coordinada con tres agentes especializados en backend/seguridad, QA/pruebas y UX/UI/producto, más revisión integradora de arquitectura, documentación y Railway.

## Identidad de la versión revisada

- Repositorio: [user221000/MetodoBaseWeb](https://github.com/user221000/MetodoBaseWeb).
- GitHub `main` y despliegue de Railway: `daa25efbf51d154710bad625025b345fa9ec9252`.
- La copia local no contiene `.git`. Una copia temporal del repositorio permitió comparar **246 archivos de aplicación, pruebas, configuración y despliegue**, normalizando únicamente CRLF/LF: **cero diferencias** en ese conjunto.
- Railway: proyecto `joyful-quietude`, entorno `production`, servicio `MetodoBaseWeb`, URL https://metodobase.up.railway.app.
- Despliegue inspeccionado: estado `SUCCESS`, creado el 13 de agosto de 2026; el commit fuente es de abril. No confundir fecha de commit con fecha del último despliegue.

Ver [comparación del repositorio](evidence/repository-comparison.json) y [estado Railway saneado](evidence/railway-summary.json). El conector de GitHub solicitó reautenticación; la lectura pública y el clon Git permitieron revisar la fuente sin esa conexión. No se verificaron desde ese conector reglas de protección de rama ni resultados recientes de Actions.

## Lo que se comprobó

| Frente | Profundidad y evidencia |
|---|---|
| Backend y seguridad | Modelos, rutas, servicios, auth, permisos, cuotas, pagos, sesiones, tenant, documentos, jobs, configuración y dependencias; diez escenarios reproducidos localmente y un probe aislado del filtro alimentario |
| QA | Suite de 1177 casos, dos preparaciones diferenciadas, cobertura de sentencias, AST de 260 archivos propios, Ruff, Bandit y probes de migración |
| Frontend | Plantillas, CSS, JavaScript y contratos; cinco capturas públicas de producción y nueve de la aplicación local real, con Playwright y axe |
| Producción Railway | Estado, topología, commit, configuración efectiva, presencia de variables, métricas, muestra de logs y HTTP público |
| PostgreSQL real | Únicamente catálogo: rol, versión, conexiones, 20 tablas, RLS, políticas, constraints de suscripciones y existencia de Alembic; transacción de sólo lectura |
| Arquitectura y documentación | Entradas web/API/desktop, compatibilidad legacy, límites entre dominio y adaptadores, fuentes de catálogo y documentación histórica |
| Desktop y herramientas | Sintaxis y pruebas que cubre la suite, análisis estático y revisión de empaquetado/estructura; no un recorrido completo de la GUI ni instaladores |

No se modificó código de producto ni configuración o registros de producción. Las pruebas con cambios de estado usaron datos sintéticos y SQLite efímero, con conexiones externas bloqueadas. El servidor local se detuvo al terminar. No se ejecutó compra real, migración de producción, carga, restore ni un ataque activo contra el servicio.

La revisión cubre todos los frentes principales del proyecto con profundidad distinta; no equivale a probar cada combinación, dispositivo, dependencia instalada o condición clínica. Los riesgos inferidos por código se distinguen de los comportamientos reproducidos. No se afirma una fuga de datos existente a partir de la ausencia de RLS.

## Resultado de pruebas

| Medición | Resultado e interpretación |
|---|---|
| Suite inicial | 1128 aprobadas, 44 fallidas, 5 omitidas; parte del fallo era preparación de entorno/fixtures |
| Suite normalizada | **1168 aprobadas, 6 fallidas, 3 omitidas**, más 7 subtests aprobados |
| Causas de las seis fallidas | Tres por catálogo Free 5 frente a 10; una por supuesto POSIX en Windows; dos por dependencia del event loop/orden de pruebas Sentry, que pasan aisladas |
| Sintaxis | **260 archivos Python propios, sin errores AST** |
| Cobertura de sentencias | **30.61% global** en las ocho carpetas medidas; web 41.12%, API alternativa 73.64% |
| Rutas SaaS críticas | Planes 17.89%, usuario 20.06%, billing 22.42%, clientes 28.41%, auth 30.39% |
| Estático | 1976 diagnósticos Ruff y seis alertas Bandit contextualizadas; no son ese número de fallos o vulnerabilidades confirmadas |
| Dependencias del lock | 37 advisories distintos en siete paquetes; **corresponden al lock histórico, no al inventario instalado en producción** |

La cobertura excluye dependencias y no mide ramas. Algunas importaciones ocurrieron antes del inicio de la medición; el informe QA explica esa limitación. La suite usa en gran parte la aplicación `api.app`, mientras el SaaS arranca `web.main_web`. Un número grande de tests no garantiza los recorridos web que faltan. Detalle, comandos y entorno: [informe QA](qa/INFORME_QA.md).

## Problemas prioritarios consolidados

La prioridad P0 es una decisión de remediación para este producto; no equivale a CVSS. Se agrupan hallazgos de varias disciplinas para no contar el mismo fallo como tres problemas distintos. Cada informe especializado contiene líneas, escenario y aceptación detallada.

| Prioridad | Problema e impacto | Evidencia principal | Trabajo |
|---|---|---|---|
| P0 | Pro se activa sin pago o con confirmación incompleta | B01; `web/routes/usuario.py:543,619,659`; reproducción local HTTP 200 y persistencia activa | R01 |
| P0 | Reconciliación comercial incompleta: Pro individual no cabe en constraint; cancelación/impago no sincroniza ambas tablas | B02/B15; constraint real PG; reproducción local IntegrityError | R01/R09 |
| P0 | VIEWER crea clientes y la membresía se pierde al entrar/refrescar | B06/B07; `web/routes/clientes.py:72`, `web/auth.py:238,543`; HTTP 201 local | R02 |
| P0 | No hay seguimiento Alembic ni hook efectivo de migración; bootstrap puede ocultar fallos | OPS01, QA03/04; `railway.toml:10`, `entrypoint.sh:13`, `db_bootstrap.py`; catálogo real y probe local | R03 |
| P0 | App con superusuario y cero políticas RLS; sesiones no preparadas para habilitarlo con seguridad | B04/B05, OPS02; catálogo PG real, `web/database/engine.py:128`, `web/routes/planes.py:88,293` | R04 |
| P0 | CI no prepara la suite SaaS ni impide todos los fallos materiales | QA01/02/05/07; manifest resuelto y workflow, fixtures no aislados | R05/R19 |
| P0 | Se promete aplicar notas que el motor no interpreta; el filtro conserva una categoría cuando todos sus alimentos se excluyen | UX02/B09/B23; `usuario_perfil.html:102`, `web/routes/planes.py:95,166`; código y probe aislado del filtro, sin demostrar un plan clínico final | R06/R33 |
| P1 | La cuota individual no se comprueba ni consume; concurrencia no protegida entre workers | B03/B17; Starter agotado aún genera en reproducción; locks por proceso | R01/R28 |
| P1 | Access puede conservar permisos tras logout, desactivación o expulsión | B08; token sigue válido en reproducción local; remember_me de siete días | R10/R32 |
| P1 | PDFs y logos dependen del disco efímero web | B11/OPS03; rutas de escritura y ausencia real de volumen/bucket | R07 |
| P1 | Backup de SQLite no respalda PG y puede reportar éxito sin archivos | B10/OPS04; `scripts/backup_daily.py`; backups nativos aún por verificar | R08 |
| P1 | Perfil individual guarda medidas fuera de rango | B09; edad/peso negativos, altura cero y grasa 150 aceptados con HTTP 200 local | R06 |
| P1 | Cuenta individual no accede al plan de su gimnasio; no existe vínculo de socio | UX07; `web/routes/usuario.py:55`, modelo/rutas | R12 |
| P1 | Equipo sin pantalla de aceptación, URL de correo incorrecta y navegación inconsistente | UX06/B06/B19; GET 404 local y contratos de invitación | R11/R16 |
| P1 | Diario se pierde al salir y no sincroniza; claves sin usuario y fecha UTC incorrecta | UX03/04; reproducción de navegador local, `base_usuario.html:170`, `usuario_mi_plan.html:428` | R14 |
| P1 | Se muestra 100% de avance sin haber registrado consumo | UX10; captura de cuenta local nueva; `usuario_mi_plan.html:520` | R15/R24 |
| P1 | Móvil corta controles y PDF; teclado ejecuta una acción distinta | UX05/08; 582/390 px en suscripciones, 483/390 en clientes; Enter abre modal | R13 |
| P1 | Contraste, nombres y controles accesibles incompletos | UX09; axe con selectores/capturas; falta revisión manual completa de asistencia | R13 |
| P1 | Redis puede degradar permitiendo solicitudes; correo no configurado y recuperación incompleta | OPS05/06; código, log histórico y presencia de variables | R16/R17 |
| P1 | Runtime no se instala desde lock congruente ni hay staging observado | B21/OPS07; Docker/manifest, topología real | R18 |
| P2 | Catálogo comercial duplicado, defaults de membresías duplicados y estados UI engañosos | QA06, UX12/13/14/17, B18; duplicados observados, carrera inferida | R09/R15/R22/R26 |
| P2 | Marketing desconectado, registro ambiguo y activación poco medible | UX16/17; landing comercial sin ruta, checklist inferido por existencia de plan | R22/R29/R30 |
| P2 | Repositorio con entornos versionados y documentación histórica presentada como vigente | 1648 de 2091 archivos tracked son de `venv/` o `.venv-test/`; ROADMAP/checklists de marzo | R20/R21 |

El pago MercadoPago presenta dos defectos adicionales reproducidos/inspeccionados en B13/B14, pero no estaba configurado en el servicio. Se considera riesgo latente antes de habilitarlo, no un incidente actual de cobro.

## Fortalezas que conviene conservar

Ya existen generación nutricional, PDF, clientes y filtros, perfiles y exclusiones explícitas, branding, planes de membresía, dashboard con señales de seguimiento, onboarding, componentes de estados, roles, servicios de cobro, rotación de refresh e idempotencia parcial. No se recomienda rehacer estas capacidades como si faltaran por completo.

La identidad visual oscura con acentos y las páginas públicas ofrecen una base coherente. La inspección pública a 390 px no mostró desbordamiento en acceso/registro; los problemas de móvil aparecen especialmente en los recorridos autenticados. Los arreglos de reflow, jerarquía y accesibilidad pueden conservar la marca y mejorar la utilidad sin un rediseño cosmético completo.

## Dirección recomendada

| Ventana orientativa | Resultado principal | Condición para avanzar |
|---|---|---|
| Primeras 72 horas | Contener acceso Pro y permisos incorrectos; retirar promesas alimentarias no aplicadas; preparar backup/CI | Regresiones de los bypass y una copia aislada para preparar cambios |
| Días 1 a 14 | Migraciones, rol restringido, aislamiento, storage y restauración | Esquema reconciliado y probado; fallos detienen release; sin habilitar RLS a ciegas |
| Días 15 a 30 | Dueño, equipo y socio conectados; móvil funcional; seguimiento persistente | Socio ve el plan correcto y sus datos sobreviven a volver a entrar |
| Días 31 a 60 | Seguimiento profesional, cobros comprensibles, observabilidad y pruebas E2E | Un piloto usa el servicio de forma repetida y se detectan fallos operativos |
| Días 61 a 90 | Mejorar conversión y elegir diferenciadores según evidencia | Medición por cohortes y P1 cerradas antes de ampliar alcance |

El [roadmap completo](ROADMAP_PRIORIZADO.md) contiene 35 elementos con prioridad, responsable, tamaño, dependencias y aceptación, más métricas y trabajo opcional. El horizonte depende del equipo y del saneamiento del esquema; el backlog completo no se promete dentro de 90 días.

La [propuesta de arquitectura y documentación](ARQUITECTURA_Y_DOCUMENTACION.md) recomienda un monolito modular, casos de uso y unidades de trabajo, sin reescritura general. Incluye una estrategia explícita para vincular socio y gimnasio conservando la cuenta independiente. La [revisión operativa](OPERACION_Y_SEGURIDAD.md) desarrolla migraciones, privilegios, persistencia, restauración y una matriz de verificación con referencias actuales como [OWASP ASVS 5.0.0](https://owasp.org/projects/asvs) y [WCAG 2.2](https://www.w3.org/TR/WCAG22/).

## Pendientes de validación específica

- Inventario de paquetes realmente instalado en la imagen publicada, escaneo de imagen, protección de ramas y último resultado real de GitHub Actions.
- Copia staging del esquema y pruebas PostgreSQL con rol restringido, migraciones desde estados anteriores y restauración medida; no basta SQLite.
- Compra/renovación/cancelación en sandbox con firma y entrega real de webhooks, correo de prueba verificado y caída controlada de proveedores.
- Pruebas de carga con datos sintéticos, concurrencia de exclusiones/cuotas y persistencia de jobs ante reinicio.
- Política y configuración nativa de backups Railway, inventario y recuperación de archivos históricos.
- Accesibilidad con lector de pantalla y teclado en recorridos completos, otros navegadores, 320/768/1440 px y ampliación.
- Revisión profesional de restricciones nutricionales y del alcance clínico anunciado; revisión legal de privacidad y tratamiento de notas de salud.
- Entrevistas y datos de negocio: conversión, renovación, uso y retención. No hay base para atribuir mejoras porcentuales o elegir precios definitivos.

Estos pendientes están incorporados al roadmap; el estado operativo actual no permite darlos por completados.

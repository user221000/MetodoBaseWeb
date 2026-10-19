# Roadmap priorizado de MetodoBase

Fecha base: 18 de octubre de 2026. La prioridad es convertir el motor nutricional y la interfaz existentes en un servicio confiable que conecte al gimnasio con sus clientes. Primero deben cerrarse fallos de cobro, permisos y despliegue; después completar la relación gimnasio y socio y medir su uso. El diagnóstico y las reproducciones están en los informes de [backend](backend/INFORME_BACKEND.md), [QA](qa/INFORME_QA.md), [UX](ux/INFORME_UX.md) y [operación](OPERACION_Y_SEGURIDAD.md).

## Resultado de producto buscado

**Para el dueño:** incorporar al cliente, generar y asignar un plan, delegar al equipo con permisos claros, conocer quién necesita seguimiento y entender pagos y vencimientos reales.

**Para el cliente:** abrir el plan que le asignó su gimnasio desde el móvil, entender qué hacer hoy, registrar lo que realmente completó y consultar su progreso sin perder datos al cambiar de dispositivo.

La propuesta comercial a validar es «planes y seguimiento nutricional que ayudan al gimnasio a mantener a sus clientes activos». No hay datos en esta auditoría para prometer un porcentaje de retención, resultados clínicos o un precio óptimo. Se recomienda validar el mensaje y la disposición de pago con gimnasios y socios antes de expandir el alcance a un sistema completo de gestión de gimnasios.

## Cómo se ordena el trabajo

P0 bloquea ampliar ventas o exposición: permite acceso/capacidades indebidas o pone en riesgo aislamiento y despliegue. P1 completa un recorrido esencial o reduce un riesgo material. P2 mejora diferenciación, eficiencia o crecimiento después de esa base. Los hallazgos técnicos deben cerrarse con evidencia; las ideas de producto deben validarse con usuarios.

Tamaños orientativos de trabajo efectivo por responsable: **S** hasta 2 días, **M** entre 3 y 5 días, **L** entre 1 y 2 semanas. Incluyen implementación y pruebas del alcance descrito; son estimaciones iniciales que requieren refinamiento. Migración de datos históricos, soporte e incidentes pueden ampliarlas.

El escenario de 90 días supone una persona de backend, una de frontend, QA con dedicación compartida y disponibilidad de producto/diseño. Las ventanas son de planificación, no un compromiso de entregar los 35 elementos en 90 días. Reservar aproximadamente 25% de capacidad para integración, remediación y validación. El trabajo P2 se selecciona según las métricas y la capacidad restante.

## Primeras 72 horas

1. Cerrar las rutas que conceden Pro o activan suscripción sin un pago verificado y la ausencia de cuota; añadir regresiones locales. No cambiar retrospectivamente derechos ni cargos reales sin revisar el efecto comercial.
2. Exigir permiso para altas y acciones sensibles; corregir la identidad de equipo en login y refresh. Aplicar contención sin esperar un refactor de carpetas.
3. Obtener respaldo verificable y copia de esquema para staging; preparar conciliación de migraciones. No habilitar RLS a ciegas en producción.
4. Hacer ejecutable la CI web con dependencias de prueba explícitas y pruebas de los defectos encontrados. El estado verde debe depender de controles que puedan fallar.
5. Retirar la promesa de que notas libres garantizan restricciones alimentarias; detener cualquier flujo que anuncie protección que no aplica. Las restricciones de seguridad alimentaria no deben depender de pagar un plan superior.

## Días 1 a 14 Seguridad y despliegue verificable

| ID y prioridad | Entregable | Responsable y tamaño | Dependencias y aceptación |
|---|---|---|---|
| R01 P0 | Unificar cobros, catálogo y derechos Pro | Backend M–L | Ningún POST/redirect ni pago incompleto concede acceso; `pro_usuario` persiste; cancelación/impago reconcilia ambas tablas y derechos; eventos repetidos/desordenados no duplican acceso; cuota agotada no genera |
| R02 P0 | Corregir RBAC e identidad de equipo | Backend M | VIEWER recibe 403 al crear; login/refresh conservan membresía autorizada; cambios de rol tienen efecto verificable; matriz completa por recurso |
| R03 P0 | Reconciliar esquema y reparar migraciones Railway | Backend L | Copia staging, inventario y backup; `preDeployCommand` real; base vacía y base existente llegan al mismo esquema; fallos detienen deploy; enum de roles coherente |
| R04 P0 | Implantar privilegios mínimos y aislamiento PostgreSQL | Backend L | Tras R02/R03; rol app sin superusuario/BYPASSRLS; tenant por transacción y por job; pruebas negativas con dos gimnasios y rol real restringido |
| R05 P0 | CI web reproducible y pruebas bloqueantes | QA + backend M | Manifest de test explícito; SQLite local y PostgreSQL de CI separados; sin depender del orden global de tests; lint/seguridad material bloquean según baseline aprobado |
| R06 P0 | Contención de promesas alimentarias y validación básica | Backend + frontend S | Edad/peso/altura/grasa inválidos no se guardan; retirar promesa de aplicar notas; excluir categoría completa no restaura alimentos; bloquear garantías no soportadas; contrato completo pasa a R33 |
| R07 P1 | Almacenamiento persistente de documentos y logos | Backend M | Tras definición de tenant; archivos sobreviven a redeploy; descargas autorizadas; migración de referencias y manejo de fallos probado |
| R08 P1 | Restauración y plan de continuidad | Operación + QA M | Verificar backups nativos e independientes según riesgo; ensayo de restauración con medición RPO/RTO; una ejecución sin fuente respaldada falla |

**Puerta de salida:** cerrar los bypass reproducidos, tener una CI confiable y un procedimiento de migración/restauración validado en staging. R03/R04 pueden prolongarse según las diferencias del esquema; su evidencia debe estar completa antes de ampliar captación de pago.

## Días 15 a 30 Completar la experiencia esencial

| ID y prioridad | Entregable | Responsable y tamaño | Dependencias y aceptación |
|---|---|---|---|
| R09 P1 | Una fuente de límites, precios y características | Producto + backend S | Tras R01; decidir Free 5 o 10 sin inferirlo de un test; API, web y Stripe reflejan el catálogo; desktop sólo si sigue soportado; importes/moneda/periodicidad claros |
| R10 P1 | Sesiones y revocación coherentes | Backend M | Access de duración corta, refresh de larga duración; desactivar usuario/miembro impide acciones; cerrar sesión invalida el acceso según política documentada |
| R11 P1 | Equipo utilizable de extremo a extremo | Full stack M–L | Tras R02 y correo; pantalla GET de invitación y canje POST de un uso; caducidad/revocación; navegación por permisos; dueño invita y miembro accede a su gimnasio |
| R12 P1 | Relación gimnasio cliente y cuenta de acceso | Backend + frontend L | Tras R04; distinguir cuenta individual y socio de gym; invitación vincula usuario al cliente correcto; socio consulta el mismo plan asignado por su gym; no ve otro gym |
| R13 P1 | Corregir móvil, teclado y accesibilidad | Frontend + QA M | Suscripciones/clientes sin acciones cortadas a 320/390 px y regresión 768/1440; hamburguesa no tapa títulos; controles nombrados; foco y Enter correctos; PDF accesible en historial |
| R14 P1 | Persistir seguimiento del usuario y del socio | Backend + frontend L | Empezar con usuario individual y fecha local sin esperar R12; integrar pertenencia al gym después; mismo estado en dos dispositivos; logout no borra historial; nunca mezcla cuentas |
| R15 P1 | Estados de progreso y pago veraces | Frontend S | No mostrar 100% por contenido del menú; redirect no afirma pago; perfil incompleto lleva a completar datos; errores visibles y accionables |
| R16 P1 | Correo e inicio de recuperación de cuenta | Backend + operación M | Proveedor verificado y entregas observables; invitación y recuperación con tokens de un uso/caducidad; sin enumeración de cuentas ni envíos reales desde pruebas |

**Puerta de salida:** un gimnasio piloto incorpora un socio y éste abre el plan correcto en móvil, registra seguimiento y vuelve a encontrarlo. Otro gimnasio no puede acceder al recorrido ni a sus archivos. El dueño puede delegar tareas con permisos efectivos.

## Días 31 a 60 Retención y calidad operativa

| ID y prioridad | Entregable | Responsable y tamaño | Dependencias y aceptación |
|---|---|---|---|
| R17 P1 | Alarmas, degradación Redis y trazabilidad | Backend + operación M | Caída Redis simulada no elimina límites de rutas sensibles; webhooks/cola/backup/correo tienen métricas y alertas; logs sin tokens o notas de salud |
| R18 P1 | Dependencias e imagen trazables | Backend + QA M | Lock Linux coherente con Docker, SBOM y escaneo de resolución/imagen; actualizar advisories aplicables; promover el mismo digest; excepciones con vencimiento |
| R19 P1 | Suite E2E de recorridos y abuso | QA M | Tras R01/R02/R12; compra sandbox, impago, refresh, invitación, generación, PDF, seguimiento y dos tenants; workers aislados; cada error bloquea el release correspondiente |
| R20 P1 | Documentación vigente y límites de arquitectura | Tech lead S inicial | README web, mapa actual, matriz de permisos, ADR de billing/tenant/storage, contratos y runbooks por commit; requisitos en cada PR posterior |
| R21 P2 | Higiene del repositorio | Backend S | Retirar entornos versionados y artefactos históricos del árbol activo con revisión; ignorar venv/.venv-test; secretos escaneados sin publicar valores; dependencias se reinstalan |
| R22 P1 | Mejorar onboarding existente por objetivo | Diseño + frontend M | Probar 5 dueños y 5 socios; dueño llega a primer plan asignado; socio comprende acción diaria; reanudar proceso; datos demo identificados y separables |
| R23 P2 | Convertir dashboard de retención en acciones | Producto + frontend M | Extender dashboard existente: lista priorizada por causa, próximo paso y responsable; distinguir cobro real de fecha de membresía; acciones medibles |
| R24 P2 | Mejorar plan diario y lista de compras | Frontend M | Tras R14; menú legible, porciones y sustituciones autorizadas; hábitos/consumo reales; lista por periodo; estados vacíos y de error revisados |
| R25 P2 | Progreso compartido con el profesional | Full stack M | Tras R12/R14; tendencias de medidas y adherencia, fecha/fuente visibles y permisos explícitos; sin gráficos ficticios ni conclusiones médicas automáticas |
| R26 P1 | Suscripción y facturación comprensibles | Producto + full stack M | Tras R01/R09; plan actual, cuotas restantes, precio MXN, periodo y estado verificados; cancelar/renovar claros; la UI distingue licencia del gym de membresía del socio |

**Puerta de salida:** la operación detecta fallos y el piloto genera evidencia de uso repetido. Las decisiones de diseño se contrastan con sesiones de usuario, no sólo capturas. Cerrar R17/R18/R19 y los riesgos de privacidad antes de incorporar más gimnasios con datos reales.

## Días 61 a 90 Conversión y crecimiento seleccionado

| ID y prioridad | Entregable | Responsable y tamaño | Dependencias y aceptación |
|---|---|---|---|
| R27 P2 | Recordatorios y recuperación de pagos | Producto + backend M | Tras R16/R26; preferencias/consentimiento, límites de frecuencia, reintentos y exclusión; distinguir mora confirmada de falta de registro; medir renovaciones sin atribuir causalidad indebida |
| R28 P2 | Generación y efectos externos durables | Backend L | Si las métricas lo justifican; job persistido, idempotencia/outbox, reintentos y estado UI; reinicio no pierde plan ni duplica correos/cuota |
| R29 P2 | Landing comercial conectada al producto | Diseño + frontend M | Mensaje para dueño y socio, prueba/demo y precio vigente; CTAs visibles en móvil; enlazar recorridos reales; retirar promesas y páginas huérfanas |
| R30 P1 | Analítica y entrevistas de producto | Producto S inicial | Medir desde semana 1 y revisar por cohorte; eventos mínimos sin salud/PII; baseline antes de objetivos; entrevistas y decisión de continuar cada experimento |
| R31 P1 | Privacidad y gestión del dato personal | Producto + backend M | Iniciar en fase 1; inventario/finalidad/retención, acceso de soporte, exportar/borrar, consentimientos aplicables y revisión legal del servicio; prueba de borrado en copias/objetos según política |
| R32 P1 | MFA o passkeys para roles privilegiados | Backend + frontend M | Tras R10/R16; alta, desafío, recuperación y revocación probados; step-up para equipo/facturación; adopción sin bloquear recuperación legítima |
| R33 P1 | Garantías del motor y revisión profesional | Responsable nutrición + backend + QA M–L | Iniciar en fase 1; contrato estructurado de alergias/exclusiones sin depender del plan pagado; entradas límite, unidades y repetibilidad; validar con especialista; condiciones clínicas fuera de automatismo no validado |
| R34 P2 | Rendimiento con carga representativa | Backend + QA M | Datos sintéticos, p95 y colas medidos por flujo; índices/paginación/pools ajustados a hallazgos; objetivos acordados; sin pruebas de carga sobre producción |
| R35 P2 | Evaluar PWA y acceso rápido móvil | Producto + frontend S inicial | Sólo tras retención y rendimiento básicos; instalar acceso y manejar conectividad con privacidad; no cachear planes sensibles sin política; construir si mejora uso medido |

R30, R31 y R33 son trabajo transversal: su fila en esta ventana no retrasa el inicio. Si hay capacidad limitada, reservar días 61 a 90 para cerrar P1 y elegir como máximo dos iniciativas P2 de mayor evidencia.

## Qué debe ver cada usuario

| Recorrido | Dueño o equipo | Socio |
|---|---|---|
| Primera sesión | Objetivo del gimnasio, configuración mínima, primer cliente y asignación | Invitación identificable, vínculo al gym y completar sólo datos necesarios |
| Inicio diario | Personas que requieren acción, vencimientos verificados y tareas del equipo | Plan vigente, siguiente comida y acciones de seguimiento pendientes |
| Plan | Generación con restricciones, revisión, entrega, versión e historial | Porciones claras, acceso PDF y explicación de cambios |
| Progreso | Tendencias y señales para contactar con contexto autorizado | Registro simple, historial persistente y avance que proviene de lo registrado |
| Pagos | Licencia SaaS separada de las membresías del negocio | Qué está pagando, a quién, cuándo y qué obtiene |
| Error | Causa comprensible, reintentar o contactar con referencia técnica | Datos conservados, estado claro y un siguiente paso útil |

## Métricas y validación

No hay baseline de negocio comprobado. Instrumentarlo sin notas de salud ni contenido del plan en analítica. Los objetivos iniciales son hipótesis y se recalibran después de dos semanas de datos.

| Métrica | Definición | Uso o meta inicial propuesta |
|---|---|---|
| Activación gym | Registro que termina con cliente invitado y plan asignado/abierto | Medir embudo y tiempo; probar objetivo de primer valor menor a 10 minutos |
| Activación socio | Invitación aceptada y primera consulta del plan asignado | Separar de usuario individual; localizar abandono por dispositivo |
| Retención D7/D30 | Usuarios activados que vuelven a una acción útil en ventana definida | Comparar cohortes y frecuencia; no fijar porcentaje sin baseline |
| Adherencia registrada | Acciones realmente registradas sobre acciones esperadas | Diferenciar uso de app y cumplimiento nutricional; no inferir consumo de calorías del menú |
| Renovación de gym | Licencias renovadas entre las que vencían | Conciliar con pagos; seguir cancelaciones y causas |
| Conversión a pago | Usuarios elegibles que completan pago verificado | Nunca contar un redirect ni acceso Pro concedido por defecto |
| Fiabilidad | Éxito de generación, p95, errores y latencia webhook | Acordar SLO tras carga de referencia; alertar por cambios |
| Aislamiento y continuidad | Casos negativos de tenants y restauraciones completadas | Cero cruces en la matriz probada; restore periódico con evidencia |

Validación inicial recomendada: entrevistas con 5 dueños y 5 socios y un piloto acotado con 2 o 3 gimnasios que acepten participar. Son tamaños propuestos para descubrir problemas; no equivalen a significancia estadística ni validación clínica. Los contactos no se han realizado y no se enviaron invitaciones desde esta auditoría.

## Opciones posteriores a validar

Reservas de clases, rutinas de entrenamiento, asistencia QR, multi-sucursal y referidos pueden ampliar el atractivo, pero incorporan nuevos datos, operaciones y soporte. Ya existen accesos de texto a WhatsApp; una ampliación consistiría en entrega autorizada de PDF o recordatorios con preferencias, no en volver a crear un enlace. Primero averiguar qué problema de mayor valor no resuelve ya cada gimnasio con otra herramienta. Para cada opción pedir evidencia de demanda, responsable, coste de integración, piloto y criterio de abandono. No incluirlas todas en el primer ciclo de 90 días.

Tampoco es necesario migrar a React/Vue, desarrollar apps nativas o introducir microservicios para corregir los recorridos actuales. Esas decisiones requieren un problema medido que el stack vigente no resuelva de forma razonable.

## Definición de terminado

Una tarea se cierra cuando cumple sus criterios en staging con datos sintéticos, tiene regresión del fallo relevante, no rompe aislamiento ni accesibilidad del recorrido, conserva contratos necesarios y actualiza documentación/runbook. Los cambios de esquema necesitan revisión de compatibilidad y restauración; los de pago necesitan sandbox y conciliación. El mismo artefacto validado se promueve a producción con observación y rollback documentados.

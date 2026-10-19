# Auditoría UX, UI, accesibilidad y producto de Método Base

Fecha de referencia: 18 de octubre de 2026, America/Mexico_City.

La base visual y el núcleo nutricional ya permiten demostrar valor. Los problemas más relevantes son la continuidad del servicio y la correspondencia entre lo que la interfaz promete y lo que guarda o confirma el servidor. Antes de invertir en un rediseño visual completo conviene corregir pagos, seguridad alimentaria, progreso persistente y recorridos móviles.

## Alcance y evidencia

- Lectura de todas las plantillas web, navegación compartida, CSS, JavaScript, rutas de páginas y contratos relacionados con clientes, perfiles, equipos, planes y suscripciones.
- Producción pública: Chrome sobre `https://metodobase.up.railway.app`, landing a 1440 × 1000 y 390 × 844; registro y ambos accesos a 390 × 844. Se bloquearon solicitudes distintas de GET/HEAD/OPTIONS. No hubo autenticación, registros, pagos ni escrituras en producción.
- Aplicación real local: `http://127.0.0.1:8765`, preparada por QA con SQLite efímero, cuentas y clientes sintéticos, sin integraciones externas. Nueve pantallas a 390 × 844, generación real de un plan y comprobaciones funcionales concretas. Las solicitudes externas del navegador local fueron bloqueadas; las capturas locales usan la tipografía de respaldo disponible.
- Accesibilidad automática: `playwright-core` 1.64.1 y `@axe-core/playwright` 4.14.0, reglas WCAG A/AA seleccionadas. No equivale a una certificación ni sustituye lector de pantalla, teclado y ampliación manuales.
- Guía local consultada: `.github/skills/auditoria-proyecto/SKILL.md`; los hallazgos históricos de esa guía se trataron como hipótesis, no como evidencia vigente.
- Sin modificaciones al producto. Este directorio contiene únicamente documentación, capturas y resultados de auditoría.

Evidencia de producción: [public-browser-audit.json](public-browser-audit.json). Evidencia autenticada local: [local-browser-audit.json](local-browser-audit.json). Las rutas y líneas siguientes corresponden al árbol local auditado; el agente principal documenta la correspondencia con GitHub y Railway.

## Lo que ya existe

| Capacidad | Evidencia | Estado observado |
| --- | --- | --- |
| Acceso y registro separados para gimnasio e individuo | `web/templates/login_gym.html`, `login_usuario.html`, `registro.html` | Presentes; email/contraseña y Google condicionado a configuración. |
| Clientes, búsqueda, filtros y estado de suscripción | `clientes.html:55`, `:519`, `:539`; `web/routes/clientes.py` | Alta sintética local 201; filtros y tabla presentes. |
| Generación guiada de planes y PDF | `generar-plan.html:14`, `:630`, `:833` | Wizard presente. Generación individual real local 200. No se ejecutó cobro ni entrega real. |
| Perfil, objetivos, macros y exclusiones explícitas | `usuario_perfil.html:39`, `:101`, `:111`; `usuario.py:114` | Guardado local 200; exclusiones existen, su tratamiento requiere revisión de seguridad alimentaria. |
| Marca del gimnasio y precios de membresía | `configuracion.html`; `gym_profile.py:150` | Configuración y logo presentes; problemas de adaptación móvil y duplicación de valores iniciales. |
| Onboarding, estados vacíos, skeletons, toast y atajos | `dashboard.html:372`; `main.js:63`, `:202`, `:255`; `components.js` | Ya implementados parcialmente; requieren correcciones de exactitud y teclado. |
| Seguimiento diario de agua/comidas y calendario | `usuario_mi_plan.html:728`, `:989`; `usuario_historial.html:184` | Existe en el navegador; no es progreso sincronizado entre dispositivos. |
| Base RBAC y API de equipo | `services/permissions.py`; `routes/team.py` | Owner/admin/nutriólogo/viewer ya existen; falta experiencia web de equipo completa. |
| Cobros, proveedores, portal e historial | `suscripciones.html`, `usuario_suscripcion.html`, `api.js:252` | Superficies existentes; validación de backend y proveedores corresponde al informe de seguridad/QA. |

Los consejos de negocio de `web/static/js/insights.js:1` son reglas heurísticas locales sobre las métricas, no un motor externo de IA. Conviene conservar su utilidad sin comunicar capacidades que no tiene.

## Hallazgos priorizados

P0: corregir antes de captar nuevos pagos o prometer protección alimentaria. P1: bloquea un recorrido principal o compromete confianza, acceso o continuidad. P2: mejora importante para activación, operación o mantenimiento.

| ID / prioridad | Hallazgo y evidencia | Impacto y corrección |
| --- | --- | --- |
| UX-01 / P0 | `usuario_suscripcion.html:708-721` interpreta parámetros de URL de éxito, llama al cambio de plan con `catch` vacío, lanza confeti y muestra Pro antes de confirmar la suscripción del servidor. | El usuario puede ver una compra confirmada que el servidor o proveedor no han validado. La activación debe venir del estado persistido y verificable del backend. Este hallazgo se comparte con seguridad; no representa un problema puramente visual. |
| UX-02 / P0 | `usuario_perfil.html:102-105` promete aplicar notas de alergias, condiciones especiales e incluso diabetes. `_do_generar_plan`, `web/routes/planes.py:95-115`, no incorpora notas al objeto nutricional: solo lee exclusiones explícitas y puede descartarlas por plan comercial. | Una nota médica no constituye una regla de seguridad del generador. Eliminar inmediatamente la promesa incorrecta, distinguir preferencia y alergia estructurada, bloquear el flujo cuando no pueda respetarse una restricción de seguridad y someter el contrato a revisión profesional. No ofrecer protección de alergias como mejora de pago. Evidencia de código, sin experimento clínico. |
| UX-03 / P1 | Diario guardado únicamente en claves como `mb_daily_FECHA`, `mb_water_FECHA`, `mb_meals_FECHA` (`usuario_mi_plan.html:428-430`, `:728`, `:783-785`, `:1067`). `base_usuario.html:170` ejecuta `localStorage.clear()`. | Reproducción local: guardar 1.5 L crea diario/agua; cerrar sesión deja ambas listas vacías. Se pierde el supuesto historial y otro dispositivo no lo recibe. Faltan persistencia por usuario y fecha, sincronización e identidad de cada registro. Las claves tampoco incluyen usuario: existe riesgo de reutilizar datos si cambian las credenciales sin el cierre que borra todo. |
| UX-04 / P1 | `new Date().toISOString().slice(0,10)` define el día del diario y del calendario (`usuario_mi_plan.html:428`; `usuario_historial.html:256`). | Verificado con navegador en America/Mexico_City: el 18 de octubre por la tarde se escribió `mb_daily_2026-10-19`. Definir fecha local del usuario/gimnasio y zona horaria explícita; probar cambio de día y horario. |
| UX-05 / P1 | Diseño móvil recorta acciones principales. `/suscripciones`: ancho de documento 582 px en viewport 390; `/clientes`: 483 px. `suscripciones.html:91` fija 3 columnas; `configuracion.html:24` mantiene 2 columnas. `styles-usuario.css:1931-1936` oculta desbordamiento del historial. El menú fijo tapa títulos de gimnasio (`styles.css:1820`, `:1877`). | Capturas locales muestran precios/CTA fuera de pantalla, búsqueda casi sin espacio y PDF del historial inaccesible visualmente. Usar layouts por breakpoint, cabecera con espacio reservado, tablas con scroll accesible o tarjetas. No ocultar el desbordamiento global como sustituto. |
| UX-06 / P1 | Equipo sin recorrido web completo: no hay pantalla en `pages.py` ni navegación de equipo. `team.py:240` genera `/auth/accept-invite?token=...`, pero la API POST real está montada en `/api/auth/accept-invite` (`main_web.py:333`). GET de esa ruta devolvió 404 local. Además `team.py:146` incorpora el enlace completo recibido como si fuera el token del correo, produciendo una URL mal formada. Los invitados son `tipo='usuario'` (`team.py:224`), mientras `auth-guard.js:26-29` envía ese tipo al portal individual. | No se puede vender operación de 2/4 profesionales simultáneos con este recorrido incompleto. Añadir gestión de miembros, aceptar invitación con URL absoluta y token correcto, sesión con gimnasio efectivo y navegación por permisos. Reutilizar RBAC existente. |
| UX-07 / P1 | Portal individual y cartera del gimnasio son productos desconectados. `usuario.py:55-77` crea un Cliente cuyo `gym_id` es el propio usuario; `models.py:162-204` no define vínculo de cuenta miembro a cliente del gimnasio. | El socio que se registra no obtiene automáticamente el plan del dueño. Diseñar invitación/asignación miembro-cliente, acceso al plan del gimnasio y reglas explícitas de revocación/traslado. Conservar también el caso independiente si es parte de la oferta. Es una brecha de producto observada en modelo y rutas, no un fallo de aislamiento que deba resolverse compartiendo cuentas. |
| UX-08 / P1 | El manejador global Enter de `main.js:272-303` intercepta elementos interactivos fuera de formularios y dispara el CTA del dashboard. | Prueba local: enfocar enlace Clientes y pulsar Enter dejó `/dashboard` y abrió el modal de cliente. Respetar la activación nativa de enlaces/botones; limitar atajos a controles concretos y evitar disparar acciones financieras o de guardado por Enter genérico. |
| UX-09 / P1 | Accesibilidad: contraste insuficiente recurrente, icono de contraseña sin nombre en ambos accesos, objetivos táctiles pequeños, inputs de precios sin nombre accesible. JSON contiene selectores y ratio. Toasts carecen de región de estado (`components.js:8-35`; `base_usuario.html:123`), filas/calendario son solo clic (`usuario_historial.html:124-150`, `:278-296`). Modales no implementan semántica, retorno/trampa de foco coherentes. | Corregir tokens, nombres, labels, botones semánticos, foco, Escape y avisos anunciables. Ya existe `:focus-visible` y reducción de movimiento en CSS del gimnasio (`styles.css:1983-1996`); extender una solución compartida a ambas interfaces. Los resultados automáticos no verifican por sí solos la operación con lector de pantalla. |
| UX-10 / P1 | `usuario_mi_plan.html:520-529` calcula "Vas al 100% de tu meta diaria" usando kcal del menú generado. Después alterna con porcentaje de cuatro checkboxes o selección (`:1210-1248`). | Captura local de una cuenta recién configurada, sin registrar alimentos: ya muestra 100%. Separar objetivo nutricional, plan prescrito, selección de opciones y consumo real; definir una sola fuente para adherencia. |
| UX-11 / P2 | Onboarding incompleto muestra Generar/Comidas/Agua/Excluir (`usuario_mi_plan.html:464-468`) y retorna antes de registrar sus listeners. Dice que bastan 3 datos (`:148`), mientras exige edad y otros campos en perfil. | Prueba local: pulsar Generar no produjo petición, mensaje ni navegación. Mostrar la siguiente acción realizable y explicar los datos necesarios; deshabilitar/explicar acciones aún no disponibles. |
| UX-12 / P1 | Fallos se muestran como ausencia o estado válido: `usuario_historial.html:155-157` muestra "Sin planes" ante error; `usuario_suscripcion.html:660-663` sustituye error por Starter activo; `usuario_mi_plan.html:452-483` silencia fallos. Muchas llamadas directas `fetch` eluden refresh y error estructurado de `api.js:85-145`. | Evitar que una falla de red o sesión parezca pérdida de datos/cambio de plan. Diferenciar vacío, permiso, sesión expirada y servicio no disponible, con reintento explícito y conservación de lo último conocido. Hallazgo de código; no se provocaron fallos en producción. |
| UX-13 / P2 | Sin suscripción local, `suscripciones.html:344-353` muestra "Sin plan" junto a "Renovación mensual automática" y "Renovación automática activa". `usuario_suscripcion.html:366-369` fuerza badge Activo sin consumir estado real. | Genera incertidumbre sobre si se cobrará al usuario. Modelar sin plan/prueba/pago pendiente/activo/vencido/cancelado y mostrar proveedor, importe, fecha y acción que correspondan. |
| UX-14 / P2 | Una cuenta nueva mostró 10 membresías en configuración: cada uno de los 5 valores iniciales duplicado. `repository.py:520-528`, `:560-568` crea defaults al leer sin unicidad de gimnasio/duración. El dashboard hace varias lecturas concurrentes. | Observación reproducida en dos ejecuciones independientes de navegador. La carrera concreta es inferencia apoyada por código; seguridad/backend debe confirmarla. Inicializar de forma idempotente y limpiar duplicados con una migración revisada antes de permitir cambios de precio. |
| UX-15 / P2 | El perfil indica "Cambios de contraseña desde ajustes" (`usuario_perfil.html:24`), pero no existe esa pantalla para individuos. Accesos no ofrecen recuperación de cuenta. Registro/login usan `novalidate`; muchas etiquetas no están asociadas mediante `for`. Rangos de datos varían entre cliente nuevo, drawer y perfil (`clientes.html:154-185`, `dashboard.html:126`, `usuario_perfil.html:44-52`). | Recuperación de contraseña y gestión de cuenta verificables; un contrato de validación compartido y errores por campo accesibles. Evitar que el usuario se dirija a una función inexistente. |
| UX-16 / P2 | Landing real (`pages.py:37`, `templates/landing.html`) es principalmente un selector de acceso. La landing comercial de `web/pages/landing.html` no está conectada a las rutas revisadas. En móvil el CTA de miembro y el registro aparecen debajo del primer viewport. No se muestran precios públicos, muestra real del resultado, límites o soporte. | Conservar accesos rápidos para usuarios recurrentes y añadir recorrido comercial para prospectos con ejemplo de plan, beneficios verificables, precios/límites, FAQ, privacidad y CTA contextual de registro. El registro por defecto es individual aunque el usuario puede llegar buscando un gimnasio. |
| UX-17 / P2 | Onboarding marca exportación terminada al existir un plan (`main.js:198`, `hasExported = hasPlans`). El botón "Actualizar mi plan" guarda perfil y luego pide regenerar por separado (`usuario_perfil.html:122`, `:315-333`). WhatsApp solo prepara texto, sin adjuntar PDF (`generar-plan.html:843-875`), mientras otro texto sugiere envío directo. | Medir los eventos reales, llamar a cada acción por lo que hace y acompañar la entrega con instrucciones o un mecanismo autorizado de compartición. Evitar un checklist al 100% sin que el cliente haya recibido nada. |

## Comprobación visual y automática

| Pantalla | Evidencia | Resultado relevante |
| --- | --- | --- |
| Landing desktop de producción | [landing-desktop.png](landing-desktop.png) | Jerarquía clara y visual consistente; ninguna regla de axe fallida en esa ejecución. No implica cumplimiento total. |
| Landing móvil de producción | [landing-mobile.png](landing-mobile.png) | Sin overflow del documento; texto secundario con contraste insuficiente en 3 elementos. |
| Registro móvil de producción | [registro-mobile.png](registro-mobile.png) | Sin overflow; contraste en selector de tipo de cuenta. |
| Accesos móviles de producción | [login-gym-mobile.png](login-gym-mobile.png), [login-usuario-mobile.png](login-usuario-mobile.png) | En cada uno: 1 botón sin nombre, 6 elementos de contraste y 1 objetivo táctil insuficiente. |
| Dashboard de gimnasio local | [local-gym-dashboard-empty-mobile.png](local-gym-dashboard-empty-mobile.png) | Menú tapa título; onboarding largo y columnas estrechas; 13 elementos con contraste insuficiente. |
| Configuración local | [local-gym-config-mobile.png](local-gym-config-mobile.png) | Dos columnas estrechas y membresías duplicadas; 19 elementos de contraste, 10 inputs sin nombre y 1 imagen sin alternativa. |
| Suscripción de gimnasio local | [local-gym-subscription-mobile.png](local-gym-subscription-mobile.png) | 582 px de contenido en 390 px; 26 elementos de contraste y 1 imagen sin alternativa. |
| Clientes local | [local-gym-clientes-mobile.png](local-gym-clientes-mobile.png) | 483 px de contenido en 390 px; tabla y búsqueda cortadas. |
| Onboarding/perfil individual local | [local-user-onboarding-mobile.png](local-user-onboarding-mobile.png), [local-user-profile-mobile.png](local-user-profile-mobile.png) | Acciones sin respuesta antes del perfil; perfil exige más datos de lo anunciado y lista de exclusiones extensa. |
| Plan individual local | [local-user-plan-mobile.png](local-user-plan-mobile.png) | Pantalla de aproximadamente 6919 px; 100% sin consumo registrado; 79 elementos de contraste insuficiente. |
| Historial individual local | [local-user-history-mobile.png](local-user-history-mobile.png) | Tabla recortada, columnas PDF/tipo/macros fuera de la vista sin scroll del contenedor. |
| Suscripción individual local | [local-user-subscription-mobile.png](local-user-subscription-mobile.png) | Layout móvil sin overflow del documento; 12 elementos de contraste insuficiente. |

Los recuentos son nodos detectados por pantalla, no defectos únicos ni puntuaciones de calidad. Se repiten componentes entre rutas y no se deben sumar para afirmar un número de vulnerabilidades.

## Roadmap UX y producto propuesto

Los tamaños son rangos de jornadas de implementación y validación por iniciativa, sujetos al diseño técnico. No son fechas prometidas ni deben sumarse como calendario: backend, QA, producto y diseño tienen dependencias compartidas.

| Orden / ventana orientativa | Iniciativa | Impacto de negocio | Tamaño | Criterio de aceptación |
| --- | --- | --- | --- | --- |
| 1 / contención inmediata | Confirmación de pagos y contrato de alergias | Protege cobros, confianza y uso responsable | S–M, 2–5 jornadas por frente, más revisión de dominio | Ningún parámetro de URL activa un pago; UI obtiene estado confirmado. No se afirma aplicar una restricción que el generador ignora. |
| 2 / primeras 2 semanas | Móvil funcional y accesibilidad de acciones principales | Mejora conversión y operación en recepción/teléfono | M, 4–8 | 320/390/768/1440 px: registro, alta, plan, historial y pago sin acciones cortadas. Pruebas de teclado completas y cero fallos serios/críticos de axe en las rutas corregidas, más revisión manual. |
| 3 / primeras 2–4 semanas | Diario persistente con zona horaria y adherencia coherente | Retención y confianza del miembro | M–L, 6–12 | Registrar comida/agua, salir, entrar en otro dispositivo y recuperar los mismos datos; aislamiento entre usuarios; fechas locales correctas; meta comienza en 0 si no hay consumo. |
| 4 / semanas 3–5 | Vincular miembro al gimnasio y completar equipos | Hace real el producto para dueño, profesional y socio | L, 8–15 | Dueño invita cliente y profesional; ambos aceptan enlace; cada rol ve únicamente las acciones y el cliente asignado que le corresponden. Revocar acceso tiene efecto verificable. |
| 5 / semanas 4–6 | Recorridos de activación, recuperación y fallos | Reduce abandono y soporte manual | M, 5–8 | Un dueño nuevo completa marca → cliente → plan → entrega con guía; individuo completa perfil y genera sin botones inertes; recuperación existe; 401/403/422/429/5xx/red tienen mensaje y recuperación específicos. |
| 6 / semanas 5–8 | Oferta pública y catálogo comercial coherentes | Mejora adquisición y claridad del precio | M, 4–7 | Precio/límite/capacidad provienen del mismo catálogo que backend; landing muestra ejemplo, límites y CTA por público; eventos de activación y pago real se registran con minimización de datos. |
| 7 / semanas 7–12 | Seguimiento profesional y reactivación útil | Diferenciación y valor recurrente para el gym | L, 8–15 | Reutilizar `ClientProgress` existente (`models.py:499`) mediante API/UI: medición fechada, evolución, revisión de plan y tareas de seguimiento; recordatorios solo con consentimiento y preferencias. |
| 8 / después de validar uso | Ampliación a reservas, rutinas y operación del gimnasio | Expansión de mercado, con coste alto de dominio | XL, estimar tras descubrimiento | Decidir con gimnasios si competir como plataforma nutricional especializada o gestión integral; prototipo y contrato antes de desarrollar calendario, aforo, asistencia, ejercicios, sesiones y cobros de membresía reales. |

Reservas de clases, check-in/asistencia, aforo, rutinas de entrenamiento, series/repeticiones/cargas, sucursales y notificaciones de producto no aparecen como recorridos implementados en las rutas/plantillas web revisadas. No son todos obligatorios para vender una solución nutricional; serían alcance nuevo si se elige una oferta integral de gimnasio. La configuración actual de precios/fechas de membresía no equivale a un sistema de recaudación y conciliación de cuotas de socios.

## Diseño de experiencia recomendado

Para el dueño, la primera pantalla debería orientar a la siguiente acción real: configurar marca, agregar cliente, generar plan, entregar y programar revisión. Las alertas de clientes sin plan y suscripciones próximas ya existen; falta distinguir fecha de membresía, actividad nutricional y dinero efectivamente cobrado antes de comunicar "pagando" o "ingresos".

Para profesionales, reutilizar permisos existentes para una cartera asignada, revisión de datos y restricciones, historial de mediciones y un plan aprobado. La experiencia de recepción puede ser una combinación de permisos de clientes/cobros sin acceso innecesario a notas de salud. No resolverlo mediante cuentas compartidas.

Para el miembro, priorizar el menú del día, la siguiente comida y un registro breve. El menú de cuatro comidas con todas las opciones y todos los consejos suma casi siete mil píxeles en móvil: usar divulgación progresiva, mostrar solo la próxima comida y abrir alternativas a petición. El progreso debe distinguir objetivos, comida elegida y consumo confirmado.

Consolidar tokens semánticos, componentes de formulario, avisos, panel/modal, tablas y cliente HTTP entre las dos interfaces. `styles.css`, `styles-usuario.css` y `styles-auth.css` ya contienen bases de diseño; una migración gradual puede corregir componentes repetidos sin reescribir toda la aplicación ni adoptar un framework por sí mismo.

### Vinculación segura de gimnasio y socio

Mantener el perfil independiente y sus datos actuales; no reasignar su `gym_id` ni unir carteras porque coincida un email. Añadir un vínculo explícito de cuenta y cliente con gimnasio, cliente, usuario, estado, invitación y permisos de compartición. Ese vínculo del socio es distinto de la pertenencia profesional `team_gym_id`.

La primera entrega puede ser de lectura: dueño invita al cliente, el destinatario autenticado y verificado acepta mediante un token de un uso y abre el mismo plan vigente publicado por el gimnasio. El backend resuelve el vínculo activo desde el usuario autenticado y aplica gimnasio y cliente autorizados en la transacción. Un selector de contexto del navegador no concede acceso por sí mismo. Comprobar que el cliente pertenece al gimnasio del vínculo mediante restricciones de datos y política de servidor.

El diario del usuario independiente puede persistirse antes de completar esta vinculación. Para socios, guardar propietario, contexto autorizado, fecha local y zona horaria de cada registro; definir qué comparte con su profesional. `ClientProgress` puede cubrir medidas corporales; comidas y agua necesitan su contrato de diario y no deben agregarse como campos improvisados de mediciones. Revocar el vínculo debe cortar acceso al gimnasio sin eliminar el perfil independiente, respetando una política explícita de retención y exportación.

Validar primero con dos gimnasios y cuentas sintéticas: invitación para destinatario equivocado, token repetido o vencido, cambio de rol, vínculo revocado, acceso al plan de otro cliente y usuario independiente sin vínculo. Incorporar migración de datos existentes y reversión antes de extender el piloto.

## Medición y salida de calidad

No se encontró instrumentación web de un funnel de activación. Sí existen métricas operativas, estadísticas del gimnasio e insights: reutilizarlas donde corresponda y añadir eventos de producto con propósito y datos mínimos.

- Activación de gimnasio: primer cliente válido, primer plan persistido y primera entrega confirmada. Medir cada evento por separado; hoy onboarding infiere exportación.
- Tiempo al primer valor: desde registro hasta plan entregable. Usar una línea base real; "menos de 5 minutos" puede ser objetivo, no un resultado de esta auditoría.
- Activación de miembro: aceptar invitación, abrir plan del gimnasio y registrar primer día; medir adopción y retención a 7/30 días antes de fijar objetivos comerciales.
- Pago: inicio de checkout → confirmación del proveedor → estado visible correcto; medir fallos y retrasos sin registrar datos de tarjeta ni información de salud.
- Calidad: matriz de roles y tenants, teclado/lector de pantalla, tamaños de pantalla, fechas locales, red lenta/fuera de línea, expiración de sesión, cambios de plan y persistencia tras logout/redeploy.

Referencia normativa de accesibilidad consultada: [WCAG 2.2, recomendación W3C](https://www.w3.org/TR/WCAG22/), en particular contraste 1.4.3, teclado 2.1.1, reflow 1.4.10, foco 2.4.7/2.4.11, tamaño de objetivo 2.5.8, nombres/roles 4.1.2 y mensajes de estado 4.1.3. Los términos "seguro", "100% privado" y otras afirmaciones absolutas de la interfaz necesitan respaldo verificable y no constituyen evidencia de cumplimiento.

## Límites pendientes

No se probaron cuentas ni datos reales, compra/cancelación/reembolso en proveedores, entrega efectiva de correo o WhatsApp, integración con equipos reales, dispositivos físicos, Safari/iOS, lector de pantalla ni visual autenticada desktop/tablet. No se realizaron pruebas médicas ni se determinó cumplimiento legal. La autenticación local y los nueve recorridos observados no garantizan el mismo resultado bajo PostgreSQL/RLS de producción. Estas verificaciones deben incorporarse a la matriz de QA antes del siguiente lanzamiento.

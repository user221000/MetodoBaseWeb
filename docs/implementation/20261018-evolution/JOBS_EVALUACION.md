# R28/R34 — Evaluación de generación y efectos durables

Revisión estática del 19 de octubre de 2026 UTC, sobre `74d66e8b6b1c7613186ad21f4710776fd6321eaf` y los archivos R07 pendientes de integración. Las huellas exactas están en [jobs-static-evaluation-source.json](evidence/jobs-static-evaluation-source.json). Esta tarea no importó la aplicación, ejecutó pruebas, abrió bases de datos, envió correos ni midió carga. Las pruebas citadas se leyeron; sus resultados deben consultarse en sus gates propios.

## Decisión propuesta

El ledger B2B protege cuota y publicación frente a varias ventanas de fallo; **no es todavía un ejecutor recuperable**. Mantener la generación HTTP actual mientras se mide R34. No escoger un broker ni mover CPU a background sin contrato de recuperación y resultados reproducibles. La reconciliación de reservas ambiguas y el outbox de correo necesitan un diseño persistente aunque la carga no justifique un broker.

Antes de reintentos automáticos debe contenerse la brecha de cuota individual descrita abajo. Añadir una cola a su flujo actual conservaría esa brecha y permitiría repetir trabajo sin vincularlo de forma atómica al crédito.

R28 permanece pendiente. Esta decisión no introduce una duración de reserva, retención, reembolso por antigüedad ni nueva promesa de entrega de correo.

## Estado observado

| Parte | Garantía actual y fuente | Límite práctico |
| --- | --- | --- |
| Reserva B2B | `gym_generation_quota.py:80` bloquea cuenta, valida las tres dimensiones de cuota y confirma una reserva única por gimnasio/clave con huella DTO, periodo y calendario capturados. | La huella cubre el DTO de generación, no una copia durable del perfil, exclusiones, catálogo, branding o versión del generador. |
| Publicación B2B | `repository.py:243` vincula Plan y `persisted_at` mediante CAS de la reserva en la misma transacción del Plan, contador y objeto ready. | El resultado HTTP se confirma después, en `complete_gym_generation`; puede quedar Plan confirmado y reserva `reserved` sin `result_json`. |
| Compensación B2B | `gym_generation_quota.py:142` libera solamente `reserved` sin `persisted_at`; un marcador confirmado sobrevive a la eliminación de Plan. La compensación incierta responde 503 con código estable. | No hay consumidor que reconcilie ese estado ni autorización para reconstruir un resultado desde datos vivos o reembolsarlo por tiempo. |
| CPU | `plan_generation.py:13` usa lock de proceso y `:32` workspace temporal; rutas web y API esperan `asyncio.to_thread`. | No hay claim, lease, número de intento/fencing, presupuesto global de CPU o admisión de pendientes. El lock local no coordina otros procesos. |
| Datos de cálculo | `plan_generation.py:54` relee Cliente y branding, y `:126` crea un catálogo inmutable durante esa ejecución. | Inmutabilidad durante una llamada no equivale a snapshot durable entre reinicios. Una repetición puede observar otro perfil o catálogo. |
| Bytes R07 | `private_objects.py:27` confirma intento pending antes del PUT; `:47` une ready y referencia del consumidor en una transacción. | Un PUT ambiguo deja pending con o sin bytes. El intento no tiene FK a reserva/job; no se puede asociar por proximidad temporal ni publicar/borrar automáticamente. |
| Notificación | `planes.py:88` registra `BackgroundTasks` después de confirmar el resultado. `plan_notifications.py:12` autoriza lectura privada por tenant y devuelve bool. | La tarea vive en el proceso; no hay fila outbox ni estado de entrega durable. El retorno bool no se persiste. |
| Transporte correo | `email_service.py:40` devuelve False si falta configuración o hay error y True si `Emails.send` retorna. | No conserva identidad de mensaje/proveedor ni clave de idempotencia. True no demuestra entrega al buzón. |

Referencias de esta tabla son rutas bajo `web/services`, `web/database` y `web/routes` respectivamente; las huellas fijan el contenido si cambian las líneas.

## Ventanas de fallo y recuperación pendiente

| Interrupción | Lo que permanece | Acción segura pendiente |
| --- | --- | --- |
| Antes de confirmar reserva | Ningún crédito nuevo confirmado en ese intento. | Reintento con la misma clave bajo la transacción de reserva. |
| Después de reservar, antes/durante CPU | Reserva consume cuota; puede faltar todo resultado. El workspace temporal no es una cola durable. | Distinguir trabajo vivo de abandonado mediante claim/fencing; no liberar por antigüedad sin impedir una publicación tardía. |
| Después de confirmar pending, antes/durante PUT | Intento de objeto durable; bytes pueden existir aunque el cliente vea error. | Verificar destino, identidad, tamaño y hash del intento. Registrar resolución sin inventar vínculo a reserva. No hacer fallback de backend. |
| Después de PUT, antes del commit Plan/ready | Objeto pending y posiblemente bytes; rollback evita referencia y contador del Plan. | Clasificar huérfano comprobable; ninguna eliminación automática o TTL ha sido aprobado. |
| Después del commit Plan/marcador, antes de completar respuesta | Plan/objeto ready y `persisted_at`; reserva puede seguir `reserved`. | Consultar historia; no volver a renderizar ni reembolsar. Para replay exacto futuro, persistir respuesta canónica con Plan y marcador. |
| Después de completar, antes de entregar HTTP | B2B conserva `result_json`. | La misma clave/huella devuelve el resultado. La UI conserva la intención para este reintento. |
| Después de confirmar Plan, antes de iniciar correo | Plan existe; puede no existir ningún intento de notificación. | Un outbox en la misma transacción elimina la pérdida de intención. |
| Proveedor aceptó correo, proceso murió antes de guardar éxito | Hoy no hay registro local de envío. | Idempotencia verificable del proveedor o estado ambiguo/manual; un reintento ciego puede duplicar el correo. |

La prueba `integration_gym_recovery_review_postgres.py:112` mata un **proceso sintético** con `os._exit(23)` después del commit real del Plan, y comprueba que ni compensación ni eliminación posterior del Plan devuelven crédito B2B. No prueba recuperación automática, snapshot, fencing, reinicio de contenedor ni entrega de correo.

También existen pruebas de último crédito entre procesos, replay exacto/conflicto DTO, compensación repetida, cambio de periodo y frontera DB/PUT: `integration_gym_caps_http_postgres.py`, `integration_gym_recovery_review_postgres.py`, `test_private_objects.py` e `integration_private_objects_review_postgres.py`. Esta revisión no las volvió a ejecutar. Las pruebas de R07 usan almacenamiento local/dobles; no equivalen a un proveedor remoto real.

## Brecha individual que bloquea reintento automático

`usuario.py:315` reserva el crédito individual, pero `:333` invoca el worker sin identidad de esa reserva. `GenerationReservation` (`models.py:744`) tiene `plan_id` y estado, pero no marcador durable de publicación ni huella de entrada. `repository.py:243` sólo vincula atómicamente `GymGenerationReservation` cuando recibe `reservation_id` B2B.

Si el worker confirma un Plan y después falla antes de devolver su resultado —por ejemplo al salir del workspace temporal o durante un commit de resultado incierto—, el `except` de `usuario.py:340`/`:343` llama `finish_generation(..., success=False)`. `generation_quota.py:68` devuelve crédito y marca released sin comprobar una publicación vinculada. Si el proceso muere en ese intervalo, queda reserved sin enlace al Plan. Son riesgos deducidos de la secuencia de commits; no se ejecutó todavía la reproducción dirigida.

Contención revisable para el siguiente lote: identidad de reserva individual explícita en el worker; vínculo Plan/marcador/estado de cuota en una sola transacción, conservado aunque se quite la referencia al Plan; compensación que verifica ese marcador bajo lock de cuenta; captura del ID antes de trabajo; manejo protegido de rollback/compensación inciertos; respuesta de reconciliación estable. No reutilizar el parámetro B2B contra la tabla individual por coincidencia de nombre.

Aceptación mínima: fallo real después del commit Plan y antes de `finish_generation`, muerte de proceso en esa ventana, error de commit cuyo resultado sea incierto, dos procesos en último crédito y compensación repetida tras cambio de mes/eliminación de Plan. En todos: un Plan publicado conserva exactamente un consumo; un fallo confirmado sin publicación se devuelve una vez; incertidumbre queda visible y no concede trabajo adicional.

## Contrato mínimo para un job durable

Propuesta de contrato, sin esquema o código implementados:

1. **Crear** reserva y job en una transacción de cuenta, con clave única por sujeto/contexto y huella de entrada. El broker, si se incorpora, sólo despierta al consumidor; la DB conserva intención y resultado. Un envío duplicado no crea otro crédito/job.
2. **Congelar** entradas autorizadas: perfil nutricional y exclusiones validados, DTO, periodo/cuota capturados, catálogo y versión de reglas/generador, parámetros de variación/seed y descriptor de branding. Persistir solamente los datos sensibles necesarios y controlar su acceso; ningún snapshot entra en logs. Un retry no toma el perfil actual por conveniencia. Las semillas actuales dependen del cliente y `plan_numero`; cambiar sus entradas o algoritmo cambia la salida.
3. **Reclamar** por transacción corta con CAS y token de intento monotónico. Registrar dueño de ejecución y lease técnica renovable con reloj DB. Su duración se calibra con métricas; no representa vigencia comercial ni retención. No mantener locks DB durante render/PUT.
4. **Publicar** solamente si siguen vigentes token, estado y tenant. Plan, objeto ready, marcador de consumo, resultado canónico y evento outbox se confirman juntos. Un worker con lease vencida no puede publicar después de otro intento. `unique(reservation_id)`/CAS conserva un único resultado. El objeto pending debe vincularse de forma explícita al job/intento antes del PUT.
5. **Recuperar** por evidencia: marcador publicado ⇒ replay; ejecución confirmada fallida y sin marcador ⇒ liberación única bajo lock; lease vencida ⇒ invalidar/fencear intento anterior antes de reclamar; PUT/commit ambiguos ⇒ reconciliar integridad y asociación o revisión, nunca reembolso ni borrado por timeout. No reintentar un error clínico/de validación como si fuese transporte transitorio.
6. **Notificar** mediante outbox con identidad única evento/canal/destino, plantilla y descriptor del documento, intentos, próximo intento técnico, estado y referencia del proveedor. Usar identidad de destinatario autorizada al producir el evento; los cambios/revocaciones posteriores requieren una política explícita. No prometer exactamente una entrega si el proveedor no permite resolver una aceptación ambigua. Un enlace autenticado evita copiar claves/rutas/credenciales al mensaje; el adjunto actual requiere revisión de consentimiento/límites del proveedor.
7. **Exponer** estado autorizado y acotado en UI: recibido, ejecutándose, listo, fallo definitivo o revisión. Cambiar de cuenta descarta intención local; una clave no autoriza acceso al estado ajeno. Métricas usan estado/clase técnica sin correo, notas, catálogo de exclusiones ni texto de excepción.

Antes de activar este contrato: matriz de caída antes/después de cada commit y PUT; dos workers reclaman el mismo job; lease perdida con worker antiguo todavía vivo; replay tras reinicio; rollover de periodo; borrado de referencia; dos tenants y conexión reutilizada; fallo/aceptación ambigua de correo. Las pruebas deben observar DB, bytes y llamadas efectivas al transporte, no sólo mocks de estado.

## R34: medición que falta para decidir el cambio de ejecución

No existe medición nueva de p95, concurrencia o cola en esta revisión. El comentario `~5–15 seg` de una ruta no es un benchmark ni un objetivo acordado.

Preparar un entorno sintético aislado con el candidato y roles app/migrador separados. Medir por flujo: validación/reserva y espera del lock; cálculo por tipo de plan y exclusiones; render; PUT/lectura; commit; tiempo total; cola/admisión; CPU/RSS; conexiones y esperas DB; clases de fallo y reservas pendientes. Separar arranque frío y caliente, API/HTML, un cliente caliente y varios tenants. Registrar versión, catálogo/inputs sintéticos, concurrencia, número de muestras y p50/p95/máximo; no extrapolar datos Windows a un contenedor Linux aún no ejecutado.

Los tamaños de carga y límites de latencia/cola requieren una demanda y objetivos acordados. Usar una rampa acotada y detenerla por presupuesto técnico del entorno; no iniciar carga sobre producción. Desacoplar CPU si la medición evidencia saturación/espera o si el producto exige continuar tras desconexión/reinicio. La necesidad de reconciliar commits ambiguos y no perder intención de correo ya está identificada, independientemente del throughput. Comparar primero un consumidor DB acotado con un broker sólo cuando haya una necesidad demostrada de entrega, reparto o escala.

## Limpieza legacy: unidades, tabla y operación

| Hallazgo | Evidencia exacta | Propuesta revisable |
| --- | --- | --- |
| Tipo incorrecto al limpiar refresh | `RefreshToken.expires_at` es Float (`models.py:159`). Auth escribe/compara epoch (`auth.py:392`, `:479`, `:617`). El script construye datetime aware (`cleanup_expired_tokens.py:49`) y lo pasa sin `.timestamp()` al SQL sin tipo (`:62`, `:75`). | Usar corte epoch explícito compatible con Float y reloj inyectable. Verificar PostgreSQL y SQLite con valores anteriores/iguales/posteriores; no ejecutar el borrado legacy para diagnosticarlo. |
| La tabla audit **sí coincide** | Script `:110`/`:123`, modelo `models.py:628`, migración `20260326_1101_add_auth_audit_log_table.py:23` y fixture R07 usan `auth_audit_log`. | No renombrar tabla ni crear alias. La sospecha singular/plural queda descartada para estas fuentes. |
| Comparación audit sin binder UTC | `cleanup_old_audit_logs` pasa datetime aware a `text()` (`:101`, `:114`, `:127`); el modelo usa `UTCDateTime` sobre TIMESTAMP sin zona (`models.py:638`). | Expresión tipada del modelo o corte UTC-naive explícito. Reproducir equivalencia UTC/México antes de cambiar; esta revisión no ejecutó el caso y no atribuye un desfase observado a este script. |
| Fallo indistinguible de cero filas | Ambos helpers capturan Exception, imprimen texto/traza y devuelven 0 (`:83`, `:135`); `main` imprime COMPLETED (`:160`) sin salida de error. | Resultado/exit status de fallo distinto de cero, log de clase/código sin parámetros SQL, conteo y métricas seguras; un timeout no equivale a cero eliminados. |
| Dos políticas existentes distintas | Script `main` aplica 30 días a tokens y 90 a auditoría (`:153`, `:156`); `web.auth._cleanup_expired_refresh_tokens` (`:609`) elimina expirados o revocados inmediatamente y se llama al inicio/cada seis horas por worker web (`main_web.py:114`, `:120`). | Inventariar qué runner se usa realmente y elegir autoridad de limpieza/política con privacidad. No inferir aprobación comercial/legal de esos defaults, ni cambiar retención o borrar históricos en este lote. |

El comentario cron del script es una instrucción de ejemplo, no evidencia de scheduler desplegado. La tarea periódica web está ligada a cada proceso; no se observó ejecución equivalente en la fábrica API. Un futuro runner debe tener privilegio mínimo, lotes acotados y observación de éxito/fallo; elegirlo y activar retención es una decisión separada de corregir unidades.

### Contrato de prueba del corte temporal de cleanup

Preparar el mismo conjunto de datos sintéticos en una SQLite temporal y una base PostgreSQL desechable creada por el fixture migrador, con conexiones de aplicación aisladas y sin cargar `.env`. No conectar producción ni ejecutar `main()` contra un destino heredado. Fijar un instante aware mediante reloj sustituido en el módulo; conservar el argumento/default temporal existente del helper que se prueba.

Para `cleanup_expired_tokens(days_to_keep=30)`, sea `cutoff_epoch = (now_utc - 30 días).timestamp()`. Crear sujetos y JTIs sintéticos y comprobar **los IDs que permanecen**, además del conteo:

| Registro | expires_at Float | revoked | Resultado que conserva la política del script |
| --- | --- | --- | --- |
| Expirado anterior al corte | corte − 1 segundo | False | Eliminado |
| En la frontera | corte exacto | False | Conservado: el predicado actual es `<` |
| Expirado reciente | now − 1 segundo | False | Conservado: sigue dentro de los 30 días del script |
| Activo | now + 1 día | False | Conservado |
| Revocado activo | now + 1 día | True | Conservado: este script no tiene predicado revoked |
| Revocado anterior al corte | corte − 1 segundo | True | Eliminado por fecha |

Antes de corregir, la prueba exige dos eliminaciones y cuatro IDs concretos conservados. Debe registrar el fallo observado sin imprimir valores reales: un bind datetime frente a Float puede fallar en PostgreSQL; en SQLite puede comparar tipos de forma distinta y eliminar de más. Este documento no ejecutó esos casos ni atribuye un incidente productivo. Después de corregir sólo la unidad del corte, el mismo contrato debe pasar con corte epoch UTC Float en ambos motores, sin alterar el significado de revoked ni los defaults de 30/90 días.

Casos complementarios: segunda ejecución devuelve cero sin alterar supervivientes; conjunto sin candidatos; dos relojes aware UTC/México que representan el mismo instante producen exactamente los mismos IDs; error de conexión/ejecución no se informa como limpieza exitosa. El flujo `web.auth.cleanup_expired_tokens` se prueba aparte con su política actual de expirado **o** revocado; no unificar ambos contratos al corregir esta unidad.

Para `cleanup_old_audit_logs(days_to_keep=90)`, usar tres filas con `created_at` UTC-naive antes/en/después del corte existente, verificar sólo la anterior eliminada en ambas zonas de sesión PostgreSQL y en SQLite, y confirmar el nombre `auth_audit_log` en el esquema migrado. El resultado debe fijarse antes de proponer binder tipado o corte UTC-naive; no cambiar retención ni habilitar scheduler durante esta prueba.

## Entrega y límites

Se entregan únicamente este documento y su evidencia estática. No se modificaron producto, modelos, pruebas, CI, registro de auditoría ni despliegue. Prioridad propuesta para el siguiente lote: contener la publicación/cuota individual; definir reconciliación y outbox; medir R34; decidir después consumidor/broker y operación. Toda nueva migración conserva las reservas y objetos ambiguos existentes para revisión explícita.

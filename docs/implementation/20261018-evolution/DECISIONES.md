# Decisiones de ejecución

## Acceso Google con código de correo — 30 de octubre

La instrucción expresa del usuario pide acceso con Google para todas las personas y un código enviado al correo de quien entra. Se implementa el orden Google verificado → código de correo de un uso → autenticador personal, si está activado → sesión. La verificación por correo no sustituye el MFA personal existente. El inicio no crea cuentas ni emite tokens; la confirmación consume el código antes de resolver la cuenta.

Para cuentas anteriores sin ninguna asociación Google, la prueba conjunta de Google y del buzón permite autenticar la cuenta existente del mismo correo. Esta continuidad no reconstruye ni guarda un `sub` histórico, no fusiona cuentas y conserva datos, roles y factores. Una asociación Google activa o revocada impide usar esta vía de continuidad. Las asociaciones existentes se resuelven por issuer/sub; sólo las altas nuevas crean una asociación nueva.

Redis conserva durante diez minutos una instantánea autenticada y un HMAC del código; cinco intentos incorrectos lo invalidan y el consumo es atómico. Los cambios de cuenta, versión de sesión o asociación invalidan la instantánea. Los códigos y credenciales Google no se escriben en logs ni en almacenamiento del navegador.

El envío requiere `RESEND_API_KEY` y un `RESEND_FROM_EMAIL` permitido por el proveedor; no se inventan credenciales ni se omite el código si falta el envío. La preparación se mantiene en una rama separada hasta disponer de envío real. No requiere migración de esquema ni modifica desktop o los cupos Free.

## Decisiones del 29 de octubre: fuente 80ccb8b5

La fuente de validación funcional FULL es `759e5639bc462ba5079fdfb0ba8636907ec94a6c`; el tooling CI actual es `80ccb8b512b03bc8a1d68b9386a21d9818d6f73b`. El delta de CI añade cuatro rutas de pruebas/herramientas y cambia un solo entrypoint del workflow. No modifica los 509 APP, las 339 fuentes de callers o los 369 bindings. Las suites amplias congeladas y el contexto offline conservan su fuente `759e5639`; sus resultados no se reatribuyen a `80ccb8b5`. El cambio acotado se valida con su transferencia específica y escaneo actual, sin repetir las suites funcionales intactas por ese delta de CI.

Mantener la ejecución exclusivamente web y la revisión por archivos, con coordinación, autor y peers independientes. Conservar los 167 requisitos y las autoridades 37/33/RAW, sus rechazos y sus fuentes; no heredar la aprobación Bandit22 a los 26 avisos actuales ni convertir controles de transporte en aceptación de producto.

Conservar el multiset exacto de seis ocurrencias de baseline, los dos universos de fuente completos, los dos multisets de 26 avisos y únicamente cuatro anclas CPython 3.11. Mantener opacos los dos fixtures hasheados y fijar LF para el matcher que autentica sus propios bytes. Los comentarios posteriores se transportan mediante igualdad AST/CodeType, con recibos nuevos y sin reetiquetar pruebas anteriores.

La instrucción del 29 de octubre a las 17:15 UTC difirió Linux y se conserva como antecedente, junto con el rechazo previo por RAM. La instrucción posterior del usuario autoriza el push Git y el build/despliegue remoto en Railway; su ejecución y validación siguen pendientes. La VM Linux local continúa sin autorización. Este permiso no sustituye la validación, el respaldo consistente ni el restore ensayado exigidos antes de intervenir datos productivos; no acredita PASS Linux, aceptación global o despliegue.

Transferencia final de calidad en Main: 106 PASS, 0 fallos, 0 errores y 0 skips principales sobre `759e5639bc462ba5079fdfb0ba8636907ec94a6c`. La fase no equivale a aprobación global de CI o release. Suite final serial: 6706 PASS, 0 fallos, 0 errores y 1 skips principales; el skip de plataforma Windows se conserva y se declara, sin afirmar cero skips; la fase está rechazada y requiere corrección y nueva validación sobre `759e5639bc462ba5079fdfb0ba8636907ec94a6c`. La fase no equivale a aprobación global de CI o release. Suite final n2 con seed 20261018: 6706 PASS, 0 fallos, 0 errores y 1 skips principales; el skip de plataforma Windows se conserva y se declara, sin afirmar cero skips; la fase está rechazada y requiere corrección y nueva validación sobre `759e5639bc462ba5079fdfb0ba8636907ec94a6c`. La fase no equivale a aprobación global de CI o release. Escaneo final completo de secretos, con otro nonce posterior a Broad y al texto documental final: cerrado sobre `80ccb8b512b03bc8a1d68b9386a21d9818d6f73b`, con 54216 hallazgos brutos, 54216 clasificados y 0 pendientes; salida efectiva 0. Esta fase no sustituye otro nonce final ni acepta release. Se mantiene el skip de plataforma Windows y se informarán por separado sus límites. Staging/configuración/rollback, custodia y retención, proveedores, datos del aviso de México, revisión jurídica/nutricional y participación real en piloto continúan pendientes. No se completan con valores supuestos ni se cambia el alcance de privacidad. También siguen pendientes cierre/purga integral de cuentas y acceso de soporte acotado (R31), y procedencia/separación de demo y cohortes (R22/R30), sujetos a política/decisiones vigentes. [Preparación y evidencia por fuente](PREPARACION_PRODUCCION_20261029.md). Estas decisiones no autorizan publicación o mutaciones productivas.

<!-- DOC166-CLOSED61-FOLLOWUP -->

## Seguimiento del checkpoint 166 — SQLite39 final aceptado; restore PG rechazado

SQLite39 final cerró normalmente con 61/61 PASS, cero fallos, errores o skips, sobre Source1557 9b3160df3820c8fd75137b8c5edfe7ccfec5cf2100a6f14fd68005ce57e6a328. Colección y JUnit exactos; fuente, 92 paquetes y binarios quietos, pip0/0. Este resultado no reemplaza los anteriores 52(38PASS/14F), 57(56PASS/1F) y 61(57PASS/4F), preservados con sus fuentes.

Restore PG38/527 superó estructura y falló después en tenant_security. Root comunica ambas UUID cerradas sin sesiones; sólo se lee el resultado cerrado, no logs. Comparador puro56 y SQLite61 no acreditan la restauración de PostgreSQL, seguridad global o integración Main; el diagnóstico de políticas es separado.

Root conserva también el rechazo precopia733f: 2258 SHA/tamaños exactos, diferencias sólo en atime de lectura y ningún root/output/Git creado. Su hijo finito es trabajo independiente de Root;733f queda sellado.

Se mantienen167 filas, los166 criterios y estados anteriores,92IDs originales,66verificados ySEC26 en_revision. R22/R30/R31/R34 son obligatorios;R28/R35 son condicionales conforme sus criterios. [Resumen166](evidence/checkpoint166-web-continuity-20261023/summary.json) y[matriz](evidence/checkpoint166-web-continuity-20261023/matrix.md).


<!-- DOC166-SOURCE-SCOPED-SEC26-IN-REVIEW -->

## Checkpoint 166 — corte documental preparado en E

167 filas: los 166 criterios/estados E165 y92IDs originales se conservan; sólo se añade SEC26 en revisión, con66verificados locales sin cambio. Sus46SQLite/25Node/23PG y14llamadas directas están ligados a fuentes propias.108SQLite/core38PG9/password23 son alcances focales; Node histórico mantiene atribución. Privacy52(38P/14F),57(56P/1F),61(57P/4F),shells8PASS1554,Node48offlinePASS1550 ypure56PASS permanecen separados. PG38restore89867 seguía en curso al mensajeRoot: sin lectura de logs ni aceptación anticipada.

R22/R30/R31/R34 siguen obligatorios; R28/R35 son condicionales conforme sus criterios. Main39/CIglobal/Linux/imagen/Redis/R34/proveedor/piloto/legal14/custodia siguen abiertos. Originales fallidos preservados, no nuevoSEC27 ni cierre por harness. [Resumen166](evidence/checkpoint166-web-continuity-20261023/summary.json) y[matriz](evidence/checkpoint166-web-continuity-20261023/matrix.md).


<!-- DOC165-LOCAL-BACKUP-ACCEPTED-SERIAL-OPEN -->

## Checkpoint165 — respaldo sintético y límites

Kit backup actual96617 aceptado en878,intento7c46/wrapperb828:2UUIDsecuenciales/3procesos independientes,cierresnormales yentornoquieto. R08_global_complete=False permanece literal; no cambia ningún criterio/estado ni valida custodia/retención real. Intento350a(wrapper32e) y fallos previos se preservan. Serial98362 está en curso,sin resultado al corte. PG/Native siguen dc9f y sevenread878 conserva su cierre distinto. [Resumen165](evidence/checkpoint165-web-continuity-20261023/summary.json) y [matriz](evidence/checkpoint165-web-continuity-20261023/matrix.md).


<!-- DOC164-ACTUAL-SEVENREAD-CLOSED -->

## Checkpoint164 — cierre acotado de sevenread

Sevenread18773 aceptado en878:14ventanas/1400respuestas200/0fallos semánticos/0observermissing;1UUID yserver propios cerrados,entornoquieto. PG509/Native35 siguen dc9f; la relación de fuentes no los relabela ni repite. No cambia ningún estado ni criterio;R05 espera broad y backup sigue sin resultado aceptado. Los rechazos históricos y el intento backup bootstrap fallido se conservan. [Resumen164](evidence/checkpoint164-web-continuity-20261023/summary.json) y [matriz](evidence/checkpoint164-web-continuity-20261023/matrix.md).


<!-- DOC163-SOURCE-SCOPED-CLOSED-GATES -->

## Checkpoint163 — una relación de fuente no es un replay

Root acepta reutilización operativa acotada del cierre Native35 dc9f únicamente tras probar que878 tiene ese único padre y la única ruta/carácter codec. Los recibos conservan sus source originales; el wrapper de backup exige cierre de carga actual y relación canónica coincidente antes de clave/prepare/ACK. La preparación del wrapper no acredita backup. QA-33 cambia sólo tras fullscan vigente completo; R05 espera broad. [Resumen163](evidence/checkpoint163-web-continuity-20261023/summary.json) y [matriz](evidence/checkpoint163-web-continuity-20261023/matrix.md).


<!-- DOC162-CLOSED-SOURCE-OBSERVATIONS -->

## Checkpoint162 — límites de la barrera común

Se aplica una sola barrera reusable a los ocho adapters actuales de PG509. La admisión y revalidación fijan generación, OID y owner; los callbacks no consultan SQL y se limitan a DSN loopback/rol/UUID y lifetimes observados. La ventana Root exclusiva sin restart es un requisito externo explícito. Un Engine.dispose histórico con préstamo no se prohíbe si la devolución posterior está demostrada; la barrera actual exige ledger completo, DBAPI cerrado y pools coherentes, sin inferir cierre del counter reiniciado.

No se atribuye causa histórica al focal verde ni se altera un recibo created original por una limpieza posterior. Native/load y subprocessos de backup conservan fronteras propias. [Resumen162](evidence/checkpoint162-web-continuity-20261023/summary.json) y [matriz](evidence/checkpoint162-web-continuity-20261023/matrix.md).


1. Trabajar sobre clon aislado y preservar original sin Git. Commit base cotejado por contenido; no se inventa historial.
2. Mantener FastAPI/Jinja/SQLAlchemy y compatibilidad de consumidores existentes mediante parámetros opcionales. No migrar de framework.
3. Pro sólo procede de un estado del proveedor verificado y reconciliado. Un redirect o preferencia nunca concede derechos. No fijar periodos de gracia ni precios nuevos sin decisión comercial.
4. Las exclusiones explícitas se aplican a todos los planes comerciales. El catálogo de generación se copia y congela por solicitud, se pasa explícitamente a los selectores, y se valida el resultado antes de PDF/persistencia. Las notas libres no constituyen reglas clínicas.
5. Decisiones explícitas del usuario: Free permite 10 clientes, un plan por cliente al día y diez planes totales al día por gimnasio; desktop continúa soportado. Los tres límites se comparten entre web/desktop. Se aclararon por separado las dimensiones cliente y total gym antes de cambiar cuotas. Corregir tests inseguros exige evidencia del contrato; no se alteran expectativas para ocultar discrepancias.
6. Revocación: nueva versión de sesión persistida y lookup de estado/rol/team. Compatibilidad temporal para tokens previos documentada; ninguna rotación o cierre live en esta ejecución.
7. RLS se activa sólo después de reconciliar esquema y demostrar contexto en cada transacción con rol restringido en PostgreSQL aislado.
8. R04 usa credenciales diferentes para migrador y aplicación; startup rechaza SUPER/BYPASS/propiedad DDL. Las asociaciones de proveedor sin intención de compra verificable no conceden derechos por coincidencia de correo. [Contrato](AISLAMIENTO.md).
9. La cuota profesional se reserva antes de CPU bajo lock de cuenta y conserva su fecha/mes local. Un plan confirmado nunca devuelve crédito por perder la respuesta o por quedar NULL su FK; la marca `persisted_at` se guarda con el plan. No se libera una reserva ambigua sólo por antigüedad. [Contrato en revisión](B2B_CUOTAS.md).
10. El esquema histórico sin zona recibe un binder explícito UTC, con32 pruebas independientes. Los resultados naive existentes se preservan; el helper no deduce su origen ni repara desplazamientos antiguos. Las dos fechas civiles de membresía del cliente quedan fuera de la adopción hasta definir su semántica. [Contrato](UTC_DATETIME.md).
11. R07 usa metadatos privados e inmutables y configuración explícita. Un fallo de proveedor no selecciona otro destino. No hay limpieza automática de huérfanos ni borrado de objetos por CASCADE antes de contar con un workflow revisado de conservación/borrado. El destino operativo sigue pendiente; no se aprovisionaron recursos. [Alcance](ALMACENAMIENTO.md).
12. La exportación R31 de un propietario no convierte su cartera profesional en datos del espacio personal. La paginación es una lectura viva y las partes deben declarar su alcance; no se promete un snapshot transaccional entre peticiones. Exportación técnica y revisión legal son comprobaciones separadas. [Inventario en revisión](PRIVACIDAD.md).

Pendientes de decisión externa: gracia/reembolsos/impuestos; retención/borrado de copias; proveedor/infraestructura con coste; política clínica y dictamen profesional; participantes de piloto. Los límites Free ya están resueltos. El silencio no autoriza cambios de derechos ni gastos.

13. La identidad de una operación HTTP se captura antes del envío y sigue vigente durante refresh, reintento y lectura. Un cambio de cuenta invalida la operación anterior sin escribir ni borrar tokens de la sesión nueva. La rotación propia y los401 concurrentes requieren una promesa compartida con resolución de todos los consumidores; SEC02 sigue en corrección.
14. La evaluación estática R28/R34 mantiene HTTP hasta medir carga. Reconciliación/outbox requieren persistencia y evidencia; no se concede reembolso ni se elimina pending por antigüedad. El posible defecto individual postcommit tiene prioridad de contención sobre diario persistido. Un eventual DDL26 para esa contención desplaza el número propuesto del diario; no se modifica una migración histórica. [Evaluación](JOBS_EVALUACION.md).

15. Publicación individual usa protocolo1 y marcador UTC de esquema26; filas previas conservan protocolo0 y no se vinculan por semejanza o fecha. La reserva captura el mes persistido de suscripción y el lector exige doble dueño/filas no borradas. Drenar todos los workers antiguos antes de migrar/reabrir generación; ninguna compatibilidad de procesos vivos se presume. [Contrato](CUOTA_INDIVIDUAL.md).
16. La contención de sesión API347 bloquea toda autenticación I/O de una instancia tras escritura/lectura Storage incierta hasta save/clear completo. Es un alcance local probado, no decisión de conservar tokens persistentes ni solución de coordinación entre pestañas. [Sesiones](SESIONES_HTTP.md).
17. Desktop debe construirse como GUI PySide onedir y validar el ZIP completo con _internal/recursos/manifiesto sobre un commit limpio exacto. Las pruebas de receta no sustituyen build/GUI/instalador/upgrade. Usar HOME y METODOBASE_DATA_DIR temporales para no modificar datos del usuario. [Inventario](DESKTOP_PUBLICACION.md).
18. El tipo legado no acredita que una cartera de rolOWNER pertenezca al espacio personal. La ampliación propuesta por coordinación se revocó al fallar el control independiente conservado; R14 admite personal noOWNER/miembroválido y mantiene el caso ambiguo para asociación explícita R02/R12. No modificar roles/pruebas ni adoptar historia por cantidad/email/suscripción. Las rutas y derechos de generación anteriores quedan fuera de este lote.

Checkpoint107: selladas la revisión independiente desktop66 (93 controles verdes, payload1215 exacto, Python3.12.15/OpenSSL3.5.9/Expat2.8.5/Qt6.8.3; sin ejecutar Setup) y las revisiones R12V1/V2. QA95 de V1 no cerró sus tres fallos de seguridad; V2 1aac pasó los mismos21 criterios independientes, sin cambiar el driver. Fuentes y paquetes estables; bases propias cerradas. Aceptación limitada al coreV2, sin casts/restore/API ni integración29. Los RAW y manifiestos originales permanecen exactos y se añaden atributos binarios sólo a estas nuevas carpetas para conservarlos en Git.


## Checkpoint 108

Checkpoint108 mantiene esquema28MAIN hasta cerrar composición29 y después30. Se acepta30 sólo en alcance índice/lector/migración120, sin SLO. Se acepta seguridadAPI939 sólo en alcance41+26; no sustituyeQA deUI/restore. SEC09 exige evaluar/corregir el ELF efectivo, separado deOS/PyPI. El falloCREATEROLE se corregirá en producto; no se precreará rol ni ampliará el migrador para ocultarlo. Se preserva soporte desktop y decisiones comercialesFree ya respondidas.


## Checkpoint 109

Se integra únicamenteelc4aceptado13, sin ampliar privilegios ni precrearrolglobal. Se rechaza aceptaciónR12completa peseaAPI/restoreverdes porfalloUIrealcriterio8. Fixec029debe superar mismos16+3 yrevisiónSEC;scopeexplicito decontroles, no main. Elhistórico28enCI correconfuenteGit66fijada, sin editaraserciones/modelofalso. Node297son ejecuciones y276criteriosúnicos,21exportrepetidas.


## Checkpoint 110

Se acepta el recorrido R12ec dentro de su alcance independiente, manteniendo integración condicionada a CI29 correcto. El emisor e8 permanece aislado hasta corregir los mismos tres negativos de Seguridad. Se mantienen separados evidencia estática de contenedor, build real, linkage, firmaAPT y SCA; incluir entorno build y componentes vendorizados en su análisis.


## Checkpoint 111

Integrar29/CI aceptado preservando su commit real como ancestor para archivar el runtime histórico sin falsear markers. Conservar restore29 exacto bajo30 y añadir restore30 en lugar de reemplazar assertions. Evidencia RAW no se normaliza; fuente/prosa usa representación Git LF documentada.


## Checkpoint 112

MFA31 reservado exclusivamente a backend; sin migraciones paralelas. R24 usa borrador de compra explícito en RAM, cantidades reales y consumo confirmado como hecho personal mínimo; no define plazo nuevo de conservación ni publica diario al gimnasio. Menús/sustituciones ambiguos no generan cantidades o recomendaciones ficticias. Contratos en trabajo aislado, no aceptación completa R24/R32.


## Checkpoint 113

No repetir amplia30 ya verde sin cambios de fuente relevantes. Conservar el control768 rojo y validar corrección con addon idéntico. Registro de consumo evita doble escritura antes de await y conserva CAS real; contratos R24/MFA31 aún en validación, sin nuevas políticas comerciales o de retención.


## Checkpoint 114

Conservar la política de retención pendiente y separar retención de uso R30 de conservación personal R31. No imponer política de caché como bloqueo de un acceso online sin nueva caché; la implementación PWA sigue condicionada a beneficio medido. Validar entradas del portal antes de resiliencia/proveedor. Los recibos de procesos exigen PID+nacimiento+perfil y generación del padre, nunca ParentPID numérico aislado.


## Checkpoint 115

Se configura core.longpaths=true sólo en clon de ejecución propio para preservar rutas de prueba; workspace original no se modifica. Los RAW CRLF se autentican byte por byte y el check whitespace se limita a fuentes/documentos normalizables. No se repiten gates sin nueva preocupación ni se atribuyen a fuentes posteriores.


## Checkpoint 116

Integrar25fuentesR24 mediante patch exacto en commitnuevo, conservando commitsprivadosautor yevitando ancestry que contieneCSRFsintéticos. Proyecciónnueva sustituye sólo4valoresidentificadoscon hashesRAW/públicos; ZIPs fuente se inspeccionan porentrada. No debilitar filtro ni reescribir pruebas/manifiestos cerrados. Priorizar reparaciónSEC12 P1 antes dediagnósticoR34 P2.


## Checkpoint 117

CongelarMAINduranteamplia dio9542fuentes/89paquetes exactos. Registrar109criterios previos sincambio ynuevoSEC13. Preservar todoslos intentos deprobeheaders; corregirfixtures contraelcontratoreal deambospadres sin tocar producto ni10aserciones. CI31 usará fuente30 auténtica, no marcadores viejos fabricados desde modelos31.


## Checkpoint 118

Conservar separados los freezes56,440,913,087 yda343 y sus alcances. Los replays no se suman como casos nuevos. Los históricos se ejecutan con su fuente auténtica y current31 tendrá contratos propios. Se acepta documentar la nueva precedencia403 de MFA para recursos ajenos o inexistentes, preservando la opacidad, la denegación y las demás aserciones; no se modifica producto para eludir el control. Objetivos R34 consultados y pendientes.


## Checkpoint119

HistóricoCI31 cambia justificadamente deeea8postR24(3rojosinfrafixture) a57335e5aceptadoanteriorR24, ambos auténticosypreservados; current31pruebaR24conacompañantesreales. Conservar23helpersinmutables ytodoslos16callbacks. D60aceptaciónmetadatasólo para nueva compilación. LF/CRLF RAWsepreservansinreescritura.


## Checkpoint 120

No atribuir los quince grupos Chrome c669 a la corrección UX19 posterior. No sumar los veinte replays de QA como casos nuevos. Exigir snapshot25 en el CI actual y confirmación obligatoria de rol restringido en los marcadores; la revisión CLI continúa antes de PostgreSQL.


## Checkpoint 121

Los canarios offline no son PostgreSQL y los replays no son casos nuevos. Un target compilado no acredita procedencia vacía ni superficie ELF alterada. Preservar D60 rojo y de69 sin reconstruirlo para disfrazar resultados. DDL32 queda reservado a R25; el contrato no autoriza copiar diarios, inferir ingesta ni conclusiones clínicas.


## Checkpoint122

La aceptación focal R17 no equivale a métricas distribuidas ni SLO. Conservar before12rojos ysame-driver24after, separar replays. No actualizar pinsCI por una cautela sin evidencia: publicación_diary no está en source_modules del mapping; comprobar gate real tras integrar79.


## Checkpoint 123

No interpretar el GUCactor como firma verificable. R25 requiere un lector mínimo con autoridad derivada, consentimiento y locks; probar pool1/restauración y revisar antes de aceptar alternativa. Conservar entitlement profesional de clínica sin impedir medidas personales, retirada ni exportación por ese paywall. La aceptación estática del compilador no equivale a un artefacto nativo aceptado.


## Checkpoint124

No arreglar el fallo de recuperación cambiando suassert. Separar identidadválida de capacidad de incrementarSV. Conservar809rojo y repetir fullmatrix con fuente nueva y nombres distintos. Retiropropio es exclusión de permisos y admiteOWNERambiguo sólo sobre user_id persistido propio; no espacio personal ni cartera. Reactivación de vínculo revocado no adopta grants; togglecuenta sin retirar consentimiento no equivale a revocación.


## Checkpoint125

No debilitar assertions para corregir carreras de fixtures: congelar sólo setup, restaurar antes del negocio y preservar la firma original. No atribuir el error3047 a una carrera sin telemetría histórica suficiente. El DEFAULTFUNCTIONS del harness era redundante y alteraba proacl: retirar ese estímulo de la nueva prueba, no relajar el guard29→30. Aceptar header/CSS sólo con los mismos canarios y fuente345. Mantener login general inválido con padreOFF; retiro necesita un flujo limitado con pruebas frescas y sin JWT, todavía pendiente. Corrección de redacción CI:4grupos,5módulos/pins. El lease autor32 usa UUID, pero write_text inicial no demuestra creación exclusiva; no alterar ese sello ni repetir la afirmación.


## Checkpoint126

Precisión de autorización: el encargo permite las migraciones locales necesarias para resolver un hallazgo técnico. La restricción «sin nueva DDL» pertenece sólo al contrato de la retirada excepcional de esquema32. Una futura asociación de Google puede requerir una migración revisada; sus sujetos deben provenir de pruebas válidas de identidad. No se puede inventar un `sub` ni reconstruirlo desde un email.

No ampliar RLS ni alterar funciones para satisfacer asserts impropios del observador. Usar verify_runtime_schema congelado y allowlist25FORCE en el futuro worker. Preservar primererror/continuaciónreadonly con prefijos distintos del futuro sucesor. Apagar sólo VM propia por QMP tras cierre de servicios y fotos de identidad. No considerar contraseñas preparadas postrestore como restauradas. ContratoGoogle: separar autoridad criptográfica tokeninfo de asociaciónlocalpor email; no usar mocks imposibles como exploit real.


## Checkpoint127

Mantener alta Google nueva vacía por issuer/sub con contacto no verificado thirdparty/nohd, sin adopción por email ni derechos/perfiles implícitos. Email ya registrado exige vínculo explícito localfresh+MFA; desenlace explícito conserva historial y primaria local utilizable. No backfill de sub desde email. Probar causalidad con ocho casos originales tokeninfo antes de sustituir verificador; proveedor final con JWT firmado y fixtureJWKS sólo por transporte, sin mock de identidad. Nuevo entorno propio, no mutar WEB89 de evidencia. SEC18: invalidar sólo Session nueva si falla limpieza, no pool global.


## Checkpoint128

Integrar código local revisado con estado en revisión sin exigir despliegue o proveedor live para autorizar cambios reversibles. Preservar semántica exacta por hashes; no atribuir Chrome219 ni broads31 al nuevo árbol completo. CI31 es histórico hasta su evolución33; mantener fixtures/targets22–32 intactos y añadir actuales33. Clasificaciones de checksum siguen pendientes de revisión independiente; no introducir excepciones de directorio o normalizar RAW para ocultar findings.


## Checkpoint129

Componer fuentes33 antes deQA integrada yconservar el ancestry real de506 paraCI histórica. Aceptar R05v1 sólo en su alcance focal; el gate global sigue abierto. ParaR23 se aprueban dos tablas,permiso dedicado deNutri asignado yningún step-up nuevo para tareas ordinarias; loginMFA ygrants deequipo/cobro permanecen. El hash por causa excluye now/as_of. Un responsable no elegible no provoca lookup decontacto privado deotro contexto. La historiaRESTRICT no define retención legal ni cierra purgaR31. La imagen final espera fuente estable.

## Checkpoint130

QA-17 es clasificación de conflicto concurrente, sin adopción de cuenta ni credenciales al perdedor. Ampliar el catch a toda la escritura; no convertir rollback incierto en409 ni añadir reintentos. El triageR05 nuevo requiere peer antes de instalarv2.

## Checkpoint131

Aceptar solamente ubicaciones con revisión independiente finita. El resto permanece bloqueante; no ampliar por patrón ni confiar en Match/Secret/Line. Registro finito R05v2 integrado desde4f4ed7:689archivos/45.910pins, unión disjunta de534/31.394 anteriores y155/14.516 nuevos. SECf008 verifica14.557ocurrencias nuevas y113controles; QA verifica separadamente el binding exacto de tres literales. Autor110casos mantenidos PASS, Ruff/pip0 yfuente quieta. ZIPv1 yalgoritmo conservados. Escaneo real sobre4f4ed7:12.793archivos,44.433hallazgos brutos,42.830clasificados y1.603bloqueantes; salida1, sin aceptación global. Los archivos de evidencia posteriores no se reatribuyen al árbol escaneado. CI33 c86 ysu PG240 conservanv1 hasta composición explícita.

## Checkpoint133

Separar deriva de producto ydocumentación en el guardCI; escanear documentación completa conR05,sin excepción nueva por patrón. CI33 integrado conservando la cadena completa de c86 ysu delta original de82 fuentes desdeCOMMON3587. La composición con MAIN132/R05v2 modifica sólo el verifier respecto a c86:pinLF del módulo,pinRAW del ZIPc5eb ybase d8 explícitos; el guard de producto separa docs yel gateR05 sigue escaneándolos completos. QA110R05/49críticos PASS,9binding ycontroles de documento/3rechazos de producto,lock,target; verificador final193canarios workflow y157bloquesBash PASS,también replay ROOT enMAIN. Conserva20reportes/240IDs actuales33,5reportes/38IDs históricos32 ylos oráculos110/49. Offline902 yPG240 anteriores corresponden a c86/R05v1; no se reatribuyen aesta composición. No broad actual,Actions,Chrome,imagen oLinux aceptados por esta fase;R05global sigueRED.

## Checkpoint135

Decisión expresa del usuario al reanudar: «continua con todos estos cambios pero ya no trabajes en la version desktop, trabaja unicamente en la version de el servicio web». Desde este checkpoint el trabajo y la entrega se limitan al SaaS. Se detienen desarrollo, QA, empaquetado e instalador desktop. Código y evidencias previos se conservan; no se eliminan funciones existentes ni se integra el candidato Desktop35. QA confirmó que todavía no había ejecutado pruebas ni creado ramas o artefactos de esa revisión. Las validaciones Windows del servicio web y el núcleo compartido siguen dentro del alcance. Esta decisión sustituye la instrucción anterior de continuar el desarrollo desktop; no declara resueltos sus defectos.

## Checkpoint136

Mantener verificaciones antiguas en su fuente auténtica yusar composición35 explícita sin cambiar aserciones oNodeIDs. Preservar errores deharness yRAW, no ampliar pool ni cambiar expiración para ocultar la retención. El target34d1 sustituyea33 sólo porNOWAIT del trigger; a33 y22–33 permanecen históricos exactos. No verificación de email simulada enR31.

## Checkpoint137

La cookie refresh es autoridad sólo para renovar/cerrar, nunca recurso privado. El headerbrowser opt-in conserva APIlegacy; invalidOrigin no muta refreshcookie, CSRFcookie existente es independiente. Locks del navegador deben conservar intención capturada antes del primerawait y mantenerse duranteSetCookie/JSON. Añadidos36 decontacto yexenciónCSRF exacta requierenpeer/PG antes de aceptar. Continúa alcance sóloSaaS; no cambios desktop.

## Checkpoint139

La verificación focal local se separa de despliegue y cierre de tareas mayores. R31 conserva APIlegacy y se prueba con cookie/RAM; los tests que exigíanJWTStorage se mantienen históricos y se mapean a criterios actuales, sin simular credenciales enStorage. No basta cambiar comandosCI: preparar fixtures nativos y verificar el navegador real. LeasePG36 exclusivoBackend; Chrome todavía no concedido aQA.

## Checkpoint140

SEC19 sólo se cierra tras la repeticiónPG independiente ybinding exacto aMAIN. Conservar cada gate ligado a su commit;108export no son108casos únicos. Nuevos companions nativos sustituyen únicamente framing de sesión/esquema de forma explícita; originales permanecen históricos. No presentar compilación comoChrome ni aceptación del proveedor comoentrega. LeasePG exclusivoQA; sin leaseChrome todavía.

## Checkpoint141

La aceptación R31 actual se limita al gate HTTP integrado; el rechazo nativo se conserva y obliga reparar QA-27 antes de repetir. QA-26 identifica registro y QA-27 invalidación DOM; sus RAW nominales anteriores permanecen intactos. Notificaciones36 y cuenta37 siguen aislados. No se amplía la exclusión tenant por prefijo ni se reduce pageErrors. Sólo web.

## Checkpoint142

Separar diagnósticoChrome2 deaceptación15; conservar el rechazo previo. QA-26 ycuenta37 tienenpeer independiente SQLite, sinatribuirPGpeer ounaUIinexistente. V3delescáner amplíaúnicamenteubicaciones finitas yconservav2;26fuentesoriginalesnodisponiblesnoreconstruidas. NoDesktop nioperacioneslive.

## Checkpoint143

La rama principal local integra notificaciones36 y su UI27, la coherencia monetaria SEC25 y el aislamiento de tenant en rutas primarias QA-26. Los30 archivos de producto del merge a387 coinciden con la composicion revisada ab1b. El gate actual pasa78/78 casos HTTP reales sobre ambas factories API y SaaS; fuentes1268, Python,92 versiones instaladas y Node permanecen estables. La preparacion inicial selecciono un archivo inexistente: cero casos y exit4; su booleano de intencion no constituye ejecucion HTTP. Se conserva ese RAW separado.

QA repitio los15 grupos originales de navegador MFA sobre PostgreSQL35 y runtime exacto a MAIN2709:11 profesionales y4 personales, pageErrors=[],12 capturas y cero violaciones axe en el alcance comprobado. Una UUID cerro normalmente y los21 procesos propios cerraron con identidad comprobada; el pool nativo era5/0, sin atribucion pool1. La reparacion DOM QA-27 queda verificada localmente en esa fuente. El intento anterior rechazado y su diagnostico permanecen intactos. Los cambios posteriores36 tienen el gate HTTP separado; no se afirma navegador nativo36 o37. La superposicion movil del boton de menu sigue en UX-09/R13.

Cuenta37 sigue aislada. Seguridad confirma QA-28: tras un401 real de recurso, la UI conserva acceso en RAM o proyecciones de la cuenta. Se preservan seis HTTP RED y doce canarias VM RED, incluidos aliases de identidad/MFA. ROOT reprodujo los mismos fallos y prepara un cambio acotado al namespace de cuenta, con fence del actor capturado y sin refresh/retry; reautenticacion primaria incorrecta no implica retirar sesion. La revision independiente de esa correccion, PG peer, restore37, CI y navegador37 siguen en curso.

R05v3 ya esta integrado con125 casos actuales y146 de revision independiente. El nuevo escaneo real del arbol405 es RED:53203 alertas,42187 clasificadas por ubicaciones finitas y11016 pendientes en236 archivos. El resultado historico RED1603 se conserva; no representa el resultado actual. Seguridad preparo una propuesta de11015 puntos y dejo uno sin preimagen historica; ninguna ampliacion v4 esta aceptada o integrada. CI37 tiene solo preparacion estructural4353 NodeIDs,43 modulos480 casos afectados y30 controles; no CI global verde.

Se conservan los144 criterios anteriores y los92 originales; se agrega QA-28, total145. Los537 archivos untracked permanecen intactos. Free mantiene10 clientes,1 plan por cliente al dia y10 planes totales al dia por gimnasio, mensual20 sin cambio. El trabajo actual es exclusivamente del servicio web. Sin push, PR, despliegue, cobros o envios reales.

## Checkpoint144

La rama principal local ya integra cuenta y esquema37 sobre notificaciones36/UI27. Los27 archivos de producto coinciden con la composición revisada3c3; el wire37 y las primitivas MFA/R31 se conservan. QA-28 queda verificado localmente: un401 de recurso retira acceso RAM y proyecciones al recibir cabeceras, con fence de la identidad capturada. No refresca ni repite, no retira una sesiónB nueva y no afirma revocación global. Una contraseña primaria incorrecta y los errores403/422 siguen siendo corregibles. Seguridad independiente pasa48 casos propios (42VM y6HTTP) más10DOM del autor. ROOT conserva todos los RED originales y residuales.

Sobre la integración real1e01 pasan234 casos pytest mixtos: servicios, HTTP y migraciones SQLite; incluyen los replays R31 deliberados. No son234 casos HTTP ni criterios semánticos nuevos. Fuentes1315/Python/92 versiones instaladas/Node permanecen estables. La selección Node inicial pasa126; el companion18 no ejecuta aserciones por checkout CRLF distinto de su GitLF congelado. Un atributo de checkout exacto conserva ese blob y sus aserciones; después pasa18 en88ff. La página pública pasa8VM, comprobando ocho líneas PASS y su JSON final; el parser genérico que esperaba un único JSON quedó rechazado y preservado. Se aceptan152 resultados Node seleccionados repartidos en fases, sin sumarle las repeticiones. Se corrige también el encuadre de143: los78 casos de36 eran mixtos, no78HTTP.

QA PostgreSQL37 independiente pasa30 casos funcionales,12HTTP correctivos y un restore poblado. El alias del primer gate no comprobaba el pool real de doce HTTP; ese alcance se rechazó y la repetición corrigió sólo la composición del fixture. El primer restore falló porque su semilla pendiente sufría un reset histórico que incrementaSV; se conserva el fallo y sólo se cambió la semilla, manteniendo75 aserciones históricas y las nuevas. Ocho UUID cerraron porDROP normal, cero sesiones y ausencia fresca. Las fotos de1279 fuentes,92 distribuciones y8084 archivos instalados permanecieron estables. Este gate deQA está ligado a su fuente5806, con backend actual exacto; no constituye nueva ejecuciónPG desdeMAIN.

UX-09/R13 tiene16 reproducciones geométricas RED en Chrome con DOM inerte declarado y sin SQL. El autor congeló una reparación en tres CSS78aa, con4 contratos SSR antes/después y sin cambiar scripts o plantillas. QA prepara su replay y el navegador completo37:15 grupos R31 y18 nuevos, fixture actual y proveedores dobles declarados. Ese gate final todavía no empezó; no se atribuye a37 la aceptación nativa anterior de35.

R05 conserva el escaneo real405 RED11016. Seguridad propuso11015 ubicaciones y ROOT revisa su vinculación. Para la última ubicación se localizó el productor histórico exacto y la comprobación independiente original de los24 checksums; no se recuperó ni reconstruyó auth-guard. La adenda independiente admite esa procedencia con1positivo/10negativos. V4 sólo se prepara:877 rutas y56285pins,641 registros v3 intactos y85 sustituciones explícitas conservadas en el ZIP histórico. No está integrado ni equivale a un escaneo final aprobado. CI37/suite amplia, imagen actual con ExpatM2 y navegador37 siguen en curso.

Los145 criterios permanecen exactos, incluidos los92 originales; los537 archivos untracked están intactos. Free:10 clientes,1 plan por cliente al día,10 planes totales por gimnasio al día y mensual20 sin cambio. Alcance exclusivo del servicio web. Sin push, PR, despliegue, cargos ni envíos reales. Retención, países, SLO y piloto conservan las decisiones externas pendientes, sin repetir consultas ya realizadas.

## Checkpoint145

El servicio web integra esquema37, seguridad de cuenta y sesiones R31, notificaciones36/UI27, la reparación móvil de tres CSS y el catálogo finito de escaneo v4. El último cambio de producto288df corrige un operando del montaje de recordatorios: usa la constante léxica Api que declara api.js. API, backend y primitivas de sesión permanecen exactos. QA-29 conserva6 canarias del autor y4 propias TypeError antes; después pasan8+6 y36 comprobaciones mantenidas,50 ejecuciones seleccionadas offline. La aceptación nativa sigue pendiente.

El primer navegador37 sí ejecutó15 grupos MFA originales (11profesionales y4personales), con pageErrors vacíos en ese alcance. La nueva selección18 se detuvo en el primer grupo de recordatorios:0 grupos nuevos completos,Timeout y un TypeError sin stack capturado. El gate combinado33 quedó rechazado y se conserva íntegro. El cierre normal excedió45 segundos: se cerró únicamente el proceso propio verificado, se confirmó cero sesiones, DROP ordinario y ausencia fresca de la UUID. No se afirma normal_server_exit. QA prepara el nuevo freeze con el fix y un observer privado; aún no inició otro PG/Chrome.

La superposición del menú móvil pasa de16/16RED a16/16PASS con las mismas canarias Chrome geométricas y DOM inerte declarado, sin SQL. Las tres CSS integradascd423 coinciden con autor78aa y revisión3c257; scripts y plantillas no cambian. Esto prueba esa geometría, no accesibilidad completa ni todos los flujos nativos.

V4 está integrado663d:877 rutas,56285 pins,641 registros v3 exactos y85 sustituciones explícitas cuyo historial se conserva. ROOT verifica11016 ubicaciones antiguas con475 negativos; Seguridad repite11016 positivos,1652 mutaciones de archivo y4 controles de anclaje. La fixture contiene sólo los bytes originales del manifiesto histórico, sin recuperar ni reconstruir auth-guard. Su peer pasa37/37. El primer gate del autor fue157PASS/5fallos de fixture; tras la corrección pasó37/37, y MAINactual pasa162/162. Son pruebas y replay del informe405, no un nuevo escaneo global. El último escaneo real sigue RED11016; el nuevo árbol y la alerta literal de identidad del test bootstrap necesitan escaneo y clasificación finita.

CI se limita al SaaS y excluye cinco pruebas de licencia offline desktop, además de sus seis módulos explícitos. La ejecución amplia anterior se canceló antes de esos casos; no es un PASS. La colección actual deOps tiene4722 IDs:4716 runtime37 y6 físicas35 separadas; el verificador33 se ejecuta sobre fuente histórica auténtica, sin reconstruir imagen antigua. Serial/cobertura, paralelo, PostgreSQL/Redis/navegador e imagen actual conservan sus gates pendientes. QA-30 documenta que el inventario56 omitía google-auth con extras y aceptaba float: parser independiente deriva57 distribuciones runtime. Se corrige antes de construir; firmas APT/PSF offline no sustituyen imagen, SCA o ejecución.

El registro conserva145 criterios exactos y añade QA-29 yQA-30:147 IDs, incluidos92 originales. Los537 archivos untracked siguen intactos. Free aprobado:10 clientes,1 plan por cliente al día,10 planes totales diarios por gimnasio; mensual20 sin cambio. Trabajo exclusivo del servicio web. Sin push, PR, despliegue, cobros ni envíos reales. Decisiones externas de retención, países, SLO y piloto siguen abiertas sin repetir consultas.

## Checkpoint146

MAIN local conserva esquema37 y147 requisitos. Integra la receta Docker57 revisada y cuatro archivos de onboarding22, además de las reparaciones previas de cuenta, sesiones, recordatorios y móvil. Los cuatro blobs de onboarding coinciden con89ca/16c y revisión independiente954f:51 resultados propios,19pytest HTTP/SQLite en ambas factories y32VM con API/controller reales y transportes declarados. El dashboard consulta dos hechos propios persistidos, independientes del periodo estadístico, y deja descarga/entrega como acción explícita. Retira la marca compartida de navegador. En perfil personal incompleto muestra el enlace funcional al perfil y oculta acciones cuyos listeners aún no existen; el texto explica los campos requeridos. Los canarios de autor conservan5RED+2controles→7PASS y2RED+1control→3PASS. No se cierra R22: navegador, PostgreSQL focal y evaluación con5dueños/5socios siguen pendientes.

Docker57 c4d9 integra12 entradas exactas347, tres helpers y cuatro tests, sin cambiar el lock web. El parser reconoce extras y exige contador entero:57web,56 bloques sin adaptador binario y57 distribuciones runtime esperadas con psycopg2 nativo. Seguridad pasa75 seleccionados y verifica firmas offline APT/PSF y preparación acotada de Expat. La autoridad Git portable conserva21 objetos originales y rutas Merkle sin inventar ancestry; autor138PASS y peer25propios, con57 del companion dentro de un caso sin Git/red/procesos. Esa capa portable todavía no está integrada en MAIN. Imagen, inventario realmente instalado, SBOM y SCA actuales siguen pendientes.

El escaneo real8d6 terminó RED753:53956 alertas,53203 clasificaciones finitas y15096 archivos estables. V4 cubre las11016 ubicaciones antiguas; las753 nuevas están en20 archivos. Seguridad las propone como750 checksums y tres aserciones de identidad del namespace. ROOT comprueba cada preimagen Git, pointer y línea física,750 controles de pointer y80 del clasificador. V5 aislado c60 prepara897 rutas/57038 pins conservando877 registros v4 exactos y el mismo algoritmo salvo tres literales. Su primera selección205 fue167PASS/38 fallos por dos fixtures omitidas del checkout reducido; al materializarlas el módulo pasa50,38 reparados y12 controles repetidos. El parser esperaba38 y se conserva ese error de conteo; la proyección enlaza205 casos distintos aceptados entre fases, sin afirmar una corrida205PASS. El loader V5 real clasifica753 en el replay privado. Peer del artefacto y nuevo escaneo tras integración siguen pendientes; V5 no está activo en MAIN.

Navegador37 sigue rechazado. V2 conserva15MFA originales PASS y3 nuevos PASS, después un SyntaxError del test al interpretar como JWT un token de dos segmentos. Cerró servidor/procesos/UUID normalmente. V3 corrige sólo ese decoder con canario puro y controles tipados; selecciona18 sin repetir15. Agotó420s sin reporte final, por lo que no hay conteo18 aceptado ni punto exacto observado. El servidor y UUID cerraron normalmente. Un ACK interno, tras verificar HANDLE/PID/nacimiento/exe/argv, terminó únicamente Node propio con125;19 Chrome observados cerraron por pipe, sin terminación directa. Se preservan ajenos, listener8802 cerrado, fuentes1325/92distribuciones/8084instalados/157Node estables y pip0. PG y Chrome quedaron libres; nueva preparación offline añadirá progreso durable por grupo y comprobará el oráculo WebLock sin evadir serialización. Ese ensayo anterior usaba runtime8d6, no acredita el onboarding nuevo.

CI serial/cobertura847 sigue parcial e inmutable, con producto anterior a onboarding22. Detectó cuatro RED de privacidad Google cuya fixture usa el contrato antiguo tokeninfo/email-only; el runtime requiere firma/JWKS y vínculo persistido. Se preservan los fallos y se prepara companion actual con los mismos criterios500/202. No hay CI global PASS. Node actual pasa13comandos/147ejecuciones más10controles, aparte del inventario legado51/865 obligaciones. Calidad web pasa F821/sintaxis y9 controles del gate; Bandit conserva28 avisos,22 sin baseline vigente, pendientes de revisión finita. La herramienta de calidad81 no tiene pip: sus exit1 no son pip0. Runtime WEB92 permanece separado. PG se prepara como234 criterios de negocio actuales, cinco físicas33 con fuente auténtica y restore37 que conserva75 aserciones históricas; pool6 sólo en la carrera R24 original y pool1 en el resto. No se ejecutó ese nuevo catálogo.

Los147 criterios, incluidos92 originales, y537 archivos untracked se conservan exactos. Sólo servicio web. Free aprobado:10 clientes,1 plan por cliente al día,10 planes totales diarios por gimnasio; mensual20 sin cambio. Sin push, PR, despliegue, cobros ni envíos reales. Retención, países, SLO y piloto mantienen sus decisiones externas pendientes.

## Checkpoint147

MAIN mantiene esquema37 y147 requisitos, exclusivamente del servicio web. El onboarding integrado pasa35/35 pytest mixtos HTTP/SQLite y42/42 comprobaciones Node seleccionadas sobre63c, con1344 fuentes y92 distribuciones estables. Son hechos persistidos propios y estados de interfaz; no acreditan navegador, PostgreSQL ni5dueños/5socios. R22 sigue abierto para esos criterios. El código web conserva los cuatro blobs revisados75dc y las correcciones previas de cuenta, sesiones, recordatorios y móvil.

La autoridad portable Docker72 ya está integrada c11d:21 objetos Git originales, rutas Merkle y pin del ZIP, sin requerir Git en el companion aislado. Conserva12 entradas Docker57 exactas y el lock web; no se importan workflows todavía. V5 también está activo924e:897 rutas/57038 pins,877 registros anteriores exactos y algoritmo del loader idéntico salvo tres literales. Su peer4ed acepta264 criterios distintos en fases (204 heredados y60 propios), con un semántico750 excluido expresamente del peer y ya revisado por ROOT;261PASS iniciales y37PASS de replay reparan sólo tres fixtures físicas, sin alterar aserciones. Se conservan sus intentos de checkout y framing rechazados. En el MAIN integrado924e pasan347/347 en una sola selección:265 del escáner y82 de portabilidad, sin errores ni skips. Un caso portable ejecuta57 hijos en árbol nuevo sin Git/red/procesos; no se añaden al347. Fuentes1358/Python92/Node estables y Ruff12 módulos PASS. Imagen, inventario instalado57, SBOM y SCA actuales siguen pendientes.

El nuevo escaneo completo realca09 usa Gitleaks8.30.1 verificado,15244 archivos estables y256.766s:54179 alertas,53956 clasificaciones finitas y223 pendientes, exit1. Resuelve las753 ubicaciones del escaneo8d6; las223 nuevas están en seis archivos de metadatos de cuenta/entorno/receta y requieren revisión por preimagen/pointer/línea antes de clasificarse. No se aprueban por forma ni por texto del scanner. El resultado actual es RED223, no CI o R05 global PASS. El informe completo y mapas permanecen privados protegidos; los históricos RED1603/11016/753 conservan sus fuentes.

La fase runtime de la suite amplia serial847 terminó4725PASS/60FAIL/1skip Windows,0errors y4786 identidades exactas,3008.04s. Las seis físicas históricas35 no se ejecutaron tras ese rechazo. Conserva41 fallos de framing de fixtures antiguas,14 del contrato antiguo de seguimiento,4 del transporte Google antiguo y uno de expectativa de lookup pre-tenant. Este último pasó status422 y falla sólo al exigir la verificación Bearer en el login público: QA26 la elimina intencionadamente antes de establecer el nuevo sujeto. Se preparan companions explícitos con criterios actuales y originales intactos; no se atribuye retrospectivamente PASS al847. Paralelo y cobertura final actuales siguen pendientes. Calidad web pasa F821/sintaxis y9 controles; Bandit28/22 sin baseline vigente sigue en revisión finita independiente. El entorno de calidad81 no tiene pip y conserva exit1; WEB92 separado conserva pip0.

Navegador37 continúa rechazado por los intentos V1/V2/V3 preservados. V3 agotó420s sin reporte final y no tiene conteo18 aceptado; Node propio cerró125 bajo ACK por identidad y Chrome salió por pipe, servidor/UUID por cierre normal y ausencia fresca. V4 se prepara offline: canario con API y WebLock reales prueba que B no puede completar antes de liberar el ACK de A, conserva el oráculo legacy RED y3PASS con orden serializado; journal privado fsync tiene8 controles. Se mantiene el producto R31 y se añade un addon R22 de dos actores sintéticos, separado de18. Todavía no se inició SQL/Chrome ni se aceptó all20. PG tiene preparación354 IDs/24 módulos y19 controles, sin SQL; incluye234 criterios legacy37,12 migración37,13 nutrición,29 notificaciones,35 cuenta,30 peer y un restore37. R22 focal adicional y físicas33 auténticas conservan sus gates propios; pool6 sólo en la carrera R24 y pool1 en el resto.

Los147 criterios, incluidos92 originales, y537 archivos untracked se conservan exactos. Desktop queda fuera de desarrollo, pruebas, instaladores e integración actuales. Los manifiestos históricos con ese nombre usados como fixtures de checksums no son ejecución del producto. Free aprobado:10 clientes,1 plan por cliente al día,10 planes totales diarios por gimnasio y mensual20 sin cambio. Sin push, PR, despliegue, cobros ni envíos reales. Retención, países, SLO y piloto mantienen sus decisiones externas pendientes.

## Checkpoint148

Trabajo y entrega exclusivamente del servicio web, esquema37 y147 requisitos (92 originales y55 añadidos), con criterios y537 archivos untracked conservados exactos. Free mantiene10 clientes,1 plan por cliente al día,10 planes totales por gimnasio al día y mensual20 sin cambio. Sin trabajo desktop, push, PR, despliegue, cobros ni envíos reales.

R22 tiene aceptación nativa focal V5:2/2 grupos sobre PostgreSQL37 y Chrome,8 capturas, cero pageErrors/axe scoped/overflow, finalizador de los dos actores alcanzado, servidor y launcher exit0, una UUID quinta acumulada con DROP normal/cero sesiones/ausencia fresca y14 procesos propios cerrados. Los15 MFA y18 account/notifications previos conservan sus fuentes y límites; no se afirma aceptación combinada actual de35. V4 sigue rechazado pese a completar su driver18: falló addon y cierre45s, finalizador no alcanzado; su recuperación manual permanece explícita. El diagnóstico de cabeceras preserva no-store/referrer general para estadísticas y no-referrer para perfil; sólo se corrigió el helper de prueba, sin cambiar la política de producto.

La inspección nativa identificó texto estrecho a390px. MAIN962d integra únicamente dos líneas CSS revisadas: el texto dispone de su fila móvil antes de la acción. QA independiente reproduce el defecto390 con el CSS anterior y acepta320/360/390/480/640/641/768/1440,16 geometrías y9 capturas, cero pageErrors/red, cierre normal y entorno estable;641/768/1440 conservan geometría. Es render aislado con fragmentos auténticos y hechos sintéticos declarados, no otro E2E autenticado. PostgreSQL focal35 y evaluación humana5dueños/5socios siguen pendientes.

V6 está integrado95382:903 rutas/57261 anclajes,897 registros V5 exactos y seis archivos/223 ubicaciones añadidas desde la propuesta semántica revisada. ROOT verifica el artefacto real con223 positivos y54 negativos, sin cambio de algoritmo salvo tres literales; MAIN95382 pasa109/109 seleccionados y Ruff3. El escaneo completo realb0fa conserva15324 archivos estables y usa Gitleaks8.30.1 verificado:54180 alertas,54179 clasificaciones finitas y una pendiente, exit1. Las223 anteriores quedan resueltas. Seguridad recalcula independientemente el checksum nombrado de esa ubicación nueva con1 positivo,15 negativos semánticos y7 de anclaje; su propuesta no activa una excepción. V7 y otro escaneo actual aún pendientes; R05 global sigue abierto/RED1.

El registro separado Bandit22 queda aprobado sólo para sus fuentes/contexto/30d y dos conjuntos completos de bytes autenticados, con baseline histórico intacto. Ops y su peer contrastan el gate real2c0; en MAIN962d pasan lint/sintaxis/Bandit y9 pruebas negativas con6 controles, además56/56 pytest de consumidor y contrato independiente, sin errores/skips. Bandit1.9.4 conserva28 ocurrencias:6 históricas (5 fingerprints únicos) y22 aprobadas, cero pendientes/errores. Fuente1372,WEB92/tool81/Node157/binarios estables. WEB pip0/0; tool81 carece de pip, sin claim de consistencia pip. Esto no acepta aislamiento compartido, imagen, SCA o CI amplio.

Serial847 conserva4725PASS/60FAIL/1skip Windows; companions actuales Google/retención pasan70/70 y lookup16/16, sin modificar los originales ni convertir847 en PASS. Ops prepara fases históricas V5peer60/V6autor48 con transporte Git autenticado y n2 actual, sin retarget ni eliminación de criterios. PostgreSQL429 está preparado/coleccionado en29 grupos con26 controles offline, todavía sin SQL; añade35R22,31seguridad y9QA26 a354 previos. La lectura real de VM devolvió guest con3.50GiB libres, memoria/cache72/nonce correctos y apagado QMP normal; no hubo upload/build. Imagen57, inventario instalado, SBOM/SCA, Redis y CI amplio actual siguen pendientes. Retención, países, SLO, piloto, revisión profesional nutricional y custodia/recuperación externa conservan decisiones o participación reales pendientes.

## Checkpoint149 — 2026-10-21

La nueva solicitud autoriza implementar rutinas genéricas y rediseñar toda la plataforma web conservando los colores de la landing. Se adopta un catálogo común de sólo lectura sin nueva tabla, sin cuotas ni prescripción personal. Se conserva FastAPI/Jinja/CSS/JS. Las pruebas y entregas desktop siguen fuera del alcance. Los ACKOct20 están expirados y no se reutilizan.

## Checkpoint150 — 2026-10-21

El catálogo PPL es general y común a todos los planes, sin seguimiento persistido ni prescripción individual. El401 nuevo usa retiro local del token exacto; no cambia el mecanismo global MFA ni adopta cuentas nuevas. Se fija semántica timer/liveoff y estadospolite conforme W3C. Se conserva el clusterPG histórico dañado y se crea uno de pruebas nuevo propio55483; ningún dato/servicio general se modifica. No se atribuye causa a la pérdida de archivos Temp.

## Checkpoint151 — 2026-10-21

Se aceptan2UUID legítimas QA37:fixturemódulo37 ypredecesor36dañado solapadas. No reciclarBD ni omitir canario para forzar68;planfull69. Aceptación porfases323+106 conIDsdisjuntos ymisma fuente runtime,no one-shotinventado. NativePPL usa SaaSreal/SQLite37;Native35requierevencimiento antesSQL/cadafase ystop propio. Nodeinventario correcto=3paquetes/157archivos. R30sólohechospropiosobservados,sinDDL/colector/globalreporter ytargetsnull hasta baseline real.

## Checkpoint152 — 2026-10-21

Un código0 del wrapper antiguo no acredita que Gitleaks terminó. Se requiere resumen positivo completo con coherencia exacta y rechazo de todo diagnóstico inesperado, retención privada antes del payload, timeout externo y peer. No variar reglas/umbrales/allowlist para ocultar parciales. Root debe publicar los ACK de recursos por rename atómico de un archivo privado cerrado y verificado; el lector y los oráculos actuales permanecen intactos.

## Checkpoint153 — 2026-10-21

No presentar analítica deunaunidad observada0/1 como retención poblacional,primerusoever,lectura oentrega. Baselineprovisionalunreviewed/targetsnull/source_revisionnull. R30 exigePGpropio de53IDs/1UUID,pool5/max0;no reatribuir429legacy. Productores actuales usan frontera2ACE semántica antespayload;no cambiarhelperhistórico ni retroatribuir exclusividad aroot4. CItransporta11asserts safetyoriginales yexcluye sóloREDNativeV6exacto conreemplazoV7obligatorio;originalesRAW intactos.

## Checkpoint154 — 2026-10-22

Rotación de firma mediante corte coordinado y reautenticación; no exige inventar otro formato de token. Revertir código conserva la clave nueva: restaurar la anterior puede resucitar tokens. Las claves MFA son independientes. B19 usa un corpus público local fijado por hash, sin transmitir contraseñas. B13 se implementa como una pasada bounded por selección privada de recursos persistidos, invocable por scheduler externo y sin crear cobros.

## Checkpoint155 — 2026-10-22

ApplyR07 se implementa sólo sobre fixtures mientras falten procedencia y quiescencia reales. El manifiesto de un operador y su hash son una declaración auditable; por sí solos no prueban quién era dueño histórico ni que todos los escritores se detuvieron. Descriptor estable/journal/CAS no autorizan adoptar archivos. La recuperación de espacio es una fase separada que escribe respaldos enC; sus presupuestos no modifican los guards de build/probe/CI/SCA.

## Checkpoint156 — 2026-10-22

La programación de conciliación pertenece al operador y no se instala automáticamente. La selección de compras es autoridad operativa exacta, no permite reparar otra compra del mismo sujeto. Una Session activa prestada se rechaza sin asumir su cleanup. Git heredado del entorno no es autoridad de fuente del CLI R07. Los dos diagnósticos LOW de subprocess se adjudican al código fijo d8e18ddbc02a70603c840ecd2a1afd09d07f6874388fd2165c217613e4d730ef: ejecutable absoluto confiable, argv literal, shellFalse, timeout5, env limpio, stderrDEVNULL y uso exclusivo CLI. Se conserva la propuesta original approvedFalse y el SAST MED/HIGH existente; no se amplía registry22 ni se suprimen reglas generales.

## Checkpoint157 — 2026-10-22

La instrucción del usuario traslada proyecto/entornos a E y continúa trabajo en E/F; se conserva alcance web exclusivo. Copia verificada no equivale a autorización global de borrado: cada retirada necesita plan/ACK exactos y lectura completa, mientras instalaciones compartidas C y recursos ajenos permanecen fuera. Rutas C de RAW históricos son evidencia inmutable; usar mapping, no reescritura. quality10E es nuevo offline desde WEB92, no reparación del C83archivos incompleto de causa desconocida. Reparar9worktrees sólo después de todas las copias. El checkpoint no reejecuta gates anteriores ni habilita servicios.


Launcher: OpsCI observó que la invocación directa fue rechazada por ExecutionPolicy del host. No se cambia la política global: usar rutas/variables de proceso E explícitas o un hijo powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass para el script confiable, sólo en ese proceso. Los10PASS anteriores conservan comandos hijos exactos y no prueban que & directo funcione bajo toda política.

## Checkpoint158 — continuidad parcial E/F

El workspace E ya configura Python web E y temporales/cachés E en terminales nuevos del repositorio F; AGENTS.md registra las rutas. Se preservan variables globales e instalaciones compartidas. El inventario adicional de nombres en Documents/Downloads y entradas directas Local/Roaming no halló candidatos:7lstat/90nombres/3reparse omitidos, profundidad3, sin escaneo universal de C.

El motor optimizado059e1a pasa17originales+11propios+6peer en fases distintas; Win55a y admisión4207 permanecen exactos. Root leyó delta/peer y preservó el MasterACK anterior mediante rename para parar sólo entre raíces, sin cortar la copia en vuelo. V3 no se ha aplicado a C y su controlador sigue pendiente. La primera raíz Native2 aún no está aceptada. Los32orígenes y Roaming del checkpoint157 conservan sus resultados. No se reescriben RAW ni se anticipa reparación de9worktrees.

Root5CIchildTEMP pasa enMain90ddb; CI57 nuevo integrado enMain8d249 pasa18controles offline, y Root prepara realmente Main90ddb con493context/480APP/57dists/12inputs y8controles propios. CalidadMain52209 conTool10E pasa cinco comandos,1623fuentes/10dists/1441RECORD quietos,28Bandit/0pendientes/0errores,9negativos y6positivos. Es continuidad local comprobada, sin serial/n2 completo, SQL, VM, Docker o imagen real nuevos. [Resumen158](evidence/portable-web-continuity-checkpoint158-20261022/summary.json), [revisión](evidence/portable-web-continuity-checkpoint158-20261022/REVIEW.md).

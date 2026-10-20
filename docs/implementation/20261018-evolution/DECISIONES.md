# Decisiones de ejecución

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

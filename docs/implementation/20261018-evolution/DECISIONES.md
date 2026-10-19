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

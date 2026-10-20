# Hallazgos añadidos durante la implementación

## OPS08 — Transición obligatoria de configuración Railway

Detectado el 18 de octubre de 2026 al verificar el contrato real de pre-deploy de R03. La [documentación oficial de Railway](https://docs.railway.com/config-as-code) identifica Config as Code como obsoleto y mantiene `railway.toml`/`railway.json` para servicios que ya lo utilizan hasta el **1 de diciembre de 2026**, con corte definitivo. Los servicios nuevos deben utilizar [Infrastructure as Code](https://docs.railway.com/infrastructure-as-code). Esta condición no estaba en los siete informes originales.

Impacto: corregir preDeployCommand en el archivo existente es una transición local útil, pero por sí sola no prepara una operación posterior a esa fecha. No se debe crear staging nuevo suponiendo que heredará el mecanismo antiguo. No se eliminó la configuración actual ni se aplicó infraestructura por esta observación.

Aceptación añadida: inventariar la configuración efectiva sin exponer valores; preparar una definición IaC compatible para el servicio existente y el entorno aislado; fijar herramientas, comparar el diff previsto y validar sintaxis/contratos; verificar pre-deploy, digest, salud, secretos por referencia, volúmenes y rollback en staging autorizado antes del corte. No crear recursos con coste, aplicar IaC ni desplegar sin la autorización correspondiente.

Responsable: coordinación/operación. Tareas vinculadas: R03, R18, R20. Estado: pendiente; la preparación local puede continuar y la aplicación externa necesita un paquete revisable y autorización. Esta entrada no modifica la auditoría histórica ni declara probado el comportamiento futuro del proveedor.

## SEC01 — Activación desktop sin autoridad verificable

Detectado al inventariar excepciones de R04. `api/routes/licencias.py` publica activar/estado sin autenticación y deriva un plan pagado de STR/PRO/CLN, concediendo365 días y sobrescribiendo la activación de un hardware existente. No verifica emisión, compra ni identidad. La validación online de desktop también acepta una caída de red sin demostrar licencia local válida. No se ejecutaron esos flujos contra un servicio externo.

Prioridad P0 de contención local. Aceptación añadida: ninguna clave inventada por prefijo concede acceso; la activación/consulta requiere autoridad emitida y propietario autorizado, no coincidencia de email; hardware de otro gimnasio no se sobrescribe; periodo y límites provienen del contrato emitido, repetición no los inventa y revocación/caducidad se respeta. La falta de red no vuelve válida una licencia desconocida. Se mantienen las licencias locales existentes que pasan su verificación, con compatibilidad y reconciliación histórica documentadas. Pruebas antes/después, dos propietarios, concurrencia y revisión independiente.

Autor root; backend añadió vínculos nullable y backfill por clave emitida coincidente en la preparación R04. Los registros sin autoridad verificable se conservan. Contención local aceptada por QA: 40 pruebas, incluidas autoridad JWT persistida y dos errores Unicode reproducidos y corregidos. Estado: en revisión; concurrencia PostgreSQL, puente remoto autenticado y autoridad criptográfica legacy siguen abiertos en [LICENCIAS.md](LICENCIAS.md). Tareas vinculadas R01/R04/R09/R31; sin activación productiva ni nueva decisión de precios/dispositivos.

## SEC02 — Refresh tardío cruza una sesión nueva

Confirmado sobre0459b0f mediante dos pruebas independientes de máquina de estados en `tests/e2e/auth_refresh_race_review.cjs`, con transporte y tokens sintéticos en memoria. Si la cuenta cambia antes de un401, el helper refresca la identidad nueva y reenvía el DTO de la operación anterior. Si cambia mientras espera el refresh anterior, la respuesta tardía sobrescribe el par de tokens nuevo. [Reproducción y huella](evidence/ux/auth-refresh-race-before-source.json). No demuestra un incidente productivo, navegación real ni acceso de servidor fuera de sus permisos.

Prioridad P0. Aceptación: petición, refresh, reintento y respuesta ligados a sesión inicial; todo cambio de cuenta invalida operaciones anteriores sin limpiar ni reemplazar tokens nuevos. Refresh habitual, varios401 concurrentes, rotación propia y error deben resolver todos los consumidores. Login/registro públicos no refrescan por401. Comprobar también PDF/logo y logout. Pruebas antes/después, navegador y revisión independiente. Frontend implementa la corrección central; QA/seguridad la revisarán. Tareas R10/R19/R31. No renumera los92 IDs originales ni requiere datos o llamadas reales.

Seguimiento: seguridad encontró un rojo adicional en candidato275 por escritura parcial de Storage, capaz de mezclar accessB/refreshA y reenviar DTO deB bajoA. API347 añade bloqueo de confianza por instancia y pasó74 VM independientes; navegador actual sigue en revisión. El cuerpo275 se conservó en copia con SHA exacto mediante inversión de parches propios, sin inventar commit Git. [Contrato, evidencia y límites](SESIONES_HTTP.md). R10, recarga y atomicidad entre pestañas permanecen abiertos.

## OPS09 — Procedencia del empaquetado desktop

Dos negativos independientes demostraron que flags Git podían ocultar cambios de fuente aceptados por el empaquetador. La receta ahora compara bytes con blobs y conserva tratamiento exacto para controles binarios y CR aislado.94 controles QA y39 del artefacto9f aceptan este alcance local:1688 fuentes exactas, integridad ZIP e inicialización Qt. No acredita instalación, firma ni todos los flujos de negocio. [Evidencia independiente](evidence/desktop-artifact-independent-review.md).

## SEC03 — HTML persistido en drawer de clientes

El nombre de un cliente se interpretaba como HTML en el drawer. La reproducción mostró modificación del DOM; CSP bloqueó el handler y no se afirma ejecución activa. La construcción con nodos/textContent/dataset se integró en0fa124e después de12 controles browser QA y22 fuentes estables. El resto de renderers sigue bajo R23. [Alcance y pruebas](DRAWER_TEXTO.md).

## OPS10 — Referencia de diseño dentro del artefacto

La revisión del ZIP9f encontró `assets/design-reference.png`, sin uso de producto, con nombres/correos cuya procedencia no está acreditada. No se afirma que sean identidades reales. La exclusión exacta bca89bb conserva el original y supera97 pruebas QA y tres CLI propios. Reemplazo7bde30b verificado51bundle/ZIP/Qt y27payloadInno; criterio local cerrado. Instalación/firma/distribución y otros criterios siguen separados. [Revisión](evidence/desktop-ops10-independent/desktop-ops10-independent-source.json).

## SEC04 — Exportación atraviesa el cambio de sesión

En UI606, una continuación del consumidor podía preparar una parte de A después de que el helper real resolviera y la sesión cambiara a B. Un evento de fallo de Storage también conservaba el archivo preparado y sus acciones. La reproducción VM es sintética; no afirma incidente con usuarios reales. La interfaz se integró después de cercar DTO/Blob/descarga por revisión e identidad canónica,invalidar caché de forma síncrona y corregir dos guardspreclic adicionales. Seguridad25VM/QA25grupos revisan la corrección; criterio local cerrado,otros alcances de sesión abiertos. Los negativos originales y la adaptación aditiva de ACKlogout permanecen intactos. [Revisión independiente](evidence/ux/diary-ui-security-independent-review.md).

## SEC05 — Metadata privada en metricas

La revision local confirma almacenamiento de ruta concreta y direccion/encabezado de cliente en memoria y errores recientes. La heuristica de agrupacion tampoco identifica correctamente las rutas declaradas. Corrección integrada7bde30b tras15propios+63replay independientes;12rojos/3controles contra blob previo,18fuentes quiet. Quince casos preservados en suite con AST idéntico; criterio local cerrado, R17/R31 completos abiertos. No afirma incidente con datos reales. [Contrato y alcance](METRICAS_PRIVACIDAD.md).

## SEC06 — JSON falso del escáner aceptado como vacío

Seguridad reprodujo enab4490b cuatro reportes JSON malformados que se convertían en lista vacía con exit0. El control de objeto no vacío fallaba cerrado. El binario real8.30.1 escribe[] seguido deLF al no hallar coincidencias. Fix41708e5 elimina únicamente la normalización `or []`; el driver independiente intacto pasó de1/5 a5/5 y ocho controles adicionales pasaron. Suite mantenida61/61; revisión7fuentes quietas. Integrado31ebb2f, criterio local verificado; no declara limpias otras fuentes. [Aceptación](evidence/secrets-wrapper-independent-review.json).

## QA-11 — Referencias históricas mutables del verificador CI28

QA reprodujo dos bypass de `--verify-only`: modificar a la vez el fixture y su snapshot, o un archivo histórico y su hash enbaseline.json. El autor encontró además sustitución del docstring por una expresión ejecutable descartada por la comparación. Los snapshots auténticos5db sí coinciden con Git; no se afirma modificación de CI remoto. Fix3978 fija referencia y snapshot, y admite sólo docstring literal. Cinco focales de autor y7CLIindependientes pasan: se rechazan los dos bypass originales y print/número/f-string, con controles intacto/documental verdes;764fuentes/89paquetes quietos. Integrado5ba98c6/7cf4e6c; criterio local verificado. [Dos negativos originales](evidence/recovery-ci28-independent-20261019/baseline-trust-red.json),[aceptación](evidence/recovery-ci28-fix-independent-20261019/final/summary.json).

## SEC07 — Cabeceras privadas ausentes en errores de historial

Root reprodujo5rojos/3controles en71 y8verdes en49. Seguridad confirmó después dos500 sin cabeceras al fallar el SELECT, sin cursor ni planes en la respuesta. Fix57cdc0d añade boundary focal: respuesta500 genérica con no-store/no-referrer, conservando handlers/CSP y rutas ajenas. Seguridad acepta24/24:2negativos originales intactos,8root y14propios;20fuentes estables. Integradofdfc9cb; composición con recuperación28 aprobó36/36 y616fuentes estables. Criterio local verificado, R34 completo sigue abierto. [Revisión](evidence/history-security-after-20261019/source.json),[composición](evidence/history-recovery28-main-composition-20261019/summary.json).

## SEC08 — Componentes heredados vulnerables en runtime y artefactos

La primera imagen real5eb6d300, de fuente92615d7, compila y contiene55distribuciones/CPython3.12.13. El SCA OSV de ese inventario devuelve12entradas que representan6avisos únicos, todos de pip25.0.1 heredado; no se demuestra explotación. pip-audit no cubre CPython ni paquetes Debian. [Inventario](evidence/linux-recovery28-image-92615d7/runtime-inventory.json),[SCA anterior](evidence/linux-recovery28-image-92615d7/sca-before/summary.json).

La [publicación oficial de Python3.12.15](https://www.python.org/downloads/release/python-31215/) incluye correcciones de seguridad posteriores a3.12.13. [OSV PYSEC-2026-3721](https://osv.dev/vulnerability/PYSEC-2026-3721) requiere pip26.2; el candidato fija26.2.1 desde PyPI por hash. El worktree aislado23e57e0/abd559a actualiza base común por digest linux/amd64 y bootstrap pip antes de deps/runtime. Su build y auditoría OS siguen en curso; no se declara limpio ni integrado.

Aceptación añadida: inventariar cada artefacto soportado, preservar anteriores, corregir con fuentes y pines verificables, reconstruir sin metadata duplicada, pip check y SCA real; revisar CPython/OS por separado y pasar regresiones independientes. Windows3.12.13 y los instaladores históricos permanecen sin actualizar: una imagen Linux nueva no los valida. Responsable operación/seguridad, tareasR09/R18/R21/R31; estado en_curso local, sin excepción general, release ni despliegue.

## SEC09 — OpenSSL vendorizado de psycopg2 fuera de la cobertura Debian y PyPI

La imagen `99c846bd28b0` carga OpenSSL 3.5.8 del wheel psycopg2-binary, separado de `_ssl` Debian con backports y de cryptography 4.0.3. Trece [registros primarios CNA](evidence/linux-runtime28-native-20261019/native-openssl-sec09/evidence-manifest.json) incluyen 3.5.8 en su rango afectado. El [inventario ELF](evidence/linux-runtime28-native-20261019/native/native.json) identifica rutas, hashes y enlaces efectivos. No se ha demostrado explotación; condiciones de API, protocolo, arquitectura y compilación requieren evaluación por aviso. Los 71 IDs OS y el resultado OSV de 55 distribuciones PyPI mantienen su alcance separado.

Cierre: corregir el componente efectivo con procedencia fijada; reconstruir, inventariar y revisar SBOM/SCA, PostgreSQL y arranque con rol restringido, con aceptación independiente. No hay excepción de riesgo ni imagen corregida aceptada. Responsable: operación y seguridad. Estado: en curso; ver registro SEC09.

## UX-18 — Interferencia de controles entre vínculos y exportación

En939, VinculosUI guarda/restaura disabled de todos los controles del documento. La exportación, dentro del mismo main, se inicializa concurrentemente y su botón puede volver a quedar deshabilitado. QAChrome/PGreal pasó siete criterios y falló el octavo por ese botón;9–16 no se alcanzaron. Se conservan fuentes, capturas y [fase rechazada](evidence/qa-r12-composition29-independent-20261019/phase939-blocked-summary.json).

El fixec029 aislado exige una colección ownedControls por consumidor para operación e invalidación; evita interferir con exportación. Los mismos tres canarios dan2rojos/1control antes y3verdes después en el ensayo del autor;16 regresiones existentes pasan sin alterar aserciones. Falta aceptación independiente y replay real16. [Contrato y límites](R12_CONTROLES_INDEPENDIENTES.md). PrioridadP1, responsable frontend/QA, registroUX-18.


## SEC10: Expat embebido de CPython3.12.15 y CVE-2026-77214

La imagen99c mide pyexpat2.8.5 embebido en CPython3.12.15; el CNA primario incluye<=2.8.5 y el source exacto conserva XML_ParseBuffer sin el fix de capacidad13c5f63. Las guardas observadas de wrappers no acreditan reparar el componente ni descartar todos sus callers.

Cierre exigido: Conservar cadena de procedencia PSF/tag/commit/blobs y ELF por artefacto; verificar rango/fix y alcanzabilidad real sin afirmar explotación sólo por versión; aplicar una reparación mantenida y fijada al componente realmente cargado, reconstruir el artefacto, comprobar versión/parche efectivo, SBOM/SCA y regresiones de parsers/runtime con revisión independiente. No sustituir Expat embebido instalando sólo libexpat Debian ni ignorar el aviso; mantener abierto el alcance no ejecutado.

[Seguridad independiente](evidence/security-native31-sca-independent-20261019/source.json). Sin reparación, explotación remota o dictamen global acreditados.


## SEC11: Retorno de portal fuera del origen y validación anterior al circuito

create_portal_session concatena BASE_URL y return_url sin exigir ruta relativa. Con @outside.example.invalid/path el puerto Stripe recibe otro host. Validar dentro del decorador de reintentos también puede clasificar entradas inválidas como fallos del proveedor y abrir el circuito compartido; la corrección debe evitar ambos efectos.

Criterio de cierre: Validar el retorno con un helper canónico antes de emitir grants y antes del circuito/puerto Stripe: una sola barra inicial, sin autoridad/esquema, backslash, espacios o controles ASCII/DEL; preservar rutas /usuario y B2B con query/fragmento permitidos. Rechazar antes de cualquier llamada externa; una secuencia de entradas inválidas no abre el circuito ni bloquea una solicitud válida. Verificar ambas factories, contratos previos, cuerpo ligado al grant y origen/URL exactos mediante puertos sintéticos y revisión independiente, sin llamadas o cargos reales.

Reproducción independiente local de preimagen:8rojos/3controles, sin DB/HTTP/red. Corrección final y revisión pendientes. [Recibo](evidence/prepared-wave114-20261019/SEC11-root-before/receipt.json).


## SEC12: Binding de Idempotency-Key en aliases de pago del candidato MFA31

Los aliases /api/pagos/stripe/session y /api/pagos/mp/preference del candidato56e810 no transmiten Idempotency-Key a step_up ni al servicio. El grant con clave exacta se rechaza y un grant sin clave acepta una cabecera nueva hasta el puerto sintético. El control de checkout canónico sí liga la clave.

Criterio: Leer la misma Idempotency-Key observada por HTTP y transmitirla sin divergencia a la validación/consumo del grant y a la intención durable en ambos aliases, conservando DTO y respuesta legacy. Rechazar clave añadida, retirada o cambiada antes del puerto y sin consumo irreversible indebido; aceptar la clave exacta. Probar ambos proveedores y factories con autenticación/MFA reales y puertos sintéticos; conservar los cinco criterios independientes originales, la revisión independiente posterior y las garantías canónicas previas. No afirmar doblecargo, proveedor real ni bypass del factor.

Reproducción inicial independiente:4rojos+1control en api.app. Candidato31 aislado, sin proveedor/cargo real. [Recibo](evidence/prepared-wave116-20261019/SEC12-initial-observation.json).


## SEC13: Elegibilidad canónica de actor y propietario al emitir y consumir MFA

MFA31 omite invitation_token del propietario en current_identity y mfa_actions.authorize. Con administrador previamente enrolado/autenticado, un OWNER activo pero con invitación noNULL permite emitir grant aunque canonical_gym de R12 es falso. Los checks truthy tampoco equivalen a IS NULL ante cadenas vacías históricas/ambiguas.

Criterio: Revalidar bajo los mismos locks de cuentas la elegibilidad persistida de actor y propietario canónico al emitir y consumir autorizaciones: activo, sin borrado, invitación estrictamenteNULL y propietario gym/OWNER sin asociación de equipo. Rechazar estados noNULL incluso vacíos sin emitir ni consumir indebidamente grants y preservar el caso legítimo; no ampliar roles o suplir propiedad. Conservar los seis criterios independientes iniciales en ambas factories, cubrir emisión/consumo y estados ambiguos con pruebas propias, revisión independiente posterior y PostgreSQL restringido cuando corresponda. No afirmar que una API legítima crea esos estados ni que se ejecutó una invitación o cargo.

Reproducción inicial:4controles+2rojos enambasfactories conestados sintéticos explícitos. [Recibo](evidence/prepared-wave117-20261019/SEC13-initial-observation.json).

## Checkpoint130

QA-17 (P2): El alta Google de gimnasio puede producir 200+503 en una colisión concurrente de issuer/sub porque el flush del perfil queda fuera del manejo estrecho de IntegrityError. Confirm puede anticipar una colisión con autoflush=True. Se conserva una cuenta y no hay credenciales del perdedor; falla la clasificación pública del conflicto. Criterio: En ambas factories, dos procesos HTTP reales con sesiones propias, pool1 y autoflush=False que intenten alta gym para el mismo issuer/sub y contactos diferentes producen un único200 y un409 google_link_conflict, sin credenciales para el perdedor y con una sola cuenta, binding, perfil y cinco plantillas canónicas. Las colisiones de constraint previas al commit en alta y confirm, incluido autoflush=True al confirmar, requieren rollback confirmado antes del409; rollback incierto conserva503. Mantener atomicidad, ausencia de adopción o reintentos, restauración del contexto y cierre de sesiones propias. Repetir los mismos canarios y conservar verificación de identidad del proveedor. Autor8a5e ypeerb792cb aceptados focalmente; wiring de CI actual en curso.

## Checkpoint132

QA-18 (P2): El candidato Backend34 devuelve409 followup_busy ante IntegrityError desconocido durante flush y ante SQLITE_ERROR=1 de tabla inexistente cuyo nombre contiene blocked. Falla la clasificación de disponibilidad; no se confirma bypass de autorización, explotación remota ni fuga de datos. Criterio: En ambas factories, los mismos canarios HTTP autenticados deben devolver503 followup_unconfirmed para errores de integridad desconocidos y SQLITE_ERROR real de tabla inexistente, con independencia de palabras como blocked en su nombre. Sólo conflictos de constraint, trigger o bloqueo conocidos, identificados mediante códigos y diagnósticos cerrados del driver, pueden producir409; un rollback incierto conserva503. Mantener cabeceras privadas, opacidad, ausencia de ACK y Task/Event parciales, sin retry, readback o adopción automática; una petición explícita posterior al fallo puede aplicar una sola operación. Preservar los controles de bloqueo SQLite real409 y tabla faltante sin ese fragmento503 y repetir las doce canarias originales sin rebajar aserciones.

## Checkpoint134

QA-18: fuente41dc5 aceptada focalmente porQA independiente con la misma canaria original c3a4:12/12PASS, desde4FAIL/8PASS anteriores, sin modificar asserts. Dieciséis controles propios directos PASS (seisSQLite reales y diezmetadatos sintéticos), sinPostgreSQL. No cubre la proyecciónUsuario posterior ni aceptación global34; el producto34 aún no está enMAIN.

## Checkpoint135

Decisión expresa del usuario al reanudar: «continua con todos estos cambios pero ya no trabajes en la version desktop, trabaja unicamente en la version de el servicio web». Desde este checkpoint el trabajo y la entrega se limitan al SaaS. Se detienen desarrollo, QA, empaquetado e instalador desktop. Código y evidencias previos se conservan; no se eliminan funciones existentes ni se integra el candidato Desktop35. QA confirmó que todavía no había ejecutado pruebas ni creado ramas o artefactos de esa revisión. Las validaciones Windows del servicio web y el núcleo compartido siguen dentro del alcance. Esta decisión sustituye la instrucción anterior de continuar el desarrollo desktop; no declara resueltos sus defectos.

### SEC19

La consulta de locks de autoridad de seguimiento carga nombre, email y password_hash de un responsable histórico que ahora pertenece a otro contexto, aunque el DTO omite su nombre.

Criterio: Consultar para autoridad únicamente los campos de elegibilidad necesarios bajo los locks originales; no hidratar contacto ni credenciales del responsable ajeno. Los atributos diferidos deben fallar de forma cerrada. Conservar permiso, aislamiento, orden de locks, clasificación de errores, respuestas y DTO. Repetir los mismos canarios HTTP/SQL y de carga ORM en ambas factories; validar el cambio con revisión independiente y PostgreSQL restringido. No atribuir una fuga HTTP al sobreacceso interno observado.

Estado: Dos RED reales SQLite/ORM pasan tras proyección de ocho campos; seis aserciones conservadas. Fuente producto81f190/service13a9. Peer PostgreSQL pendiente. El nombre informal Sec18projection de comunicaciones previas corresponde a SEC19; SEC18 existente conserva su identidad.

### SEC20

Con NutriB no asignado, bloquear sólo UsuarioC responsable de una tarea ajena cambia la respuesta a409 mientras un ID inexistente conserva404; el hint incorpora C al lockset antes del filtro de asignación.

Criterio: En ambas factories, una tarea fuera de la asignación autorizada debe conservar la misma denegación opaca que un ID inexistente, incluso al mantener bloqueada únicamente la cuenta del responsable ajeno. Aplicar el predicado de asignación antes de incorporar identidades sensibles al hint o lockset, revalidando autoridad y estados persistidos sin ampliar permisos. Mantener CAS, locks necesarios, historial e idempotencia y repetir las cuatro canarias originales junto con QA-21 en PostgreSQL con rol restringido. No inferir exposición de DTO o modificación autorizada por este oracle de contención.

Estado: Revisión independiente sobre f848/producto81f190: dos RED por oracle, auth y MFA reales. No hay parche integrado ni aceptación global.

### QA-19

El diálogo Qt de edición llama a GestorBDClientes.actualizar_cliente, método inexistente en la preimagen55a3, por lo que no confirma ni guarda la edición.

Criterio: La edición real del diálogo Qt debe persistir los cambios de perfil mediante un método existente y aceptar sólo el guardado confirmado, sin incrementar el contador de planes. La misma canaria con diálogo y gestor de la preimagen exacta debe fallar antes y pasar después de la corrección. Conservar formulario y datos ante un fallo de escritura.

Estado: Hallazgo confirmado antes del recorte de alcance. Candidato0d20 aislado y evidencia cf0b conservados; no se integra ni continúa su revisión. Resolución de alcance no_aplicable a la entrega SaaS por decisión expresa del usuario, sin afirmar cierre técnico.

### QA-20

PUT /api/clientes/{id_cliente} con sólo peso sobre un perfil inicialmente vacío devuelve400 client_update_failed en api.app por AttributeError.lower de objetivoNULL, mientras web.main_web guarda200.

Criterio: El contrato de perfil progresivo debe aceptar una actualización parcial válida en ambas factories sin exigir, rellenar o calcular con datos no declarados. Persistir únicamente los campos enviados y conservar la declaración nutricional y los campos omitidos. Rechazar entradas inválidas sin aplicar parcialmente los otros campos. Conservar pertenencia, permisos, cabeceras privadas y validación completa antes de generar; repetir las mismas canarias antes/después y obtener revisión independiente.

Estado: Frontend confirmó1RED api/1controlSaaS en55a3. ROOT reprodujo en54e511 dos RED y seis controles con el framing de declaración desconocida corregido explícitamente. Reparación aislada en curso, sin integración MAIN.

### QA-21

El SELECT FOR SHARE del cliente y el trigger34 esperan ante FOR UPDATE externo; la canaria PostgreSQL acaba503 tras statement_timeout700ms en lugar del409 inmediato de contención conocido.

Criterio: Usar adquisición NOWAIT de los locks compartidos del cliente tanto en servicio como en el guard PostgreSQL, conservando el orden y las invariantes de causa/cliente. Con la misma fila retenida por otra conexión propia, ambas factories deben devolver409 followup_busy dentro del umbral original, sin esperar al statement_timeout, sin ACK ni Task/Event parcial y sin retry automático. SQLSTATE57014 y los fallos desconocidos siguen503. Preservar targets22–33, conservar el target34 anterior y recapturar únicamente la firma34 afectada si cambia el trigger. Repetir los mismos cuatro canarios originales compartidos con SEC20 y las regresiones afectadas.

Estado: Dos RED reales PG sobre81f190; app4flagsfalse/noowner/FORCE28/pool1. Primera UUID propia cerrada por DROP normal,0sesiones y ausencia fresca. Parche y nuevo target34 pendientes, target35 todavía no capturado.

## Checkpoint136

### QA-22

La lectura de exclusiones alimentarias persistidas con JSON malformado devuelve500 en ambas factories porque _cliente_to_dict ejecuta json.loads antes de la validación nutricional cerrada.

Criterio: Validar la declaración y las exclusiones persistidas antes de serializar el perfil. Ante JSON truncado, forma incorrecta o valores inválidos, GET detalle/listado y generación deben devolver el error nutricional público422, con no-store/no-referrer y sin reflejar los hechos rechazados. No reinterpretar corrupción como lista vacía ni información desconocida, no modificar la persistencia y no reservar cuota, generar Plan u objeto. Conservar listas legítimas y su orden, DTO y permisos; repetir las mismas dos canarias independientes y los controles añadidos, con peer posterior al parche.

QA independiente:83 mantenidos PASS;18 propios con16PASS y2RED. Autor e0ca valida antes de json.loads: mismos2 pasan y8mantenidos pasan,10ejecuciones finales. ROOT repite8enPG35 y todos pasan dentro de su fase global29/34; sello del peer pendiente.

### SEC21

NutritionRoute sanea errores sólo cuando el body es dict con restricciones_nutricionales; POST/PUT de clientes con una lista que contiene esa declaración refleja los valores rechazados en422.

Criterio: Las escrituras de perfil nutricional deben rechazar cuerpos de forma inválida sin reflejar declaraciones o datos de salud en la respuesta, incluidos arrays, objetos anidados, escalares y cadenas. Seleccionar el error público acotado por la superficie de escritura autorizada y conservar validación estricta, códigos y cabeceras privadas; no aceptar arrays ni degradar validación. Mantener contratos de lectura/paginación y rutas vecinas. Repetir las seis canarias independientes originales en ambas factories, controles propios y revisión independiente del parche. No afirmar fuga a terceros o bypass por la reflexión autenticada observada.

SEC independiente sobref7c:4RED+2controlesPASS,0errores/skips; canaria21b224 byte exacta, sinPG. Corrección focal en ramaSEC en curso; no integrada ni aceptada.

### QA-23

Cuatro casos HTTP de generación PostgreSQL con pool1 y expire_on_commit=True devuelven500/TimeoutError antes de la guarda worker o publicación, mientras el contrato esperaba422/409. La fábrica productiva usa expire_on_commit=False; no se atribuye allí el mismo fallo.

Criterio: Confirmar y resolver la retención de checkout entre la reserva durable confirmada y el worker de generación, preservando el contrato con pool1 y ambas configuraciones de expiración admitidas. La lectura del resultado de reserva no debe abrir una transacción innecesaria que bloquee al worker. Mantener atomicidad, idempotencia, cuota, tenant y clasificación veraz de commit o compensación inciertos; no aumentar el pool, poner expire=False en la prueba ni cambiar expectativas para ocultar el fallo. Repetir los mismos cuatro casos PG y controles de handoff y replay, distinguiendo explícitamente defectos del harness de cambios de producto y revisando independientemente la corrección.

ROOT fasef7c:34casos,29PASS5FAIL0E/skip. Un fallo adicional de seed booleano es harness y se conserva separado. Causa probable lectura ORM expirada tras commit; confirmación con telemetría propia y corrección pendientes.

## Checkpoint137

### SEC22

Una excepción inesperada al leer el perfil autenticado devuelve500 genérico sin Cache-Control en ambas factories. Fronteras de405, slash y422 también necesitan la política privada finita.

Criterio: Conservar un500 opaco ante fallos inesperados de perfil o generación, con no-store/no-referrer y sin texto de excepción, declaración, traceback o valores privados en respuesta o logs. Aplicar cabeceras privadas también en405,422 y alias de una barra de las rutas reales de clientes, perfil personal y generación, manteniendo códigos, contrato de lectura/paginación, CSP existente y vecinos fuera del matcher. Repetir las dos canarias independientes originales y controles de logs y límites; otro agente debe revisar el parche. No afirmar filtración a terceros o bypass por la ausencia observada de cabeceras.

Autor d474 conserva500/headers y sanea logs; ROOTpeer12HTTP originales y17PGprivacidadPASS en scopes separados, con seis originalesSEC21 y controles propios. MAIN sigue33; integración pendiente.

### SEC23

En el candidato36, cambiar Usuario.email de A a B y de vuelta a A sin nuevo consentimiento permite que una capacidad antigua de exclusión vuelva a coincidir con el hash de contacto y desactive una preferencia. Reproducción SQL, sin ruta HTTP vigente de cambio de email.

Criterio: Un cambio real de contacto debe invalidar de forma monotónica las capacidades, el consentimiento aplicable y el handoff pendientes ligados al contacto anterior, incluso ante A→B→A. Conservar los eventos append-only y exigir nueva autorización explícita para el contacto actual; no reactivar por coincidencia de hash. Verificar la época actual bajo lock antes de exclusión o envío, y capturarla en preferencias/outbox/fuente. Impedir decremento, reset, fracción, NULL, saltos y overflow; un incremento manual conservador sólo puede invalidar. Probar incrementos automáticos y el mismo A→B→A original en SQLite y PostgreSQL restringido, con migración, aislamiento, rollback y revisión independiente. No presentar este SQL como explotación HTTP.

Autor informa2RED→2PASS con0→1→2 automático, más17/17SQLite de exclusión/época/migraciones; canariaac49732d recuperada por inversa completa SHAigual a foto original. PG36 ypeer pendientes; columna metadata nueva36, targets22–35 intactos.

### QA-24

El POST público de exclusión por capacidad funciona en la API pero recibe403 CSRF previo al router en SaaS; la página pública usa credentials:omit y no puede completar la operación anónima.

Criterio: Permitir que la exclusión pública anónima por capacidad de propósito único complete en ambas factories sin sesión o cookies, con JSON estricto, límite de frecuencia, hash/expiración/versión de capacidad y autoridad disable-only intactos. Una exención CSRF, si es necesaria, debe ser exacta para POST /api/notificaciones/excluir y su alias de una barra, configurable con default vacío; no ampliar prefixes o vecinos. GET/prefetch no muta, bearer ajeno no cambia el sujeto y capacidad vieja no afecta preferencias nuevas. Probar el mismo caso anónimo original y vecinos403, errores privados y ausencia de otros efectos, con revisión independiente.

Autor informa reparación exactaCSRF y17/17SQLite con controles de época/migración; actualizador de factory/config predeterminado acotado. No aceptación PG36, peer, entrega de correo o despliegue.

## Checkpoint139

### SEC24

El candidato de transporte browser rechazaba Origin inválido con403 pero, en la API, TenantMiddleware podía consultar primero un bearer auténtico. SaaS ya excluía /api/auth/. No se observó bypass de autenticación ni consumo o cambio de prueba/cookie.

Criterio: La admisión estricta de las operaciones finitas del transporte browser debe ocurrir antes de cualquier consulta de bearer, SQL, verificación de proveedor o efecto de autenticación, incluso si la solicitud lleva un bearer válido. Rechazar Origin, header browser, contenido, query, método o alias no admitidos con error público privado y sin modificar refresh cookie, prueba o estado de sesión. Mantener rutas finitas y el comportamiento de APIlegacy sin header, vecinos y contexto tenant/finally, sin excluir un prefijo global ni convertir cookie en autoridad general. Repetir la misma canaria independiente689a, controles de SQL/verificador cero y límites antes/después en ambas factories, con revisión independiente. No presentar esta consulta previa como auth bypass o como un contador SQL observado si la aserción anterior lo impidió.

## Checkpoint141 SEC25

Snapshot de factura contradictorio (paid mayor que due con remaining positivo, o paidTrue/open) podía calificar como deuda y programar recordatorio en candidato36.

Criterio: Aceptar deuda sólo con importe entero acotado y coherencia due=paid+remaining, estado y paid compatibles; contradicción o ausencia produce unknown y no nuevo envío. Aplicar la misma validación a snapshots nuevos y hechos persistidos. Preservar canaria original RED, contratos coherentes, fuentes Stripe/MP, RLS y ausencia de cargos/envío real; repetir ambosfactories y revisión independiente, sin atribuir aceptación del proveedor como entrega.

## Checkpoint141 QA-25

Dos companions R31 asumían finales LF y fallaban al compilar fuentes RAW CRLF antes de invocar HTTP o Chrome; no eran regresión del runtime MFA.

Criterio: Conservar los originales RAW y sus hashes; normalizar EOL exclusivamente en la copia en memoria usada por el companion. Mantener aserciones de negocio y de ciclo de sesión, informar hash RAW y de compilación por separado, repetir controles LF/CRLF y puentes MFA contra HTTP real en ambasfactories. No presentar compilación como navegador nativo.

## Checkpoint141 QA-26

Registro público legacy con Bearer válido ajeno devuelve500 en API después de persistir una identidad nueva; el mismo caso SaaS devuelve200. La cuenta manager original conserva su autoridad.

Criterio: La ruta pública de registro debe derivar la identidad sólo del registro actual y no heredar contexto tenant de un Bearer ajeno. Completar una cuenta independiente con200 sin adopción de autoridad ajena o dejar cero identidad parcial cuando se rechace por ese contexto. Preservar la admisión browser antes de cualquier consulta, vecinos protegidos y reset finally; usar rutas y métodos finitos, sin exención global de prefijo. Repetir canaria original y controles en ambasfactories con revisión independiente.

## Checkpoint141 QA-27

La invalidación de sesión elimina el DOM privado mientras callbacks de configuración/branding/perfil/privacidad conservan búsquedas de nodos o continúan una inicialización; diagnóstico nativo separado observa cuatro TypeError.

Criterio: Tras invalidación local o externa, los consumidores privados deben detenerse, limpiar su RAM y tolerar la eliminación del DOM sin TypeError, lectura tardía, envío o readopción de actor. Capturar referencias propias y verificar vigencia antes de usar nodos o continuar await; cubrir las cuatro ubicaciones observadas, personalización y pagehide. Preservar pageErrors==[] y todas las aserciones de negocio del navegador original; verificar reparación focal y después repetir navegador con fuente actual y revisión independiente.

## Checkpoint143

QA-28: Un401 de recurso en seguridad de cuenta37 conserva la credencial RAM y/o proyecciones del actor anterior; incluye status, requestEmail, changePassword y aliases context/factorStatus/verify.

Criterio: Un401 de recurso debe retirar la autoridad local capturada y limpiar sus proyecciones, sin refresh, replay automatico, adopcion de actor ni afirmacion de revocacion global. Una respuesta tardia de A nunca retira B ni sobrescribe un epoch externo. Preservar403/422 corregibles y401 de reautenticacion primaria incorrecta, captura del cuerpo antes de await, WebLock hasta respuesta y frontera local antes de liberarlo cuando corresponda. Repetir seis HTTP reales originales en ambas factories, doce VM RED y bordes independientes, sin modificar primitives globales MFA/R31.

SeisHTTP ydoceVM RED independientes preservados. Correccion focal yrevision en curso; no defecto de autorizacion backend demostrado.

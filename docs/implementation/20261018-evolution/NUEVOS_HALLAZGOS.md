# Hallazgos añadidos durante la implementación

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

## Checkpoint163 — codec de carga y conservación de rechazos

private_control usaba utf8-sig, nombre no reconocido: LookupError con JSON válido. Root corrigió sólo utf-8-sig;878CRLF y demás bytes intactos. Se preservan originalRED, cuatro controles autor y cuatro Root como fases distintas, sin presentar el parser como carga HTTP. Los rechazos PG509 anteriores y sus created/JUnit no se convierten en PASS por el actual509. No se añade criterio. [Resumen163](evidence/checkpoint163-web-continuity-20261023/summary.json) y [matriz](evidence/checkpoint163-web-continuity-20261023/matrix.md).


<!-- DOC162-CLOSED-SOURCE-OBSERVATIONS -->

## Checkpoint162 — seguimiento sin criterio nuevo

Se conserva el rechazo de dos intentos PG509 por una sesión observada en teardown, primero migration37 y luego legacy-followup. La inspección y DROP normal posteriores acreditan cierre propio posterior, no causa retrospectiva. Los originales, JUnit y recibos created permanecen intactos.

La barrera común observada/revisada integra ledger por lifetimes y pools originales: QueuePool.dispose puede reiniciar counters y sustituir pools, por lo que un cero posterior aislado no prueba devolución previa. Main13 y PG1 actual pasan;509 actual sigue sin resultado. No se añade ID ni se cambia ningún criterio. [Resumen162](evidence/checkpoint162-web-continuity-20261023/summary.json) y [matriz](evidence/checkpoint162-web-continuity-20261023/matrix.md).


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

## Checkpoint144

QA-28 verificado localmente:1e01/12b4 y revisión independiente28e. Todos los RED se conservan, incluidos cuatro GET retenidos hastaJSON en el candidato intermedio. Fix final retira alheader401 con fence exacto; MFAglobal/reauthcorrigible intactos. La corrección de checkoutLF y los parsers de evidencia son framing, no defectos de producto ni criterios nuevos.

## Checkpoint145

### QA-29

El montaje predeterminado de recordatorios usa window.Api aunque api.js declara una constante léxica Api; la página real falla al iniciar sin una API inyectada.

Aceptación: Montar recordatorios con la API real de scripts clásicos, sin crear window.Api ni inyectar options.api. Cubrir llamada predeterminada, DOMContentLoaded y documento completo para gimnasio y personal, sin escrituras iniciales ni refresh automático. Mantener cancelación por pagehide, fence del epoch y páginas sin widget. Conservar canarias RED, repetirlas tras la corrección y comprobar el recorrido nativo actual sin pageErrors, sin relajar negocio ni contratos de sesión.

### QA-30

El parser del lock de contenedor omite google-auth[pyjwt] y su contrato acepta un contador float equivalente al entero; inventario56 no coincide con requisitos realmente instalables.

Aceptación: Reconocer y canonicalizar todos los requisitos fijados, incluidos extras, preservando nombres, versiones y hashes de cada bloque y rechazando duplicados o entradas ambiguas. Derivar el catálogo completo y su distribución nativa explícita; exigir type(count) is int y correspondencia exacta entre nombres/versiones/conteo del contrato. Preservar el candidato56 rechazado y sus controles literales, preparar un companion explícito para el catálogo corregido y exigir revisión independiente. Validar después la imagen realmente construida y su inventario instalado, sin sustituir esa ejecución por el contrato estático.

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

QA-31: caducidad del ACK por fase del controlador PostgreSQL. La autorización se comprobaba al inicio, permitiendo un hijo nuevo después del vencimiento. El canario puro original y el corregido se conservan en evidence/security-pg-lease-expiry-independent-20261020/. Corrección aislada e256, integración y runtime pendientes.

UX-21 y R36 añaden el rediseño integral y las rutinas solicitadas expresamente por el usuario; ver REDISENO_WEB_Y_RUTINAS.md. No modifican ningún criterio anterior.

## Checkpoint150 — 2026-10-21

QA-32: retiro local exacto ante401 del catálogo, antes del cuerpo, con fences de snapshot/token y controles de rotación/cuenta nueva. Corregido955, peer9dfa12HTTP+23Node/3mutantes; focal local verificado.

UX-22: contador output con status implícito. Corrección503 añade sólo role=timer y aria-live=off, conserva región polite;1RED/1control→2PASS. Fuente W3C y canario64390 preservados, sin afirmar lector real ni navegador completado.

## Checkpoint152 — 2026-10-21

### QA-33 — Finalización del escáner no acreditada

El wrapper aceptaba exit1 y una lista coherente de hallazgos sin verificar finalización; Gitleaks usa exit1 también para errores y escaneos parciales. Descartaba sus diagnósticos, permitiendo aprobar una lista parcial completamente clasificada.

Aceptación: Exigir evidencia positiva de finalización completa del escáner fijado y coherencia exacta entre resumen, reporte y código de salida antes de clasificar o aceptar el gate. Rechazar errores, cancelación, timeout, omisiones, diagnósticos inesperados, resúmenes ausentes/duplicados y salidas ambiguas aunque todos los hallazgos parciales estén clasificados. Conservar RAW privado de diagnósticos y reporte con frontera verificada antes del payload, timeout externo acotado y mensajes públicos sin valores. Preservar originales y controles literales; demostrar el falso PASS antes y su rechazo después, repetir controles reales positivos/timeout y revisión independiente. Ejecutar posteriormente el escaneo completo del árbol actual; no presentar los contadores del wrapper antiguo como prueba de finalización.

Checkpoint152: hallazgo nuevo QA-33. El fullscanV8 deMain25d terminó wrapper0/raw1/43532clasificadas/0restantes/15615archivosquietos, pero el wrapper descartó los diagnósticos y no acreditó finalización. Resultado conservado, NOaceptado como gate completo. Canario Ops12RED/1control confirma falsoPASS de reporte parcial no vacío; binario real8.30.1 usa exit1 en timeout. Corrección aislada en revisión, sin cambiar reglas ni registros finitos. Producto50325 y validaciones previas de rediseño/PPL permanecen ligados a su fuente; no son invalidadas por esta limitación del escáner.

[Evidencia](evidence/root-main-r05-v8-completion-unproven-20261021/summary.json). Los controles reales y el canario no prueban la causa exacta del fullscan25d. Corrección todavía aislada; no hay escaneo corregido aceptado.

## Checkpoint153 — 2026-10-21

### QA-34 — Coherencia del helper provisional

El helper de baseline provisional aceptaba, después de recalcular su hash, madurez incompatible con el ancla semanal, publicaciones contradictorias y un ancla posterior al corte civil exclusivo. No se reprodujo como defecto de las lecturas reales ni bypass de autorización.

Aceptación: Rechazar en el helper las contradicciones derivables del ancla semanal y del período: publicaciones anteriores al ancla o ausencia de su publicación si la semana está visible, D30 maduro con D7 inmaduro, madurez imposible respecto de los extremos civiles convertidos a UTC y ancla posterior a through. Conservar incertidumbre del instante dentro de la semana, ancla anterior a from, as_of inclusivo, corte civil exclusivo y semanas con cambio de horario. Preservar canarios3RED/1control y1RED/2controles, verificar corrección con revisión independiente y no afirmar procedencia, baseline real, importador o completitud semántica poblacional.

Verificado local con3RED/1control y1RED/2controles preservados,QA43finales yRoot59dominio. [Revisión](REVISION_QA_R30_V1.md).

### QA-35 — Admisión y cierre Native finitos

El controlador NativeV6 original admitía su fixture ante un ACK SQL vencido; el canario puro preservó1RED/1control sin ejecutar SQL o procesos.

Aceptación: Rechazar ACK ausente, ambiguo, vencido o no ligado a fuente, perfil y selección antes de iniciar SQL y cada driver; exigir admisión separada para Chrome y startup real37. Conservar los22 helpers originales, aserciones y plazos; usar companions con inversas finitas y shutdown ligado a PID, generación y fuente propios. Verificar esquema/rol/pool/index reales, cierre normal y ausencia fresca de la UUID propia. Preservar canario original RED y cualquier intento rechazado; publicar ACK completo de forma atómica y no convertir cierre tardío o evidencia parcial en PASS.

58controles yNative35por4fases sobre50325aceptados;V1REJECTED se conserva. [Evidencia](evidence/security-native35-v7-v2-current35-20261021/result.json).

## Checkpoint156 — 2026-10-22

### QA-36 — Selección exacta de compra en conciliación

Problema: El nuevo trabajo privado seleccionaba la compra A, pero una lectura canónica podía describir la compra B del mismo sujeto y reparar un recurso fuera de la selección operativa.

Criterio: Cuando se selecciona una PurchaseIntent, cada lectura canónica de suscripción o pago, incluida la segunda lectura bajo lock, debe conservar exactamente esa intención además de sujeto y recurso. Un desvío debe revertir el recurso completo, conservar revisión manual y no modificar derechos de otra compra. Mantener controles legítimos de ambos proveedores y conservar el canario literal RED/PASS.

Revisión: Root independiente: cuatro canarios literales, dos RED/1196 y cuatro PASS/7b7; final10/cdda y137/Main. Autor añadió cambios entre primera/segunda lectura para Stripe y MercadoPago.

### QA-37 — Ownership de Session del trabajo de conciliación

Problema: Un puerto de fábrica deliberadamente incorrecto que devolvía una Session prestada con transacción activa podía provocar rollback/cierre de trabajo del llamador al rechazarla.

Criterio: Construir la Session bajo contexto neutral y asumir ownership sólo después de verificar que no tiene transacción activa. Rechazar una Session prestada activa sin rollback, close o invalidate de esa instancia, conservar el cursor y restaurar el ContextVar del llamador. Las Session propias deben seguir cerrándose antes de confirmar resultado. Conservar canarios plan/apply RED/PASS y controles de contexto y avance finito.

Revisión: Root independiente: seis canarios literales, dos RED/6758 y cuatro controles PASS; final10/cdda y137/Main. El defecto se refiere al puerto mal configurado, sin afirmar fallo de SessionLocal por defecto o de HTTP.

### QA-38 — Autoridad de fuente del CLI de archivos históricos

Problema: El CLI nuevo heredaba GIT_DIR y aceptaba como HEAD otro valor de un namespace sintético aunque sus archivos no cambiaran. La reproducción no ejecutó DB ni PUT.

Criterio: Obtener la identidad de fuente del checkout propio mediante ejecutable Git absoluto y argumentos fijos, sin shell, con timeout acotado y stderr privado; eliminar autoridad GIT_* heredada y fijar configuración/prompt/locks. Conservar canario literal con namespace sintético RED y control legítimo, sin atribuir esa fixture a historia real ni a la aplicación HTTP.

Revisión: Seguridad autora conservó1RED/1control en09ab; Backend independiente repitió39 originales y9 propios. Root leyó source_check y ejecutó los dos canarios enMain137. No se afirma procedencia de archivos históricos reales.

### QA-39 — Privacidad de errores de argumentos de conciliación

Problema: argparse procesaba int/float fuera de la frontera opaca del CLI y reflejaba valores inválidos en stderr con salida2, en contra del contrato de entrada inválida64.

Criterio: Rechazar argumentos de consola inválidos sin reflejar valores, rutas ni detalle interno en stdout/stderr; devolver64 con el JSON fijo reconciliation_invalid_input. Mantener --help con salida0 sin abrir manifiesto ni importar base de datos y conservar canarios independientes literales RED/PASS.

Revisión: Seguridad independiente conservó2RED/1control; autor preservó5RED/1help y6PASS. Root revisó el fix y ejecutó literalmente los3 de seguridad dentro del gate137. Son fases distintas, sin sumar replays como nuevos criterios.

## Checkpoint157 — 2026-10-22

### QA-40 — Identidad del destino durante copia/ACL/readback

Problema: La herramienta8782 permitía sustituir la identidad destino entre create/ACL/reopen y sobrescribir un outside sintético en E. No afectó fuentes C: C0. El resultado RED original permanece intacto.

Criterio: Mantener la identidad CREATE_NEW del destino desde la instalación y lectura de su DACL hasta escritura, fsync, SHA completo y retirada fuente; conservar el mismo HANDLE/FD y no reabrir por ruta para escribir payload. Conservar la sustitución de identidad sintética original, validar rechazos y ciclo normal/error con revisión independiente, sin atribuir el outside de E a datos reales C ni inferir aceptación de todas las raíces.

Revisión:41a14autorPASS y9peerPASS en fases separadas; first32real32Rootaceptadas y32peerfullreadback. El peer no repitió literalmente la sustitución8782; observó los mismos descriptores/identidades y errores acotados. No se afirma ausencia global de carreras ni aceptación de4207raíces.

### QA-41 — Ausencia estricta y propagación de errores de metadatos

Problema:608usaba os.path.lexists y convertía PermissionError/OSError31 de os.lstat simulado en False:1PASS/2FAIL. No es evidencia de fallo real del sistema de archivos.

Criterio: Decidir ausencia mediante os.lstat directo y devolver False sólo ante FileNotFoundError; propagar PermissionError y cualquier otro OSError. Conservar los canarios literales con os.lstat simulado, su RED original y los intentos de transporte rechazados; verificar las tres ramas y el ciclo finito de la herramienta sin afirmar un fallo real del sistema de archivos ni trasladar capacidad histórica a una fuente nueva.

Revisión:34adstrictos.lstat pasa3Rootliterales y7peer pequeños E. d8metadata0PASS/3FAIL/0mockcalls quedó rechazado porque Path.lstat invocó os.stat; no aceptar sus booleanos de no acceso FS ni atribuir C. WinAPI55aigual608; capacidad8193de fuente anterior no reejecutada. SHAarchivo sellado Artifact pendiente; resultados/review/freeze concretos sí disponibles. Evidencia [curada](evidence/migration-c-to-e-checkpoint157-20261022/summary.json), sin reescribir RAW.


## Checkpoint159 — 2026-10-22

### QA-42 — Bootstrap privado CI57 al importar desde pytest

Problema: El módulo CI57 inicializaba ARTIFACT sólo en __main__; pytest importaba los18 unittest y test05 fallaba en directory con NoneType.

Criterio: Permitir ejecutar los18 controles CI57 originales tanto mediante pytest como por CLI explícito sin alterar métodos, aserciones, directory ni main. Si ARTIFACT es None, crear ámbito temporal privado antes del payload y restaurar ARTIFACT/SERIAL mediante cleanups incluso al fallar setUpClass; no reemplazar ni borrar una raíz CLI ya provista. Conservar el RED original, inversa literal y revisión independiente; no presentar estas fixtures como construcción o aceptación de imagen.

Revisión: Autor18pytest/18CLI y3bootstrap en fases; peer6 propios PASS con inversa completa/WinAPI DACL real; RootMain21 PASS18.860s,21IDs únicos,12fuentes seleccionadas quietas. REDtest05 real preservado. Replays de los18 no son criterios adicionales.

### QA-43 — Identidad admitida del plan antes de ATTEMPT, ACK y apply

Problema: El controlador366 permitía que una sustitución sintética de la raíz entre lstat y prepare alcanzara apply con un plan de identidad no admitida;1RED/1control en E, sin C.

Criterio: Revalidar la identidad original admitida y el ámbito exacto del plan retornado por prepare antes de persistir ATTEMPT, emitir ACK por raíz o ejecutar apply. Rechazar sustitución de inode/identidad o raíz ajena conservando los orígenes y sin apply para la sustitución. Preservar los dos canarios literales RED/PASS, el archivo de12 criterios originales y la revisión independiente; las fixtures E no acreditan ejecución real41a/34ad ni retirada C.

Revisión: Binding literal source366:1PASS/1FAIL; source2b22:2PASS/0FAIL y12 originales PASS. Root repite12+2 sobreeeaa con mismos cuerpos; peer7 actual valida además sustitución/expiración. Son fases finitas E, sin ACK ni ejecución realC.

### QA-44 — COMPLETE debe ser el estado terminal del journal validado

Problema: El controlador2b22 aceptaba un journal íntegro por hash con COMPLETE histórico seguido por TARGET_CREATED; peer conservó1RED en E, sin pérdida C observada.

Criterio: Exigir que la última fila del journal completo validado sea COMPLETE y conserve los campos y valores verdaderos requeridos por el protocolo antes de aceptar un resultado previo, reanudarlo o declarar cierre. Un COMPLETE histórico seguido de otro evento no concede autoridad terminal. Mantener la validación de cadena, recibos e identidades; conservar el RED literal y reparar sólo la guarda necesaria con inversa exacta, sin atribuir cierre real4207 o ejecución C a las fixtures.

Revisión: Root cambia una guarda2b22→eeaa con resto de bytes exacto, motor059/Win55a intactos. Replays Root12+2 PASS y peer7 PASS incluido el mismo RED terminal→PASS. Resultado actual C/Root1 y verificación agregada siguen pendientes.

Evidencia [curada](evidence/checkpoint159-web-continuity-20261022/summary.json); no se incluyen payloads negativos privados.

## Checkpoint160 — 2026-10-22

### QA-45 — Asignación de directorios y readback de payload

Problema: El auditor independiente ef717 comparaba size del directorio destino contra el plan del origen. Un directorio E con churn real conservaba asignación 393216 y su copia tenía 0, con inventario y payload iguales; el predicado producía un falso rechazo. No se observó pérdida de datos por este defecto del auditor.

Criterio: Comparar tamaño y SHA como integridad de payload para archivos, sin exigir que el tamaño nativo de asignación de un directorio destino coincida con el del origen. Para directorios conservar inventario completo, identidades del destino, atributos, creation/mtime y permisos; su tamaño y demás metadatos nativos deben permanecer estables durante el readback. Conservar el falso rechazo literal ef717, la reparación finita 290618, los nueve controles originales y la revisión independiente. No alterar motores ni recibos anteriores y no atribuir la auditoría de una raíz al cierre de las 4207 admitidas.

Revisión: RED literal ef717 preservado. Fix 290618 pasa tres controles del witness MFT, nueve controles originales literales y cuatro peer independientes en fases separadas. Root revisó el delta; la auditoría real autorizada Root1 pasó con 38.169 archivos/1.625.941.057 bytes/43.960 entradas, salida 0 y ausencia lstat final C, sin payload C. R37 sigue en_curso; no se atribuye cierre 4207, PG o CI global.

[Resumen160](evidence/checkpoint160-web-continuity-20261022/summary.json), [revisión160](evidence/checkpoint160-web-continuity-20261022/REVIEW.md).

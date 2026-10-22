# Cambios de comportamiento

## Integración de recuperación28 y gates

Recuperación de cuenta c297ea9/33d5980: solicitudes uniformes y acotadas, token opaco de un uso con digest persistido, confirmación transaccional que cambia contraseña/revoca sesiones y cabeceras privadas también en errores de método.202 indica recepción, no entrega; cola local no durable y ningún correo real enviado. Esquema28 conserva26tablas/20familias RLS. Pruebas QA94aa552 conservan restore27 completo y añaden restore28 propio.

CI5ba98c6/7cf4e6c exige21reportesPG,restore28 ymarker28. La revisión independiente rechazó dos bypass de referencias y sustituciones de docstring por código antes de aceptar. Composición integrada:6propias yCIverify-only verdes,606fuentes estables. [Resumen](evidence/recovery28-main-composition-20261019/summary.json). El gate amplio2064 sigue vinculado a7bde30b; R34 permanece aislado porSEC07.

Escáner0c6cfae/31ebb2f: excepciones finitas y dos pines completos revisados para fragmentaciónGitleaks; JSON malformado falla cerrado. Scan41708e5:3028archivos estables,2raw/2clasificados/0restantes; no cubre las fuentes posteriores. [Contrato](ESCANER_FRAGMENTACION.md).

Commit `166038f88b211c52f0d149ce550880795361707c`, lote A1 local:

- Pro ya no se concede mediante POST de preferencias, suscripción incompleta ni redirect. Compra persistida antes del proveedor, conciliación Stripe/MP compartida y cuota individual reservada con idempotencia; callbacks viejos no revocan otra compra vigente. Compras históricas sin mapping y sandbox real siguen abiertos.
- Identidad consistente en contraseña/Google/refresh, roles/tenant persistidos, permisos desconocidos denegados y VIEWER sin alta. Logout incrementa versión de sesión; se retiró mantenimiento público. Tokens legacy tienen transición explícita; no hubo cierre de sesiones reales.
- DTOs comunes rechazan rangos inválidos y NaN/infinito. Exclusiones no dependen del pago, catálogo por solicitud inmutable llega a selectores/ajustes y valida resultado antes del PDF. Notas libres no se presentan como garantías clínicas; etiquetas históricas se representan como texto.
- Plan JSON y plan_id exacto se persisten junto con contadores. Tests ya no heredan destinos reales ni silencian preparación; fixtures/orden/UTF-8 y permisos Windows corregidos. Tres tests HTML pasan por la app SaaS real.
- Backup sin fuente falla; respaldo cifrado y manifiesto autenticado preceden restore a destino vacío. En R08 falta recuperar el esquema candidato/objetos históricos y verificar backups nativos.
- Fuente de catálogo compartida inicial, Free 10 aprobado, locks separados por OS con hashes; tzdata explícita evita fallos de zona horaria que el venv histórico ocultaba. Soporte desktop se mantiene; la resolución y pruebas GUI candidatas aún tienen su gate propio.

Gate congelado: 207 aprobadas, cero omisiones, 42.753 s; revisiones independientes enlazadas en VALIDACION/QA_R05. El commit no cierra por sí solo R01/R02/R05/R06/R08/R09/R10/R18/R19/R33.

Seguimiento abierto después de A1: carrera de GET al crear/resetear cuota; cuotas B2B y multiproceso; FeatureGate aceptaba moroso/expirado (tres regresiones reproducidas y corrección local en revisión); esquema/migraciones; compra y portal frontend, accesibilidad y diario persistente.

Compatibilidad prevista: parámetros opcionales del catálogo para consumidores desktop/legacy, precios sin cambios arbitrarios, tokens previos bajo transición explícita y migración aditiva. El estado final debe contrastarse con los contratos implementados antes de release.

## Hitos integrados posteriores a A1

- `af177b1` unifica catálogo y derechos efectivos: Free10 clientes, un plan por cliente/día y diez por gimnasio/día según las tres decisiones del usuario; desktop sigue soportado. Estados/expiración se resuelven de manera central. El catálogo no reemplaza las reservas atómicas B2B que siguen en revisión.
- `c769667` impide que un GET concurrente vuelva a crear/resetear cuota individual mientras otro proceso reserva el último crédito. Tres casos PostgreSQL multiproceso verifican el recorrido.
- `e8a6806` sustituye DDL/fallback de arranque por migración explícita, firma estructural y fallo no cero. R03 conserva su contrato de22 tablas y restore completo. `f325fc4` prepara asociaciones de proveedor y activaciones emitidas en un contrato nuevo de23 tablas, sin reinterpretar compras o licencias huérfanas.
- `501ceaa` activa17 familias RLS en bases de prueba, contexto por transacción y startup que rechaza privilegios de propietario/SUPER/BYPASS. Migrador y aplicación usan usuarios distintos; el servidor no hereda la credencial migradora. No se cambiaron roles ni políticas productivas. [Contrato](AISLAMIENTO.md).
- `b03e20a` conecta equipo e invitaciones con autoridad comercial persistida, token de un uso, CAS de roles y revocación de sesiones. Una expulsión conserva el espacio personal. Se mantiene compatibilidad acotada de enlaces históricos; cuentas con correo ya existente requieren el flujo de consentimiento aún pendiente. `19298e7` aclara el parseo JS y repite siete recorridos reales. [Contrato](EQUIPO.md).
- `4d03300`/`501ceaa` exigen propietario y licencia emitida vigente para activar hardware; el prefijo no concede derechos. Se impide sobrescribir hardware ajeno y se conserva el vencimiento emitido, también con sesiones PostgreSQL en México. La caché online exige licencia local verificable. [Alcance pendiente desktop](LICENCIAS.md).
- `0a0b6d4` hace atómico INCR/TTL Redis y acota fallos: las acciones sensibles fallan antes del handler si no hay limitador; lecturas/logout tienen degradación local limitada. La prueba con Redis real queda en CI, pendiente de ejecución. [Contrato](REDIS.md).
- `c45a71c` conecta compra/portal/estado de suscripción y corrige móvil/teclado con evidencia acotada; R11 añade recorridos completos auth/API/SQLite. No se atribuye entrega de correo ni lector de pantalla a esas pruebas.
- `abc896f` añade objetos privados inmutables con namespace de propietario, integridad y lectura acotada en volumen/S3 compatible. Todavía no cambia las rutas PDF/logo. [Contrato y límites](ALMACENAMIENTO.md).
- `9a53215` añade normalización de parámetros UTC sin cambiar tipos físicos ni datos históricos.32 pruebas independientes distinguen la corrección del desfase del driver. Aún sin adopción en modelos. [Contrato](UTC_DATETIME.md).

`9b97068` añade factory R07 con configuración explícita,32 pruebas independientes y sin descubrimiento de credenciales/endpoints ni fallback. `822de09` conecta Docker al lock con hashes y alinea manifest desktop con los targets ensayados; la revisión estática independiente no ejecuta la imagen.

`b81cfc1` integra reserva profesional antes de CPU, capacidad de clientes bajo lock de cuenta y ledger24 con RLS. Un retry con la misma clave/contenido devuelve la respuesta guardada; publicación y consumo no se compensan al perder respuesta o borrar FK. El helper de compensación protege también rollback y responde503 de reconciliación si no puede confirmar liberación, sin parámetros SQL en logs. Los nombres PDF son UUID y el worker está compartido entre web/API. [Contrato y pendientes UI/worker](B2B_CUOTAS.md).

`dbb6af5` integra exportación personal readonly en ambos factories y perfil, con descarga acotada por partes, manifiesto, sin datos de la cartera profesional ni persistencia de exportación en navegador. También contiene excepciones globales/alertas automáticas: sólo clase/contador/verbo HTTP reconocido, sin traceback, SQL ni metadata libre. No sustituye el workflow de borrado/retención ni sanea todos los sinks. [Alcance](PRIVACIDAD.md).

`e3039c2` incorpora gates y evidencia independiente:1621 aprobadas serial y con dos workers/orden mezclado, con387 Python/deps y55 frontend estables. Una omisión de symlink Windows queda explícita. La suite conserva sus límites de SQLite/dobles; las integraciones PG/restore y browser tienen gates separados. Las evidencias de cada hito se conservan por fuente/entorno. Ninguno de estos commits se publicó ni se desplegó.

`5bb5395` adopta UTC en52 columnas de instantes: un datetime con offset se convierte a UTC antes de escribir en TIMESTAMP sin zona. Se conservan dos fechas civiles y todos los resultados históricos. El cambio evita el desfase y vencimiento prematuro reproducidos bajo México; no modifica esquema ni intenta reparar historia.

`4e22852` añade contratos preparatorios del diario con35 pruebas, sin API/persistencia; `bc6804c` prepara IaC con SDK fijado, preservación de variables y guardas de destino/digest. La definición bloquea apply y necesita adopción/import real y prueba del loader/árbol final antes de aplicarse.

`31ad545` permite descargar el PDF exacto de un plan y conserva no-referrer en respuestas privadas; corrige el override global reproducido también en exportación. `93a9e1d` limita logs y telemetría de autenticación/correo a categorías, preserva auditoría local y añade adjunto PDF autorizado por bytes sin abrir archivos en ese camino. Storage25 y correcciones nuevas del wizard permanecen WIP en revisión.

## Checkpoint 0459b0f — Documentos privados y UI revisados

ddaf71a integra UI B2B idempotente, modal y descarte de respuesta al cambiar sesión sobre evidencia snapshot24.74d66e8 integra esquema25 con StoredObject y dos referencias nullable;0459b0f integra publicación/lectura privada, branding, configuración explícita en ambas factories y dependencias fijadas. El PDF exacto y el adjunto por bytes conservan sus lotes previos. Los objetos históricos mantienen referencia nula sin backfill, y un error de proveedor no elige otro backend. Restore25 y recorridos navegador tienen gates independientes. Ninguna infraestructura externa fue creada.

Hallazgos abiertos: SEC02 confirmado con dos casos rojos de refresh en memoria; riesgo individual postcommit deducido, en reproducción. Inventario histórico readonly y corrección cleanup en curso. No se ejecutó una suite completa del head nuevo ni scan posterior a b20e071.

## Checkpoint integrado26 / sesiones / CI

`bd6b067` integra inventario histórico readonly sin apply ni atribución de procedencia; `0e8cd42` compara expiración Float por epoch, conserva UTC de auditoría y hace visibles errores de cleanup mediante exit1 sin parámetros sensibles. Parámetros30/90 existentes, sin scheduler o política legal nueva.

`34d8fb1` publica Plan/objeto ready/consumo individual y marcador en una transacción; conserva consumo tras respuesta perdida o FKNULL. Captura periodo de suscripción bajo lock y filtra Plan/Cliente por mismo dueño y soft-delete. Legacy ambiguo no se reembolsa ni se enlaza por tiempo. El protocolo nuevo requiere drenar workers antiguos al migrar; no se aplicó live.

`754d56d` vincula refresh/reintentos/lecturas al contexto de sesión inicial y comparte una promesa que siempre resuelve sus consumidores. Fallos parciales de Storage bloquean I/O hasta guardar o limpiar completamente el par.74 VM independientes y navegador actual aceptan esta contención por instancia; reload/cross-tab y otros escritores siguen abiertos. El candidato histórico275 se preservó por SHA exacto en copia, sin inventar commit.

`6d33b9e` exige reportes Node tipados/no vacíos,17 JUnit PG y cinco fixtures navegador con logs diferenciados. QA actual36 grupos/19 pantallas más3 Storage; serial1813/1skip Windows, n2shuffle1813/1skip en133.73s,519 fuentes y89 paquetes estables. No se ejecutó Actions, imagen Linux ni Redis real. Desktop41ad55f y UI individual se desarrollan en worktrees separados y aún no integrados.

## Checkpoint local 19 de octubre: UI, disponibilidad y procedencia

Integrados c11256a (UI personal40fd2af),0fa124e (SEC037321d3b) y desktop3930398/171a8f0/9f3f32e. Estadísticas ba4deb4 ya tiene QA independiente0e4bc07. Evidencias del autor y de QA se mantienen separadas, incluida reproducción de400 tras commit, HTML con CSP activa, source flags y controles binarios/CR aislado.

La receta desktop exige bytes exactos para controles ASCII/DEL/CR aislado; ESC es conservador aunque Git lo considere texto. La primera compilación9f3f32e rechazó un log ANSI convertido por autocrlf antes de Analysis; fuentes estables y diagnóstico preservados. Se ensaya el mismo commit en checkout LF sin cambiar configuración Git. Todavía sin artefacto aceptado, Inno, firma o publicación.

CI incorpora operación personal18+2 y sexta fixture15/8pantallas con formatos tipados de reporte. QA encontró que dos tests batch Windows se colectarían con skip en webUbuntu: ahora se enrutan explícitamente al targetWindows y se excluyen por nombre en la recetaLinux; tests portables se mantienen en ambos targets desktop. Guard exige los dosJUnit no vacíos y sin skips/fallos/errores.91 canarios del guard y9 del nuevo routing aceptados independientemente, sin ejecución remota.

Build Windows real9f3f32e terminó0/343.82s,78 pruebas+7subtests/44.46s,1688fuentes estables yZIP122774966 bytes. Operación39/39 independientes verifica archivos/CRC/PE/recursos/código embebido acotado/Qt nonce con perfil propio. Se preservan tres falsas alertas iniciales del verificador (BOM Inno y CA público certifi), corregidas sólo en harness. NuevoOPS10 retiene distribución por captura de referencia no acreditada; receta se corrige antes de nuevo build. No instalación/firma/publicación.

Checkpoint99: backend diario27 integrado423296f tras QA/restore y seguridad; OPS10 integrado bca89bb tras97 casos+3CLI; SDK169241a aceptado22+17. UI606 retenida por cuatro negativos; se registra SEC04 sin alterar los92 criterios originales. Documentacion y pruebas independientes de27 se conservan por lote; nuevo ZIP y gates amplios siguen pendientes.

CI27 aceptado:19 reportesPG obligatorios, restore27 explícito preservando fixture26, OPS10 en ambos targetsdesktop. QA15 canarios guard,60Bash,73 referencias/81 fuentes estables; Windows97real20.99s, colecciónLinux95local. Sin Actions/Linux/PG nuevos. Quality27:429 fuentes parseadas,F8210,Bandit6base/0nuevos.

## Aceptación integrada27, UI y métricas

e0f74da/06d291b/6abe08c conectan el diario persistente y corrigen las continuaciones de exportación: contexto canónico y revisión antes/después de cada frontera, invalidación síncrona de parte/URLs/acciones y guards tras controles que pueden invalidar.0c55b16 confirma logout sólo después del commit con success=true. Los negativos previos permanecen en evidencia; no se toca legado localStorage sin dueño verificable.

7bde30b elimina direcciones/rutas concretas de memoria y errores de métricas; usa rutas declaradas y fallback fijo. Seguridad independiente aceptó15propios+63replay; el mismo driver conserva12rojos/3controles antes.5c9e097 conserva esos15 en suite mediante copia de funciones/aserciones AST idénticas, gate focal15/15.

El gate amplio7bde30b pasó2064/1skip en serial y n2; no se suman15posteriores ni gates de otros entornos. Desktop7bde30b reemplaza el ensayo9f:51controlesbundle/ZIP/Qt y27payloadInno exacto; OPS10 ausente. Setup compilado sin ejecutar, instalar o firmar. db368a8 añade caracterización local1400HTTP sin cambiar producto; revela historial ilimitado pendiente de paginar. R16/schema28 sigue aislado y no integrado.

## Checkpoint104: historial y oferta pública integrados

Historial antes ilimitado pasa a summaries50/default,200máximo, cursor HMAC por identidad/perfil y carga explícita de páginas. Boundary privado conserva cabeceras también en errores422/405/500. Integrados21b7ed9/924dd6f/fdfc9cb; seguridad24 y composición36 con recuperación28 aceptadas. R34 no declara todavía mejora de p95 PostgreSQL.

Landing integrada647eda8/1f9bdb1 muestra catálogo canónico B2B/B2C, CTA móvil por audiencia, acceso rápido, ejemplo sintético y FAQ factual; registro inicializa modo correcto. Retirados los dos HTML comerciales huérfanos tras comprobar ausencia de montaje y referencias; RAW originales fuera del entregable y Git preservados. R29/UX-16 verificados localmente por QA y composición20+6; sin publicación ni compras. [QA historial](evidence/history-independent-20261019/final-summary.json),[QA landing](evidence/landing-independent-20261019/final-summary.json).

## Checkpoint105: regresión integrada y candidatos separados

a753b2c corrige únicamente la aserción de un test vecino que esperaba checkout sinuso ya retirado;conserva15nodosAST previos yresto del módulo. Original2fallos preservado;20focales y ambos amplios2360/1skip verdes. No runtime modificado por elfix.

Contrato R12v2 documentado4d537e4/6b0dc01 y aceptado porseguridad para implementar29 aislado;productoMAIN sigue28. Nuevo runtimeLinux fijaCPython3.12.15,pip26.2.1 yliblzma5u2 porfuentes oficiales/digest/hash;build2 yPythonSCA verdes,OS/startup noaceptados todavía. Windows3.12.15 separado tiene83paquetes/OSV0 y45+97tests verdes;artefactosdesktop anteriores permanecen históricos,porreconstruir.

52af400 integra CI para23VM dehistorial ydosfixturesactuales (history10,landing8),conguardversionado yprimariasfijadas;QAindependienteycomposiciónaceptadas. Conserva21PG/restore28/7fixtures/162VM anteriores ynoejecutaActions poresteincremento.

Checkpoint106: Dockerbase/bootstrap/liblzma integrado tras seguridad independiente;OS71IDs abiertos. Desktop66 recompilado con3.12.15,ZIP4966896c/Setup5651f418,pendiente payloadindependiente. R34medido200HTTP;prototipo adicional deíndice/lectoraislado,noMAIN. R12núcleo29 enQA/seguridad yAPI/UI/restore aún aislados.

Checkpoint107: selladas la revisión independiente desktop66 (93 controles verdes, payload1215 exacto, Python3.12.15/OpenSSL3.5.9/Expat2.8.5/Qt6.8.3; sin ejecutar Setup) y las revisiones R12V1/V2. QA95 de V1 no cerró sus tres fallos de seguridad; V2 1aac pasó los mismos21 criterios independientes, sin cambiar el driver. Fuentes y paquetes estables; bases propias cerradas. Aceptación limitada al coreV2, sin casts/restore/API ni integración29. Los RAW y manifiestos originales permanecen exactos y se añaden atributos binarios sólo a estas nuevas carpetas para conservarlos en Git.


## Checkpoint 108

Checkpoint108 sólo incorpora evidencia/documentación: aceptación independiente del índice30 aún aislado; revisión API29 y reparaciones de cabeceras/correlación en939 aún aisladas; inventario nativo y gate symlink de imagen99c. Nuevo SEC09 sobreOpenSSL vendorizado. No cambia producto enMAIN. Se registra el fallo real debootstrapCREATEROLE sin reinterpretar los ensayos anteriores con administrador.


## Checkpoint 109

Integrado5d0e668:c4 elimina únicamenteCREATEROLE/GRANTglobales para permitir dueño de esquemaNOCREATEROLE;políticas/función/revisiones/targets yACLprevios sin cambio. Repairhistórico justificado porque una revisión posterior no puede superar el fallo previo. FixUIec029 permanece separado deMAIN yse registraUX-18. No27/29/30retargeting para ocultar históricos.


## Checkpoint 110

Se preservan aceptaciones R12ec y del delta estático d038; no se integra código29/30 ni emisor en este checkpoint. Se actualiza sólo validación UX-18 respecto del candidato aceptado; criterios exactos106 intactos. CI1 tiene dos bypass de ejecutables y dos de archivo histórico reproducidos por QA; correcciones aisladas requieren replay independiente.


## Checkpoint 111

Se integra29/CI29 con ancestry fd real, los16 targets históricos antiguos y c4 conservados. Se sella regresión de la misma fuente integrada. UX-18 pasa a verificado local tras integración y revisiones;106 criterios exactos intactos.30/R23/emisor/Docker nuevos siguen aislados.


## Checkpoint 112

Se integra30 y CI30 con ancestry29 real. Se registraSEC10 sin renumerar106 previos; total107. Se sella aceptación independiente de navegador/CI30 y triage estático. R23/expiración,MFA31,R24 y Docker nuevos aún no integrados.


## Checkpoint 113

Se sella regresión amplia del esquema30 integrado. Se autentican147+manifest de composición R23 y42+manifest de corrección de foco; ambos aislados, sin presentar CI adicional como integrado.107 criterios exactos preservados.


## Checkpoint 114

Se registra SEC11:108 total,107 criterios previos exactos. Se sella aceptación CI573 y M2 estático; no merge de esas fuentes en este checkpoint. R24/MFA31 están aislados, R25 diseño y R35 evaluación inicial explícitos.


## Checkpoint 115

R23/expiración/CI573 integrado3643; no nuevoDDL. Estecheckpoint sólo documentación/evidencia. R24headers4042,SEC11/531 yMFA31 no se atribuyen aMAIN.


## Checkpoint 116

SEC11 integrado5949 yR24 parcialbd3 con cabeceras privadas en todoslos errores de diario. Datos propios confirmados sobreviven revocación de fuente; nuevas escrituras se rechazan. Se registraSEC12 candidatoMFA, sin31 integrado. ProyeccionesSSR publican hashesRAW yredacciones puntuales sin modificar originales.


## Checkpoint 117

Se sella gate actualR23/R24/SEC11 yse registraSEC13 de fuente31aislada.78d27key y8b64privacidad están fueraMAIN ypendientes de revisión posterior. No nuevo producto encheckpoint.


## Checkpoint 118

Se sellan revisiones independientes de MFA, su composición UI aislada y el diagnóstico del pool. La rama principal no cambia producto ni esquema. En la candidata da343 se ajustan veinte textos en tres archivos; la inversa reconstruye exactamente los bytes anteriores. Las pruebas de invitación se adaptan con MFA real y tres expectativas de status cambian por una precedencia deliberada de autorización, documentada y aún sin integrar.


## Checkpoint119

MAIN sólo añade documentación/evidencias. Candidata aislada compone5testsDAB en2010, nuevafixturemember31 en102f ydosinserciones UI4a para retirar resumenMFAobsoleto. Unliteral deesperabrowserc669 siguecopyrevisado, sinotrosassertscambiados. SeañadenQA-12yUX-19sinrenumerar.


## Checkpoint 120

Se incorpora documentación de la aceptación focal de fixtures, y se preserva e0 como preimagen CI incompleta. MAIN no cambia producto ni esquema. La candidata bd348 incorpora el delta CI e0 para revisión; sus gates no están aceptados.


## Checkpoint 121

MAIN sólo registra seis hallazgos y evidencia. CIed4 repara CLI, snapshot y rol obligatorio; de69 añade un único header auténtico. La candidataR17 monta observabilidad protegida y cuenta errores500 sin guardar detalles. La adaptación de fixtures Google/publicación no altera producto. R25 sigue documental.


## Checkpoint122

SEC14 añade cabeceras privadas para respuestas de método405 ylector500 de tres rutas operativas exactas. Mergeaislado38b integraCIed4;5637 integraR17b500. MAIN sólo registra evidencia/criterios; no producto31 integrado todavía.


## Checkpoint 123

La candidata aislada809 integra fixtures79 después del peer, preservando producto y CI. Expat72 corrige call, visibilidad y gates sin cambiar pines, parche,31inputs ni12locks. Backend/UI R25 comenzaron en ramas separadas; MAIN sólo registra evidencia y estado.


## Checkpoint124

SEC15 añade identidadSVmáximo válida y guard409 de capacidad antes de cambiar factor, sin wrap/decremento ni assertions antiguas alteradas. MAIN sólo registra evidencia. Runtimec538 combinaapp809+native72;366Gitblobs contextoconSHA22fc3b52, sin secretos/DB/docs/tests/assetsreferencia. R25router montado ywirev1 fijo, sinproducto32 aceptado.


## Checkpoint125

MAIN sólo incorpora evidencia y control, sin producto31/32. Cambios aislados: loggerAlembic474, clocks9b14/9ab, exportprivate200295 y CSSef9; composiciónUI345. Backend32bd0501 ofrece medidas explícitas, consentimientos append-only/CAS y lector limitado; UI8dc conserva RAMfences y export8. Las reparaciones no cambian contratos clínicos/comerciales. Fuenteimagenf74=app6a75+native72+logger474; contextoa644366Gitblobs. Se conservan todos los befores y diagnósticos rechazados.


## Checkpoint126

MAIN sólo registra pruebas y control. Runtimef74 app6a75/native72/logger474 medido con su USERreal y firststartup; noatribución32. Nuevo retiro API/UI permanece en WT independientes desde345 conwire5b6de9 congelado. Ningún cambio producto en este checkpoint.


## Checkpoint127

MAIN incorpora sólo control/evidencia. Composición aislada219f89 integra fcfc+UIde216+de506 con bytes exactos; no se atribuyen broads31 a32. UI tiene32paths de evidencia incluidos atributos (31además del archivo de atributos). Dos fallos de preparación del import se corrigieron antes de escribir: manifestGoogle excluye atributos y UI31contaba sin ellos. No cambian producto ni resultados.


## Checkpoint128

Integración local real desde227: MFA31, progreso/mediciones32, lector y consentimientos, exportación y UI/retiro público. Fuentes y tests de la candidata se copian exactamente; control/evidencias históricos de MAIN se conservan. No se altera Dockerfile ni locks. El retiro invalida sólo su Session nueva ante close fallido; el resto del módulo y servicio permanecen exactos. Google33 no se integra todavía.


## Checkpoint129

MAIN integra Google33 por issuer/sub, alta nueva vacía y enlace/desenlace explícitos. SEC17 revisa la composición3587. La coincidencia de correo no adopta una cuenta existente. La continuidad Google-only con sub histórico desconocido y la pérdida total de factores siguen pendientes. Los locks web/test/desktop incorporan las tres dependencias de verificación Google del autor33:google-auth2.62.0,pyasn1 0.6.4 ypyasn1-modules0.4.2. Entorno propio92; WEB89 permanece intacto. Dockerfile no cambia. Imagen,SBOM ySCA final vigentes siguen pendientes; el artefacto31 no se reatribuye. Diseño aprobado con propuestas UI77f179 ybackend844beab. No hay backend34 ni consumidor34 integrados. Backend implementa enWT propia desde3587: tareas/eventos durables,causa,próximo paso,responsable actual,CAS,idempotencia,historia y métricas de declaraciones guardadas. Nutri sólo accede a sus asignadas sin stats globales. Sin cobro inferido,contacto automático ni texto sanitario libre. El código yDDL34 requieren QA/SEC.

## Checkpoint130

Google33: corrección8a5e integra QA-17 con peer12SQLite+11PG PASS. La carrera HTTP original mantiene200+409 y cuenta única. No cierra continuidad Google-only histórica ni recuperación total. Backend34 integra el fix8a5e y avanza con mecanismos, HTTP y límites SQLite; router montado en ambas factories sólo enWT34. Wirev1 33bfe88f fijado con ACK técnico de coordinación; aún sin backend/UI34 integrados o PG34 ejecutado.

## Checkpoint131

Sólo dos paths de producto R05: nuevo ZIPv2 ybinding de tres literales. Inversa RAW/AST exacta;sin nuevas excepciones de algoritmo. Registro finito R05v2 integrado desde4f4ed7:689archivos/45.910pins, unión disjunta de534/31.394 anteriores y155/14.516 nuevos. SECf008 verifica14.557ocurrencias nuevas y113controles; QA verifica separadamente el binding exacto de tres literales. Autor110casos mantenidos PASS, Ruff/pip0 yfuente quieta. ZIPv1 yalgoritmo conservados. Escaneo real sobre4f4ed7:12.793archivos,44.433hallazgos brutos,42.830clasificados y1.603bloqueantes; salida1, sin aceptación global. Los archivos de evidencia posteriores no se reatribuyen al árbol escaneado. CI33 c86 ysu PG240 conservanv1 hasta composición explícita.

## Checkpoint132

Se incorpora sólo evidencia yregistro; ningún producto34 oCIc86 cambiaMAIN en este checkpoint.

## Checkpoint133

CI33 integrado conservando la cadena completa de c86 ysu delta original de82 fuentes desdeCOMMON3587. La composición con MAIN132/R05v2 modifica sólo el verifier respecto a c86:pinLF del módulo,pinRAW del ZIPc5eb ybase d8 explícitos; el guard de producto separa docs yel gateR05 sigue escaneándolos completos. QA110R05/49críticos PASS,9binding ycontroles de documento/3rechazos de producto,lock,target; verificador final193canarios workflow y157bloquesBash PASS,también replay ROOT enMAIN. Conserva20reportes/240IDs actuales33,5reportes/38IDs históricos32 ylos oráculos110/49. Offline902 yPG240 anteriores corresponden a c86/R05v1; no se reatribuyen aesta composición. No broad actual,Actions,Chrome,imagen oLinux aceptados por esta fase;R05global sigueRED.

## Checkpoint134

Sólo evidencia/control,sin incorporar aún productos34/35. Candidato35 fuente55a3 tiene162casosSQLitePASS con perfiles/DTO/persistencia/cuota/PDFreal yguard final; ambasfactories gimnasio ypersonal sóloSaaS. Contratos anteriores intactos; downgrade no borra declaraciones. Cambio de restricciones durantePDF deja ceroPlan/READY,reserva liberada yobjetoPENDING explícito para reconciliación. Un fallo de framing personal404 yla foto parcial inicial137 se preservan; final162 enumera fuentes nuevas. SECfad3 acepta sólo dominio/constructoresd5:79replay y24propiosPASS,no integración35. UI ydesktop avanzan enWTpropias;PG35/peerintegrado pendientes,no aprobación clínica ni MAIN/despliegue.

## Checkpoint135

Decisión expresa del usuario al reanudar: «continua con todos estos cambios pero ya no trabajes en la version desktop, trabaja unicamente en la version de el servicio web». Desde este checkpoint el trabajo y la entrega se limitan al SaaS. Se detienen desarrollo, QA, empaquetado e instalador desktop. Código y evidencias previos se conservan; no se eliminan funciones existentes ni se integra el candidato Desktop35. QA confirmó que todavía no había ejecutado pruebas ni creado ramas o artefactos de esa revisión. Las validaciones Windows del servicio web y el núcleo compartido siguen dentro del alcance. Esta decisión sustituye la instrucción anterior de continuar el desarrollo desktop; no declara resueltos sus defectos. Se importan únicamente30archivos de evidencia anterior, sin producto34/35/desktop. Se añaden SEC19/SEC20/QA-19/QA-20/QA-21 y se conserva íntegra la definición de los128criterios anteriores.

## Checkpoint136

Sólo importación de evidencias/control, sin producto34/35/36. Sólo servicio web. Se conservan133criterios previos yse añadenQA-22,SEC21,QA-23. QA-20 tienepeer24PASS; UI34/35 están congeladas con pruebas deautor sinChrome. SEC20/QA-21 reparados en rama aislada; finalhint1afa validado5SQLite yROOTpeer4PGPASS. PG35target5bae capturado contra34d1:únicocolumnacheck yseguridad exacta; faseROOTf7c34casos=29PASS5FAIL,0errores/skips, 1109fuentes/92dists/4540Python-METADATA quietos,pip0/0,8UUID normalescerradas y ausencia fresca. Los fallos son seedbooleanoPG ycuatrohandsoffTimeoutError con expiraciónORM de la fixture; no atribuir el fallo al runtimeFalse sin reproducir. QA-22fixe0ca tieneautor10PASS y8replaysPGROOT; SEC21 sigue4RED/2controles yreparación pendiente. La nueva composición explícita defixtures35 conserva54NodeIDs y54PASS, sin tocar loshelpershistóricos; UIyhintconsumidores adicionales pendientes. R27 inicia36aislado;R31sesiónbrowser en implementación;R16emailverify siguependiente. MAIN todavía33,R05globalRED1603;no despliegue ni desktop.

## Checkpoint137

Sólo evidencias ycontrol enMAIN, sin integrar producto. Sólo servicio web.139requisitos (92originales+47añadidos),136criterios anteriores exactos. MAIN continúa esquema33; candidatos34/35/R31/36 aislados. ROOT35 targetPG5bae sobre34d1:1columna+CHECK,seguridad igual. Faseinicial34=29PASS5FAIL conservada; seedPGcorregido1/1, QA23trasfix8/8PG y28/28SQLite másunit4/4. QA23peerindependiente33/33SQLite; SEC21/22ROOTpeer42+12SQLite y17PG en scopes separados, sin sumar replays. Fixturesactuales35:72/72SQLite, helpershistóricos/asercionesintactos; selección inicial errónea0casosexit4 conservada. ROOT12UUIDnormalescerradas,0sesiones/ausenciafresca; leasePG ahoraBackend36. BackendR31producto180839 ytests b297:32HTTPrealesPASS, revisiónindependiente en curso; GoogleSignedProvidercompañero conserva14criteriosprevios ycuatroactualestrasframingdocumentado. UIR31ycompatibilidadCI siguen en curso. SEC23contactoA→B→A yQA-24CSRFexclusión añadidos: autor17/17SQLite, PG36/peer pendientes. R05global sigueRED1603 en su fuente4f4; broad,Chrome,CI,imagen actuales ydespliegue pendientes. Desktop fuera del trabajo actual por decisión expresa.

## Checkpoint138

MAIN integra localmente seguimiento34 y perfil nutricional35. Los108 archivos de código y pruebas coinciden con la rama revisada fdaa. El único conflicto fue de atributos de evidencia, resuelto por unión finita. Once archivos RAW con CRLF se conservan intactos mediante atributos específicos. El esquema es35 y el target PostgreSQL5bae parte de34d1. Se preservan139 criterios y537 archivos untracked previos. Las sesiones R31 y notificaciones36 siguen aisladas; desktop queda fuera del trabajo y la entrega. Las pruebas anteriores siguen ligadas a sus commits y entornos. Faltan validación de MAIN, CI, Chrome, imagen y despliegue actuales. R05 global sigue RED1603.

## Checkpoint139

MAIN conserva esquema35 y140 requisitos (92 originales y48 añadidos), con139 criterios anteriores exactos. Tras integrar seguimiento34 y perfil nutricional35, el árbol c4f9 pasa75/75 contratos dirigidos, sin errores o skips y con fuentes/Python/92 distribuciones estables. Los hallazgos focales QA-20/21/22/23 y SEC20/21/22 quedan verificados localmente con peer; SEC19 conserva pendiente la revisión independiente de PostgreSQL; esto no cierra R19, R31 o R33 completos. Servidor R31 aún aislado: SEC24 reparado y106/106 pruebas independientes pasan. Frontend bee520 y sus companions siguen aislados; la exportación actual pasa108 ejecuciones con49 casos distintos, sin afirmar navegador nativo. QA prepara revisión y E2E; frontend migra fixtures nativos. Backend mantiene leasePG exclusivo para36: restore y últimos bordes aún pendientes. R05 global sigue RED1603 en4f4, sin nuevo escaneo global. CI, broad, Chrome, imagen y despliegue actuales pendientes. Sólo servicio web; desktop fuera del trabajo y entrega por instrucción expresa.

## Checkpoint140

MAIN continúa esquema35 con140 requisitos (92 originales y48 añadidos). Sus75 contratos dirigidos conservan su fuente c4f9. SEC19 queda verificado local: QA repite2/2 originales enPG35 restringido, observaSQL/ORM y confirma que no carga contacto ajeno; ocho blobs relevantes son exactos aMAIN. R31joint8878 permanece aislado: servidor106peerPASS, frontend925ejecuciones offline/848labels/865obligaciones; QAexport108ejecuciones/49casos y4mutacionesrechazadas. ROOT pasa4/4MFAUI conHTTP real en ambasfactories. Nuevos companions nativos4233 compilan6/6 sin ejecutarChrome; QA prepara fixtures35 y mantiene leasePG exclusivo paraR31. Seguridad acepta UI26/26 con4mutacionesrechazadas y pasa a36. Notificaciones36 autor9248350:109SQLite+5PGDDL+10PGfuncionales+1restore finalPASS;22BD cerradas normal/ausenciafresca. ROOTaa3231 compone36 aislado, sin atribuirle esos gates ni integrar producto enMAIN. UI36/peer,CI/broad/Chrome/imagen actuales ydespliegue siguen pendientes. R05 global continúa RED1603 en4f4, sin nuevo escaneo. Sólo servicio web; desktop fuera del trabajo yentrega.

## Checkpoint141

MAIN integra localmente el servidor y la interfaz R31 sobre esquema35. El gate del producto integrado8144 pasa110/110 contratos HTTP en ambas factories, sin errores o skips; no representa CI completo, PostgreSQL o Chrome. Se conservan140 criterios anteriores y se registran SEC25, QA-25, QA-26 y QA-27, total144 (92 originales y52 añadidos). El navegador nativo sigue rechazado:11 grupos profesionales alcanzados,2TypeError finales y9 capturas; los4 grupos personales no se ejecutaron. Diagnóstico SQLite35 separado reproduce4TypeError de acceso a DOM invalidado, sin atribuirlos uno a uno a los2 anteriores; reparación focal en curso. QA-25 se verifica localmente: normalizar EOL sólo en memoria repara2 compilaciones; el gate integrado incluye4 puentes MFA conHTTP real. Notificaciones36 permanece aislado: autor120/120SQLite tras reparar SEC25; seguridad independiente31/31 y ROOT60/60PostgreSQL restringido, pool1 y FORCE32, dosBD cerradas normal sin sesiones y ausencia fresca. ROOT es autor del delta monetario y su replay PG no sustituye la revisión independiente de ese delta. Registro con Bearer ajeno QA-26 confirmado1RED/1control en ambas factories: API500 con una identidad persistida; SaaS200. Cuenta37 aislada pasa61 contratos iniciales y69 de compatibilidad/bordes;20HTTP repetidos tras estilo, revisión independiente en curso yPG37 pendiente. R05 global sigue RED1603 en4f4, sin nuevo escaneo. Sólo servicio web; desktop fuera del trabajo y entrega. Sin despliegue, cargos o envíos reales.

## Checkpoint142

La rama principal local integra la reparación de invalidación del DOM de R31 y conserva el esquema35. Los cuatro archivos de producto coinciden con c822; API y backend no cambiaron. Sobre MAIN2709 pasan37 comprobaciones Node dirigidas. QA conserva las seis canarias RED originales y repite6/6 corregidas, seis controles propios y21 de exportación. El diagnóstico nativo separado pasa2/2 con pageErrors=[]; su observador contiene siete filas informativas y cero pageerror. El intento original de11 grupos rechazado y los cuatro grupos personales no ejecutados siguen preservados; QA prepara los15 grupos completos enPG35 y aún no hay aceptación de ese gate.

Notificaciones36 y seguridad de cuenta37 siguen aislados. QA-26 pasa20 contratos deautor en36 y9 independientes, incluida la canaria literal de registro con Bearer ajeno; su corrección aún no está en MAIN35. Cuenta37 conserva130 casos pytest SQLite/R31 distintos y8VM del autor; seguridad independiente24/24, migracionesPG12/12 yHTTPPG35/35. Las14 bases37 cerraron normalmente con cero sesiones y ausencia fresca. UI27 continúa en composición y la UI autenticada37 está pendiente. No hubo correo real.

R05 tiene un candidato finito v3:726 archivos y47513 pares ubicación/regla, con689 registros v2 intactos y37 archivos nuevos. ROOT recalculó las1603 ubicaciones propuestas;26 son checksums de un productor cuya fuente histórica original no está disponible y no se reconstruyó. El algoritmo permanece idéntico salvo tres literales de versión; se fija LF para la configuración cuyo Git blob no cambia. El gate deautor pasa125/125; revisión independiente del código y nuevo escaneo global pendientes. El resultado global conservado sigueRED1603 en4f4.

Se conservan los144 criterios, incluidos los92 originales, y537 archivos untracked. Free mantiene10 clientes,1 plan por cliente al día y10 planes totales por gimnasio al día. Trabajo y entrega sólo del servicio web; desktop fuera del alcance actual. Sin push, PR, despliegue, cargos o envíos reales.

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

V7 ya integrado resuelve la última ubicación pendiente del escaneo anterior. Se documenta el resultado real de Main y la corrección del verificadorR24 en rama aislada. En curso: sistema visual web coherente con landing y panel de rutinas generalizadas; todavía no integrados. No hay cambio de esquema37, cobro, cuota ni despliegue.

## Checkpoint150 — 2026-10-21

Integrados607PPL,955QA32,6f130rediseño y50325semántica timer. La paleta se unifica con la landing y se reemplazan métricas ficticias de login y promesa no medida de60segundos por texto factual. Se conservan formularios/IDs/handlers/CSRF y derechos. Catálogo nuevo sólolectura/noDDL/nocuotas/noCliente-bootstrap; estado de semana/temporizador sóloRAM. Validación actual89 y gates estáticos focales; Native aún pendiente.

## Checkpoint151 — 2026-10-21

Producto50325 permaneceexacto. Integrados harness/recibos nativos yfinitoV8 para5checksums,ZIPV7originalintacto. Nuevas pruebas usan clasificador real ymutaciones negativas. PGcorrige presupuesto de fixtureQA,no producto ni aserciones originales. R30sóloWTaislada/noMain.

## Checkpoint152 — 2026-10-21

Nuevo QA-33 y calificación explícita del fullscanV8 no acreditado. Producto50325 exacto; corrección del escáner y R30 siguen aislados.152criterios anteriores y537untrackedSHA intactos.

## Checkpoint153 — 2026-10-21

R30API yhelper integrados;QA34sólo validación de consecuencias derivables. QA33parser/frontera y72controles integrados,fullscanactualpendiente. NativeV7harness/proofs sin cambiar producto;NodecompilerdescubreNode yrechazaausencia,mismosasserts.12proofQA33restauradosbyteexactRAWautorconatributos finitos. Único conflictoR30documental:se aplicó creación13998709antesactualizaciónc368,producto no cambió.

## Checkpoint154 — 2026-10-22

Se reconcilian estados de24 criterios con evidencia ya aceptada y criterio inmutable. No se rehacen funcionalidades terminadas ni se trasladan resultados entre fuentes. Se integraron126 helpersCI y se retiró el job desktop; las siguientes composiciones esperan B19/B13/B20. Arquitectura actualizada al esquema37. [PG53](evidence/security-pg53-r30-ppl-independent-20261021/result.json) y [imagen144/59](evidence/image57-r30-real-build-probe-20261022/summary.json) conservan sus límites.

## Checkpoint155 — 2026-10-22

B19/B20 integrados y82replays de composición aceptados. Nuevo bloqueo de contraseñas completas y422privado de invitación; sin cambiar login existente. B20 aporta procedimiento y tests, sin runtime/tokenformat nuevo. PRIVACIDAD actualizada. CIweb/Node/PG/Historical31 actualizados como preparación, sin declarar ejecución remota ni global verde.

## Checkpoint156 — 2026-10-22

Integrados B13 y R07/B11 como herramientas explícitas del operador, sin nuevos endpoints ni DDL. QA36–39 verificadas localmente con fallos previos preservados. El CLI de archivos históricos pasa a formar parte de lint/syntax/SAST mantenidos; sus dos diagnósticos LOW B404/B603 son invocación Git fija revisada, sin shell ni argumentos privados. No se añadió baseline/ignore ni aceptación de riesgo real.

## Checkpoint157 — 2026-10-22

Sólo documentación de progreso y tres criterios nuevos: R37 en_curso, QA-40/41 verificados localmente en sus scopes finitos;159criterios anteriores y92IDs intactos. Herramientas de migración viven en E y no se incorporan como runtime de aplicación. Main7023a370 permanece sin cambios de producto. Primer32orígenes C retirados bajo autorización Root; lote4175en_curso sin resultados. Roaming retirado porRoot en operación separadaCOMPLETE3files/51111B. No se reescriben RAW históricos ni se añaden cambios desktop.

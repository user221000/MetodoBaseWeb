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

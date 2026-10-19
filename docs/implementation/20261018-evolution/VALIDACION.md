# Validación

Checkpoint99: diario27 integrado423296f tras QA141 HTTP/SQLite,33 migraciones/PG y1 restore poblado, más34 controles de seguridad;78 fuentes estables. Las pruebas independientes mantenidas se incorporan sin modificar fixtures26. Ver `evidence/qa-diary27-independent/qa-diary27-final-source.json` y `DIARIO.md`.

ACKlogout0c55b16:13 casos independientes sin fallos/omisiones, ambas factories reales,18 fuentes estables. Incluye fallo antes del commit, ACK perdido después de persistir, aislamiento de otra cuenta y regresiones históricas. Alcance SQLite; consumidor/browser se revisan aparte. `LOGOUT_CONFIRMACION.md` conserva contrato aditivo y límites.

Desktop9f real: build343.82s y ZIP122774966 bytes,39 controles independientes aceptan procedencia/integridad/Qt, sin acreditar instalación/firma ni flujo autenticado. OPS10 está corregido enbca89bb con QA97+3CLI; falta construir/verificar el reemplazo. El comando Windows de CI actualizado pasa97/0skip en20.99s. Autoría CI27 valida60 bloques Bash y19 reportes PG requeridos; QA acepta15 canarios del guard real,73 referencias y81 fuentes estables; colección local97Windows/95Linux filtrado, sin atribuir ejecución Linux/PG/Actions.

UI606 sigue retenida:129VM y21 grupos browser de QA son parciales; seguridad conserva6/10 y cuatro negativos. El nuevo driver machineACK adapta sólo dos fixtures positivas al protocolo aditivo del servidor y conserva aserciones/negativos. Ningún resultado anterior aprueba la corrección todavía en curso.

Entorno inicial: Windows 10 build 19045, PowerShell 5.1; Python objetivo local 3.12.13 instalado por uv (predeterminado del host 3.14.6); uv 0.11.26; Git 2.55; Node 24.21. Herramientas Linux/imagen aún sin comprobar. PostgreSQL 17.11 instalado fuera de PATH; QA prepara cluster exclusivo, sin usar el servicio existente. Docker CLI disponible; daemon no disponible al inspeccionar.

QA conserva baseline en snapshot del commit base, con SQLite temporal y bloqueo de conexiones externas. Consulte `evidence/baseline-source.json` y archivos baseline generados por QA. No se reutiliza como aprobación de cambios posteriores.

Regresiones de cobro: ocho casos fallidos antes; backend y seguridad conservan gates dirigidos de 96/97 casos y revisión con hashes. Gate integrado A1 congelado: 207 aprobadas, cero fallos/errores/skips, 42.753 s (`evidence/A1-containment.xml`); 328 archivos estables (`A1-containment-source.json`). Commit integrado `166038f88b211c52f0d149ce550880795361707c`. Siguiente corrección de GET/cuota y reserva B2B permanece abierta; este resultado no demuestra concurrencia PostgreSQL completa.

QA independiente R05 sobre candidato Windows: 109 aprobadas con n=2 y orden mezclado; gate de nutrición 156 regresiones más 29 dirigidas, con 100% de líneas/ramas en tres módulos nuevos. Umbral razonado CI para esos módulos: 95% líneas/90% ramas, sin exigir porcentaje engañoso global. Consulte QA_R05.md y JSON de cobertura.

Restore PostgreSQL sintético cifrado y autenticado: además del ensayo pequeño inicial, R03 completó restauración del esquema íntegro de22 tablas, filas, relaciones, secuencias, revisión y PDF/logo;15 regresiones independientes finales. La preparación R04 recibió otro ensayo de23 tablas pobladas, incluidas asociaciones de proveedor y activaciones vinculadas/legacy NULL. No es una promesa RPO/RTO comercial ni una comprobación de backups nativos. Consulte BACKUP_RESTORE.md y las evidencias de cada revisión.

Dependencias: runtime candidato Windows instalado con hashes en venv nuevo, sin GUI. Locks Linux/Windows resueltos con versiones/hashes; base Python 3.12.13-slim fijada al índice OCI `sha256:229a2c5bfa27522db7815ea81f9bed70af17ccb9de9fc7ad142b1877b5830d36`. SCA de resolución Linux posterior a tzdata: exit0, sin vulnerabilidades conocidas en ese inventario; SBOM CycloneDX en `sbom-linux-runtime.json`. No atribuir el resultado a una imagen final inexistente ni a producción. Docker no pudo iniciar por virtualización deshabilitada; CI/imagen/Redis real siguen pendientes.

Revisión estática R18 posterior por backend, contrastada por seguridad:32 requisitos directos compatibles con los locks,13 fuentes COPY existentes, instalación con hashes, nonroot, readiness con PORT y retiro de credencial migradora antes del servidor. `evidence/backend-runtime-static-review.json` fija hashes y alcance. Dockerfile y manifest desktop se alinean con los targets ya ensayados; este check no construye ni certifica la imagen.

Quality ampliada: el coordinador ejecutó lint, syntax, security y canarios reales con código cero; Bandit conserva seis huellas históricas y ninguna nueva. Nueve casos SQLite independientes de scripts archivados y102 contratos de identidad/equipo dieron111 aprobadas en22.50s. Commit64fe65a. R11 posterior se validó por separado con128 pruebas independientes,11 estados UI y7 recorridos auth/API/SQLite reales, commitb03e20a. Las invitaciones nuevas exigen derecho multiusuario efectivo; cambios concurrentes de roles consumen una sola versión. El ajuste JS posterior en19298e7 repitió los7 recorridos. Correo real y asociación consentida de cuentas existentes siguen pendientes.

R04 preparación:19 pruebas del coordinador y callbacks/restore de23 tablas de QA, commitf325fc4. Activación local posterior en501ceaa:64 casos de matriz/DML más37 de seguimiento con17 familias sin tenant, startup, onboarding, equipo y callbacks; restore23 con FORCE RLS. Root ejecutó38 dirigidas y QA23 de CLI/harness. Se separaron credenciales migrador/app y se rechaza rol propietario/SUPER/BYPASS antes de auth. Los seis grupos de control tienen contratos explícitos de identidad y autorización; no se afirma RLS universal. Sin intervención productiva ni aceptación de staging.

SEC01:19 fallos reproducidos antes;40 casos locales finales y3 PostgreSQL independientes,43 en33.77s. Incluyen carrera de dos propietarios y repetición bajo UTC/México; la escritura UTC sin zona evita recortar seis horas al repetir la activación. Commit501ceaa y license-timezone-independent-source.json. El puente remoto autenticado y la autoridad HMAC legacy siguen abiertos. No atribuir un sandbox o una emisión comercial a esta prueba.

R07:33 pruebas independientes finales y una omitida porque el host no permite crear symlinks, commitabc896f. Incluyen volumen privado, fallos de publicación/cleanup y contratos del SDK boto3/botocore1.43.114 con Stubber, sin servicio externo. El primer ensayo del harness tuvo un identificador pytest enorme y se interrumpió; se conservó su hash/causa y se corrigieron IDs cortos. Esta evidencia no demuestra aún persistencia tras reemplazar contenedor, metadatos PostgreSQL, autorización de rutas ni migración de archivos.

Composición R07 separada en9b97068:32 pruebas independientes SDK, incluidas cinco nuevas de seguridad, verifican destino/credenciales explícitos, ausencia de fallback y de descubrimiento de credenciales/endpoints heredados. El factory todavía no se conecta al startup ni añade SDK al runtime. Consulte ALMACENAMIENTO.md.

R31 preparatorio:41 pruebas independientes de exportación personal, con propietario por rol, cursores UUID conservando mayúsculas, límites de bytes y cero commits. Esa evidencia corresponde al router sin montar; integración de fábricas, PostgreSQL y UI se valida después. El helper UTC separado tiene32 pruebas independientes aprobadas, incluidas seis nuevas de QA con Session real, filtro tipado y control del driver UTC/México. Aún sin adopción en modelos ni reinterpretación de filas históricas.

Lote B2B/privacidad integrado enb81cfc1/dbb6af5, gates en e3039c2: QA verificó18 PostgreSQL (8 HTTP multiproceso+7 recuperación+3 RLS/TZ),41 worker/nutrición con5 PDFs reales,6 migraciones y restore24 poblado. Se conservan los8 fallos B2B previos y las dos exposiciones de logs al fallar compensación. El seguimiento final de compensación/logs/rollback/PDF/caducidad dio25 aprobadas; no se repitieron migraciones inmutadas por cambiar sólo el manejo de errores.

R31 montado: dos composiciones PostgreSQL restringido con factories/procesos reales y sin auth/tenant mocks; GET200/401, owner sólo cuenta, miembro sólo espacio personal, cero DML/commits y sesión sin tenant vacía antes/después. UI independiente:8 grupos,5 pantallas y7 descargas, cero axe AA de la sección nueva/desborde/pageerrors; partes sin duplicar colecciones/cuenta, UUID con caso original, errores y cambio de sesión. Capturas y JSON independientes no sobrescriben los del autor. Véanse privacy-composition-independent-source.json y ux/privacy-export-independent-source.json.

Regresión amplia final, candidato Windows y runtime bloqueado anterior a UTCmodels/DDL25: **1621 aprobadas y1 omitida**, serial182.54s y n2shuffle111.34s seed20261018.387 fuentes Python/dependencias y55 frontend permanecieron estables en ambos gates e idénticas entre ellos. La única omisión es creación de symlink sin permiso Windows; Linux CI debe ejercitarla. Se incluyeron4 regresiones B2B de compensación y9 de errores/alertas/rollback. Un serial anterior1607/1fallo/1skip queda conservado: M03 buscaba una cadena en el router extraído; ahora prueba emisión/persistencia del vencimiento configurado y rechazo exacto al caducar. Ese primer serial también registra explícitamente tres cambios de fuentes durante su ejecución; no se presenta como aceptación congelada.

Registro: `python -X utf8 scripts/implementation_registry.py --render --check` verifica los92 IDs originales más OPS08/SEC01, campos, fuentes y sincronización Markdown/JSON. El registro no demuestra que los comportamientos estén implementados.

Pendientes: suite completa actual; ramas de dominios críticos; nueva cuota B2B bajo concurrencia; integración R31 y adopción UTC; staging de migraciones/restore; sandbox de pagos y entrega de correo reales de prueba; imagen Linux/SBOM/SCA; recorridos posteriores integrados en navegador; lector de pantalla; validaciones clínica/legal y piloto. Las pruebas locales de RLS, migraciones, restore y navegador ya citadas conservan su alcance y no cierran estas comprobaciones externas.

Adopción UTC5bb5395: cuatro fallos antes,42 casos autor después; QA independiente16 sobre modelos reales y102 regresiones auth/billing/entitlements/licencias, incluidas3 PostgreSQL multiproceso UTC/México.52 columnas instante usan el binder y dos fechas civiles conservan DateTime. Firmas y RLS head24/filas históricas intactas, sin DDL. No se repitió la suite1621 por rutina.

R14 preparatorio4e22852:35 casos independientes (27 autor+8 QA), un RecursionError legado reproducido y traducido a409. Sin ruta/modelo/diario servidor. OPS08bc6804c:23 Node y tsc independientes,12 fuentes estables; SDK npm audit sin vulnerabilidades conocidas en6 dependencias. No se ejecutó plan/apply, loader nativo ni entorno aislado. El wrapper npm CLI vulnerable quedó fuera del nuevo lock; sólo se verificaron bytes/versión/help del binario existente.

PDF exacto31ad545:49 independientes (24 PDF,21 middleware,4 composiciones PG). Telemetría93a9e1d:106 independientes y23 fuentes estables, con SDK real/envelopes en memoria y controles de baggage y sesiones. No hay entregas reales ni aceptación legal. WIP R07:120 consumidores autor+16 worker/cuota; DDL25 autor18+10. No sumar estos conteos como suite candidata final ni revisión independiente de storage. Locks/SBOM/SCA del nuevo SDK están en private-runtime-dependency-review.json;54 Linux/53 Windows, cero vulnerabilidades conocidas, versiones anteriores intactas.

## Checkpoint de integración 0459b0f

No sustituye los gates históricos ni suma casos de distintos entornos como una suite. Esquema25:18 pruebas independientes QA con37 fuentes estables; coordinador22 (12 migración SQLite/PG +10 startup) y6 del contrato24 preservado. Restore poblado25:1 caso independiente sobre DB UUID, filas/referencias/secuencias/políticas y bytes;19 familias FORCE. [DDL](evidence/storage25-ddl-independent-source.json), [revisión](evidence/storage25-root-review.json), [restore](evidence/qa-storage25-restore-final-source.json).

Consumidores R07:14 independientes backend (5 PostgreSQL reales),48 SDK/config sobre SDK fijado/Stubber y transporte efectivo,3 API/equipo,10 grupos navegador/6 pantallas runtime25 con0 infracciones axe/overflow/errores JS del alcance. CI local: YAML,39 referencias,6 bloques Bash y canarios reales de skips/artefactos; no Actions/Linux/imagen. Dependencias: instalación Windows con hashes y SBOM/SCA de resolución54 Linux/53 Windows,0 conocidas al corte, sólo6 componentes SDK añadidos. [Composición](evidence/qa-r07-composition-final-source.json), [dependencias](evidence/private-runtime-dependency-review.json).

UI B2B ddaf71a:9 grupos/8 pantallas y4 controles suplementarios; snapshot24 inmutable, distinta evidencia del runtime25 posterior. Auth/audit/correo/Sentry93a9e1d conserva106 independientes; no correo real ni servicio Sentry remoto. SEC02: dos fallos rojos reproducidos por el coordinador con `node tests/e2e/auth_refresh_race_review.cjs`; transporte sólo en memoria. [Huella roja](evidence/ux/auth-refresh-race-before-source.json). Su corrección y revisión siguen pendientes. Cuota individual postcommit sólo deducida hasta obtener la reproducción dirigida.

Último serial/n2 completo sigue siendo e3039c2,1621/1 symlink omitida en cada orden; no valida el head0459b0f. Último scan limpio sigue siendo b20e071. Gates nuevos pendientes tras congelar contenciones. Docker/Redis real/proveedor/producción y dictámenes externos conservan sus límites.

## Seguimiento de contenciones y CI antes de integrar26

Inventario bd6b067:31 independientes del coordinador tras31 autor, siete fuentes/dependencias estables; no apply/procedencia/producción. Cleanup0e8cd42:25 casos únicos QA (15 SQLite autor+8 propios+2 PG UTC/México), sin sumar17 autor de nuevo. Fallos commit/ACK perdido, rollback, rowcount y exit0/1 cubiertos. [Cleanup](CLEANUP.md).

Publicación individual26: QA7 afectados y13 migración/restore sobre fuente a621; seguridad encontró después dos negativos legacy mixtos, corregidos en lector246 con13 dirigidas independientes. Los20 contratos anteriores, DDL/modelos y25 tablas/19 familias permanecen iguales; el último lector espera repetir5 PG que no ejecutaron sus cuerpos por clúster55482 apagado. QA recuperó únicamente su data directory registrado con WAL recovery, sin initdb ni servicio previo del usuario. Muerte individual real de proceso está en preparación; no confundir excepción inyectada con muerte de contenedor. [Contrato y fuentes](CUOTA_INDIVIDUAL.md).

API347:74 VM independientes (13+33+26+2) tras un negativo de escritura parcial. El cuerpo histórico275 se reconstruyó en copia con SHA exacto y volvió a dar12/13 frente a13/13 final. Ninguna fuente final se reescribió para esa reproducción; no se inventó commit. Navegador actual y garantías reload/cross-tab no demostradas por ese gate.

CI local:58 canarios independientes/8 Bash,56 referencias, guards de Node/17PG/browser. QA reprodujo {} aceptado por el primer guard; corrección exige tipos/mínimos/listas y reportes PG no vacíos/sin skips/failures/errors. Después sólo se añadió la ruta de un test de proceso:57 referencias y guards exactos idénticos. [Revisión](evidence/ci-session-publication-independent-review.json), [delta acotado](evidence/ci-individual-process-followup.json). No ejecución GitHub/Linux/imagen.

## Checkpoint integrado26 / API347 / CI6d33b9e

Este checkpoint sustituye sólo los pendientes de las secciones anteriores, conservadas como historia. Los5 PG del último lector pasaron después de recuperar exclusivamente el clúster QA; sus5 errores de setup anteriores permanecen diferenciados. La prueba independiente de muerte real de proceso usó worker/core/PDF, publicó y ejecutó os._exit(23); otro proceso recuperó mismo resultado sin CPU ni consumo adicional. Tras borrar Plan se conserva marcador y crédito consumido. No es prueba de muerte de contenedor ni outbox general. [PG](evidence/individual-reader-postgres-after-restart-independent-source.json), [proceso](evidence/individual-process-recovery-independent-source.json).

Navegador actual: cuatro fixtures runtime26,36 grupos/19 pantallas/0 pageErrors,224 fuentes estables; Storage adicional3 grupos/0 errores y225 fuentes estables. Usa auth/quota/worker/PDF reales sobre datos sintéticos; eje/overflow sólo donde los drivers lo verifican. No valida toda accesibilidad, quota nativa, recarga o coordinación entre pestañas. [Gate](evidence/ux/runtime26-browser-independent-source.json), [Storage](evidence/ux/auth-refresh-storage-browser-independent-source.json).

CI final b3574782 requiere17 reportes PG y cinco fixtures navegador;58 referencias/8 bloques Bash. Los guards son idénticos a los58 canarios independientes; delta posterior añade Storage browser y logs distintos. [Delta](evidence/ci-storage-browser-followup.json). Sin ejecución GitHub/Linux/imagen.

Serial independiente actual:1813 passed/1 skipped/3 warnings en232.55s,519 fuentes y paquetes estables. Skip único symlink Windows; n2shuffle20261018 aprobado1813/1skip en133.73s. [JUnit](evidence/pytest-web-candidate-protocol26-serial-independent.xml), [fuentes](evidence/web-candidate-protocol26-serial-independent-source.json). No sumar pruebas dirigidas ni resultados históricos al total. El registro mantiene95 IDs, incluidos SEC01/SEC02/OPS08; render/check sólo valida su integridad.

Cierre del gate amplio26: [resumen independiente](evidence/qa-web-candidate-protocol26-final-summary.json), SHA c7cc3464ce23a9685334bd9e78a126478e543b5ab8e67b79d64b5668fffb46c5; [JUnit n2](evidence/pytest-web-candidate-protocol26-shuffle-independent.xml). Cuatro fotos519 fuentes/403 Python y cuatro inventarios89 paquetes idénticos; pip check antes/después0. Tres categorías de deprecación (src.gestor_bd, httpx TestClient, Sentry propagate_traces): serial3 avisos, n2 cinco por imports repetidos entre workers. No fallos; skip único symlink Windows. Linux CI debe ejecutar ese control sin omisión. No se repetirán gates amplios sin cambio o incertidumbre nueva.

Checkpoint posterior, aún en revisión: [R21](HIGIENE.md) conserva scan2f8b7f9 fallido294/1490,293 SHA públicos verificados, una familia sintética saneada,1445 canarios independientes verdes y11 wrapper(1.41s). Nuevo scan completo pendiente. [Estadísticas](ESTADISTICAS_DISPONIBILIDAD.md):4 rojos/3 controles antes,48 autor verdes después,19.42s; requiere QA independiente. [UI individual](evidence/ux/personal-ambiguity-root-review/REVIEW.md): cuatro casos400 ambiguo rojos antes y verdes después sobre cuerpos exactos del controlador;40fd2af0 todavía en rama aislada. El gate amplio1813 de6d33b9e no se atribuye a las fuentes nuevas.

## Aceptaciones dirigidas posteriores al gate amplio26

- Estadísticas:15 HTTP independientes (8 QA+7 autor),6.23s;2 estados navegador y21 fuentes estables. Errores SQL dan503 saneado, vacío real conserva200/ceros; ambos adapters y recuperación de sesión comprobados.
- UI personal40fd2af integrada c11256a: backend42+1 probe N+1; QA15 grupos/8pantallas31.47s +4 propios10.09s,11 fuentes/36 dependencias estables; root4VM antes/después. [QA](evidence/ux/personal-plan-ui-independent-source.json), [copia exacta](evidence/ux/personal-plan-ui-independent-copy.json), [SQL](evidence/personal-ui-backend-review-40fd2af/personal-ui-backend-review.md).
- SEC037321d3b integrada0fa124e:12 browser independientes,0 pageErrors,22 fuentes estables. [Fuente](evidence/ux/sec03-independent-7321d3b/sec03-qa-independent-source.json). HTML previo, sin ejecución activa demostrada.
- Desktop:94 independientes/22.85s,0 errores/fallos/skips,27 fuentes/índice/config estables. [Fuente](evidence/desktop-qa-review-abfee196/desktop-provenance-final-independent-source.json). Valida receta y procedencia; build real posterior se registra aparte.

Los1813 serial/n2 siguen vinculados a6d33b9e; no se suman resultados dirigidos ni se atribuyen al nuevo candidato. Backend diario27 y UI/CI nuevos necesitan sus revisiones antes de integración/aceptación.

## CI personal y routing desktop

[Guard independiente](evidence/ci-personal-independent/ci-personal-independent-source.json):91 canarios CLI propios,27 pytest,20 Node,8 reportes históricos y8 escenarios inertes de la función de fixtures. Tres fuentes estables; cinco llamadas previas y guardNode exactos. Primera metadata autor apuntaba a ruta inexistente aunque fallback ejecutó reporte real author-freeze; manifest inicial preservado y errata final conSHA, sin resultado ni producto cambiado.

[Routing independiente](evidence/ci-desktop-routing-independent/ci-desktop-routing-independent-source.json): workflow2e475314,guard08618abb/test91e4c69;58 Bash válidos. Colección localWindows85/Linux-selección83, diferencia exactamente dos node IDs batch nativos. No ejecutaLinux. El guard real de dosJUnit rechaza9 casos ausentes/vacíos/skip/fail/error/malformed y acepta positivo. Autor ejecutó comandoWindows exacto85/0skip/0fail/0error,19.853s. Ambos gatesweb excluyen el módulo entrypoints completo, cuya parte portable sí está cubierta en desktop de ambos sistemas. Cero-skips sigue obligatorio para la selección de cada sistema.

Quality tras integrar receta:lint0,415 Python mantenidos parseados,Bandit6 baseline/0nuevos. Sin Actions ni imagenLinux real. No repetir91 canarios al revisar sólo routing, pues guard y pruebas mantuvieron SHA exacto.

## Gate conjunto27 y verificaciones posteriores

[Gate amplio7bde30b](evidence/qa-integrated27-final-20261019/qa-integrated27-final-source.json): comando aislado exacto CI web, excluye test_login_desktop.py y test_desktop_entrypoints.py completos. Serial2064pass/1skip/0fail/error457.33s y n2shuffle20261018 mismo resultado180.92s. Cuatro fotos618 fuentes/89paquetes quiet,4pipcheck0. Omisión symlinkWindows conocida;100%líneas/ramas sólo tres módulos de dominio. Tres categorías de deprecación existentes,3warnings serial/5n2 por imports de workers. No atribuir2064 a nuevas pruebas posteriores.

UI final:162VM únicos; seguridad25controles yQA25grupos/12pantallas (17replay+4nuevos+4propios),57fuentes quiet.0pageErrors/axe/desborde sólo alcance escaneado; cuatro nuevas pantallas acotan export/logout. [QA](evidence/ux/diary-ui-bf46-independent-20261019-qa/run2/diary-ui-bf46-independent-source.json),[seguridad](evidence/ux/diary-ui-controls-security-source.json). No sumar las17reutilizadas dentro del driver21 de controles como casos nuevos.

Métricas:[15propios+63replay](evidence/metrics-privacy-independent-source.json),18fuentes quiet; anterior12rojos/3controles. [Copia mantenida](evidence/metrics-privacy-maintained-copy.json) conserva AST de todas las funciones/aserciones; `python -X utf8 tests/run_isolated.py tests/test_metrics_privacy_review.py -q --tb=short` pasa15/15 en2.05s,una deprecaciónhttpx existente. Fuera de2064.

Desktop:[build0/404.75s](evidence/desktop-real-build-7bde30b-source.json),[Inno0/97.19s](evidence/desktop-inno673-compile7bde-source.json),[51controlesbundle](evidence/desktop-artifact27-independent-source.json),[27instalador](evidence/desktop-artifact27-independent-installer-source.json).1215archivos/254690179bytes exactos; Qt nonce/offscreen sin flujo de negocio. Parser inicial de listado rechazó formato y bloqueó extracción; evidencia parcial/errata intactas. Inno firmado y extractor fijado sin firma; Setup no ejecutado. No instalación/upgrade/desinstalación/firma/OSnetwork ni buildLinux/macOS.

R34:[revisión de datos](evidence/qa-load-root-data-review.json),1400HTTP/observaciones enlazados,cuantiles recalculados y248fuentes quiet; pruebas acotadas a5clientes pendientes. No carga abierta,SLO o medición de producción. R16 autor181+17PG+6SQLite+9browser no constituye aceptación independiente ni validación del MAIN27. CI8435 integrado00d2114 tras replay162Node/21CLI/8startup/13inertes/15origen y43canarios propios,61Bash/82refs,275fuentes/89paquetes quiet. No nuevos browser/Actions/Linux/imagen.

Calidad actual tras CI00d2114:436 fuentes Python mantenidas parseadas,F8210,Bandit6baseline/0nuevos,Windows local. [Recibo](evidence/quality-integrated27-final-source.json). Sin fotos dedicadas antes/después de este chequeo corto; no se inventa estabilidad de fuentes.

## Recuperación28: aceptación independiente focal

Seguridad46 propios contra35a; headers antes6/10 y después89010/10 más diez propios,88fuentes quiet. QA181dirigidas d9c; en453 seispropias/seisSQLite/17PG/restore28,0skip/fail/error.701fuentes/89paquetes quiet,pip0;40asserts26/27 preservadas y limpieza startup de cuatro revocados esperada por IDs exactos. No nuevo amplio2064 ni entregas reales. [Contrato y alcance](RECUPERACION_CUENTA.md). MAIN27 espera CI28 y composición.

## Checkpoint103: escáner y revisiones de gates

Scan exacto41708e5:3028fuentes estables/45.938s,raw2/clasificadas2/restantes0. Guard independiente30,parser original5tras4rojos y8extras;61suite mantenida. Se conservan21probes reales anteriores y1134negativos protegidos por config idéntica. [Aceptación](evidence/secrets-wrapper-independent-review.json),[scan](evidence/secrets-final41708e5-summary.json).

CI28: QA55JUnit+7delta+5Bashinertes y replay de autor verdes, pero2bypass de referencia quedaron rojos. Fix3978 aceptado7CLI propios y764fuentes/89paquetes quietos,integrado5ba98c6/7cf4e6c; no se repitieron PG/181/broad/162VM/browser. Historial: driver root original8 conserva5rojos/3controles antes y8verdes después49eb441,10fuentes estables; [manifest](evidence/history-headers-root-independent-20261019/manifest.json). El before conserva foto posterior y HEAD; no se inventa una foto previa. Linux prepara herramientas y build en curso, no gate de aplicación ni rendimiento.

Composición integrada7cf4e6c:6pruebas propias mantenidas yCI28verify-only pasan,606fuentes estables. Delta no documental contra el candidato aceptado92615d7 limitado a siete rutas deCI/escáner; código runtime de recuperación idéntico. [Resumen](evidence/recovery28-main-composition-20261019/summary.json). Seguridad24HTTP/cursor/root y12VM de historial verdes en49, pero2rojos500sinheaders mantienenSEC07abierto; QA74Python+23VMverdes en49, navegador espera fix.

Imagen Linux de composición92615d7 construida0/698.969s,296archivosGit exactos y contexto17233920bytes sin.env. IDsha256:5eb6d3009ae98c845f2eab0aeff0d249bf336887f124578284714728a3359d0e; inventario real55distribuciones/Python3.12.13/uid999,pipcheck0,capabilities0/no-new-privileges1/rednone/raízreadonly. Sólo build/inventario, no startup de aplicación. SCApip-audit2.10.1/OSV de55paquetes devuelve12entradas equivalentes a6avisos distintos, todos enpip25.0.1 heredado de la base;54distribuciones restantes sin coincidencia en esta consulta. No se declara verdeSCA: actualización bootstrap fijada por hash en preparación, SO aún sin auditar. [Prueba e inventario](evidence/linux-recovery28-image-92615d7/runtime-inventory.json),[auditoría roja](evidence/linux-recovery28-image-92615d7/sca-before/audit.json). No modifica locks/entornosWindows ni demuestra explotación.

## Checkpoint104: aceptación focal y composición

Historial57: QA74Python y8propios SQL,23VM nuevos,10grupos browser de autor ejecutados una vez y3propios; fotos de fuentes/89paquetes estables. Seguridad24/24 conserva2negativos originales,8root y14propios. En MAINfdfc9cb, los drivers originales intactos pasan36/36 junto con recuperación28,616fuentes estables. [QA](evidence/history-independent-20261019/final-summary.json),[seguridad](evidence/history-security-after-20261019/source.json),[composición](evidence/history-recovery28-main-composition-20261019/summary.json).

Landing55: QA12HTTP,2criterios dinámicos rojos antes/verdes después,8grupos browser de autor una vez y3propios,4pantallas axe AA sin desbordes/erroresJS del alcance. En MAIN1c24d3c,20/20 antes de retirar checkout huérfano y6/6 rutas404 después; sólo ese HTML cambia entre622y621fuentes. RAW fuera del entregable. [QA](evidence/landing-independent-20261019/final-summary.json),[composición](evidence/r29-main-composition-20261019/summary.json).

No gate amplio nuevo, medición posterior PG, Actions ni startup de producto en imagen por estas pruebas. SCA de la primera imagen real es roja y se registraSEC08; reconstrucción corregida/OS/CPython tienen evaluación separada.

## Checkpoint105: gate amplio actual y correcciones de runtime

[Aceptación independiente a753b2c](evidence/qa-integrated28-history-landing-postfix-20261019/final-summary.json):2360passed/1skip,serial588.64s y n2shuffle20261018/275.43s.2361nodeids/resultados iguales;667fuentes/89paquetes idénticos en4fotos,4pipcheck0. TresSQLite readonly integrity ok/26tablas/diario/3camposrecovery. Cobertura100%líneas/ramas sólo nutrition_validation,food_catalog,profile_schemas.6mensajes de deprecación existentes iguales,8avisos n2 por imports repetidos. No nuevoPG/Actions/Linux/performance por este gate.

Originaldd987:2358pass/2fail/1skip;ambos fallos esperaban checkout HTML huérfano ya retirado. [Original](evidence/qa-integrated28-history-landing-20261019/serial-red-review.json) intacto. a753 modifica sólo esa aserción y exige ausencia/404 de rutas públicas;15nodosprevios/restomódulo AST idénticos,20dirigidas verdes. [Fix](evidence/landing-retirement-test-fix-20261019/summary.json). No tests excluidos ni runtime cambiado.

Linuxecae/abd:55inventariados reales/OSV0,pipcheck0. Trivy0.76.0 sobre87OS:exit1,166entradas/73IDs(67CVE+5TEMP+1DSA),sinignore. [Matriz73](evidence/linux-recovery28-image-abd559a/os-audit/triage-matrix/TRIAGE.md):21grupos;2alias del mismoXZfixu2,otros71abiertos. BackportsOpenSSL13 confirmados por fuentes primarias. Candidatobc365c1 sobreMAINa753:build0/900.985s/imagen99c846bd28b0;55PyPI OSV0 yúnico cambioOS liblzma5u1→u2. AuditoríaOS final/startup/independencia aún pendientes.

[Windows3.12.15](evidence/desktop31215-security-20261019/README.md):83paquetes OSV0,pipcheck0;45desktop+97packaging/entrypoints nativos sinfallos/errores/skips,dd987/576fuentes estables. Runtime extraído desdefuente oficialAstral inmutable conAPI/checksum iguales;sin firma acreditada. OpenSSL3.5.9/Expat2.8.5. No bundle/Setup nuevo ni auditoríaDLL nativa.

[R12v2](evidence/r12-contract-security-review-20261019/source.json) aceptado sólo para diseño y autoría29 aislada. [Rootprototipo](evidence/r12-root-mechanism-review-20261019/review-summary.json):4criterios propios positivos y1rojo payload real;1error propio deharness corregido sólo paraesecriterio,original intacto. Autor informa55canónicos verdes traspayload/lockowner;no aceptación independiente29/API. CI57dba41 en revisión independiente,16inertes/13delta/23VM autor más negativos propios aún sin integración.

CI de historial y landing integrado en52af400 tras aceptación independiente57dba41. Verificador13delta/16inertes/65Bash/90refs,23VM y30canariospropios verdes. Browserhistory10/4pantallas ylanding8/4pantallas ejecutados una vez cada uno,0axe/overflow/pageErrors;fuentes742comunes/89paquetes/146deps estables. Elverificador históricoCI28 y21PG/restore28/7fixtures/162VM permanecen íntegros,sinrepetiresosensayos. ComposiciónMAINverify-only/13delta verde,623fuentes/89paquetes quietos,pipcheck0. [QA](evidence/history-landing-ci-independent-20261019/final-summary.json),[composición](evidence/history-landing-main-ci-review-20261019/summary.json). No Actions/Linux/PG/perf por estegate.

Imagenbc365c1/99c846bd28b0:55PyPI OSV0. Trivy sobre87OS finalizóexit1/142.835s:164entradas/71IDs,162affected+2fix_deferred. MismaDB yhashes exactos:elimina sóloDSA-6549-1 yTEMP-1147318-639065 (mismoXZ),sinentradas nuevas;otras164idénticas enID/paquete/versión/fix/status/severidad. [Manifiesto53](evidence/linux-recovery28-image-bc365c1/evidence-manifest.json). Seguridad revisa deltaDocker ymatriz;sinaceptaciónOSglobal. VMQEMUpropia cerradaordenadamente porQMPtrasexportarpruebas;PID29456 ylisteners ausentesconfirmados,overlayconservado. [Cierre](evidence/linux-owned-shutdown-20261019/after-closure-confirmed.json).

## Checkpoint 106: imagen aceptada por delta, historial medido y desktop reconstruido

Docker/bootstrap integrado en9401b5e/b6cdaac/f8ceaa1/66d9dec tras revisión independiente del delta. [Seguridad](evidence/sec08-linux-independent-20261019/source.json) conserva164entradas/71IDs rojos, matriz73 y ceroignores. Los seis campos de164hallazgos coinciden; Fingerprint/PkgIdentifier cambian, sin afirmar igualdad de objetos completos. FlagsNNP/capdrop/rootfsRO pertenecen al laboratorio. Bibliotecas vendorizadas y runtime de producto pendientes.

[Ensayo200](evidence/history-pg200-independent-20261019/final-summary.json):100C1+100C5,todos200/50filas/8161bytes/200ACK;737fuentes89paquetes quietos. Root rehashó37artefactos y recalculó p95 por rango más cercano16.2312/144.2441ms. Tresintentosauth/readiness y unwarmup excluidos. EXPLAINLimit51 procesa1000;UUID/PIDs eliminados. SinSLO ni atribución causal;baseline1400 intacto.

[Probesroot](evidence/history-index-probes-root-20261019/README.md):índice adicional reduceprimerapágina1000→51 sinSort,pero cursoravanzado siguevisitando1000. LectorUNION aislado produce51candidatos para mismas50filas;96mantenidas verdes. BasesUUID eliminadas. No migración30 ni integraciónMAIN;mezclaNULL/dated y revisión independiente pendientes. Nuevohelper no estaba tracked enlaprimera foto,limitación explícita conservada.

[Desktop66](evidence/desktop31215-build66-20261019/README.md):build0/474.859s bajo3.12.15,78pruebas/siete subtests,Qt offscreen,ZIP y1215archivos;4433fuentes83paquetes estables,pip0. Inno0/102.906s,inputs/bundle/tools quietos. ZIP122441614B SHA4966896c41e53b1b5df443045a0175626571a4bfd98731e200bcd299353ed353;Setup89973261B SHA5651f4189b7640edced7986db007a4a63f54ba00801658f31fa789587d219363. Revisión independiente payload/nativos pendiente;Setup no ejecutado.

R12 canónico ad712 sigue aislado y fue rechazado por tres negativos PG independientes: permisos de lectura tras cambiar pertenencia de un OWNER fuente o de un OWNER padre, y comprobación diferida con prueba GUC nula antes del commit. Seguridad conserva 18 positivos y esos tres rojos; backend prepara V2. Los 55 casos reutilizados y 22 propios de QA verdes no cierran estos defectos. Sin fuga HTTP ni incidente productivo atribuidos.

Checkpoint107: selladas la revisión independiente desktop66 (93 controles verdes, payload1215 exacto, Python3.12.15/OpenSSL3.5.9/Expat2.8.5/Qt6.8.3; sin ejecutar Setup) y las revisiones R12V1/V2. QA95 de V1 no cerró sus tres fallos de seguridad; V2 1aac pasó los mismos21 criterios independientes, sin cambiar el driver. Fuentes y paquetes estables; bases propias cerradas. Aceptación limitada al coreV2, sin casts/restore/API ni integración29. Los RAW y manifiestos originales permanecen exactos y se añaden atributos binarios sólo a estas nuevas carpetas para conservarlos en Git.


## Checkpoint 108

Checkpoint108 autentica QA30:120/120 verdes,14UUID cerrados,4580fuentes+7helpers/89paquetes estables. SeguridadR12:41 controlesAPI propios y26 finales,4933fuentes finales estables,UUID cerrado; los rojos de cabeceras y correlación permanecen. No agrega esos resultados como una ejecución única ni acredita restore/UI. InventarioLinux811ELF,13CNA primarios y symlink1/1 se guardan por fase; runtime42501 sigue fallido. El empaquetado verifica cada manifiesto y cada blobRAW contra Git; los informes públicos saneados conservan esa clasificación original.


## Checkpoint 109

Se autentican173 archivosLinuxoriginales,204filesfaseQA939rechazada y revisión migrador13verdes(11originales+2propios). NativePGno acreditaLinuxcorregido. Backend147 se describe144pass/1harnesserror/2skips+replay1, no ejecuciónúnicaverde. Restore29poblado1/UI10/HTTP28/Node297ejecuciones276únicos separados. Browser939:7pass,1fail,8noalcanzados;fixec029autor3+16verdes,sintaxis6,fuentecerrada. TodoslosRAW/derivados mantienen suclasificación;manifiestos yGitblobs verificados byteabyte.


## Checkpoint 110

QA ec029 completa16/16 Chrome/HTTP/PostgreSQL29 con pool real20/10,3/3 mismos canarios y15 UUID propios ausentes al cierre. Seguridad31/31 controles. No nuevo Node300 de QA: QA original17 reportes sumaba297 ejecuciones/276 únicos y tres canarios se repitieron aparte. Root CI2 sí ejecutó18 módulos/300 con sus parsers, evidencia aislada en preparación. La fase939 rechazada, errores de harness y replays siguen intactos. d038 sólo estática29 autor/27 Seguridad; emisor e8 rechazado7/10, autor11 ytransporte74 intactos.


## Checkpoint 111

MAIN29 e250:2464pass+1skip Windows conocido en serial/cobertura(686.25s) y n2/shuffle(284.328s);6087 fuentes/89 paquetes estables,pip0. Gate tres módulos100% líneas/ramas. CI29 QA final268 archivos autenticados, aceptación acotada local. Restore30 QA1+8 propios+1 SQLite; no Chrome/Actions/SLO por esos resultados.


## Checkpoint 112

QA navegador30:50unit+22propios+16freshreal/fixture0,5496fuentes/5helpers/89paquetes/157Node estables,UUID/Chrome/8798 cerrados. QA CI30:74unit+19propios/full28reports/27workflow/55+24parser/27inert/76Bash/107refs,5706fuentes estables. Merge MAIN30 conserva106criterios y18targets; amplia30 pendiente. Dockerc02 sólo estático3+6;SEC SCA6/6 y16CNA primarias, errata inicial preservada.


## Checkpoint 113

MAIN30 6d4e8b4:2491pass+1skip Windows conocido en serie/cobertura731.093s y n2/shuffle277.25s. Gate cobertura0,7381fuentes/89paquetes quietos,pip0. QA R23 aislado53HTTP/50R12unit/2PG/4propios/118Node/8R23real/16R12real; addon768 antes1/3 por foco, después mismo3/3 y30Node. Recursos propios cerrados, evidencias exactas por scope; sin Actions/imagen/SLO.


## Checkpoint 114

QA CI573:87mantenidas disjuntas+35propias,23VM/348mínimos,19parsers+Node-e4legacy+5normalizers y8freshreal;6591fuentes/5helpers/89pkgs/157Node quietos y recursos propios cerrados. ExpatM2 sólo estático37+6+22/GPG0. R24 rootquality0 sobre5942/89 y fix9bfa16/16+17VM; fuente/browser anteriores se conservan por scope. SEC11 root11:8rojos+3verdes,6fuentes/89pkgs quietos, sin DB/HTTP/red.


## Checkpoint 115

R23 merge3643 padres/tree/108criterios/targets22–30/c4 verificados. Configlocal core.longpaths=true resuelve falsoM por ruta larga. Se conservan wrappers fallidos; comparación de sourceCRLF vs GitLF reparada comparando blobs exactos, sin normalizar RAW. SEC11root mismo11criterios verdes contra531; autor13secuencia aún requiere revisión. QA R24preimagen31SQLite+65Node+2PG+1canario y4headersrojos; fix4042 mismo4verde+94mantenidas, independiente final pendiente. SEC R24acotada25puros/18HTTP/16VM.


## Checkpoint 116

QA4042:98/98 en424.86s,21focales,freshR24_11+R12_16;5987/89/157Node/tools/config quietos y4UUID ausentes. PG9bfa2+1concurrencia y31SQLite/65Node no se reatribuyen. SEC4042 mismo27propios4/27→27/27 y4QAHTTP; SEC5315propios+11rootreplay. Integraciónselectiva bd3:25sourcesGit exactas,179RAW autenticados,21pins esquema/c4 yregistro intactos, ancestryADC excluida. Actualamplia pendiente.


## Checkpoint 117

Ampliaeea8:serial2597pass+1skipWindows777.079s,shuffle2597pass+1skip384.438s;9542fuentes/89paquetes estables,pip0,cobertura0,2492caseIDs previos exactos más106nuevos cada modo.3módulos100%líneas/ramas. No PG/Redis/Linux/Actions/imagen/SLO. Composición46dc94mantenidas+8propias porfases;1+1rojos de fixture cache preservados y10assertsAST intactos en refinamiento final, sincambioproducto.


## Checkpoint 118

Seguridad: backend440 aceptado con los mismos replays6+4+5+20; PG4 pertenece sólo56 y composición913 sólo tiene peer estático. Autor UI087 conserva15 grupos/12 pantallas; root da343 pasó74VM+14SSR/HTTP,679 fuentes/89 paquetes estables. R34:16 solicitudes200,0 timeout,9 snapshots de los cuales3 son solapamientos efectivos;3UUID cerradas y8804 sin listener. No capacidad, SLO, Actions, Linux ni proveedor real inferidos.


## Checkpoint119

QA independiente:10VM+4flujosSQLite, replayPG deesos4,15grupos mantenidosChrome/12pantallasc669,1restorepoblado4a yUX19mismo3+2propios. STOPtimeout ypreparaciónfallida preservados; no runtimekeyafter ni cierregrácil. DAB174esautor, peerpendiente. QA-12:13/16original→16causalstubs(sólocausa)→16actualcompanions nueva fixture. D60firmas/7negativos/metadatainvariante, no compilación.


## Checkpoint 120

QA peer de fixtures aceptado: 24 SQLite (20 replays y4 propios) y16 VM con módulos reales. CI e0 se conserva sin aceptación: histórico573 FULL+348; actual31/494 con snapshot25 omitido. Los173PG siguen pendientes. Composición bd348 sólo cambia33 archivos CI/tests y conserva23 helpers; la regresión amplia está activa, aún sin resultado.


## Checkpoint 121

Se preservan el rechazo CIe0 y el contrato ed4 aceptado independientemente: mismos tres negativos,205 canarios offline,145 workflow, snapshot25 y SQL de rol. Los173PG están en curso, no aprobados todavía. Broad bd348:2381=2360pass+2fail+18error+1skip; maxfail20 y fuente/89paquetes quietos. de69 tiene aceptación estática21+11 y target compilado0/6smokes, con compiler argv vacío y superficie ELF diferente aún sin aceptación. R17 es autor103+52, no QA independiente.


## Checkpoint122

QA173PG:12comandos exit0/checker1730;42UUIDcerradas sinFORCE/cero sesiones/ausenciafreshconn. R17mismo24before12rojos→after24verdes, mismos2boundsverdes; autor84 yreplay24 solapados, noPG. Candidataaislada5637 componeCIed4 yR17b500 exactos; peer79 ybroadcomún pendientes.


## Checkpoint 123

QA peer79:56/56,58aserciones originales e inversas completas, misma SQLite31/33tablas;10176fuentes89paquetes/Python quietos,pip0. Composición809 conserva4tests exactos y otros10143blobs; preflightCI145 pasa. Broadserial en curso, n2 pendiente. Expat72:41autor+13propios son alcances solapados; PASS_STATIC_ONLY, nuevo build todavía sin resultado.


## Checkpoint124

Serial809:3039=3036pass+2fail+1skipWindows;2598IDs preservados y cobertura pasa, fuente10178/89paquetes/Pythonquiet,pips0. SEC15mismo14before10rojos4controles→after14green,8nuevos y6replays;3NodeVMexit0. Peer y nueva fullserial6a75 en curso,n2 pendiente. Native72independiente16XML+19contratos verde, argv registrados ligados a objetos; no nuevosgcc ni falsa prephoto propia.


## Checkpoint125

SEC15:41/41 peer. Logger474:36autor/3peer. Reloj9b14:35positivos SQLite y34/34 PostgreSQL;CI145/173/23 quieto,4grupos/5módulos. Helper9ab:51autor pero2keyword now= rojos independientes;d012 conserva esos2canarios y pasa53+4=57IDs distintos deQA. Comúnde506 preflight145workflow/205parser/173PGIDs/23helpers,10208fuentes/89paquetes/Pythonquiet,pip0/0; nueva serial iniciada21:07UTC,n2pendiente. Serial6a75:3045PASS+1setupERROR+1skip, no aprobación ni causalidad retrospectiva; cobertura real100%líneas/ramas en3módulos. R25lector:22criterios repartidos20/22+3/3; no23green enuna tanda. UIb7:152VM/2SSR/22autorHTTP/14Chrome con sufuente;345: mismos2HTTP+4móviles afterverdes,8vistas axe/reflow/capturas revisadas. Todos los recursos propios de esas fases cerrados. Runtimec538:54metadata/import/355fuentes medidos perostartup rojo; QA ACLsinDEFAULTFUNCTIONS29/head31green,conDEFAULTFUNCTIONS29commit+headrollback correctamente rojos. No SLO ni SCA71.


## Checkpoint126

Imagen f74 construida una vez:147.922s exit0, digestdc8fab52ffd440399baba71923aba008d54ebfbcf503d149b933b15f9ada62e3.54metadata/imports/355fuentes/USERreal999:999/218base/11XML/native0f618/5argv/1export medidos. Migración31,health200/ready200/Dockerhealthy/PID1sinMIGRATOR observados. Config.Env inicialsíconservaURL:dockerexec noheredaunsetdePID1. WorkerINCOMPLETO:2criteriosdelobservador eranmásampliosquecontrato (prefijomfa_ y19funcsuniversal;25FORCE/20funcsobservadas). Sin cambio producto ni replay; selloPARTIAL. SQL/Redis/appcerrados,UUID/2rolespropiosausentes/viejosintactos,VMownOFFporQMP. Restore32independiente sobre345aa7 PASS:1casomantenido60asserts,inversa58originalexacta,original31intacto. ControlesHTTPweb/apiMFAconpassword/recovery originalesrestaurados;progresocontrolesusanpasswordspreparadasdespuésdelrestore declarado,nocredencialesrestauradas.34físicas/26FORCE/rev32/4flagsfalse/nonowner/pool1.2UUIDleasesexclusivas/OID,cierrecero sesiones/DROPnormal/freshausencia;797fuentes89metadataPythonPGperfilinfraquiet,pip0/0. FlujopurposepadreOFFpassword+MFAenimplementación,wirecongeladoperoaúnnoaceptado;CI32/matrizcomúnpendientes.


## Checkpoint127

Serial y n2 de506 cerrados: cada modo3056PASS+1skipWindows exacto,3057IDs únicos y3047anteriores preservados,10208fuentes/89paquetes/Python quietos,pip0/0. Gate real de cobertura serial100%líneas/branches en3módulos críticos. Fullgitleaks de UI:exit1,31566raw,2pins existentes,31564restantes; sólo2nuevos fingerprints metadata verificados FP,31562previos sin clasificar. Scanner119 acotado no equivale a gitleaks global. Dos modos completos de506 PASS con la misma omisión histórica Windows de symlink. Duraciones1358.688s serial/621.156s n2 son diagnósticas, noSLO. No atribuir a estas ejecuciones PostgreSQL/Redis/Chrome/Linux/desktop/Actions ni nueva composición32. Retiro backend congeladofcfb +UIde216 +clocks/loggerde506 compuesto219f89,10332otrasGitentries exactas y todos los cambios RAW=Git productor. Autorbackend SQLite50funcionales y fases superpuestas,PG16=10+4+2; UI36controllerVM+9DOMVM+8SSR, todavía no browser integrado. Seguridadindependiente:SQLite73PASS/2rojos,PG24PASS/2rojos; todos los casos autor pasan. ParentOFF con invitación real permitemetadata/withdraw200 sin habilitarlogin general401. SEC18 retienecheckout bajo commit/rollback/close fallidos simultáneos;503opaco/contextorestaurado se conservan. Delta focal y QA pública en curso. SEC17 confirmado por revisión independiente sobre345:4canarios rojos y4controles verdes en ambas factories, con respuesta válida Google modelada y asociación local por email. No se demuestra bypass criptográfico ni explotación live. Asociación issuer/sub33, enlace explícito con primaria local+factor y alta nueva sin adoptar cuentas están en implementación separada.

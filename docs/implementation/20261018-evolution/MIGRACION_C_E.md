# Migración C → E y continuidad E/F

## Instrucción y criterio R37

Por instrucción expresa del usuario, trasladar los archivos del proyecto y entornos activos que ocupan C a E, continuar el trabajo en E/F y retomar el backlog exclusivamente del servicio web. Esta decisión no reabre desarrollo, QA ni empaquetado desktop; conservar archivos históricos de desktop en un traslado no constituye trabajo de producto desktop.

Criterio añadido R37: Migrar a E los archivos del proyecto y sus entornos activos que ocupan C, continuar el trabajo en E/F y retomar el backlog exclusivamente web. Preservar bytes, evidencia RAW histórica, permisos y trazabilidad; no eliminar instalaciones compartidas ni recursos ajenos. Retirar cada origen sólo tras copia y verificación completas y autorización operativa exacta; reparar rutas y worktrees antes de reanudar las validaciones pendientes.

Estado en_curso. No hay aceptación de migración completa, despliegue ni cierre global del backlog. Fuente del mandato: instrucción de sesión del usuario conservada por coordinación; este documento fija su criterio de ejecución y no inventa una cita literal nueva.

## Estado actual al corte160

R37 sigue en_curso. Se aceptaron 33/4207 raíces CTemp: el primer lote de 32 y Root1, con 38.375 archivos y 2.832.653.251 bytes lógicos. El readback independiente Root1 está aceptado en su alcance; Roaming conserva sus tres archivos/51.111 bytes por separado. V3 real ya inició después de validar los 33 previos. No se declara terminado el resto ni aceptado el agregado4207. No se ejecutó la reparación de los nueve worktrees ni los gates finales web. Los apartados históricos y sus RAW conservan el progreso de cada checkpoint; el detalle160 está al final.

## Avance histórico del primer lote (checkpoint157)

El primer lote41a aceptó32raíces reales de4207 inventariadas:206archivos de438581 y1,206,712,194bytes lógicos de24,415,403,485. Quedan4175raíces de esa base. El espacio libre observado en C pasó de2,255,372,288 a3,462,336,512bytes (2.255→3.462GB decimales). Los bytes lógicos y el espacio físico liberado son medidas distintas; hardlinks y asignación impiden igualarlos por suposición.

Root verificó copia completa, fsync, SHA completo del destino y segundo SHA fuente antes de retirar cada origen por handle. Artifact leyó posteriormente los206archivos E completos y verificó ausencia lstat/lexists de las32fuentes exactas, sin mutar fuente/destino. Ese peer compara contra el checkpoint de copia; no acredita lectura independiente del contenido C histórico después de su retirada.

Base Python3.12.13 y WEB92 están copiados y verificados en E; los92 RECORD permanecen iguales y sólo se ajustó pyvenv.cfg del clon activo. Scripts conserva sus bytes históricos con referencias C: usar Epython -m, sin activar esos wrappers. quality10 E es un entorno nuevo offline con10versiones/RECORD de WEB92: el origen Tool10 C se observó incompleto,83archivos, causa desconocida, y no se reparó ni se presenta como clon íntegro. PostgreSQL17 bin/lib/share, Node y uv también se copiaron y leyeron completos; sin cluster/config global ni arranque. El launcher sólo configura el proceso (TEMP/TMP/TMPDIR,caches,PATH portable,datos E y limpieza de COVERAGE_*). No modifica variables User/Machine. No se afirma que invocarlo directamente con & funcione bajo todas las políticas: OpsCI observó un rechazo por ExecutionPolicy del host. Se conserva la política global; usar paths E y variables sólo del proceso, o lanzar el script confiable en un hijo powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass. La excepción se limita a ese proceso. Los10controles previos del launcher conservan sus comandos exactos, ya ejecutados en procesos hijos con esa opción; no se presentan como prueba de invocación directa bajo la política del host. WindowsPowerShell5.1 omite argumentos nativos vacíos y no se localizó LICENSE de Node; límites explícitos del recibo.

Los datos Roaming MetodoBase se copiaron a E/appdata/MetodoBase:3archivos/51,111B, DACL2, SHA completo e identidades ligadas a su plan. Después Root leyó el código716c/plan6f1b, emitió un ACK nuevo y ejecutó la retirada real: COMPLETE, ausencia lstat estricta en C y fullreadback fresco del destino E. Este origen Roaming se registra separado del inventarioCTemp4207. La solicitud original se copió a E/inputs/original-request-20261018.txt,36,051B; su attachment C administrado por la aplicación no se elimina. Las instalaciones compartidas de Python/Node/PG/uv en C y el PostgreSQL ajeno quedan fuera de retirada.

## QA-40 y QA-41: alcance de las reparaciones

8782 permitía sustituir el archivo destino entre CREATE_NEW/ACL/reopen y sobrescribir un outside sintético E. El canario conservado tiene C0.41a mantiene el descriptor original durante ACL/escritura/fsync/readback/retirada;14controles autor y9independientes pasan en fases separadas. El lote real32 y su peer32 tienen aprobación propia. No se afirma que el canario exacto original se repitió ni ausencia global de carreras.

608 traducía PermissionError y OSError31 de os.lstat simulado a False mediante os.path.lexists:1PASS/2FAIL conservados. El intento d8 de usar Path.lstat quedó rechazado:0PASS/3FAIL,0llamadas del mock porque este Python lo despacha por os.stat; sus campos real_filesystem_access:false no son evidencia aceptada y no hubo C.34ad llama os.lstat directamente y sólo captura FileNotFoundError: los3canarios Root literales y7peer pequeños pasan. La biblioteca WinAPI55a permanece idéntica a608; la prueba previa8193handles mantiene su fuente y no se repitió ni demuestra migración8193completa. El SHA del archivo sellado Artifact sigue pendiente; resultados, freeze y review locales sí están disponibles.

## Continuación y límites del checkpoint157 (histórico)

El lote restante4175acaba de iniciar bajo34ad y controladorRoot4797407c/peer73f21403 con MasterRoot nuevo exacto; no hay resultados disponibles y permanece en_curso. Completarlo con sus presupuestos y ACK propios, manteniendo planes/mapas/journals protegidos. Reparar los9worktrees con rutas C sólo después de todas las copias y verificar identidad Git. No reescribir rutas C embebidas en RAW históricos: conservar bytes y añadir mapping para uso operativo nuevo en E/F. No crear junctions para simular que C sigue activo.

Tras cerrar copias y rutas, fijar fuente y entornos finales, revisar una generación/perfil PostgreSQL E nueva y ejecutar los companions B13/R07 autorizados. Siguen pendientes gates amplios serial/n2/cobertura/fullscan, imagen final, SBOM/SCA con DB vigente y Redis/carga.137/quality,PG53,Native35 e imagen144/59 conservan fuentes y entornos anteriores; esta migración no los reejecuta ni los traslada a la fuente actual por declaración documental. Continúan las validaciones externas de proveedores/custodia/retención/soporte/procedencia/legal/nutrición/piloto5+5. Sin push, PR, despliegue, cobros o envíos reales.

Evidencia curada y SHA de metadatos privados: [summary.json](evidence/migration-c-to-e-checkpoint157-20261022/summary.json), [revisión](evidence/migration-c-to-e-checkpoint157-20261022/REVIEW.md). Los RAW anteriores permanecen intactos.

## Checkpoint158 — continuidad parcial E/F

El workspace E ya configura Python web E y temporales/cachés E en terminales nuevos del repositorio F; AGENTS.md registra las rutas. Se preservan variables globales e instalaciones compartidas. El inventario adicional de nombres en Documents/Downloads y entradas directas Local/Roaming no halló candidatos:7lstat/90nombres/3reparse omitidos, profundidad3, sin escaneo universal de C.

El motor optimizado059e1a pasa17originales+11propios+6peer en fases distintas; Win55a y admisión4207 permanecen exactos. Root leyó delta/peer y preservó el MasterACK anterior mediante rename para parar sólo entre raíces, sin cortar la copia en vuelo. V3 no se ha aplicado a C y su controlador sigue pendiente. La primera raíz Native2 aún no está aceptada. Los32orígenes y Roaming del checkpoint157 conservan sus resultados. No se reescriben RAW ni se anticipa reparación de9worktrees.

Root5CIchildTEMP pasa enMain90ddb; CI57 nuevo integrado enMain8d249 pasa18controles offline, y Root prepara realmente Main90ddb con493context/480APP/57dists/12inputs y8controles propios. CalidadMain52209 conTool10E pasa cinco comandos,1623fuentes/10dists/1441RECORD quietos,28Bandit/0pendientes/0errores,9negativos y6positivos. Es continuidad local comprobada, sin serial/n2 completo, SQL, VM, Docker o imagen real nuevos. [Resumen158](evidence/portable-web-continuity-checkpoint158-20261022/summary.json), [revisión](evidence/portable-web-continuity-checkpoint158-20261022/REVIEW.md).


## Checkpoint159 — continuidad web y guardas finitas

Se añaden QA-42, QA-43 y QA-44:165criterios/63verificados locales, con162criterios y estados anteriores y92IDs originales intactos. R37 permanece en_curso; sólo web.

CI57 ya integrado enMain6d81/b7c4: Rootpytest21 PASS18.860s,21JUnit únicos y12fuentes seleccionadas quietas. Autor18pytest/18CLI/3bootstrap y peer6 se conservan como fases, no como criterios duplicados. Los18métodos, directory y main son literales.

Controlador: el binding366 dejó1RED/1control enE;2b22 pasa los2canarios literales y12originales. OtroRED peer mostró COMPLETE histórico no terminal; Root reparó una guarda2b22→eeaa, repitió12+2 y OpsCI pasó7propios incluido eseRED literal. Motor059/Win55a intactos. No se emitió ACK nuevo ni se ejecutóV3 sobreC.

Siguen aceptadas sólo32/4207raícesCTemp y Roaming separado. Native2/Root1 no está aceptada. El readbackRoot1 tiene9canariosREADY,sin auditoría real; el agregado está preparado con20+5fixturesE y freeze8fba,sin configuración/ejecuciónreal4207. Reparación9worktrees y gates amplios/imagen/SBOM/SCA/Redis siguen pendientes. No servicios, SQL, VM, envíos, cargos o despliegue nuevos.

Root completó la configuración local del workspace E: METODOBASE_DATA_DIR apunta a E/appdata/MetodoBase; PYTHONUSERBASE, PYCACHE, NOUSERSITE y directorios UV se fijan por proceso junto a temporales y cachés. SHA actual c3811866; la preimagen 5ef66 del checkpoint158 se conserva sin reasignar su autoridad. El recibo acredita configuración y existencia del directorio, no arranque de aplicación o servicio; no cambia variables Windows User/Machine ni añade un criterio.

[Resumen159](evidence/checkpoint159-web-continuity-20261022/summary.json), [revisión159](evidence/checkpoint159-web-continuity-20261022/REVIEW.md).

## Checkpoint160 — Root1 aceptada y PG27 preparado

Se añade únicamente QA-45: 166 criterios, 64 verificados locales; los 165 criterios y estados previos y los 92 IDs originales permanecen intactos. R37 continúa en_curso y el alcance sigue siendo sólo web.

Root1 cerró normalmente y el auditor independiente 290618 leyó 38.169 archivos/1.625.941.057 bytes/43.960 entradas en E, verificó DACL2, identidades, atributos y tiempos, estabilidad de directorios, recibos/journal y ausencia lstat final C. No leyó payload C. El maestro Native2 terminó exit1 esperado por el desarme en frontera; la raíz tiene resultado accepted y COMPLETE terminal. La auditoría independiente terminó exit0 en 253.691 s. Con el primer lote de 32 quedan aceptadas 33/4207 raíces, 38.375 archivos y 2.832.653.251 bytes lógicos; Roaming es un resultado separado. V3 real inició tras esa verificación, sin anticipar cierre del resto ni agregado 4207.

El falso rechazo ef717 por size de directorios se preserva. Un witness E con churn real tenía asignación 393216 en origen y 0 en destino, con los mismos archivos/bytes. Fix 290618: tres controles del witness MFT (una aceptación y dos rechazos de integridad de archivo), nueve controles originales literales y cuatro peer pasan en fases separadas. No se modificaron motores, controladores, planes o recibos anteriores. La aceptación de Root1 no cierra R37.

PG27 local f095 y Linux Main986 se integraron como preparación: autor local 6, peer inicial 14/16 y followup EOL 2/2; autor Linux 8 sintéticos y 6 Windows; peer Linux 33/34 literal, I04 CRLF preservado, followup GitLF 1/1 y dos controles adicionales. Root Main f095 pasó 6 y plan inerte. Root Main986 conservó 13 PASS/1 ERROR por YAML ausente en BaseE; el único test YAML pasó después en quality10 con PyYAML 6.0.3, 157 fuentes y 18 archivos YAML quietos. El primer followup se rechazó antes del test por framing CRLF y permanece preservado. Ninguna aserción cambió. Los 509 IDs y 71 UUID son inventario y presupuesto futuros, no ejecución SQL, Linux o Actions aceptada.

Nueve reparaciones Git sólo tienen plan y 23 controles sintéticos; requieren cierre global, agregado y nueva autorización Root. Serial/n2/cobertura/fullscan, PG actual, imagen/SBOM/SCA, Redis y validaciones externas siguen pendientes. Runtime, rediseño y PPL exactos 7023; sin nuevos endpoints, producto desktop, despliegue, cobros o envíos reales.

[Resumen160](evidence/checkpoint160-web-continuity-20261022/summary.json), [revisión160](evidence/checkpoint160-web-continuity-20261022/REVIEW.md).

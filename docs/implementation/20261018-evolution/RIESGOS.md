# Riesgos activos

| ID | Impacto / probabilidad razonada | Mitigación | Responsable | Estado |
|---|---|---|---|---|
| EX-01 | Cobros/permisos actuales altos; defectos reproducidos localmente | Contener R01/R02 y exigir regresiones/revisión independiente | Backend / seguridad | en_curso |
| EX-02 | Impacto alto al migrar; el ensayo local no demuestra compatibilidad del estado productivo | R03/R04 ensayados desde vacío/legado y restore completo22/23; tabla24 en gate posterior. Inspección/backup/staging antes de cualquier cambio live | Datos / operación | mitigado_local; staging_pendiente |
| EX-03 | Impacto alto por exclusión incumplida; regresión histórica reproducida, sin dictamen clínico | Catálogo inmutable y validación final con156 regresiones más29 dirigidas. No equivale a garantía clínica ni versión desplegada | Coordinación / QA | mitigado_local; revisión_clínica_pendiente |
| EX-04 | Validación clínica/legal no disponible; ninguna revisión profesional ejecutada | Limitar promesas, registrar dictamen externo sin sustituirlo con agentes | Usuario / profesionales | pendiente |
| EX-05 | Impacto alto si imagen difiere del runtime probado; Docker local no puede ejecutarse | Locks con hashes por target, instalaciones nuevas Windows web/desktop y SCA/SBOM de resolución. Imagen Linux/Redis real y CI remota siguen pendientes | QA / operación | mitigación_parcial |
| EX-06 | Confundir resultado local con despliegue o sandbox; no hay evidencia nueva live | Estado por entorno y artefacto, aprobación final sólo cuando paquete concreto exista | Coordinación | activo |
| EX-07 | La divergencia Free web/desktop tenía tres dimensiones comerciales | Usuario confirmó 10 clientes, 1 plan por cliente/día y 10 totales por gimnasio/día; catálogo único y 46 pruebas independientes. Consumo B2B servidor integrado con pruebas multiproceso; UI idempotente aceptada; revisión completa desktop y contención SEC02 pendientes | Backend / QA | decisión_resuelta; integración_abierta |
| EX-08 | Impacto alto por abuso entre workers; fallo de Redis reproducido con dobles, no con servicio real | Rechazo503, fallback acotado y Lua atómico;52 pruebas QA y69 de revisión backend. Ejecución Redis real permanece pendiente en CI | Coordinación / backend / QA | mitigado_local; Redis_real_pendiente |
| EX-09 | Desfase temporal confirmado de6h en PostgreSQL/México al bind aware sobre TIMESTAMP sin zona; puede acortar derechos o mover periodos | SEC01 corregido; binder adoptado en52 columnas,16 modelos/PG y102 regresiones independientes; dos fechas civiles y jobs legados separados. No reinterpretar historia | Backend / QA | corrección_parcial |
| EX-10 | Pérdida/exposición de PDF/logo; rutas actuales dependen de filesystem y uploads públicos | Metadatos25/consumidores/restore y UI privada aceptados localmente; migración/procedencia histórica y destino durable real pendientes. UUID nuevo evita colisión pero no acredita durabilidad | Root / datos / operación | en_curso |
| EX-11 | Tokens persistentes en navegador y datos de diario locales pueden cruzar sesiones o perderse; inventario confirmado | Exportación personal aislada y R14 preparatorio; migración de sesiones/diario aún necesaria. No cachear exportaciones ni planes con un service worker | Seguridad / frontend | abierto |
| EX-12 | Fallo de compensación B2B expone parámetros SQL en logs globales; dos casos rojos independientes | Helper protegido y handlers/alertas saneados;25 dirigidas y1621 serial/n2 verdes. Otros sinks inventariados siguen abiertos | Root / seguridad / QA | mitigado_local; sinks_restantes_abiertos |
| EX-13 | Borrado físico puede eliminar cartera por CASCADE o perder prueba de consumo/objetos; política de conservación desconocida | No habilitar DELETE de cuenta como sustituto de un workflow. Inventario y exportación técnica; definir alcance, retención, copias y revisión legal antes de borrado | Seguridad / usuario / profesionales | abierto |

| EX-14 | Carrera de refresh y par parcial Storage pueden reenviar DTO bajo otra identidad; reproducidos en memoria | API347 con revisión lógica/cola y confianza pegajosa tiene74 VM independientes. QA39 grupos navegador actuales verdes, incluidos3 Storage; reload, escritores directos y atomicidad entre pestañas siguen abiertos | Frontend / seguridad / QA | mitigado_local_por_instancia; sesiones_integrales_abiertas |
| EX-15 | Reembolso postcommit, periodo mensual incoherente y replay legacy mixto confirmados independientemente | DDL26/marker atómico, periodo de suscripción capturado y lector con doble dueño; seguridad13 verdes tras último lector. Los5 PG finales y muerte real de proceso con worker/PDF pasaron; legacy ambiguo queda retenido. Migración26 requiere drenar procesos antiguos antes de reabrir generación | Backend / QA / coordinación | mitigado_local; transición_operativa_pendiente |
| EX-16 | Cleanup legacy: SQLite borró6 tokens sintéticos en vez de2 y PG informó0 tras fallar la comparación Float/datetime | Integrado0e8cd42:25 únicos QA incluidas fronteras PG UTC/México y fallos de commit/CLI. Parámetros existentes30/90, sin scheduler ni nueva política de retención | Coordinación / operación / QA | mitigado_local; política_legal_pendiente |
| EX-17 | Build desktop mezclaba contrato GUI onedir con validación de servidor/EXE suelto y spec ausente | Receta integrada con94 controles QA, build exacto9f y39 controles independientes de ZIP/procedencia/Qt; instalador sólo preparado. Reemplazo OPS10 pendiente | Operación / frontend desktop / QA | mitigado_local; instalacion_firma_pendientes |
| EX-18 / OPS09 | Alto para procedencia de release: dos flags Git ocultaron cambios que el empaquetador aceptó con commit correcto | Comparación con blobs y tratamiento binario/CR verificados94 QA;1688 fuentes exactas y ZIP revisado39. No acredita distribución ni incidente live | Operación / backend / QA | verificado_local; distribucion_pendiente_OPS10 |
| EX-19 / SEC03 | HTML persistido modificaDOM del drawer; CSP bloqueóJS pero el contenido sigue interpretado | ConstrucciónDOM/textContent/dataset integrada0fa124e;12 controles browser QA,22 fuentes estables. Otros renderers pendientes | Seguridad / QA | mitigado_local |
| EX-20 | Tipo legado usuario junto aOWNER no distingue perfilpersonal de carteraprofesional; test independiente impide ampliación insegura | Preservar exclusión export y rechazar contexto ambiguo del diario nuevo; asociación explícita posterior sin heurística ni cambio automático de roles | Coordinación / datos / seguridad | contención_preservada; asociación_pendiente |

OPS10: artefacto Windows9f contiene material de referencia no usado con nombres/correos sin procedencia acreditada. No se afirma identidad real. Integridad y Qt están aceptados39/39; distribución retenida mientras se excluye ese recurso, se revisa el delta y se construye/verifica el nuevoSHA. Original y primer ZIP se conservan. No confundir este hallazgo con la procedencia de fuentes OPS09 ya verificada.

SEC04 mitigado localmente: consumidor cercado e invalidación síncrona,guardspreclic corregidos; seguridad25VM yQA25grupos/12pantallas verdes. Cuatro rojos606 y dos guard87 preservados. UI integrada; reload/cross-tab/escritores directos permanecen abiertos bajo R10/R31.

SEC05 mitigado localmente e integrado7bde30b: ruta declarada/fallback fijo,métodos cerrados,sin identidad;15propios+63replay independientes,12rojos/3controles previos. R17distribuido,otros sinks y revisión legal siguen abiertos. No afirma incidente externo ni política nueva.

Actualización OPS10:51controlesbundle/ZIP y27payloadInno verifican ausencia casefold de referencia en7bde30b,original intacto. Criterio local cerrado; aún sin distribución,instalación/upgrade/desinstalación o firma. El extractor tercero fijado no está firmado. R16/schema28 aislado: seguridad/QA/restore pendientes;202 significa solicitud recibida,cola no durable,ningún envío real ejecutado. R34 caracteriza carga cerrada; historial ilimitado confirmado requiere paginación y no justifica ampliar pools.

SEC06 cerrado localmente por41708e5/31ebb2f y revisión independiente de JSON malformado. R21 continúa abierto por fuentes posteriores y demás criterios. QA-11 cerrado localmente tras7CLI independientes; no afecta autenticidad de los snapshots históricos preservados. LinuxTCG resuelve disponibilidad de contenedor/Redis local, conserva límites de procedencia de firma y rendimiento; producto todavía sin build aceptado. R34 revisa paginación y mantiene baseline1400sin reescritura. R29 elimina promesas sin respaldo desde un worktree separado.

Imagen Linux de composición92615d7 construida0/698.969s,296archivosGit exactos y contexto17233920bytes sin.env. IDsha256:5eb6d3009ae98c845f2eab0aeff0d249bf336887f124578284714728a3359d0e; inventario real55distribuciones/Python3.12.13/uid999,pipcheck0,capabilities0/no-new-privileges1/rednone/raízreadonly. Sólo build/inventario, no startup de aplicación. SCApip-audit2.10.1/OSV de55paquetes devuelve12entradas equivalentes a6avisos distintos, todos enpip25.0.1 heredado de la base;54distribuciones restantes sin coincidencia en esta consulta. No se declara verdeSCA: actualización bootstrap fijada por hash en preparación, SO aún sin auditar. [Prueba e inventario](evidence/linux-recovery28-image-92615d7/runtime-inventory.json),[auditoría roja](evidence/linux-recovery28-image-92615d7/sca-before/audit.json). No modifica locks/entornosWindows ni demuestra explotación.

Checkpoint104: SEC07 cerrado localmente por24controles independientes y36de composición. R29/UX-16cumplen criterios locales con QA/recorridos reales y retiro de ambas páginas comerciales sin uso. SEC08abierto: pip25.0.1 y CPython3.12.13 heredados; se preservan inventarios y resultados anteriores. Nuevo Linuxaislado en build, aún sin aceptación; Windows/desktop requiere corrección y regresiones propias. Ninguna excepción general ni release autorizado. R34mantiene medición PG/SLO abiertos; R12mantiene revisión de contrato/locks/RLS previa a29.

Checkpoint105: elgate amplio actual2360/1skip enserial/n2 acepta runtime28+historial/landing;la omisiónWindows de symlink requiereLinux.2fallos anteriores fueron unaaserción de test desactualizada trasretirarHTML sinuso yse conservan antes del fix a753.

SEC08 sigue abierto:LinuxPyPI55 verde no implicaOS verde;Trivy87 detectó73IDs/21grupos,sinignore ni excepción. Sólo2alias delmismo defectoliblzma5 tienenfixbinario trixie;restantes71no se descartan porausencia deservicio o comparación deversión. Candidatonuevo conu2 enscan. Windows3.12.15/83PyPI y142tests verdes noactualizanlosZIP/Setup3.12.13 históricos ni acreditanCVE deDLL. R12canónico29 corrige rojosdeprototipo,peroAPI/PDF/restore/seguridad independiente pendientes. NuevosRAW requieren scanexactoR21 posterior.

Checkpoint106: respuesta limitada no prueba trabajoSQL limitado;EXPLAIN dehistorial sigue1000filas. Probes deíndice ylectorUNION ya muestran51,pero faltan migración30/mezclaNULL/revisiónindependiente. Desktop3.12.15 recompilado noimplica payloadrevisado niinstalación. SEC08mantiene71IDsOS ybibliotecasvendorizadas pendientes;capdrop/NNP/rootfsRO no son defaults deDockerfile. Sinexcepcionesderiesgo.

R12 canónico ad712 sigue aislado y fue rechazado por tres negativos PG independientes: permisos de lectura tras cambiar pertenencia de un OWNER fuente o de un OWNER padre, y comprobación diferida con prueba GUC nula antes del commit. Seguridad conserva 18 positivos y esos tres rojos; backend prepara V2. Los 55 casos reutilizados y 22 propios de QA verdes no cierran estos defectos. Sin fuga HTTP ni incidente productivo atribuidos.

Checkpoint107: selladas la revisión independiente desktop66 (93 controles verdes, payload1215 exacto, Python3.12.15/OpenSSL3.5.9/Expat2.8.5/Qt6.8.3; sin ejecutar Setup) y las revisiones R12V1/V2. QA95 de V1 no cerró sus tres fallos de seguridad; V2 1aac pasó los mismos21 criterios independientes, sin cambiar el driver. Fuentes y paquetes estables; bases propias cerradas. Aceptación limitada al coreV2, sin casts/restore/API ni integración29. Los RAW y manifiestos originales permanecen exactos y se añaden atributos binarios sólo a estas nuevas carpetas para conservarlos en Git.


## Checkpoint 108

SEC09/P1, operación y seguridad: OpenSSL3.5.8 depsycopg2-binary coincide con13 rangosCNA; Debianpatch no lo cubre. Impacto condicionado por API/protocolo/arquitectura/compilación, explotación no demostrada. Mitigación en curso: componente mantenido con procedencia y reconstrucción/SCA/regresión independiente; no excepción. R03/OPS01:bootstrap histórico exigeCREATEROLE pese a contrato migradorrestringido; reproducciónLinux42501 y rollback completo. Se corrige código, sin elevar permisos. R18 ya dispone LinuxQEMU operativo: se elimina el bloqueo obsoleto de falta dehost; quedan componentes/startup y gateOS abiertos.


## Checkpoint 109

UX-18/P1 bloquea exportaciónUI en flujoR12 por interferencia deestado disabled;mitigaciónownedControls yreplay16independiente en curso. R34pool1:waiterGETauthme checkout,holderdesconocido;no atribuir causa ni cerrarlo conpool20. C4fix nativoaceptado, Linuxcorregidopendiente;ACLheredados sepreservan ynosepurgaunrolglobal sin alcanceaplicable. SEC09/71OSsiguenabiertos. 55484apagado y recursos propioscerradosconidentidadverificada.


## Checkpoint 110

CI29 no se acepta con checker vacío, runner falso, replace-ref o export-ignore que suplanten la fuente histórica. Los pins del ejecutable corrigen sólo el primer grupo; verificar árbol/blobs del archivo sigue pendiente. Emisor e8: expiración antigua puede redirigir una recuperación B síncrona; sin fuga o DTO B enviado demostrado. R34 pool1 continúa sin holder identificado. d038 estático no cierra71 IDs OS/13 coincidencias CNA, ni acredita imagen o producción.


## Checkpoint 111

Los bypass CI29 anteriores están corregidos y aceptados independientemente; rechazos conservados. CI30 aún pendiente. e8+9eb tiene aceptación focal, no composición. R23 parcial y readonly. Linux imagen/SCA/ProductionSettings/readiness pendiente; no inferir cierre71IDs de triage estático. Pool1 holder desconocido sigue abierto.


## Checkpoint 112

SEC10 Expat2.8.5 embebido sincapacityfix13c5f63; no reparación ni vía remota demostrada. SQLite50812 exclusión v3 rechazada;71 OS siguen abiertos. c02 scriptsparent arreglado sólo estático; build/runtime/SCA efectivo pendiente. Pool1holder desconocido abierto. Regresión30 debe corresponder a merge actual.


## Checkpoint 113

R23 sigue parcial por responsables/eventos no persistidos. El foco768 fue corregido y revisado sólo en fuente aislada; no declaración global de accesibilidad. MFA31 y R24 tienen hallazgos funcionales/concurrencia en corrección; no aceptados. Expat requiere reparar componente cargado y artefacto real; Linux y71OS siguen abiertos.


## Checkpoint 114

SEC11 retorno fuera de origen y validación dentro de breaker requieren corrección común previa al puerto/circuito. Restore31 tiene deriva CHECK en corrección sólo31;22–30 intactos. Cuatro UUID candidatos de spawn sin atribución no se eliminan. R24 botón oculto se mantiene disabled en9bfa, sin fuga/capacidad demostrada; revisión final pendiente. Expat necesita artefacto real;71OS abiertos.


## Checkpoint 115

R23 sigue parcial por responsables/eventos persistidos. R24errores404 requieren no-referrer, fix4042 aislado enQA;98dirigidaspreimagen timeout no pasaron. SEC11candidato pendiente revisióncircuito/grants. Restore31 autor verde no sustituye QA/Seguridad. Políticaretención pendiente y71IDsOS abiertos.


## Checkpoint 116

SEC12:aliases31 no ligan key observada al grant/puerto,4rojos+1control; reparación/revisión pendientes, sin bypassfactor/doblecargo demostrado. R24/R23 siguen parciales. MFA31 authorrestore no sustituye QA/Seguridad/UI/CI.71 IDsOS ypolíticaR31 pendientes.


## Checkpoint 117

SEC13 parent/actor canónicos de31 requieren invitation_token estrictamenteNULL bajo locks al emitir/consumir.2rojos/4controles, sinacciónexternareal. SEC12fix yprivacidadprimary enrevisión; no aceptarMFA por corregir sólo5o20. Linux71OS,políticaR31,pilotos yconfiguraciónproveedores siguenpendientes.


## Checkpoint 118

MFA no está aceptado integralmente: faltan QA de integración/UI, CI31 y restauración independiente, avisos, custodia/rotación de claves y configuración real de servicios. No existe recuperación administrativa simulada ante pérdida de todos los factores. R34 no reprodujo el timeout, por lo que ampliar el pool no acredita solución. Continúan los71 IDs OS, la política de privacidad y los pilotos externos.


## Checkpoint119

PersistenCI31/regresiónactual/imagen,avisosMFA/custodia/configuraciónrealypérdidatotaldefactores. UX19tieneaceptaciónfocal, noreplay15posterior. STOPbrowsernoobservócierregrácil/claveRAMafter,limitesexplícitos. QA-12confianzaenfixtureenpeer. D60noacreditaABI/linkage/SCA/71OS. Políticas,pilotos,clínicaySLOrequierenhechos/decisionesreales.


## Checkpoint 120

CI e0 no tiene aceptación por omisión de siete casos nuevos snapshot y marcador de rol opcional. El checker CLI sigue en revisión. La compilación nativa está activa, sin prueba final de ABI/linkage ni SCA. No se infiere seguridad de producto desde un marcador incompleto del laboratorio.


## Checkpoint 121

Pendientes: integración y regresión amplia31,173PG eimagen común; instrumentación argv y exportaciones ELF del target nativo; revisión independiente R17 y aspectos operativos MFA. OPS13 conserva la diferencia real de símbolos y su causa: falta -fvisibility=hidden de la configuración interna de la base. Continúan políticas, entrevistas/pilotos reales, validación profesional y objetivos de carga sin inventarlos.


## Checkpoint122

Pendientes peer79, regresión serial con cobertura y n2 de la composición,imagen común y operacionesMFA. Linux requiere revisar/reconstruir argvreal yvisibilidad antes de aceptación. R25DDL32 aún exclusivo ysinproducto; políticas/países/SLO/pilotos/dictámenes no inventados.


## Checkpoint 123

Pendientes resultado broadserial/n2 de809, imagen común y validación nativa72. R25 añade mediciones/consentimiento32 bajo revisión; el acceso compartido no puede depender de un GUC falsificable ni exponer sesiones o filas privadas. Siguen configuración/operacionesMFA, políticas, objetivos de carga, pilotos y dictámenes reales pendientes.


## Checkpoint124

Pendientes peerSEC15,nueva fullserial/n2, imagen runtime ysourcefixposterior. Native72diagnóstico no cierra54/SCA71/SEC10. R25lector/restore32/freeze e integración pendientes. ConfiguraciónMFA,avisos,custodia,rotación,políticas,objetivos,pilotos ydictámenes siguen sin inventarse.


## Checkpoint125

QA-16 helpers aceptados acotadamente; serial/n2 de la composición31 siguen pendientes, y las pruebas seriales no garantizan aislamiento de contextos copiados. R25/R31 retiroparentOFF sigue abierto, al igual que restore32/CI32/matrizcomún. Runtime nuevo requiere sello delsmoke/cierre yrevisión; c538rojo no acreditahealth/ready/worker. RAMhostobservada cerca1.5GiBconVM2GiB: sinChrome ni nuevos trabajos pesados simultáneos, cierrecooperativo de propios. CryptographyOpenSSL4.0.3 ysystem3.5.7 son identidades distintas y no cierranSCA71. Se conserva lease32write_text noexclusivo como límite de evidencia. Políticas/retención/países, SLOrepresentativo, pilotos, dictamen especialista y dependenciasMFA/proveedores siguen pendientes.


## Checkpoint126

Worker31 todavía sin atestación completa; source/image parcial no habilita despliegue. Serial/n2 y matrizcomún32 pendientes. Retiroexcepcional yGoogle-only requieren pruebas; asociaciónsub nuevaDDL/backfillnoautorizada por inferencia ni implementada todavía. VMOFF liberóRAM después de presión observada; QA esperó1.8GiB antesCREATE, no se tocó proceso ajeno. Las dependencias de políticas, países, retención, SLO, pilotos y especialista permanecen abiertas.


## Checkpoint127

Las migraciones locales reversibles necesarias están autorizadas; inventar identidad Google histórica a partir de email carece de evidencia y no es una migración técnica legítima. SEC17 y SEC18 pendientes de aceptación. Gitleaks global31564remaining:2FPmetadata confirmados/31562previos sin clasificar, no todo falso positivo. Worker31parcial no habilita despliegue. Países,retención,SLO,pilotos,especialista y pérdida total de factores permanecen abiertos.


## Checkpoint128

MAIN es candidata local32, todavía sin regresión/CI/artefacto común vigente. SEC17 Google pendiente y las limitaciones de recuperación total/legacy Google siguen abiertas. SEC18 tiene aceptación focal, pero ninguna implementación puede prometer checkout0 si también falla invalidate antes de liberar. Gitleaks no está globalmente verde. Política de retención/países, objetivos SLO, entrevistas y validación profesional real siguen pendientes de datos/autorización aplicable.


## Checkpoint129

Implementación33 yUI integradas localmente en3587. Los8 criterios originales del primer peer pasan con transporteJWT/JWKS normalizado yasserts AST exactos. PeerPG,ataques,QAHTTP/browser yCI siguen en curso; no se declara cierre global. Las pruebas e intentos de la nueva UI Google se mantienen enRAM. Esto no resuelve la exposición legacy global deStorage,retención,borrado o acceso de soporte. El clasificador finito no acepta secretos nuevos. La historia de tareas prevista exige inventario ypurga bajoR31; no se inventa una política legal de conservación. El gate globalR05 sigue abierto yel árbol33 no tiene un escaneo completo nuevo. Las cifras de tablas34 son previsión,no observación. Países/retención,volumen/SLO,entrevistas yvalidación profesional requieren datos oparticipación real.

## Checkpoint130

Candidato8012 cubre14.557 ocurrencias/14.516pins únicos/155archivos del informe17c9, ahora sin ubicaciones pendientes de triage. Registrov1 instalado intacto; revisión independiente nueva en curso. No es escaneo nuevo ni PASS global. Los nueve digests de configuración prueban productor puro y recibos, sin reconstruir valores privados. Revisión completa de fuente3587 conservada, incluidos dos framingSSR rojos y carreraQA-17. El fix8a5e tiene replay propio independiente verde. Los canarios de adopción previos se preservan. Aceptación global33 y continuidad legacy aún abiertas.

## Checkpoint131

Persisten1.603hallazgos del último escaneo real yse requiere scan final de artefacto estable. Ninguna ubicación nueva se presume falsa positiva. El cierre de PG240 yla recuperación de agentes tras cuota se auditan antes de reutilizarPG55483; no se reejecuta a ciegas.

## Checkpoint132

El candidato Backend34 devuelve409 followup_busy ante IntegrityError desconocido durante flush y ante SQLITE_ERROR=1 de tabla inexistente cuyo nombre contiene blocked. Falla la clasificación de disponibilidad; no se confirma bypass de autorización, explotación remota ni fuga de datos. La reproducción deQA-18 permanece abierta hasta corrección yreplay independiente. QA recuperó sin rerun los20reportes/240IDs únicos PG33 sobrec86:240PASS0FAIL/error/skip. 52UUID propias ausentes y0sesiones confirmados en conexión nueva tras la pausa; DROP ordinario ysin terminate. 1114fuentes/92distribuciones/8084archivos instalados ybinarios exactos. Los testigos distinguen engine de negocio de15sondeos auxiliares poscaso; no se atribuye su engine al negocio. Fuentesc86/R05v1; composiciónMAINv2, broad,Chrome,imagen,Linux yActions no demostrados por esta fase.

## Checkpoint135

SEC19 conserva riesgo de hidratación innecesaria hasta revisión independiente; SEC20 yQA-21 están reproducidos enPG y requieren reparación antes de integración34. QA-20 bloquea el guardado progresivo delAPI en perfil vacío. Responsable:backend/seguridad/coordinación. Desktop tiene excepción expresa de alcance para la entrega actual; no se afirma que el defectoQA-19 haya desaparecido.

## Checkpoint136

SEC21 refleja declaración rechazada en422 para bodylista; requiere erroracotado porruta antes de integrar35. QA-23 investiga retenciónpool con ORMexpirable; no se declara impacto enFalse. QA-22ya tieneparche,peerPGfocal pendiente desello. Responsables seguridad/coordinación. Riesgos legales/retención/proveedor/piloto permanecen externos; transporteStorage no resuelto aún.

## Checkpoint137

SEC21/22 yQA23 tienen reparación ypeerfocal; no integradosMAIN. R31 requiere cierre extremo aextremo ycompatibilidadCI, sin reponerJWTStorage para obtenerPASS. SEC23ABAcontacto yQA-24optoutanónimo son candidatos36 todavía sinpeer/PG. Retención/países,SLO,piloto,proveedorcorreo yvalidaciónprofesional permanecen sin resolución externa. No aceptación global ni despliegue.

## Checkpoint139

SEC24 tenía consultaBearer previa al rechazoOrigin enAPI; reparación y106 controles independientes cierran focalmente el candidato, pendiente integración. Los nativos antiguos inyectanJWTStorage y requieren nueva composición, sin etiquetarlosPASS. Restore36 reveló deriva deCHECK antes/despuésdump y no se acepta todavía. Retención, países, SLO acordado, piloto y revisión profesional requieren evidencia o participación externa.

## Checkpoint140

R31 UI tienepeer26PASS local; nativos/CI antiguos dependen deStorage yfixtures31/33. Notificaciones36 mantiene puertos cerrados hasta revisiónQA/SEC/UI; su tolerancia a incertidumbre nunca prueba envío o causalidad. Retención, países, SLO acordado, piloto yrevisión profesional mantienen sus decisiones externas pendientes.

## Checkpoint141

Nativo actual rechazado por accesos DOM tras invalidación. Registro público API puede persistir una identidad antes de responder500 con Bearer ajeno. R05 global RED1603 y CI/broad/imagen/restore actuales pendientes; PG37 y consumo UI pendiente. Retención, países, SLO y piloto conservan decisiones externas pendientes.

## Checkpoint142

Nativo15actual,peerPG37/restore,UI27/UI37,CI/broad/imagen/escaneoactualpendientes. MAINcontinúa35, porloquecorrecciónQA-26ycandidatos36/37aúnnoestánintegrados. Retención,países,SLOypilotoconservandecisionesexternaspendientes.

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

Rediseño y rutinas pueden afectar navegación, reflow, foco e invalidación de sesión. Mitigación: contratos DOM conservados, autorización API revalidada, pruebas por roles y navegador a320/390/768/1440, revisión independiente. Responsable: frontend/backend con coordinación yQA/seguridad. Estado: en_curso. El catálogo es educativo y general, sin predicción de resultados ni prescripción individual.

## Checkpoint150 — 2026-10-21

Riesgo de foco invisible en menús móviles, impresión y ciclo de sesión tras rediseño: QA nativa independiente preparada con16capturas y flujos reales. Fuente50325congelada hasta esa validación. Tool81 incompleto yclusterTemp antiguo no arrancable se preservan; reemplazos de pruebas aislados verifican sus propias versiones/identidades. No hay evidencia para atribuir una causa común. Owners: coordinación, QA/seguridad yoperación; estado en_curso.

## Checkpoint151 — 2026-10-21

Foco móvil/impresión/sesión delpanel comprobados en16capturas;35flujos actuales yPostgreSQLfocal pendientes.353pytestPASS primerintentoREJECTEDporbudget se conserva;429válidos porfases. Tool10/Tool81 incompletos hoy,sincausa demostrada. No reescribir esos entornos para aparentar quietud; preparar otro aislado si hacefalta un gate nuevo.

## Checkpoint152 — 2026-10-21

QA-33 puede producir falsoPASS al clasificar todos los hallazgos de un escaneo parcial. Bloquea aceptación de seguridad completa hasta corregir/revisar/repetir el gate actual. Los diagnósticos descartados impiden atribuir la causa exacta de la corrida25d. Root detectó además una carrera de publicación del ACK propio; se conserva el rechazo y se corrige sólo la publicación, sin ampliar el plazo ni aceptar el intento como navegador ejecutado.

## Checkpoint153 — 2026-10-21

QA33global sigueabierto hastaescaneoactualcompleto;loscontadores antiguosnoacreditancompletitud. Error depermisos delproductorOpsse corrigióenrootnuevo,pasado4ACEpreservado yrechazadoenesaspecto,sin afirmación de exposición. PGreadonly/RLS deR30aúnsinpruebareal;SQLite/lectura deSQLAlchemy no sustituyenPG. F2.30GiBestrecho:ningunaVMhasta revisar presupuesto/espacio propio,sinprune/custodiahistórica.

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

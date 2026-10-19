# Trazabilidad de ejecución

Ejecución: `20261018-evolution`. Fuente canónica: [TRAZABILIDAD.json](TRAZABILIDAD.json).

Los 92 IDs se conservan; los solapamientos no representan defectos independientes. Los estados pendientes no constituyen aprobación.

| ID | Prioridad | Responsable | Tareas | Estado | Validación | Entorno |
|---|---|---|---|---|---|---|
| [R01](#r01) | P0 | Backend y datos | R01 | en_revision | en_curso | local |
| [R02](#r02) | P0 | Backend y datos | R02 | en_curso | en_curso | local |
| [R03](#r03) | P0 | Backend y datos | R03 | en_revision | en_curso | local |
| [R04](#r04) | P0 | Backend y datos | R04 | en_revision | parcial | local |
| [R05](#r05) | P0 | QA y automatización | R05 | en_revision | en_curso | local |
| [R06](#r06) | P0 | Backend y datos | R06 | en_curso | en_curso | local |
| [R07](#r07) | P1 | Operación y documentación | R07 | en_revision | parcial | local |
| [R08](#r08) | P1 | Operación y documentación | R08 | en_revision | en_curso | local |
| [R09](#r09) | P1 | Coordinación y arquitectura | R09 | en_revision | en_curso | local |
| [R10](#r10) | P1 | Seguridad y privacidad | R10 | en_curso | en_curso | local |
| [R11](#r11) | P1 | Backend y datos | R11 | en_revision | parcial | local |
| [R12](#r12) | P1 | Backend y datos | R12 | pendiente | pendiente | local |
| [R13](#r13) | P1 | Frontend y UX/UI | R13 | en_revision | en_curso | local |
| [R14](#r14) | P1 | Backend y datos | R14 | en_curso | parcial | local |
| [R15](#r15) | P1 | Frontend y UX/UI | R15 | en_revision | en_curso | local |
| [R16](#r16) | P1 | Backend y datos | R16 | pendiente | pendiente | local |
| [R17](#r17) | P1 | Operación y documentación | R17 | en_revision | en_curso | local |
| [R18](#r18) | P1 | QA y automatización | R18 | en_revision | en_curso | local |
| [R19](#r19) | P1 | QA y automatización | R19 | en_revision | pendiente | local |
| [R20](#r20) | P1 | Coordinación y arquitectura | R20 | en_curso | en_curso | local |
| [R21](#r21) | P2 | Operación y documentación | R21 | en_revision | en_curso | local |
| [R22](#r22) | P1 | Frontend y UX/UI | R22 | pendiente | pendiente | local |
| [R23](#r23) | P2 | Frontend y UX/UI | R23 | pendiente | pendiente | local |
| [R24](#r24) | P2 | Frontend y UX/UI | R24 | pendiente | pendiente | local |
| [R25](#r25) | P2 | Backend y datos | R25 | pendiente | pendiente | local |
| [R26](#r26) | P1 | Backend y datos | R26 | en_revision | en_curso | local |
| [R27](#r27) | P2 | Backend y datos | R27 | pendiente | pendiente | local |
| [R28](#r28) | P2 | Backend y datos | R28 | pendiente | pendiente | local |
| [R29](#r29) | P2 | Frontend y UX/UI | R29 | pendiente | pendiente | local |
| [R30](#r30) | P1 | Coordinación y arquitectura | R30 | pendiente | pendiente | local |
| [R31](#r31) | P1 | Seguridad y privacidad | R31 | en_revision | parcial | local |
| [R32](#r32) | P1 | Seguridad y privacidad | R32 | pendiente | pendiente | local |
| [R33](#r33) | P1 | Coordinación y arquitectura | R33 | en_curso | en_curso | local |
| [R34](#r34) | P2 | QA y automatización | R34 | pendiente | pendiente | local |
| [R35](#r35) | P2 | Frontend y UX/UI | R35 | pendiente | pendiente | local |
| [B01](#b01) | P0 | Backend y datos | R01 | en_curso | en_curso | local |
| [B02](#b02) | P1 | Backend y datos | R01, R09, R26 | pendiente | pendiente | local |
| [B03](#b03) | P1 | Backend y datos | R01 | pendiente | pendiente | local |
| [B04](#b04) | P1 | Backend y datos | R03, R04 | en_revision | en_curso | local |
| [B05](#b05) | P1 | Backend y datos | R04 | pendiente | pendiente | local |
| [B06](#b06) | P1 | Backend y datos | R02, R11 | en_curso | en_curso | local |
| [B07](#b07) | P1 | Backend y datos | R02 | en_curso | en_curso | local |
| [B08](#b08) | P1 | Seguridad y privacidad | R10 | en_curso | en_curso | local |
| [B09](#b09) | P1 | Backend y datos | R06, R33 | en_curso | en_curso | local |
| [B10](#b10) | P1 | Operación y documentación | R08 | en_revision | en_curso | local |
| [B11](#b11) | P1 | Operación y documentación | R07 | pendiente | pendiente | local |
| [B12](#b12) | P1 | Operación y documentación | R17 | en_revision | en_curso | local |
| [B13](#b13) | P2 | Backend y datos | R01, R19, R26 | en_curso | en_curso | local |
| [B14](#b14) | P2 | Backend y datos | R01, R19, R26 | en_curso | en_curso | local |
| [B15](#b15) | P1 | Backend y datos | R01, R26, R27 | en_curso | en_curso | local |
| [B16](#b16) | P2 | Backend y datos | R01, R19, R28 | en_revision | en_curso | local |
| [B17](#b17) | P2 | Backend y datos | R01, R14, R19, R28, R34 | en_revision | en_curso | local |
| [B18](#b18) | P2 | Backend y datos | R03, R26 | en_revision | en_curso | local |
| [B19](#b19) | P2 | Seguridad y privacidad | R10, R11, R16, R32 | en_curso | en_curso | local |
| [B20](#b20) | P2 | Seguridad y privacidad | R10, R31, R32 | en_curso | en_curso | local |
| [B21](#b21) | P1 | QA y automatización | R18 | en_curso | en_curso | local |
| [B22](#b22) | P2 | Backend y datos | R02, R06, R17, R20 | en_curso | en_curso | local |
| [B23](#b23) | P1 | Backend y datos | R06, R33 | en_curso | en_curso | local |
| [OPS01](#ops01) | P0 | Backend y datos | R03 | en_revision | en_curso | local |
| [OPS02](#ops02) | P0 | Backend y datos | R04 | pendiente | pendiente | local |
| [OPS03](#ops03) | P1 | Operación y documentación | R07 | pendiente | pendiente | local |
| [OPS04](#ops04) | P1 | Operación y documentación | R08 | en_revision | en_curso | local |
| [OPS05](#ops05) | P1 | Operación y documentación | R17 | en_revision | en_curso | local |
| [OPS06](#ops06) | P1 | Backend y datos | R16, R27 | pendiente | pendiente | local |
| [OPS07](#ops07) | P1 | QA y automatización | R05, R18 | en_revision | en_curso | local |
| [QA-01](#qa-01) | P0 | QA y automatización | R05 | en_revision | en_curso | local |
| [QA-02](#qa-02) | P0 | QA y automatización | R05 | en_revision | en_curso | local |
| [QA-03](#qa-03) | P0 | Backend y datos | R03 | en_revision | en_curso | local |
| [QA-04](#qa-04) | P0 | Backend y datos | R03 | en_revision | en_curso | local |
| [QA-05](#qa-05) | P0 | Backend y datos | R02, R04, R19 | pendiente | pendiente | local |
| [QA-06](#qa-06) | P1 | Coordinación y arquitectura | R09 | pendiente | pendiente | local |
| [QA-07](#qa-07) | P1 | QA y automatización | R05 | en_revision | en_curso | local |
| [QA-08](#qa-08) | P1 | QA y automatización | R05, R19 | en_revision | en_curso | local |
| [QA-09](#qa-09) | P1 | QA y automatización | R05, R13, R19 | en_revision | en_curso | local |
| [QA-10](#qa-10) | P2 | QA y automatización | R05, R18, R21 | en_revision | en_curso | local |
| [UX-01](#ux-01) | P0 | Backend y datos | R01, R15, R26 | en_curso | en_curso | local |
| [UX-02](#ux-02) | P0 | Backend y datos | R06, R24, R33 | en_curso | en_curso | local |
| [UX-03](#ux-03) | P1 | Backend y datos | R14, R31 | pendiente | pendiente | local |
| [UX-04](#ux-04) | P1 | Backend y datos | R14 | pendiente | pendiente | local |
| [UX-05](#ux-05) | P1 | Frontend y UX/UI | R13, R35 | en_revision | en_curso | local |
| [UX-06](#ux-06) | P1 | Backend y datos | R11 | pendiente | pendiente | local |
| [UX-07](#ux-07) | P1 | Backend y datos | R12, R25 | pendiente | pendiente | local |
| [UX-08](#ux-08) | P1 | Frontend y UX/UI | R13 | en_revision | en_curso | local |
| [UX-09](#ux-09) | P1 | Frontend y UX/UI | R13, R35 | en_revision | en_curso | local |
| [UX-10](#ux-10) | P1 | Frontend y UX/UI | R15, R24 | pendiente | pendiente | local |
| [UX-11](#ux-11) | P2 | Frontend y UX/UI | R15, R22 | pendiente | pendiente | local |
| [UX-12](#ux-12) | P1 | Frontend y UX/UI | R15, R20, R22 | pendiente | pendiente | local |
| [UX-13](#ux-13) | P2 | Backend y datos | R01, R15, R23, R26, R27 | en_revision | en_curso | local |
| [UX-14](#ux-14) | P2 | Backend y datos | R03 | en_revision | en_curso | local |
| [UX-15](#ux-15) | P2 | Backend y datos | R06, R16 | en_curso | en_curso | local |
| [UX-16](#ux-16) | P2 | Coordinación y arquitectura | R09, R29 | pendiente | pendiente | local |
| [UX-17](#ux-17) | P2 | Frontend y UX/UI | R15, R22, R24, R30 | pendiente | pendiente | local |
| [OPS08](#ops08) | P1 | Coordinación y operación | R03, R18, R20 | en_revision | parcial | local |
| [SEC01](#sec01) | P0 | Root - seguridad y licencias; backend - campos/preparaciónR04 | R01, R04, R09, R31 | en_revision | parcial | local |

## R01

Fuente: [R01 P0](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: Unificar cobros, catálogo y derechos Pro

Criterio original: Ningún POST/redirect ni pago incompleto concede acceso; `pro_usuario` persiste; cancelación/impago reconcilia ambas tablas y derechos; eventos repetidos/desordenados no duplican acceso; cuota agotada no genera

Estado: en_revision; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Contención A1 integrada localmente; ver CAMBIOS.md para comportamiento y límites por criterio.; Carrera GET/proyección vs reserva corregida e integrada;3casos PG con tres procesos. B2B diario/mes, sandbox y R04 posteriores siguen abiertos.; Reserva B2B atomica antesCPU: cliente activo/cupo10, diario10gym/1cliente, mensual20Free; calendario local, hash idempotente y publicacion persistida sin reembolso tras crash/FKNULL.

Commits: 166038f88b211c52f0d149ce550880795361707c, c769667, b81cfc1, e3039c2, 5bb5395

Pruebas: A1:207passed/0failed/0skipped en candidatoWindows3.12.13; huella estable328archivos.; 18 PG independientes +41 worker/nutricion(5PDF reales),6 migraciones y restore24;25 seguimiento compensacion/logs/PDF/caducidad. Serial/n2 finales1621 cadauno,1skip Windows.

Evidencia: evidence/backend-before.log; evidence/backend-money-contract.md; evidence/security-money-source.json; evidence/A1-containment.xml; evidence/A1-containment-source.json; evidence/pytest-quota-postgres-before.xml; evidence/pytest-quota-postgres-after.xml; evidence/quota-a1-snapshot.json; evidence/gym-quota-independent-source.json; evidence/pytest-gym-quota-independent.xml; evidence/error-compensation-final-independent-source.json; evidence/model-utc-independent-source.json; evidence/pytest-model-utc-auth-billing-license-independent.xml

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md; CATALOGO.md; B2B_CUOTAS.md

Revisión: QA y seguridad independientes; coordinador integra, alcance local sin sandbox ni despliegue

Bloqueo: no registrado

Observaciones: Cuota individual: carrera GET/reserva corregida y revisada en PostgreSQL con 3 procesos (3 casos aprobados). Reserva B2B y compra sandbox real siguen abiertas.; Seguimiento temporal confirmado con4DBUUID: columnas TIMESTAMPsinTZ de suscripcion y plan desplazan6h al bindawareUTC bajoMexicoCity; helperUTC9a53215 aceptado32independientes; adopcion en curso, sin reinterpretar filas historicas. No llamar a las4pruebas diagnosticas una correccion.; UTC modelos adoptado:52 instantes explicitos/2civiles conservadas,16PGindependientes+102auth/billing/licencias verdes; sinDDL ni reescritura de historia.

## R02

Fuente: [R02 P0](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: Corregir RBAC e identidad de equipo

Criterio original: VIEWER recibe 403 al crear; login/refresh conservan membresía autorizada; cambios de rol tienen efecto verificable; matriz completa por recurso

Estado: en_curso; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Contención A1 integrada localmente; ver CAMBIOS.md para comportamiento y límites por criterio.

Commits: 166038f88b211c52f0d149ce550880795361707c

Pruebas: A1:207passed/0failed/0skipped en candidatoWindows3.12.13; huella estable328archivos.

Evidencia: evidence/backend-auth-review.md; evidence/security-controls.md; evidence/A1-containment.xml; evidence/A1-containment-source.json

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## R03

Fuente: [R03 P0](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: Reconciliar esquema y reparar migraciones Railway

Criterio original: Copia staging, inventario y backup; `preDeployCommand` real; base vacía y base existente llegan al mismo esquema; fallos detienen deploy; enum de roles coherente

Estado: en_revision; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Preparación local sin DDL en fábricas;31 casos autor y15 independientes, vacío/legado/drift/restore22tablas. Staging, privilegios y R04 siguen abiertos.

Commits: e8a6806, b81cfc1, 5bb5395

Pruebas: pendiente

Evidencia: evidence/alembic-empty-psycopg2-before.log; evidence/backend-r03-before.log; evidence/backend-r03-paths-restorable.xml; evidence/pytest-r03-restorable-independent.xml; evidence/r03-restorable-independent-source.json; evidence/gym-migrations-independent-source.json; evidence/pytest-gym24-restore-independent.xml; evidence/gym24-restore-independent-source.json; evidence/model-utc-independent-source.json; evidence/pytest-model-utc-auth-billing-license-independent.xml

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md; evidence/backend-r03-design.md; evidence/coordinator-r03-review.md

Revisión: Coordinador y QA independientes del autor backend; alcance local R03/R08, no aceptación productiva.

Bloqueo: no registrado

Observaciones: Seguimiento temporal confirmado con4DBUUID: columnas TIMESTAMPsinTZ de suscripcion y plan desplazan6h al bindawareUTC bajoMexicoCity; helperUTC9a53215 aceptado32independientes; adopcion en curso, sin reinterpretar filas historicas. No llamar a las4pruebas diagnosticas una correccion.; Head24 anade ledgerB2B y politica18 sin reescribir contratos22/23.6 casos migracion y restore24 completo independientes; staging y operacion real pendientes.; UTC modelos adoptado:52 instantes explicitos/2civiles conservadas,16PGindependientes+102auth/billing/licencias verdes; sinDDL ni reescritura de historia.

## R04

Fuente: [R04 P0](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: Implantar privilegios mínimos y aislamiento PostgreSQL

Criterio original: Tras R02/R03; rol app sin superusuario/BYPASSRLS; tenant por transacción y por job; pruebas negativas con dos gimnasios y rol real restringido

Estado: en_revision; implementación: parcial; validación: parcial; despliegue: no_desplegado; entorno: local.

Dependencias: R02, R03

Cambios: pendiente

Commits: f325fc4, 501ceaa, b81cfc1, 5bb5395

Pruebas: Coordinador independiente:19 aprobadas,63.30s; preparacion23 SQLite/PostgreSQL sin activar politicas

Evidencia: evidence/coordinator-r04-preparation-review.md; evidence/r04-preparation-root.xml; evidence/r04-preparation-root-source.json; evidence/r04-followup-independent-source.json; evidence/pytest-r04-followup-independent.xml; evidence/r04-activation-root-final.xml; evidence/gym-migrations-independent-source.json; evidence/pytest-gym24-restore-independent.xml; evidence/gym24-restore-independent-source.json; evidence/model-utc-independent-source.json; evidence/pytest-model-utc-auth-billing-license-independent.xml

Documentación: AISLAMIENTO.md

Revisión: pendiente

Bloqueo: no registrado

Observaciones: Aceptacion local:17familias FORCE/ENABLE,6controlplane explicitas;64matriz y37seguimiento+restore23. Staging/produccion pendientes.; Head24 anade ledgerB2B y politica18 sin reescribir contratos22/23.6 casos migracion y restore24 completo independientes; staging y operacion real pendientes.; UTC modelos adoptado:52 instantes explicitos/2civiles conservadas,16PGindependientes+102auth/billing/licencias verdes; sinDDL ni reescritura de historia.

## R05

Fuente: [R05 P0](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: CI web reproducible y pruebas bloqueantes

Criterio original: Manifest de test explícito; SQLite local y PostgreSQL de CI separados; sin depender del orden global de tests; lint/seguridad material bloquean según baseline aprobado

Estado: en_revision; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Contención A1 integrada localmente; ver CAMBIOS.md para comportamiento y límites por criterio.; 14fuentes seguimiento congeladas, aislamiento/CI bloqueante preparada, contratos obsoletos sustituidos por comportamiento; Redis real/R04/imagen/CI remota pendientes.

Commits: 166038f88b211c52f0d149ce550880795361707c, e8e0c44, 64fe65a, e3039c2

Pruebas: A1:207passed/0failed/0skipped en candidatoWindows3.12.13; huella estable328archivos.; Quality scripts/entrypoints: lint, AST, Bandit y canarios reales bloqueantes;111 pruebas independientes incluyen9 SQLite archivadas y102 contratos de identidad/equipo; 1621pass/1skip serial182.54s y n2shuffle111.34s seed20261018;387Python/deps+55frontend estables e identicas. Unico skip symlinkWindows; no Linux/imagen/Redisreal.

Evidencia: QA_R05.md; evidence/pytest-r05-frozen-candidate.xml; evidence/qa-r05-frozen-hashes.json; evidence/A1-containment.xml; evidence/A1-containment-source.json; evidence/r05-followup-frozen-source.json; evidence/coordinator-quality-expansion-review.md; evidence/quality-expanded-source.json; evidence/quality-expanded-root-canaries.log; evidence/pytest-team-quality-root.xml; evidence/web-candidate-containment-final-source.json; evidence/pytest-web-candidate-containment-final.xml; evidence/web-candidate-containment-shuffle-source.json; evidence/pytest-web-candidate-containment-shuffle.xml; evidence/qa-b2b-privacy-utc-final-source.json

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md; QA_R05.md

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## R06

Fuente: [R06 P0](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: Contención de promesas alimentarias y validación básica

Criterio original: Edad/peso/altura/grasa inválidos no se guardan; retirar promesa de aplicar notas; excluir categoría completa no restaura alimentos; bloquear garantías no soportadas; contrato completo pasa a R33

Estado: en_curso; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Contención A1 integrada localmente; ver CAMBIOS.md para comportamiento y límites por criterio.

Commits: 166038f88b211c52f0d149ce550880795361707c

Pruebas: A1:207passed/0failed/0skipped en candidatoWindows3.12.13; huella estable328archivos.

Evidencia: evidence/security-review.md; evidence/pytest-nutrition-independent.xml; evidence/coverage-nutrition-focused.json; evidence/A1-containment.xml; evidence/A1-containment-source.json

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## R07

Fuente: [R07 P1](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: Almacenamiento persistente de documentos y logos

Criterio original: Tras definición de tenant; archivos sobreviven a redeploy; descargas autorizadas; migración de referencias y manejo de fallos probado

Estado: en_revision; implementación: parcial; validación: parcial; despliegue: no_desplegado; entorno: local.

Dependencias: R04

Cambios: pendiente

Commits: abc896f, 9b97068

Pruebas: 33 pruebas independientes aprobadas y1 symlink omitida Windows; volumen privado y SDK S3 Stubber. Sin DB/consumidores/proveedor real.; 32 SDK independientes de configuracion explicita (27autor+5seguridad); no runtimemetadata/consumidor aun.

Evidencia: evidence/storage-volume-author.xml; evidence/storage-sdk-author.xml; evidence/storage-volume-harness-before.json; evidence/r07-storage-frontend-independent-source.json; evidence/r07-storage-frontend-fix-independent.xml; evidence/security-storage-configuration-source.json; evidence/security-storage-configuration.xml

Documentación: ALMACENAMIENTO.md

Revisión: Frontend independiente y coordinador; adaptadores solamente

Bloqueo: "Metadatos/RLS posteriores a R04, consumidores y migracion por implementar; proveedor/volumen persistente, contenedor y retencion pendientes de validacion/decision"

Observaciones: 33independientes/1symlinkomitidaWindows; adapters solamente, sin DB/consumidores/proveedorreal.

## R08

Fuente: [R08 P1](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: Restauración y plan de continuidad

Criterio original: Verificar backups nativos e independientes según riesgo; ensayo de restauración con medición RPO/RTO; una ejecución sin fuente respaldada falla

Estado: en_revision; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Contención A1 integrada localmente; ver CAMBIOS.md para comportamiento y límites por criterio.; Restore real del esquema Alembic22tablas, relaciones/secuencias/revisión/PDF/logo; cifrado+MAC. Tiempos técnicos no equivalen a RPO/RTO ni backup nativo.

Commits: 166038f88b211c52f0d149ce550880795361707c, e8a6806, b81cfc1

Pruebas: A1:207passed/0failed/0skipped en candidatoWindows3.12.13; huella estable328archivos.

Evidencia: BACKUP_RESTORE.md; evidence/security-review.md; evidence/postgres-restore-independent.json; evidence/A1-containment.xml; evidence/A1-containment-source.json; evidence/postgres-restore-release-schema-independent.json; evidence/pytest-r03-restorable-independent.xml; evidence/gym-migrations-independent-source.json; evidence/pytest-gym24-restore-independent.xml; evidence/gym24-restore-independent-source.json

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md; BACKUP_RESTORE.md; evidence/coordinator-r03-review.md

Revisión: QA independiente y revisión seguridad/coordinador.

Bloqueo: no registrado

Observaciones: Head24 anade ledgerB2B y politica18 sin reescribir contratos22/23.6 casos migracion y restore24 completo independientes; staging y operacion real pendientes.

## R09

Fuente: [R09 P1](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: Una fuente de límites, precios y características

Criterio original: Tras R01; decidir Free 5 o 10 sin inferirlo de un test; API, web y Stripe reflejan el catálogo; desktop sólo si sigue soportado; importes/moneda/periodicidad claros

Estado: en_revision; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: R01

Cambios: Contención A1 integrada localmente; ver CAMBIOS.md para comportamiento y límites por criterio.; Reserva B2B atomica antesCPU: cliente activo/cupo10, diario10gym/1cliente, mensual20Free; calendario local, hash idempotente y publicacion persistida sin reembolso tras crash/FKNULL.

Commits: 166038f88b211c52f0d149ce550880795361707c, af177b1, b81cfc1, e3039c2

Pruebas: A1:207passed/0failed/0skipped en candidatoWindows3.12.13; huella estable328archivos.; Seguimiento:3regresiones realesDBmoroso/expirado rojas antes;33after;QA46conlímites de periodos.; 18 PG independientes +41 worker/nutricion(5PDF reales),6 migraciones y restore24;25 seguimiento compensacion/logs/PDF/caducidad. Serial/n2 finales1621 cadauno,1skip Windows.

Evidencia: DECISIONES.md; evidence/A1-containment.xml; evidence/A1-containment-source.json; evidence/catalog-before.log; evidence/catalog-after.xml; evidence/gym-quota-independent-source.json; evidence/pytest-gym-quota-independent.xml; evidence/error-compensation-final-independent-source.json

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md; CATALOGO.md; B2B_CUOTAS.md

Revisión: QA y seguridad independientes; coordinador integra, alcance local sin sandbox ni despliegue

Bloqueo: no registrado

Observaciones: Usuario aprobó Free10clientes,1planporcliente/día,10planestotalesgym/día; soporte desktop continúa. Fuente única y precios/periodo/mes separados. Integración/aceptación completa aún abierta.

## R10

Fuente: [R10 P1](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: Sesiones y revocación coherentes

Criterio original: Access de duración corta, refresh de larga duración; desactivar usuario/miembro impide acciones; cerrar sesión invalida el acceso según política documentada

Estado: en_curso; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Contención A1 integrada localmente; ver CAMBIOS.md para comportamiento y límites por criterio.

Commits: 166038f88b211c52f0d149ce550880795361707c, dbb6af5

Pruebas: A1:207passed/0failed/0skipped en candidatoWindows3.12.13; huella estable328archivos.

Evidencia: evidence/backend-auth-review.md; evidence/security-controls.md; evidence/A1-containment.xml; evidence/A1-containment-source.json; evidence/security-error-privacy-source.json; evidence/security-error-privacy-after.xml

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md; evidence/security-error-privacy.md

Revisión: pendiente

Bloqueo: no registrado

Observaciones: Contencion concreta de handlers/tracker automaticos y compensacion verificada con13regresiones. No declara saneados login, email, auth_audit, Sentry o alertas directas; R31 inventaria esos pendientes.

## R11

Fuente: [R11 P1](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: Equipo utilizable de extremo a extremo

Criterio original: Tras R02 y correo; pantalla GET de invitación y canje POST de un uso; caducidad/revocación; navegación por permisos; dueño invita y miembro accede a su gimnasio

Estado: en_revision; implementación: parcial; validación: parcial; despliegue: no_desplegado; entorno: local.

Dependencias: R02, R16

Cambios: pendiente

Commits: b03e20a, 5bb5395

Pruebas: pendiente

Evidencia: evidence/ux/team-followup-independent-review.json; evidence/pytest-r11-followup-independent.xml; evidence/model-utc-independent-source.json; evidence/pytest-model-utc-auth-billing-license-independent.xml

Documentación: EQUIPO.md

Revisión: pendiente

Bloqueo: no registrado

Observaciones: La etapa102 pruebas no acepta el cierre: QA/backend encontraron carreras de cambios de rol/revocacion y nuevas invitaciones sin derecho comercial. Correcciones CAS/comerciales/legacy en revision con nuevas huellas.; 128independientes y11UI/7flujosreales; CAS/entitlement/perfillegacy verificados local. Entrega real y vinculacion consentida de cuentas previas pendientes.; UTC modelos adoptado:52 instantes explicitos/2civiles conservadas,16PGindependientes+102auth/billing/licencias verdes; sinDDL ni reescritura de historia.

## R12

Fuente: [R12 P1](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: Relación gimnasio cliente y cuenta de acceso

Criterio original: Tras R04; distinguir cuenta individual y socio de gym; invitación vincula usuario al cliente correcto; socio consulta el mismo plan asignado por su gym; no ve otro gym

Estado: pendiente; implementación: pendiente; validación: pendiente; despliegue: no_desplegado; entorno: local.

Dependencias: R04

Cambios: pendiente

Commits: pendiente

Pruebas: pendiente

Evidencia: pendiente

Documentación: pendiente

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## R13

Fuente: [R13 P1](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: Corregir móvil, teclado y accesibilidad

Criterio original: Suscripciones/clientes sin acciones cortadas a 320/390 px y regresión 768/1440; hamburguesa no tapa títulos; controles nombrados; foco y Enter correctos; PDF accesible en historial

Estado: en_revision; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: B2B6recorridos, R13 17estados y5personales con27fuentes estables. TransporteAPI sintético, no sandbox/auth/RLS/lector de pantalla. Seguimiento R11 corrige fixture token y añade auth real.

Commits: c45a71c

Pruebas: pendiente

Evidencia: evidence/ux/frontend-independent-source.json; evidence/ux/frontend-independent-review.md

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md; CATALOGO.md

Revisión: QA independiente; root revisó contratos/sinks/destinos B2B.

Bloqueo: no registrado

Observaciones: sin observaciones

## R14

Fuente: [R14 P1](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: Persistir seguimiento del usuario y del socio

Criterio original: Empezar con usuario individual y fecha local sin esperar R12; integrar pertenencia al gym después; mismo estado en dos dispositivos; logout no borra historial; nunca mezcla cuentas

Estado: en_curso; implementación: parcial; validación: parcial; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: pendiente

Commits: 4e22852

Pruebas: Preparacion pura35independientes tras1regresionRecursionError; NO API/DB/UI servidor implementados aun.

Evidencia: evidence/personal-diary-values-independent-source.json; evidence/pytest-personal-diary-values-independent.xml

Documentación: DIARIO.md

Revisión: QA independiente de DTO/helpers, sin cierre de persistencia R14

Bloqueo: no registrado

Observaciones: sin observaciones

## R15

Fuente: [R15 P1](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: Estados de progreso y pago veraces

Criterio original: No mostrar 100% por contenido del menú; redirect no afirma pago; perfil incompleto lleva a completar datos; errores visibles y accionables

Estado: en_revision; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: B2B6recorridos, R13 17estados y5personales con27fuentes estables. TransporteAPI sintético, no sandbox/auth/RLS/lector de pantalla. Seguimiento R11 corrige fixture token y añade auth real.

Commits: c45a71c

Pruebas: pendiente

Evidencia: evidence/ux/frontend-independent-source.json; evidence/ux/frontend-independent-review.md

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md; CATALOGO.md

Revisión: QA independiente; root revisó contratos/sinks/destinos B2B.

Bloqueo: no registrado

Observaciones: sin observaciones

## R16

Fuente: [R16 P1](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: Correo e inicio de recuperación de cuenta

Criterio original: Proveedor verificado y entregas observables; invitación y recuperación con tokens de un uso/caducidad; sin enumeración de cuentas ni envíos reales desde pruebas

Estado: pendiente; implementación: pendiente; validación: pendiente; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: pendiente

Commits: pendiente

Pruebas: pendiente

Evidencia: pendiente

Documentación: pendiente

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## R17

Fuente: [R17 P1](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: Alarmas, degradación Redis y trazabilidad

Criterio original: Caída Redis simulada no elimina límites de rutas sensibles; webhooks/cola/backup/correo tienen métricas y alertas; logs sin tokens o notas de salud

Estado: en_revision; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Redis: Lua atómico, TTL estable, acciones sensibles503, lecturas fallback acotadas; dependencia5/900 compartida y HMAC de cuenta. Revisión independiente pendiente.; Contención aceptada localmente:52QA y69revisión backend; falta Redis real, ingress y alertas de servicios.

Commits: 0a0b6d4, dbb6af5

Pruebas: pendiente

Evidencia: evidence/redis-dependency-before.log; evidence/redis-final-author.xml; evidence/pytest-redis-final-independent.xml; evidence/redis-final-independent-source.json; evidence/backend-policy-review.md; evidence/security-error-privacy-source.json; evidence/security-error-privacy-after.xml

Documentación: REDIS.md; evidence/security-error-privacy.md

Revisión: QA y backend independientes del autor root.

Bloqueo: no registrado

Observaciones: 21 pruebas autor aprobadas. Redis real y alertas externas pendientes; no equivale a cierre completo R17.; Contencion concreta de handlers/tracker automaticos y compensacion verificada con13regresiones. No declara saneados login, email, auth_audit, Sentry o alertas directas; R31 inventaria esos pendientes.

## R18

Fuente: [R18 P1](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: Dependencias e imagen trazables

Criterio original: Lock Linux coherente con Docker, SBOM y escaneo de resolución/imagen; actualizar advisories aplicables; promover el mismo digest; excepciones con vencimiento

Estado: en_revision; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: pendiente

Commits: 822de09

Pruebas: pendiente

Evidencia: evidence/sbom-linux-runtime.json; evidence/sca-linux-runtime-final.log; evidence/backend-runtime-static-review.json

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md

Revisión: pendiente

Bloqueo: {"falta": "Host Linux/Docker operativo para construir y escanear imagen/digest exacto.", "obtener": "Habilitar virtualización del host mediante decisión del usuario o usar runner Linux autorizado existente.", "responsable": "Usuario/operación", "puede_continuar": "Locks conhash, instalación Windows, SCA resolución, SBOM y CI preparada; no atribuirlos a imagen ejecutada."}

Observaciones: 32requisitos/13COPY revisados estaticamente backend y seguridad; Dockerfile usa hashes y basepin, desktopmanifest alineado. No imagenfinal ejecutada/SCAimagen; SDKR07 todavia fuera runtime.

## R19

Fuente: [R19 P1](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: Suite E2E de recorridos y abuso

Criterio original: Tras R01/R02/R12; compra sandbox, impago, refresh, invitación, generación, PDF, seguimiento y dos tenants; workers aislados; cada error bloquea el release correspondiente

Estado: en_revision; implementación: pendiente; validación: pendiente; despliegue: no_desplegado; entorno: local.

Dependencias: R01, R02, R12

Cambios: pendiente

Commits: e3039c2

Pruebas: 1621pass/1skip serial182.54s y n2shuffle111.34s seed20261018;387Python/deps+55frontend estables e identicas. Unico skip symlinkWindows; no Linux/imagen/Redisreal.

Evidencia: evidence/web-candidate-containment-final-source.json; evidence/pytest-web-candidate-containment-final.xml; evidence/web-candidate-containment-shuffle-source.json; evidence/pytest-web-candidate-containment-shuffle.xml; evidence/qa-b2b-privacy-utc-final-source.json

Documentación: pendiente

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## R20

Fuente: [R20 P1](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: Documentación vigente y límites de arquitectura

Criterio original: README web, mapa actual, matriz de permisos, ADR de billing/tenant/storage, contratos y runbooks por commit; requisitos en cada PR posterior

Estado: en_curso; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Contención A1 integrada localmente; ver CAMBIOS.md para comportamiento y límites por criterio.

Commits: 166038f88b211c52f0d149ce550880795361707c, 9a53215, b81cfc1, dbb6af5

Pruebas: A1:207passed/0failed/0skipped en candidatoWindows3.12.13; huella estable328archivos.

Evidencia: ESTADO.md; TRAZABILIDAD.json; evidence/A1-containment.xml; evidence/A1-containment-source.json

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md; ARQUITECTURA_ACTUAL.md; B2B_CUOTAS.md; PRIVACIDAD.md; UTC_DATETIME.md

Revisión: pendiente

Bloqueo: no registrado

Observaciones: Mapa actual/transitorio yERD explicitos; contratos/docs porhito. Inventario definitivo yrunbooks release/piloto aunpendientes.

## R21

Fuente: [R21 P2](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: Higiene del repositorio

Criterio original: Retirar entornos versionados y artefactos históricos del árbol activo con revisión; ignorar venv/.venv-test; secretos escaneados sin publicar valores; dependencias se reinstalan

Estado: en_revision; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Retiro del índice de1648archivos de entornos versionados; original e historial preservados.; Scan exacto b20e071:1006 archivos/0hallazgos, estable; canarioindependiente valida excepcionesSHApublicas. Commits/WIP posteriores exigen escaneo final.

Commits: dff6fd9, cd78c47, 19298e7, b20e071

Pruebas: pendiente

Evidencia: evidence/repository-comparison.json; evidence/secrets-tree-final.json; evidence/pytest-secret-encoding-independent.xml; evidence/secrets-encoding-wrapper-independent.json; evidence/secrets-commit-binding.json; evidence/secrets-self-report-triage.json; evidence/secrets-09243-triage.json; evidence/secrets-b20-limited-independent.json

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md; HIGIENE.md

Revisión: QA revisó configuración/wrapper/canarios; coordinador revisó retiro de artefactos.

Bloqueo: no registrado

Observaciones: Pendiente cierre de higiene completa/portabilidad/escaneo; commit por sí solo no cierra requisito.; Scan exactcommit887files,0findings,estable; no WIP/historia/imagen/produccion.; No generalizar scan1006b20 alheadUTC/IaC/diario/PDF/UI posterior.

## R22

Fuente: [R22 P1](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: Mejorar onboarding existente por objetivo

Criterio original: Probar 5 dueños y 5 socios; dueño llega a primer plan asignado; socio comprende acción diaria; reanudar proceso; datos demo identificados y separables

Estado: pendiente; implementación: pendiente; validación: pendiente; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: pendiente

Commits: pendiente

Pruebas: pendiente

Evidencia: pendiente

Documentación: pendiente

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## R23

Fuente: [R23 P2](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: Convertir dashboard de retención en acciones

Criterio original: Extender dashboard existente: lista priorizada por causa, próximo paso y responsable; distinguir cobro real de fecha de membresía; acciones medibles

Estado: pendiente; implementación: pendiente; validación: pendiente; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: pendiente

Commits: pendiente

Pruebas: pendiente

Evidencia: pendiente

Documentación: pendiente

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## R24

Fuente: [R24 P2](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: Mejorar plan diario y lista de compras

Criterio original: Tras R14; menú legible, porciones y sustituciones autorizadas; hábitos/consumo reales; lista por periodo; estados vacíos y de error revisados

Estado: pendiente; implementación: pendiente; validación: pendiente; despliegue: no_desplegado; entorno: local.

Dependencias: R14

Cambios: pendiente

Commits: pendiente

Pruebas: pendiente

Evidencia: pendiente

Documentación: pendiente

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## R25

Fuente: [R25 P2](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: Progreso compartido con el profesional

Criterio original: Tras R12/R14; tendencias de medidas y adherencia, fecha/fuente visibles y permisos explícitos; sin gráficos ficticios ni conclusiones médicas automáticas

Estado: pendiente; implementación: pendiente; validación: pendiente; despliegue: no_desplegado; entorno: local.

Dependencias: R12, R14

Cambios: pendiente

Commits: pendiente

Pruebas: pendiente

Evidencia: pendiente

Documentación: pendiente

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## R26

Fuente: [R26 P1](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: Suscripción y facturación comprensibles

Criterio original: Tras R01/R09; plan actual, cuotas restantes, precio MXN, periodo y estado verificados; cancelar/renovar claros; la UI distingue licencia del gym de membresía del socio

Estado: en_revision; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: R01, R09

Cambios: B2B6recorridos, R13 17estados y5personales con27fuentes estables. TransporteAPI sintético, no sandbox/auth/RLS/lector de pantalla. Seguimiento R11 corrige fixture token y añade auth real.

Commits: c45a71c

Pruebas: pendiente

Evidencia: evidence/ux/frontend-independent-source.json; evidence/ux/frontend-independent-review.md

Documentación: CATALOGO.md

Revisión: QA independiente; root revisó contratos/sinks/destinos B2B.

Bloqueo: no registrado

Observaciones: sin observaciones

## R27

Fuente: [R27 P2](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: Recordatorios y recuperación de pagos

Criterio original: Tras R16/R26; preferencias/consentimiento, límites de frecuencia, reintentos y exclusión; distinguir mora confirmada de falta de registro; medir renovaciones sin atribuir causalidad indebida

Estado: pendiente; implementación: pendiente; validación: pendiente; despliegue: no_desplegado; entorno: local.

Dependencias: R16, R26

Cambios: pendiente

Commits: pendiente

Pruebas: pendiente

Evidencia: pendiente

Documentación: pendiente

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## R28

Fuente: [R28 P2](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: Generación y efectos externos durables

Criterio original: Si las métricas lo justifican; job persistido, idempotencia/outbox, reintentos y estado UI; reinicio no pierde plan ni duplica correos/cuota

Estado: pendiente; implementación: pendiente; validación: pendiente; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: pendiente

Commits: pendiente

Pruebas: pendiente

Evidencia: pendiente

Documentación: pendiente

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## R29

Fuente: [R29 P2](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: Landing comercial conectada al producto

Criterio original: Mensaje para dueño y socio, prueba/demo y precio vigente; CTAs visibles en móvil; enlazar recorridos reales; retirar promesas y páginas huérfanas

Estado: pendiente; implementación: pendiente; validación: pendiente; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: pendiente

Commits: pendiente

Pruebas: pendiente

Evidencia: pendiente

Documentación: pendiente

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## R30

Fuente: [R30 P1](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: Analítica y entrevistas de producto

Criterio original: Medir desde semana 1 y revisar por cohorte; eventos mínimos sin salud/PII; baseline antes de objetivos; entrevistas y decisión de continuar cada experimento

Estado: pendiente; implementación: pendiente; validación: pendiente; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: pendiente

Commits: pendiente

Pruebas: pendiente

Evidencia: pendiente

Documentación: pendiente

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## R31

Fuente: [R31 P1](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: Privacidad y gestión del dato personal

Criterio original: Iniciar en fase 1; inventario/finalidad/retención, acceso de soporte, exportar/borrar, consentimientos aplicables y revisión legal del servicio; prueba de borrado en copias/objetos según política

Estado: en_revision; implementación: parcial; validación: parcial; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Exportacion personal readonly integrada ambosfactories/UI por partes; propietario excluye cartera profesional, UUID preservado, limites bytes y sin persistir descarga en navegador. Contencion de handlers/alertas automaticas sin str/traceback/metadata libre.

Commits: dbb6af5, e3039c2

Pruebas: 41 preparatorias+2 composiciones PG restringido reales+8 grupos navegador/5 pantallas independientes;13 seguridad incluidas en25 dirigidos y serial/n2 finales1621 cadauno.

Evidencia: evidence/security-controls.md; evidence/privacy-independent-source.json; evidence/pytest-privacy-final-independent.xml; evidence/privacy-composition-independent-source.json; evidence/pytest-privacy-composition-independent.xml; evidence/ux/privacy-export-independent-source.json; evidence/security-error-privacy-source.json; evidence/pytest-error-compensation-final-independent.xml

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md; PRIVACIDAD.md; evidence/security-error-privacy.md

Revisión: QA independiente de servicio/composicion/GUI; coordinador reviso servicio/UI y contencion; autor seguridad separado de autores B2B/UI

Bloqueo: "Retencion/borrado legal y de copias sin politica aprobada; cierre de cuenta/consentimientos/tokens/sinks restantes pendientes. Export tecnicamente integrado no sustituye esos criterios."

Observaciones: Dictamen profesional externo no ejecutado ni sustituido por revisión de agentes; tarea técnica local sigue abierta.; Montado y aceptado localmente tras41preparatorias; documento actualizado despuesdel freeze sin cambiar servicio/router. No snapshot entre paginas ni binarios/desktop/diario local exportados.

## R32

Fuente: [R32 P1](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: MFA o passkeys para roles privilegiados

Criterio original: Tras R10/R16; alta, desafío, recuperación y revocación probados; step-up para equipo/facturación; adopción sin bloquear recuperación legítima

Estado: pendiente; implementación: pendiente; validación: pendiente; despliegue: no_desplegado; entorno: local.

Dependencias: R10, R16

Cambios: pendiente

Commits: pendiente

Pruebas: pendiente

Evidencia: pendiente

Documentación: pendiente

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## R33

Fuente: [R33 P1](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: Garantías del motor y revisión profesional

Criterio original: Iniciar en fase 1; contrato estructurado de alergias/exclusiones sin depender del plan pagado; entradas límite, unidades y repetibilidad; validar con especialista; condiciones clínicas fuera de automatismo no validado

Estado: en_curso; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: pendiente

Commits: pendiente

Pruebas: pendiente

Evidencia: evidence/pytest-nutrition-independent.xml; evidence/security-review.md

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md

Revisión: pendiente

Bloqueo: no registrado

Observaciones: Dictamen profesional externo no ejecutado ni sustituido por revisión de agentes; tarea técnica local sigue abierta.

## R34

Fuente: [R34 P2](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: Rendimiento con carga representativa

Criterio original: Datos sintéticos, p95 y colas medidos por flujo; índices/paginación/pools ajustados a hallazgos; objetivos acordados; sin pruebas de carga sobre producción

Estado: pendiente; implementación: pendiente; validación: pendiente; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: pendiente

Commits: pendiente

Pruebas: pendiente

Evidencia: pendiente

Documentación: pendiente

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## R35

Fuente: [R35 P2](../../audit/2026-10-18/ROADMAP_PRIORIZADO.md).

Problema: Evaluar PWA y acceso rápido móvil

Criterio original: Sólo tras retención y rendimiento básicos; instalar acceso y manejar conectividad con privacidad; no cachear planes sensibles sin política; construir si mejora uso medido

Estado: pendiente; implementación: pendiente; validación: pendiente; despliegue: no_desplegado; entorno: local.

Dependencias: R14, R34

Cambios: pendiente

Commits: pendiente

Pruebas: pendiente

Evidencia: pendiente

Documentación: pendiente

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## B01

Fuente: [B01 P0 Activar Pro sin pago y antes de confirmar Stripe](../../audit/2026-10-18/backend/INFORME_BACKEND.md).

Problema: `web/routes/usuario.py:543` admite `POST /api/usuario/suscripcion` con `{"plan":"pro"}` y persiste el plan, el límite y `status=active` sin intervención de un proveedor. Reproducción local: HTTP 200 y Pro habilitado. `usuario_stripe_subscribe` en la línea 619 hace lo mismo tras crear una suscripción que puede estar `incomplete`. `usuario_confirm_subscription` en la línea 659 activa Pro incluso cuando el servicio devuelve `activated=False`: también reproducido.

Criterio original: un usuario no puede adquirir derechos de pago mediante un cambio de preferencias. Los derechos se actualizan desde un servicio único tras confirmar identidad del cliente, precio/moneda, estado del proveedor y período pagado. Tarjeta rechazada, autenticación pendiente o `activated=False` conservan el plan gratuito. Los escenarios deben pasar por API con proveedor de pruebas y webhooks firmados.

Estado: en_curso; implementación: en_revision; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Contención A1 integrada localmente; ver CAMBIOS.md para comportamiento y límites por criterio.

Commits: 166038f88b211c52f0d149ce550880795361707c

Pruebas: A1:207passed/0failed/0skipped en candidatoWindows3.12.13; huella estable328archivos.

Evidencia: evidence/backend-before.log; evidence/backend-money-contract.md; evidence/security-money-source.json; evidence/A1-containment.xml; evidence/A1-containment-source.json

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## B02

Fuente: [B02 P1 El plan Pro pagado no cabe en el esquema de suscripciones](../../audit/2026-10-18/backend/INFORME_BACKEND.md).

Problema: `web/constants.py` define `pro_usuario`; `web/services/stripe_service.py:286` confirma esa compra mediante `activate_subscription`. `web/database/models.py:336` restringe `Subscription.plan` a free, standard, gym_comercial y clinica. El catálogo de PostgreSQL confirma el mismo constraint en producción. Reproducción local: `activate_subscription(..., "pro_usuario")` produce IntegrityError. Un cobro correcto puede terminar sin activación fiable.

Criterio original: separar explícitamente suscripciones B2B y B2C o usar un modelo común consistente. Pruebas de compra, renovación, cancelación, reembolso y pago fallido actualizan el derecho correcto para ambos tipos de cuenta. Ningún cobro queda sin reconciliación por una restricción del esquema.

Estado: pendiente; implementación: pendiente; validación: pendiente; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: pendiente

Commits: pendiente

Pruebas: pendiente

Evidencia: pendiente

Documentación: pendiente

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## B03

Fuente: [B03 P1 La generación individual no aplica ni registra la cuota mensual](../../audit/2026-10-18/backend/INFORME_BACKEND.md).

Problema: `web/routes/usuario.py:310` genera sin consultar `UserSubscription`, comprobar `max_planes_mes` o incrementar `planes_usados_mes`. Reproducción con Starter agotado 1/1: HTTP 200, generador invocado y contador intacto. La interfaz puede mostrar un límite que el servidor no impone.

Criterio original: reservar cuota de forma atómica antes de generar, devolverla cuando el trabajo falle según la política definida, consumirla una sola vez ante reintentos y usar la zona/período del producto. Dos solicitudes simultáneas con un crédito restante producen como máximo un trabajo aceptado.

Estado: pendiente; implementación: pendiente; validación: pendiente; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: pendiente

Commits: pendiente

Pruebas: pendiente

Evidencia: pendiente

Documentación: pendiente

Revisión: pendiente

Bloqueo: no registrado

Observaciones: Contención individual no cierra reservaB2B, concurrenciaPG/multiproceso ni compra real sandbox; nueva carrera de lectura al cambio de mes identificada, pendiente corrección backend.

## B04

Fuente: [B04 P1 PostgreSQL opera sin RLS ni control de migraciones y la app usa superusuario](../../audit/2026-10-18/backend/INFORME_BACKEND.md).

Problema: Producción: todas las banderas RLS son falsas, políticas vacías y ausencia de alembic_version. La app está configurada con el rol postgres superusuario/BYPASSRLS. Un filtro `gym_id` omitido en código no tendría una segunda barrera de base de datos; esto no demuestra que hoy exista acceso cruzado explotable.

El código contribuye al problema: `db_bootstrap.py:56` hace create_all y, en una base nueva, `:80` hace stamp(head), sin ejecutar las políticas o backfills de las migraciones. `:117` oculta errores de upgrade. `web/main_web.py:160` vuelve a crear tablas en startup y la revisión de versión solo emite advertencias. El hook Railway se revisa en el informe principal de infraestructura.

Criterio original: inventariar y reconciliar el esquema existente con un plan de migración probado en un clon, backup y restauración verificada. Ejecutar migraciones con un rol separado; la app usa NOSUPERUSER/NOBYPASSRLS y permisos mínimos. Una base vacía llega a head ejecutando migraciones, incluidos datos y políticas; cualquier error aborta el despliegue. No ejecutar stamp indiscriminadamente sobre producción.

Estado: en_revision; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Preparación local sin DDL en fábricas;31 casos autor y15 independientes, vacío/legado/drift/restore22tablas. Staging, privilegios y R04 siguen abiertos.

Commits: e8a6806

Pruebas: pendiente

Evidencia: evidence/backend-r03-paths-restorable.xml; evidence/pytest-r03-restorable-independent.xml; evidence/r03-restorable-independent-source.json

Documentación: evidence/backend-r03-design.md; evidence/coordinator-r03-review.md

Revisión: Coordinador y QA independientes del autor backend; alcance local R03/R08, no aceptación productiva.

Bloqueo: no registrado

Observaciones: sin observaciones

## B05

Fuente: [B05 P1 Habilitar RLS exige reparar primero el contexto de todas las sesiones](../../audit/2026-10-18/backend/INFORME_BACKEND.md).

Problema: `web/database/engine.py:128` instala tenant solo en get_db/get_db_readonly y solo al principio de la transacción. `web/middleware/tenant.py:61` ignora usuarios individuales sin equipo. `web/routes/planes.py:88` y `:293` abren SASession directamente; webhooks en `web/routes/billing.py:301` y `:505` abren SessionLocal sin tenant. Los commits internos terminan el SET LOCAL y la siguiente transacción de esa sesión no lo reinstala. Activar FORCE RLS con un rol restringido puede romper generación, perfil individual, cobros y otras lecturas.

Criterio original: una fábrica de sesiones/unidad de trabajo instala el tenant validado en cada transacción, también en workers. El consumidor de webhooks resuelve el tenant desde un identificador de proveedor confiable y usa un permiso explícito. Pruebas reales PostgreSQL con dos gimnasios, miembros, cuenta individual y usuario sin tenant verifican denegación cruzada y funcionamiento completo, incluidos commits internos y devolución de conexiones al pool.

Estado: pendiente; implementación: pendiente; validación: pendiente; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: pendiente

Commits: pendiente

Pruebas: pendiente

Evidencia: pendiente

Documentación: pendiente

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## B06

Fuente: [B06 P1 La identidad de equipo se pierde al entrar y refrescar](../../audit/2026-10-18/backend/INFORME_BACKEND.md).

Problema: `web/auth.py:238` consulta ya la misma tabla usuarios que el supuesto fallback de equipo. Construye el rol a partir de tipo y omite team_gym_id; por ello el fallback de `web/routes/auth.py:95` queda sin uso para credenciales válidas. `_get_user_by_id` en `web/auth.py:543` repite la pérdida al refrescar. Reproducido: ambos flujos devuelven viewer sin asociación. Google en `web/routes/auth.py:217` también infiere owner para cualquier tipo usuario y omite la membresía. Registro, contraseña, Google e invitación no producen la misma identidad.

Criterio original: una sola función transforma el usuario persistido en identidad autenticada; conserva rol y membresía validados y distingue cuenta individual de miembro. Login, OAuth, invitación y refresh entregan los mismos permisos. Cambiar rol o quitar acceso surte efecto según una política de revocación explícita.

Estado: en_curso; implementación: en_revision; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Contención A1 integrada localmente; ver CAMBIOS.md para comportamiento y límites por criterio.

Commits: 166038f88b211c52f0d149ce550880795361707c

Pruebas: A1:207passed/0failed/0skipped en candidatoWindows3.12.13; huella estable328archivos.

Evidencia: evidence/backend-auth-review.md; evidence/security-controls.md; evidence/A1-containment.xml; evidence/A1-containment-source.json

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## B07

Fuente: [B07 P1 Un VIEWER puede crear clientes](../../audit/2026-10-18/backend/INFORME_BACKEND.md).

Problema: `web/routes/clientes.py:72` depende de check_daily_registration_limit, pero ni la ruta ni esa dependencia verifican `create,cliente`. La tabla de permisos niega esa acción a viewer. Reproducción local: token viewer con team_gym_id válido crea un cliente del gimnasio con HTTP 201, aunque has_permission devuelve false.

Criterio original: permisos obligatorios por ruta o caso de uso, además de cuotas. Matriz API por rol y recurso: viewer solo lee; no crea, actualiza, elimina ni elude restricciones a través de rutas individuales. Validar también la propiedad del recurso en cada caso de uso.

Estado: en_curso; implementación: en_revision; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Contención A1 integrada localmente; ver CAMBIOS.md para comportamiento y límites por criterio.

Commits: 166038f88b211c52f0d149ce550880795361707c

Pruebas: A1:207passed/0failed/0skipped en candidatoWindows3.12.13; huella estable328archivos.

Evidencia: evidence/backend-auth-review.md; evidence/security-controls.md; evidence/A1-containment.xml; evidence/A1-containment-source.json

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## B08

Fuente: [B08 P1 Los accesos emitidos sobreviven a logout desactivación y cambios de rol](../../audit/2026-10-18/backend/INFORME_BACKEND.md).

Problema: `web/auth.py:420` verifica firma, tipo y expiración sin revisar estado del usuario o versión de sesión. Logout revoca refresh, pero el access sigue válido. `config/settings.py:63` permite siete días de access con remember_me; Google activa remember_me siempre. Reproducción: el access del owner sigue válido tras desactivar su fila y revocar refresh. Miembros expulsados pueden conservar permisos del token anterior hasta la expiración.

Criterio original: access breve también al recordar sesión, refresh rotativo revocable y una versión de sesión/estado del usuario consultada con caché de invalidación controlada. La prueba API de usuario borrado/desactivado o rol reducido debe fallar dentro de un SLA definido. No basta con vaciar localStorage del navegador que ejecutó logout.

Estado: en_curso; implementación: en_revision; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Contención A1 integrada localmente; ver CAMBIOS.md para comportamiento y límites por criterio.

Commits: 166038f88b211c52f0d149ce550880795361707c

Pruebas: A1:207passed/0failed/0skipped en candidatoWindows3.12.13; huella estable328archivos.

Evidencia: evidence/backend-auth-review.md; evidence/security-controls.md; evidence/A1-containment.xml; evidence/A1-containment-source.json

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## B09

Fuente: [B09 P1 Perfil individual sin límites de validación y notas fuera del generador](../../audit/2026-10-18/backend/INFORME_BACKEND.md).

Problema: `web/routes/usuario.py:34` acepta números sin rangos; update_perfil solo valida algunas enumeraciones. Reproducción: edad -5, peso -80, estatura 0 y grasa 150 persisten con HTTP 200. El flujo gym sí usa límites Pydantic en api/schemas.py. La reconstrucción del cliente en `web/routes/planes.py:96` omite notas, aunque la UI invita a registrar condiciones especiales; los detalles de esa promesa se describen en el informe UX.

Criterio original: los dos portales comparten validadores de dominio con rangos coherentes y rechazo de NaN/infinito. Reglas de restricciones, alergias e información clínica deben tener un contrato estructurado y verificable; la UI no debe prometer que un texto libre modifica el plan si el motor no lo consume. Validación profesional de seguridad nutricional antes de promocionar usos clínicos.

Estado: en_curso; implementación: en_revision; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Contención A1 integrada localmente; ver CAMBIOS.md para comportamiento y límites por criterio.

Commits: 166038f88b211c52f0d149ce550880795361707c

Pruebas: A1:207passed/0failed/0skipped en candidatoWindows3.12.13; huella estable328archivos.

Evidencia: evidence/security-review.md; evidence/pytest-nutrition-independent.xml; evidence/coverage-nutrition-focused.json; evidence/A1-containment.xml; evidence/A1-containment-source.json

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## B10

Fuente: [B10](../../audit/2026-10-18/backend/INFORME_BACKEND.md).

Problema: `scripts/backup_daily.py:44` respalda únicamente archivos SQLite; no PostgreSQL. Si todos faltan, el script sale exitosamente. No incluye PDFs/logos.

Criterio original: Respaldo PostgreSQL y objetos, retención cifrada, fallos alertados; restauración en entorno aislado medida contra RPO/RTO acordados. Verificar backups Railway existentes antes de concluir ausencia de respaldos del proveedor.

Estado: en_revision; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Restore real del esquema Alembic22tablas, relaciones/secuencias/revisión/PDF/logo; cifrado+MAC. Tiempos técnicos no equivalen a RPO/RTO ni backup nativo.

Commits: e8a6806

Pruebas: pendiente

Evidencia: evidence/postgres-restore-release-schema-independent.json; evidence/pytest-r03-restorable-independent.xml

Documentación: BACKUP_RESTORE.md; evidence/coordinator-r03-review.md

Revisión: QA independiente y revisión seguridad/coordinador.

Bloqueo: no registrado

Observaciones: sin observaciones

## B11

Fuente: [B11](../../audit/2026-10-18/backend/INFORME_BACKEND.md).

Problema: PDFs en CARPETA_PLANES y logos en web/static/uploads. Sin almacenamiento duradero de aplicación confirmado por revisión Railway del equipo. Las rutas de descarga exigen archivos en disco.

Criterio original: Objetos privados durables con autorización por tenant y descarga firmada o streaming; prueba de descarga del mismo PDF tras redeploy y desde cualquier worker/replica. Logo y plan sobreviven al despliegue.

Estado: pendiente; implementación: pendiente; validación: pendiente; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: pendiente

Commits: pendiente

Pruebas: pendiente

Evidencia: pendiente

Documentación: pendiente

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## B12

Fuente: [B12](../../audit/2026-10-18/backend/INFORME_BACKEND.md).

Problema: `web/rate_limiter_redis.py:74` permite toda solicitud ante fallo Redis. Logs de producción inspeccionados por el equipo contienen este fallback. Dependency de login usa otro limitador en memoria.

Criterio original: Fallback local acotado y alertas de degradación; protección por cuenta/IP distribuida en login, refresh e invitación; pruebas con Redis caído y cuatro workers. No cerrar toda la aplicación por una falla de caché.

Estado: en_revision; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Redis: Lua atómico, TTL estable, acciones sensibles503, lecturas fallback acotadas; dependencia5/900 compartida y HMAC de cuenta. Revisión independiente pendiente.; Contención aceptada localmente:52QA y69revisión backend; falta Redis real, ingress y alertas de servicios.

Commits: 0a0b6d4

Pruebas: pendiente

Evidencia: evidence/redis-dependency-before.log; evidence/redis-final-author.xml; evidence/pytest-redis-final-independent.xml; evidence/redis-final-independent-source.json; evidence/backend-policy-review.md

Documentación: REDIS.md

Revisión: QA y backend independientes del autor root.

Bloqueo: no registrado

Observaciones: 21 pruebas autor aprobadas. Redis real y alertas externas pendientes; no equivale a cierre completo R17.

## B13

Fuente: [B13](../../audit/2026-10-18/backend/INFORME_BACKEND.md).

Problema: `web/routes/billing.py:484,533` responde HTTP 200 a fallos MercadoPago, perdiendo el mecanismo de reintento. Firma usa data.id de query pero procesa id de body sin exigir igualdad; no valida antigüedad. MP no estaba configurado en producción en esta revisión.

Criterio original: Autenticar y vincular el evento completo, validar replay, conservar inbox duradero; responder reintentable ante fallo temporal; reconciliación periódica.

Estado: en_curso; implementación: en_revision; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Contención A1 integrada localmente; ver CAMBIOS.md para comportamiento y límites por criterio.

Commits: 166038f88b211c52f0d149ce550880795361707c

Pruebas: A1:207passed/0failed/0skipped en candidatoWindows3.12.13; huella estable328archivos.

Evidencia: evidence/backend-before.log; evidence/backend-money-contract.md; evidence/security-money-source.json; evidence/A1-containment.xml; evidence/A1-containment-source.json

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## B14

Fuente: [B14](../../audit/2026-10-18/backend/INFORME_BACKEND.md).

Problema: `subscription_service.py:77` usa cadena vacía como stripe_subscription_id para pagos MP, sobre columna unique. Reproducido: el segundo destinatario MP falla IntegrityError.

Criterio original: IDs ausentes como NULL, claves del proveedor separadas y constraint único apropiado; dos compras MP independientes completan sin colisión.

Estado: en_curso; implementación: en_revision; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Contención A1 integrada localmente; ver CAMBIOS.md para comportamiento y límites por criterio.

Commits: 166038f88b211c52f0d149ce550880795361707c

Pruebas: A1:207passed/0failed/0skipped en candidatoWindows3.12.13; huella estable328archivos.

Evidencia: evidence/backend-before.log; evidence/backend-money-contract.md; evidence/security-money-source.json; evidence/A1-containment.xml; evidence/A1-containment-source.json

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## B15

Fuente: [B15](../../audit/2026-10-18/backend/INFORME_BACKEND.md).

Problema: Stripe gestiona Subscription, mientras rutas individuales mantienen UserSubscription. Cancelación/pago fallido en `stripe_service.py:576,621` no actualizan UserSubscription. checkout.completed activa sin comprobar payment_status ni diferidos.

Criterio original: Estado canónico de derechos por sujeto; eventos duplicados, fuera de orden, retrasados y pagos diferidos convergen al estado actual del proveedor; no acceso de pago después de cancelación/impago fuera de la política.

Estado: en_curso; implementación: en_revision; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Contención A1 integrada localmente; ver CAMBIOS.md para comportamiento y límites por criterio.

Commits: 166038f88b211c52f0d149ce550880795361707c

Pruebas: A1:207passed/0failed/0skipped en candidatoWindows3.12.13; huella estable328archivos.

Evidencia: evidence/backend-before.log; evidence/backend-money-contract.md; evidence/security-money-source.json; evidence/A1-containment.xml; evidence/A1-containment-source.json

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## B16

Fuente: [B16](../../audit/2026-10-18/backend/INFORME_BACKEND.md).

Problema: `stripe_service.py:208` crea Customer antes de la llamada idempotente Subscription.create; un fallo/reintento puede dejar objetos huérfanos. ID de suscripción se deriva de gym/plan/payment_method y no de intención de compra persistida.

Criterio original: Persistir intención y claves idempotentes por operación; reintentar sin duplicar Customer/cobro, conservar estados recuperables y reconciliar fallos DB posteriores al proveedor.

Estado: en_revision; implementación: en_revision; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Contención A1 integrada localmente; ver CAMBIOS.md para comportamiento y límites por criterio.; Reserva B2B atomica antesCPU: cliente activo/cupo10, diario10gym/1cliente, mensual20Free; calendario local, hash idempotente y publicacion persistida sin reembolso tras crash/FKNULL.

Commits: 166038f88b211c52f0d149ce550880795361707c, b81cfc1, e3039c2

Pruebas: A1:207passed/0failed/0skipped en candidatoWindows3.12.13; huella estable328archivos.; 18 PG independientes +41 worker/nutricion(5PDF reales),6 migraciones y restore24;25 seguimiento compensacion/logs/PDF/caducidad. Serial/n2 finales1621 cadauno,1skip Windows.

Evidencia: evidence/backend-before.log; evidence/backend-money-contract.md; evidence/security-money-source.json; evidence/A1-containment.xml; evidence/A1-containment-source.json; evidence/gym-quota-independent-source.json; evidence/pytest-gym-quota-independent.xml; evidence/error-compensation-final-independent-source.json

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md; B2B_CUOTAS.md

Revisión: QA y seguridad independientes; coordinador integra, alcance local sin sandbox ni despliegue

Bloqueo: no registrado

Observaciones: sin observaciones

## B17

Fuente: [B17](../../audit/2026-10-18/backend/INFORME_BACKEND.md).

Problema: `web/routes/planes.py:53` usa locks por proceso y generación con to_thread; cuotas se consultan antes del lock. Cuatro workers no comparten locks ni límites transaccionales.

Criterio original: Reserva atómica de cuota, idempotencia por solicitud, jobs con estado/reintentos y límites CPU; prueba concurrente de último crédito y mismo cliente entre workers.

Estado: en_revision; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Carrera GET/proyección vs reserva corregida e integrada;3casos PG con tres procesos. B2B diario/mes, sandbox y R04 posteriores siguen abiertos.; Reserva B2B atomica antesCPU: cliente activo/cupo10, diario10gym/1cliente, mensual20Free; calendario local, hash idempotente y publicacion persistida sin reembolso tras crash/FKNULL.

Commits: c769667, b81cfc1, e3039c2

Pruebas: 18 PG independientes +41 worker/nutricion(5PDF reales),6 migraciones y restore24;25 seguimiento compensacion/logs/PDF/caducidad. Serial/n2 finales1621 cadauno,1skip Windows.

Evidencia: evidence/pytest-quota-postgres-before.xml; evidence/pytest-quota-postgres-after.xml; evidence/quota-a1-snapshot.json; evidence/gym-quota-independent-source.json; evidence/pytest-gym-quota-independent.xml; evidence/error-compensation-final-independent-source.json

Documentación: CATALOGO.md; B2B_CUOTAS.md

Revisión: QA y seguridad independientes; coordinador integra, alcance local sin sandbox ni despliegue

Bloqueo: no registrado

Observaciones: Cuota individual: carrera GET/reserva corregida y revisada en PostgreSQL con 3 procesos (3 casos aprobados). Reserva B2B y compra sandbox real siguen abiertas.

## B18

Fuente: [B18](../../audit/2026-10-18/backend/INFORME_BACKEND.md).

Problema: `repository.py:520` crea defaults de membresías al leer si la lista está vacía, sin uniqueness de plantilla. QA UX observó diez planes tras lecturas concurrentes.

Criterio original: Crear defaults en onboarding transaccional con unique(gym_id,template_key) y upsert; lecturas paralelas nunca duplican.

Estado: en_revision; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Preparación local sin DDL en fábricas;31 casos autor y15 independientes, vacío/legado/drift/restore22tablas. Staging, privilegios y R04 siguen abiertos.

Commits: e8a6806

Pruebas: pendiente

Evidencia: evidence/backend-r03-paths-restorable.xml; evidence/pytest-r03-restorable-independent.xml; evidence/r03-restorable-independent-source.json

Documentación: evidence/backend-r03-design.md; evidence/coordinator-r03-review.md

Revisión: Coordinador y QA independientes del autor backend; alcance local R03/R08, no aceptación productiva.

Bloqueo: no registrado

Observaciones: sin observaciones

## B19

Fuente: [B19](../../audit/2026-10-18/backend/INFORME_BACKEND.md).

Problema: Registro exige doce caracteres (`auth.py:202`) e invitación seis (`team.py:585`); invitaciones DateTime sin timezone se comparan con UTC aware (`:578,658`). Faltan rutas de recuperar contraseña, verificación de email, cambiar credenciales y MFA utilizable.

Criterio original: Política común, bloqueo de contraseñas comprometidas, flujos de recuperación/verificación seguros; MFA/passkeys al menos para owners; invitación probada en PostgreSQL y SQLite con tiempo UTC coherente.

Estado: en_curso; implementación: en_revision; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Contención A1 integrada localmente; ver CAMBIOS.md para comportamiento y límites por criterio.

Commits: 166038f88b211c52f0d149ce550880795361707c

Pruebas: A1:207passed/0failed/0skipped en candidatoWindows3.12.13; huella estable328archivos.

Evidencia: evidence/backend-auth-review.md; evidence/security-controls.md; evidence/A1-containment.xml; evidence/A1-containment-source.json

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## B20

Fuente: [B20](../../audit/2026-10-18/backend/INFORME_BACKEND.md).

Problema: `auth.py` usa formato HMAC propio sin versión de clave, issuer/audience o inventario de sesiones; `routes/auth.py:378` expone mantenimiento de tipo mediante el mismo secreto de firma. Tokens refresh/access están en localStorage.

Criterio original: Preferir sesiones o biblioteca de tokens revisada; rotación de claves y audiencias verificadas; eliminar endpoint de emergencia del runtime público o convertirlo en operación administrativa con identidad/MFA y auditoría. Reducir exposición de tokens y verificar XSS en todos los sinks. No se confirmó un exploit XSS en esta revisión.

Estado: en_curso; implementación: en_revision; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Contención A1 integrada localmente; ver CAMBIOS.md para comportamiento y límites por criterio.

Commits: 166038f88b211c52f0d149ce550880795361707c, dbb6af5

Pruebas: A1:207passed/0failed/0skipped en candidatoWindows3.12.13; huella estable328archivos.

Evidencia: evidence/backend-auth-review.md; evidence/security-controls.md; evidence/A1-containment.xml; evidence/A1-containment-source.json; evidence/security-error-privacy-source.json; evidence/security-error-privacy-after.xml

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md; evidence/security-error-privacy.md

Revisión: pendiente

Bloqueo: no registrado

Observaciones: Contencion concreta de handlers/tracker automaticos y compensacion verificada con13regresiones. No declara saneados login, email, auth_audit, Sentry o alertas directas; R31 inventaria esos pendientes.

## B21

Fuente: [B21](../../audit/2026-10-18/backend/INFORME_BACKEND.md).

Problema: Docker instala requirements_web.txt con rangos flotantes; lock difiere de txt (adaptador PostgreSQL distinto; faltan paquetes web). SCA del lock: 68 registros, 37 advisories distintos en siete paquetes.

Criterio original: Lock actualizado compatible Linux/Python3.12 con hashes, build que lo usa, SBOM y scan de imagen final y dependencias; tratar exposición por alcance real. No atribuir resultados del lock a paquetes de producción sin inventario instalado.

Estado: en_curso; implementación: en_revision; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: pendiente

Commits: pendiente

Pruebas: pendiente

Evidencia: evidence/sbom-linux-runtime.json; evidence/sca-linux-runtime-final.log

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## B22

Fuente: [B22](../../audit/2026-10-18/backend/INFORME_BACKEND.md).

Problema: ClienteUpdate difiere de Create; PerfilUpdate duplica reglas; manejo de excepciones en clientes y planes devuelve str(exc). `has_permission` otorga a owner permisos no definidos.

Criterio original: DTOs comunes, errores de dominio con código público estable/request_id, detalles internos solo en logs saneados; denegar acciones no registradas a todos los roles.

Estado: en_curso; implementación: en_revision; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Contención A1 integrada localmente; ver CAMBIOS.md para comportamiento y límites por criterio.

Commits: 166038f88b211c52f0d149ce550880795361707c, dbb6af5

Pruebas: A1:207passed/0failed/0skipped en candidatoWindows3.12.13; huella estable328archivos.

Evidencia: evidence/backend-auth-review.md; evidence/security-controls.md; evidence/security-review.md; evidence/pytest-nutrition-independent.xml; evidence/coverage-nutrition-focused.json; ESTADO.md; TRAZABILIDAD.json; evidence/A1-containment.xml; evidence/A1-containment-source.json; evidence/security-error-privacy-source.json; evidence/security-error-privacy-after.xml

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md; evidence/security-error-privacy.md

Revisión: pendiente

Bloqueo: no registrado

Observaciones: Contencion concreta de handlers/tracker automaticos y compensacion verificada con13regresiones. No declara saneados login, email, auth_audit, Sentry o alertas directas; R31 inventaria esos pendientes.

## B23

Fuente: [B23 P1 El filtrado conserva una categoría totalmente excluida y modifica catálogos compartidos](../../audit/2026-10-18/backend/INFORME_BACKEND.md).

Problema: `web/routes/planes.py:166` calcula la lista filtrada, pero `:168` solo reemplaza los elementos cuando esa lista no está vacía. Al excluir todos los alimentos de una categoría, conserva íntegra la lista original. La prueba aislada ejecuta ese mismo nodo del AST: ambos elementos sintéticos excluidos permanecen disponibles. Esta evidencia confirma el fallo del filtrado; no demuestra qué alimento devolverá un plan final ni un efecto clínico.

Existe además un riesgo de concurrencia inferido del código: `:152` solo toma `_categorias_lock` para solicitudes con exclusiones, mientras `:179` modifica referencias globales CATEGORIAS de varios módulos. Una generación sin exclusiones no espera ese lock y puede leer el catálogo temporal de otra solicitud; `core/generador_opciones.py:235` consulta esas referencias durante la selección. No se ejecutó una reproducción concurrente completa ni se probó contra producción.

Criterio original: pasar un catálogo inmutable por solicitud/caso de uso a todos los selectores, sin modificar globals. Si las exclusiones dejan sin alternativas una categoría requerida, devolver un error de dominio claro o una sustitución explícitamente validada; nunca restaurar silenciosamente alimentos excluidos. Pruebas de exclusión total, parcial y generación simultánea con restricciones distintas deben verificar resultados independientes y ausencia de alimentos prohibidos. Vincular este criterio al trabajo de garantías del motor R33 del roadmap principal.

Estado: en_curso; implementación: en_revision; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Contención A1 integrada localmente; ver CAMBIOS.md para comportamiento y límites por criterio.

Commits: 166038f88b211c52f0d149ce550880795361707c

Pruebas: A1:207passed/0failed/0skipped en candidatoWindows3.12.13; huella estable328archivos.

Evidencia: evidence/security-review.md; evidence/pytest-nutrition-independent.xml; evidence/coverage-nutrition-focused.json; evidence/A1-containment.xml; evidence/A1-containment-source.json

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## OPS01

Fuente: [OPS01 Migraciones ausentes del despliegue efectivo](../../audit/2026-10-18/OPERACION_Y_SEGURIDAD.md).

Problema: **Prioridad P0. Confirmado en configuración, despliegue y catálogo.** `railway.toml:10` declara `releaseCommand`. La documentación y el esquema actuales de Railway utilizan `preDeployCommand`. El manifiesto efectivo no contiene un comando previo al despliegue. Además, `entrypoint.sh:13` omite Alembic cuando existe `RAILWAY_ENVIRONMENT`.

El catálogo de producción sin `alembic_version` demuestra que no se está gestionando allí el esquema mediante el seguimiento esperado de Alembic. No se debe deducir que toda migración del repositorio puede ejecutarse sobre esa base sin preparación: parte del esquema ya existe.

**Acción:** inventariar tablas, columnas, índices y restricciones; reconciliar el esquema existente en una copia de staging; establecer una revisión inicial verificada; corregir el hook y ejecutar futuras migraciones antes del arranque. Ante fallo, detener el despliegue. No usar `stamp head` para ocultar diferencias. El bootstrap de base nueva también necesita revisión: `create_all` seguido de `stamp` puede omitir políticas y otras operaciones que sólo viven en migraciones.

Criterio original: base vacía y copia del esquema actual alcanzan la misma revisión y restricciones mediante un procedimiento reproducible; Alembic reporta un único head; el despliegue fallido por migración no recibe tráfico. Fuente: [configuración de Railway](https://docs.railway.com/config-as-code/reference) y [comando previo al despliegue](https://docs.railway.com/deployments/pre-deploy-command).

Estado: en_revision; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Preparación local sin DDL en fábricas;31 casos autor y15 independientes, vacío/legado/drift/restore22tablas. Staging, privilegios y R04 siguen abiertos.

Commits: e8a6806

Pruebas: pendiente

Evidencia: evidence/backend-r03-paths-restorable.xml; evidence/pytest-r03-restorable-independent.xml; evidence/r03-restorable-independent-source.json

Documentación: evidence/backend-r03-design.md; evidence/coordinator-r03-review.md

Revisión: Coordinador y QA independientes del autor backend; alcance local R03/R08, no aceptación productiva.

Bloqueo: no registrado

Observaciones: sin observaciones

## OPS02

Fuente: [OPS02 Aislamiento de datos sin defensa en PostgreSQL](../../audit/2026-10-18/OPERACION_Y_SEGURIDAD.md).

Problema: **Prioridad P0. Configuración real confirmada.** No hay políticas RLS y la aplicación usa un rol con privilegios que las eludiría. Esto no prueba una filtración existente: implica que cualquier filtro de tenant omitido en la aplicación puede alcanzar otros gimnasios sin una segunda barrera en la base.

**Acción:** separar rol migrador y rol de aplicación `NOSUPERUSER NOBYPASSRLS`; definir el alcance de usuario individual y miembro de equipo; hacer que todas las sesiones establezcan contexto de tenant por transacción, incluidos trabajos y generación en segundo plano. Corregir primero las sesiones que no reciben contexto; luego activar y probar RLS gradualmente. Encender RLS directamente puede romper rutas legítimas.

Criterio original: pruebas reales de PostgreSQL con dos gimnasios y un rol restringido verifican lectura, alta, actualización, borrado, exportación, tareas y reutilización de conexiones; un contexto ausente o incorrecto falla cerrado. Deben cubrirse tablas de clientes, planes, suscripciones, pagos y las nuevas tablas que contengan pertenencia a un gimnasio.

Estado: pendiente; implementación: pendiente; validación: pendiente; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: pendiente

Commits: pendiente

Pruebas: pendiente

Evidencia: pendiente

Documentación: pendiente

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## OPS03

Fuente: [OPS03 Archivos de clientes y branding en almacenamiento efímero](../../audit/2026-10-18/OPERACION_Y_SEGURIDAD.md).

Problema: **Prioridad P1. Ruta y topología confirmadas.** `web/routes/gym_profile.py:30` guarda logos bajo `/app/web/static/uploads/logos`; `web/routes/planes.py:149` y siguientes escriben planes en directorios locales. El contenedor define `/data`, pero el servicio web no tiene volumen montado. Crear ese directorio en Docker no lo vuelve persistente.

**Acción:** mover logos y documentos a un puerto de almacenamiento con un adaptador de object storage, metadatos en PostgreSQL y descargas autorizadas o URLs de duración limitada. Un volumen puede servir como transición para una sola réplica, con inventario y respaldo explícitos; no resuelve por sí solo despliegues distribuidos.

Criterio original: un logo y un plan de prueba sobreviven a reemplazar el contenedor; usuario y gimnasio ajenos no pueden descargarlos; existe política de retención y borrado. El alcance exacto de los PDFs recuperables desde datos JSON debe verificarse antes de migrar archivos históricos.

Estado: pendiente; implementación: pendiente; validación: pendiente; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: pendiente

Commits: pendiente

Pruebas: pendiente

Evidencia: pendiente

Documentación: pendiente

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## OPS04

Fuente: [OPS04 El script de backup no protege PostgreSQL](../../audit/2026-10-18/OPERACION_Y_SEGURIDAD.md).

Problema: **Prioridad P1. Confirmado en código; política nativa del proveedor pendiente de inspección específica.** `scripts/backup_daily.py:46` enumera archivos SQLite, y su salida puede ser exitosa si todos se omiten. No implementa dump de PostgreSQL ni respaldo de objetos. No se encontró un servicio o cron de backup en la topología consultada. Esto no demuestra que Railway no tenga snapshots configurados por otros mecanismos.

**Acción:** verificar backups nativos, documentar retención y restauración; añadir respaldo independiente cifrado según riesgo, monitorizar edad y resultado y ensayar la restauración en un entorno aislado. El script debe fallar si no respaldó ninguna fuente esperada.

Criterio original: RPO de 24 horas y RTO de 4 horas como objetivos iniciales a validar con el negocio; ensayo fechado que restaure esquema, usuarios, relaciones y referencias a objetos. Estos tiempos son metas propuestas, no capacidades actuales.

Estado: en_revision; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Contención A1 integrada localmente; ver CAMBIOS.md para comportamiento y límites por criterio.; Restore real del esquema Alembic22tablas, relaciones/secuencias/revisión/PDF/logo; cifrado+MAC. Tiempos técnicos no equivalen a RPO/RTO ni backup nativo.

Commits: 166038f88b211c52f0d149ce550880795361707c, e8a6806

Pruebas: A1:207passed/0failed/0skipped en candidatoWindows3.12.13; huella estable328archivos.

Evidencia: BACKUP_RESTORE.md; evidence/security-review.md; evidence/postgres-restore-independent.json; evidence/A1-containment.xml; evidence/A1-containment-source.json; evidence/postgres-restore-release-schema-independent.json; evidence/pytest-r03-restorable-independent.xml

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md; BACKUP_RESTORE.md; evidence/coordinator-r03-review.md

Revisión: QA independiente y revisión seguridad/coordinador.

Bloqueo: no registrado

Observaciones: sin observaciones

## OPS05

Fuente: [OPS05 Protección Redis degrada permitiendo solicitudes](../../audit/2026-10-18/OPERACION_Y_SEGURIDAD.md).

Problema: **Prioridad P1. Comportamiento de código e incidente histórico observados.** `web/rate_limiter_redis.py:74` deja pasar solicitudes cuando Redis falla. Una consulta de hasta 80 líneas filtradas devolvió 39 registros, de los cuales 30 contenían `Redis rate limiter unavailable, allowing request`; el último de esos registros era del 15 de octubre. Una muestra posterior de la última hora devolvió 17 líneas, sin ese mensaje. No se afirma una caída permanente de Redis ni se intentó provocar un ataque de fuerza bruta.

**Acción:** alarma y métrica de degradación; política distinta para login, refresh y generación costosa; fallback limitado o rechazo temporal en rutas sensibles. La expiración Redis se reinicia en cada petición (`:42`), por lo que también debe definirse y probarse la semántica de la ventana.

Criterio original: pérdida de Redis simulada en staging no deja autenticación o generación sin límites; recuperación comprobada; alerta verificable y sin secretos.

Estado: en_revision; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Redis: Lua atómico, TTL estable, acciones sensibles503, lecturas fallback acotadas; dependencia5/900 compartida y HMAC de cuenta. Revisión independiente pendiente.; Contención aceptada localmente:52QA y69revisión backend; falta Redis real, ingress y alertas de servicios.

Commits: 0a0b6d4

Pruebas: pendiente

Evidencia: evidence/redis-dependency-before.log; evidence/redis-final-author.xml; evidence/pytest-redis-final-independent.xml; evidence/redis-final-independent-source.json; evidence/backend-policy-review.md

Documentación: REDIS.md

Revisión: QA y backend independientes del autor root.

Bloqueo: no registrado

Observaciones: 21 pruebas autor aprobadas. Redis real y alertas externas pendientes; no equivale a cierre completo R17.

## OPS06

Fuente: [OPS06 Correo transaccional deshabilitado](../../audit/2026-10-18/OPERACION_Y_SEGURIDAD.md).

Problema: **Prioridad P1 para activación y recuperación.** Sin `RESEND_API_KEY`, `web/services/email_service.py:43` omite envíos. Las rutas de bienvenida e invitación pueden existir sin que el usuario reciba un correo. Tampoco se encontró un recorrido completo de recuperación de contraseña en las rutas revisadas.

**Acción:** configurar remitente y dominio verificado en el proveedor seleccionado, observar entregas/rebotes y añadir recuperación segura con token de un uso y caducidad. Ocultar o corregir promesas que todavía no tengan recorrido funcional.

Criterio original: usuario de prueba recibe y completa invitación y recuperación; los tokens expiran y no se reutilizan; respuestas no facilitan enumeración; correos no se envían desde pruebas automatizadas ordinarias.

Estado: pendiente; implementación: pendiente; validación: pendiente; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: pendiente

Commits: pendiente

Pruebas: pendiente

Evidencia: pendiente

Documentación: pendiente

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## OPS07

Fuente: [OPS07 Despliegues difíciles de reproducir y sin staging](../../audit/2026-10-18/OPERACION_Y_SEGURIDAD.md).

Problema: **Prioridad P1.** Docker instala `requirements_web.txt` con rangos abiertos; el lock histórico no es su fuente de instalación y tiene diferencias. Sólo se observó el entorno `production`. No se construyó ni desplegó una imagen durante esta auditoría.

**Acción:** resolver y fijar dependencias para Linux/Python de producción, ejecutar SCA sobre esa resolución y sobre la imagen, generar SBOM, publicar la imagen por digest y promover el mismo artefacto de staging a producción. Separar dependencias desktop, web, pruebas y herramientas de agentes.

Criterio original: un commit produce un artefacto identificable; pruebas y escaneo bloquean vulnerabilidades aplicables por encima del umbral acordado; rollback ensayado sin modificar destructivamente el esquema.

Estado: en_revision; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: 14fuentes seguimiento congeladas, aislamiento/CI bloqueante preparada, contratos obsoletos sustituidos por comportamiento; Redis real/R04/imagen/CI remota pendientes.

Commits: e8e0c44

Pruebas: pendiente

Evidencia: evidence/r05-followup-frozen-source.json; evidence/pytest-r05-frozen-candidate.xml

Documentación: QA_R05.md

Revisión: pendiente

Bloqueo: {"falta": "Host Linux/Docker operativo para construir y escanear imagen/digest exacto.", "obtener": "Habilitar virtualización del host mediante decisión del usuario o usar runner Linux autorizado existente.", "responsable": "Usuario/operación", "puede_continuar": "Locks conhash, instalación Windows, SCA resolución, SBOM y CI preparada; no atribuirlos a imagen ejecutada."}

Observaciones: sin observaciones

## QA-01

Fuente: [QA-01 — Alta: el CI no instala dependencias necesarias para recolectar y ejecutar la suite web](../../audit/2026-10-18/qa/INFORME_QA.md).

Problema: **Referencia:** `.github/workflows/ci.yml:95`, `:96`, `:142`; `requirements.txt:1`.

CI instala el manifest desktop más pytest, pytest-cov y pytest-xdist. Resolución seca con `uv pip compile requirements.txt --python-version 3.12` confirma ausentes `httpx`, `sqlalchemy`, `alembic`, `jinja2`, `python-multipart`, SDK de pagos, `pypdf` y `pytest-asyncio`; ver `ci-manifest-check.json`. FastAPI y bcrypt sí llegan transitivamente, por lo que no se reportan como ausentes. Los tests importan directamente bibliotecas ausentes durante colección/ejecución. No se consultó la última ejecución remota de GitHub Actions.

Criterio original: separar dependencias web, desktop y pruebas; job SaaS instala el mismo runtime bloqueado que Docker más dependencias de tests; runner limpio Python 3.11/3.12 recolecta toda la suite sin módulos faltantes; build valida la imagen real.

Estado: en_revision; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Contención A1 integrada localmente; ver CAMBIOS.md para comportamiento y límites por criterio.; 14fuentes seguimiento congeladas, aislamiento/CI bloqueante preparada, contratos obsoletos sustituidos por comportamiento; Redis real/R04/imagen/CI remota pendientes.

Commits: 166038f88b211c52f0d149ce550880795361707c, e8e0c44, e3039c2

Pruebas: A1:207passed/0failed/0skipped en candidatoWindows3.12.13; huella estable328archivos.; 1621pass/1skip serial182.54s y n2shuffle111.34s seed20261018;387Python/deps+55frontend estables e identicas. Unico skip symlinkWindows; no Linux/imagen/Redisreal.

Evidencia: QA_R05.md; evidence/pytest-r05-frozen-candidate.xml; evidence/qa-r05-frozen-hashes.json; evidence/A1-containment.xml; evidence/A1-containment-source.json; evidence/r05-followup-frozen-source.json; evidence/web-candidate-containment-final-source.json; evidence/pytest-web-candidate-containment-final.xml; evidence/web-candidate-containment-shuffle-source.json; evidence/pytest-web-candidate-containment-shuffle.xml; evidence/qa-b2b-privacy-utc-final-source.json

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md; QA_R05.md

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## QA-02

Fuente: [QA-02 — Alta: fixtures no aíslan ni preparan la BD de pruebas](../../audit/2026-10-18/qa/INFORME_QA.md).

Problema: **Referencia:** `conftest.py:18`, `:40`, `:41`, `:64`, `:65`; `web/database/engine.py:27`.

No se impone DATABASE_URL de pruebas ni schema/rollback/cleanup por caso. La fixture usa el engine por configuración, intenta insertar usuario y silencia cualquier excepción; después emite un token aunque el usuario no exista. En BD local vacía se reprodujeron respuestas 500 por `no such table: clientes` y fallos de login. Si el operador hereda variables reales, las fixtures pueden escribir usuarios sintéticos en esa BD. Esta auditoría evitó ese riesgo con harness offline y BD efímera.

Criterio original: rechazar URL no autorizada antes de conectar; BD PostgreSQL de tests y namespace por worker; migrar una vez y rollback/limpieza garantizados; cualquier fallo al crear fixture aborta explícitamente; ejecutar suite nunca cambia BD de desarrollo o producción.

Estado: en_revision; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Contención A1 integrada localmente; ver CAMBIOS.md para comportamiento y límites por criterio.; 14fuentes seguimiento congeladas, aislamiento/CI bloqueante preparada, contratos obsoletos sustituidos por comportamiento; Redis real/R04/imagen/CI remota pendientes.

Commits: 166038f88b211c52f0d149ce550880795361707c, e8e0c44, e3039c2

Pruebas: A1:207passed/0failed/0skipped en candidatoWindows3.12.13; huella estable328archivos.; 1621pass/1skip serial182.54s y n2shuffle111.34s seed20261018;387Python/deps+55frontend estables e identicas. Unico skip symlinkWindows; no Linux/imagen/Redisreal.

Evidencia: QA_R05.md; evidence/pytest-r05-frozen-candidate.xml; evidence/qa-r05-frozen-hashes.json; evidence/A1-containment.xml; evidence/A1-containment-source.json; evidence/r05-followup-frozen-source.json; evidence/web-candidate-containment-final-source.json; evidence/pytest-web-candidate-containment-final.xml; evidence/web-candidate-containment-shuffle-source.json; evidence/pytest-web-candidate-containment-shuffle.xml; evidence/qa-b2b-privacy-utc-final-source.json

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md; QA_R05.md

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## QA-03

Fuente: [QA-03 — Alta: las migraciones pueden aparentar éxito sin cambios aplicados](../../audit/2026-10-18/qa/INFORME_QA.md).

Problema: **Referencia:** `db_bootstrap.py:56`, `:80`, `:114`, `:117`; `entrypoint.sh:17`.

Bootstrap crea tablas ORM, y en ausencia de alembic_version ejecuta stamp(head). Eso omite operaciones que no forman parte de metadata, como políticas RLS de `c4f8e9d2a3b1_enable_rls_policies_multi_tenant.py:41`. Además captura fallos de upgrade como no fatales. Probe SQLite local con fallo de upgrade inyectado confirma retorno normal y versión `20260402_plan_json`. La omisión de RLS es deducción del flujo; no se verificó pg_policies de Railway.

Criterio original: migración desde vacío y actualización desde snapshots previos reales en PostgreSQL; fallo de DDL devuelve código no cero e impide release; comprobar schema, índices, constraints y políticas, además de número de versión. Probar restauración y rollback con datos sintéticos.

Estado: en_revision; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Preparación local sin DDL en fábricas;31 casos autor y15 independientes, vacío/legado/drift/restore22tablas. Staging, privilegios y R04 siguen abiertos.

Commits: e8a6806

Pruebas: pendiente

Evidencia: evidence/backend-r03-paths-restorable.xml; evidence/pytest-r03-restorable-independent.xml; evidence/r03-restorable-independent-source.json

Documentación: evidence/backend-r03-design.md; evidence/coordinator-r03-review.md

Revisión: Coordinador y QA independientes del autor backend; alcance local R03/R08, no aceptación productiva.

Bloqueo: no registrado

Observaciones: sin observaciones

## QA-04

Fuente: [QA-04 — Alta: rol por defecto de migración incompatible con el ORM](../../audit/2026-10-18/qa/INFORME_QA.md).

Problema: **Referencia:** `web/database/alembic/versions/f8a1b2c3d4e5_add_all_missing_tables_production.py:44`; `web/database/models.py:82`.

La migración añade role con `server_default='viewer'`; SQLEnum(UserRole) espera los nombres `OWNER`, `ADMIN`, `NUTRIOLOGO`, `VIEWER`. Insertar localmente un usuario con el valor que produciría la migración y cargarlo por ORM reproduce LookupError. Impacta bases antiguas cuyos usuarios reciben ese default; no se afirma que existan esos registros en Railway.

Criterio original: contrato de serialización único para enums, backfill de valores antiguos y mapeo correcto de propietarios; migración de snapshot con usuarios antiguos permite login y conserva permisos sin elevar privilegios.

Estado: en_revision; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Preparación local sin DDL en fábricas;31 casos autor y15 independientes, vacío/legado/drift/restore22tablas. Staging, privilegios y R04 siguen abiertos.

Commits: e8a6806

Pruebas: pendiente

Evidencia: evidence/backend-r03-paths-restorable.xml; evidence/pytest-r03-restorable-independent.xml; evidence/r03-restorable-independent-source.json

Documentación: evidence/backend-r03-design.md; evidence/coordinator-r03-review.md

Revisión: Coordinador y QA independientes del autor backend; alcance local R03/R08, no aceptación productiva.

Bloqueo: no registrado

Observaciones: sin observaciones

## QA-05

Fuente: [QA-05 — Alta: el aislamiento entre gimnasios no está demostrado en PostgreSQL real](../../audit/2026-10-18/qa/INFORME_QA.md).

Problema: **Referencia:** `tests/test_multi_tenant_isolation.py:123`, `:127`, `:150`, `:274`, `:312`, `:316`; `.github/workflows/ci.yml:68`.

Los casos de clientes cross-tenant sustituyen autenticación y repositorio por mocks vacíos; comprueban parámetros/respuestas simuladas, sin crear dos gimnasios y sus clientes reales. Algunos tests silencian errores y sólo afirman si el mock fue llamado. Los repositorios de configuración sí tienen un caso de separación local, que no cubre las rutas de clientes/planes/RLS. CI no define un servicio PostgreSQL.

Criterio original: dos tenants, propietario/admin/nutriólogo/viewer/cliente y datos reales en PostgreSQL; intentos cruzados de listar, leer, actualizar, borrar y descargar nunca filtran datos; mismo resultado con conexiones reutilizadas y con tenant ausente; políticas comprobadas con rol de aplicación sin bypass RLS.

Estado: pendiente; implementación: pendiente; validación: pendiente; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: pendiente

Commits: pendiente

Pruebas: pendiente

Evidencia: pendiente

Documentación: pendiente

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## QA-06

Fuente: [QA-06 — Media: catálogo de planes discrepante entre web, desktop y tests](../../audit/2026-10-18/qa/INFORME_QA.md).

Problema: **Referencia:** `web/constants.py:59`, `config/constantes.py:93`, `tests/test_feature_gate.py:62`, `:277`, `:302`.

Free permite 5 clientes en web y 10 en config desktop/tests. Tres fallos persistentes lo reproducen; no debe cambiarse el test ni el límite sin fijar la decisión comercial.

Criterio original: única definición de catálogo y contrato; pricing, endpoints, dashboard y ambos clientes muestran y aplican el mismo límite; probar N−1, N, N+1 y downgrade con datos existentes.

Estado: pendiente; implementación: pendiente; validación: pendiente; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: pendiente

Commits: af177b1

Pruebas: pendiente

Evidencia: pendiente

Documentación: CATALOGO.md

Revisión: pendiente

Bloqueo: no registrado

Observaciones: Usuario aprobó Free10clientes,1planporcliente/día,10planestotalesgym/día; soporte desktop continúa. Fuente única y precios/periodo/mes separados. Integración/aceptación completa aún abierta.

## QA-07

Fuente: [QA-07 — Media: controles CI no impiden promoción con problemas de calidad/seguridad](../../audit/2026-10-18/qa/INFORME_QA.md).

Problema: **Referencia:** `.github/workflows/ci.yml:62`, `:110`, `:170`, `:176`.

Ruff y Bandit usan continue-on-error; ci-success no depende del job security; cobertura no impone umbral ni tiene config que excluya entornos versionados. No hay job visible de navegador, accesibilidad, performance ni migración PostgreSQL.

Criterio original: baseline revisado de reglas relevantes y fallos de seguridad confirmados bloqueantes; gates de cobertura de código modificado y casos críticos; E2E SaaS sobre imagen candidata; exclusión explícita de venv/build/tests en métrica de producto.

Estado: en_revision; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Contención A1 integrada localmente; ver CAMBIOS.md para comportamiento y límites por criterio.; 14fuentes seguimiento congeladas, aislamiento/CI bloqueante preparada, contratos obsoletos sustituidos por comportamiento; Redis real/R04/imagen/CI remota pendientes.

Commits: 166038f88b211c52f0d149ce550880795361707c, e8e0c44

Pruebas: A1:207passed/0failed/0skipped en candidatoWindows3.12.13; huella estable328archivos.

Evidencia: QA_R05.md; evidence/pytest-r05-frozen-candidate.xml; evidence/qa-r05-frozen-hashes.json; evidence/A1-containment.xml; evidence/A1-containment-source.json; evidence/r05-followup-frozen-source.json

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md; QA_R05.md

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## QA-08

Fuente: [QA-08 — Media: orden/paralelismo puede omitir regresiones](../../audit/2026-10-18/qa/INFORME_QA.md).

Problema: **Referencia:** `tests/test_api.py:78`, `:118`, `:134`; `.github/workflows/ci.yml:113`; `tests/test_sentry_setup.py:255`, `:278`.

Lectura y borrado dependen de pytest.created_id creado por otro test. En xdist cada proceso tiene su copia y esos tests pueden omitirse. Los dos tests Sentry asumen un event loop global: fallan después de otros tests async, pero ambos pasan solos. No se ejecutó xdist en esta auditoría; el riesgo de omisión está sustentado por el estado global y el skip explícito.

Criterio original: fixture por caso que crea/limpia recurso; ningún test depende de otro; usar asyncio.run o fixtures async; suite pasa serial, con orden aleatorio y con al menos dos workers sin omisiones por dependencia.

Estado: en_revision; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Contención A1 integrada localmente; ver CAMBIOS.md para comportamiento y límites por criterio.; 14fuentes seguimiento congeladas, aislamiento/CI bloqueante preparada, contratos obsoletos sustituidos por comportamiento; Redis real/R04/imagen/CI remota pendientes.

Commits: 166038f88b211c52f0d149ce550880795361707c, e8e0c44, e3039c2

Pruebas: A1:207passed/0failed/0skipped en candidatoWindows3.12.13; huella estable328archivos.; 1621pass/1skip serial182.54s y n2shuffle111.34s seed20261018;387Python/deps+55frontend estables e identicas. Unico skip symlinkWindows; no Linux/imagen/Redisreal.

Evidencia: QA_R05.md; evidence/pytest-r05-frozen-candidate.xml; evidence/qa-r05-frozen-hashes.json; evidence/A1-containment.xml; evidence/A1-containment-source.json; evidence/r05-followup-frozen-source.json; evidence/web-candidate-containment-final-source.json; evidence/pytest-web-candidate-containment-final.xml; evidence/web-candidate-containment-shuffle-source.json; evidence/pytest-web-candidate-containment-shuffle.xml; evidence/qa-b2b-privacy-utc-final-source.json

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md; QA_R05.md

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## QA-09

Fuente: [QA-09 — Media: faltan contratos E2E sobre la aplicación web publicada](../../audit/2026-10-18/qa/INFORME_QA.md).

Problema: **Referencia:** `tests/test_api.py:16`, `tests/test_integracion.py:21`, `tests/test_auth_audit.py:309`; porcentajes por ruta en `summary.json`.

La mayor parte de integración usa api.app.create_app, mientras Railway arranca web.main_web. Sólo un test de auditoría importa la app web real; las pruebas HTML del API están omitidas. No se halló suite Playwright/axe/Selenium en el proyecto. No se probaron en suite persistencia del portal del cliente, teclado, móvil o pagos con eventos reales de sandbox. El agente UX añadió evidencia de navegador independiente en esta auditoría.

Criterio original: flujos automatizados de propietario y cliente sobre la app/imagen que se publica: registro→onboarding→cliente→plan→PDF→portal; invitación→rol→revocación; checkout sandbox→webhook duplicado→estado; refresh/logout; accesibilidad teclado, validación visible, 390 px y desktop; estados vacíos/error/carga.

Estado: en_revision; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: B2B6recorridos, R13 17estados y5personales con27fuentes estables. TransporteAPI sintético, no sandbox/auth/RLS/lector de pantalla. Seguimiento R11 corrige fixture token y añade auth real.

Commits: c45a71c, e3039c2

Pruebas: 1621pass/1skip serial182.54s y n2shuffle111.34s seed20261018;387Python/deps+55frontend estables e identicas. Unico skip symlinkWindows; no Linux/imagen/Redisreal.

Evidencia: evidence/ux/frontend-independent-source.json; evidence/ux/frontend-independent-review.md; evidence/web-candidate-containment-final-source.json; evidence/pytest-web-candidate-containment-final.xml; evidence/web-candidate-containment-shuffle-source.json; evidence/pytest-web-candidate-containment-shuffle.xml; evidence/qa-b2b-privacy-utc-final-source.json

Documentación: CATALOGO.md

Revisión: QA independiente; root revisó contratos/sinks/destinos B2B.

Bloqueo: no registrado

Observaciones: sin observaciones

## QA-10

Fuente: [QA-10 — Baja: pruebas/herramientas poco portables y deuda estática](../../audit/2026-10-18/qa/INFORME_QA.md).

Problema: **Referencia:** `tests/services/test_key_manager.py:26`, `tests/test_audit_remaining_fixes.py:155`, `requirements_web.lock:110`, `ui_desktop/pyside/login_premium.py:1365`.

Un test asume bits POSIX en Windows; 9 fallos iniciales vienen de read_text sin encoding. El lock incluye uvloop sin marcador de plataforma y su instalación falló en Windows. Ruff detectó QApplication no importado en login premium: el NameError queda capturado y desactiva animaciones silenciosamente, sin demostrar crash. Es un defecto desktop, separado del SaaS.

Criterio original: encoding UTF-8 explícito; validación permisos acorde al SO; lock y manifests coherentes por target; reglas F821 y sintaxis bloqueantes. No convertir todos los 1976 diagnósticos Ruff en bugs de producto.

Estado: en_revision; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Contención A1 integrada localmente; ver CAMBIOS.md para comportamiento y límites por criterio.; 14fuentes seguimiento congeladas, aislamiento/CI bloqueante preparada, contratos obsoletos sustituidos por comportamiento; Redis real/R04/imagen/CI remota pendientes.

Commits: 166038f88b211c52f0d149ce550880795361707c, e8e0c44

Pruebas: A1:207passed/0failed/0skipped en candidatoWindows3.12.13; huella estable328archivos.

Evidencia: QA_R05.md; evidence/pytest-r05-frozen-candidate.xml; evidence/qa-r05-frozen-hashes.json; evidence/sbom-linux-runtime.json; evidence/sca-linux-runtime-final.log; evidence/repository-comparison.json; evidence/A1-containment.xml; evidence/A1-containment-source.json; evidence/r05-followup-frozen-source.json

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md; QA_R05.md

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## UX-01

Fuente: [UX-01 / P0](../../audit/2026-10-18/ux/INFORME_UX.md).

Problema: `usuario_suscripcion.html:708-721` interpreta parámetros de URL de éxito, llama al cambio de plan con `catch` vacío, lanza confeti y muestra Pro antes de confirmar la suscripción del servidor.

Criterio original: El usuario puede ver una compra confirmada que el servidor o proveedor no han validado. La activación debe venir del estado persistido y verificable del backend. Este hallazgo se comparte con seguridad; no representa un problema puramente visual.

Estado: en_curso; implementación: en_revision; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Contención A1 integrada localmente; ver CAMBIOS.md para comportamiento y límites por criterio.

Commits: 166038f88b211c52f0d149ce550880795361707c

Pruebas: A1:207passed/0failed/0skipped en candidatoWindows3.12.13; huella estable328archivos.

Evidencia: evidence/backend-before.log; evidence/backend-money-contract.md; evidence/security-money-source.json; evidence/A1-containment.xml; evidence/A1-containment-source.json

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## UX-02

Fuente: [UX-02 / P0](../../audit/2026-10-18/ux/INFORME_UX.md).

Problema: `usuario_perfil.html:102-105` promete aplicar notas de alergias, condiciones especiales e incluso diabetes. `_do_generar_plan`, `web/routes/planes.py:95-115`, no incorpora notas al objeto nutricional: solo lee exclusiones explícitas y puede descartarlas por plan comercial.

Criterio original: Una nota médica no constituye una regla de seguridad del generador. Eliminar inmediatamente la promesa incorrecta, distinguir preferencia y alergia estructurada, bloquear el flujo cuando no pueda respetarse una restricción de seguridad y someter el contrato a revisión profesional. No ofrecer protección de alergias como mejora de pago. Evidencia de código, sin experimento clínico.

Estado: en_curso; implementación: en_revision; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Contención A1 integrada localmente; ver CAMBIOS.md para comportamiento y límites por criterio.

Commits: 166038f88b211c52f0d149ce550880795361707c

Pruebas: A1:207passed/0failed/0skipped en candidatoWindows3.12.13; huella estable328archivos.

Evidencia: evidence/security-review.md; evidence/pytest-nutrition-independent.xml; evidence/coverage-nutrition-focused.json; evidence/A1-containment.xml; evidence/A1-containment-source.json

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## UX-03

Fuente: [UX-03 / P1](../../audit/2026-10-18/ux/INFORME_UX.md).

Problema: Diario guardado únicamente en claves como `mb_daily_FECHA`, `mb_water_FECHA`, `mb_meals_FECHA` (`usuario_mi_plan.html:428-430`, `:728`, `:783-785`, `:1067`). `base_usuario.html:170` ejecuta `localStorage.clear()`.

Criterio original: Reproducción local: guardar 1.5 L crea diario/agua; cerrar sesión deja ambas listas vacías. Se pierde el supuesto historial y otro dispositivo no lo recibe. Faltan persistencia por usuario y fecha, sincronización e identidad de cada registro. Las claves tampoco incluyen usuario: existe riesgo de reutilizar datos si cambian las credenciales sin el cierre que borra todo.

Estado: pendiente; implementación: pendiente; validación: pendiente; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: pendiente

Commits: pendiente

Pruebas: pendiente

Evidencia: pendiente

Documentación: pendiente

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## UX-04

Fuente: [UX-04 / P1](../../audit/2026-10-18/ux/INFORME_UX.md).

Problema: `new Date().toISOString().slice(0,10)` define el día del diario y del calendario (`usuario_mi_plan.html:428`; `usuario_historial.html:256`).

Criterio original: Verificado con navegador en America/Mexico_City: el 18 de octubre por la tarde se escribió `mb_daily_2026-10-19`. Definir fecha local del usuario/gimnasio y zona horaria explícita; probar cambio de día y horario.

Estado: pendiente; implementación: pendiente; validación: pendiente; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: pendiente

Commits: pendiente

Pruebas: pendiente

Evidencia: pendiente

Documentación: pendiente

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## UX-05

Fuente: [UX-05 / P1](../../audit/2026-10-18/ux/INFORME_UX.md).

Problema: Diseño móvil recorta acciones principales. `/suscripciones`: ancho de documento 582 px en viewport 390; `/clientes`: 483 px. `suscripciones.html:91` fija 3 columnas; `configuracion.html:24` mantiene 2 columnas. `styles-usuario.css:1931-1936` oculta desbordamiento del historial. El menú fijo tapa títulos de gimnasio (`styles.css:1820`, `:1877`).

Criterio original: Capturas locales muestran precios/CTA fuera de pantalla, búsqueda casi sin espacio y PDF del historial inaccesible visualmente. Usar layouts por breakpoint, cabecera con espacio reservado, tablas con scroll accesible o tarjetas. No ocultar el desbordamiento global como sustituto.

Estado: en_revision; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: B2B6recorridos, R13 17estados y5personales con27fuentes estables. TransporteAPI sintético, no sandbox/auth/RLS/lector de pantalla. Seguimiento R11 corrige fixture token y añade auth real.

Commits: c45a71c

Pruebas: pendiente

Evidencia: evidence/ux/frontend-independent-source.json; evidence/ux/frontend-independent-review.md

Documentación: CATALOGO.md

Revisión: QA independiente; root revisó contratos/sinks/destinos B2B.

Bloqueo: no registrado

Observaciones: sin observaciones

## UX-06

Fuente: [UX-06 / P1](../../audit/2026-10-18/ux/INFORME_UX.md).

Problema: Equipo sin recorrido web completo: no hay pantalla en `pages.py` ni navegación de equipo. `team.py:240` genera `/auth/accept-invite?token=...`, pero la API POST real está montada en `/api/auth/accept-invite` (`main_web.py:333`). GET de esa ruta devolvió 404 local. Además `team.py:146` incorpora el enlace completo recibido como si fuera el token del correo, produciendo una URL mal formada. Los invitados son `tipo='usuario'` (`team.py:224`), mientras `auth-guard.js:26-29` envía ese tipo al portal individual.

Criterio original: No se puede vender operación de 2/4 profesionales simultáneos con este recorrido incompleto. Añadir gestión de miembros, aceptar invitación con URL absoluta y token correcto, sesión con gimnasio efectivo y navegación por permisos. Reutilizar RBAC existente.

Estado: pendiente; implementación: pendiente; validación: pendiente; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: pendiente

Commits: pendiente

Pruebas: pendiente

Evidencia: pendiente

Documentación: pendiente

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## UX-07

Fuente: [UX-07 / P1](../../audit/2026-10-18/ux/INFORME_UX.md).

Problema: Portal individual y cartera del gimnasio son productos desconectados. `usuario.py:55-77` crea un Cliente cuyo `gym_id` es el propio usuario; `models.py:162-204` no define vínculo de cuenta miembro a cliente del gimnasio.

Criterio original: El socio que se registra no obtiene automáticamente el plan del dueño. Diseñar invitación/asignación miembro-cliente, acceso al plan del gimnasio y reglas explícitas de revocación/traslado. Conservar también el caso independiente si es parte de la oferta. Es una brecha de producto observada en modelo y rutas, no un fallo de aislamiento que deba resolverse compartiendo cuentas.

Estado: pendiente; implementación: pendiente; validación: pendiente; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: pendiente

Commits: pendiente

Pruebas: pendiente

Evidencia: pendiente

Documentación: pendiente

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## UX-08

Fuente: [UX-08 / P1](../../audit/2026-10-18/ux/INFORME_UX.md).

Problema: El manejador global Enter de `main.js:272-303` intercepta elementos interactivos fuera de formularios y dispara el CTA del dashboard.

Criterio original: Prueba local: enfocar enlace Clientes y pulsar Enter dejó `/dashboard` y abrió el modal de cliente. Respetar la activación nativa de enlaces/botones; limitar atajos a controles concretos y evitar disparar acciones financieras o de guardado por Enter genérico.

Estado: en_revision; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: B2B6recorridos, R13 17estados y5personales con27fuentes estables. TransporteAPI sintético, no sandbox/auth/RLS/lector de pantalla. Seguimiento R11 corrige fixture token y añade auth real.

Commits: c45a71c

Pruebas: pendiente

Evidencia: evidence/ux/frontend-independent-source.json; evidence/ux/frontend-independent-review.md

Documentación: CATALOGO.md

Revisión: QA independiente; root revisó contratos/sinks/destinos B2B.

Bloqueo: no registrado

Observaciones: sin observaciones

## UX-09

Fuente: [UX-09 / P1](../../audit/2026-10-18/ux/INFORME_UX.md).

Problema: Accesibilidad: contraste insuficiente recurrente, icono de contraseña sin nombre en ambos accesos, objetivos táctiles pequeños, inputs de precios sin nombre accesible. JSON contiene selectores y ratio. Toasts carecen de región de estado (`components.js:8-35`; `base_usuario.html:123`), filas/calendario son solo clic (`usuario_historial.html:124-150`, `:278-296`). Modales no implementan semántica, retorno/trampa de foco coherentes.

Criterio original: Corregir tokens, nombres, labels, botones semánticos, foco, Escape y avisos anunciables. Ya existe `:focus-visible` y reducción de movimiento en CSS del gimnasio (`styles.css:1983-1996`); extender una solución compartida a ambas interfaces. Los resultados automáticos no verifican por sí solos la operación con lector de pantalla.

Estado: en_revision; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: B2B6recorridos, R13 17estados y5personales con27fuentes estables. TransporteAPI sintético, no sandbox/auth/RLS/lector de pantalla. Seguimiento R11 corrige fixture token y añade auth real.

Commits: c45a71c

Pruebas: pendiente

Evidencia: evidence/ux/frontend-independent-source.json; evidence/ux/frontend-independent-review.md

Documentación: CATALOGO.md

Revisión: QA independiente; root revisó contratos/sinks/destinos B2B.

Bloqueo: no registrado

Observaciones: sin observaciones

## UX-10

Fuente: [UX-10 / P1](../../audit/2026-10-18/ux/INFORME_UX.md).

Problema: `usuario_mi_plan.html:520-529` calcula "Vas al 100% de tu meta diaria" usando kcal del menú generado. Después alterna con porcentaje de cuatro checkboxes o selección (`:1210-1248`).

Criterio original: Captura local de una cuenta recién configurada, sin registrar alimentos: ya muestra 100%. Separar objetivo nutricional, plan prescrito, selección de opciones y consumo real; definir una sola fuente para adherencia.

Estado: pendiente; implementación: pendiente; validación: pendiente; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: pendiente

Commits: pendiente

Pruebas: pendiente

Evidencia: pendiente

Documentación: pendiente

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## UX-11

Fuente: [UX-11 / P2](../../audit/2026-10-18/ux/INFORME_UX.md).

Problema: Onboarding incompleto muestra Generar/Comidas/Agua/Excluir (`usuario_mi_plan.html:464-468`) y retorna antes de registrar sus listeners. Dice que bastan 3 datos (`:148`), mientras exige edad y otros campos en perfil.

Criterio original: Prueba local: pulsar Generar no produjo petición, mensaje ni navegación. Mostrar la siguiente acción realizable y explicar los datos necesarios; deshabilitar/explicar acciones aún no disponibles.

Estado: pendiente; implementación: pendiente; validación: pendiente; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: pendiente

Commits: pendiente

Pruebas: pendiente

Evidencia: pendiente

Documentación: pendiente

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## UX-12

Fuente: [UX-12 / P1](../../audit/2026-10-18/ux/INFORME_UX.md).

Problema: Fallos se muestran como ausencia o estado válido: `usuario_historial.html:155-157` muestra "Sin planes" ante error; `usuario_suscripcion.html:660-663` sustituye error por Starter activo; `usuario_mi_plan.html:452-483` silencia fallos. Muchas llamadas directas `fetch` eluden refresh y error estructurado de `api.js:85-145`.

Criterio original: Evitar que una falla de red o sesión parezca pérdida de datos/cambio de plan. Diferenciar vacío, permiso, sesión expirada y servicio no disponible, con reintento explícito y conservación de lo último conocido. Hallazgo de código; no se provocaron fallos en producción.

Estado: pendiente; implementación: pendiente; validación: pendiente; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: pendiente

Commits: pendiente

Pruebas: pendiente

Evidencia: pendiente

Documentación: pendiente

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## UX-13

Fuente: [UX-13 / P2](../../audit/2026-10-18/ux/INFORME_UX.md).

Problema: Sin suscripción local, `suscripciones.html:344-353` muestra "Sin plan" junto a "Renovación mensual automática" y "Renovación automática activa". `usuario_suscripcion.html:366-369` fuerza badge Activo sin consumir estado real.

Criterio original: Genera incertidumbre sobre si se cobrará al usuario. Modelar sin plan/prueba/pago pendiente/activo/vencido/cancelado y mostrar proveedor, importe, fecha y acción que correspondan.

Estado: en_revision; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: B2B6recorridos, R13 17estados y5personales con27fuentes estables. TransporteAPI sintético, no sandbox/auth/RLS/lector de pantalla. Seguimiento R11 corrige fixture token y añade auth real.

Commits: c45a71c

Pruebas: pendiente

Evidencia: evidence/ux/frontend-independent-source.json; evidence/ux/frontend-independent-review.md

Documentación: CATALOGO.md

Revisión: QA independiente; root revisó contratos/sinks/destinos B2B.

Bloqueo: no registrado

Observaciones: sin observaciones

## UX-14

Fuente: [UX-14 / P2](../../audit/2026-10-18/ux/INFORME_UX.md).

Problema: Una cuenta nueva mostró 10 membresías en configuración: cada uno de los 5 valores iniciales duplicado. `repository.py:520-528`, `:560-568` crea defaults al leer sin unicidad de gimnasio/duración. El dashboard hace varias lecturas concurrentes.

Criterio original: Observación reproducida en dos ejecuciones independientes de navegador. La carrera concreta es inferencia apoyada por código; seguridad/backend debe confirmarla. Inicializar de forma idempotente y limpiar duplicados con una migración revisada antes de permitir cambios de precio.

Estado: en_revision; implementación: en_curso; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Preparación local sin DDL en fábricas;31 casos autor y15 independientes, vacío/legado/drift/restore22tablas. Staging, privilegios y R04 siguen abiertos.

Commits: e8a6806

Pruebas: pendiente

Evidencia: evidence/backend-r03-paths-restorable.xml; evidence/pytest-r03-restorable-independent.xml; evidence/r03-restorable-independent-source.json

Documentación: evidence/backend-r03-design.md; evidence/coordinator-r03-review.md

Revisión: Coordinador y QA independientes del autor backend; alcance local R03/R08, no aceptación productiva.

Bloqueo: no registrado

Observaciones: sin observaciones

## UX-15

Fuente: [UX-15 / P2](../../audit/2026-10-18/ux/INFORME_UX.md).

Problema: El perfil indica "Cambios de contraseña desde ajustes" (`usuario_perfil.html:24`), pero no existe esa pantalla para individuos. Accesos no ofrecen recuperación de cuenta. Registro/login usan `novalidate`; muchas etiquetas no están asociadas mediante `for`. Rangos de datos varían entre cliente nuevo, drawer y perfil (`clientes.html:154-185`, `dashboard.html:126`, `usuario_perfil.html:44-52`).

Criterio original: Recuperación de contraseña y gestión de cuenta verificables; un contrato de validación compartido y errores por campo accesibles. Evitar que el usuario se dirija a una función inexistente.

Estado: en_curso; implementación: en_revision; validación: en_curso; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: Contención A1 integrada localmente; ver CAMBIOS.md para comportamiento y límites por criterio.

Commits: 166038f88b211c52f0d149ce550880795361707c

Pruebas: A1:207passed/0failed/0skipped en candidatoWindows3.12.13; huella estable328archivos.

Evidencia: evidence/security-review.md; evidence/pytest-nutrition-independent.xml; evidence/coverage-nutrition-focused.json; evidence/A1-containment.xml; evidence/A1-containment-source.json

Documentación: ESTADO.md; DECISIONES.md; VALIDACION.md

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## UX-16

Fuente: [UX-16 / P2](../../audit/2026-10-18/ux/INFORME_UX.md).

Problema: Landing real (`pages.py:37`, `templates/landing.html`) es principalmente un selector de acceso. La landing comercial de `web/pages/landing.html` no está conectada a las rutas revisadas. En móvil el CTA de miembro y el registro aparecen debajo del primer viewport. No se muestran precios públicos, muestra real del resultado, límites o soporte.

Criterio original: Conservar accesos rápidos para usuarios recurrentes y añadir recorrido comercial para prospectos con ejemplo de plan, beneficios verificables, precios/límites, FAQ, privacidad y CTA contextual de registro. El registro por defecto es individual aunque el usuario puede llegar buscando un gimnasio.

Estado: pendiente; implementación: pendiente; validación: pendiente; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: pendiente

Commits: af177b1

Pruebas: pendiente

Evidencia: pendiente

Documentación: CATALOGO.md

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## UX-17

Fuente: [UX-17 / P2](../../audit/2026-10-18/ux/INFORME_UX.md).

Problema: Onboarding marca exportación terminada al existir un plan (`main.js:198`, `hasExported = hasPlans`). El botón "Actualizar mi plan" guarda perfil y luego pide regenerar por separado (`usuario_perfil.html:122`, `:315-333`). WhatsApp solo prepara texto, sin adjuntar PDF (`generar-plan.html:843-875`), mientras otro texto sugiere envío directo.

Criterio original: Medir los eventos reales, llamar a cada acción por lo que hace y acompañar la entrega con instrucciones o un mecanismo autorizado de compartición. Evitar un checklist al 100% sin que el cliente haya recibido nada.

Estado: pendiente; implementación: pendiente; validación: pendiente; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: pendiente

Commits: pendiente

Pruebas: pendiente

Evidencia: pendiente

Documentación: pendiente

Revisión: pendiente

Bloqueo: no registrado

Observaciones: sin observaciones

## OPS08

Fuente: [OPS08 - Configuración Railway posterior al 1 de diciembre de 2026](NUEVOS_HALLAZGOS.md).

Problema: Config as Code obsoleto: el archivo Railway existente deja de estar soportado tras el corte anunciado.

Criterio original: Inventario efectivo saneado, IaC compatible preparado y fijado, diff revisado, sintaxis y contratos validados; pre-deploy/digest/salud/secretos/volúmenes/rollback ensayados en staging autorizado antes del corte. Sin aplicar infraestructura ni contratar recursos por esta entrada.

Estado: en_revision; implementación: parcial; validación: parcial; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: pendiente

Commits: bc6804c

Pruebas: 23Node ytsc independientes,12fuentesestables; SDK npm audit0conocidas/6deps; sinplanCLI/apply/loader/staging.

Evidencia: evidence/ops08-independent-source.json; evidence/ops08-node-local.xml; evidence/ops08-readonly-inventory.json

Documentación: NUEVOS_HALLAZGOS.md; RAILWAY_IAC.md

Revisión: QA independiente de Node/tsc y coordinador de contrato/limites

Bloqueo: "Adopcionlegacy, importcompleto,privilegios,digestfinal/entornoaislado/costes ypinningloaderCLI necesitan paquete final yautorizacion; definicionpreparatoria bloqueaapply."

Observaciones: Fuente primaria consultada2026-10-18; no cambia los92IDs originales ni autoriza aplicar IaC.

## SEC01

Fuente: [SEC01 - Licencias sin autoridad verificable](NUEVOS_HALLAZGOS.md).

Problema: Activación pública deriva plan de prefijo, otorga365d y sobrescribehardware; offlineonline acepta falta de red sin licencia local demostrada.

Criterio original: Ningún prefijo concede acceso; autoridad emitida y propietario verificados sin asociar por email; hardware ajeno no se sobrescribe; periodo/límites proceden de licencia emitida; revocación/caducidad/repetición seguros; caída de red no valida desconocidas; compatibilidad local existente y reconciliación con regresiones/revisión independientes.

Estado: en_revision; implementación: parcial; validación: parcial; despliegue: no_desplegado; entorno: local.

Dependencias: sin dependencia declarada

Cambios: pendiente

Commits: 4d03300, f325fc4, 501ceaa, 5bb5395

Pruebas: 19 fallos antes;40 aprobadas finales,7.98s; autoridad JWT persistida y Unicode rechazado

Evidencia: evidence/license-security-before.xml; evidence/pytest-license-unicode-final.xml; evidence/license-independent-source.json; evidence/license-timezone-independent-source.json; evidence/pytest-license-timezones-final.xml; evidence/model-utc-independent-source.json; evidence/pytest-model-utc-auth-billing-license-independent.xml

Documentación: NUEVOS_HALLAZGOS.md; LICENCIAS.md

Revisión: QA independiente

Bloqueo: "Puente remoto autenticado, autoridad HMAC y campos comerciales legacy pendientes; contencion local y concurrencia PostgreSQL aceptadas, sin despliegue"

Observaciones: 43finales incl3PG procesosUTC/Mexico; normalizacionUTCnaive evita recorte6h. Puente remoto/HMAClegacy pendientes.; UTC modelos adoptado:52 instantes explicitos/2civiles conservadas,16PGindependientes+102auth/billing/licencias verdes; sinDDL ni reescritura de historia.

# Seguimiento de Auditoría y faltantes

**Fecha:** 2 de noviembre de 2026. **Corte documental:** cierre local previo a commit/CI; los cortes09:11 y09:24 y sus matrices se conservan en evidencias. **Ámbito:** servicio web. **Estado de esta entrega:** candidato aislado preparado y con pruebas focales; esta ejecución todavía no ha publicado código ni DDL en producción. La producción observada continúa en `fc7950ec` y esquema40. El acceso Google confirmado por el usuario y la contratación Stripe sin activar otro factor pertenecen a las publicaciones anteriores y se conservan.

Este documento continúa [Auditoría y faltantes](AUDITORIA_Y_FALTANTES.md), cuyo original se mantiene intacto. No reemplaza sus recibos ni convierte pruebas históricas en resultados de la fuente nueva. La política nueva aprobada por el usuario es mantener el acceso hasta acabar el periodo pagado ante una devolución parcial; la devolución completa conserva su tratamiento anterior.

## Trabajo realizado por agentes reales

| Responsabilidad | Agente y resultado concreto |
|---|---|
| Coordinación y arquitectura | `/root`: alcance, matriz de once pendientes, contratos, autorizaciones técnicas de recursos propios, revisión cruzada, integración, preservación y entrega. |
| Backend y datos | `/root/audit_backend_ci`: observaciones monetarias opcionales, migración41 con restricciones, conciliación consistente, historial personal/DTO y controles de fuente vigentes; 55 pruebas del autor en el corte final. |
| Frontend y UX/UI | `/root/audit_frontend`: presentación compartida de devoluciones, estado desconocido, historial personal, cambios de sesión y seis campañas Node con obligaciones explícitas. |
| QA y automatización | `/root/audit_qa`: permisos y factories HTTP reales, migraciones, PostgreSQL restringido/RLS, concurrencia, rollback/reintentos, navegador y controles negativos independientes. |
| Seguridad y privacidad | `/root/audit_security`: tres reproducciones financieras adversariales, revisión de la corrección, 34 controles finales, revisión de PostgreSQL, Bandit, secretos, wiring y planes de recuperación. Su clasificación de secretos fue validada por QA ajeno al autor. |
| Operación y documentación | `/root/audit_operations`: inventario real de proveedores y continuidad, privacidad S3, expiración efectiva de enlace, copia cifrada actual y preparación del ensayo local40→41, con límites y fallos preservados. |

Los roles trabajaron por olas conforme a las plazas disponibles. La autoría de aplicación y su aceptación independiente permanecieron separadas. El worktree de referencia no se editó; al preparar esta entrega se comprobaron intactas las 715 fuentes locales originales del worktree activo y su HEAD. Los temporales y evidencias nuevos permanecen en E/F.

## Comportamiento implementado

El candidato conserva el importe original y registra devolución acumulada, instante de observación e identidad interna de cargo cuando el proveedor permite confirmarlos. Los datos históricos desconocidos permanecen NULL. Una devolución parcial mantiene el acceso dentro del periodo ya pagado, no reinicia consumos y no revoca una renovación posterior independiente. El historial muestra importe original, devuelto e importe tras devolución; no lo presenta como ganancia, liquidación bancaria o contabilidad integral.

Las lecturas contradictorias de una misma factura durante la conciliación ahora provocan respuesta reintentable y rollback conjunto de acceso, pagos, consumo e inbox. Se distinguieron tipos, valores y presencia de campos. Seguridad conservó las reproducciones que antes permitían confirmar acceso tras observar una devolución completa, ampliar un periodo con una parcial o equiparar captura ausente con NULL.

Ambos historiales usan un DTO común y fechas UTC. El historial personal de un miembro de equipo lee sólo su identidad, con sesión vigente y límite1–100; no adopta el gimnasio del equipo ni un ID de query. No expone las nuevas identidades internas de cargo o PaymentIntent. Las respuestas tardías después de cambiar de sesión se descartan aun cuando el guard ya retiró el DOM.

La migración41 añade sólo tres columnas opcionales con CHECK y sin backfill. Su downgrade rechaza borrar hechos de devolución observados. La imagen40 no es compatible con41: [recuperación y publicación](../../implementation/20261102-audit-followthrough/RECUPERACION.md) y [decisiones/contratos](../../implementation/20261102-audit-followthrough/DECISIONES.md) describen los límites.

## Evidencia y alcance

| Conjunto | Resultado comprobado | Límite |
|---|---|---|
| Backend final | 55 PASS, 25 fuentes estables; migraciones SQLite 9 y transición nativa 19 tienen recibos separados | Proveedor controlado; no sustituye QA o sandbox real. |
| Seguridad financiera final | 34 PASS; tres oráculos adversariales corregidos y revocación JWT200→401 en ambas factories | SQL/HTTP aislados; proveedor sintético. |
| PostgreSQL final | 5 PASS, cero fallos/errores/skips; 646 fuentes estables, dos backends físicos, una UUID cerrada normalmente | Migraciones41, rol restringido/RLS, HTTP firmado, tres variantes503→rollback→retry→dedup; no Stripe real. El rechazo anterior4PASS/1FAIL de oráculo FULL se conserva. |
| Navegador independiente | 22 PASS a 320/390/1440, seis superficies axe sin hallazgos y sin errores JS/overflow observados | SSR/Api/JS reales; todas las peticiones HTTP interceptadas. |
| Extensión de cuatro anchos de coordinación | 24 PASS a 320/390/768/1440, conservando los asserts originales y añadiendo dos casos768 | Solapa los22 anteriores; no se suma como cobertura global. |
| Node vigente | Seis campañas aceptadas:51 comandos/925 ejecuciones/865 obligaciones;13→147; rutinas8→96 trazadas a 94 antiguas; producto 13; contraseña25; privacidad 48 | Programas/obligaciones se solapan. No acredita navegador o proveedor. |
| Controles de CI preparados | Companions41: 220 controles y54 de release, ejecutados como274PASS integrados; Node27 y secretos7 canarios independientes; once jobs históricos idénticos | El intento previo363 tuvo346PASS/17FAIL y se conserva. Tres familias financieras completas14/25/31 y privacidad19 pasaron en ese corte. Conjuntos solapados; CI completo e imagen Linux aún requieren aceptación propia. |
| Calidad estática real | Ruff PASS; sintaxis de 1206 archivos PASS; Bandit31 clasificados como5 históricos+26 técnicos;12 controles positivos y12 rechazos reales PASS | Clasificación finita de392 fuentes con revisión independiente y vencimiento; no acredita aislamiento del contenedor. |
| Inventario REST actual | API 185 / Web 204 registros efectivos; 210 pares método/ruta, sin duplicados | Inventario estático de 389 registros. No equivale a389 recorridos funcionales aprobados. |

Las cifras tienen recibos propios y conjuntos solapados; no se agregan. La fuente financiera física comprobada es SHA256 `8b49969b521349f33e073f8d1ab0308e98ae8cf61031f7c9394642fdb227fdca`; la variante Git/LF se vincula por separado en los contratos. [Operaciones](seguimiento/OPERACIONES.csv), [diferencias y metadatos](seguimiento/RESUMEN_API.json) y [traza de siete pantallas prioritarias](seguimiento/TRAZA_PANTALLAS.json) permiten continuar la revisión por elemento.

## Faltantes y siguiente acción

| ID | Estado e impacto al corte | Responsable y siguiente comprobación |
|---|---|---|
| **PEND-01 · P0** | Sandbox identificado por el usuario; todavía sin acceso autenticado de pruebas para esta ejecución. No hubo cargos ni ciclo real. | Dueño de pagos/QA: conectar Stripe al sandbox o custodiar sus claves test fuera del chat; comprobar modo/cuenta antes de compra/3DS, renovación, fallo, cancelación, devolución, webhooks y derechos. La integración sugerida aún no se acredita conectada. |
| **PEND-02 · P0 condicionado** | El corte anterior retenido tenía0 eventos/0 facturas ignoradas; no demuestra historia completa. No se detectó aquí un afectado que autorice reparar cuentas. | Operación/datos: ante una diferencia concreta, diagnóstico limitado y dry-run proveedor/pago/acceso; no replay ciego ni invención de ledger. |
| **PEND-04 · P1** | Política aceptada e implementación verificada localmente, incluida concurrencia, reintentos, cuota y renovación. Aún no publicada ni aceptada mediante sandbox real. | Backend/QA/operación: cerrar PEND-01, controles de publicación y migración revisada; verificar después runtime y recorrido de pago. |
| **PEND-05 · P1** | Mercado Pago sigue sin token/secreto; la UI deshabilitada coincide con esa disponibilidad. | Dueño de pagos/operación: mantener cerrado hasta configuración separada y ciclo sandbox/firma/consulta autoritativa. |
| **PEND-06 · P1** | Controles estáticos y274 controles integrados aceptados localmente, con fuentes/fixtures/oráculos vigentes y rechazos anteriores preservados. El escaneo físico estable rechazó1274 registros en28 archivos históricos por CRLF/LF; sus blobs Git y1274 coordenadas se cotejaron contra V9 sin ampliar el clasificador. CI completo, escaneo Git final, imagen/SBOM/SCA y publicación pendientes. | CI/arquitectura/seguridad: escanear el payload Git final exacto y ejecutar el workflow del commit, revisar fallos sin omitir gates, construir imagen y verificar entrada/revisión reales. No anunciar CI global verde con resultados parciales. |
| **PEND-07 · P1** | Siete pantallas trazadas y recorridos financieros focales probados. Faltan permisos/éxito/fallo/persistencia de todas las funciones ofrecidas. | Responsables de dominio/QA: completar matriz por actor válido y A/B para clientes, generación→historial→PDF, equipo, vínculos, privacidad, notificaciones, rutinas y analítica. |
| **PEND-08 · P1** | Copia cifrada actual de las 08:53:39 UTC y restauración local v4 aceptadas: 44 tablas/274 filas y tres objetos con hashes exactos; upgrade40→41 conserva cuotas, privacidad y hechos previos. Ensayo local de 104.172 s con fsync/synchronous_commit activados, sin promesa RPO/RTO; base y servidor propios cerrados normalmente. El rechazo v3 por captura PIPE permanece separado y se corrigió su atribución al arranque. PITR desactivado y cero calendarios de snapshots observados. | Operación/negocio: acordar RPO/RTO, agenda, retención, custodia externa y alertas; preservar respaldo y clave separados y ejercitar recuperación periódica. El ensayo local actual ya está verificado. No prometer una pérdida o tiempo máximos sin acuerdo. |
| **PEND-09 · P1** | Cuarenta referencias históricas siguen sin bytes recuperados; no se presentan como archivos restaurados. | Datos/custodia/soporte: localizar copias verificables o registrar pérdida, afectados, tratamiento y responsable. |
| **PEND-10 · P1** | Resend conserva clave de envío; consultas administrativas 401 restricted_api_key. La recepción diagnóstica histórica en Spam y el acceso Google confirmado mantienen sus evidencias distintas. | Correo/operación: habilitar un canal administrativo separado o webhook de entrega/rebote/queja firmado y alertas sin guardar OTP; no ampliar la clave runtime por defecto. |
| **PEND-11 · P1 antes de campaña** | ACL sin grants públicos, políticaIsPublic=false; objeto actual autenticado200/anónimo403. Una sonda diagnóstica del proveedor con URL firmada 10 s dio 200 inicial/403 a 15.562 s; no es una nueva función de entrega de la app. | Seguridad/operación/negocio: completar denegación entre tenants, muestra ampliada, custodia, carga representativa y objetivos/alertas/soporte. Dos APIs de políticas no soportadas por el proveedor 501 no equivalen a certificación AWS. |
| **PEND-12 · P2** | Historial de pagos con DTO común y GET personal documentado en ambas factories. Persisten diferencias intencionales y parsers manuales con metadatos incompletos. | Arquitectura/backend/frontend: clasificar cada diferencia y documentar payload, error, propósito y acceso. Una mutación sin body documentado puede no llevar payload o usar parser acotado; el inventario no la declara vulnerable por ese solo dato. |

## Publicación y continuidad

La aceptación local de devoluciones no autoriza a describir como vendible todo el servicio. Los criterios externos y operativos pendientes se mantienen explícitos. No se modificaron precios, cuotas, claves, lista de eventos Stripe, SDK/API del proveedor o permisos productivos. El candidato usa esquema41 y necesita una ventana de publicación y recuperación coherentes; no debe reemplazarse la imagen de producción sobre el esquema 40 sin preparar esa transición.

La documentación original, los 167 requisitos del backlog y los recibos anteriores conservan sus estados. La entrega actual enlaza implementaciones, controles y faltantes; el estado global sólo cambia con evidencia propia del criterio correspondiente.

## Índice de recibos

Los recibos completos permanecen fuera del entregable de aplicación en E, sin claves, códigos o datos restaurados en el repositorio:

- Autor: `E:/MetodoBaseWorkspace/evidence/audit-ci-author-20261102/final-author-handoff-v3.json`.
- Frontend: `E:/MetodoBaseWorkspace/evidence/audit-frontend-20261102-refund/final-frontend-node-handoff.json`.
- QA inicial y PostgreSQL final: `E:/MetodoBaseWorkspace/evidence/audit-followthrough-qa-20261102/final-qa-handoff.json` y `final-financial-qa-v4.json`.
- Seguridad: `E:/MetodoBaseWorkspace/evidence/audit-followthrough-security-20261102-gitleaks/financial-final-independent-decision-v3.json`, `financial-PG-v4-peer-review.json`, `bandit-final-independent-decision-v3.json` y `ci41-wiring-independent-review-v1.json`.
- Operación: `E:/MetodoBaseWorkspace/evidence/audit-operations-20261102T0805/operations-wave2-final-addendum-v2.json`, SHA256 `96c98167c49f634fbd381cd849ba89b03e24730c78463f106f0c72c7d090b00e`; enlaza restauración v4, snapshot, caducidad firmada, planes revisados y fallos anteriores.
- Coordinación: `E:/MetodoBaseWorkspace/evidence/audit-followthrough-root-20261102T075052Z/`; preservación715, inventario, autoridades, calidad y navegador de cuatro anchos.

Referencias aplicables consultadas: [recursos Charge en API2024-06-20](https://docs.stripe.com/api/charges/object?api-version=2024-06-20), [devoluciones](https://docs.stripe.com/refunds), [sandboxes](https://docs.stripe.com/sandboxes) y [claves y separación sandbox/live](https://docs.stripe.com/keys). Se mantuvieron Stripe SDK 11.6.0, FastAPI 0.146.0, Pydantic 2.14.1 y SQLAlchemy 2.1.5 del entorno, sin actualización de dependencias.

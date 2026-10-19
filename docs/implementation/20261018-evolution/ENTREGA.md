# Entrega candidata

Implementación local en curso; todavía sin release final, imagen probada ni despliegue. Rama `implementation/20261018-execution`, base daa25efbf51d154710bad625025b345fa9ec9252; código integrado hasta9f3f32e. [Estado](ESTADO.md), [historia](CAMBIOS.md), [registro97](TRAZABILIDAD.md).

| Hito | Evidencia local | Pendiente material |
| --- | --- | --- |
| Catálogo, derechos y cuotas | Free10/1/10 confirmado, catálogo común; ledger B2B24 y publicación individual26 atómica; PG y recuperación tras muerte real de proceso | Sandbox, diario27 y validación del artefacto desktop |
| Datos/RLS/restore | Contratos22–26 preservados por revisión; restore26 de25 tablas y19 familias FORCE, roles separados | Inspección/backup/staging y compatibilidad live |
| Archivos privados | Esquema25, lectores/worker/branding, SDK fijado, inventario readonly31 pruebas | Procedencia/apply legacy, destino durable real, imagen/proveedor |
| Sesiones y privacidad | API347,74 VM;36 grupos navegador actuales y3 Storage; sinks saneados y exportación personal | Reload/cross-tab/escritores directos, borrado/retención y revisión legal |
| CI/regresión | Node/17PG/cinco fixtures navegador configurados; serial1813/1skip Windows con519 fuentes estables | n2shuffle1813/1skip aprobado en133.73s; Actions/Linux/imagen/Redis real pendientes |
| Desktop | Receta3930398/171a8f0/9f3f32e integrada,94 pruebas independientes | Build/diagnóstico/ZIP real en curso; instalador/upgrade/firma pendientes |
| Equipo y licencias | R11 independiente128 casos/recorridos; SEC0143 incluidas carreras PG | Correo/canje consentido, puente remoto y autoridad HMAC legacy |

Antes de solicitar una operación externa faltan artefacto exacto/digest, variables sin secretos, migraciones en orden, backup/restore de ese candidato, transición de workers, rollback y observación. Migración26 exige drenar workers antiguos antes de reabrir generación: el startup nuevo no protege procesos viejos aún vivos. No se ejecutó ese cambio live.

El scan limpio más reciente cubre b20e071, no6d33b9e. Docker está bloqueado por virtualización deshabilitada. Los ensayos históricos, SBOM/SCA de resolución y checks estáticos conservan sus alcances; no prueban una imagen final inexistente. Diario persistente, recuperación/cuenta, progreso, MFA, contrato nutricional y restantes criterios97 siguen abiertos. No se publicaron commits/PRs ni se alteró Railway.

Estado vigente del19 de octubre: [ESTADO.md](ESTADO.md) sustituye los pendientes históricos resueltos, sin atribuir gates antiguos a las fuentes nuevas. UI individual y SEC03 integrados; estadísticas aceptada localmente; desktop94 receta aceptada y primer preflight rojo conservado. Diario27/restore/UI y CI nuevos siguen en revisión. PostgreSQL QA ahora55483. R21scan11b3123 tiene3 coincidencias pendientes, no aceptación limpia.

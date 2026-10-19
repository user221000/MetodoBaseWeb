# Entrega candidata

Estado: implementación local en curso; sin aprobación de release ni despliegue staging/producción. Rama: `implementation/20261018-execution`; base: `daa25efbf51d154710bad625025b345fa9ec9252`. A1 está integrado en166038f; los hitos posteriores constan en [CAMBIOS.md](CAMBIOS.md) y [VALIDACION.md](VALIDACION.md). Últimos módulos integrados:b81cfc1 cuotas/worker ydbb6af5 exportación/logs, con gate e3039c2. No existe todavía una imagen candidata final probada.

| Hito | Estado comprobado | Límite de aceptación |
| --- | --- | --- |
| Catálogo/derechos, cuotas individuales y nutrición | Integrado localmente con revisión independiente | Sandbox de pagos y revisión clínica pendientes |
| Alembic, backup/restore y RLS | R03 de22 tablas y R04 de23 ensayados; startup exige roles separados | Staging y cambio de privilegios productivos pendientes |
| Equipo y suscripciones UI | R11 con128 pruebas independientes y recorridos reales | Correo real y canje consentido por cuentas existentes pendientes |
| Licencias |43 pruebas finales, incluidas carreras PostgreSQL y UTC/México | Puente remoto desktop y autoridad HMAC legacy abiertos |
| Objetos privados | Puerto/adaptadores con33 pruebas independientes/una omisión Windows y factory con32 independientes | Metadatos/consumidores y destino durable aún en construcción |
| UTC |52 instantes adoptados en5bb5395,16 modelos/PG+102 regresiones independientes | Dos fechas civiles e historia conservadas; jobs legados requieren revisión separada |
| Cuotas B2B y privacidad | Integradas;25 dirigidas finales y1621 aprobadas tanto serial como n2shuffle | UI idempotente de generación, reconciliación durable y privacidad legal/borrado siguen abiertas |

Inventario completo: [TRAZABILIDAD.md](TRAZABILIDAD.md), generado desde [JSON](TRAZABILIDAD.json). Ningún registro pendiente se considera terminado por pertenecer a una tarea agrupadora.

Pendiente de materializar antes de pedir despliegue: commit candidato final, digest de la imagen probada, inventario definitivo de variables sin secretos, orden completo de migraciones, backup/restore de ese head, compatibilidad con versión anterior, rollback y observación posterior. Los ensayos ya ejecutados conservan su revisión y entorno; no prueban por anticipado los heads siguientes.

Docker no puede ejecutarse en este host por virtualización deshabilitada. La configuración CI exige Linux/imagen/Redis y desktop, pero no se ha ejecutado remotamente ni se sustituye por checks estáticos. El escaneo de secretos limpio más reciente cubre exactamente b20e071 (1006 archivos), no los cambios posteriores. Consulte [HIGIENE.md](HIGIENE.md).

El original permanece intacto; los cambios reviewables viven en `F:\MetodoBaseWeb-execution-20261018`. No se publicaron commits/PRs ni se modificó Railway. Las operaciones externas y dictámenes sin evidencia conservan estado abierto.

Preparaciones posteriores: diario4e22852 (35 pruebas puras, sin persistencia) e IaCbc6804c (23 Node/tsc independientes, sin plan/aplicar). PDF exacto y middleware no-referrer continúan en revisión, y la UI B2B debe congelar su servidor con las mismas fuentes antes de DDL25.

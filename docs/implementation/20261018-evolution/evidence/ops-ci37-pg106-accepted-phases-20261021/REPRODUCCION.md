# PostgreSQL37: 429 identidades aceptadas por fases congeladas

El complemento de siete fases en `c717df981c160d305a71d67a3dea46a94dd98b10` ejecutó **106/106 casos correctos**, sin fallos, errores ni omisiones. Sus siete fases aceptaron las identidades exactas, testigos físicos y nueve UUID previstas. Junto a las primeras22 fases aceptadas en `9955a8a55b7bb5902b269a2a5534e28521dca856`, cubre exactamente323+106=429 identidades en29 fases. No fue una ejecución única de429 casos. El primer intento completo sigue RECHAZADO con353 casos pytest correctos: los30 del bloque QA rechazado por el presupuesto anterior no se cuentan dos veces.

Se releen de forma independiente los29 JUnit y sus testigos físicos; las identidades son disjuntas entre las22 fases anteriores y las siete del complemento. El inventario completo de429 y los módulos/funciones/aserciones originales no cambiaron. Las únicas cinco diferencias de fuente frente a9955 son el presupuesto del runner, el selector opcional de preparación, sus controles y la copia RAW histórica del control68.

La corrección autorizada declara dos UUID acumuladas/concurrentes para `independent-qa`: una base de módulo37 más la base36 dañada que abre el caso original de rechazo de migración. Restore conserva sus dos UUID; las otras fases mantienen sus presupuestos y pools originales. El catálogo completo necesita69 UUID, corregido desde68. Los controles nuevos reprodujeron cinco rechazos y siete casos correctos antes del cambio; después pasaron29/29 (12nuevos y17anteriores). Se rechazan éxito con1,3,booleanos,float o cadena, y la selección complementaria conserva todas las identidades. El control antiguo68 está preservado byte exacto en `tests/ci_web37/fixtures/pg-lease68-original.py.RAW`, SHA256 `1a1bbe3061c7cd253b406ce26e7f68494c493e24f5034a4c34c2eb94b4c73e1e`.

En las fases únicas aceptadas se usaron69 UUID. Entre ambos intentos se crearon71 (62del primero más9del complemento), porque las dos bases del bloque QA rechazado se volvieron a crear en el complemento. Las71 cerraron mediante planificación exclusiva anterior a CREATE, identidad OID/propietario/nacimiento, cero sesiones, DROP normal y ausencia mediante conexión nueva. Una auditoría posterior volvió a confirmar las71 ausencias y la terminación de todos los procesos de ejecución. El master privado16040 quedó inactivo para Root; se devolvió la lease de fases y no se inició otro servicio.

La fuente ejecutada, el intérprete, todos los ficheros instalados de92 distribuciones,157 paquetes Node, binarios PostgreSQL y roles permanecieron iguales antes/después y en la auditoría independiente. `pip check` devolvió0 antes/después. La fuente de producto es el backend37 congelado anterior al rediseño y las rutas de rutinas del21 de octubre; esta aceptación no se atribuye a esas funciones nuevas ni a Linux/Actions/imagen. Los transportes puramente ASGI/SDK conservan su alcance y no prueban denegación RLS. No se ejecutó Desktop, Chrome, Redis, VM ni n2.

La preparación explícita `--groups independent-qa restore security-notifications onboarding-author onboarding-security qa26-primary qa26-registration` produjo contrato SHA256 `d5f08cb68c7f9b5eabdee7fdc0ce5c79b73b01335141e37f4a44e67063d658bd`. Root lo revisó, volvió a ejecutar29 controles puros y emitió una ACK nueva ligada a fuente/perfil/selección, SHA256 `148e02d72874ad1ec3507a4e64205f24eeba0b69cb74be7a39a91e48074396d4`. La ACK anterior se rechazó en la comprobación sinSQL. El runner revalidó la caducidad antes de cada child y auditó el cierre después de cada uno.

Originales privados (todas las raíces protegidas User+SYSTEM antes del payload y todos los miembros verificados por lectura):

| Captura | ZIP SHA256 | Miembros |
| --- | --- | ---: |
| Primer intento353, RECHAZADO | `80f4085850d2db9ece448af46fda3e09c347c90048535fc61404aa65733f022d` |228|
| Complemento106, aceptado | `748f5e5e31de3c76d9cefbd40e75a2e8c1ca71615c8d70894860886f27fb1af2` |99|
| Auditoría final71UUID y unión429 | `97deeac6f0c1a61df986a4e2b8c6d53ab16af0003fceef8dc2985964712969ea` |10|
| Preparación106 sinSQL | `ead9a5c9792803b98ed2ed041c853f727738badae8086bfd441a0161dcddd17c` |7|
| Controles antes de corregir presupuesto | `cad3913cb2204511c6e539ee7e5a1c38a69868208d1205af60225445d55bee2a` |18|
| Controles29 después de corregir | `1a8459d91db72edf6a3672cc24c16991a03f97ee3c58e50407004a0f05fbf2ce` |28|

Las raíces principales son `C:/Users/Consu/AppData/Local/Temp/metodobase-test-ci37-pg106-runtime-private-20261021-v1` y `C:/Users/Consu/AppData/Local/Temp/metodobase-test-ci37-pg106-final-audit-private-20261021-v2`. El primer productor de auditoría final rechazó una comparación de representación: las tuplas de `role_catalog` frente a las listas de su JSON. El productor original y ese rechazo están en el ZIP final. V2 compara la serialización JSON canónica conservando los tipos Boolean/integer; volvió a auditar bases, fuentes y roles. No modifica ni reclasifica el resultado pytest.

Los cinco resúmenes adjuntos son bytes originales públicos. Para reproducir se requiere una fuente congelada, perfil privado nuevo o revisado y otra ACK Root ligada a su contrato actual; ninguna ACK histórica autoriza una nueva ejecución. Los instaladores, roles/configuración del servicio general y el cluster histórico incompleto no se modificaron.

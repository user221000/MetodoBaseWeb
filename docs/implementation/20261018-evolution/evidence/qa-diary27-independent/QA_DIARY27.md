# QA independiente R14 backend27

Aceptación delimitada del commit a5a6bf1: 141 pruebas HTTP, 33 de migración/PostgreSQL y un restore poblado propio. Los gates finales no tuvieron fallos, errores ni omisiones. Las 78 fuentes y contratos autorales permanecieron idénticos.

El restore usa revisión explícita `20261019_personal_diary`, 26 tablas de negocio y 20 familias ENABLE/FORCE. Conserva filas, relaciones, cinco objetos privados, bytes/SHA/tamaño, secuencias y el crédito anterior. Añade cinco días de dos sujetos: agua, comidas completas o pendientes, versiones, UUID, fechas locales e instantes UTC. Eliminar el Plan de origen conserva su snapshot.

Las dos fábricas reales leen y exportan la base restaurada con rol app restringido, identidad persistida y sin overrides. La cuenta personal recibe tres días y el miembro profesional dos, sin cartera del propietario; los cursores con limit1 recorren todos los registros. Anónimo 401 y OWNER 403; RLS impide INSERT ajeno 42501 y UPDATE ajeno 0. GET/export no ejecutan COMMIT ni DML.

El primer restore fallido se conserva como errata del observador QA: incluyó el COMMIT de limpieza de tokens del lifespan SaaS. La lectura se mide ahora después del arranque; ambos intervalos tienen contadores separados. No hubo corrección de producto.

La fixture histórica 26 no se modificó. Al promover 27, CI debe enrutar el restore vigente al caso nuevo y conservar el probe pequeño y el histórico 26 separados. UI, composición final en main y RPO/RTO de negocio siguen fuera de esta aceptación. Ver `qa-diary27-final-source.json`, logs y JUnit.

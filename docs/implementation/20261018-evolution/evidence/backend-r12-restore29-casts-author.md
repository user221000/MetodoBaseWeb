# R12: cuatro predicados PG29 estables ante pg_dump/restore

Delta separado sobre el núcleo V2 `1aacbcb5`, aceptado independientemente en
sus21 criterios NULL/OWNER. No incluye API/servicios como producto ni los da
por aceptados. No cambia normalizadores v1, modelos, targets22–28 ni SQLite29.

El primer restore poblado29 falló antes de evaluar filas: PostgreSQL17
reexpresó casts de arrays varchar/text en un índice parcial y un CHECK
compuesto del descriptor. El intento con casts sólo de literales no bastó:
PostgreSQL volvía a escoger el tipo varchar de la columna. Se conservan ambos
estados exactos, diffs estructurales y logs; no se atribuye pérdida de datos.

Con columna y literales explícitamente text, la estructura quedó idéntica.
La siguiente verificación reveló la misma transformación en dos WITH CHECK
de políticas nuevas29, diagnosticada por separado. Funciones/triggers eran
idénticos. Se aplicó el mismo cast explícito sólo en estos cuatro predicados:

- índice único parcial `uq_client_link_current`, estados pending/active;
- CHECK `ck_client_publication_pdf`, backend local/s3 dentro de la asociación
  completa que sigue exigiendo todos los campos presentes;
- WITH CHECK `r12_link_update`, rama gym pending/revoked;
- WITH CHECK `r12_invitation_update`, rama gym pending/revoked.

No cambia el conjunto de estados, columnas, nulabilidad, FK, flags de RLS,
roles, funciones ni permisos; varchar se comparaba previamente como text en
la expresión de PostgreSQL. Ahora su deparse es estable sin ampliar la
normalización del contrato histórico. Los20 predicados históricos siguen
idénticos y la firma de funciones/guards es exactamente la de1aac.

Preimágenes RAW en Temp, antes de cada delta:

- primera variante: ZIP54cb6b91bb4c357dab2178c4623d25a3b9fbc4b0302186a631a1a00acecb7601;
- literales sin columna, rechazada: ZIP389e8baf765f739677ff7067eb043219fe0da87b2e2c5e7e77be83cb48f85ab0;
- antes de cast de políticas: ZIP641840a75a7379fad7e56dc0f9d99eca5bbba4aaf75358a59f3e31dc789becb3.

Restore completo verde25.70s en el gate sellado, con516 fuentes y81
distribuciones Python observadas antes/después sin cambios. Es medición
técnica local funcional, sin claim SLO/RPO/RTO ni proveedor real.

El caso nuevo deriva por separado del restore28 inmutable y conserva sus
asserts de26/27/28: ledger individual/B2B, PDF/logo/pending privados, diario
con fuente borrada, recuperación one-use y ambas factories. Añade seis links,
seis invitaciones, pending/active/revoked, tres publicaciones vigentes y dos
retiradas, cinco PDF exactos, OWNER propio y externo, denegación de otro
destinatario del mismo gym, FK/guard diferidos y23 familias ENABLE+FORCE.
Tras reconstruir adaptador/rol restringido, mantiene estructura, filas,
funciones, triggers, hash, descriptor y bytes. Las dos UUID exactas quedaron
eliminadas y se comprobó su ausencia en catálogo.

**Reproducibilidad del commit parcial:** el replay de restore utiliza el
overlay de servicios/API aún no incluido como producto en este commit. Su
RAW exacto está en Temp, archivo
`metodobase-r12-casts-restore-runtime-overlay.zip`, SHA
73730ec761c672a5d003d5bcf52f2f932dcf2cbad4117ee7d9dc9f1ba81a6081.
Los dos módulos nuevos de tests de restore se incorporarán con la API para
que el checkout completo sea ejecutable sin overlay. Este commit permite
revisar/migrar el núcleo y basar revisión30, no declara la API aceptada.

La primera invocación falló por faltar METODOBASE_TEST_EVIDENCE_DIR en el
harness antes del cuerpo del test; catálogo posterior backup/restore vacío,
sin DROP adicional ni inferir propiedad. Se corrigió el destino antes de
crear las UUID. Esto es errata de harness, separada de los rojos reales de
representación. No se modifica ni ejecuta una base ajena.

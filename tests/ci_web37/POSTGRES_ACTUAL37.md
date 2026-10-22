# PostgreSQL actual37: catálogo y transporte

El catálogo de33 contenía240 casos:234 de dominio, cinco físicos de migración33
y un restore33. Los234 se conservan en18 companions nuevos, con88 objetos de
función originales idénticos y parámetros completos. Los36 archivos originales
de funciones/fixtures quedan fijados por SHA256 LF. No se alteran cuerpos,
aserciones, helpers históricos ni targets. Las cinco migraciones físicas33
requieren su fuente33 auténtica; no se renombran como físicas37. El restore37 de
QA conserva75 aserciones históricas, incluidas las de33.

La colección actual tiene354 identidades en24 módulos:234 legacy,12 migraciones37,
13 nutrición,29 notificaciones,35 cuenta,30 del peer independiente y un restore37.
Los seis/ocho/catorce tests de nutrición/notificaciones/cuenta eran objetos de
función; los parámetros producen13/29/35 casos, respectivamente. Los12 HTTP
correctivos ya están contenidos en los30 casos actuales del peer. Sus replays
anteriores no se suman como otras12 obligaciones.

`pg_legacy_fixtures.py` crea únicamente UUID con la primitiva37 original. La base
se migra a37 antes de abrir la aplicación restringida. Se exigen41 tablas ORM,
42 físicas,32 FORCE RLS, cuatro privilegios falsos más membresía de owner falsa,
rol no propietario, FKs validadas, índice30 exacto y cuatro GUC vacíos. El engine
ordinario usa pool1/overflow0. El único caso R24 de espera real conserva su pool6
original para holder/worker/revocación concurrentes y registra explícitamente6.
No se afirma que ese escenario use pool1.

Las fixtures legacy de diary/followup/onboarding que ya migraban a `head` conservan
esa lógica sobre el nuevo transporte37. Los fixtures con target físico33 se
sustituyen por nuevos transports explícitos. El seed RLS completo mantiene la
misma AST del cuerpo original; su CREATE/DROP FORCE histórico no se importa.
Los factores y actores se obtienen mediante los endpoints/servicios originales;
no se sustituye un principal ni se añade autoridad. JWKS y JWT Google siguen el
transporte firmado actual de los criterios originales.

`pg_observer.py` sólo registra el valor devuelto por los witnesses reales; el
witness QA37 original se invoca completo y se restaura al cerrar pytest. Las
aserciones del peer y sus archivos permanecen intactos. Los registros privados
incluyen test/PID y las mediciones físicas, no un valor derivado de modelos sólo.

Comando de preparación sin SQL:

    python -B -X utf8 tests/ci_web37/run_postgres.py --plan-only --private <nuevo-absoluto-privado> --output <nuevo-absoluto-publico>

El primer plan354 pasó con92 distribuciones/source/157 archivos Node quietos y
pip0/0, sin ejecutar fixtures ni abrir SQL. Los19 controles offline de objetos
idénticos y seed también pasaron. Esto no acepta el runtime PostgreSQL.

La ejecución sin `--plan-only` requiere un lease exclusivo previo de Root y los
URLs sintéticos restringido/migrador en55483, además de `METODOBASE_TEST_PG_BIN`.
No crea roles, modifica HBA ni privilegios por defecto. Cada fase tiene un proceso
propio, JUnit ligado a colección exacta, witness físico y journal fsync. Skips,
errores, omisiones o cambios de identidad rechazan la fase. `--groups` permite
un replay focal explícito y nunca declara aceptado el catálogo completo354.

`ACCOUNT37_PRIVATE_LEASES` se crea bajo el Temp global auténtico en un directorio
privado cuyo nombre conserva el prefijo que exige la primitiva. TEMP/TMP no se
modifican. El owner registra planned antes de CREATE, OID y nacimiento del proceso;
exige cero sesiones antes del DROP ordinario y ausencia desde una conexión fresca.
El runner vuelve a comprobar catálogo/sesiones al final. No hay terminación de
backends ni DROP FORCE ante fallos. Los roles, cinco binarios PG, intérprete,
todos los archivos instalados y fuente deben permanecer quietos.

Pendientes del catálogo final: adaptación PG explícita de los nuevos19 criterios
R22/UX17, los criterios monetarios/tenant adicionales que confirme Root, y el
overlay final R22/R05 sobre la fuente que se ejecute. Estos354 no incluyen ni
aceptan todavía esos incrementos, Chromium, Redis, imagen Linux o Actions.

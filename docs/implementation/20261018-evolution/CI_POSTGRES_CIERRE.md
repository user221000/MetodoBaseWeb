# Cierre PostgreSQL de los companions actuales

<!-- DOC166-CLOSED61-FOLLOWUP -->

## Seguimiento del checkpoint 166 — SQLite39 final aceptado; restore PG rechazado

SQLite39 final cerró normalmente con 61/61 PASS, cero fallos, errores o skips, sobre Source1557 9b3160df3820c8fd75137b8c5edfe7ccfec5cf2100a6f14fd68005ce57e6a328. Colección y JUnit exactos; fuente, 92 paquetes y binarios quietos, pip0/0. Este resultado no reemplaza los anteriores 52(38PASS/14F), 57(56PASS/1F) y 61(57PASS/4F), preservados con sus fuentes.

Restore PG38/527 superó estructura y falló después en tenant_security. Root comunica ambas UUID cerradas sin sesiones; sólo se lee el resultado cerrado, no logs. Comparador puro56 y SQLite61 no acreditan la restauración de PostgreSQL, seguridad global o integración Main; el diagnóstico de políticas es separado.

Root conserva también el rechazo precopia733f: 2258 SHA/tamaños exactos, diferencias sólo en atime de lectura y ningún root/output/Git creado. Su hijo finito es trabajo independiente de Root;733f queda sellado.

Se mantienen167 filas, los166 criterios y estados anteriores,92IDs originales,66verificados ySEC26 en_revision. R22/R30/R31/R34 son obligatorios;R28/R35 son condicionales conforme sus criterios. [Resumen166](evidence/checkpoint166-web-continuity-20261023/summary.json) y[matriz](evidence/checkpoint166-web-continuity-20261023/matrix.md).


<!-- DOC166-SOURCE-SCOPED-SEC26-IN-REVIEW -->

## Checkpoint 166 — corte documental preparado en E

167 filas: los 166 criterios/estados E165 y92IDs originales se conservan; sólo se añade SEC26 en revisión, con66verificados locales sin cambio. Sus46SQLite/25Node/23PG y14llamadas directas están ligados a fuentes propias.108SQLite/core38PG9/password23 son alcances focales; Node histórico mantiene atribución. Privacy52(38P/14F),57(56P/1F),61(57P/4F),shells8PASS1554,Node48offlinePASS1550 ypure56PASS permanecen separados. PG38restore89867 seguía en curso al mensajeRoot: sin lectura de logs ni aceptación anticipada.

R22/R30/R31/R34 siguen obligatorios; R28/R35 son condicionales conforme sus criterios. Main39/CIglobal/Linux/imagen/Redis/R34/proveedor/piloto/legal14/custodia siguen abiertos. Originales fallidos preservados, no nuevoSEC27 ni cierre por harness. [Resumen166](evidence/checkpoint166-web-continuity-20261023/summary.json) y[matriz](evidence/checkpoint166-web-continuity-20261023/matrix.md).


Contrato documental del helper `tests/ci_web37/pg_close.py` integrado en dc9f. No modifica `tests/account_security37_owned.py` (SHA603f), CREATE/DROP, oráculos ni presupuestos históricos. Requiere ventana Root exclusiva y generación PostgreSQL estable sin restart; callbacks no ejecutan SQL ni miden por sí mismos esa generación.

| Adapter | Consumidores / límite |
|---|---|
| `tests/ci_web37/pg_legacy_fixtures.py::current_database` | Legado234; fixtures actuales de reexportación |
| `tests/ci_web37/fixtures.py::followup_db` | Current37/autor/onboarding/QA26 |
| `tests/integration_account_security37_pg_migrations.py::account_database` | Doce DDL, cuerpos originales |
| `tests/account37_qa_pg_fixtures.py::peer37_database` | Peer de cuenta37 |
| `tests/account37_qa_pg_controls.py` | Binding del control DDL, sin cambiar su cuerpo |
| `tests/integration_current37_restore.py::owned_databases` | Contextos anidados separados |
| `tests/integration_r30_ppl37_postgres.py::followup_db` | 53 IDs; pool5/max0 |
| `tests/billing13_legacy_apply37_pg_fixtures.py::pg37` | 27 IDs; pool1 y operador R07 admin explícito |

Admite generación/OID/owner antes del cuerpo y los revalida antes de disponer pools. Los callbacks filtran psycopg2 real, DSN loopback, rol y UUID; registran Record/DBAPI por lifetimes débiles y conservan referencias a cada Pool original. Un dispose histórico no implica cierre físico: una devolución posterior demostrada es válida; un préstamo/detach vivo o un hueco/incoherencia del ledger rechaza.

La barrera exige estado actual sin préstamos y pools coherentes antes de cada dispose propio. Después de disponer todos los pools, exige DBAPI cerrados antes de aceptar el drenaje natural. Dispone únicamente recursos atribuidos y consulta todas las sesiones de la UUID; cualquier PID desconocido rechaza inmediatamente. Sólo espera salida natural de PIDs conocidos, con deadline2s, consultas limitadas250ms y comprobaciones antes/después de cada consulta y del cero. No cancela, termina, cierra conexiones prestadas ni usa DROP FORCE. El owner original conserva su count0, DROP normal y ausencia fresca.

El recibo nuevo se publica en `pool-close/<UUID>.json`, fuera del glob original de leases, después del finally del owner. Un error del observador o acceptedFalse hace fallar el teardown; no basta escribir JSON negativo. No se promete retención de la DB si el finally original puede cerrarla normalmente.

Las siete regresiones portátiles de `tests/test_ci_web37_pg_close.py` usan métodos reales y dobles inertes, sin SQL/SUT/SDK. PG53 conserva sus bindings históricos y añade exactamente los dos bindings de fixture actual; su prueba copia la unión. PG27 añade el helper a BOUND_PATHS y Native actual cambia sólo ese pin de contrato; no se alteran los22helpers históricos. Native/load y subprocessos pg_dump/pg_restore requieren ownership separado.

Ante un teardown rechazado, conservar JUnit y leases originales, no reetiquetar created, y suspender aceptación del gate. Root inspecciona generación/OID/owner y sesiones en operación separada; sólo con cero actual puede usar DROP normal y conexión fresca para ausencia. Ese cierre posterior y un focal verde no prueban causa retrospectiva. Repetir el gate necesita una fuente/contrato/ACK y ventana vigentes, no una relajación del oráculo.

Evidencia del checkpoint: [matriz](evidence/checkpoint162-web-continuity-20261023/matrix.md). PG1 actual/1UUID está aceptado; PG509 actual está en curso. Ningún ensayo de proveedor, Native35 nuevo, backup retenido, carga, imagen o despliegue queda acreditado por esta barrera.

## Actualización163 por fuente

El párrafo anterior conserva el corte162. PG509 actual93251 terminó aceptado sobre dc9f:509casos,71UUID y71recibos comunes; Native35 tiene su propio cierre35grupos/1UUID sobre dc9f. Ningún resultado Native, carga, Redis o backup procede de esta barrera. La precisión DBAPI es documental: no_loans/coherencia antes de cada dispose; no_open_dbapi después de todos, antes de aceptar el drenaje. [Resumen163](evidence/checkpoint163-web-continuity-20261023/summary.json) y [matriz](evidence/checkpoint163-web-continuity-20261023/matrix.md).

Revisión independiente PG37 y restore actual

Fuente de producto: 5806e09231fbecd5925a01863eaa55b0398196fa. Durante las ejecuciones los ocho módulos QA eran archivos nuevos no tracked, congelados con SHA explícitos. El commit de entrega sólo los incorpora con evidencia; no atribuye esos archivos al HEAD previo.

Se ejecutaron 30 casos funcionales: 24 canarias SEC literales y seis controles propios. Los oráculos compartidos de servicio usan una Session de lectura con actor explícito, por exigencia de sus asserts; ese montaje no valida el binding de producción. Cuatro casos críticos propios usan factory normal y HTTP conserva autenticación/MFA reales. Una dependencia pytest nueva reemplaza el alias que creaba dos pools: se repitieron sólo los 12 HTTP, observando el engine verdadero y cuatro GUC vacíos. No son doce casos nuevos.

El restore37 nuevo conserva por inversa textual/AST los 75 asserts de restore36 y los helpers históricos. Compara esquema, índice, familias de seguridad, todas las filas, objetos y bytes de referencias; usa backup AES-256-GCM/HKDF y rol no owner/pool1. Añade pending/verificado/ABA, UTC, cuatro restricciones, ausencia de propósito plaintext y consumo único de prueba restaurada con delta exacto de siete campos y un audit.

El primer restore se rechazó por una precondición nueva después del reset histórico real: el actor pending había cambiado SV. Se preservó el fallo y se modificó una única semilla al actor existente cuyo SV1 queda intacto por el helper histórico. No cambió ninguna aserción. La repetición única pasó. Las ocho UUID acumuladas cerraron mediante DROP normal después de cero sesiones; conexión nueva verificó ausencia.

NodeID restauración:
`tests/integration_current37_restore.py::test_revision37_restore_preserves_contact_and_all_revision26_through36_contracts`

Contrato de entorno para CI: aislamiento antes de importar app; `METODOBASE_TEST_MIGRATOR_URL`, `METODOBASE_TEST_POSTGRES_URL` y `METODOBASE_TEST_PG_BIN` sólo en child privado, loopback55483; `METODOBASE_TEST_EVIDENCE_DIR` absoluto, existente y privado. `ACCOUNT37_PRIVATE_LEASES` apunta a leases bajo un directorio privado Temp cuyo nombre comienza `metodobase-account37-author-pg-`. No cambiar TEMP/TMP global: el primitive verifica la raíz Temp auténtica. Datos, basetemp y temporales de backup quedan bajo DACL privada. La primitiva exige receipts beforeCREATE, PID+birthday, OID/owner, cero sesiones y DROP normal; no FORCE. El aislamiento fuente exige todos los módulos web/api/core/config/src/tests/scripts y Base de la WT propia. Los runners archivados requieren adaptar sólo rutas propias; sus salidas cerradas no pueden sobrescribirse.

El measurement heredado conserva etiquetas34 y una suma histórica28; no es el testigo físico actual. El helper ejecutado exige revisión37, 41 ORM/42 físicas, FORCE32, cuatro flags y membership falsos, no owner e índice30 exacto. Ver la proyección etiquetada.

No se ejecutaron UI/Chrome, Redis, VM, proveedores, Actions ni Linux. No se evalúan latencia, capacidad, SLO, RPO/RTO. Los XML fallidos, filas, dumps, ciphertext, claves y configuración permanecen privados con recibos SHA; los XML de éxito y código archivados conservan sus bytes.

Aceptación acotada sobre el replay RAW GitLF 2c0aeebf, árbol f8dce26c:
Bandit1.9.4 produjo 28 hallazgos (6 históricos +22 aprobados), cero pendientes y
cero errores. Lint, sintaxis, seguridad y los nueve negativos reales terminaron
en cero; los seis positivos también fueron correctos. La fase separada de
17 controles WEB92 pasó sin fallos/errores/saltos y con pip check0 antes/después.
Los 1880 archivos RAW, 92 distribuciones WEB, 81 distribuciones de herramientas,
binarios y 157 archivos Node permanecieron quietos.

El entorno de herramientas81 no contiene pip. No se afirma pip check0 o
consistencia pip para ese entorno. No se instalaron ni copiaron dependencias.
El primer productor de recibo falló al final por indexar una lista como dict;
se conserva rechazado. El productor v2 validó versión primero y registró con
fsync START/FINISH y exit de cada uno de los cuatro pasos. Repitió la misma
fuente inmutable; no cambió las herramientas o assertions para obtener el sello.

Originales revisables en Windows:

```text
C:/Users/Consu/AppData/Local/Temp/metodobase-test-ci37-quality-approved-source-private-20261020-v1/source-manifest.json
C:/Users/Consu/AppData/Local/Temp/metodobase-test-ci37-quality-approved-private-20261020-v2/run-approved-quality.py
C:/Users/Consu/AppData/Local/Temp/metodobase-test-ci37-quality-approved-private-20261020-v2/bandit-original.private.json
C:/Users/Consu/AppData/Local/Temp/metodobase-test-ci37-approved-registry-controls-private-20261020-v1/pytest.xml
```

El productor v2 ejecuta, con el Python de herramientas81 existente, los modos
lint/syntax/security de quality.py y verify_quality.py --evidence; con WEB92 se
ejecuta run_web.py --suite registry-controls --replay-manifest. Los argumentos
exactos, fotos, salidas originales y productores están dentro de los ZIP
privados leídos completos. Cada límite DACL se instaló antes de sus payloads.

El recibo enumera nueve paths mínimos de código/datos/atributos para integrar
desde Git RAW, con sus hashes y dependencias ya presentes en Main. El matcher
y la propuesta SECfc08 son literales; el baseline6 no cambió. La aceptación de
este replay no acredita Main posterior V6, release, imagen57, SCA o aislamiento.

La inspección VM separada sólo leyó recursos y cache nativa72. Tras el rechazo
inicial de banner SSH todavía no listo, el segundo intento confirmó espacio,
memoria, cero contenedores y cache exacta. Se pidió apagado QMP normal después
de comprobar birth/exe/argv/nonce y se verificaron PID/puertos ausentes. No hubo
upload, build, SQL, Redis, Chrome, force o limpieza de discos.

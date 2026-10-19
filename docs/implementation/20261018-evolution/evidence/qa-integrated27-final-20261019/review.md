# Gate amplio independiente del candidato integrado 27

Aceptado para el commit `7bde30b1877f3b4471ef5a75c47839ceaec209a9`.

- Serial con cobertura: **2064 aprobados, 1 omitido, cero fallos o errores**, 457.33 s, 3 advertencias existentes.
- Dos workers aislados, orden mezclado con seed `20261018`: **2064 aprobados, 1 omitido, cero fallos o errores**, 180.92 s, 5 advertencias existentes.
- Cuatro fotos conservan los hashes de los mismos **618 archivos** de código, pruebas, recursos y dependencias; los mismos **89 paquetes** instalados y cuatro `pip check` con salida 0. HEAD se mantuvo en el commit indicado durante las cuatro fotos.

Ambos comandos siguen la selección web de CI: `tests --ignore=tests/test_login_desktop.py --ignore=tests/test_desktop_entrypoints.py`. La pasada serial incluye `--cov`, reportes XML y JSON; la segunda usa `--shuffle-seed=20261018 -n 2`. Los comandos exactos y las raíces temporales distintas constan en los dos archivos `*-result.json`. Se ejecutó cada pasada una sola vez.

La única omisión es exactamente `tests.test_object_storage::test_symlink_cannot_redirect_a_private_document`: Windows no concede creación de symlinks en este host. El mensaje exige que Linux CI ejercite esta frontera. No aparecen omisiones nuevas. Las advertencias corresponden a `src.gestor_bd`, TestClient con httpx y `propagate_traces` de Sentry; el segundo worker duplica las dos primeras.

El guard de cobertura aprueba con 100% de líneas y ramas en los tres contratos que evalúa: `core/nutrition_validation.py`, `core/food_catalog.py` y `web/profile_schemas.py`. Esto no afirma cobertura total del producto ni del diario nuevo.

Cada ejecución tiene SQLite temporal propio y el lanzador de aislamiento desactiva proveedores y bloquea sockets externos en Python. Los módulos de integración PostgreSQL no forman parte de esta colección. Las evidencias anteriores de 1813 casos quedan intactas. Los 97 casos Windows de empaquetado y entrypoints, PostgreSQL 27, navegador, Linux, imagen y Actions conservan sus controles separados.

Resumen definitivo: `qa-integrated27-final-source.json`. JUnit, logs, cobertura, guard y las cuatro fotos quedan en este mismo directorio. Este gate no modifica producto, flags Git ni paquetes.

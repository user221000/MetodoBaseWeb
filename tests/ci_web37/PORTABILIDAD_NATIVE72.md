# Autoridad original del contenedor, sin dependencia de ramas locales

`git_recipe.py` autentica un ZIP finito de343384 bytes por SHA256
`62bf62f3dc5ec1be7d6abbe453b79b0004895d5df20943d3400be4aa24491d6b`.
Los21 miembros contienen los frames RAW originales de Git (`tipo longitud\0payload`).
Cada SHA1 se vuelve a calcular con el tipo y la longitud canónicos. Los dos commits
originales son72c44a1834d7bd9803b4b8846c6c87e85a53bfd3 y
cd423ab0961898ce94fd2574cb4d6452cf8338b3. No se reconstruyen ni importan objetos,
no se añaden padres y no se presume que72c pertenezca a la historia de Main.

La prueba recorre las rutas Merkle desde el árbol que figura en cada commit.
Incluye los nueve inputs nativos originales, Docker original y su lock histórico
de53 distribuciones, más el lock web57 y los árboles de `tests/ci_google33` del
baseline. Los blobs de los verificadores33 no se duplican: sus IDs originales
autenticados permiten comparar el conjunto exacto y cada archivo actual.
Los padres del commit y los hijos de árboles ajenos a estas rutas no se necesitan.
Se rechazan objetos sobrantes, ausentes, duplicados, mal tipados o no alcanzables.

`container_inputs.verify()` usa esta autoridad sin lanzar Git y mantiene sin cambios
los12 inputs del candidato57 aprobado34707350afcc810e546cbb668dd63089ec7982ae.
Los pins de origen siguen exigiendo tanto el blob Git como el SHA256 RAW originales.
El lock web se declara LF para evitar diferencias de checkout sin cambiar su blob.

`test_security_container37_portable_peer.py` ejecuta los40 criterios del peer original
23a5bb4637b7443c45342760914ce0887f98e4be desde un testigo RAW cuyo SHA256 es
1eb22aa94088334d12a202ca2376d7da0b5e566795b0cefd765be4b5b679f76e.
No cambia cuerpos, parametrizaciones ni aserciones. Sus adaptaciones explícitas son:

- Lecturas Git originales por rutas autenticadas; el criterio33 compara además el
  conjunto completo y bytes actuales con su árbol baseline, sin depender de8c local.
- Fixture de copia de los12 inputs, sin copiar un puntero `.git` de una worktree.
- Archivo fuente Python por `METODOBASE_TEST_PYTHON_SOURCE_ARCHIVE`, absoluto y
  existente. La función nativa original sigue validando el SHA256 del tar completo,
  los31 miembros y los bytes del backport; nunca se descarga dentro del test.

El peer original sigue intacto. La selección actual utiliza el companion y excluye
su replay literal para no sumar dos veces los mismos40 criterios. El serial847954df
ya iniciado conserva su selección literal anterior y no se atribuye a esta fuente.

Hay17 controles nuevos de autoridad, framing y rutas. El primer gate138 conservó
137PASS/1RED por una canaria propia que supuso un `FROM` literal donde el Docker
original emplea un ARG. Se corrigió a la identidad SHA256 exacta del Docker original;
el siguiente gate138 pasó completo, sin fallos, errores ni skips. Los40 criterios
portables pasaron en ambas fases. Se conservan ambos RAW privados y los92 paquetes,
los157 archivos Node y toda la fuente permanecieron quietos, con pip0/0.

Esto acredita preparación y controles offline de fuente. No acredita un build,
runtime Linux, SBOM/SCA, Actions, PostgreSQL, Redis, Chromium ni aceptación global R05.
La revisión independiente de esta nueva capa portable sigue pendiente.

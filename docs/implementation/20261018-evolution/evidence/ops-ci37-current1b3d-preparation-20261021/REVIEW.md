Preparación actual: 5531 casos web recogidos sin ejecutar fixtures ni pruebas.
Fuente de colección y 29 controles focales:
7759e5283108131358af16a48ed4cf77003562df. El código de aplicación coincide en
Git con Main1b3d/195 y el producto144/59 declarado por Root. Las 483 entradas
Docker COPY usan los bytes Git RAW actuales; los 17 bindings de calidad usan
la alternativa completa authenticated_git_lf ya aprobada. No se ejecutó Bandit.

Contra la colección5257: 5246 identidades retenidas, 285 añadidas y 11 retiradas.
Las únicas retiradas son safety11, transportadas una a una al companion actual;
el puente adjunto conserva nombres/parámetros exactos y los code objects
originales. Las incorporaciones incluyen los 127 casos R30, peerQA33 27,
Native58, controles propios y controles nuevos QA33. Los 43 módulos originales
con fixtures históricas conservan su composición explícita actual37; ninguna
fixture quedó pendiente de revisión. No hay aceptación broad serial ni n2.

Los dos deselect Native son exactos: el canario original de expiración conserva
su resultado RED histórico y se exige su reemplazo V7 más controles entre fases;
el control original unexpired sigue seleccionado. El criterio original22 se
transporta completo mediante el mismo code object, proyectando exclusivamente
alembic.ini y db_bootstrap.py a sus antiguas preimágenes Windows autenticadas.
Los otros20 helpers se leen realmente del host. Se preservan el módulo V7,
manifiesto22, todos los asserts y todos los bytes originales. La cápsula ancla
tres rutas en b21b62c0 mediante siete objetos Git originales, SHA1/tipo/longitud
y recorrido Merkle; no necesita Git, procesos o red durante el assert.

Los 29 controles focales pasaron con IDs exactos, 0 fallos/errores/skips,
fuente/intérprete/92 distribuciones y tres paquetes Node con157 archivos quietos,
pip check0/0. La raíz del productor tenía sólo User/SYSTEM, protegida y verificada
antes de payload. Se cubren byte alterado del host/preimagen/cápsula, case o ruta
desconocida, manifest/test alterados, conservación del code object y rechazo de
companion omitido o duplicado. La procedencia Root de Native y QA33 permanece
separada de esta preparación de CI.

Después de la colección se añadió únicamente la regla existente de Main
`* -text` al atributo de fixtures, conservando las tres reglas finitas nuevas.
La unión no cambió ningún byte presente, criterio ni selector. Main debe conservar
esa regla y no sustituirla por las tres reglas nuevas. El diff mínimo tiene123
rutas no-doc:121 nuevas CI/tests y dos existentes (workflow y atributo de
fixtures). No incluye cambios nuevos de producto. El workflow aún sólo elimina
Desktop; su conexión actual37 completa se entregará en un commit posterior.

El runner serial está preparado; requiere la cesión de recursos de Root tras
PG53 y fuente inmóvil durante todo el gate:

```powershell
& 'C:/Users/Consu/AppData/Local/Temp/metodobase-google33-author-aamidzkr/venv/Scripts/python.exe' -B -X utf8 tests/ci_web37/run_web.py --suite serial --private C:/Users/Consu/AppData/Local/Temp/metodobase-test-ci37-current-final-serial-private-20261021-v1 --output C:/Users/Consu/AppData/Local/Temp/metodobase-ci37-current-final-serial-public-20261021-v1
```

Para un replay aislado, materializar primero el commit final con replay.py y
pasar su manifest a --replay-manifest. El serial calcula cobertura/risk gate;
n2 usa --suite parallel con semilla20261018 y requiere una lease posterior.
Estimaciones: serial50-65min/0.8GiB adicional/1GiB disco; n2 30-45min/1.5GiB
adicional. No ejecutar n2 junto a PG, Chrome, VM o Redis. El historial35 y las
fases R05 originales60+48+15 mantienen comandos separados obligatorios; su
aceptación independiente previa123 no se vuelve a atribuir como runtime actual.

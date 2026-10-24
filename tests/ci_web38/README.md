# Composición SQLite actual38

Estos proveedores se activan sólo con `-p tests.ci_web38.composition
--web38-current-fixtures`. No retargetean las recetas ni los fixtures37
históricos. La tabla de bindings conserva las43 entradas anteriores completas y
añade31 namespaces actuales; no es un conteo de casos ejecutados.

Se clona únicamente el namespace seleccionado: cada objeto original `test_*` o
`Test*`, sus aserciones y sus globals originales permanecen idénticos. Sólo se
sustituyen los fixtures enumerados y se verifican sus nombres/proveedores y el
SHA completo del módulo original con el transporte LF explícito existente.
El mapa incluye los consumidores account37/B19/B13/R07/R30, los dos módulos nuevos
de contraseña ya enlazados al compañero38 y los dos módulos de origen38.

Todos los nuevos proveedores ejecutan la cadena Alembic real hasta
`20261023_product_facts`, exigen el target38 de `schema_control`, comparan los
nombres físicos completos con Base+alembic_version y comprueban foreign_key_check.
No hay create_all, stamp, fallback37 ni skip ante un target ausente. Los targets
SQLite/PG38 siguen pendientes de captura/revisión Root: preparar estos archivos
no prueba su existencia ni acepta una migración.

`recipes.py` conserva las selecciones, ignores y deselects históricos. Sólo cambia
el plugin de composición y su flag; reutiliza el filtro web/journal original37.
No añade exclusiones para ocultar fallos del producto38. El runner37 mantiene su
guard de head37 y no debe usarse como runner38. La derivación del runner y una
colección independiente con sus identidades/bindings son el siguiente paso antes
de una ejecución broad38. La futura invocación aislada usa los selectores de
`tests.ci_web38.recipes.CURRENT_RUNTIME_SELECTORS`, no tokens editados a mano.

Los oráculos PG/Native/Node e historias de migración siguen en sus contratos
propios; este paquete no los transforma ni los ejecuta. Los nuevos casos
`integration_product38_concurrency.py` requieren una composición PG38 separada.
La fuente raíz conftest conserva el contrato histórico unit/API basado en
metadata; no se cuenta como testigo de migración. En este sparse worktree falta
materializar ese archivo raíz antes de ejecutar broad: no hay fallback implícito.

Estado de esta entrega: sólo generación de fuente, compilación y comparación AST/
bytes. No hubo importaciones del producto, colección pytest, fixtures, SQL ni
servicios durante la ventana serial98362. Las evidencias de preparación viven
fuera del repositorio y no sustituyen resultados posteriores de Root.

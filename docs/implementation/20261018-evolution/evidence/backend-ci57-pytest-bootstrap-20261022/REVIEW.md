# CI57: arranque privado de unittest bajo pytest

Base de autor `f766a09d1bad9ad74c1614a1d5232b18cf7d78e5`.
El RED de Root en Main `d99c80bcdf5262f2ea63f1428fd0be5d1c00292d`
es un caso real de pytest: test05 llega a `directory()` con ARTIFACT=None y
falla con TypeError. Su XML y log se conservan en el privado original E;
el sello registra sus hashes sin reescribirlos. No es un error de Docker.

El delta sólo añade import tempfile y un setUpClass a Offline57. Cuando no
existe ARTIFACT, crea un TemporaryDirectory vacío y un hijo nuevo mediante
la autoridad privada existente, antes de que los tests escriban payloads.
Unittest registra cleanups incluso ante fallo posterior de setUpClass.
Los globales ARTIFACT/SERIAL se restauran antes de limpiar el árbol temporal
propio. No altera el estado del CLI que ya recibió un artifact-root explícito.
El CLI conserva su validación y su bloque main exactos; el llamador sigue siendo
responsable de aportar una raíz apropiada. En esta tanda la raíz CLI es privada.

Los 18 métodos, sus aserciones, el helper directory y el bloque __main__
conservan sus bytes y AST. Una inversa completa retira únicamente el import
y el nuevo método. No hay ignore, skip, cambio de expectativas ni autenticidad
simulada de una imagen. Tres controles nuevos prueban privacidad previa al
payload, restauración/limpieza, fracaso real de setUpClass y preservación de
la raíz explícita; no son otros 18 criterios diferentes.

Resultados de autor, fases separadas:

- pytest real mediante tests/run_isolated.py: 18/18, sin fallos, errores o skips.
- CLI con raíz privada E nueva: los mismos 18/18, sin fallos o errores.
- Controles nuevos del bootstrap: 3/3.
- 117 fuentes observadas y 92 metadatos de distribución estables; pip check0/0.

TEMP/TMP/TMPDIR y cachés se fijaron a E antes de iniciar Python web92 E.
Los payloads/RAW permanecen bajo DACL privada verificada por el helper canónico.
No se ejecutó Docker, imagen, SQL, VM, servicio ni gate amplio. No se modificó
MAIN, fuentes anteriores, C ni instalaciones. La limitación temporal de pytest
se arregla localmente; la revisión independiente y la integración son posteriores.

El primer sellador rechazó correctamente publicar la preimagen completa porque
el test18 original contiene un literal negativo que el scanner excluye. La
preimagen queda en el ZIP privado con su SHA, disponible también por el blob
f766/d99c idéntico. El sucesor conserva las proyecciones ya iguales y no publica
ese RAW; no se cambió el scanner, el test ni su resultado para publicar el sello.

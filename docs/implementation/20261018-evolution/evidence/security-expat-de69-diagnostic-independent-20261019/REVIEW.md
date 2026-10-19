# Expat DE69: confirmación independiente offline de OPS12 y OPS13

Se autentican la fuente/manifest congelados del diagnóstico nativo DE69, sus 66 primarias y los 18 outputs del tar de 911360 bytes. Se comparan bytes retenidos, sin ejecutar ELF, importar extensiones, compilar, usar VM, PG, Chrome o proveedores. El exit0 nativo y sus seis smoke checks siguen siendo observaciones del autor; no una ejecución ni aceptación independiente.

OPS12 confirmado: el build-provenance.json real contiene compiler_commands vacío. Los AST de las fuentes instaladas de setuptools84 muestran que _compile y link llaman directamente self.call; el hook de DE69 intercepta compiler.spawn y por ello no observa esas llamadas. La función spawn instalada es a su vez un wrapper de call. No se reconstruyen argv históricos con sysconfig, nombres de objetos o logs.

OPS13 confirmado mediante un parser ELF64 propio en Python: la base exporta sólo PyInit_pyexpat; DE69 exporta 93 símbolos, 92 añadidos y ninguno retirado. Incluye XML_SetHashSalt16Bytes y dos símbolos de implementación globales. DT_NEEDED contiene sólo libc.so.6 y no hay RPATH/RUNPATH. Se rechazan tres controles malformados del parser. La mayor superficie de símbolos es una diferencia concreta respecto a la base, sin afirmar explotación o una segunda copia de Expat cargada.

Los 31 hashes de fuentes anteriores al backport corresponden al tar PSF fijado, ya autenticado por firma en la revisión independiente estática anterior. Namespace y config seleccionados son idénticos al mismo tar, y sólo xmlparse.c cambia en el manifest posterior. El Makefile instalado conserva -fvisibility=hidden mediante CONFIGURE_CFLAGS_NODIST→PY_CFLAGS_NODIST→PY_STDMODULE_CFLAGS; PY_CFLAGS público no lo contiene. Esto fundamenta seleccionar sólo visibilidad, sin reconstruir el comando original ni añadir PGO/LTO.

El primer control de Makefile comparaba la variable sin expandir y falló por preparación. Se conserva su driver y SHA; el v2 expande las referencias como texto, sin ejecutar make. Los 25 controles finales incluyen autenticación, comparaciones y tres negativos de parser; no representan 25 criterios nuevos del producto ni reemplazan el build futuro.

Resultado: CONFIRM_OPS12_OPS13_OFFLINE_ARTIFACT_REVIEW. El siguiente sourcefix y su compilación requieren revisiones separadas. SEC10, SEC09, runtime54, OS71, SCA, tests de producto y operación real no quedan cerrados. Los artefactos nativos y los proofs históricos permanecen intactos.

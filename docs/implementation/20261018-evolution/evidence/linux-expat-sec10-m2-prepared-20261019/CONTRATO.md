# SEC10: backport de capacidad en Expat embebido

Candidato M2 sobre c02. Fuente PSF 3.12.15 exacta y firmada, Expat 2.8.5, más los cinco renglones upstream de `13c5f63a7f1c52c2feee3b16a1134d4fb68e9ea0` en XML_ParseBuffer. No cambia ninguna macro de versión. Los hashes de origen, destino y diff están en source-pins.json.

M1 evaluó la release actual 2.9.0. Se conserva el preview fallido: retiró xcsinc.c y añade API de propiedades/contadores64, elimina XML_ATTR_INFO y requiere revisar namespace/exportaciones e integración. Para el alcance focal SEC10 se elige el backport exacto autorizado, conservando headers, expat_config.h, pyexpatns.h y C API.

`_elementtree` no incorpora otro Expat: importa pyexpat.expat_CAPI, comprueba magic/size y MAJOR/MINOR/MICRO, y llama Parse por esos punteros. Al conservar exactamente el header/layout y 2.8.5, se conserva su ELF original. La corrección se recompila en pyexpat y sus tres fuentes Expat con el compiler helper de setuptools84, configuración/headers de la misma base, arquitectura64 y SOABI/EXT_SUFFIX exactos. Se verifican antes/después interpreter, libpython, _elementtree, pyconfig, Makefile y todos los headers instalados. No se recompila el intérprete ni se introduce libexpat sistema.

El build vive en una etapa heredada del builder d038 ya fijado. No instala paquetes extra ni descarga dependencias transitorias: utiliza pip26.2.1/setuptools84 existentes y su SCA sigue pendiente, incluidos vendors/ensurepip. Sólo copia al runtime pyexpat y sus pruebas/procedencia/SBOM/licencia. El contador esperado permanece54, con las mismas dependencias de aplicación.

Antes del build: revisión independiente de patch, fuente/firma/hash, guardas del helper y delta Docker. Durante la futura ventana Linux: compilación, trazas de argv/compiler/sysconfig, ELF64/linkage, seis casos pequeños de pyexpat/ElementTree y rechazo read2049 sobre buffer2048. No se llama XML_ParseBuffer con tamaños nativos incompatibles ni se ejecutan PoC de crash/hugeRAM. Después: pruebas stdlib acotadas y XML-related del producto elegidas sobre fuente final, inventario/54 exactos, SCA runtime/build y OS sin ignores. Los seis smoke checks del builder no sustituyen esas suites.

El SBOM conserva versión2.8.5 con pedigree del commit/diff backport y hash del ELF real cuando exista. Un scanner puede seguir coincidiendo por versión; se documenta el patch, sin ocultar coincidencias ni añadir excepciones. Actualmente no se compiló ni se reparó imagen alguna. SQLite50812, zlib27171, OS71 y SEC09 siguen abiertos.

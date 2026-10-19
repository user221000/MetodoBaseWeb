# Windows desktop: preparación de runtime corregido

CPython3.12.15 x64 procede del release inmutable20261013 de python-build-standalone del proyecto Astral; SHA/API/checksums coinciden. Se extrajo en Temp con validación de rutas y tipos, sin ejecutar instalador ni modificar PATH, registro o entornos anteriores. OpenSSL3.5.9 y Expat2.8.5 inspeccionados. No se acredita firma del artefacto.

Entorno nuevo:83 paquetes instalados con hashes y sólo wheels; incluye pip26.2.1. OSV sobre inventario efectivo83:0 coincidencias, pip check0. Fuente dd987:45 pruebas desktop soportadas y97 de receta/entrypoints nativos Windows, todas sin skips/fallos/errores.576 fuentes y83/89 paquetes target/herramienta estables. No se suman a la regresión SaaS2360.

Esto no es un nuevo bundle/ZIP/Setup ni una auditoría CVE de DLL nativas. Los artefactos históricos con3.12.13 se conservan. Reconstrucción, revisión independiente del payload e instalación siguen pendientes. El archivo de46MB y entornos están sólo en Temp; el ZIP conserva metadatos oficiales y runners RAW. La foto completa de fuentes queda privada; el resumen conserva su agregado.

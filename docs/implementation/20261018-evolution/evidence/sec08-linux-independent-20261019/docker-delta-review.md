# SEC08/R18: hito independiente Docker/bootstrap

Se acepta para integración local únicamente el delta Dockerfile + requirements-container-bootstrap.lock de bc365c1 sobre a753b2c. No se acepta el estado global del sistema operativo: permanecen 164 entradas y 71 IDs, incluidas 44 entradas HIGH, sin ignores ni aceptación de riesgo.

La revisión rehashó los 197 archivos de evidencia inicial y los 53 del candidato; ambos manifiestos coinciden y los únicos archivos fuera de cada inventario son el propio manifiesto y su checksum. Se verificaron por bytes el índice, manifest amd64, config y referencia oficial de la base CPython3.12.15. La base común aplica pip26.2.1 con wheel hash antes de deps/runtime; el lock instalado coincide. No se modifican los locks de aplicación/Windows.

El APT del Dockerfile usa repositorios Debian trixie/updates/security con keyring explícito, sin repositorio inseguro ni AllowUnauthenticated. La evidencia retenida registra update/download correctos, metadatos del paquete de309696 bytes y SHA fijada, build con comprobación OK y versión instalada5.8.1-1+deb13u2. El inventario de87 paquetes cambia exclusivamente liblzma5. El revisor comprobó esta evidencia; no volvió a construir ni ejecutar APT/firma.

La comparación independiente confirma que el scanner y DB son los mismos y el ignore está vacío. Sólo desaparecen DSA-6549-1 y TEMP-1147318-639065 (aliases del arreglo XZ); los seis campos VulnerabilityID/PkgName/InstalledVersion/FixedVersion/Status/Severity de las164 entradas restantes coinciden. Los objetos completos cambian Fingerprint en164 y PkgIdentifier en3; no se afirma igualdad byte por byte de esos objetos.

USER appuser y UID999 están comprobados en la ejecución retenida. read-only rootfs, cap-drop ALL, no-new-privileges y network none son opciones de aquel laboratorio, no defaults del Dockerfile. La imagen conserva utilidades SUID que requieren revisión operativa; UID no prueba por sí solo su contención. La aceptación no comprende arranque de aplicación, PostgreSQL, despliegue, otras arquitecturas ni desktop.

Continúa una revisión separada de aplicabilidad por ID y medidas concretas, manteniendo el rojo original. No se ejecutaron builds, auditorías, aplicación, invitados ni servicios en este hito.

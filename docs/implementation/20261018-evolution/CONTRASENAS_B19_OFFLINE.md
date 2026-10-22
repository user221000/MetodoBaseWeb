# Contraseñas nuevas: blocklist offline B19

El validador compartido `web/account_values.py::validate_new_password` conserva mínimo12caracteres y máximo72bytesUTF-8 y compara la contraseña completa con el corpus offline. Registro, aceptación de invitación, recuperación y cambio autenticado ya llaman a este validador; login de credenciales existentes y lecturas no lo consultan. No hay comprobaciones de substrings, trim, casefold, normalización Unicode, reglas de composición adicionales ni consultas externas con contraseñas o hashes.

El rechazo por corpus ausente, truncado, alterado o sobredimensionado falla cerrado con un `ValueError` fijo y sin reflejar candidato/ruta. Los adaptadores conservan sus rechazos400/422. En SaaS, un wrapper finito del router de invitación evita que el error de validación Pydantic refleje password/token/input/contexto; sólo captura `RequestValidationError` de POST `/api/auth/accept-invite` y su alias de una barra. No cambia BrowserAuthRoute/MFA ni otros contratos de rutas. API no expone los routers de equipo, igual que antes: se comprueba404 explícito y no se afirma paridad de invitación entre factorías.

## Procedencia y distribución

Fuente pública [SecLists Common-Credentials100k](https://github.com/danielmiessler/SecLists/blob/c205c36a445bff37f8e58a9ec829105cd4975c58/Passwords/Common-Credentials/xato-net-10-million-passwords-100000.txt), commit `c205c36a445bff37f8e58a9ec829105cd4975c58`. Sólo se descargaron el archivo exacto, su [LICENSE MIT](https://github.com/danielmiessler/SecLists/blob/c205c36a445bff37f8e58a9ec829105cd4975c58/LICENSE) y metadata pública de su commit. No se descargó ni ejecutó el repositorio.

| Entrada | Bytes | SHA-256 |
|---|---:|---|
| Archivo fuente100k |781879|`1472aafa2561df5e3293aee252aee3ca660c12b399a283cf808bb01b39be388b`|
| LICENSE |1072|`3dbdc93d5f8829de0941744841730a09c106d0732e5ae0e98ca1d77be7ded66c`|
| Corpus distribuido |3199968|`d0d787734cd3ad38731ca3012e34532ff109e915feeb152cbf0fbd361c27c101`|

`web/data/password-blocklist/` contiene el corpus, manifest de procedencia y licencia íntegra. El corpus concatena99999digests SHA-256 de32bytes únicos y ordenados lexicográficamente. No contiene contraseñas en texto ni hashes de usuarios de este servicio. La entrada vacía de la fuente se omite porque el mínimo existente ya la rechaza. Docker ya copia `web/` y no excluye estos archivos; un atributo local preserva bytes binarios y LF del manifest/licencia. No se ha construido ni validado una imagen nueva por este cambio.

Cada validación lee como máximo3199969bytes, exige tamaño exacto y SHA-256 pinneado en el lector y realiza búsqueda binaria del digest de los bytesUTF-8 completos. Se verifica de nuevo en cada llamada, incluso después de un uso correcto anterior. No hay cache que acepte una copia alterada posteriormente. El manifest documenta procedencia y no sustituye el pin del código.

## Regeneración y actualización

La actualización es una revisión de código/datos, nunca una descarga en runtime. Guardar el archivo público exacto fuera del repositorio, comprobar su SHA/tamaño y licencia, dividir únicamente porLF y retirar elLF final. Comprobar100000líneasUTF-8 y ausencia deCR; omitir únicamente su entrada vacía, calcular SHA-256 de cada entrada completa sin transformar sus bytes, eliminar digests duplicados, ordenar y concatenar. El resultado debe coincidir con el pin anterior para una reproducción. Una fuente nueva requiere commit/URL/SHA/licencia, manifest y constantes revisados conjuntamente, controles de frontera y revisión independiente antes de entrega. No persistir el corpus plaintext ni contraseñas de solicitudes en evidencia pública.

La selección es una lista acotada de contraseñas comunes conocidas, no una base exhaustiva de todas las filtraciones ni garantía de fortaleza de una contraseña ausente. [NIST SP800-63B §3.1.1.2](https://pages.nist.gov/800-63-4/sp800-63b.html#passwordver) sustenta comparar el secreto completo al establecerlo/cambiarlo. Este cambio no afirma conformidad NIST completa, no cambia el mínimo12existente ni añade rotación periódica forzada de contraseñas.

## Validación y límites

Los canarios iniciales preservados prueban3RED reales antes del cambio: validador y registro HTTP de ambas factorías. Un intento previo1F/2E por sparse API incompleta se conserva como fallo de preparación. El primer gate de45casos produjo33PASS y12fallos del harness nuevo (Subscription sintética ausente/campo de snapshot equivocado), sin atribuirlos a política. Ambos se corrigieron en pruebas propias manteniendo los RAW. El focal posterior reprodujo1RED de reflexión Pydantic en invitación SaaS y1control de cambio con MFA PASS, antes del wrapper finito.

La selección final incluye corpus íntegro/orden/licencia, comparación completa y UTF-8 sin modificar, fallos de archivo, cero intento de socket, registro/reset/cambio reales en ambas factorías, invitación real sólo SaaS y404de API existente. Los rechazos conservan hash/SV/rol/tenant, refresh, prueba primaria, factor y enlaces/tokens; el mismo recurso válido permite reintentar con contraseña fuerte. MFA se enrola y reautentica realmente en el fixture actual37SQLite; proveedores son dobles sin correos reales. Se conserva compatibilidad de login de una contraseña existente incluida en corpus.

Resultado autor:51casos nuevos PASS y7regresiones originales PASS en2fases, sin fallos/errores/skips; fuente congelada `c12263718ab1255727330037055f5fcfb53a98be`. Fuente10archivos,92RECORD del entorno y ejecutable Python permanecieron idénticos antes/después. Ruff completo de3archivos nuevos y controles críticos de5modificados:0. El lint completo de los módulos históricos no se presenta como limpio; no se reescribieron sus diagnósticos ajenos a este cambio. Hashes y NodeIDs figuran en `evidence/backend-b19-offline-password-20261021/`.

Se necesita revisión independiente posterior; no se ejecutaron PostgreSQL, Chrome, Redis, VM ni fullscan y no se atribuyen Native35/PG53 anteriores a esta fuente nueva. B19 completo conserva sus restantes validaciones operativas de correo/custodia fuera de este cambio.

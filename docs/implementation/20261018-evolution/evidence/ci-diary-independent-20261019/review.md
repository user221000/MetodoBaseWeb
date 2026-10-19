# Revisión independiente del cableado CI del diario

Aceptado localmente para `8435bd079ef5a48c081043ebe8efe542278143c4`, basado en `7bde30b1877f3b4471ef5a75c47839ceaec209a9`.

El verificador congelado se reprodujo en un directorio temporal nuevo con el Python candidato: **162 contratos Node únicos, 21 canarios CLI de reportes, 8 de startup, 13 escenarios Bash inertes y 15 casos de origen**. Los 61 bloques Bash pasan sintaxis y existen las 82 referencias. Los seis llamados previos mantienen su orden y contenido; jobs PostgreSQL, desktop y demás jobs ajenos al delta conservan su estructura. El guard frontend y sus pruebas no cambian; no se repiten sus 91 canarios antiguos.

Se añadieron controles propios:

- **12 canarios CLI de startup**: archivo ausente, UTF-8 inválido, salud sin marker, JSON embebido/nested/array, tipos erróneos, revisión ausente y duplicados conflictivos. Un marker válido rodeado de logs ordinarios se acepta; un marker de otra fixture no sustituye al requerido.
- **21 casos de origen**: solo default 8777 y las cadenas canónicas exactas 8776/8777 se aceptan. Variaciones de normalización, credenciales, delimitadores, espacios, controles y otro puerto se rechazan antes de crear salidas. Se ejecuta solo el preámbulo congelado, con límites explícitos de filesystem y browser; no hay navegador ni red.
- **10 escenarios propios con el cuerpo Bash exacto**: salud 200 sin marker no inicia drivers; el marker demorado permite ambos drivers después de su aparición; otra fixture, head o tabla no pasan. Fallar el segundo driver incluso después de escribir un reporte válido, omitir/vaciar el reporte, incluir errores de página o perder la fixture entre drivers impide éxito. En todos se comprueban el mismo PID, una limpieza y que el proceso inerte propio ya no existe después.

Las cuatro aserciones browser del exportador conservan su cuerpo desde `const report=` respecto del baseline; solo se parametriza y restringe el origen. La secuencia compartida de dos drivers se prueba con procesos inertes y guards CLI reales. No fue necesario repetir las 25 pruebas reales de navegador aceptadas para la UI: su evidencia conserva un alcance separado.

Las fotos antes y después conservan los hashes de **275 archivos versionados y de evidencia**, incluidos los 6 archivos del cambio y las 81 dependencias declaradas por el autor. Los 89 paquetes instalados conservan nombre y versión; ambos `pip check` pasan. El worktree del autor termina sin diff tracked y no hay cambios en producto `web`, `api` o `core` respecto del baseline. No se toca MAIN producto, ningún listener 8776/8777, flags Git ni commits.

Resumen: `ci-diary-independent-source.json`. La repetición original está en `author-verifier-replay/`; los canarios propios, logs y scripts quedan en `own/` y archivos adyacentes. Esta revisión usa Windows y Git Bash local; no acredita Actions, Linux nativo, ejecución de aplicación, migraciones, PostgreSQL ni proveedores externos.

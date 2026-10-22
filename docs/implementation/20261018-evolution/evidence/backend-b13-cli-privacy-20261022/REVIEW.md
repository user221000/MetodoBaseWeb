# B13: argumentos CLI sin reflexión

El parser por defecto convertía int/float y emitía el valor inválido en stderr antes de alcanzar el manejador opaco. SEC conservó dos RED y un control help en su fuente63dc, con custodia independiente. El cambio añade únicamente una subclase de ArgumentParser cuyo error produce un ValueError fijo y mueve parse_args dentro del try existente. Los errores de entrada retornan64 y JSON fijo sin stderr; help mantiene SystemExit0 y uso visible. No cambia el servicio, los callbacks SDK, locks, selección, cuotas ni cleanup.

Los seis controles autor se preservan idénticos entre antes/después: entero inválido, float inválido, opción desconocida, valor faltante, argumento obligatorio faltante y help. Antes:5RED+1controlPASS en e19 con el archivo nuevo; después:6/6PASS en fd77167166b85b1fd15816692752ff7eed84c26c, cero errores/skips. Los tests prohíben importar servicio/SQLAlchemy/proveedores o abrir archivos durante el parseo y comprueban salida/logs. Son valores sintéticos. El archivo literal SEC no se edita; su replay3 queda a cargo del peer.

Seis fuentes, intérprete WEB92, sus92 RECORD y el binario Node quedaron iguales durante la fase final. Ruff completo del CLI y archivo nuevo pasó sin diagnósticos. RAW/JUnit previos y finales, snapshots exactos y Git, metadata y canario SEC original permanecen en un ZIP privado con DACL2 antes de payload y readback integral.

No se repiten ni reatribuyen autor63/Root10/SEC7 de fuentes previas por un cambio sólo del parser. Replay literal SEC3, gate Root integrado, PostgreSQL actual, CI amplio/imagen/despliegue y operación real siguen pendientes; no hay llamadas reales a proveedores ni SQL externo. Este recibo no cierra B13 globalmente ni modifica el registro Main.

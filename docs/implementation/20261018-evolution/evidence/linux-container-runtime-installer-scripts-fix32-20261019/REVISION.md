# Guarda del padre de scripts antes de la limpieza runtime

Corrección focal del Dockerfile sobre `af548f71a8a763ba523853e85903a9ab8cf2b0a7`. Sólo cambia la precondición Python que precede a todos los comandos de eliminación. Los doce locks permanecen idénticos por bytes; no cambia la aplicación, el inventario esperado de 54 distribuciones ni las rutas fijas de limpieza.

Se añade `scripts = Path('/usr/local/bin')`, se exige que `sysconfig.get_path('scripts')` corresponda a esa ruta y se comprueba que el padre sea un directorio, no un symlink y resuelva a sí mismo. Así se rechazan tanto un destino scripts inesperado como un alias del padre. No se observó un alias real en la imagen: se corrige la garantía de la guarda a partir de casos controlados.

El driver independiente original `test_runtime_installer_paths.py`, SHA256 `67388a1948844492550986f63fb9eab776c8b86a92a94ccf5be26adc81e630f4`, se copió sin cambios a Temp propio y se ejecutó con imports controlados, plugins pytest desactivados y fuera del conftest de producto. Antes: un positivo aprobado y dos negativos fallidos. Después: los mismos tres casos aprobados. Los logs y JUnit de ambas fases se preservan. Se comprobó adicionalmente sintaxis Bash del RUN y compilación, sin ejecución, de sus dos snippets Python.

El rechazo independiente anterior permanece congelado: `backend-container-installer-static-review-20261019/freeze.json`, SHA256 `cd6cbf607fd161b253b327210b7c2d0b85c21e98eed69a79071b64a7373a3bab`. No se modificaron af548 ni sus evidencias publicadas. La identidad del nuevo commit, el estado limpio, el hash Dockerfile y la comparación de locks están en `freeze.json` y los recibos antes/después.

No se ejecutó la limpieza, ningún instalador, Docker, QEMU, red o arranque del producto. La aceptación de rutas de este harness no demuestra aún el filesystem real de la imagen, la composición exacta de 54 distribuciones o su SCA. La revisión independiente posterior y los gates de imagen siguen pendientes; OS71, SEC09 y SQLite50812 permanecen abiertos.

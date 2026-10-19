# Reparación aislada de empaquetado desktop

Rama `implementation/desktop-packaging-20261019`, worktree separado `F:/MetodoBaseWeb-desktop-20261019`, base `0e8cd42`. Se prepararon receta y pruebas; no se construyó ni lanzó un ejecutable real. El artefacto usará después el commit integrado y congelado que indique coordinación. No se modificaron el original ni el WIP de ejecución, runtime del producto, migraciones, locks web o CI.

## Contrato nuevo

`build.py` requiere `--source-commit` con SHA completo. Comprueba HEAD exacto y worktree limpio, inventaría por hash los archivos trackeados y compara el conjunto antes/después de pruebas y empaquetado. No importa `config.constantes`: lee VERSION por AST, evitando crear perfiles o interpretar variables de producto durante el import del script.

`MetodoBase.spec` analiza `main.py`, conserva PySide6 y produce onedir `dist/MetodoBase` con `_internal`. Declara fuentes, recursos gráficos y QSS como archivos individuales obtenidos de Git; no copia carpetas de configuración, módulos Python o datos personales como bloques de datos. Limpia variables `GIT_*` antes de inventariar y comprueba la raíz efectiva del worktree. La lista de extensiones y los recursos mínimos son explícitos; faltar un recurso requerido aborta. Los módulos del producto se incluyen mediante el análisis/imports de PyInstaller.

El bundle requiere ejecutable, fuentes/QSS y plugins Qt nativo/offscreen según plataforma. Un manifiesto cubre el conjunto exacto y SHA256 de cada archivo; después de un build guardaría además commit y versiones de herramientas. El ZIP incluye todo el árbol y manifiesto, con nombres POSIX bajo `MetodoBase/`. Rechaza archivos privados, bases, cachés de licencia, directorios de datos/entornos, nombres ambiguos, symlinks y junctions. Verifica también los bytes dentro del ZIP antes de publicar mediante reemplazo de un archivo temporal. Un error conserva el ZIP anterior y elimina el temporal.

La limpieza se limita a `build` y `dist` bajo la raíz seleccionada, con comprobación previa de límites/enlaces. Conserva `.spec`, `__pycache__` y archivos ajenos. Un bundle previo impide inferir éxito de una compilación nueva. Los errores del subproceso y cambios de fuente invalidan el candidato.

`validate_build.py` valida estructura/manifiesto por defecto sin ejecutar nada. `--gui-smoke` selecciona explícitamente un diagnóstico empacado: perfil, datos, cwd y preferencias en un Temp propio, Qt offscreen y comprobante con nonce. El hook crea QApplication, carga Inter/tema e instancia la ventana de login, luego termina antes del flujo de negocio de `main.py`; no activa licencias ni concede sesión. No usa HTTP, `--help` o `--no-browser` como señal de éxito.

Ese hook limita sockets Python y registra `os_network_isolation_verified=false`. No equivale a bloqueo de red del sistema operativo para código nativo Qt. Su primera ejecución real debe realizarse en un entorno de prueba con ese aislamiento ya verificado; no se ejecutó durante esta reparación. Tampoco sustituye los recorridos funcionales, un equipo sin Python o la revisión del puente de licencias.

## Herramientas verificadas

Se consultaron las [opciones oficiales de PyInstaller](https://pyinstaller.org/en/stable/usage.html), su [contrato de specs](https://pyinstaller.org/en/stable/spec-files.html) y los metadatos primarios de [PyInstaller 6.22.3](https://pypi.org/pypi/pyinstaller/6.22.3/json) y [hooks 2026.8](https://pypi.org/pypi/pyinstaller-hooks-contrib/2026.8/json). El spec expresa onedir mediante EXE/COLLECT, sin UPX; conserva BUNDLE adicional en macOS. La rueda Windows AMD64 publicada de PyInstaller tiene SHA256 `500bd58c7bf7e584a8435adccbd763a0b918d5c12b08d74ff50fd79b2915458b`, incluido en el lock.

`requirements_build.txt` contiene sólo PyInstaller y hooks fijados. `requirements_build.lock` resuelve transitivas y hashes con marcadores de plataforma; ya no instala runtime sin hashes ni contradice el pytest del target desktop. Se instaló exclusivamente en `Temp/metodobase-desktop-build-tools-20261019` mediante uv 0.11.26 y Python 3.12.13. Se ejecutaron únicamente versión/ayuda del empaquetador, ninguna Analysis real.

El entorno Windows contiene 7 paquetes: altgraph 0.17.5, packaging 26.3, pefile 2024.8.26, PyInstaller 6.22.3, hooks 2026.8, pywin32-ctypes 0.2.3 y setuptools 84.0.0. pip-audit 2.10.1 ejecutado en otro entorno temporal informó 0 vulnerabilidades conocidas para ese conjunto. Macholib aparece en el lock para macOS; no fue instalado ni auditado mediante este gate Windows. Este resultado tampoco acredita el runtime completo ni futuras bases de vulnerabilidades.

## Pruebas y aceptación

El gate final aprobó **58 pruebas en 6.35 segundos: 51 independientes y 7 de autor**, con 9 archivos fuente estables. Las pruebas usan archivos sintéticos y mocks de los constructores PyInstaller/subprocesos de GUI. Hay Git real en repositorios Temp, una junction temporal y ZIPs reales de bytes inertes; nunca un binario o instalador ejecutable. La revisión independiente añade negativos de datos privados, onedir incompleto, conjunto/hash del manifiesto, mutación transitoria al crear ZIP, lectura incompleta del árbol, limpieza, contaminación Git, commit/dirty/source drift y comprobante de diagnóstico/perfil.

Antes de corregir se conservó el gate con `licencia_config.json` aceptado y otro con error de lectura de árbol omitido. La primera tanda también tenía dos errores de fixture de limpieza, identificados y corregidos sin atribuirlos al producto. La revisión posterior comprobó cada corrección. Evidencia final y hashes: `evidence/desktop-packaging-independent-source.json` y `pytest-desktop-packaging-final-independent.xml`. Las pruebas de estructura Windows/Linux/macOS son sintéticas y no acreditan compilaciones de esos sistemas.

## Alcance que sigue abierto

La ruta reparada es `build.py`/`MetodoBase.spec` y el wrapper `build_all.sh`. **`setup.py`, `build_config.py`, `build_all.bat`, el launcher portable, README histórico y `setup_installer.iss` permanecen fuera de este cambio**: todavía contienen recetas o instrucciones divergentes; no se deben presentar como pipeline unificado aceptado. El ISS requiere revisar conservación de datos, versión y arquitectura antes de compilar/ensayar. No se instaló Inno Setup ni se inspeccionaron certificados.

Windows necesita build real, diagnóstico empacado con aislamiento, recorridos de aplicación sin Python y prueba del instalador. Linux conserva su receta nativa y requiere build/Qt real en Linux. macOS conserva el BUNDLE nativo; sus frameworks usan enlaces y su archivo `.app`, DMG, firma/notarización y semántica de ZIP necesitan revisión nativa separada. El ZIP seguro actual está definido para el directorio onedir y no promete empaquetar un `.app` con enlaces. No se reducen estos pendientes a un pase sintético en Windows.

Para la siguiente fase, coordinación integrará la receta, congelará el commit y aprobará el destino del ensayo. Se creará un entorno temporal con el runtime desktop correspondiente y el tooling fijado, se repetirá su gate de fuentes y entonces se invocará `build.py --source-commit <SHA-integrado> --zip`. El diagnóstico real, compilación/instalación Inno y firma/publicación son verificaciones posteriores separadas. Las licencias legacy y su puente remoto siguen bajo `LICENCIAS.md`, sin cambios de derechos.

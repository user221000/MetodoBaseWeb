# Desktop: inventario y preparación de publicación

Revisión de sólo lectura sobre el checkout de ejecución, con referencia inicial `0e8cd42`. El original permanece intacto. No se inició la aplicación, activación, consulta remota de licencias, empaquetado ni instalador. Sólo se escriben este documento y `evidence/desktop-publication-readonly-source.json`. La revisión no acepta una publicación desktop ni extiende el smoke anterior al head actual.

## Contrato observado

`main.py` inicia una aplicación PySide6: fuentes Inter, tema, splash y FlowController; el recorrido gimnasio continúa por autenticación, configuración, licencia y GymAppWindow. Su alternativa sin PySide6 pide datos en consola. No implementa un modo `--help` ni el servidor HTTP esperado por algunos scripts históricos. Importar configuración puede crear directorios de datos, por lo que esta inspección usó lectura/AST y metadatos de paquetes, sin importar producto.

`setup.py` y `build_config.py` seleccionan `main.py`, nombre `MetodoBase`, modo windowed y directorio onedir. El resultado esperado es `dist/MetodoBase/MetodoBase.exe` junto con sus dependencias `_internal`. Los datos incluyen assets, fuentes, configuración, módulos y estilos desktop; ambas recetas difieren: `build_config.py` incluye además `static` y `api`. Los hidden imports cubren Qt, autenticación, criptografía y ReportLab, pero falta verificarlos en un ejecutable real.

`config/constantes.py::VERSION` y `setup_installer.iss` coinciden hoy en `2.0.0`; la versión del instalador está duplicada como literal. Inno conserva AppId `8A2F4E7B-3C9D-4B1A-A5E6-7F8D9C0B2E3A`, instala en `{autopf}/Método Base`, requiere administrador, usa español y copia recursivamente `dist/MetodoBase/*`. Produce `Output/MetodoBaseSetup_v2.0.0.exe`, crea accesos y ofrece iniciar la aplicación. El script no declara restricción de arquitectura ni firma de código.

Los datos efectivos se resuelven por `METODOBASE_DATA_DIR`, o en Windows por `%APPDATA%/MetodoBase`, con subdirectorios `config`, `registros` y `planes`. El desinstalador elimina carpetas homónimas bajo `{app}`; esto no demuestra conservación de instalaciones antiguas que hayan usado esa ubicación. Upgrade, desinstalación y reinstalación requieren ensayo con una copia sintética y respaldo previo, sin tocar datos del usuario.

## Herramientas disponibles

| Elemento | Observación local |
| --- | --- |
| Python explícito | CPython 3.12.13, AMD64, 64 bits, administrado por uv |
| uv | 0.11.26; no se instaló ni actualizó nada |
| Venv desktop candidato | Existe en Temp; PySide6 6.8.3, Pillow 13.0.0, cryptography 50.0.2, ReportLab 4.5.1; `qwindows.dll` presente |
| PyInstaller y auxiliares | Ausentes del venv desktop y del venv QA consultados; `pyinstaller` no está en PATH |
| Inno Setup / ISCC | No aparece en PATH, en las tres rutas que busca el batch, en directorios Inno de las raíces estándar ni en los registros de desinstalación revisados |
| Firma Windows | `signtool.exe` no está en PATH; no existe el directorio estándar Windows Kits/10/bin consultado. No se inspeccionaron certificados ni claves |
| Salidas locales | No hay `dist`, `build`, `Output` ni `MetodoBase.spec` en este checkout; tampoco hay un `.spec` trackeado |

Las búsquedas acotadas no afirman que una herramienta sea imposible de encontrar en otra ubicación. `python`/`py` de PATH apuntan a alias WindowsApps, por lo que no deben seleccionarse implícitamente para el futuro build. Los iconos `.ico` referidos por las dos recetas tampoco existen; ambas permiten continuar con un icono por defecto.

`requirements.txt` contiene rangos desktop. Los locks `requirements-test-desktop*.lock` fijan runtime y pruebas con hashes por plataforma; el entorno candidato existente incluye también dependencias API/web. `requirements_build.txt` conserva `pyinstaller>=6.0.0,<7` sin lock y `pytest<9`, mientras el smoke aprobado usó pytest 9.1.1. No existe todavía un entorno de build reproducible fijado ni se resolvió esa diferencia modificando los entornos existentes.

## Evidencia y diferencias pendientes

La evidencia histórica `pytest-desktop-candidate.log` registra **63 pruebas y 7 subtests aprobados en 38.30 segundos**. Su JUnit contiene 70 testcase, 0 errores, 0 fallos y 0 omisiones, con fecha `2026-10-18T19:41:49-06:00`. Cubre login Qt, servicios locales de autenticación/criptografía y generación PDF. El harness configura `QT_QPA_PLATFORM=offscreen`, datos temporales y bloqueo de sockets externos; las ventanas se prueban desde Python con dobles de ciertos servicios.

Esto no ejecuta `main.py` como aplicación empaquetada, no prueba el plugin Qt desde `_internal`, no instala/desinstala ni demuestra compatibilidad en una máquina sin Python. La CI definida exige QApplication offscreen y pruebas desktop en Windows/Linux; no contiene un job de compilación del instalador ni acredita una ejecución remota nueva. El head candidato actual debe volver a pasar sus pruebas desktop tras congelarse.

Se identificaron contradicciones estáticas que deben corregirse antes de usar los wrappers:

- `build.py` pide onedir pero busca `dist/MetodoBase.exe`. Su prueba ejecuta `--help`, contrato que la entrada GUI no ofrece. Su ZIP sólo incluye el árbol completo si recibe un directorio; pasar únicamente el EXE real omitiría `_internal`.
- `validate_build.py` lanza `--no-browser` y consulta un servidor HTTP. Puede saltarse esa verificación si no encuentra requests. No valida el producto PySide6 seleccionado.
- `build_all.bat` borra salidas relativas al directorio actual, ejecuta pytest directamente y llama a `setup.py`. Sus mensajes finales anuncian una versión 1.0.0 distinta de la configurada.
- `build_all.sh` requiere un `.spec` ausente. Su recorrido opcional de ofuscación reemplaza fuentes y no garantiza restaurarlas si falla un paso anterior; no se ejecutó.
- README y `metodobase_iniciar.bat` describen un servidor/navegador y otra ubicación de datos; el launcher además puede instalar dependencias. No constituyen el inicio del paquete GUI standalone actual.

La contención SEC01 conserva licencias locales válidas hasta su propio vencimiento, pero [LICENCIAS.md](LICENCIAS.md) mantiene abierto el puente remoto autenticado y la autoridad HMAC legacy. La gestión de licencias al arrancar captura excepciones antes de abrir GymAppWindow; esta inspección no prueba qué operaciones posteriores permitiría ese recorrido. Debe revisarse y ensayarse sin crear licencias comerciales ni habilitar red real. No se atribuye al instalador una solución a ese contrato.

## Producción del artefacto local después de congelar

1. Trabajar en un worktree separado del siguiente commit aprobado. Registrar commit, árbol y hashes de fuentes; usar únicamente archivos trackeados y datos sintéticos. No incluir `.env`, bases, licencias, respaldos, logs o datos locales del desarrollador.
2. Reparar y revisar la receta única de build, el validador GUI y el ZIP onedir completo en ese worktree; añadir pruebas del manifiesto y de los fallos de empaquetado. Alinear versión, rutas de salida, recursos, instrucciones y limpieza acotada. Fijar PyInstaller, hooks y transitivas en un entorno temporal de build, con hashes y evaluación de seguridad, sin cambiar instalaciones del usuario.
3. Repetir el gate desktop del commit congelado mediante `tests/run_isolated.py`, incluyendo servicios/PDF y licencias offline. Crear el ejecutable onedir con esa receta revisada; registrar herramientas, dependencias, advertencias de PyInstaller y manifiesto SHA256 de todos los archivos. No usar los wrappers actuales sin su corrección.
4. Ensayar el paquete desde una ruta con espacios y fuera del repositorio, con perfil temporal, red bloqueada y sin proveedores: apertura/cancelación, fuentes/estilos, login con datos sintéticos, permisos, historia local y generación/lectura PDF. Añadir recorrido GUI real en una máquina de prueba sin Python; offscreen no sustituye esa comprobación.
5. Obtener un compilador Inno fijado y verificado en un directorio temporal cuando se autorice esa fase. Compilar el ISS contra el onedir probado y comprobar versión/AppId, accesos, rutas y arquitectura. Ensayar instalación, upgrade, desinstalación y reinstalación en un entorno Windows descartable, con usuario estándar y elevación sólo durante instalación; no instalar el candidato en el perfil del usuario actual.
6. Entregar ZIP completo e instalador locales con SHA256, manifiesto de archivos, commit, herramientas y resultados separados. Si todavía no hay firma, registrar el estado sin presentarlo como distribución firmada. Firmar/verificar EXE e instalador requiere certificado y proceso autorizados; no se compró certificado ni se usó un servicio de sellado de tiempo. La publicación externa permanece pendiente de revisión del artefacto concreto.

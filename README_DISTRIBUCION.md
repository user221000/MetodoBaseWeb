# Distribución desktop de Método Base

La aplicación desktop soportada usa PySide6. El paquete onedir contiene `MetodoBase.exe`, `_internal/`, `build-manifest.json` y el launcher Windows. Se debe extraer y conservar **todo el directorio**; copiar sólo el EXE rompe sus dependencias. El cliente no requiere Python instalado en el equipo destinatario.

Este repositorio prepara una receta local. No hay todavía aceptación de un ejecutable, instalador o firma del candidato final. Las pruebas Python, los tests sintéticos de empaquetado y una aplicación instalada son comprobaciones diferentes. Consulte [la preparación desktop](docs/implementation/20261018-evolution/DESKTOP_EMPAQUETADO.md).

## Uso del paquete Windows

El target declarado es Windows 10/11 x64. Después de validar el artefacto, abra `MetodoBase.exe` o `metodobase_iniciar.bat` desde la carpeta extraída. Se abre una ventana desktop; no necesita iniciar un servidor local ni un navegador. El launcher no instala dependencias y sólo comprueba la presencia del EXE, `_internal` y manifiesto; la verificación de hashes corresponde al proceso de entrega.

Los datos se guardan normalmente en `%APPDATA%/MetodoBase`, con `config`, `registros` y `planes`. `METODOBASE_DATA_DIR` permite un destino explícito. Las preferencias de tema usan además el perfil de usuario. No se debe mover ni borrar información de instalaciones antiguas para corregir una ruta. Actualización, recuperación y desinstalación necesitan un respaldo probado y un procedimiento revisado; el instalador preparado conserva los datos locales que no forman parte del payload.

No se necesita ejecutar el programa como administrador para su trabajo diario. La receta del instalador conserva la elevación durante instalación. Una licencia local válida continúa según su propio contrato; la compatibilidad del puente remoto permanece documentada en [LICENCIAS.md](docs/implementation/20261018-evolution/LICENCIAS.md). Este paquete no concede nuevos derechos ni autoriza activaciones remotas de prueba.

## Crear un candidato revisable

Usar un checkout limpio del commit integrado aprobado y un entorno temporal Python 3.12. Instalar el runtime desktop de la plataforma mediante su lock con hashes y, por separado, `requirements_build.lock`. No instalar herramientas globales ni usar requirements genéricos sin hashes como sustituto del entorno aprobado.

La receta única es:

```powershell
& '<python-temporal-verificado>' build.py --source-commit <SHA-completo-integrado> --zip
```

`setup.py build` y `build_all.bat` delegan en esa misma receta y requieren el mismo SHA. Para el batch, fijar `METODOBASE_BUILD_PYTHON` al ejecutable temporal explícito; no busca Python ni compila Inno automáticamente. `build_all.sh` conserva el recorrido nativo Linux/macOS y acepta `METODOBASE_BUILD_PYTHON`. Ningún wrapper reemplaza fuentes, ofusca, borra `.spec` o limpia desde el directorio del llamante.

La procedencia compara los archivos con los blobs del commit, sin confiar solamente en `git status` o las banderas del índice. Sólo admite bytes exactos o la política LF/CRLF documentada; filtros/encodings personalizados y overrides locales de atributos necesitan revisión y se rechazan. Los manifiestos y el ZIP verifican el conjunto completo. No incorporar `.env`, bases, licencias, perfiles o backups del desarrollador.

`validate_build.py --bundle <directorio>` verifica el manifiesto sin lanzar la aplicación. `--gui-smoke` es un diagnóstico optativo con perfil temporal y Qt offscreen: comprueba bindings, fuentes, tema y ventana de login, y termina antes del flujo de negocio. Sus sockets Python se bloquean; no es aislamiento de red OS ni una prueba completa de producto. El diagnóstico real aún no se ejecutó para el candidato final.

## Instalador y firma

Después del build aprobado, `--prepare-installer` prepara una lista explícita de archivos y un script `installer-entry.iss`, vinculados al commit, versión AST, SHA256 del manifiesto y cabecera PE x64. No ejecuta Inno Setup. `setup_installer.iss` rechaza una compilación directa sin esas entradas; conserva AppId y directorio/modo de actualización existentes, no lanza el programa al terminar ni elimina registros/planes/datos al desinstalar.

Todavía faltan compilador Inno fijado/verificado, compilación y comparación del payload, instalación/upgrade/desinstalación en Windows descartable y verificación de firma. No hay certificado ni firma acreditada por esta preparación. Una actualización debe reemplazar el conjunto probado del paquete, con respaldo y compatibilidad verificados; no sólo el EXE.

Linux y macOS conservan los recorridos nativos. El `.app` de macOS, frameworks/enlaces, DMG, firma/notarización y las bibliotecas Qt de Linux necesitan ensayos en sus sistemas. Las estructuras sintéticas comprobadas en Windows no acreditan esos binarios. No se ejecutan operaciones de publicación desde estos scripts.

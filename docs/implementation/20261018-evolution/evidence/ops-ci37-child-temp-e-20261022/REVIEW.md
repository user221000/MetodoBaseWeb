# TEMP privado en E: continuidad acotada de CI web

El código a53cb8ff conserva `--private-as-child-temp`: TEMP/TMP/TMPDIR sólo cambian en el diccionario del hijo; `_METODOBASE_TEST_ROOT` y basetemp quedan debajo. La preimagen del runner es exactamente el GitOID a554046736eebf6028be1d1b5a64f0ffcfceae89 de Main08d. No se cambian runtime, aislamiento, fixtures de producto ni selectores.

Los cinco documentos históricos se cerraron en c5ea7e48. Sus cuatro payloads conservan bytes RAW originales; sólo su archivo de atributos pasó a cinco nombres explícitos para retener CRLF y admitir su comprobación de whitespace. Su5PASS original con padreC/hijoF sigue siendo historia, sin atribuirle rutasE.

La primera faseE v1 fue RECHAZADA:4PASS/1FAIL. Al colectar el probe absolutoE desde cwdF, pytest intentó consultar `E:/WpSystem/__init__.py` y recibió WinError1337. La carpeta ajena no se modificó. El productor se detuvo al no encontrar su probe; JUnit, logs, fuente y observación de rechazo permanecen en el archivo privado con prefijo v1-rejected.

El cambio 8b21d1eb añade sólo `--rootdir=<private>` y `--confcutdir=<private>` a la invocación del probe externo del test nuevo. Todas las aserciones AST permanecen idénticas a53, cuyo RAW se retuvo. Los controles de fuga, raíz previa y basename siguen usando `tests/isolation.py` original. El ajuste limita los padres de colección del probe sin saltar casos ni alterar reglas de aislamiento.

La faseE v2 pasó5/5,0fallos/errores/omisiones en11.422s. Ejecutó pytest anidado y SQLite real. El padre conserva su entorno y tempfileE/tmp; pruebas, base SQLite y tmp_path están en raíces privadasE. PythonWEB92 y base son exclusivamente E. La raíz del productor se verificó semánticamente User+SYSTEM2 antes/después; los límites de los hijos usan el constructor original que verifica esa frontera antes del payload. Los cinco archivos críticos de fuente conservaron SHA RAW antes/después. Se usaron cachesE y variables sólo del proceso.

El launcher confiable8015819d fue inspeccionado, pero su invocación directa fue rechazada por ExecutionPolicy local. No se cambió política global ni se atribuye PASS al launcher: se usó explícitamente PythonE con -I/-B y, en hijos, PythonE -B para ejecutar módulos/scripts. El primer bootstrap creó únicamente metadataE, no un resultado de prueba.

Los dos intentos, productores, logs, SQLite y fuentes quedaron archivados con full member readback y segundo SHA de origen; `archive-readback.json` detalla sus identidades. `summary.RAW.json` preserva la salida original: su campo source_commit describe la selección candidata c5ea+dos argumentos; source-bindings liga esos bytes al commit final8b21d1eb sin reescribir el RAW.

No se ejecutaron pip check ni un nuevo inventario completo de paquetes: no se afirma quietud de todo el entorno instalado. No hubo serial/n2/PG/Redis/Chrome/VM/imagen, escritura/lectura de payload de proyectoC, cambio de Main ni nueva colección final. Las suites completas siguen HOLD hasta cierre de migración, integraciónCI57 y freeze Root. Los comandos canónicos futuros usan E:/MetodoBaseWorkspace/envs/web92/Scripts/python.exe, cachesE, `--private` nuevoE/F y `--private-as-child-temp`; conservan semilla20261018 y umbrales originales, pero no están autorizados por este canario.

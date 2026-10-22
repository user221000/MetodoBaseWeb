# Trabajo local de MetodoBase Web

El trabajo autorizado se limita al servicio web. No desarrollar, probar ni empaquetar desktop. Se conservan sus archivos históricos.

El repositorio de ejecución está en `F:/MetodoBaseWeb-execution-20261018`; `F:/MetodoBaseWeb-main` es la copia de referencia. El estado y los criterios vigentes están en `docs/implementation/20261018-evolution/`.

Por instrucción del usuario, todos los archivos temporales, cachés, nuevos entornos y evidencias del proyecto deben escribirse en `E:/MetodoBaseWorkspace` o F. Configurar TEMP, TMP y TMPDIR del proceso a `E:/MetodoBaseWorkspace/tmp` antes de arrancar Python o herramientas. No modificar variables globales de Windows ni instalaciones compartidas.

Herramientas locales verificadas:

- Python web: `E:/MetodoBaseWorkspace/envs/web92/Scripts/python.exe`.
- Python de calidad: `E:/MetodoBaseWorkspace/envs/quality10/Scripts/python.exe`.
- Python base: `E:/MetodoBaseWorkspace/tools/python-3.12.13/python.exe`.
- Node, uv y PostgreSQL: `E:/MetodoBaseWorkspace/tools/`.
- Configuración por proceso: `E:/MetodoBaseWorkspace/Invoke-MetodoBase.ps1`.

Invocar Python con `-B -X utf8` y las herramientas Python con `python.exe -m modulo`. Los wrappers copiados de Scripts conservan sus bytes originales y algunos contienen rutas C; no activar esos entornos ni ejecutar sus wrappers. La política de ejecución del host puede exigir un proceso PowerShell con `-ExecutionPolicy Bypass` para el launcher; no cambiar la política global.

Preservar los 537 archivos untracked históricos; añadir sólo archivos explícitos de la tarea. Preservar los RAW y recibos originales de las validaciones, incluidas las rutas C históricas. Usar mapas de migración para rutas operativas nuevas. La migración pendiente se documenta en `MIGRACION_C_E.md`; consultar su estado antes de copiar o retirar una raíz. No crear junctions para sustituir rutas antiguas.

Free aprobado: 10 clientes, 1 plan por cliente al día, 10 planes totales diarios por gimnasio y 20 mensuales.

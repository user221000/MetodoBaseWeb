# Contención de dos hallazgos fragmentados de Gitleaks 8.30.1

Este cambio parte de `c28d718233856b4c245b31b8d7f66904855b05a5` y todavía requiere revisión independiente y escaneo del árbol congelado. No declara limpio ningún commit posterior.

El escaneo anterior de 3026 archivos terminó con 930 hallazgos. La revisión identificó líneas literales de huellas de código y marcadores cerrados de fixtures. De 123 huellas distintas, se recalcularon 116 desde preimágenes concretas; siete sólo se conservan como metadatos históricos sin preimagen disponible. La configuración distingue esos casos mediante excepciones finitas por regla, ruta y línea completa. No convierte esas siete huellas en procedencia verificada. Conserva las reglas y excepciones anteriores.

La revisión independiente encontró dos problemas del escáner. `Finding.Line` puede incluir el LF precedente; las expresiones nuevas permiten como máximo ese LF y el CR final de una línea. Además, en el límite de fragmentos de 100000 bytes, Gitleaks puede devolver `Match` y `Secret` truncados junto a una `Line` que abarca líneas ajenas. Dos líneas3081 de manifiestos históricos siguen detectándose aun con la excepción literal correcta. Modificar datos fuera del fragmento conserva el mismo `Match` truncado: por ello, éste no sirve como criterio de aceptación.

El wrapper clasifica únicamente esos dos hallazgos de `generic-api-key`, sujetos a todas estas comprobaciones:

- Ruta relativa exacta de cada manifiesto histórico.
- SHA256 de todos los bytes originales, fijado por separado para LF y CRLF uniformes.
- SHA256 idéntico de la copia privada efectivamente escaneada; una transcodificación BOM/UTF16 no coincide.
- `StartLine` y `EndLine` enteros, ambos3081, y hash de la línea física completa. Sólo se retira un CR terminal tras verificar el archivo completo.
- Conjunto y contenido de las fuentes estables antes y después del escaneo.

El informe distingue hallazgos crudos, clasificados y restantes. Los restantes producen salida1; cambios de fuentes producen salida2. Un error del escáner o incoherencia entre su estado y el informe falla sin mostrar su salida capturada. No se inspeccionan `Match`, `Secret` ni `Finding.Line` para clasificar; tampoco existe una excepción genérica para cadenas de64 caracteres. Otra línea o regla del mismo archivo sigue bloqueando.

Las pruebas mantenidas usan los manifiestos reales LF/CRLF y rechazan alteraciones en el sufijo del hash, el nombre del campo, una clave adyacente, posición, ruta, regla, tipos de coordenadas, bytes de la copia y codificaciones. También verifican conteos, otro hallazgo en el mismo archivo y el rechazo de cambios de fuente durante la ejecución. El primer ensayo tuvo dos errores de preparación: intentaba modificar `api` en una ruta que contiene `tests/`. Esa sustitución no cambió bytes y falló la precondición del test. Se conservó el driver inicial; el ensayo corregido pasó53 pruebas (11 existentes y42 nuevas).

La contención es específica de Gitleaks8.30.1. No corrige su fragmentador ni reemplaza la revisión de nuevos resultados. Los informes crudos de esta revisión se conservan fuera del árbol entregable para evitar que sus mapas de huellas se conviertan en nuevas entradas del mismo escaneo. El inventario agregado y las ubicaciones saneadas permiten auditar el alcance sin revelar valores de credenciales.

Fuentes primarias del defecto observado: [fragmentador](https://github.com/gitleaks/gitleaks/blob/v8.30.1/sources/file.go), [coordenadas de líneas](https://github.com/gitleaks/gitleaks/blob/v8.30.1/detect/location.go) y [construcción del hallazgo](https://github.com/gitleaks/gitleaks/blob/v8.30.1/detect/detect.go). Los resultados locales provienen de la ejecución del binario fijado, no de una afirmación del proyecto upstream.

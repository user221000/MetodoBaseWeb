# Ajuste focal de legibilidad de tablas de progreso

Base: `b7f8e129251dfd5216f811ba77d0b6183ca76735`. Único producto modificado: `web/static/css/progreso.css`. No cambia HTML, datos, permisos, transporte, MFA ni API.

## Diagnóstico y cambio

La combinación de `width: 100%` y `overflow-wrap: anywhere` permitía que las columnas midieran apenas unas letras. El contenedor ya tenía región accesible, nombre, foco y `overflow-x: auto`, pero no existía desbordamiento interior útil: fechas y medidas se partían para encajar.

La tabla conserva el tamaño de letra de `.95rem` (15,2 px en esta prueba). El mínimo de `36rem` permite cuatro columnas de al menos `9rem`; las tablas de medidas tienen cinco o siete columnas y su ancho puede crecer según el contenido. Los encabezados pueden envolver palabras completas. Las celdas mantienen fechas, cifras con unidad y marcas UTC en una línea. El desplazamiento permanece dentro de la región existente y sus estilos quedan acotados a `.progress-table-wrap`.

No se agregan columnas: el renderer profesional probado recibe únicamente `peso_kg`. Sus columnas de grasa y masa magra siguen ausentes. Los valores de esta prueba son ejemplos sintéticos en RAM, no mediciones de una persona.

## Evidencia y alcance

QA preservó cuatro rojos con autenticación y API reales en su lote independiente anterior, referenciado por hash en `before-source.json`. Esa ejecución pertenece a QA; este lote no la presenta como prueba propia ni como aceptación posterior.

El mismo `driver.cjs` ejecutó el renderer real `progreso-vista.js` y su módulo de datos, con CSS anterior y posterior, en Chromium local. No inicia servidor ni base de datos y bloquea solicitudes de red. Las ocho combinaciones son personal/profesional por 320, 390, 768 y 1440 px.

| Comprobación | Antes | Después |
| --- | --- | --- |
| Casos completos | 1/8 | 8/8 |
| Cifra y unidad, fecha civil y marca UTC | Fragmentación en 7 casos | Un fragmento cada una en los 8 casos |
| Desbordamiento horizontal de página | 0 px | 0 px |
| Desplazamiento interior por `ArrowRight` | Sin desbordamiento útil en móvil | Efectivo en las 7 tablas que exceden su región |
| Tabla profesional a 1440 px | Cabe en su región | Cabe en su región; no necesita desplazarse |
| Tamaño de letra de celda | 15,2 px | 15,2 px |
| Infracciones axe AA / errores JS | 0 / 0 | 0 / 0 |

El ancho interior posterior es de 1244/1258 px en la tabla personal y 916/925 px en la profesional cuando exceden la región; la región móvil mide 286/356 px. El usuario puede moverla con teclado sin mover la página. Las capturas se toman después del ejercicio de teclado y pueden mostrar un desplazamiento interior; las medidas de fragmentos se toman directamente de los rangos DOM. También se representa la tabla de contadores y se inspecciona visualmente su parte visible, sin atribuirle un canary de teclado independiente.

`before/` conserva los siete rojos originales y el caso verde de control. `after/` conserva los ocho verdes. Cada lote incluye ocho capturas, fuentes antes/después, versiones de herramientas, hashes binarios y recibo de cierre. Ambos perfiles propios cerraron cooperativamente, sin procesos restantes; los procesos Chrome ajenos presentes al inicio seguían presentes. Los perfiles temporales se conservaron y no se inspeccionaron datos del usuario. No se tocó el servidor ajeno 8776.

Esto valida presentación sintética, no autenticación/API32, datos clínicos, lector de pantalla ni aceptación global de UX. QA repetirá su canary real independiente después del freeze. No se repiten las suites VM/HTTP históricas porque no cambia código ejecutable ni el contrato.

## Reproducción y preservación

Desde este worktree, con las dependencias y Chrome locales declarados en el driver:

```powershell
$env:R25_LAYOUT_STAGE = 'before' # usar CSS anterior en una copia separada
node docs/implementation/20261018-evolution/evidence/r25-table-layout/driver.cjs
$env:R25_LAYOUT_STAGE = 'after'  # usar CSS posterior en otra copia separada
node docs/implementation/20261018-evolution/evidence/r25-table-layout/driver.cjs
```

El driver rehúsa sobrescribir un directorio de lote existente. Para reproducir, usar una copia temporal con esos dos directorios de salida ausentes, conservando las pruebas históricas originales. El resultado anterior devuelve código 1 por sus aserciones de legibilidad; el posterior devuelve 0.

`before.css` conserva la preimagen RAW. `after.css` y `change.patch` conservan el resultado y su delta. `seal.cjs` verifica la preimagen contra Git, aplica la inversa exclusivamente en una copia temporal y comprueba que recupera sus bytes exactos. `freeze.json` fija hashes RAW y Git LF, el driver intacto, los reportes/capturas y las dependencias inspeccionadas. `.gitattributes` fue creado antes de las pruebas para conservar estos archivos sin transformación de texto.

El primer intento de sellar la inversa detectó la conversión CRLF heredada de la configuración global de Git en la copia temporal. `seal-initial-failure.json` conserva el diagnóstico y el hash del script previo. Se corrigió pasando `core.autocrlf=false` a esa llamada; se mantiene la comparación de bytes exactos, sin cambios de producto, driver ni resultados del navegador.

Clasificación: código propio, datos sintéticos, rutas de herramientas locales e identificadores de procesos. No contiene credenciales, tokens, contactos, salud real, semillas, grants ni claves de recuperación. No se afirma un freeze global de paquetes: se registran las versiones/rutas utilizadas y los hashes de su entrada al sellar, además de los binarios capturados al iniciar y al cerrar.

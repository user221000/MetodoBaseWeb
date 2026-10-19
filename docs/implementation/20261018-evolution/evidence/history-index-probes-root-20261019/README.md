# Experimentos funcionales del índice y cursor

Tres bases UUID propias, todas eliminadas con ausencia verificada. Sin carga HTTP, benchmark, SLO o migración productiva. El primer ensayo en 28 conservó las 1000 filas ordenadas, cinco empates y diez fechas NULL: el índice propuesto eliminó Sort y redujo el lector de planes de 1000 a 51. Las estructuras anteriores y 20 familias RLS quedaron iguales al quitar el índice adicional de la comparación.

La consulta real del cursor avanzado se capturó sobre núcleo 29 aislado con el índice adicional: visitó 1000 filas para devolver 50. El cambio de lector usa comparación de tupla y UNION de ramas acotadas en una sola sentencia. El mismo criterio de cursor devolvió las mismas 50 filas visitando 51 en el corpus sin fechas NULL. La mezcla dated/NULL y la migración 30 aún requieren gates propios. Las 96 pruebas mantenidas de historial/cursor/headers/error pasaron, con cuatro avisos existentes; log PowerShell UTF16 conservado sin transcodificar.

Fotos de los probes cubren archivos ya tracked. El nuevo helper estaba untracked y su SHA se conserva después en el ZIP, sin inventar una foto previa de ese archivo. La revisión independiente deberá fijar también ese helper antes de ejecutar. Fuente y cambios sólo en F:/mb-hidx-20261019; MAIN no contiene el lector nuevo ni la migración 30.

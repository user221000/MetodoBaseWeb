# Integridad de los ejecutables de CI29

QA reprodujo dos bypass en CI1: un checker con `REPORTS={}` y un runner que imprimía éxito sin ejecutar el histórico. El verificador completo aceptó ambos. Sus negativos se conservan en `qa-ci29-phase1-independent-20261019`; los positivos anteriores no constituyen aceptación de CI1.

El verificador ahora autentica por hash de bytes LF los dos ejecutables antes de importarlos o lanzarlos. La especificación esperada de los cinco informes vive además en el verificador y debe coincidir exactamente; generar menos de 55 controles de informes falla. Los archivos históricos y sus aserciones permanecen intactos. Esta protección permite detectar cambios posteriores de esos ejecutables respecto del cuerpo revisado; los nuevos cambios de referencia requieren revisión de código.

Las pruebas nuevas cubren los dos cuerpos sustituidos y la reducción de la especificación en memoria. El recorrido de navegador y la ejecución de Actions son controles separados.

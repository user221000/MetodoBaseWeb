# Revisión independiente UI606f3c6: bloqueada

El gate VM independiente conserva **6/10 verdes, cuatro rojos, exit1**, sobre `606f3c6b61ad6eeb470f418e03ea29b41532010c`. Las 51 fuentes del manifiesto autor `2283e6ee…` coinciden y permanecieron intactas. No se modificó producto ni tests del autor. Los 21 grupos browser de QA prueban fronteras distintas y constituyen cobertura parcial, no aceptación de estos cuatro negativos.

## Hallazgos reproducidos

1. `Api.auth.logout` devuelve `closed_local` con par vacío correctamente, pero también `server_confirmed:true` ante HTTP200 con `{success:false}` o `{}`. El cuerpo real del endpoint es `{message:'Sesión cerrada. Todas las sesiones revocadas.'}`, emitido después de la llamada de revocación; los dos negativos no corresponden a ese contrato. La revocación persiste versión/access/refresh en una transacción y propaga fallo de commit. Se debe distinguir cierre local de confirmación remota sin imponer al backend un campo success inexistente.
2. Exportación permite que una respuesta de A atraviese el límite de su consumidor después de sustituir la sesión por B. El doble nominal espera al helper real `Api.usuario.exportarDatos`, llama `Api.saveTokens(B)` y devuelve la respuesta ya resuelta. `usuario-privacidad.js` prepara y descarga un Blob cuyo account.id es A mientras el par actual pertenece a B. No se modifica request/refresh ni se sustituye la comprobación del transporte. Es una reproducción VM de la frontera asíncrona, no una afirmación de explotación con usuarios reales o navegación completa.
3. Tras preparar una parte, exportación ignora `metodobase-session-changed` con `session_storage_error`: conserva visible la repetición del archivo y el contador del diario. El resto del nuevo diario sí escucha ese evento. La prueba comprueba la invalidación de estado en memoria; no demuestra una descarga posterior autenticada tras el fallo de Storage.

Los controles positivos cubren B durante la primera eliminación del par, B entre el aviso de éxito y el redirect, cambio de role/SV del contexto canónico, cursor de fecha exclusivo repetido, diario A tardío tras B y rechazo de un diario malformado. Las trampas de Storage impiden leer/escribir/borrar legado o ejecutar clear; los seis controles verdes comprueban sus bytes. El rótulo original del último caso es más amplio que su cuerpo: ese caso concreto prueba un contexto personal estable ante respuesta malformada, no realiza además un reemplazo de cuenta.

## Conservación y adaptación del harness

El driver original `diary-ui-security-independent-driver-before.cjs`, SHA `3bff0cbb461ef62b6340242b6f96c4104d1fd1353fdbb8e3800505291ea7c131`, y su primer resultado permanecen intactos. El driver parametrizado cambia únicamente SOURCE_ROOT y directorio de salida. La versión `driver-param-realack.cjs` sustituye además dos respuestas positivas sintéticas success:true por el cuerpo message real. Ninguna aserción, payload negativo, orden de casos ni fuente de producto cambia; invertir esas sustituciones recupera exactamente los bytes de la versión anterior. La repetición con fixtures corregidas mantiene 6/10 y los mismos cuatro rojos.

El primer manifiesto `source-before.json` anotó erróneamente success:true como contrato del servidor. Se conserva por huella como errata; `contract-addendum.json` corrige sólo esa descripción con lectura de main y autor, sin reescribir resultados. No se debe usar aquel campo descriptivo incorrecto para exigir success:true al producto. La copia del body real del endpoint y sus fuentes coinciden entre main y autor tras normalizar LF/CRLF.

Repetición del autor o revisor, guardando cada ejecución en un directorio nuevo:

```powershell
$env:DIARY_UI_SOURCE_ROOT = 'F:\MetodoBaseWeb-diary-ui-20261019'
$env:DIARY_UI_REVIEW_OUTPUT = 'C:\Users\Consu\AppData\Local\Temp\diary-ui-security-new-run'
node 'F:\MetodoBaseWeb-execution-20261018\docs\implementation\20261018-evolution\evidence\ux\diary-ui-security-independent-driver-param-realack.cjs'
```

Es una prueba VM con Storage/transporte/DOM sintéticos. No usa red, navegador, proveedores ni PostgreSQL. Los hallazgos alimentan R10/R14/R31/R15; la coordinación decide si el cruce de exportación merece SEC04. No renumera el inventario ni cierra R23/R10 general.

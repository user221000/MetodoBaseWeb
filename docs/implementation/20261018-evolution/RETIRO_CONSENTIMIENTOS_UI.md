# Retiro propio sin sesión: contrato y preparación UI

Base aislada: `345aa7ce16f65fec9481b48cfcd63c33ff3835fc`. Worktree de autor: `F:/mb-progress-retirement-ui-20261019`. No se modifica MAIN, el transporte Api.js, MFA existente, modelos, RLS ni rutas API.

Entrada contractual inmutable de backend: `backend-progress32-retirement-20261019/wire-v1.md`, SHA256 `5b6de9c0ecbb9bdf070a1ef6831d5f22f2ac11bddf32c54f3787b99d315bc706`. Backend confirmó que no hay cambios previstos de campos/códigos. Su implementación seguía WIP al preparar este consumidor: los dobles de esta entrega no acreditan aceptación de esa API.

## Página y autoridad

`GET /retirar-consentimientos` monta un formulario público en ambas factories mediante el router de páginas existente. Ambas páginas de acceso y la sección de datos personales de `/mi-perfil` incluyen un enlace fijo. Es un flujo de propósito exclusivo: no consulta `/auth/me`, inicia sesión, adquiere bearer, usa cookies ni adopta perfil/cartera. Tampoco toca la sesión que pueda estar abierta en otra página.

La página no carga Api.js, GIS ni recursos de terceros. Su formulario no tiene nombres de campos ni valores serializados, empieza deshabilitado hasta conectar el adaptador y una meta CSP anterior a los recursos prohíbe navegación de formulario. La SSR devuelve `no-store` y `no-referrer`. Backend posee el delta de middleware para CSP fija y privacidad en todos los estados de la página exacta y las APIs; requiere composición/revisión independiente y no se atribuye a estas pruebas.

## Solicitudes y datos mostrados

El controlador sólo puede ejecutar dos POST JSON en rutas constantes, con `credentials: omit`, `mode: same-origin`, `redirect: error`, `cache: no-store` y `referrerPolicy: no-referrer`. Nunca acepta una URL del DTO. No hay retry, refresh, lectura posterior ni factor automático.

| Acción explícita | Cuerpo propio |
| --- | --- |
| Consultar primera página | `primary` password/email recién escritos, factor opcional recién escrito, `limit:50`, `after:null` |
| Consultar siguiente página | Otra prueba completa, mismo límite, `after` exacto y minúsculo emitido por el servidor |
| Retirar la selección | Otra prueba completa, `link_id`, `expected_consent_id` y `expected_version` del registro seleccionado en RAM |

La selección no envía una solicitud. Abrir la página tampoco. La prueba usada para consultar no se conserva para retirar ni paginar. El usuario puede pegar códigos y usar un gestor de contraseñas. Una cuenta sin segundo factor debe escoger la opción sin factor; no se adivina ni se revela su configuración a partir de un error de autenticación.

El correo introducido permanece como propiedad de formulario para mantener visible la cuenta que se está comprobando; contraseña y código se limpian inmediatamente al despachar o rechazar la acción, además de cancelación/error/cambio de cuenta/salida. No se escriben como atributos, texto, URL, Storage, logs o telemetría. Cambiar el correo invalida los resultados, selección y cursor; una comprobación adicional detecta cambios de propiedad que no disparen `input`. La identidad de los metadatos queda ligada en RAM al correo exacto observado, y no se mezcla con una prueba posterior de otra cuenta.

Sólo se muestran categorías, fechas, tipo de evento y marca temporal original. No se muestran IDs, gimnasio, profesional, contactos, perfil ni medidas. Los ordinales de pantalla son locales a cada página. Si los datos mínimos no permiten distinguir el permiso, se indica que no se confirme el retiro. Los registros históricos no se presentan como autoridad vigente.

La página muestra sólo una página de hasta 50 filas: la siguiente reemplaza la anterior. UUID, enteros, claves exactas, categorías booleanas, fechas, orden de keyset y alcance se verifican antes de guardar o representar un DTO. La confirmación de retiro exige el mismo vínculo, evento de retiro, versión siguiente, identificador nuevo, categorías/periodo/version del vínculo iguales a la selección y `effective:false`. Un ACK desconocido no produce éxito. El lector limita la respuesta a 256 KiB como defensa técnica del consumidor; el stream normal del navegador se cuenta antes de acumularlo. No es una política de negocio ni un nuevo límite del servidor.

## Estados y cercos

Carga, lista vacía, selección, consulta/confirmación en curso, error y retiro confirmado tienen mensajes propios y foco accesible. Un doble clic no produce otra solicitud. Cancelar aborta sólo la petición propia. Se comprueba la época y el correo antes/después de cada await, decodificación y representación. Invalidar borra filas/cursor/selección sincrónicamente. Una continuación antigua no limpia una prueba nueva ni vuelve a mostrar sus metadatos.

Los eventos `pagehide`, `metodobase-session-changed` y los eventos Storage de autenticación invalidan la vista sin leer sus valores ni acceder a Storage. Se mantiene el aislamiento del transporte previo: esta página no emite ni modifica tokens o eventos de sesión generales.

401 no distingue contraseña, cuenta o factor incorrecto. 429 explica la espera. 409 no sustituye el consentimiento por el último. 503 o fallo de transporte puede significar que se consumió el factor o se confirmó el retiro sin recibir el ACK: se descartan resultados y se exige una consulta manual nueva con otra prueba válida. No hay botón para repetir ciegamente el retiro. Google como primaria y pérdida de todos los factores se explican como límites de esta vía; no se ofrece un canal de recuperación inventado.

## Pruebas y límites

- Canario anterior real de SSR: cuatro rojos (404 y tres enlaces ausentes), fuente de aserciones conservada. Tras implementar, las cuatro mismas aserciones pasan.
- Ocho casos SSR finales en SQLite sintética: los cuatro anteriores, tres de markup/privacidad/accesibilidad semántica y uno de composición pública en la factory API. No verifican retiro de backend.
- 36 casos finales del controlador en Node VM y nueve del adaptador montado en DOM mínimo VM, con respuestas y pruebas sintéticas en RAM. Cubren peticiones exactas, limpieza, selección/CAS, páginas, doble clic, incertidumbre, strict DTO, eventos, cuenta/correo durante awaits y callbacks reentrantes.
- El primer 33/34 de VM detectó un error de sincronización del harness: aún no había entrado al lector de stream. Se conserva su cuerpo y reporte; sólo se añadió una señal de entrada antes de disparar la invalidación, manteniendo las aserciones y el producto.
- Dos canarios adicionales de autor preservan rojos y cuerpos previos: un código de error que coincidía con el prototipo del diccionario podía producir un mensaje que no era texto (34/35 → 35/35); una invalidación durante la colección de prueba podía limpiar la prueba nueva (35/36 → 36/36). No hubo petición cruzada en esos canarios. El código final usa propiedades propias y descarta la continuación antigua antes de limpiar.

No sumar ejecuciones intermedias como criterios nuevos. Este lote no ejecutó Chrome, axe, lector de pantalla, PG ni la API WIP de retiro. Quedan pendientes composición con backend congelado, HTTP de propósito real, browser 320/390/768/1440/teclado/axe y revisión independiente. No se declara cierre global de recuperación, MFA, privacidad ni UX.

## Reproducción y evidencia

```powershell
node tests/e2e/progress_retirement.cjs
node tests/e2e/progress_retirement_dom.cjs
python -X utf8 tests/run_isolated.py tests/test_progress_retirement_ui.py tests/test_progress_retirement_ui_contract.py -q --tb=short
```

`PROGRESS_RETIREMENT_VM_OUTPUT` y `PROGRESS_RETIREMENT_DOM_OUTPUT` permiten un archivo nuevo de salida; los drivers rechazan sobrescribir evidencia. No registrar cuerpos/errores de prueba con secretos: los reportes imprimen únicamente nombre, estado y clase de fallo.

Evidencia propia: `docs/implementation/20261018-evolution/evidence/progress-retirement-ui/`, con atributos `-text` creados antes de los archivos, preimágenes RAW, fuente de canarios previos, resultados por etapa, patch/inversa y freeze RAW/GitLF. El código de sesión, parciales y JS MFA/R24/export quedan fijados como dependencias de sólo lectura. La clasificación es código propio/datos sintéticos y huellas públicas; no credenciales reales, semillas, kits, grants, tokens, salud o contactos reales.

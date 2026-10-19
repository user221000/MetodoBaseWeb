# Revisión independiente del campo remitente

Se acepta acotadamente el cambio de clave `from_` a `from` para los bytes originales del sender RAW `9a70a3bc4ec2c8912540f04d479de121d6ad70f29f18c898abe98892aa3c5f6a` y del test autor RAW `58c0c827881a10ccef44050c89dcd2804cf0412d6d7f8e524cecbabbe06bcd45`. La evidencia no acepta cambios posteriores por inferencia.

La fuente anterior se obtuvo mediante `git show` del commit exacto registrado de `f34ae98`, sin reconstrucción. Las copias `email-sdk-wire-independent-before-exact-git.py` y `email-sdk-wire-independent-after-exact-raw.py` conservan esos bytes. Tras normalizar únicamente CRLF a LF, la única diferencia es una clave del diccionario. El SDK instalado y fijado es Resend 2.50.0; sus fuentes locales, RequestsClient y requests también están ligados por huella en `email-sdk-wire-independent.json`.

Pasaron 22 canarios propios. Se usaron el SDK, RequestsClient y la preparación JSON real de requests; sólo `Session.send` devolvió una respuesta en memoria después de crear PreparedRequest. Los sockets externos estaban bloqueados y se suministró exclusivamente una key sintética. La fuente Git anterior produce `from_` y recibe el rechazo sintético esperado en tres variantes: texto, adjunto y PDF privado. Los bytes actuales producen `from` y superan ese mismo contrato en memoria. Se preservan destinatario, asunto, HTML, adjuntos y nombre constante plan.pdf; los bytes de PDF no acceden a Path. Los controles sin configuración, HTTP 400/403/422/429/500, JSON inválido y excepción de transporte retornan False con logs operativos sin destinatario, asunto, cuerpo, ruta ni mensaje privado del error.

## Negativo separado de confirmación

Ambas fuentes devuelven True y registran delivery_sent ante un HTTP200 sintético con `{}`. El SDK no valida en runtime el tipo SendResponse ni exige un ID. Se conservó como negativo real separado: `email-sdk-wire-independent-ack-negative.json` y su log tienen dos casos, cero verdes y exit1. Es anterior al cambio de clave y no se presenta como regresión del sender. No se confirma que el proveedor real produzca ese cuerpo.

Este hallazgo debe contenerse en un lote aditivo antes de aceptar confirmación de envío. Un futuro sender que lo corrija necesita otra huella y evidencia; los 22 verdes anteriores y los dos negativos permanecen atribuidos sólo a los bytes congelados indicados. La entrega efectiva, verificación del dominio/proveedor, observabilidad y recuperación de R16 siguen abiertas. Ningún correo fue enviado a la red ni aceptado o entregado por un proveedor real.

El driver de evidencia es una copia histórica del ejecutado desde Temp, con sus rutas originales explícitas. No modifica producto ni tests de main. La lectura inicial intentó importar RequestsClient desde un módulo que no lo exporta; falló antes de ejecutar el sender y se resolvió inspeccionando el tipo real de `resend.default_http_client`. No fue un fallo de producto ni un gate.

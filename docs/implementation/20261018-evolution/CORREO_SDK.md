# Contrato local del adaptador de correo

R16 conserva pendientes el proveedor/dominio verificados, entregas observables y recuperación de cuenta. Este lote corrige dos defectos del adaptador existente sin efectuar envíos reales.

Resend2.50.0 fijado recibe `from`, no `from_`. Se comprobó en SendParams y en la serialización del SDK instalado; coincide con la [referencia oficial](https://resend.com/docs/api-reference/emails/send-email). El SDK conserva literalmente las claves del diccionario, por lo que el adaptador anterior producía un payload que no satisface ese contrato.

También aceptaba HTTP200 con `{}` y registraba éxito. Ahora exige una respuesta dict con id string no vacío y de hasta256 caracteres. Una respuesta sin confirmación válida retorna False y registra sólo delivery_unconfirmed/invalid_response. La respuesta válida registra delivery_accepted; eso acredita aceptación del adaptador, no entrega al destinatario. Los rechazos y errores conservan logs sólo con clase técnica. No se cambia remitente, destinatario, cuerpo, adjuntos ni configuración del proveedor.

Autor: dos fallos de contrato y dos controles iniciales; después23 pruebas verdes con el SDK real y HTTPClient en memoria. El negativo de ACK dio nueve fallos antes de la segunda corrección. El primer seguimiento obtuvo31 verdes/1 fallo: la fixture de privacidad para sent devolvía un Mock sin id. Se preservó íntegra y se añadió exclusivamente un ACK sintético a esa preparación; sus38 aserciones AST siguen idénticas. Resultado final32 verdes/1 deprecación en4.62s. Ningún test abrió red ni entregó correo.

Seguridad independiente:22 casos de wire y17 ACK sobre SDK/RequestsClient/PreparedRequest reales, interceptando el transporte en memoria. Baseline Git exacto y sender intermedio se conservan; el `{}` anterior continúa dando el positivo incorrecto. Quince fuentes estables y ocho artefactos originales intactos. [Manifiesto inicial](evidence/email-sdk-wire-independent-source.json), [seguimiento ACK](evidence/email-sdk-wire-independent-ack-fix-source.json), [comparación de aserciones](evidence/email-sdk-wire-independent-ack-assertions.json).

El correo real, la entrega/rebote, idempotencia duradera, recuperación y verificación de identidad necesitan sus propios recorridos y gates. Este lote no acredita esos criterios ni autoriza envíos externos.

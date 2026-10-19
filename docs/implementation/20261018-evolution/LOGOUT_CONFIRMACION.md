# Confirmación persistida de logout

`POST /api/auth/logout` agrega `success:true` a su respuesta200 y conserva el mensaje anterior. El campo se construye sólo después de que `revocar_refresh_tokens_usuario` complete el commit de la versión de sesión y la revocación de todos los refresh del sujeto. Es una ampliación del contrato anterior, que sólo devolvía `message`.

El consumidor puede afirmar confirmación remota únicamente con ese booleano explícito. Un cuerpo vacío, `success:false`, una respuesta antigua que sólo contiene el mensaje o una respuesta perdida permiten informar cierre local con confirmación remota pendiente. El texto traducido del mensaje no constituye un protocolo.

Las seis pruebas de `tests/test_logout_confirmation_contract.py` usan ambas factories reales, dos pares de tokens por sujeto y consultas posteriores desde otra sesión. Antes del cambio fallan sólo los dos200 sin el campo nuevo. Después pasan las seis: commit confirmado invalida access y ambos refresh; fallo antes de commit mantiene la versión y las sesiones; pérdida sintética del ACK después del commit devuelve500 sin `success:true`, aunque la revocación ya persiste. No se simulan los resultados de autorización ni la persistencia; se inyecta únicamente el fallo del commit.

Este cambio no altera el orden de bloqueo del helper ni acredita logout entre todas las pestañas, recuperación de cuenta o una revisión completa de autenticación. La corrección del consumidor y sus casos de cambio de cuenta se revisan por separado.

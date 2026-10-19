# R31: autenticación y telemetría clasificada

Lote autor local del19 de octubre de2026 UTC. No hay envío a Sentry, Resend u otro proveedor: el harness bloquea sockets externos y los transportes son mocks de entrega o `sentry_sdk.transport.Transport` en memoria. Datos/identidades son sintéticos. No hay borrado histórico, nueva retención ni cambio a contratos de acceso de soporte.

## Antes y después

[Baseline](auth-telemetry-privacy-before.log), [JUnit](auth-telemetry-privacy-before.xml), [fuentes](auth-telemetry-privacy-before-source.json):13 fallos y1 éxito,4.35s. Los seis archivos seleccionados permanecieron estables durante esa ejecución. Comprueba las exposiciones de login/refresh/audit/Sentry/correo descritas en PRIVACIDAD.md; la prueba de fallo del transporte de correo ya era verde porque registraba sólo clase.

El [primer gate](auth-telemetry-privacy-first.log), [JUnit](auth-telemetry-privacy-first.xml), dio43 verdes/4 fallos: al retirar el uso incorrecto del generador `get_db` en el escritor de auditoría quedaban dos lectores referenciando ese import. Se corrigieron a `SessionLocal` y se conserva este resultado, sin presentarlo como aceptación.

El [segundo gate](auth-telemetry-privacy-second.log), [JUnit](auth-telemetry-privacy-second.xml), [huella](auth-telemetry-privacy-second-source.json), dio61 aprobadas en11.61s:19 controles nuevos,20 Sentry existentes adaptados al contrato de privacidad,13 de auditoría y9 de errores automáticos. Sus16 fuentes permanecieron estables. Es anterior a la adaptación de correo por bytes y la última declaración directa de Pillow en los locks, por lo que se conserva como etapa.

El [gate autor final](auth-telemetry-privacy-final.log), [JUnit](auth-telemetry-privacy-final.xml), [huella](auth-telemetry-privacy-final-source.json), dio72 aprobadas en10.47s: las61 anteriores,9 de correo por bytes y2 de compatibilidad de logging H07. Las22 fuentes seleccionadas permanecieron estables, incluidos los cuatro locks actuales, configuración, modelos y factories; ocho son archivos propios de este lote y14 son soporte registrado. [Ruff F821](auth-telemetry-privacy-quality.log) y AST de esos ocho archivos están verdes. La advertencia restante es la de Starlette/httpx ya observada; no hay advertencia de inicio/cierre del cliente Sentry. La integración R07 muta otros servicios en paralelo: este resultado no acepta almacenamiento, migraciones ni notificación en background.

## Contrato

- Los logs de contraseña y refresh conservan resultado/reason/revocación sin identidad, IP, versión de token o `jti`. La limpieza inicial de auth ya no formatea excepciones libres.
- Auditoría mantiene el registro DB actual autorizado; el logger recibe únicamente tipo de evento o clase de fallo. Su sesión propia usa `SessionLocal`, rollback al fallar y cierre incluso si commit/rollback fallan. Una sesión suministrada sigue bajo la responsabilidad del llamador.
- Correo conserva el payload autorizado de entrega; el logger sólo registra enviado, omitido por falta de configuración o clase de fallo. El transporte de prueba verifica que recipient/subject/body/adjuntos nunca se transforman para aparentar privacidad.
- Sentry utiliza proyección cerrada en error y transacción, no una lista de nombres secretos a tachar. Conserva clase, módulo propio/línea, IDs técnicos con formato cerrado, tiempos y categorías. Excluye los campos libres completos en cualquier profundidad, incluidos secciones futuras desconocidas.
- Un frame se acepta sólo si su módulo ya está cargado y pertenece a `web`, `api` o `core`; el filename se deriva del módulo. No se conserva texto de función, rutas recibidas, source context ni locals. Clases desconocidas se agrupan como `ApplicationError`, con pérdida de detalle explícita.
- Adjuntos se retiran del `hint` antes de crear el envelope, tanto en error como en transacción. Perfiles, sesiones automáticas y canales independientes logs/métricas están apagados; no se asume que el callback de evento los sanee. Traces estáticos sin streaming GenAI ni propagación saliente.

El SDK real2.72.0 serializa envelopes que la prueba inspecciona después del callback: sólo elementos `event`/`transaction`, sin adjunto/perfil y sin marcadores privados. Incluye request FastAPI con parámetros URL, header Authorization y body, `StatementError` con SQL/parámetros, captura de mensaje, excepción y logger ERROR. Una segunda familia verifica argumentos malformados sin incluir datos desconocidos en la proyección. Las pruebas de auditoría verifican además que IP/email permanecen en la fila local y no en su LogRecord.

La política de recolección usa opciones revisadas en el SDK instalado/pinneado. Referencia primaria: [API oficial Sentry Python2.72.0](https://getsentry.github.io/sentry-python/api.html), [`client.py` oficial2.72.0](https://github.com/getsentry/sentry-python/blob/2.72.0/sentry_sdk/client.py). La lectura local verificó que el envelope recoge `hint.attachments` después de `before_send` y que el perfil se maneja fuera del evento. Una actualización del SDK debe repetir esta prueba de envelope; no basta mantener el nombre del callback.

## Revisión independiente

El coordinador revisó los cuatro cambios de producto y el orden real de serialización de envelopes en `client.py` instalado. El gate independiente pasó106 pruebas en15.30s; incluye cuatro casos nuevos sobre integraciones predeterminadas del SDK, baggage entrante con identidad, headers finales de envelope, adjuntos y propiedad de las sesiones lectoras de auditoría. Las23 fuentes seleccionadas coinciden con el freeze autor, más la prueba nueva. [JUnit](pytest-auth-telemetry-independent.xml), [fuentes](auth-telemetry-independent-source.json). Transportes sólo en memoria; no acredita configuración ni retención del servicio real.

## Alcance pendiente

La aceptación independiente del lote no está incluida en el número autor. No se revisaron con este cambio todos los loggers, integraciones de proveedores, notificaciones directas, access logs de Uvicorn/proxy/hosting ni configuración de retención/acceso/región de Sentry/Resend. La metadata libre del audit persistido, los tokens en localStorage, el resto del export y el borrado transversal siguen sujetos a R31 y requisitos relacionados. No se afirma cumplimiento legal ni seguridad total.

## Adaptación de adjunto para R07

`send_plan_generated` conserva `pdf_path` legacy y añade `pdf_content` keyword-only. Si se suministran bytes, no abre `Path`: valida tipo `bytes`, header `%PDF-` y tamaño entre1 y `MAX_OBJECT_BYTES`; entrega exactamente esos bytes con filename constante `plan.pdf`. Un payload inválido retorna `False` sin entrega ni fallback a la ruta legacy. La autoridad sobre destinatario/tenant/plan pertenece al caller; este helper no convierte bytes recibidos en prueba de autorización. No crea archivos temporales ni interpreta claves de storage.

La inserción del nombre en HTML se escapa y el asunto retira CR/LF; no cambia el destinatario autorizado. Nueve casos propios verifican bytes exactos, precedencia de bytes sobre ruta, cinco payloads inválidos, ambas variantes de nombre y compatibilidad legacy sin adjunto/con archivo. [Baseline corregido](email-plan-bytes-baseline.log), [JUnit](email-plan-bytes-baseline.xml), [fuentes](email-plan-bytes-baseline-source.json):8 fallos/1 éxito,1.53s, incluidas capacidad ausente y la inserción HTML legacy. La primera preparación [antes](email-plan-bytes-before.log), [JUnit](email-plan-bytes-before.xml), [fuentes](email-plan-bytes-before-source.json), tiene además cinco errores del harness por un símbolo que aún no existía; se conserva y no se cuenta como reproducción del defecto. [Gate parcial posterior](email-plan-bytes-after.log), [JUnit](email-plan-bytes-after.xml):28 verdes junto a los19 controles de telemetría; la aceptación autor vigente es el gate final72 con huella, no ese ensayo parcial.

El camino `pdf_path` mantiene comportamiento legacy, incluida la lectura de archivo existente; este lote no lo presenta como resolver de objetos autorizado. El nuevo wrapper web, su apertura de sesión/tenant, envío diferido, reintentos y límites reales del proveedor corresponden a R07/R28 y requieren su validación aparte. Todos los envíos de estos casos usan `_send`/Resend doblados, sin correo real.

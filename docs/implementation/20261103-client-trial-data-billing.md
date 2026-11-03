# Datos y suscripciones para la prueba web con clientes

Fecha: 2026-11-03, America/Mexico_City. Sólo servicio web; Linux y desktop quedan fuera. Trabajo coordinado con máximo cuatro agentes activos incluyendo al principal; roles rotados con QA y seguridad independientes.

## Alcance y fuente publicada

La lectura autenticada actual de QA observó `fc7950ec341371b4354cba30ffd6c9a9860336fd`, deployment `356637a8-b4fe-4996-b491-aec3c5ab9efd`, a las 2026-11-03T19:35:28Z. Salud, readiness, portada, registro y accesos respondieron 200; las lecturas anónimas privadas de suscripción/PDF respondieron 401. Los cuatro precios live mensuales en MXN coinciden con el catálogo. Son lecturas: no se hicieron cobros ni cancelaciones de clientes, cambios de configuración o envíos de correo.

El código preparado en esta tarea parte de esa fuente en un worktree aislado. No incorpora el candidato posterior `f69058f4`, sus migraciones o cambios financieros. Los resultados se separan en: observación productiva actual, reproducción aislada de fuente Git exacta, delta de información de privacidad y recuperación de un respaldo anterior. No se atribuyen compras sandbox históricas de otra fuente a esta versión.

## Información de privacidad preparada

El usuario indicó como único contacto `consultoriahernandez@icloud.com` y dejó pendiente la razón social. El domicilio no se recibió. Se prepara `GET /privacidad` en ambas factories con información factual y estado explícito de preparación, enlaces desde registro/portada/ambos espacios y aclaración de cancelación en ambas suscripciones.

La proyección pública no contiene secretos, datos de cuenta o el inventario jurídico interno. No inventa un responsable, no publica `null` o placeholders como contenido, no añade consentimiento ni infiere aceptación de un registro, una visita o Google. La página informa de contacto y de la diferencia entre cancelar una renovación y solicitar acciones sobre datos; no constituye un aviso integral completo ni cierra la revisión jurídica. Completar datos del negocio no equivale automáticamente a aprobar un aviso.

Quedan pendientes identidad y domicilio del responsable y revisión del contenido integral, incluyendo finalidades/categorías, tratamiento de datos sensibles, terceros, derechos, conservación, supresión, incidentes y cambios del aviso. No se fija una retención o plazo jurídico sin decisión revisada. El contrato y las fuentes oficiales se conservan en la evidencia de seguridad de esta tarea.

## Contrato de suscripción y conservación

- La contratación y activación requieren confirmación autoritativa del proveedor y permisos del actor persistido.
- La cancelación al final del periodo conserva acceso hasta la vigencia confirmada; la interfaz no debe confundirla con cancelación inmediata.
- Al vencimiento, negocio vuelve a Free y personal a Starter según la política vigente. Cambiar a Starter no cancela por sí mismo un cobro en Stripe.
- Cancelar o vencer no implica borrar la cuenta, clientes/perfil, historial, PDF o reiniciar el consumo. Solicitar supresión de datos es un procedimiento distinto.
- El historial/PDF propio mantiene su autorización, y otra cuenta no adquiere acceso por conocer un identificador o referencia de archivo.

Las pruebas aisladas y sus límites se registran en los dictámenes finales. Un proveedor simulado permite comprobar el contrato del código, sin acreditar por sí solo una transacción live. No se cargó dinero ni se alteraron suscripciones reales para probar.

El ensayo adicional con Stripe test completó dos ciclos, Standard y Pro, usando la cápsula Git exacta `fc7950ec`. Verificó cuenta y `livemode=false` antes de crear actores sintéticos sin correo, confirmó pago con los servicios publicados, programó cancelación al final del periodo y avanzó relojes de prueba para comprobar el regreso a Free/Starter. Se conservaron SQL, bytes PDF y consumo personal de tres usos; el PDF ajeno fue rechazado. Ambas suscripciones de ese ensayo quedaron canceladas, la fuente permaneció estable y el cierre fue aceptado.

Este ensayo usa API saliente real del proveedor y dominio local aislado. No acredita compra UI, entrega de OTP, transporte HTTP de webhook real ni cargos live. La firma/transporte HTTP con proveedores simulados tiene evidencia QA separada. La revisión independiente de seguridad y los recibos se conservan en `backend/sandbox-published-fc/` y `security/`. El intento anterior del instrumento falló antes de cualquier mutación por un argumento Python en conflicto; se conserva separado del ensayo aceptado y no se atribuye a producto.

## Recuperación comprobada

El 2026-11-03 se repitió una recuperación nativa en una cuarentena privada nueva, utilizando el dump cifrado capturado a las 2026-11-03T01:12:42Z y el archivo de objetos capturado a las 01:38:37Z. No se consultó o modificó producción durante esta recuperación.

Se autenticaron ciphertexts y recibos, se descifró en memoria, se restauró SQL en una base vacía del esquema 40 y se cotejaron los descriptores SQL con los tres objetos recuperados. Se verificaron tamaño/SHA, lectura del propietario y denegación de otra cuenta. El rol SQL restringido no puede saltarse RLS; sin tenant no ve las veinte familias protegidas. Se preservaron los fingerprints de las 44 tablas/286 filas, sin migración, downgrade o borrado, y el cluster cerró normalmente con puerto y pidfile ausentes.

Las capturas SQL/objetos fueron separadas: el cotejo positivo de descriptores no supone una pausa coordinada de escritores. Esta copia no acredita datos posteriores a su fecha, no recupera cuarenta referencias históricas sin bytes y no es una agenda de respaldo periódico externo. La clave sigue segregada, con ACL privada; separar carpetas del mismo equipo no protege contra su pérdida completa.

Cualquier restauración destinada a servir usuarios necesita además el registro externo fresco de supresiones y su aplicación antes de habilitar acceso. La cuarentena de esta tarea no sirve aplicación ni está autorizada para promoverse sobre producción. La automatización externa, retención, custodia independiente, responsable y objetivos de pérdida/recuperación siguen requiriendo definición operativa; se conserva el plan actual de Railway.

## Registro y evidencia

La aceptación independiente de QA comprobó 21 casos distintos sobre una cápsula de 572 blobs Git exactos de la versión publicada: contratación de los cuatro planes, activación sólo ante evidencia válida, cancelación, reactivación, conservación, idempotencia y aislamiento. Incluye conservar doce clientes y doce PDF al pasar a Free, rechazar lecturas ajenas y bloquear nuevas altas por cuota sin borrar la cartera. El proveedor está simulado en este conjunto; sus tres fases de 12+8+1 casos tienen recibos propios.

Backend comprobó separadamente 30 casos de conservación y regresión sobre una cápsula de 584 blobs Git exactos. No se suman estos conjuntos como cobertura global. Los intentos anteriores del instrumento quedan conservados con sus errores y límites.

Para el delta de privacidad, QA aceptó 15 casos con fuentes estables: ambas factories, información de preparación, cabeceras, escape HTML, contacto fijo, ausencia de SQL/consentimiento y conservación de la cookie técnica CSRF existente. Frontend V3 comprobó navegación sin JavaScript y composición a 320/390/1440 píxeles, con once capturas, sin errores o desbordes; axe A/AA se aplicó a la página nueva. Root revisó las capturas de privacidad en móvil y escritorio, Ruff de los tres archivos Python nuevos y `git diff --check`. Los trece archivos vinculados por QA seguían coincidiendo al leerlos después de finalizar frontend.

Operación revisó independientemente el driver de recuperación, 121 fuentes vinculadas, ambos ciphertexts y siete fronteras con DACL protegida para propietario/SYSTEM. El puerto propio cerrado y el pidfile ausente se comprobaron de nuevo; no se repitió otra restauración.

Evidencia raíz: `E:/MetodoBaseWorkspace/evidence/client-trial-web-20261103-994c1bb0/`.

- `ORQUESTACION.md`: propietarios, archivos, contratos, dependencias, oleadas y criterios de cierre.
- `qa/current-runtime-20261103T193528778159Z.json`: lectura productiva sanitizada.
- `backend/`: conservación y regresiones de dominio con source bindings.
- `qa/`: aceptación independiente y cápsula de fuentes Git exactas.
- `frontend/`: recorridos y capturas de las superficies nuevas.
- `security/`: contrato, fundamento oficial y dictámenes independientes.
- `operations/current-pg-restore-receipt-4f7f27ba02dd4b168d253d84e0a8b261.json`: recuperación SQL/objetos PASS, cierre normal, cero conexiones productivas.

El resultado final debe distinguir preparado, probado y publicado. Este documento no registra un despliegue de la página nueva ni aprobación comercial/jurídica global.

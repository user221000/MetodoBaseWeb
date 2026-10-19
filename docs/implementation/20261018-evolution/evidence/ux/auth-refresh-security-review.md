# SEC02: revisión independiente del transporte de autenticación

Revisión sobre `api.js` SHA256 `275506e8e8e769b37ddd1b679cd56b8d045dfb5e27bf555156587f23779a91df`, HEAD `bd6b067c1e6185493e3d2dad38f0621e72a28355`. No modifica producto, pruebas autor ni reproducciones root. Sólo añade `tests/e2e/auth_refresh_security_review.cjs`.

[Resultado rojo](auth-refresh-security-before.json), [fuentes](auth-refresh-security-before-source.json):12 aprobadas/13, exit1, seis fuentes estables. VM y transporte de memoria; no importa factories/modelos/DDL26 ni usa servidores, sockets o proveedores. Cada operación tiene un timeout para que un coordinador atascado produzca fallo. El driver imprime JSON `total`, `passed`, `results` y devuelve exit distinto de cero si falla algún caso.

## Controles aprobados en esta etapa

Cambio de sólo access o sólo refresh, ABA mediante `clearTokens`/`saveTokens` aun con valores idénticos, cola mixta JSON/multipart/export frente a cambio de cuenta,401 muy tardío tras dos rotaciones legítimas,401 de retry tras otra rotación, invitaciones públicas sin Bearer/refresh, multipart con bytes originales sin Content-Type JSON, fallo de red tardío, logout que comparte refresh antiguo y recuperación del coordinador tras credenciales incompletas del refresh. Estos12 controles no constituyen aceptación del conjunto mientras haya un fallo independiente.

## Bloqueo adicional reproducido

El caso13 no necesita una carrera entre pestañas:

1. El par persistido pertenece a A. `saveTokens(B)` logra escribir `mb_token=accessB`.
2. La escritura siguiente de `mb_refresh_token=refreshB` lanza `QuotaExceededError`; persiste el par mezclado `accessB`/`refreshA`.
3. Se intenta una mutación preparada para B; su primer envío con accessB responde401.
4. El helper acepta refreshA como autoridad de la supuesta misma sesión, almacena la rotación A1 y repite el DTO de B con accessA1.

El transporte sintético trata A/A1 como credenciales válidas de A y B como access vencido; la reproducción observa un segundo PUT con el DTO de B autorizado como A. La prueba también rechaza una supuesta solución que restaure A y envíe inmediatamente el DTO con su access original. La operación posterior debe quedar rechazada hasta que el estado de credenciales pueda establecerse explícitamente de forma completa.

El fallo se inyecta en una llamada concreta de `Storage.setItem`, cuya posibilidad de lanzar `QuotaExceededError` está especificada por [HTML Standard: Web Storage](https://html.spec.whatwg.org/multipage/webstorage.html#the-storage-interface). No se afirma haber agotado la cuota real de un navegador ni haber observado explotación. El mismo estándar tampoco promete un bloqueo global entre procesos; el límite entre pestañas sigue separado.

Root aceptó conservar este rojo y pidió contención ante escritura parcial en `saveTokens`, refresh y clear, sin restaurar ni sobrescribir credenciales de una sesión externa. El agente de revisión no implementa esa corrección. La repetición posterior debe conservar esta evidencia y enlazar una huella nueva; no debe rebajar el caso a una omisión para obtener verde.

## Límites

La suite comprueba el orden y autoridad del transporte cliente con tokens sintéticos, no firmas JWT, RBAC, persistencia backend ni ejecución de una mutación real. No prueba atomicidad entre procesos/pestañas, XSS, todos los escritores directos de localStorage, durabilidad del almacenamiento ni cierre de R10. La composición real deberá reiniciarse con el runtime26 congelado antes de atribuir el navegador a ese candidato.

## Seguimiento independiente del bloqueo de Storage

Frontend entregó un segundo freeze de dos fuentes: [manifest](auth-refresh-storage-source.json), SHA256 `f4bf42a20afb9c55225a060e6e8810fab3b64548a93277279fe6e2b1b14bb501`; `api.js` pasa a `347242a6319c5672df08e4393f4c31351f436ee3b20f12653c444020925950a3`. Las13 pruebas propias y las2 de root mantienen sus bytes y se conservan los artefactos rojos anteriores.

[Repetición independiente](auth-refresh-storage-independent-source.json):74 de74 aprobadas, exit0 en los cuatro drivers y cinco fuentes estables. Desglose:13 casos propios,33 de regresión autor,26 de fallos Storage autor y2 reproducciones root. Los cuatro reportes JSON están enlazados desde ese manifiesto; éste no reutiliza la ejecución del autor como si fuera independiente.

Revisión de código: `_persistPair` marca el estado como no confiable antes de modificar credenciales y verifica readback tras cada paso. Un fallo o discrepancia mantiene el bloqueo; leer el par o recibir un evento storage no permite adoptar automáticamente ese estado. JSON, PDF, logo, export y refresh comprueban la confianza; una cola antigua no puede instalar su rotación tras el fallo de guardado. Sólo un save o clear explícito completo devuelve confianza a esta instancia. No hay rollback de credenciales que pudiera sobrescribir la sesión externa; una recuperación explícita posterior completa conserva prioridad.

El nuevo caso13 pasa sin relajar su condición: tras el guardado parcial no se despacha el DTO posterior bajo A. Esta aceptación se limita a las fuentes y al alcance VM registrados. La confianza sigue siendo memoria de una instancia; no persiste una marca de fallo al recargar y las dos claves continúan expuestas a escritores legacy y cambios de otras pestañas. No se repitió navegador ni se importó app/modelos durante esta revisión; R10 y la validación de composición sobre runtime26 continúan abiertos.

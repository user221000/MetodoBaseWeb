# R17: bloqueo de política privada en errores operativos

Fuente fee219929ac2c6a16cc8d8a6bec42cb757245a4e en checkout propio, sin overlays ni edición de producto. Driver independiente inmutable8ab728f0…:24 casos,12 controles verdes y12 rojos reales. Dos casos de historial acotado pasan aparte; no se suman los52 del autor ni sus103 dirigidos como aceptación independiente.

Las tres rutas canónicas /metrics, /alerts y /health/circuits devuelven correctamente200 autorizado y403 opaco con headers privados. Configuración ausente queda cerrada; cada factory conserva su key incluso si cambia el entorno o se crea otra app. Bearer/query/cookie/headers falsos y valores noASCII no reemplazan el header. La comparación recibe bytes UTF8; no se exponen valores. La serialización de Enum de alerts funciona con200 y política privada.

Hallazgo:2factories×3rutas×2salidas=12 fallos. OPTIONS se rechaza405 pero sin Cache-Control/Pragma y con Referrer-Policy strict-origin-when-cross-origin. Un fallo sintético del lector autorizado genera500 opaco sin los tres headers. El helper privado sólo decora el GET que llega a producir respuesta; ambos caminos externos lo omiten. No se demostró fuga, acceso sin key, redirección ni eco del marcador de excepción. La revisión pide la misma política privada en errores de estas tres rutas exactas; no un catch global ni ampliar a vecinos.

Los controles restantes verifican métricas fuera de los otros middlewares:503 temprano y excepción real500 cuentan una vez con ruta declarada o fallback fijo; no conservan query, sujeto, IP/headers/body, key ni parámetros de excepción. Un factory deshabilitado permanece deshabilitado tras cambiar env; el default explícito se activa aunque el valor global importado fuerafalse. Contadores127 completos por factory sobreviven a historias de7 y100 errores y sólo dos labels, pese a sujetos y URLs404 distintos. No es prueba de carga, p95 ni agregado distribuido.

Se revisó el delta histórico del test de excepción: conserva ID y añade docstring explícito; el requisito de0 registros pasa deliberadamente a1 registro500 con ruta fija y no_identity. No se retira una aserción de privacidad. Los tests/criterios del autor no se editaron. La cobertura del autor no incluía estos405/500 operativos.

Las10145 fuentes y89 paquetes propios conservan bytes/versiones antes/después; módulos importados proceden del checkout propio. Los seis productos están autenticados como GitLF y se distingue su RAW de autor. La fotografía propia inicial no hashó por separado python.exe; el hash actual coincide con el before/after congelado del autor. No se atribuye una foto propia inexistente.

Sin PG, Chrome, VM, proveedores, alertas/correo real, cambios de dependencias ni MAINproducto. Quedan fuera streaming completo del body, agregación entre procesos, retención, operación real y aceptación global R17/R31/ASVS. El bloqueo se limita a headers de error; RAW, XML, driver y12 proofs originales quedan privados íntegros.

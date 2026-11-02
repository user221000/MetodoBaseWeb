# Contratos de esta ejecución

La guía es [Auditoría y faltantes](../../audits/20261102/AUDITORIA_Y_FALTANTES.md). La base de código es `fc7950ec`: conserva la contratación Stripe sin activar otro factor de cuenta, posterior al corte de aquella auditoría. Esta documentación describe el candidato; no acredita su publicación.

## Devoluciones parciales y evidencia monetaria

El usuario confirmó mantener el acceso hasta acabar el periodo ya pagado cuando sólo se devuelve parte de una mensualidad. Se conserva el tratamiento anterior de devolución completa. Una observación parcial no amplía el periodo, reinicia consumos ni revoca una renovación posterior pagada por otra factura.

El esquema `20261102_payment_refund_facts` añade a `payments` tres columnas opcionales: importe devuelto acumulado, instante UTC de observación e identidad interna del cargo. Las filas históricas conservan NULL; no se infiere que no tuvieron devoluciones. Los CHECK de SQL vinculan rango, identidad, observación y estado (`succeeded`, `partially_refunded`, `refunded`) cuando hay datos conocidos. El importe tras devolución es original menos devolución conocida: no incorpora comisiones, impuestos o fecha de abono bancario. No se crea un ledger individual de cada devolución.

La identidad y los fondos proceden de recursos actuales del proveedor, comprobados bajo el bloqueo transaccional de la cuenta. Dentro de una conciliación, lecturas de la misma factura deben conservar sus hechos monetarios y de identidad. El comparador incluye presencia, tipo y valor: ausencia de un campo no equivale a NULL, ni un booleano a un entero. Una contradicción produce un fallo reintentable y rollback conjunto de acceso, pagos, consumo e inbox. El intento no queda confirmado como pendiente después de haber usado otra evidencia para conceder acceso.

La revisión independiente conservó tres reproducciones rechazadas: devolución completa entre consultas, primera devolución parcial entre consultas y captura opcional que cambia de ausente a NULL. Sus resultados originales no se sustituyen por los reruns corregidos.

## Historial personal y de negocio

`GET /api/billing/payments` y `GET /api/usuario/payments` usan el mismo DTO de respuesta. El personal se registra una sola vez en cada factory y lee el ID del actor autenticado, incluido su espacio personal si pertenece a un equipo. No adopta el gimnasio del equipo ni un ID enviado como query. La ruta conserva autenticación fresca, límite 1–100, rechazo de roles ajenos y aislamiento de datos. Mantiene la referencia de factura ya existente en el contrato; la nueva identidad interna del cargo y el PaymentIntent no se exponen.

Ambas pantallas comparten presentación y traducción de estados. La información desconocida o incoherente aparece como «Sin dato confirmado». El código escribe texto, evita interpretar HTML y descarta respuestas tardías después de cambiar de sesión, incluso si el guard ya retiró el DOM. La vista de historial es de lectura: no activa derechos ni calcula nuevos periodos.

## Controles vigentes y evidencia histórica

Los companions41 autentican las fuentes39 completas y cada sustitución declarada de revisión, ruta o fuente vigente. Conservan asserts y funciones, y se prueban modificaciones que deben ser rechazadas. Los controles originales, RAW y recibos rechazados permanecen intactos. Los 96 criterios actuales de rutinas se trazan contra las 94 obligaciones históricas; no se presenta esa diferencia como un PASS de la fuente antigua.

La ampliación final incluye 18 fuentes y un mapa de 76 consumidores que conserva los75 anteriores y añade privacidad HTTP sobre migración genuina41. Tres oráculos de parciales cambian sólo su función aprobada y añaden importe observado; sus deltas AST son explícitos. Los controles de release corrigen nueve valores literales de evidencia/opciones41, conservando los atributos privados39 del observador delegado. El gate integrado previo363 conserva346PASS/17FAIL; el cierre posterior ejecutó los220 controles de fuente y54 de release sin fallos. No se reetiquetó el intento anterior ni se volvió a ejecutar la parte financiera ya aceptada sin cambios.

Bandit conserva cinco ocurrencias históricas y retira sólo la observación MD5 que dejó de existir. La revisión nueva se limita a 26 ocurrencias técnicas y a 392 fuentes exactas, con aprobación independiente y de coordinación, vencimiento y controles negativos. Las dos ocurrencias de construcción Docker dependen del contexto finito verificado; su clasificación estática no acredita aislamiento o una imagen construida. La transición Docker se valida mediante inversa exacta del sufijo de producción; no se modifica el Dockerfile.

La clasificación de secretos reconoce cuatro ubicaciones públicas o sintéticas por bytes, línea y regla exactos, con transportes LF/CRLF explícitos. No admite secretos nuevos, ubicaciones movidas o copias duplicadas. Una revisión de esta clasificación y un escaneo completo del entregable son comprobaciones separadas.

El inventario nuevo contiene 185 operaciones efectivas API y 204 Web, equivalentes a 210 pares método/ruta. No tiene duplicados. [Matriz de operaciones](../../audits/20261102/seguimiento/OPERACIONES.csv), [diferencias y metadatos](../../audits/20261102/seguimiento/RESUMEN_API.json) y [siete pantallas prioritarias](../../audits/20261102/seguimiento/TRAZA_PANTALLAS.json) conservan su alcance: inventariar y rastrear una ruta no demuestra todos sus permisos, persistencia o recorridos.

Las pruebas de SDK controlado, navegador con HTTP interceptado, HTTP/SQL real, PostgreSQL, recuperación de datos y sandbox del proveedor se informan por separado. No se suman conjuntos solapados como cobertura total. La configuración de precios, cuotas, versiones SDK/API y disponibilidad de Mercado Pago no cambia en este candidato.

## Transporte finito del escaneo canónico

El escaneo físico completo rechazó1274 ubicaciones; el primer escaneo Git completo del commit2009fb8a rechazó2250 en90 rutas. Sus recibos se conservan. Dos revisores independientes comprobaron los90 blobs contra2009/fc795 y cada wholefile CRLF contraV9; QA verificó además línea, regla, digest y multiplicidad. Cinco spans cambian columnas entre frames y se fijan por separado.

El puente adicional exige ZIP autenticada, fuente completa, longitud, inventario, línea, columnas, regla y digest exactos; una ubicación completa sólo puede usarse una vez. Para esas90 rutas no existe fallback al lector anterior si falla la admisión. Fuera de ellas conserva la delegación, y el adaptador sin documento adicional mantiene la rama anterior. No hay normalización genérica en producción del lector, ampliación de fechas o reescritura deV9/RAW. Los37 controles nuevos,166 históricos originales y la revisión independiente no sustituyen el siguiente escaneo completo del commit ni la CI real.

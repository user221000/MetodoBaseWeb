# Revisión independiente de seguridad: B2B, configuración R07 y empaquetado

Revisor security_privacy; fuentes de producto no editadas. [Huella B2B](security-b2b-review-source.json): las 17 fuentes coinciden con `backend-b2b-source-after.json`. La revisión no sustituye las pruebas PG/concurrencia/restauración de QA ni atribuye esos resultados a una ejecución propia.

## Hallazgo reproducido y corregido en seguimiento

En ambos adapters `generar_plan`, la rama `except ValueError` llama a `fail_gym_generation` sin proteger una excepción de compensación. Si esa operación falla, la excepción llega al handler global, que registra `str(exc)`. Se reprodujo con un `StatementError` cuyo parámetro contiene un marcador privado sintético: el log incluye SQL y parámetros. El cuerpo HTTP permanece genérico; la exposición demostrada es en logs. La rama `except Exception` ya captura el error de compensación y registra sólo su clase.

[Prueba independiente](../../../../tests/test_gym_generation_security_review.py): factories web/API reales, JWT y principal persistidos, aislamiento de solicitud y reserva real. Sólo CPU y compensación fallida son doubles explícitos, sin auth/API/tenant mock. Resultado: dos casos ValueError fallidos y dos RuntimeError aprobados, 6.71 s. [Log](security-b2b-compensation-before.log), [JUnit](security-b2b-compensation-before.xml). Todos los datos son sintéticos; no se contactó un proveedor.

Se propuso proteger también la compensación del fallo de dominio, conservar la reserva para reconciliación si la compensación no se confirmó, emitir código público estable y registrar clase/código sin SQL/parámetros. Root recibió el hallazgo antes de modificar producto y conservó el freeze hasta terminar el gate amplio. Después implementó el helper compartido con rollback protegido y HTTP 503 de reconciliación; security_privacy corrigió los handlers/tracker globales en su ownership separado. [Seguimiento, límites y regresiones](security-error-privacy.md). La huella original de 17 fuentes describe la lectura anterior a esas tres modificaciones posteriores de root; el nuevo manifiesto del seguimiento registra la combinación ensayada.

## Aspectos revisados sin otro bypass directo observado

La autoridad de ambos adapters procede del principal persistido/RBAC; el payload de plan no elige gimnasio. El worker vuelve a comprobar cliente activo, tenant y `deleted_at`, y propaga contexto explícito. La publicación revalida el cliente/reserva/tenant por CAS. Una desactivación después de cargar el cliente no revoca retroactivamente el trabajo ya aceptado; los nuevos trabajos se rechazan y el replay completado conserva el historial mientras no esté borrado, conforme al contrato acordado.

Las decisiones de capacidad y generación se serializan por fila de cuenta antes de crear cliente o reservar CPU. El hash canónico liga la clave a los campos del DTO; los replays completados devuelven el JSON persistido. Día y mes se capturan en America/Mexico_City y se comparan con límites UTC naive explícitos. Las reservas activas/completadas y los planes históricos no vinculados se cuentan una sola vez. `persisted_at` sobrevive a la FK nula y la restricción impide `released` con publicación persistida. Un fallo o crash posterior a publicación conserva el consumo para reconciliación.

Los nuevos nombres PDF contienen UUID opacos y no usan nombre del cliente ni resolución de segundos como identidad. La tabla 24 tiene `ENABLE`/`FORCE RLS`, predicados `USING`/`WITH CHECK` de tenant y snapshots físico/de seguridad revisables. Las consultas usan parámetros SQLAlchemy; no se encontró SQL construido a partir del payload. No se efectuó borrado, migración o ensayo contra datos compartidos/productivos.

Los jobs/outbox, recuperación tras crash, entrega de email, almacenamiento durable/metadata y keys persistidas en UI siguen en sus requisitos correspondientes. Un gate de cuotas no los declara completos.

## Configuración R07 aceptada dentro de su alcance local

[Gate independiente](security-storage-configuration.log): **32 aprobadas, 2.42 s**, 27 del autor más cinco independientes, [fuentes estables](security-storage-configuration-source.json). SDK target separado, `--noconftest` y guard de sockets externos; sin DB, bucket, proceso de credenciales ni servicio real.

Se verificaron credenciales/region/endpoint explícitos, ausencia de fallback local, construcción sin uploads, límites de red/reintentos y endpoint HTTPS. HTTP sólo se admite en loopback de desarrollo. Config/variables de AWS, credenciales heredadas y un perfil compartido no reemplazan endpoint, credenciales o presupuesto explícitos; `credential_process` no se ejecuta. La ausencia de session token explícito no hereda uno del entorno.

La lectura encontró que un endpoint inválido podía contener credenciales/query en `repr` antes de validar; root ocultó ese campo antes del gate. Tres casos independientes confirman que ni representación ni error incluyen los marcadores, y que se rechaza antes de construir SDK. No queda ese hallazgo pendiente dentro del contrato ensayado.

Esto no verifica permisos privados/region/retención reales, imagen Linux, montaje durable, reemplazo de contenedor ni consumidores de producto. La integración S3 deberá incorporar su SDK al target runtime con hashes y conservar estos gates; el SDK usado aquí pertenece únicamente al entorno aislado de pruebas.

## Dockerfile y requirements desktop

Se revisaron el Dockerfile candidato y `requirements.txt` desktop, con hashes en el manifiesto de revisión. Docker consume el lock web con `--require-hashes`, fija digest de Python, ejecuta con usuario no root y readiness local; no añade secretos mediante `ARG`/`ENV`/COPY de dotenv. El manifiesto desktop conserva su target separado y no se usa para instalar el servidor. No apareció un hallazgo alto nuevo por inspección.

La imagen sigue sin construir/ejecutar en este host por el bloqueo de virtualización ya documentado. Esta revisión no acredita digest final, SBOM/SCA de imagen, runtime Linux o permisos de un volumen montado. Esos límites permanecen abiertos; no se intenta Docker ni se modifica el sistema para eludirlos.

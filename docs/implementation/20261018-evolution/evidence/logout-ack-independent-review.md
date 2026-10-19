# Revisión independiente del ACK de logout

Aceptado localmente para el cambio aditivo de `web/routes/auth.py`: devuelve `success: true` después de que el helper existente confirma la transacción de revocación. El texto anterior de `message` se conserva.

Resultado independiente: **13 casos aprobados, cero fallos, errores u omisiones**. Los 18 archivos congelados conservaron sus bytes durante la ejecución, incluidas las evidencias originales antes y después del autor.

- Seis casos del contrato del autor, repetidos en ambas factorías reales: éxito, excepción previa al commit y excepción después del commit, esta última con revocación durable y respuesta HTTP 500 sin ACK. Consultan el estado persistido y prueban los bearer y refresh anteriores mediante HTTP.
- Cuatro casos propios con ambas factorías: solicitudes anónimas o con bearer malformado reciben 401 sin ACK ni revocación; un cuerpo que menciona otra cuenta no cambia el sujeto del logout; la cuenta ajena conserva access y refresh; repetir logout con el access revocado recibe 401 y no vuelve a incrementar la versión de sesión.
- Tres regresiones históricas, sin modificación: logout revoca access y refresh; logout durante la rotación no resucita sesiones; logout invalida access legado con época cero.

La ejecución usa SQLite temporal sintético, proveedores desactivados y el bloqueo de sockets externos del lanzador aislado. No acredita PostgreSQL ni aislamiento de red del sistema operativo. No modifica el orden de bloqueos de la transacción existente. La confirmación del consumidor web y sus cambios de cuenta siguen sujetos a la revisión independiente de frontend y seguridad.

El contrato anterior solo incluía `message`; no debe interpretarse retrospectivamente como un ACK booleano. La prueba original anterior queda preservada con 2 fallos y 4 aprobaciones, y la posterior con 6 aprobaciones. Una respuesta vacía o con `success: false` no constituye este ACK.

Fuentes, comando exacto, límites y resumen JUnit: `logout-ack-independent-source.json`. Ejecución: `logout-ack-independent.log` y `logout-ack-independent.xml`. Pruebas propias: `tests/test_logout_confirmation_review.py`.

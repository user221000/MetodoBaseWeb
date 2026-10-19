# QA independiente de la interfaz bf46

Aceptada localmente en `bf46e163f82a318873c4da6b460609520eb80d85`: **25 grupos de navegador** aprobados (17 históricos del autor, 4 nuevos y 4 propios históricos) y **162 casos VM únicos** aprobados. El driver de controles repite 17 casos del consumidor: son 179 observaciones, sin contarlas como casos únicos adicionales.

La fixture propia escucha exclusivamente en 8789 y prepara SQLite temporal mediante metadata, objetos privados locales y dos cuentas VIEWER registradas por HTTP real. Auth, logout, refresh, diario, worker, PDF y exportación son reales. Welcome usa el doble explícito sin envío y se bloquean los sockets Python externos. Esto no acredita migraciones Alembic ni PostgreSQL.

El replay histórico persiste primero los datos que necesitan los casos posteriores. Las cuatro regresiones nuevas comprueban el intervalo entre helper y consumidor, el intervalo después de verificar el contexto al repetir una parte, la invalidación síncrona del archivo preparado ante un evento de Storage y la pérdida del ACK booleano después del logout durable real. Las cuatro propias conservan los controles de refresh previo al logout, pérdida completa de la respuesta, fallo parcial de Storage y respuesta del diario retenida durante logout en otro contexto.

Se conservaron los cuerpos de pruebas y sus aserciones. Las copias solo cambian los puertos y directorios declarados, con reversión exacta comprobada. Un envoltorio de seguridad independiente exige el origen exacto de 8789 y `maxRedirects=0` en API y fetch de rutas. Registró 78 llamadas API y 10 fetch de rutas; abortó 38 intentos de otros orígenes antes de entregarlos. No constituye aislamiento de red del sistema operativo.

Hay 12 capturas (8 del replay y 4 de las regresiones nuevas), sin errores de página, overflow ni violaciones axe en los ámbitos registrados. Se inspeccionaron visualmente el bootstrap a 320 y el estado de exportación descartada a 320. Axe en las cuatro regresiones nuevas cubre el bloque de exportación y el estado visible de logout, sin certificar todo el perfil.

Los 57 archivos del manifiesto `cfecc433a12a796cf7014a62311002535cb82fd787a90e62a8c76cbcba19ef7d` conservaron sus bytes. Los 42 archivos fotografiados al arrancar conservaron sus hashes hasta el cierre. Las evidencias históricas previas no cambiaron. Se validaron PID, proceso padre, ejecutable, comando y creación antes de cerrar exclusivamente el listener propio 16276 y su launcher 26976. El puerto 8789 quedó cerrado; 8776/15680 y 8777/30168 conservaron sus identidades.

La primera preparación del runner se detuvo antes de ejecutar producto: PowerShell devolvía código 1 al consultar un puerto libre con `-LocalPort`. Se preservan el runner inicial y sus dos inventarios. El runner corregido consulta la lista de listeners y filtra el puerto; no cambia pruebas ni producto. Toda la ejecución efectiva y su evidencia están en `run2/`, con resumen `run2/diary-ui-bf46-independent-source.json`.

No hay integración, despliegue, ejecución Linux, Actions, proveedor externo ni aceptación global del producto en este control. La revisión de seguridad independiente conserva su alcance separado.

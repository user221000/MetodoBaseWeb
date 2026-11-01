# Máquinas disponibles por gimnasio

El dueño puede guardar el inventario de su gimnasio en **Configuración → Máquinas de tu gimnasio**. La lista contiene 33 tipos de máquinas, estaciones y accesorios, agrupados y con búsqueda. Barras, bancos, mancuernas, discos y peso corporal se consideran equipo básico; no hay que marcarlos. Sólo el dueño puede guardar cambios; el equipo del gimnasio puede consultar el inventario.

El inventario se guarda por gimnasio, con una revisión que evita sobrescribir cambios de otra pestaña. No haberlo configurado y haber guardado una lista vacía son estados diferentes. Una lista vacía significa usar únicamente el equipo básico. Se conserva el resto de la configuración del gimnasio.

## Generación y biblioteca

En el espacio del gimnasio, el servidor obtiene las máquinas guardadas y las aplica tanto a los ejercicios principales como a sus alternativas. El cliente no puede habilitar máquinas mediante el JSON de requisitos. Se distinguen, entre otros, polea alta, baja y doble, estación de jalón con apoyo, Smith, rack con seguridades, prensa horizontal o a 45 grados, y las distintas máquinas de curl femoral. Una polea genérica no implica disponer de una estación de jalón.

La biblioteca conserva sus 91 ejercicios y señala los que no están disponibles. La página del gimnasio empieza sin sesiones publicadas hasta generar una propuesta con el inventario vigente. Si el dueño cambia las máquinas durante el cálculo, la propuesta se rechaza y hay que actualizar antes de regenerar. La lectura final usa otra sesión de base de datos para detectar ese cambio.

Se mantienen Push/Pull/Legs, seis a ocho ejercicios por sesión, actividad, experiencia independiente, objetivo, tiempo, variantes, exclusiones y calendario de tres a seis días. Si el inventario y los requisitos no permiten cubrir los patrones exigidos, se explica el problema: no se inventa equipo ni se reduce silenciosamente la rutina. Por ejemplo, sólo equipo básico puede resultar insuficiente para los requisitos de tirón vertical o flexión de rodilla. El espacio personal conserva su selección manual de categorías de equipo.

## Persistencia y permisos

- `GET /api/rutinas/equipamiento?context=gym`: lectura autorizada del inventario y catálogo de máquinas.
- `PUT /api/rutinas/equipamiento?context=gym`: sólo el dueño canónico, cuerpo estricto de hasta 16 KiB, `machine_ids` y `expected_revision`. Una revisión obsoleta devuelve 409 y nunca se reintenta automáticamente.
- `POST /api/rutinas/generar`: el contexto de gimnasio exige `expected_inventory_revision`; el servidor verifica inventario y permisos al generar y antes de publicar. El contexto personal no acepta esa revisión.

El esquema pasa de 39 (`20261023_privacy_disposition`) a 40 (`20261031_gym_equipment`). La migración sólo añade `gym_settings.training_equipment_json`, nullable, con límite de longitud; no reasigna clientes, no añade permisos ni cambia las políticas RLS. Se conservaron ENABLE/FORCE y los roles restringidos. El downgrade se niega si hay inventarios guardados; su comprobación falla de forma segura ante filas ocultas por RLS.

## Verificación

Evidencia privada en `E:/MetodoBaseWorkspace/evidence/gym-equipment-20261031-54511935cf4244e5ba8fcefe90c5fea3/`.

El gate integrado del inventario pasó **199 pruebas**, sin fallos, errores ni omisiones, con las fuentes estables. Los cinco módulos Node existentes también pasaron. La revisión independiente pasó 128 controles de motor/equipo, 40 HTTP reales en ambas factories, 15 Node, 39 Chrome y ocho PostgreSQL 18.6. Incluye permisos, aislamiento entre gimnasios, conflictos de edición, límites de cuerpo, rollback, cambios durante el cálculo, pantallas de 320/390/1365 px e impresión. No hubo errores de página ni llamadas externas. El navegador usa transporte aislado y datos sintéticos; no se atribuyen estas pruebas a cuentas reales ni a Google.

La migración se ensayó desde una base vacía y desde una restauración aislada de PostgreSQL 18.6: se conservaron 44 tablas de aplicación y 242 filas del respaldo preliminar, y se verificaron el contrato, la repetición idempotente, la vuelta atrás sin inventario y la protección de inventarios guardados. El respaldo preliminar no se tomó en mantenimiento y no sustituye al respaldo coordinado de la intervención.

## Preparación de publicación

La publicación sigue el [runbook de migración](../RUNBOOK_DB_MIGRATION.md). Los datos actuales deben respaldarse cifrados en E:, con la clave separada, verificar el manifiesto y ensayar su restauración en cuarentena. La pausa debe bloquear nuevas escrituras y acreditar el drenaje de solicitudes y trabajos antes del respaldo y del cambio de esquema.

Se detectaron 39 referencias históricas a PDF y una a un logo cuyos archivos ya no existen en el servidor. El usuario indicó: «esos pdf eran planes pasados no importan». Se registra esa exclusión histórica sin borrar filas o referencias y sin reconstruir archivos para aparentar un respaldo completo. El logo antiguo ausente también se registra; el logo y los documentos actuales disponibles en S3 se verifican por tamaño y checksum. El respaldo cubre la base completa y todos los objetos disponibles; no promete recuperar los bytes históricos ausentes.

El recibo final de respaldo, mantenimiento y publicación se guardará junto a la evidencia. Hasta que exista ese recibo no se considera desplegada esta función. La imagen anterior de esquema 39 no puede arrancar contra el esquema 40; no es un rollback compatible después de guardar inventarios.

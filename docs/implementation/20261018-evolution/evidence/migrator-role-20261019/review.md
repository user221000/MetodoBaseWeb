# Reparación histórica c4: separar roles de clúster del migrador

Estado: corrección de autor aislada desde a40d5dffe1d77760416dbe9ffaa51d3dfa6a0088;
pendiente revisión independiente e integración. Sólo cambia un archivo de producto,
la revisión c4f8e9d2a3b1. No hay revisión nueva, cambio de schema target, rol compartido
creado o revocado, elevación del migrador, fallback ni parche del bootstrap.

## Fallo y autoridad vigente

La imagen Linux99c (fuente bc365c13) falló con42501 al intentar CREATE ROLE
metodobase_app desde un migrador NOSUPERUSER/NOBYPASSRLS/NOCREATEDB/NOCREATEROLE.
La preimagen fuente LF d18036c9 y el JSON original Linux se conservan. El ensayo
de autor usa la instancia nueva17.11 SCRAM55484 entregada por Operación, con el
rol global realmente ausente; no cambia nombres SQL para simular esa ausencia.
El mismo productionSettings/CLI devuelve1/42501/InsufficientPrivilege y rollback
con cero tablas; la relación alembic_version no llega a quedar. La presencia del
rol permanece falsa. No se precrea ese rol para sortear el fallo.

CREATE ROLE administra entidades globales del clúster y exige CREATEROLE o
superusuario; no corresponde a un propietario DDL de una base concreta.
[PostgreSQL17 CREATE ROLE](https://www.postgresql.org/docs/17/sql-createrole.html).

La búsqueda de código encuentra ese nombre operativo sólo en c4: creación y
cuatro GRANT; runtime no hace SET ROLE ni selecciona ese usuario fijo. Las
políticas c4 y las20 actuales se aplican a PUBLIC, con contexto LOCAL de sujeto.
TO omitido significa PUBLIC, sin otorgar por sí solo privilegios sobre tablas.
[PostgreSQL17 CREATE POLICY](https://www.postgresql.org/docs/17/sql-createpolicy.html).
El contrato de despliegue configura roles app/migrador distintos, mismo destino,
grants DML/secuencias del app explícitos, app noowner/noBYPASS, y verifica el
esquema antes de auth. Se inspeccionaron bootstrap, env de Alembic, engine,
tenant_context, tenant_policy, firmas y activación R04/historia posterior.

## Delta compatible e inmutabilidad

Se eliminan exclusivamente el DO/CREATE ROLE y el bucle GRANT al nombre global.
Las4políticas, set_tenant SECURITY INVOKER/search_path, IDs/down_revision y
downgrade quedan idénticos; la comparación AST de todo el módulo lo prueba tras
retirar esas dos sentencias. Las34fixtures/targets/baselines22–28 conservan bytes.
Bootstrap no oculta errores ni crea tablas fuera de Alembic. No se pide CREATEROLE.

Una revisión posterior no puede arreglar un predecessor que aborta antes de que
se alcance su DDL; hacerlo exigiría saltar o falsificar la historia. Por eso es
una reparación explícita del recorrido histórico imposible en una instalación
nueva con el contrato de roles actual, conservando la lineage. Las instalaciones
con c4 aplicado no lo vuelven a ejecutar: conservan rol y ACL existentes sin
REVOKE, DROP o reasignación. No se afirma que esas ACL heredadas sean necesarias
o seguras universalmente; su revisión operativa sigue separada. Nuevas bases ya
no conceden permisos oportunistas al nombre global aunque éste exista.

En55483, donde el rol global sí existía previamente, la prueba antes alcanzaba28
pero encontraba16privilegios nuevos (4×4tablas) no solicitados para ese nombre.
Después queda cero ACL automática al rol. Otra prueba instala la historia
original completa hasta28 desde la preimagen RAW y luego ejecuta el CLI actual;
conserva exactamente las4ACL de tablas, estructura, políticas y helper previos.

## Pruebas y límites de evidencia

Antes:2rojos semánticos, uno en cada estado real del rol. Después:5casos PG55484
sin rol global y6casos PG55483 con rol presente, sin skips/errores/fallos. Cubren
vacío/repetición, prefijo936af15af980 con filas, rollback tras ejecutar realmente
las4políticas y helper tanto desde vacío como desde prefijo, más la instalación
histórica con ACL. El rol app distinto conserva20familias ENABLE/FORCE: DML propio
permitido; sin contexto0filas; UPDATE ajeno0; INSERT ajeno, DISABLE RLS y CREATE
ROLE denegados42501. Flags y ausencia de pertenencia al migrador se verifican.

19pruebas focales anteriores de bootstrap/URL/driver/factories/entrypoint pasan;
sus fuentes y expectativas no cambian. Ruff F/E9 de producto y driver pasa.
Cada tanda registra2327fuentes antes/después quietas. Las dos pruebas rojas
conservan exactamente sus aserciones y helpers; sólo se añade una prueba propia
de autoridad negativa del app después. No hay adaptación de nombre de rol.

Se crearon y cerraron exactamente17bases UUID y34roles UUID del autor; receipts
confirman ausencia y estado/miembros del rol legacy preservados. AdminSCRAM55484
se lee sólo en el child desde el pointer privado entregado; nunca entra en DSN,
CLI, logs o variables de entorno. Las URLs de roles efímeros permanecen sólo en
los procesos de prueba. No se modifica HBA/config ni roles ajenos. La instancia
55484 queda viva, con propiedad entregable a Seguridad, por instrucción root;
apagado y conservación del datadir se coordinan después de la revisión.

Esta evidencia es de Python/PG nativos Windows, con CLI production y datos
sintéticos. No se ejecutó Docker, imagen nueva, QEMU, Linux corregido, despliegue
ni proveedor. La reproducción Linux original es histórica y el replay Linux
corregido sigue pendiente del coordinador. No se integra en MAIN aquí.

## Replay independiente

Desde un checkout del commit entregado y el venv de QA, ejecutar el runner
aislado con tests/integration_restricted_migrator.py. Sólo se pasan paths/mode:
METODOBASE_TEST_ROLE_CLUSTER=handoff55484, METODOBASE_TEST_ROLE_HANDOFF_POINTER
al pointer público entregado y METODOBASE_TEST_ROLE_EVIDENCE a un directorio
absoluto nuevo; seleccionar -k 'not installed_historical'. Para el caso presente,
CLUSTER=qa55483 y METODOBASE_TEST_ROLE_QA_CONFIG al env.json privado registrado;
ejecutar los6casos. El driver valida puerto/host/destino explícitos y el estado
real esperado, falla si no coincide, genera recursos propios y no toca ajenos.
Es un harness local deliberado; no reemplaza las guardas globales R05 ni afirma
que la configuración privada exista en CI. No copiar credenciales a comandos.

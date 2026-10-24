# Fases nuevas de PostgreSQL38

Preparación de fuente; ninguna fase ha sido ejecutada. Este plan no cambia ni
redeclara los 429/53/27 casos, targets, fixtures o recibos37. Es una selección nueva
justificada por la tabla/producto38 y los nuevos mínimos de contraseña.

| Fase | Módulo nuevo | UUID totales/concurrentes | Pools propios |
| --- | --- | --- | --- |
| migration | integration_product38_migrations.py | 1/1 | migrator1/0; sin app persistente |
| core | integration_product38_postgres.py | 1/1 | app1/0, admin observador2/0, hasta2 workers app1/0 |
| password-http | integration_product38_password_http.py | 1/1 | app1/0 y admin1/0 |
| restore | integration_product38_restore.py | 2/1 secuenciales | un app1/0 y admin1/0 en cada UUID |

El owner603f conserva su engine1/0 y su contrato exacto, aunque core crea otro
engine admin2/0 para semilla/observación. Es necesario para mantener una Session
con lock de Usuario y consultar pg_stat_activity sin bloquearse en el mismo
pool1. Los cuatro canarios se reexportan como objetos originales de8eca sin tocar
sus cuerpos/globals; no se presenta el conjunto concurrente como un único pool1.
Todos los engines/Pools propios quedan dentro del ledger e905 y se cierran antes
de cero sesiones/DROP normal/ausencia fresca; los desconocidos y préstamos vivos
siguen rechazándose. No hay FORCE, terminate, restart ni fallback SQLite.

La migración ejecuta la cadena real37→38, conserva las filas previas, repite el
upgrade, prueba downgrade vacío y comprueba rechazo sin pérdida cuando ya existe
un hecho. Los tests core observan firma real38, cinco flags false, no owner, FORCE
de la tabla nueva, GUCs limpios, no contexto/cross-tenant, owner/admin/viewer/
personal, append/rollback/immutabilidad/fuente y los cuatro cruces/replay. Los
counts de tablas/ORM/FORCE se registrarán desde la conexión real y el target38;
no se presentan los esperados estáticos como una captura que todavía no existe.

Viewer puede leer la procedencia del cliente donde ya tiene permiso de lectura,
sin declararla. La consulta agregada mantiene el permiso analytics original
owner/admin; leer clientes no le concede analytics global. En PG el trigger
reemplaza el reloj aportado por el reloj servidor; su caso comprueba que no queda
el timestamp backdated. No se transporta como literal el caso SQLite que rechaza
ese input, ni se modifica su aserción original.

Los cinco cuerpos HTTP de contraseña y sus labels originales se reexportan sin
cambios. Reset/cambio/registro/login usan ambas factories originales; invitación
conserva el SaaS-only original porque API no ofrece ese endpoint. No se sustituye
principal, validador, ruta, hash/MFA ni proveedor real: se conservan sus sinks
locales y aislamiento originales. Las identidades/counters finales deben salir
de la colección real y JUnit exacto, no de los14 objetos estáticos preparados.

Restore usa el núcleo backup_restore sin cambios: snapshot cifrado/autenticado de
dos tenants con declaraciones y plan_saved, reclasificación posterior y dos
objetos privados sintéticos. Primero commonclose cierra y verifica ausencia de
la UUID fuente. Luego autentica los artefactos y restaura en otra UUID vacía. Se
comparan exactamente IDs, versiones, origen, timestamps y fuentes del ledger,
firma38 completa, contexto vacío y aislamiento por tenant, más bytes/propiedad de
los objetos. Es una extensión de esquema de prueba; no atribuye custodia durable
de negocio, RPO/RTO o aceptación R08 global al kit37 anterior.

La concesión nueva usa `product38-pg-exclusive-v1`, cuatro claves ACK originales:
`approved`, `scope`, `contract_sha256`, `expires_at_UTC` (máximo8h). Root debe pasar
`PG38_PHASE`, `PG38_PROFILE`, `PG38_GENERATION`, `PG38_ACK`, y un Task nuevo directo
bajo E/tmp con `ACCOUNT37_PRIVATE_LEASES=Task/leases` y evidencia privada existente
`METODOBASE_TEST_EVIDENCE_DIR`. TEMP/TMP/TMPDIR permanecen E/tmp; no convertir Task
en TEMP porque el owner603f liga su parent al tempfile original. No hay publisher
automático ni ACK creado por este paquete.

API propuesta para emisión Root: `pg_contract.build_contract(phase, profile,
generation)` seguido de `require_ack(ack, contract)`. El contrato liga la ruta
real del repo, mapa RAW de las8 raíces runtime y cierre de helpers de esa fase,
perfil/generación y selección/presupuesto. Su FileSetDigest es **distinto** del
digest del capturador: incluye los tests/helpers relevantes. Se recomputa después
de copiar targets38 aceptados; no usar el digest previo de preparación como ACK
para otros bytes. No hay HEAD ficticio para esta beta sin commit.

La primera SQL exige ACK38; cada CREATE vuelve a validar fuente/perfil/lease y la
generación c6ff en **el mismo cursor inmediatamente antes de CREATE**. Se rechaza
otro scope, presupuesto, sesión anidada o intento tras cierre fallido. El wrapper
e905 vuelve a validar generación/OID/owner al drenar. Sigue siendo obligatoria la
ventana Root exclusiva sin restart; los callbacks metadata no son una prueba de
generación nativa en cada evento. Los helpers603f/e905/c6ff permanecen literales.

Tras revisión Root y targets38 genuinos, la selección futura es sólo el módulo
de la fase de pg-plan.json usando tests/run_isolated.py. Antes de runtime Root
debe recoger identidades sin fixtures, exigir JUnit exacto sin skips/fallos/
errores/duplicados, fotos fuente/WEB92/Node/base/PG/roles y pip0 antes/después,
auditoría exacta de todas las leases y sus commonclose. Este paquete no ejecuta
esa orquestación ni sustituye esas evidencias con un contador local. Nada de
SQL, pytest, importaciones SUT, procesos PG/VM/Chrome o servicios se ejecutó al
preparar las fuentes.

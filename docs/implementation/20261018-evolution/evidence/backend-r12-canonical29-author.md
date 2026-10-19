# R12: traslado canónico29, mecanismos de autor

Base de producto7cf4e6c; worktree exclusivo member-link. El contrato v2 y el
laboratorio35 permanecen históricos e intactos. Este lote no monta rutas/API,
no envía correo, no usa un proveedor ni declara aceptación independiente.

## Traslado

La revisión `20261019_client_account_links` añade tres tablas de negocio:
client_account_links, client_link_invitations y client_plan_publications.
El resultado son29 tablas de negocio,23 familias RLS y las6 tablas de control
anteriores. No hay backfill ni adopción de Cliente/Plan por correo o cercanía.
Las claves compuestas nuevas de Cliente/Plan acreditan doble propietario.

El DDL nuevo está congelado en member_link_ddl por dialecto, generado una vez
desde la definición nueva para revisión; la migración ejecuta esas sentencias
fijas y no usa create_all. El import de modelos no ejecuta DDL. Preflight28
verifica estructura y seguridad exactas antes de modificar la primera tabla.
Bootstrap conserva su transacción bloqueante/FK-check de SQLite y rollback PG.

Los targets22–28, las20 políticas anteriores y los vocabularios v1 anteriores
no se alteran. El target29 compone esa firma de estructura/policies con una
sección nueva versionada de funciones/triggers: invoker, search_path fijo,
volatilidad, permisos, cuerpos, flags y declaraciones de triggers diferidos.
Runtime rechaza deshabilitar/quitar un guard además del drift estructural.
El hook real de cada begin borra el digest de invitación de cualquier sesión
previa; no cambia tenant ni conserva una capacidad entre commits.

La definición SQLite conserva FK diferida, inmutabilidad, origen y efectos de
invalidación. No se le atribuye la seguridad RLS/GUC de PostgreSQL; producción
SQLite sigue prohibida. La validación completa de menú en SQLite será también
responsabilidad del servicio compartido antes de la escritura.

## Fuente de la proyección

El guard INSERT toma/relee la fuente autorizada y deriva una proyección desde
sus cuatro comidas y diez campos meta conocidos. No copia notas/perfil/paths.
La función invoker sólo interpreta la fila argumento, no consulta datos
globales. Rechaza JSON duplicado/corrupto, claves/formas desconocidas, comidas
vacías, números no finitos, exceso de profundidad/volumen y alimentos/opciones
fuera de los límites técnicos. No recalcula nutrientes desde un catálogo.

Límites técnicos íntegros: fuente y proyección256KiB UTF-8, profundidad12,
256 opciones por grupo,32 vegetales,256 alimentos en comida fija, nombre200,
equivalencia500 y números nutricionales entre0 y10^12 (gramos positivos).
Son presupuestos de representación, no cupos comerciales; ante exceso se
rechaza entero. La API deberá además conservar cuerpo16KiB/response512KiB.

INSERT compara el JSON propuesto contra la derivación exacta y verifica SHA
de sus bytes; persiste la representación canónica DB y su SHA recalculado.
El límite de bytes de NEW se comprueba antes de parsearlo. FK/descriptor no
permiten sustituir Plan/PDF o autorizar un payload distinto. Todos los campos
del descriptor presente son NOT NULL explícitos; SQL UNKNOWN no lo satisface.
DB exige ready/kind y descriptor/backend permitido iguales al objeto exacto;
servicio y descarga deberán exigir también el backend configurado y nunca
resolver otro objeto, bytes legacy o fallback.

## Canarios y errores de harness

- Canónico35:35 passed /19.82s con fuentes migradas29 y rol app restringido.
  Es una adaptación explícita separada de tablas/fixture/columnas nuevas;
  el original de laboratorio no se reescribió.
- Proyección/constraints/migración:31 passed /90.08s. Incluye13 PG de payload,
  proof/hook real y cuatro comidas fijas/opciones;8 CHECK/FK SQLite;10 casos
  de vacío/poblado28→29, repeat, rollback real, drift y preservación.
- Driver root adaptado+payload:19 passed /14.95s. Conserva los4 positivos y el
  criterio rojo original de payload con columnas/SHA canónicos requeridos;
  los adversariales propios usan fuente válida completa y SHA coherente.
- La primera tanda de proyección tuvo47 positivos y2 errores del mismo caso
  oversize: pytest construyó un ID de262KiB que excedió PYTEST_CURRENT_TEST en
  Windows. Sólo se pusieron IDs cortos al parámetro; RAW previo está en Temp,
  SHA3d19ad7fdace4ca1d8401d99c999e4fde51bc11aaa3552d41730ff64038c55d0.

## Rojo adicional de lock del propietario, antes de API

El test directo `test_direct_publisher_retains_owner_lock_before_waiting_for_object`
demostró1 fallo /8.29s: el guard retenía Cliente/Link/Plan y esperaba Objeto,
pero otro proceso podía confirmar la desactivación del propietario. Tras
liberar Objeto, la publicación confirmaba con la elegibilidad anterior.

Preimagen RAW de SQL/target/driver/log/XML conservada en Temp, ZIP SHA
f9693f739983104630c5ad8d154a9b99ef8b2d0465c47dcff7111e23ec753653;
policy antes9848769ab667e6fddbac27afef4b7c1f2a8bc0d19c2de0fd185a400ce9dba8f5;
driver114d6f5c1a52f96651100ec64ee50543d5fbc574515a490a659b3d7b75d4d5e0.
No se afirma un incidente de producción.

La corrección agrega un helper invoker de lock/revalidación de propietario
FOR SHARE NOWAIT en toda nueva concesión/rotación, antes de fuentes en INSERT
de publicación. El servicio seguirá bloqueando TODOS los Usuario requeridos en
orden total/NOWAIT antes de recursos; el guard sólo repite el requisito. En
consumo directo, un lock adicional de propietario también es NOWAIT: no crea
una espera inversa con R11. Revocación/invalidation/withdraw no vuelven a
Usuario ni requieren su elegibilidad, preservando el delta Gscope aprobado.

Replay final del cambio: **55 passed /38.51s**, incluye35 canónicos,14 de
proyección/proof/volumen,5 criterios root adaptados y el nuevo canario de
lock Usuario. La preimagen roja no se sobrescribe. Después:
API/servicios, matriz HTTP/PDF/mail double, compatibilidad runtime RC completa,
históricos explícitos y restore29. Ninguna cifra anterior cierra esos gates.

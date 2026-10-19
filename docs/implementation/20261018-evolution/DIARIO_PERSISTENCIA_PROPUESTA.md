# Contrato de implementación R14 personal

Secuencia posterior al checkpoint26; todavía propuesta técnica sin API ni tabla integrada. La preparación4e22852 conserva35 pruebas de DTO/fecha/snapshot. La revisión de publicación individual ya ocupa26; la nueva migración del diario será27, posterior a `20261018_individual_publication`. No cambiar contratos/migraciones anteriores.

El alcance obligatorio procede de R14 y UX-03/UX-04: mismo estado autenticado en dos dispositivos, logout conserva historial, cuentas aisladas y fecha local explícita. El espacio personal puede implementarse antes de R12; no autoriza compartir datos con un gimnasio ni convertir un cliente profesional en perfil personal. Los datos locales sin identidad no se importan, asignan ni borran por heurística.

## Identidad y almacenamiento

Nueva tabla `personal_diary_days`, propietaria por `user_id` autenticado persistido, no por un campo del body o un parámetro gym. Admitir las mismas identidades personales que el producto soporta: cuenta individual activa o miembro profesional activo que conserva su espacio personal; no cartera de propietario. Verificar Usuario activo/no borrado y rol/tipo actuales, enlazar contexto con `bind_verified_subject` y rechazar contexto incompatible. El middleware ya selecciona identidad personal para `/api/usuario/`.

La nueva capacidad admite identidades personales inequívocas: cuenta `tipo=usuario` con rol válido noOWNER o miembro válido que conserva su espacio personal. Registro nuevo crea VIEWER. El tipo legado por sí solo no acredita procedencia personal: la prueba independiente `test_owner_authority_excludes_portfolio_even_with_individual_persisted_type` cambia un propietario con cartera a `tipo=usuario` conservando OWNER y exige mantener la cartera excluida de exportación. Esa barrera y ese test se conservan. Un OWNER ambiguo recibe `diary_context_requires_review`; no se adopta un Cliente/Plan por cantidad, email, suscripción o semejanza. R02/R12 deben establecer asociación personal explícita antes de ampliar ese caso. Las rutas/derechos existentes de generación no se alteran en este lote.

Coordinación propuso inicialmente ampliar por tipo al observar la fixture de UI individual con OWNER; el primer gate125/1 del backend mostró que vulneraba la barrera anterior. Esa expectativa de permiso se revocó antes de integrar: no se modifica la prueba independiente ni la historia para ocultar el fallo. La fixture UI y su éxito en una ruta existente no acreditan titularidad personal de una cartera.

Unicidad `(user_id, local_date)`; fecha SQL Date, zona `America/Mexico_City` explícita y fija conforme a la preparación existente, agua en ml0–20000, versión positiva, instantes nuevos UTC tipados, contenido de cuatro comidas en JSON textual acotado y comprobado antes de deserializar. FK de cuenta RESTRICT para no introducir borrado CASCADE de historia sensible sin workflow/política revisados. La migración añade la familia FORCE RLS por `user_id`; ausencia/otra identidad deniega lectura y escritura bajo rol app. No cambia familias anteriores ni concede privilegios.

Cada comida guarda snapshot de alimentos/gramos/macros del plan propio autorizado más selección explícita, fuente y fecha UTC de registro. No acepta totales, alimentos, `user_id` ni `gym_id` del cliente. Usar lector con doble dueño de Plan/Cliente, no un filtro único de Plan. Inactivo puede mantener historia; borrado o asociación mixta no sirve como fuente nueva. Acotar plan JSON, número/tamaño de alimentos y snapshot antes de persistir; legado ilegible exige409, sin completar valores ficticios. Un plan nuevo no reescribe snapshots consumidos, y borrar el origen no borra el snapshot.

## Operaciones HTTP

| Operación | Contrato |
| --- | --- |
| GET `/api/usuario/diario/{day}` | Lectura readonly/no-store de fecha ISO; día ausente responde versión0 y valores vacíos, sin INSERT/commit |
| GET `/api/usuario/diario?start=...&end=...` | Hasta62 fechas, orden/presupuesto explícitos, sin buscar historia ilimitada; incluir zona/today servidor |
| PATCH `/api/usuario/diario/{day}` | Unión discriminada existente: water, meal o completion y expected_version; body no admite campos extra |

Una mutación sustituye sólo el valor declarado. Se serializa con lock de cuenta usado por servicios existentes; refresca estado persistido y verifica versión bajo ese lock. expected_version0 sólo crea si no hay fila; conflicto409 permite recargar sin sobrescribir otro dispositivo. El límite evita overflow de versión; ningún error confirma guardado anticipado. Un solo commit atómico por operación. Un fallo de commit no devuelve éxito; logs públicos y técnicos no contienen contenido/SQL/parámetros sensibles. No crear borrador al hacer GET ni mantener un Session global.

No guardar fechas futuras según `local_today` existente; conservar fechas anteriores y frontera México/UTC. Completar una comida requiere su snapshot existente; no inventar calorías a partir de una marca. Registrar snapshot nuevo de esa comida debe tener semántica explícita sobre su completado y no modificar otras comidas/agua. El estado devuelto incluye versión, local_date, timezone, agua, snapshots/completado e instantes verificables; sin tokens ni datos de otra cuenta.

## Integraciones y aceptación

Montar router en ambas composiciones, probar primero `web/main_web.py`. La exportación personal debe incorporar el diario con keyset por fecha y presupuesto; el mismo contrato de cuenta personal excluye la cartera profesional. No introducir una tabla sensible sin acceso a la exportación técnica existente.

Frontend continúa después de integrar su reparación de generación/PDF: reemplazar seguimiento local por API de diario y fecha local del servidor, cargar al cambiar día, estados guardando/guardado/error/conflicto veraces, fence de sesión para respuestas tardías y ninguna persistencia nueva de datos sanitarios en localStorage. Dos contextos navegador autenticados deben observar mismos valores tras recargar; logout/login no los borra; cambio de cuenta no muestra el anterior. Las claves legacy quedan sin adopción automática y con una explicación de que esos datos no están sincronizados, sin promesas de recuperación/importación no implementadas.

Aceptación independiente: SQLite/PG restringido con RLS ausencia/otra identidad, body mass assignment, plan mixto/borrado, datos sobredimensionados/corruptos, CAS concurrente multiproceso sobre día ausente y existente, lost-response/reconsulta, rollback/fallo commit, distintas cuentas/fechas, frontera medianoche local y agua/comidas sin pisarse. Migración exacta26→27/vacío, drift y rollback tras DDL, contratos26 inmutables y restore poblado27 deben conservar snapshots/versiones/políticas/filas/objetos. Navegador real móvil/teclado y dos contextos sobre mismo backend, más lectura independiente de seguridad, antes de aceptar el módulo.

R12/R25 añadirán contexto compartido y consentimiento en otro contrato; este lote no otorga acceso a profesionales ni modifica una política de retención. Los35 casos preparatorios por sí solos no prueban persistencia ni cierran R14.

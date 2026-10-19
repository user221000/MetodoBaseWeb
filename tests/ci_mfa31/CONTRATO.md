# CI31: fuente histórica y aceptación actual

La fuente histórica es `57335e5b4bcba3c76c97d47e481b526fb52874a6`, tree `31bebf83a760a500420f6552628d6a3a022b8832`: 6.591 archivos Git regulares y 233.299.475 bytes. Se materializa con `ls-tree` y `cat-file`, verificando modo, tamaño y bytes de cada objeto. No se usa `git archive`, checkout, atributos, replace refs, enlaces ni submódulos. La salida debe ser nueva, fuera del repositorio y sin ancestros reparse/symlink. Los 23 helpers históricos conservan sus hashes.

El intento anterior auténtico `eea8f773fba9b7f92241958139fcefa23b9ee1d4` permanece en evidencia: 9.542 archivos/450.366.072 bytes, canarios CI30 completos verdes, 22 VM verdes y `member_link_consumers.cjs` con 13/16. R24 incorporó companions reales que el antiguo DOM de ese harness no cargaba. No se modificó esa fuente para obtener un pase. Root autorizó seleccionar el freeze CI30 anterior a R24 y añadió el nuevo `member_link_consumers31.cjs`: conserva los 16 callbacks y carga los cuatro companions R24 reales y los includes de la plantilla. El workflow y los 23 hashes de helpers son iguales entre ambos ancestros.

## Jobs separados

| Alcance | Fuente y contratos |
| --- | --- |
| `historical-ci30` | Fuente573 auténtica; verificador íntegro: 33 canarios workflow, 55 informes R12, 24 índice, 12 seguimiento y 27 procesos inertes; 23 VM/348 ejecuciones. |
| `historical-postgres` | CWD fijo de la fuente573; exactamente 29 informes originales, incluidos índice, restore y seguimiento. Los runners28/29 reciben `--history-repository "$GITHUB_WORKSPACE"`. |
| `historical-image` | Docker y browsers originales sobre fuente573. Los informes publicados son una lista explícita de proyecciones, sin carpetas RAW. |
| `test-web`, desktop, Redis | Fuente actual; se conservan serial con cobertura, umbral, SDK, n2/shuffle, no-skips y ambos targets desktop. |
| `frontend-contracts` | Los otros22 módulos previos y los16 callbacks de consumo con companions reales; MFA74 y otros72 casos de cantidades/controles/exportación actuales. No se suman como criterios únicos. |
| `current-postgres` | Fuente actual31, 12 informes y 173 identidades completas, sin skips, errores, fallos, duplicados ni sustitución de dialecto/nodo. |
| `current-image` | Imagen actual, CMD/entrypoint real, migración one-shot, rol app restringido no owner y MIGRATOR ausente. Browsers actuales de imagen/MFA, R12, R24 y seguimiento con montaje real31. |

## Las 173 identidades actuales

`current-report-nodeids.json` proviene de colección offline de la fuente actual. Está fijado por SHA256 en `check_mfa31_reports.py`; editar JSON y su propio campo hash no cambia esa ancla ejecutable. `current-business-mapping.json` conserva el vínculo con cada función de negocio anterior.

| Informes | Casos |
| --- | ---: |
| R12 servicios / HTTP / carreras y publicación CAS | 16 / 34 / 4 |
| R24 publicación y consumo / bloqueo físico y revocación | 2 / 1 |
| MFA migraciones / servicios y procesos / restore poblado | 5 / 12 / 1 |
| Seguimiento, ambas factories | 2 |
| RLS, tenant y worker | 81 |
| Exportación privada, ambas factories | 2 |
| Diario y revisión de identidad/contexto | 13 |

Los wrappers R12 importan las funciones originales sin cambiar sus asserts. Su fixture nueva crea un UUID propio, migra a31 y verifica 32 tablas ORM, 33 físicas, el índice30 exacto y el rol restringido. El HTTP realiza password, reauth, enrollment, TOTP, password202 y recuperación persistida; rechaza replay y no construye bearer tokens. Los casos directos de servicios/RLS conservan su alcance de autorización de datos; no se presentan como pruebas del protocolo MFA.

El test de carrera R24 conserva byte a byte el cuerpo decorado del driver independiente `eb4f7d36d69fb903c1f31d5eb072f6f8063c8ef9bf8051a7915adf14cfe38f3c`; cambia sólo el montaje actual y su pool acotado. Restore31 ejecuta el caso poblado real con MFA y todos los contratos26–30; un resultado estático no lo sustituye.

Los fixtures browser nuevos migran su UUID real antes del arranque. Cada marcador31 compara datos leídos del motor; no se imprime30 usando Base31. La inscripción MFA incrementa `session_version` una vez: los nuevos controles de identidad conservan roles/perfiles y exigen ese delta causal, además del bump explícito de revocación. No se alteran los controles originales de la fuente histórica.

## Privacidad y ciclo de vida

Los logs completos, pares, challenges, semillas, kits, grants y configuración permanecen en directorios privados del runner; los archivos de credenciales tienen modo0600. Ningún valor secreto se pasa por argv o `docker inspect Env`. La imagen recibe un env-file privado y se identifica por ID exacto, image ID y label nonce. El cierre sólo usa el CID propio validado; los fixtures conservan su finalizador de UUID y los controladores esperan la salida del Popen propio. Los flags cap-drop/NNP/read-only son flags del laboratorio, no defaults del Dockerfile.

Los uploads enumeran archivos públicos exactos. Los gates de nodos completos validan el RAW antes de publicar. JUnit conserva identidades públicas/estado y elimina mensajes, stdout y trazas; si un parámetro del nombre contiene un factor, sólo esa identidad pública se sustituye por un ordinal. Los173 nodos PG fijados no contienen tales parámetros. JSON publica contadores y SHA del RAW. Se escanean valores firmados de dos partes, JWT, el formato CSRF real de tres partes y miembros ZIP expandidos, también con preámbulo. No se suben DOM/SSR, QR, kits ni carpetas privadas. Un fallo de proyección bloquea publicación.

Los proveedores están desactivados o tienen una frontera sintética declarada. Los browsers abortan orígenes externos y los fixtures host bloquean sockets fuera de loopback antes de importar producto. Esto no demuestra aislamiento de red del sistema operativo. Se usan Settings de testing para CI; no se atribuye validación de configuración de producción, entrega de correo, pagos ni despliegue.

## Evidencia y pendientes

Se ejecutaron offline materialización/FULL/VM históricos y comandos frontend actuales en Windows, controles JUnit/trust/publicación y procesos inertes. El prelude POSIX `install -m700` no funciona en este volumen Windows: el ensayo de comandos actual lo declara y precrea sólo su carpeta de logs sintéticos; la validación Linux de permisos permanece pendiente. Sus RAW iniciales se conservan.

La revisión offline no acredita Actions, Linux, build de imagen, los173 PG, restore31 ni Chromium. Esos jobs están preparados y requieren la ventana coordinada y la revisión de este freeze. No se cambian Dockerfile, locks, migraciones, targets, producto ni helpers históricos desde este delta CI.

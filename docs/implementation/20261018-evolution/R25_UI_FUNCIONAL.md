# R25 UI: consumidor contractual para composición32

Worktree exclusivo `F:/mb-r25-progress-ui-20261019`, base `809eab28c40c112cb6e3c9d8caceebae28683abd`, preparación preservada en `c7ee06d2c5277f8f182c72cfb323f3f55d29900a`. No se modificó MAIN ni el worktree backend. El wire sintético completo está conservado sin cambios como `evidence/r25-ui/backend-wire-v1.json`, SHA256 `982c26596daaf6a315661151ab8ad76bb42a61290dcec7bc6833e3c5aa7533a0`. Es un contrato de entrada; no prueba aceptación del API o del accesor SQL. El backend congeló `bd0501cdfbad1e48d483718b66e31bb65559f05e` después; todavía no está compuesto en esta rama.

## Rutas y fuentes

- `/mi-progreso`: SSR privado, medidas/contadores propios, selección explícita de perfil y descubrimiento de permisos propios.
- `/clientes/{client_id}/progreso`: SSR privado de sólo lectura, historia nativa de la ficha y proyección de un vínculo elegido por separado.
- API helpers: bootstrap/perfiles, mediciones/lista/exacto/PUT/retirada, completados, consentimientos propios/lista/exacto/PUT/retirada y las tres consultas profesionales que fija wire-v1. No se montan routers32 desde la UI.
- Exportación: octavo conjunto `progress_consents`, cursor `after_progress_consent`, scope `own_append_only_scope_metadata`, coverage `account_persisted_personal_space_active_member_links_and_own_progress_consents`. Límite completo1064960 bytes y131072 por colección, sin truncar registros ni repetir colecciones ya finalizadas entre partes. No incluye salud compartida ni cartera profesional.

Los helpers y el parser distinguen identificadores: perfil legacy/cursor de perfiles String1..36 no crea autoridad; fuente para registros/grants nuevos UUID canónico; medición propia key UUID retenida en RAM; página de mediciones cursor opaco hasta512; permiso id+version más versión del vínculo; consultas profesionales repiten esos CAS. El cursor nuevo de exportación exige lowercase UUID; los siete cursores anteriores mantienen su representación sin conversión.

## Medidas y observación

No se elige el primer perfil automáticamente. El formulario muestra fecha civil y unidades explícitas; exige una medida declarada y no deriva masa magra. Legacy conserva fuente/fecha de medición no verificadas; su timestamp histórico sólo figura como registro. Las tablas siguen accesibles sin gráfico. La tendencia contiene únicamente puntos de mediciones declaradas en al menos dos fechas distintas; no interpola, rellena ausencias o interpreta clínicamente.

Completados significa X de Y snapshots de consumo registrados marcados completados. No se asumen cuatro comidas, ingesta por abrir un plan, porcentajes para días ausentes ni adherencia clínica. Una base0 se muestra sin proporción. Today y zona proceden del servidor; no se obtiene el día con UTC del navegador. Las consultas tienen el máximo técnico62 inclusivo ya fijado por backend. No hay guardados al abrir, cambiar filtros o seleccionar un perfil.

El primer PUT conserva key/payload en RAM antes del await. No hay refresh/replay automático de mutaciones. Respuesta perdida o desconocida conserva la intención; la consulta exacta puede confirmar el estado, mostrar conflicto o permitir un reintento explícito con la misma key/payload si no se encontró el registro. Corrección usa el key existente y la versión observada. Tras conflicto se compara una lectura fresca y sólo una nueva acción explícita prepara otra corrección. Retirar no afirma borrar datos ni fija retención.

## Permisos y barreras

Discovery/retirada se cargan antes e independientemente de bootstrap personal. OWNER legítimo o ambiguo puede acceder exclusivamente a los eventos propios/retirada que autorice el servidor, aun con fuente oculta. Se mantienen ocultos perfil, medidas, nuevas autorizaciones y contactos de la fuente cuando no hay capacidad personal. Una lista de eventos o exportación no concede permiso nuevo.

Para un grant se elige un vínculo activo, se consulta su estado, se marcan categorías sin defaults y se elige perfil propio habilitado si hay medidas. Fechas de consentimiento futuras son válidas; ongoing exige checkbox y fin null expresos. Cambiar el alcance desmarca la confirmación. El PUT usa el id+version del evento y la versión de vínculo observados. Retirada usa sólo CAS propio; no MFA ni paywall. Después de error/conflicto/incertidumbre se ofrece lectura fresca y revisión, nunca reenvío automático o sustitución silenciosa por el último evento.

Profesional es sólo lectura. El servidor determina identidad persistida, roles y derecho vigente `progresion_clientes`; el cliente no asigna ese derecho ni ofrece un CTA de cobro. La proyección admite sólo campos/categorías consentidos y la identidad exacta del vínculo/evento. Las columnas no compartidas no se rotulan como medidas inexistentes. Un fallo de relectura descarta la proyección y la ficha visible; no hay copia profesional persistida ni acceso recíproco al diario, alimentos, agua, notas, contactos o planes personales.

## Fences y persistencia

Se reutilizan `MemberLinkContext` y el transporte existente. Hay comprobaciones antes/después de cada await, normalización, control y render. El evento central síncrono, Storage o pagehide descartan formularios, resultados, cursores e intenciones en RAM. Los handlers no continúan si los controles invalidaron el contexto. La escritura se liga al access exacto; no pide grant MFA ni reenvía su DTO con credenciales renovadas o de otra cuenta.

No se añaden datos sanitarios, claves, cursores, grants ni caches a Storage. No se leen, importan, asignan o borran las claves legacy sin identidad. El transporte/MFA y los consumidores R24 se conservan; el sello comprueba la preimagen completa de Api.js al invertir exclusivamente los helpers/cursor nuevos, y compara bloques de fences/exportación preexistentes. No se cierra R10 ni se promete atomicidad de las dos claves de sesión, reload o pestañas.

## Evidencia y límites

Antes SSR dos404 preservados; preparación52VM y2SSR en c7ee06d. Export8 inicial0/2 con fixture del nuevo contrato, después38/38 (21 aserciones previas reutilizadas sin cambios y17 propias). Dos sondas adicionales detectaron fecha imposible normalizada y ciclo por caso; se preservan36/38 antes,38/38 después, y cuerpo intermedio reconstruido por inversión de patch con replay explícitamente posterior. No se presenta esa reconstrucción como captura RAW original. Wire-v1 aclaró después lowercase estricto para el cursor nuevo y perfiles legacy; fixtures y cliente se ajustaron al contrato, sin retarget de los siete cursores anteriores.

El canario de columnas compartidas conservó13/14 antes y14/14 después; el cuerpo anterior existe en `functional-edge-source-raw.zip`. La composición VM de páginas pasó12 iniciales y16 finales, incluyendo doble submit, ACK perdido, retry exacto, conflicto CAS, OWNER tras reload y limpieza síncrona de Storage. Los informes finales separan152 VM (131 propios y21 aserciones de exportación previas) y dos SSR web reales. Son DOM/HTTP/auth/store doblados salvo los dos SSR; no son152 HTTP32.

Falta composición aislada con backend32 aceptable, HTTP autenticado real de ambas factories, condiciones del lector PG, navegador móvil/desktop, teclado, foco, axe y revisión independiente. No se atribuyen estos gates a esos pendientes ni se afirma R25 cerrado. No hubo Chrome, PG, servidores, proveedores, envíos o cargos en esta fase. R14/diario, MFA y privacidad previa conservan su alcance; no se añaden derivaciones clínicas o nuevas políticas de duración.
